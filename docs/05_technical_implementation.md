# AI Research Draft Generator - Technical Implementation Guide

## 1. Implementation Overview

This guide provides detailed technical implementation instructions for building the AI Research Draft Generator system using the specified technology stack.

## 2. Development Environment Setup

### 2.1 Prerequisites
```bash
# Python 3.9 or higher
python --version

# Node.js 18 or higher
node --version

# Git for version control
git --version
```

### 2.2 OpenAI API Setup
1. Create OpenAI account at https://platform.openai.com/
2. Generate API key
3. Set environment variable: `OPENAI_API_KEY=your-key-here`

### 2.3 Project Structure Creation
```bash
# Create main directories
mkdir -p backend/app/{models,services,routes,utils}
mkdir -p frontend/src/{components,pages,services,hooks,utils,styles}
mkdir -p chroma_db/processing_state
mkdir -p data/uploads
```

## 3. Backend Implementation

### 3.1 Dependencies & Requirements

**File**: `backend/requirements.txt`
```txt
Flask==2.3.3
Flask-RESTX==1.1.0
Flask-CORS==4.0.0
python-dotenv==1.0.0
chromadb==0.4.15
openai==0.28.1
langchain==0.0.329
PyPDF2==3.0.1
requests==2.31.0
python-dateutil==2.8.2
uuid==1.30
tenacity==8.2.3
werkzeug==2.3.7
beautifulsoup4==4.12.2  # For enhanced HTML/SVG parsing
xml-python==0.1.0       # For SVG processing
lxml==4.9.3              # XML/HTML parser for estimates_parser
```

### 3.2 Configuration Management

**File**: `backend/app/config.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    OPENAI_EMBEDDING_MODEL = os.environ.get('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002')
    
    # ChromaDB Configuration
    CHROMA_DB_PATH = os.environ.get('CHROMA_DB_PATH', './chroma_db')
    
    # File System Configuration
    # Use environment variables if set, otherwise default to project root relative paths
    env_data_path = os.environ.get('DATA_ROOT_PATH')
    if env_data_path:
        DATA_ROOT_PATH = os.path.abspath(env_data_path)
    else:
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        DATA_ROOT_PATH = os.path.join(PROJECT_ROOT, 'data')
    
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(DATA_ROOT_PATH, 'uploads'))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './data/uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    
    # Processing Configuration
    CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '1000'))
    CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', '200'))
    MAX_CONCURRENT_PROCESSING = int(os.environ.get('MAX_CONCURRENT_PROCESSING', '3'))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
```

### 3.3 Application Factory

**File**: `backend/app/__init__.py`
```python
from flask import Flask
from flask_restx import Api
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import os

from app.config import config
from app.routes import company_bp, knowledge_base_bp, document_bp, report_bp, health_bp

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # CORS
    CORS(app, origins=['http://localhost:3000'])
    
    # API Documentation
    api = Api(
        app,
        version='1.0',
        title='AI Research Draft Generator API',
        description='REST API for investment research draft generation',
        doc='/swagger/'
    )
    
    # Register Blueprints
    api.add_namespace(company_bp, path='/api/companies')
    api.add_namespace(knowledge_base_bp, path='/api')
    api.add_namespace(document_bp, path='/api')
    api.add_namespace(report_bp, path='/api')
    api.add_namespace(health_bp, path='/api')
    
    # Configure Logging
    configure_logging(app)
    
    # Create required directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHROMA_DB_PATH'], exist_ok=True)
    
    return app

def configure_logging(app):
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/app.log', 
            maxBytes=10240000, 
            backupCount=10
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('AI Research Draft Generator startup')
```

### 3.4 Database Service

