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
- **Technology**: React 18 with Create React App
- **Key Features**:
  - Company dashboard with analytics
  - Knowledge base management interface
  - Document upload and processing status
  - Report generation and preview

### 3.2 Backend API (Flask Application)
- **Purpose**: REST API server handling business logic and data processing
- **Technology**: Python Flask with Flask-RESTX for Swagger documentation
- **Key Features**:
  - RESTful API endpoints
  - Document processing pipeline
  - Knowledge base management
  - AI-powered report generation
  - Structured logging

### 3.3 Vector Database (Chroma)
- **Purpose**: Persistent storage for document embeddings and metadata
- **Technology**: ChromaDB (local deployment)
- **Key Features**:
  - Document embeddings storage
  - Similarity search capabilities
  - Metadata filtering
  - Persistent collections

### 3.4 Document Processing Pipeline
- **Purpose**: Extract, chunk, and embed documents for knowledge base
- **Technology**: PyPDF2, LangChain, OpenAI Embeddings
- **Key Features**:
  - PDF text extraction
  - Intelligent text chunking
  - Embedding generation
  - Duplicate detection

### 3.5 AI Integration (OpenAI)
- **Purpose**: Generate embeddings and draft reports
- **Technology**: OpenAI API (GPT-4o-mini, text-embedding-ada-002)
- **Key Features**:
  - Text embeddings for similarity search
  - Report draft generation
  - Context-aware content creation

## 4. Data Flow Architecture

### 4.1 Knowledge Base Creation Flow
```
PDF Files → PyPDF2 → Text Chunks → OpenAI Embeddings → Chroma Storage
JSON Data → Validation → Structured Storage → Chroma Metadata
```

### 4.2 Report Generation Flow
```
New Document → Text Extraction → Similarity Search → Context Retrieval → 
OpenAI Analysis → Draft Generation → Response Formatting
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
│   │   ├── routes/
│   │   └── utils/
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── package-lock.json
├── data/
│   └── research/
│       └── {TICKER}/
│           ├── past_reports/
│           └── investment_data/
├── docs/
└── chroma_db/
```

## 6. Data Storage Strategy

### 6.1 File System Storage
- **Location**: `data/research/{TICKER}/`
- **Structure**: 
  - `past_reports/`: PDF files of historical research
  - `investment_data/`: JSON files with current investment data

### 6.2 Vector Database Collections
- **Collection per Company**: `company_{ticker}_reports`
- **Metadata Fields**: document_type, file_name, processed_date, chunk_index
- **Content**: Text chunks with embeddings

### 6.3 Processing State Management
- **Processed Files Tracking**: JSON file per company
- **Incremental Updates**: Skip already processed PDFs
- **Investment Data Refresh**: Always update with latest JSON data

## 7. Security Considerations

### 7.1 API Security
- No authentication required (single-user system)
- Input validation and sanitization
- File upload restrictions (PDF only, max 5MB)

### 7.2 Data Protection
- Local storage only (no cloud dependencies)
- OpenAI API key security
- Sensitive data handling in logs

## 8. Scalability & Performance

### 8.1 Design Constraints
- Maximum 10-15 companies
- PDF files up to 5MB each
- Local deployment only

### 8.2 Performance Optimizations
- Chunked document processing
- Incremental knowledge base updates
- Caching of embeddings
- Async processing for large documents

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
