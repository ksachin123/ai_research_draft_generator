# AI Research Draft Generator - System Architecture

## 1. System Overview

The AI Research Draft Generator is a Gen AI-powered solution designed to help investment research analysts author research reports in reaction to new company updates. The system leverages existing research knowledge and current investment thesis to generate draft content highlighting changes and new insights.

## 2. High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   React UI      │◄──►│  Flask API      │◄──►│   Chroma DB     │
│   (Frontend)    │    │   (Backend)     │    │ (Vector Store)  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │                 │
                       │   OpenAI API    │
                       │   (GPT-4o-mini) │
                       │                 │
                       └─────────────────┘
```

## 3. Core Components

### 3.1 Frontend (React Application)
- **Purpose**: User interface for knowledge base management and report generation
- **Technology**: React 18 with TypeScript and Create React App
- **Key Features**:
  - Company dashboard with analytics and financial metrics
  - Knowledge base management interface
  - Document upload and processing status tracking
  - Financial estimates data visualization
  - Report generation and preview
  - Real-time processing status updates

### 3.2 Backend API (Flask Application)
- **Purpose**: REST API server handling business logic and data processing
- **Technology**: Python Flask with Flask-RESTX for Swagger documentation
- **Key Features**:
  - RESTful API endpoints with comprehensive documentation
  - Document processing pipeline with PDF and SVG support
  - Financial estimates processing and comparative analysis
  - Knowledge base management with incremental updates
  - AI-powered report generation with context awareness
  - Structured logging and error handling
  - Background task processing

### 3.3 Vector Database (Chroma)
- **Purpose**: Persistent storage for document embeddings and metadata
- **Technology**: ChromaDB (local deployment)
- **Key Features**:
  - Document embeddings storage with financial data priority weighting
  - Similarity search capabilities with metadata filtering
  - Persistent collections per company ticker
  - Financial estimates integration with embeddings

### 3.4 Enhanced Document Processing Pipeline
- **Purpose**: Extract, chunk, and embed documents for knowledge base
- **Technology**: PyPDF2, Custom SVG parsers, LangChain, OpenAI Embeddings
- **Key Features**:
  - PDF text extraction with enhanced processing
  - **SVG Financial Data Processing**: Balance sheets, cash flow, income statements, margin analysis
  - Intelligent text chunking with financial context awareness
  - Embedding generation with priority weighting
  - Incremental processing and duplicate detection
  - Financial estimates extraction and comparative analysis

### 3.5 Financial Data Processing Suite
- **Purpose**: Process and analyze SVG financial statements and estimates
- **Technology**: Custom SVG parsers, XML processing, financial data modeling
- **Key Features**:
  - **Balance Sheet Parser**: Assets, liabilities, equity analysis
  - **Cash Flow Parser**: Operating, investing, financing activities
  - **Income Statement Parser**: Revenue, segments, margins, earnings
  - **Margin Analysis Parser**: Product-specific margins and trends
  - **Current Quarter Estimates Extractor**: AI-ready estimates data
  - Comprehensive comparative analysis capabilities

### 3.6 AI Integration (OpenAI)
- **Purpose**: Generate embeddings and draft reports with financial context
- **Technology**: OpenAI API (GPT-4o-mini, text-embedding-ada-002)
- **Key Features**:
  - Text embeddings for similarity search with financial weighting
  - Enhanced report draft generation with quantitative analysis
  - Context-aware content creation with estimates integration
  - Comparative analysis with statistical precision
  - Investment thesis integration

## 4. Data Flow Architecture

### 4.1 Knowledge Base Creation Flow
```
PDF Files → PyPDF2 → Text Chunks → OpenAI Embeddings → Chroma Storage
JSON Data → Validation → Structured Storage → Chroma Metadata
SVG Financial Data → Enhanced Parsers → Financial Metrics → Priority Embeddings → Chroma Storage
```

### 4.2 Financial Data Processing Flow
```
SVG Files → Balance Sheet Parser → Structured Financial Data
         → Cash Flow Parser → Operating/Investing/Financing Metrics
         → Income Statement Parser → Revenue/Segments/Margins
         → Margin Analysis Parser → Product Margins/Trends
         → Current Quarter Extractor → AI-Ready Estimates → Context Integration