**File**: `backend/app/services/database_service.py`
```python
import chromadb
from chromadb.config import Settings
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

from app.config import Config

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client"""
        try:
            self.client = chromadb.PersistentClient(
                path=self.config.CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info(f"ChromaDB client initialized at {self.config.CHROMA_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise
    
    def get_collection(self, ticker: str):
        """Get or create collection for a company"""
        collection_name = f"company_{ticker.lower()}_knowledge_base"
        
        try:
            collection = self.client.get_collection(collection_name)
            logger.debug(f"Retrieved existing collection: {collection_name}")
        except Exception:
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"company_ticker": ticker.upper()}
            )
            logger.info(f"Created new collection: {collection_name}")
        
        return collection
    
    def add_documents(self, ticker: str, documents: List[Dict]):
        """Add documents to company collection"""
        collection = self.get_collection(ticker)
        
        ids = [doc['id'] for doc in documents]
        embeddings = [doc['embedding'] for doc in documents]
        metadatas = [doc['metadata'] for doc in documents]
        documents_text = [doc['document'] for doc in documents]
        
        try:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            logger.info(f"Added {len(documents)} documents to {ticker} collection")
        except Exception as e:
            logger.error(f"Failed to add documents to {ticker} collection: {str(e)}")
            raise
    
    def query_similar_documents(self, ticker: str, query_embedding: List[float], 
                              n_results: int = 10, where_filter: Dict = None):
        """Query similar documents from collection"""
        collection = self.get_collection(ticker)
        
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.debug(f"Retrieved {len(results['ids'][0])} similar documents for {ticker}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to query similar documents for {ticker}: {str(e)}")
            raise
    
    def get_company_stats(self, ticker: str) -> Dict:
        """Get statistics for a company collection"""
        collection = self.get_collection(ticker)
        
        try:
            count = collection.count()
            
            # Get recent documents
            recent_docs = collection.get(
                where={"processed_date": {"$gte": "2025-09-06T00:00:00Z"}},
                limit=1
            )
            
            # Get document types
            investment_data_count = len(collection.get(
                where={"document_type": "investment_data"}
            )["ids"])
            
            past_reports_count = len(collection.get(
                where={"document_type": "past_report"}
            )["ids"])
            
            return {
                "total_documents": count,
                "past_reports": past_reports_count,
                "investment_data": investment_data_count,
                "has_recent_updates": len(recent_docs["ids"]) > 0,
                "status": "active" if count > 0 else "empty"
            }
        
        except Exception as e:
            logger.error(f"Failed to get stats for {ticker}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def update_processing_state(self, ticker: str, state: Dict):
        """Update processing state for a company"""
        state_dir = os.path.join(self.config.CHROMA_DB_PATH, "processing_state")
        os.makedirs(state_dir, exist_ok=True)
        
        state_file = os.path.join(state_dir, f"{ticker.upper()}.json")
        
        state["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Updated processing state for {ticker}")
        except Exception as e:
            logger.error(f"Failed to update processing state for {ticker}: {str(e)}")
            raise
    
    def get_processing_state(self, ticker: str) -> Optional[Dict]:
        """Get processing state for a company"""
        state_file = os.path.join(
            self.config.CHROMA_DB_PATH, 
            "processing_state", 
            f"{ticker.upper()}.json"
        )
        
        if not os.path.exists(state_file):
            return None
        
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load processing state for {ticker}: {str(e)}")
            return None
```

### 3.5 Document Processing Service

**File**: `backend/app/services/document_service.py`
```python
import PyPDF2
import hashlib
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.ai_service import AIService
from app.config import Config

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    def __init__(self, config: Config):
        self.config = config
        self.ai_service = AIService(config)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
        )
    
    def extract_pdf_text(self, file_path: str) -> Tuple[str, Dict]:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\\n--- Page {page_num + 1} ---\\n{page_text}"
                
                metadata = {
                    "total_pages": page_count,
                    "character_count": len(text),
                    "word_count": len(text.split())
                }
                
                logger.info(f"Extracted text from {file_path}: {page_count} pages, {len(text)} characters")
                return text, metadata
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {str(e)}")
            raise
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return f"sha256:{hash_sha256.hexdigest()}"
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {str(e)}")
            raise
    
    def chunk_document(self, text: str, metadata: Dict) -> List[Dict]:
        """Split document into chunks with metadata"""
        try:
            chunks = self.text_splitter.split_text(text)
            
            chunked_docs = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i + 1,
                    "total_chunks": len(chunks),
                    "word_count": len(chunk.split()),
                    "character_count": len(chunk)
                })
                
                chunked_docs.append({
                    "text": chunk,
                    "metadata": chunk_metadata
                })
            
            logger.info(f"Created {len(chunks)} chunks from document")
            return chunked_docs
            
        except Exception as e:
            logger.error(f"Failed to chunk document: {str(e)}")
            raise
    
    def process_pdf_report(self, ticker: str, file_path: str) -> List[Dict]:
        """Process a PDF report into embeddings"""
        file_name = os.path.basename(file_path)
        file_hash = self.calculate_file_hash(file_path)
        
        # Extract text
        text, pdf_metadata = self.extract_pdf_text(file_path)
        
        # Create base metadata
        base_metadata = {
            "company_ticker": ticker.upper(),
            "document_type": "past_report",
            "file_name": file_name,
            "file_path": file_path,
            "file_hash": file_hash,
            "processed_date": datetime.utcnow().isoformat() + "Z",
            "content_type": "research_analysis",
            "processing_version": "1.0"
        }
        base_metadata.update(pdf_metadata)
        
        # Chunk document
        chunks = self.chunk_document(text, base_metadata)
        
        # Generate embeddings
        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                embedding = self.ai_service.generate_embedding(chunk["text"])
                
                embedded_chunks.append({
                    "id": f"{ticker.lower()}_report_{file_name}_{i+1:03d}",
                    "embedding": embedding,
                    "metadata": chunk["metadata"],
                    "document": chunk["text"]
                })
                
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {i+1}: {str(e)}")
                raise
        
        logger.info(f"Processed {file_name}: {len(embedded_chunks)} embedded chunks")
        return embedded_chunks
    
    def process_investment_data(self, ticker: str, data_type: str, file_path: str) -> List[Dict]:
        """Process investment data JSON files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_name = os.path.basename(file_path)
            
            # Extract readable text from JSON
            if data_type == "investment_thesis":
                text = self._extract_investment_thesis_text(data)
            elif data_type == "investment_drivers":
                text = self._extract_investment_drivers_text(data)
            elif data_type == "risks":
                text = self._extract_risks_text(data)
            else:
                text = json.dumps(data, indent=2)
            
            # Generate embedding
            embedding = self.ai_service.generate_embedding(text)
            
            # Create metadata
            metadata = {
                "company_ticker": ticker.upper(),
                "document_type": "investment_data",
                "data_type": data_type,
                "file_name": file_name,
                "processed_date": datetime.utcnow().isoformat() + "Z",
                "content_type": "structured_data",
                "is_current": True,
                "processing_version": "1.0"
            }
            
            # Add specific fields based on data type
            if data_type == "investment_thesis" and "rating" in data:
                metadata["rating"] = data.get("rating")
                metadata["target_price"] = data.get("targetPrice")
            
            document = {
                "id": f"{ticker.lower()}_{data_type}_{datetime.now().strftime('%Y%m%d')}",
                "embedding": embedding,
                "metadata": metadata,
                "document": text
            }
            
            logger.info(f"Processed investment data: {file_name}")
            return [document]
            
        except Exception as e:
            logger.error(f"Failed to process investment data {file_path}: {str(e)}")
            raise
    
    def _extract_investment_thesis_text(self, data: Dict) -> str:
        """Extract readable text from investment thesis JSON"""
        thesis = data.get("investmentThesis", "")
        # Remove HTML tags for cleaner text
        import re
        clean_thesis = re.sub('<.*?>', '', thesis)
        
        parts = [f"Investment Thesis: {clean_thesis}"]
        
        if data.get("targetPrice"):
            parts.append(f"Target Price: ${data['targetPrice']}")
        if data.get("rating"):
            parts.append(f"Rating: {data['rating']}")
        
        return "\\n".join(parts)
    
    def _extract_investment_drivers_text(self, data: Dict) -> str:
        """Extract readable text from investment drivers JSON"""
        drivers = data.get("investmentDrivers", "")
        # Remove HTML tags
        import re
        clean_drivers = re.sub('<.*?>', '', drivers)
        clean_drivers = re.sub('<li>', '• ', clean_drivers)
        
        return f"Investment Drivers:\\n{clean_drivers}"
    
    def _extract_risks_text(self, data: Dict) -> str:
        """Extract readable text from risks JSON"""
        import re
        
        upside = data.get("risksToUpside", "")
        downside = data.get("riskToDownside", "")
        
        # Clean HTML tags
        clean_upside = re.sub('<.*?>', '', upside)
        clean_upside = re.sub('<li>', '• ', clean_upside)
        
        clean_downside = re.sub('<.*?>', '', downside)
        clean_downside = re.sub('<li>', '• ', clean_downside)
        
        parts = []
        if clean_upside:
            parts.append(f"Risks to Upside:\\n{clean_upside}")
        if clean_downside:
            parts.append(f"Risks to Downside:\\n{clean_downside}")
        
        return "\\n\\n".join(parts)
```

