import PyPDF2
import hashlib
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
import re

from langchain.text_splitter import RecursiveCharacterTextSplitter
from .enhanced_pdf_processor import EnhancedPDFProcessor

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    def __init__(self, config, ai_service):
        self.config = config
        self.ai_service = ai_service
        self.enhanced_processor = EnhancedPDFProcessor()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
        )
    
    def extract_pdf_text(self, file_path: str) -> Tuple[str, Dict]:
        """Enhanced PDF text extraction with table processing"""
        try:
            # Use enhanced processor for better table extraction
            text, extracted_tables, metadata = self.enhanced_processor.extract_pdf_with_tables(file_path)
            
            # If enhanced extraction fails, fall back to basic extraction
            if not text:
                logger.warning("Enhanced extraction failed, falling back to basic PyPDF2")
                return self._basic_pdf_extraction(file_path)
            
            # Convert tables to structured text and append
            if extracted_tables:
                structured_tables = self.enhanced_processor.convert_tables_to_structured_text(extracted_tables)
                text += "\n\n=== EXTRACTED FINANCIAL TABLES ===\n" + structured_tables
                
                # Extract key financial metrics
                financial_metrics = self.enhanced_processor.extract_key_financial_metrics(extracted_tables)
                if financial_metrics:
                    metrics_text = self._format_financial_metrics(financial_metrics)
                    text += "\n\n=== KEY FINANCIAL METRICS ===\n" + metrics_text
                    
                # Add table metadata
                metadata["extracted_tables"] = len(extracted_tables)
                metadata["financial_tables"] = len([t for t in extracted_tables if t.table_type == 'financial'])
                metadata["table_confidence"] = sum(t.confidence_score for t in extracted_tables) / len(extracted_tables) if extracted_tables else 0
            
            logger.info(f"Enhanced extraction from {file_path}: {metadata}")
            return text, metadata
            
        except Exception as e:
            logger.error(f"Enhanced PDF extraction failed for {file_path}: {str(e)}")
            # Fall back to basic extraction
            return self._basic_pdf_extraction(file_path)
    
    def _basic_pdf_extraction(self, file_path: str) -> Tuple[str, Dict]:
        """Fallback basic PDF extraction using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                
                metadata = {
                    "total_pages": page_count,
                    "character_count": len(text),
                    "word_count": len(text.split()),
                    "extraction_method": "basic_pypdf2"
                }
                
                logger.info(f"Basic extraction from {file_path}: {page_count} pages, {len(text)} characters")
                return text, metadata
                
        except Exception as e:
            logger.error(f"Failed basic extraction from {file_path}: {str(e)}")
            raise
    
    def _format_financial_metrics(self, metrics: Dict) -> str:
        """Format financial metrics into readable text"""
        formatted_text = ""
        
        for category, data in metrics.items():
            if not data:
                continue
                
            formatted_text += f"\n{category.upper()} METRICS:\n"
            for metric_name, values in data.items():
                if values:
                    formatted_text += f"  {metric_name}: {', '.join(str(v) for v in values if v)}\n"
        
        return formatted_text
    
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
            if data_type == "investmentthesis" or "thesis" in data_type.lower():
                text = self._extract_investment_thesis_text(data)
            elif data_type == "investmentdrivers" or "drivers" in data_type.lower():
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
            if ("thesis" in data_type.lower() or data_type == "investmentthesis") and "rating" in data:
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
        clean_thesis = re.sub('<.*?>', '', thesis)
        
        parts = [f"Investment Thesis: {clean_thesis}"]
        
        if data.get("targetPrice"):
            parts.append(f"Target Price: ${data['targetPrice']}")
        if data.get("rating"):
            parts.append(f"Rating: {data['rating']}")
        
        return "\n".join(parts)
    
    def _extract_investment_drivers_text(self, data: Dict) -> str:
        """Extract readable text from investment drivers JSON"""
        drivers = data.get("investmentDrivers", "")
        # Remove HTML tags
        clean_drivers = re.sub('<.*?>', '', drivers)
        clean_drivers = re.sub('<li>', '• ', clean_drivers)
        
        return f"Investment Drivers:\n{clean_drivers}"
    
    def _extract_risks_text(self, data: Dict) -> str:
        """Extract readable text from risks JSON"""
        upside = data.get("risksToUpside", "")
        downside = data.get("riskToDownside", "")
        
        # Clean HTML tags
        clean_upside = re.sub('<.*?>', '', upside)
        clean_upside = re.sub('<li>', '• ', clean_upside)
        
        clean_downside = re.sub('<.*?>', '', downside)
        clean_downside = re.sub('<li>', '• ', clean_downside)
        
        parts = []
        if clean_upside:
            parts.append(f"Risks to Upside:\n{clean_upside}")
        if clean_downside:
            parts.append(f"Risks to Downside:\n{clean_downside}")
        
        return "\n\n".join(parts)