```

### 4.3 Enhanced Report Generation Flow
```
New Document → Text Extraction → Similarity Search → Context Retrieval → 
Financial Context → Estimates Integration → Comparative Analysis →
OpenAI Analysis → Quantitative Insights → Draft Generation → Response Formatting
```

### 4.4 Estimates Processing Flow
```
SVG Upload → Financial Parser Suite → Structured Data → Embeddings Generation →
Knowledge Base Integration → Comparative Analysis Engine → AI Context Enhancement
```

## 5. File System Structure

```
ai_research_draft_generator/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── database_service.py
│   │   │   ├── document_service.py
│   │   │   ├── knowledge_base_service.py
│   │   │   ├── estimates_parser.py
│   │   │   ├── enhanced_svg_parser.py
│   │   │   ├── enhanced_pdf_processor.py
│   │   │   └── current_quarter_estimates_extractor.py
│   │   ├── routes/
│   │   │   ├── company_routes.py
│   │   │   ├── document_routes.py
│   │   │   ├── estimates_routes.py
│   │   │   ├── health_routes.py
│   │   │   ├── knowledge_base_routes.py
│   │   │   └── report_routes.py
│   │   └── utils/
│   ├── standalone_enhanced_parser.py
│   ├── balance_sheet_parser.py
│   ├── cash_flow_parser.py
│   ├── income_statement_parser.py
│   ├── margin_analysis_parser.py
│   ├── current_quarter_estimates_extractor.py
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── KnowledgeBaseContent.tsx
│   │   │   ├── common/
│   │   │   ├── company/
│   │   │   ├── document/
│   │   │   └── report/
│   │   ├── pages/
│   │   │   ├── CompanyDetail.tsx
│   │   │   └── DocumentManagementPage.tsx
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── public/
├── data/
│   ├── research/
│   │   └── {TICKER}/
│   │       ├── past_reports/
│   │       ├── investment_data/
│   │       └── estimates/
│   └── uploads/
├── chroma_db/
└── docs/
```

## 6. Enhanced Financial Data Processing

### 6.1 SVG Financial Parser Suite
The system includes a comprehensive suite of financial data parsers:

- **Balance Sheet Parser** (`balance_sheet_parser.py`): Extracts assets, liabilities, and equity data
- **Cash Flow Parser** (`cash_flow_parser.py`): Processes operating, investing, and financing activities
- **Income Statement Parser** (`income_statement_parser.py`): Handles revenue, segments, and profitability metrics
- **Margin Analysis Parser** (`margin_analysis_parser.py`): Analyzes product-specific margins and trends

### 6.2 Enhanced Data Processing Architecture
```
SVG Files → Transform Matrix Parsing → Text Element Extraction → 
Period Detection → Metric Parsing → Data Structuring → JSON Output → 
Embeddings Generation → Knowledge Base Integration
```

### 6.3 Current Quarter Estimates Integration
- **Current Quarter Estimates Extractor** (`current_quarter_estimates_extractor.py`): Provides AI-ready estimates data
- Integrates with comparative analysis for enhanced report generation
- Supports target date filtering and quarter-specific data extraction

## 7. Data Storage Strategy

### 7.1 File System Storage
- **Location**: `data/research/{TICKER}/`
- **Structure**: 
  - `past_reports/`: PDF files of historical research
  - `investment_data/`: JSON files with current investment data
  - `estimates/`: SVG files with financial statements and analyst estimates
- **Upload Location**: `data/uploads/{TICKER}/`

### 7.2 Vector Database Collections
- **Collection per Company**: `company_{ticker}_reports`
- **Metadata Fields**: document_type, file_name, processed_date, chunk_index, financial_metrics
- **Content**: Text chunks with embeddings, financial data with priority weighting
- **Enhanced Metadata**: Estimates data with temporal information, financial periods, metric types

### 7.3 Processing State Management
- **Processed Files Tracking**: JSON file per company with file hashes
- **Incremental Updates**: Skip already processed PDFs and unchanged SVG files
- **Investment Data Refresh**: Always update with latest JSON data
- **Financial Estimates Tracking**: Monitor SVG file changes and reprocess when updated
- **Background Processing**: Concurrent processing support (max 3 simultaneous)

## 8. Security Considerations

### 8.1 API Security
- No authentication required (single-user system)
- Input validation and sanitization
- File upload restrictions (PDF, SVG only, max 5MB)
- Cross-origin resource sharing (CORS) configuration

### 8.2 Data Protection
- Local storage only (no cloud dependencies)
- OpenAI API key security and environment variable protection
- Sensitive data handling in logs with appropriate log levels
- Financial data encryption at rest in ChromaDB

## 9. Scalability & Performance

### 9.1 Design Constraints
- Maximum 10-15 companies supported
- PDF files up to 5MB each
- SVG files with complex financial data structures
- Local deployment with resource optimization

### 9.2 Performance Optimizations
- Chunked document processing with intelligent segmentation
- Incremental knowledge base updates with change detection
- Caching of embeddings and parsed financial data
- Async processing for large documents and SVG parsing
- Concurrent processing limits (max 3 simultaneous operations)
- Financial data caching and reuse strategies

### 9.3 Enhanced Processing Capabilities
- **SVG Parser Suite**: Optimized for complex financial data extraction
- **Priority Weighting**: Financial estimates receive higher priority in embeddings
- **Comparative Analysis**: Real-time variance calculations and statistical analysis
- **Memory Management**: Efficient handling of large financial datasets

## 9. Error Handling & Monitoring

### 9.1 Logging Strategy
- Structured JSON logging
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Request/response logging
- Processing pipeline logging

### 9.2 Error Recovery
- Graceful PDF processing failures
- OpenAI API error handling
- Database connection recovery
- User-friendly error messages

## 10. Technology Stack Summary

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Frontend | React | 18.x | User Interface |
| Backend | Flask | 2.3.x | REST API Server |
| API Docs | Flask-RESTX | 1.1.x | Swagger Documentation |
| Vector DB | ChromaDB | 0.4.x | Document Storage |
| PDF Processing | PyPDF2 | 3.0.x | PDF Text Extraction |
| AI Framework | LangChain | 0.0.x | RAG Pipeline |
| AI Model | GPT-4o-mini | - | Report Generation |
| Embeddings | text-embedding-ada-002 | - | Document Embeddings |

## 11. Development & Deployment

### 11.1 Development Environment
- Python 3.9+
- Node.js 18+
- Local ChromaDB instance
- OpenAI API key

### 11.2 Deployment Strategy
- Local development server
- Separate frontend/backend processes
- Swagger UI for API testing
- Environment-based configuration