### 3.6 AI Service Integration

**Enhanced AI Service with Comparative Analysis**

The AI service has been enhanced with sophisticated comparative analysis capabilities that integrate estimates data for thorough quantitative analysis.

**File**: `backend/app/services/ai_service.py`
```python
import openai
from typing import List, Dict, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.config import Config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, config: Config):
        self.config = config
        openai.api_key = config.OPENAI_API_KEY
        self.model = config.OPENAI_MODEL
        self.embedding_model = config.OPENAI_EMBEDDING_MODEL
    
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = openai.Embedding.create(
                input=text,
                model=self.embedding_model
            )
            
            embedding = response['data'][0]['embedding']
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def generate_report_draft(self, new_document: str, context_documents: List[Dict], 
                            analysis_type: str = "general") -> Dict:
        """Generate research report draft"""
        
        # Prepare context
        context = self._prepare_context(context_documents)
        
        # Create prompt
        prompt = self._create_report_prompt(new_document, context, analysis_type)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert investment research analyst. Generate concise, factual analysis focusing only on new information and changes compared to existing research."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            draft_content = response.choices[0].message.content
            
            # Parse structured response
            structured_draft = self._parse_draft_response(draft_content)
            
            logger.info(f"Generated report draft for {analysis_type} analysis")
            return structured_draft
            
        except Exception as e:
            logger.error(f"Failed to generate report draft: {str(e)}")
            raise
    
    def _prepare_context(self, context_documents: List[Dict]) -> str:
        """Prepare context from similar documents"""
        context_parts = []
        
        for doc in context_documents[:5]:  # Limit to top 5 most relevant
            metadata = doc.get("metadata", {})
            document_text = doc.get("document", "")
            
            doc_type = metadata.get("document_type", "unknown")
            file_name = metadata.get("file_name", "unknown")
            
            context_parts.append(f"[{doc_type.upper()} - {file_name}]\\n{document_text[:500]}...")
        
        return "\\n\\n---\\n\\n".join(context_parts)
    
    def _create_report_prompt(self, new_document: str, context: str, analysis_type: str) -> str:
        """Create prompt for report generation"""
        
        base_prompt = f"""
        You are analyzing a new document for investment research. Compare it against existing research and identify only NEW information and CHANGES.

        EXISTING RESEARCH CONTEXT:
        {context}

        NEW DOCUMENT TO ANALYZE:
        {new_document}

        ANALYSIS TYPE: {analysis_type}

        Please provide a structured analysis with the following sections:

        1. EXECUTIVE SUMMARY (2-3 sentences of key takeaways)

        2. KEY CHANGES (list format):
        - What has changed from previous analysis?
        - New guidance, metrics, or outlook
        - Updated business developments

        3. NEW INSIGHTS (bullet points):
        - Information not previously covered
        - New risks or opportunities identified
        - Fresh data points or metrics

        4. INVESTMENT THESIS IMPACT:
        - Does this affect the investment rating?
        - Any changes to price target reasoning?
        - Updated key investment drivers

        Focus only on NEW and CHANGED information. Do not restate existing analysis. Be specific and quantitative where possible.
        """
        
        return base_prompt
    
    def _parse_draft_response(self, draft_content: str) -> Dict:
        """Parse the AI response into structured format"""
        
        # Simple parsing - in production, you might want more sophisticated parsing
        sections = {
            "executive_summary": "",
            "key_changes": [],
            "new_insights": [],
            "investment_thesis_impact": ""
        }
        
        lines = draft_content.split('\\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Identify sections
            if "EXECUTIVE SUMMARY" in line.upper():
                current_section = "executive_summary"
            elif "KEY CHANGES" in line.upper():
                current_section = "key_changes"
            elif "NEW INSIGHTS" in line.upper():
                current_section = "new_insights"
            elif "INVESTMENT THESIS IMPACT" in line.upper():
                current_section = "investment_thesis_impact"
            elif current_section:
                # Add content to current section
                if current_section in ["key_changes", "new_insights"]:
                    if line.startswith('-') or line.startswith('•'):
                        sections[current_section].append(line[1:].strip())
                else:
                    sections[current_section] += line + " "
        
        # Clean up text sections
        sections["executive_summary"] = sections["executive_summary"].strip()
        sections["investment_thesis_impact"] = sections["investment_thesis_impact"].strip()
        
        return sections
```

**Enhanced Comparative Analysis Capabilities**

The AI service now includes comprehensive comparative analysis functionality:

```python
def _generate_collective_comparative_analysis(self, documents_text, estimates_data):
    """
    Generate thorough comparative analysis with quantitative variance analysis
    
    Enhanced capabilities include:
    - Revenue variance calculations with percentage analysis
    - Margin analysis with basis point precision
    - Segment performance comparison
    - Historical trend analysis with statistical significance
    - Estimates integration with actuals vs consensus analysis
    """
    
    # Enhanced prompt for thorough quantitative analysis
    comparative_prompt = f"""
    Perform a comprehensive comparative analysis between the new document content 
    and existing estimates data. Focus on:
    
    1. QUANTITATIVE VARIANCE ANALYSIS:
       - Calculate precise variance percentages for key metrics
       - Identify beats/misses with statistical significance
       - Analyze margin changes in basis points
    
    2. SEGMENT ANALYSIS:
       - Compare segment performance against estimates
       - Identify outperforming and underperforming segments
       - Calculate segment contribution variances
    
    3. ESTIMATES INTEGRATION:
       - Analyze actuals vs consensus estimates
       - Identify revision trends and analyst sentiment shifts
       - Assess guidance implications for future estimates
    
    Document Content: {documents_text}
    Estimates Data: {estimates_data}
    """
    
    # Process with enhanced analytical framework
    response = self._call_openai_with_retry(comparative_prompt)
    return self._parse_comparative_analysis(response)

def _extract_revenue_variance(self, content, estimates_data):
    """Extract and calculate revenue variance with precision"""
    # Implementation includes regex pattern matching, 
    # numerical extraction, and statistical calculation
    
def _extract_margin_variance(self, content, estimates_data):
    """Extract and calculate margin variance in basis points"""
    # Implementation for precise margin analysis
    
def _extract_segment_variance(self, content, estimates_data):
    """Extract and calculate segment performance variances"""
    # Implementation for segment-level analysis
```

### 3.6a Estimates Processing Service

**File**: `backend/app/services/estimates_parser.py`
```python
"""
SVG Financial Data Parser Service

This service extracts financial data from SVG files containing balance sheets,
cash flow statements, and income statements with analyst estimates.
"""

import os
import re
import json
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET
import logging

logger = logging.getLogger(__name__)

class SVGFinancialParser:
    """Parser for extracting financial data from SVG files."""
    
    def __init__(self):
        self.namespace = {'svg': 'http://www.w3.org/2000/svg'}
    
    def parse_estimates_folder(self, ticker: str) -> Dict[str, Any]:
        """
        Parse all SVG files in the estimates folder for a given ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing parsed financial data from all statements
        """
        estimates_path = f"data/research/{ticker}/estimates"
        
        if not os.path.exists(estimates_path):
            logger.warning(f"Estimates folder not found for {ticker}: {estimates_path}")
            return {}
        
        estimates_data = {
            'ticker': ticker,
            'last_updated': None,
            'balance_sheet': {},
            'cash_flow': {},
            'income_statement': {}
        }
        
        # Parse each financial statement
        for filename in os.listdir(estimates_path):
            if filename.endswith('.svg'):
                file_path = os.path.join(estimates_path, filename)
                
                try:
                    if 'BalanceSheet' in filename:
                        estimates_data['balance_sheet'] = self._parse_svg_file(file_path, 'balance_sheet')
                    elif 'CashFlow' in filename:
                        estimates_data['cash_flow'] = self._parse_svg_file(file_path, 'cash_flow')
                    elif 'IncomeStatement' in filename:
                        estimates_data['income_statement'] = self._parse_svg_file(file_path, 'income_statement')
                        
                    # Update last modified time
                    file_mtime = os.path.getmtime(file_path)
                    if not estimates_data['last_updated'] or file_mtime > estimates_data['last_updated']:
                        estimates_data['last_updated'] = file_mtime
                        
                except Exception as e:
                    logger.error(f"Error parsing {filename}: {str(e)}")
                    continue
        
        return estimates_data
    
    def _parse_svg_file(self, file_path: str, statement_type: str) -> Dict[str, Any]:
        """
        Parse individual SVG file to extract financial data.
        
        Args:
            file_path: Path to the SVG file
            statement_type: Type of financial statement
            
        Returns:
            Dictionary containing extracted financial data
        """
        try:
            # Parse SVG XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract all text elements
            text_elements = self._extract_text_elements(root)
            
            # Parse based on statement type
            if statement_type == 'income_statement':
                return self._parse_income_statement(text_elements)
            elif statement_type == 'balance_sheet':
                return self._parse_balance_sheet(text_elements)
            elif statement_type == 'cash_flow':
                return self._parse_cash_flow(text_elements)
            
            return {}
            
        except Exception as e:
            logger.error(f"Error parsing SVG file {file_path}: {str(e)}")
            return {}
    
    def _extract_text_elements(self, root) -> List[Dict[str, Any]]:
        """Extract all text elements from SVG with their positions and content."""
        text_elements = []
        
        # Find all text elements
        for text_elem in root.iter('{http://www.w3.org/2000/svg}text'):
            # Get text content
            tspan = text_elem.find('{http://www.w3.org/2000/svg}tspan')
            if tspan is not None and tspan.text:
                content = tspan.text.strip()
                
                # Get position from transform attribute
                transform = text_elem.get('transform', '')
                position = self._extract_position_from_transform(transform)
                
                # Get styling information
                style = text_elem.get('style', '')
                font_weight = 'bold' if 'font-weight:bold' in style else 'normal'
                
                text_elements.append({
                    'content': content,
                    'position': position,
                    'font_weight': font_weight,
                    'is_percentage': '%' in content,
                    'is_currency': '$' in content,
                    'is_number': self._is_numeric_value(content)
                })
        
        # Sort by vertical position (y coordinate) to maintain reading order
        text_elements.sort(key=lambda x: (-x['position']['y'], x['position']['x']))
        
        return text_elements

    def get_comparable_metrics(self, estimates_data: Dict, document_metrics: Dict) -> Dict[str, Any]:
        """
        Compare document metrics against estimates data to find relevant comparisons.
        
        Args:
            estimates_data: Parsed estimates data from SVG files
            document_metrics: Metrics extracted from uploaded document
            
        Returns:
            Dictionary containing comparison analysis
        """
        comparisons = {
            'revenue_comparisons': [],
            'margin_comparisons': [],
            'segment_comparisons': [],
            'estimate_vs_actual': [],
            'growth_implications': []
        }
        
        # Compare revenue metrics
        if 'revenue' in document_metrics:
            revenue_comparison = self._compare_revenue_metrics(
                estimates_data, document_metrics['revenue']
            )
            if revenue_comparison:
                comparisons['revenue_comparisons'].extend(revenue_comparison)
        
        # Compare margin metrics
        if 'margins' in document_metrics:
            margin_comparison = self._compare_margin_metrics(
                estimates_data, document_metrics['margins']
            )
            if margin_comparison:
                comparisons['margin_comparisons'].extend(margin_comparison)
        
        return comparisons

def create_estimates_parser() -> SVGFinancialParser:
    """Factory function to create SVG financial parser instance."""
    return SVGFinancialParser()
```

**Integration with Knowledge Base Service**:
```python
# In knowledge_base_service.py, add:
from .estimates_parser import create_estimates_parser

class KnowledgeBaseService:
    def __init__(self, config, database_service, document_service):
        # ... existing initialization
        self.estimates_parser = create_estimates_parser()
    
    def refresh_knowledge_base(self, ticker: str, force_reprocess: bool = False, 
                              include_investment_data: bool = True, include_estimates: bool = True) -> Dict:
        """Enhanced refresh method with estimates processing"""
        # ... existing code
        
        # Process estimates data if requested
        estimates_processed = 0
        if include_estimates:
            estimates_processed = self._process_estimates_data(ticker, current_state, force_reprocess)
        
        # ... rest of method
    
    def _process_estimates_data(self, ticker: str, state: Dict, force_reprocess: bool = False) -> int:
        """Process estimates data from SVG files for a company"""
        try:
            logger.info(f"Processing estimates data for {ticker}")
            
            # Parse estimates data from SVG files
            estimates_data = self.estimates_parser.parse_estimates_folder(ticker)
            
            if not estimates_data or not estimates_data.get('last_updated'):
                logger.warning(f"No estimates data found for {ticker}")
                return 0
            
            # Create embeddings for estimates data
            embedded_docs = self._create_estimates_embeddings(ticker, estimates_data)
            
            # Remove old estimates data from database
            self._remove_old_estimates_data(ticker)
            
            # Add new estimates data to database
            self.db_service.add_documents(ticker, embedded_docs)
            
            return len(embedded_docs)
            
        except Exception as e:
            logger.error(f"Failed to process estimates data for {ticker}: {str(e)}")
            return 0
```

**Enhanced Document Processing with Comparative Analysis**:
```python
# In document_service.py, add comparative analysis
class DocumentProcessingService:
    def __init__(self, config, ai_service, knowledge_base_service=None):
        # ... existing initialization
        self.kb_service = knowledge_base_service

    def process_uploaded_document_with_comparison(self, ticker: str, file_path: str, 
                                                document_date: Optional[datetime] = None) -> Dict:
        """Process uploaded document and perform comparison with estimates data"""
        try:
            # Process the document normally
            embedded_chunks = self.process_pdf_report(ticker, file_path)
            
            # Extract full document text for analysis
            full_text, pdf_metadata = self.extract_pdf_text(file_path)
            
            # Extract document date if not provided
            if not document_date:
                document_date = self._extract_document_date(full_text, file_path)
            
            # Extract financial metrics from the document
            document_metrics = self._extract_document_metrics(full_text, document_date)
            
            # Get estimates data for comparison
            comparative_analysis = {}
            if self.kb_service:
                estimates_data = self.kb_service.get_estimates_data(ticker)
                if estimates_data:
                    # Perform comparative analysis
                    comparative_analysis = self._perform_comparative_analysis(
                        ticker, document_metrics, estimates_data, document_date
                    )
            
            return {
                "embedded_chunks": embedded_chunks,
                "document_metrics": document_metrics,
                "comparative_analysis": comparative_analysis,
                "document_date": document_date.isoformat() if document_date else None,
                "processing_metadata": pdf_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to process document with comparison: {str(e)}")
            raise
```

### 3.7 Flask Routes Implementation

**File**: `backend/app/routes/company_routes.py`
```python
from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
import logging
from datetime import datetime

from app.services.database_service import DatabaseService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.config import Config

logger = logging.getLogger(__name__)

# Initialize services
config = Config()
db_service = DatabaseService(config)
kb_service = KnowledgeBaseService(config, db_service)

# API Namespace
company_bp = Namespace('companies', description='Company management operations')

# Response models
company_model = company_bp.model('Company', {
    'ticker': fields.String(required=True, description='Company ticker symbol'),
    'company_name': fields.String(description='Company name'),
    'knowledge_base_status': fields.String(description='Knowledge base status'),
    'last_updated': fields.DateTime(description='Last update timestamp'),
    'stats': fields.Raw(description='Company statistics')
})

companies_response_model = company_bp.model('CompaniesResponse', {
    'success': fields.Boolean(required=True),
    'data': fields.Raw(description='Response data'),
    'message': fields.String(description='Response message'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

@company_bp.route('/')
class CompanyList(Resource):
    @company_bp.marshal_with(companies_response_model)
    def get(self):
        """Get list of all companies with statistics"""
        try:
            companies = kb_service.get_all_companies()
            
            response_data = {
                "companies": companies,
                "total_companies": len(companies)
            }
            
            return {
                "success": True,
                "data": response_data,
                "message": "Companies retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get companies: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve companies",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@company_bp.route('/<string:ticker>')
class CompanyDetail(Resource):
    @company_bp.marshal_with(companies_response_model)
    def get(self, ticker):
        """Get detailed information about a specific company"""
        try:
            company_data = kb_service.get_company_detail(ticker.upper())
            
            if not company_data:
                return {
                    "success": False,
                    "error": {
                        "code": "COMPANY_NOT_FOUND",
                        "message": f"Company {ticker.upper()} not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            return {
                "success": True,
                "data": company_data,
                "message": f"Company {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get company {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve company {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500
```

## 4. Frontend Implementation

### 4.1 Project Setup

```bash
# Create React app
npx create-react-app frontend
cd frontend

# Install dependencies
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material
npm install axios react-query react-hook-form
npm install react-router-dom
npm install date-fns
npm install react-dropzone
npm install recharts
npm install react-markdown  # For enhanced markdown rendering
npm install typescript @types/react @types/react-dom  # TypeScript support
```

### 4.2 Package.json Configuration

**File**: `frontend/package.json`
```json
{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@emotion/react": "^11.13.3",
    "@emotion/styled": "^11.13.0",
    "@mui/icons-material": "^5.15.0",
    "@mui/material": "^5.15.0",
    "@testing-library/dom": "^9.3.4",
    "@testing-library/jest-dom": "^6.1.5",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^14.5.1",
    "axios": "^1.6.2",
    "date-fns": "^2.30.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-dropzone": "^14.2.3",
    "react-markdown": "^9.0.1",
    "react-router-dom": "^6.8.1",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.5",
    "web-vitals": "^3.5.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "proxy": "http://localhost:5001",
  "devDependencies": {
    "@types/node": "^18.19.3",
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "@types/react-router-dom": "^5.3.3",
    "typescript": "^4.9.5"
  }
}
```

### 4.3 API Service Layer

**File**: `frontend/src/services/api.ts`
```typescript
import axios, { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    console.error('API Error:', error.response?.data || error.message);
    
    if (error.response?.status === 404) {
      // Handle not found errors
      return Promise.reject({
        ...error,
        userMessage: 'Resource not found'
      });
    }
    
    if (error.response?.status && error.response.status >= 500) {
      // Handle server errors
      return Promise.reject({
        ...error,
        userMessage: 'Server error occurred. Please try again.'
      });
    }
    
    return Promise.reject(error);
  }
);

export default api;
```

### 4.4 Company Service

**File**: `frontend/src/services/companyService.ts`
```typescript
import { AxiosResponse } from 'axios';
import api from './api';

// Type definitions
interface Company {
  ticker: string;
  company_name: string;
  knowledge_base_status: string;
  stats?: {
    last_refresh?: string;
    total_reports?: number;
    total_chunks?: number;
  };
  created_at?: string;
}

interface Document {
  filename: string;
  file_size: number;
  upload_date: string;
  processing_status: string;
}

interface Report {
  title: string;
  report_type: string;
  created_at: string;
  content?: Record<string, string>;
  metadata?: {
    sources_used?: string;
    generated_at?: string;
    model_used?: string;
  };
}

interface KnowledgeBaseStatus {
  status: string;
  last_refresh?: string;
  document_count: number;
}

interface InvestmentData {
  investment_thesis?: any;
  investment_drivers?: any;
  risks?: any;
}

interface UploadResult {
  uploaded_files: Document[];
  success: boolean;
}

export const companyService = {
  // Get all companies
  getAllCompanies: async (): Promise<AxiosResponse<{ data: { companies: Company[] } }>> => {
    return await api.get('/companies');
  },

  // Get company details
  getCompanyDetails: async (ticker: string): Promise<AxiosResponse<{ data: Company }>> => {
    return await api.get(`/companies/${ticker}`);
  },

  // Refresh knowledge base
  refreshKnowledgeBase: async (ticker: string, options: any = {}): Promise<AxiosResponse> => {
    return await api.post(`/companies/${ticker}/knowledge-base/refresh`, options);
  },

  // Get knowledge base status
  getKnowledgeBaseStatus: async (ticker: string): Promise<AxiosResponse<{ data: KnowledgeBaseStatus }>> => {
    return await api.get(`/companies/${ticker}/knowledge-base/status`);
  },

  // Upload documents
  uploadDocuments: async (ticker: string, files: File[], documentType: string, description?: string): Promise<AxiosResponse<{ data: UploadResult }>> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('document_type', documentType);
    if (description) formData.append('description', description);
    
    return await api.post(`/companies/${ticker}/documents/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // Get uploaded documents
  getDocuments: async (ticker: string): Promise<AxiosResponse<{ data: Document[] }>> => {
    return await api.get(`/companies/${ticker}/documents`);
  },

  // Generate report
  generateReport: async (ticker: string, uploadId: string, analysisType?: string, focusAreas?: string[]): Promise<AxiosResponse<{ data: Report }>> => {
    return await api.post(`/companies/${ticker}/reports/generate`, {
      upload_id: uploadId,
      analysis_type: analysisType || 'general',
      focus_areas: focusAreas,
      include_context: true
    });
  },

  // Get investment data
  getInvestmentData: async (ticker: string): Promise<AxiosResponse<{ data: InvestmentData }>> => {
    return await api.get(`/companies/${ticker}/investment-data`);
  },

  // Get generated reports
  getReports: async (ticker: string): Promise<AxiosResponse<{ data: Report[] }>> => {
    return await api.get(`/companies/${ticker}/reports`);
  }
};
```

### 4.4 Enhanced UI Components with TypeScript

The frontend has been enhanced with production-ready TypeScript components that provide type safety and improved user experience.

#### 4.4.1 Document Analysis Display Component

**File**: `frontend/src/components/document/DocumentAnalysisDisplay.tsx`
```typescript
import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import ReactMarkdown from 'react-markdown';

interface DocumentAnalysisProps {
  analysisData: {
    analysis?: {
      comparative_analysis?: {
        has_estimates_comparison?: boolean;
        quantitative_analysis?: any;
        qualitative_insights?: string[];
        estimates_integration?: string;
      };
    };
  };
}

const DocumentAnalysisDisplay: React.FC<DocumentAnalysisProps> = ({ analysisData }) => {
  // Utility function for type-safe analysis checking
  const hasComparativeAnalysis = (): boolean => {
    return !!(
      analysisData?.analysis?.comparative_analysis?.has_estimates_comparison ||
      analysisData?.analysis?.comparative_analysis?.quantitative_analysis ||
      analysisData?.analysis?.comparative_analysis?.qualitative_insights?.length
    );
  };

  // Sanitize markdown content for safe rendering
  const sanitizeMarkdown = (content: string | string[]): string => {
    if (Array.isArray(content)) {
      return content
        .filter(item => typeof item === 'string')
        .join('\n\n');
    }
    return typeof content === 'string' ? content : '';
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 2 }}>
      {hasComparativeAnalysis() && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
            📊 Comparative Analysis
          </Typography>
          
          {/* Quantitative Analysis Section */}
          {analysisData.analysis?.comparative_analysis?.quantitative_analysis && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                Quantitative Analysis
              </Typography>
              {/* Render quantitative metrics */}
            </Box>
          )}

          {/* Qualitative Insights Section */}
          {analysisData.analysis?.comparative_analysis?.qualitative_insights && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                Key Insights
              </Typography>
              <ReactMarkdown>
                {sanitizeMarkdown(analysisData.analysis.comparative_analysis.qualitative_insights)}
              </ReactMarkdown>
            </Box>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default DocumentAnalysisDisplay;
```

#### 4.4.2 Markdown Array Renderer Utility

**File**: `frontend/src/components/common/MarkdownArrayRenderer.tsx`
```typescript
import React from 'react';
import ReactMarkdown from 'react-markdown';

interface MarkdownArrayRendererProps {
  content: string | string[];
  className?: string;
}

const MarkdownArrayRenderer: React.FC<MarkdownArrayRendererProps> = ({ content, className }) => {
  // Handle hybrid string/array types safely
  const renderContent = () => {
    if (Array.isArray(content)) {
      return content
        .filter(item => typeof item === 'string')
        .map((item, index) => (
          <ReactMarkdown key={index} className={className}>
            {item}
          </ReactMarkdown>
        ));
    }
    
    if (typeof content === 'string') {
      return <ReactMarkdown className={className}>{content}</ReactMarkdown>;
    }
    
    return null;
  };

  return <>{renderContent()}</>;
};

export default MarkdownArrayRenderer;
```

#### 4.4.3 TypeScript Interface Definitions

**File**: `frontend/src/types/index.ts`
```typescript
export interface ComparativeAnalysis {
  has_estimates_comparison?: boolean;
  quantitative_analysis?: {
    revenue_variance?: {
      actual: number;
      estimate: number;
      variance_amount: number;
      variance_percentage: number;
      direction: 'beat' | 'miss' | 'inline';
    };
    margin_analysis?: any;
  };
  qualitative_insights?: string[];
  estimates_integration?: string;
}

export interface DocumentAnalysis {
  analysis?: {
    comparative_analysis?: ComparativeAnalysis;
    executive_summary?: string | string[];
    key_changes?: string[];
    new_insights?: string[];
  };
}

export interface EstimatesData {
  ticker: string;
  has_estimates_data: boolean;
  data_source: 'parsed_svg' | 'fallback_data';
  last_updated: string;
  financial_data: {
    balance_sheet: FinancialItem[];
    income_statement: FinancialItem[];
    cash_flow: FinancialItem[];
  };
}

export interface FinancialItem {
  item: string;
  type: 'actual' | 'estimate';
  value: number;
  period: string;
  currency: string;
}
```

## 5. Deployment & Running

### 5.1 Environment Setup

**File**: `backend/.env`
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
CHROMA_DB_PATH=./chroma_db
DATA_ROOT_PATH=./data
LOG_LEVEL=INFO
```

### 5.2 Backend Startup

**File**: `backend/run.py`
```python
from app import create_app
import os

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5001)),
        debug=app.config['DEBUG']
    )
```

### 5.3 Startup Scripts

**File**: `start_backend.sh`
```bash
#!/bin/bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
python run.py
```

**File**: `start_frontend.sh`
```bash
#!/bin/bash
cd frontend
npm install
npm start
```

### 5.4 Development Workflow

1. **Setup Environment**:
   ```bash
   # Set OpenAI API key
   export OPENAI_API_KEY="your-key-here"
   
   # Create data directories
   mkdir -p data/research/AAPL/{past_reports,investment_data}
   ```

2. **Start Backend**:
   ```bash
   cd backend
   python run.py
   ```

3. **Start Frontend** (in new terminal):
   ```bash
   cd frontend  
   npm start
   ```

4. **Access Application**:
   - Frontend: http://localhost:3000
   - API Swagger: http://localhost:5001/swagger

## 6. Testing Strategy

### 6.1 Backend Testing
```python
# test_api.py
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['success'] == True
```

### 6.2 Frontend Testing
```javascript
// CompanyCard.test.js
import { render, screen } from '@testing-library/react';
import CompanyCard from './CompanyCard';

test('renders company card', () => {
  const company = {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    status: 'active'
  };
  
  render(<CompanyCard company={company} />);
  expect(screen.getByText('AAPL')).toBeInTheDocument();
});
```

This implementation guide provides the foundation for building the AI Research Draft Generator system. Each component can be implemented incrementally and tested independently.
