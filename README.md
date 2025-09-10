# AI Research Draft Generator

A comprehensive Gen AI-powered investment research platform that helps analysts author research reports in reaction to company updates like earnings transcripts, press releases, and other financial documents.

## 🌟 Features

- **Knowledge Base Management**: Upload and process PDF documents for 10-15 companies with automated refresh capabilities
- **Advanced Document Analysis**: AI-powered analysis with thorough comparative analysis and quantitative variance detection
- **Estimates Processing**: Sophisticated SVG parsing for analyst estimates data with automated balance sheet, income statement, and cash flow analysis
- **Enhanced Comparative Analysis**: Deep quantitative comparison between new information and existing knowledge base with variance calculations
- **AI-Powered Report Generation**: Generate structured investment research reports using GPT-4o-mini with comprehensive analytical insights
- **Production-Ready UI**: TypeScript-safe React components with ReactMarkdown rendering and Material-UI design
- **Document Processing**: Automated PDF text extraction and chunking with enhanced content analysis
- **Vector Search**: ChromaDB-powered similarity search for relevant context retrieval with fallback data support
- **Interactive Dashboard**: Modern responsive interface with real-time data display and professional styling
- **Comprehensive API**: RESTful Flask-based API with Swagger documentation including estimates management endpoints

## 🏗️ Architecture

### Backend
- **Framework**: Flask 2.3.3 with Flask-RESTX for API documentation
- **Vector Database**: ChromaDB 0.4.15 (local deployment with processing state management)
- **Document Processing**: PyPDF2 3.0.1 for PDF text extraction with enhanced content analysis
- **Estimates Processing**: Custom SVG parser service for financial data extraction from analyst estimates
- **AI Integration**: OpenAI GPT-4o-mini with text-embedding-ada-002 for comparative analysis and report generation
- **Pipeline**: LangChain for RAG (Retrieval-Augmented Generation) with enhanced quantitative analysis
- **Data Services**: Comprehensive document analysis, knowledge base management, and estimates data processing

### Frontend
- **Framework**: React 18 with TypeScript support and strict compilation safety
- **UI Library**: Material-UI 7.3.2 with enhanced responsive design
- **HTTP Client**: Axios for API communication
- **Routing**: React Router for navigation
- **File Upload**: React Dropzone for drag-and-drop uploads

## 📁 Project Structure

```
ai_research_draft_generator/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── config.py            # Configuration management
│   │   ├── services/            # Core business logic
│   │   │   ├── ai_service.py           # Enhanced AI analysis with comparative capabilities
│   │   │   ├── database_service.py     # ChromaDB vector database operations
│   │   │   ├── document_service.py     # Document processing with quantitative analysis
│   │   │   ├── enhanced_pdf_processor.py # Advanced PDF content extraction
│   │   │   ├── estimates_parser.py     # SVG financial data parser service
│   │   │   └── knowledge_base_service.py # Knowledge management with fallback data
│   │   └── routes/              # API endpoints
│   │       ├── company_routes.py
│   │       ├── document_routes.py
│   │       ├── estimates_routes.py     # New estimates management endpoints
│   │       ├── knowledge_base_routes.py
│   │       ├── report_routes.py
│   │       └── health_routes.py
│   ├── requirements.txt
│   └── start.sh                 # Backend startup script
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── company/
│   │   │   │   └── CompanyCard.jsx
│   │   │   ├── document/
│   │   │   │   ├── DocumentUpload.jsx
│   │   │   │   ├── DocumentAnalysisDisplay.tsx  # Enhanced analysis display
│   │   │   │   └── CollectiveAnalysisDisplay.tsx # Comparative analysis UI
│   │   │   ├── report/
│   │   │   │   └── ReportGeneration.jsx
│   │   │   ├── common/
│   │   │   │   └── MarkdownArrayRenderer.tsx    # TypeScript-safe rendering
│   │   │   └── Dashboard.tsx
│   │   ├── pages/
│   │   │   └── CompanyDetail.jsx
│   │   └── services/
│   │       ├── api.js
│   │       └── companyService.js
│   ├── package.json
│   └── start.sh                 # Frontend startup script
└── data/
    ├── documents/               # Uploaded PDF files
    └── chromadb/               # Vector database storage
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ with pip
- Node.js 16+ with npm
- OpenAI API key

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai_research_draft_generator
   ```

2. **Set up environment variables**
   ```bash
   # Create .env file in backend directory
   echo "OPENAI_API_KEY=your_openai_api_key_here" > backend/.env
   echo "FLASK_ENV=development" >> backend/.env
   ```

### Backend Setup

1. **Start the backend server**
   ```bash
   cd backend
   ./start.sh
   ```
   
   The script will:
   - Create a Python virtual environment
   - Install dependencies from requirements.txt
   - Set up necessary directories
   - Start Flask development server on http://localhost:5001

2. **Access API Documentation**
   - Swagger UI: http://localhost:5001/swagger
   - Health Check: http://localhost:5001/api/health

### Frontend Setup

1. **Start the frontend development server**
   ```bash
   cd frontend
   ./start.sh
   ```
   
   The script will:
   - Install npm dependencies
   - Install additional required packages
   - Start React development server on http://localhost:3000

## 📚 API Endpoints

### Company Management
- `GET /api/v1/company/` - List all companies
- `POST /api/v1/company/` - Add new company
- `GET /api/v1/company/{ticker}` - Get company details
- `DELETE /api/v1/company/{ticker}` - Remove company

### Knowledge Base
- `POST /api/v1/knowledge-base/{ticker}/refresh` - Refresh company knowledge base
- `GET /api/v1/knowledge-base/{ticker}/stats` - Get knowledge base statistics

### Document Management
- `POST /api/v1/document/upload/{ticker}` - Upload PDF documents
- `GET /api/v1/document/{ticker}` - List company documents
- `DELETE /api/v1/document/{ticker}/{filename}` - Delete document

### Report Generation
- `POST /api/v1/report/generate/{ticker}` - Generate AI research report
- `GET /api/v1/report/{ticker}` - List generated reports

## 🎯 Usage Workflow

1. **Add Companies**: Use the dashboard to add companies you want to track
2. **Upload Documents**: Upload PDF reports, earnings transcripts, press releases
3. **Build Knowledge Base**: System automatically processes and indexes documents
4. **Generate Reports**: Create AI-powered research reports with customizable sections
5. **Review & Download**: Review generated content and download reports

## 🔧 Configuration

### Backend Configuration (`backend/app/config.py`)
```python
OPENAI_API_KEY = "your-api-key"
CHROMADB_PATH = "./data/chromadb"
UPLOAD_FOLDER = "./data/documents"
AI_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-ada-002"
```

### Frontend Configuration (`frontend/src/services/api.ts`)
```typescript
const API_BASE_URL = 'http://localhost:5001/api';
```

## 📊 Features in Detail

### Enhanced Document Processing
- **PDF Upload**: Drag-and-drop interface for PDF documents with progress tracking
- **Advanced Text Extraction**: PyPDF2-based extraction with enhanced content analysis and error handling
- **Intelligent Chunking**: Optimized text chunking for vector search with context preservation
- **Content Analysis**: Deep document analysis with quantitative variance detection

### Comparative Analysis Engine
- **Quantitative Analysis**: Precise variance calculations for financial metrics (revenue, margins, segments)
- **Historical Comparison**: Thorough comparison against existing knowledge base with statistical analysis
- **Estimates Integration**: Advanced SVG parsing for analyst estimates with balance sheet, income statement, and cash flow data
- **Change Detection**: Automated identification of significant changes and new information

### AI-Powered Insights
- **Enhanced Prompting**: Sophisticated prompts for thorough comparative analysis with estimates context
- **Fallback Data**: Robust estimates data fallback system for consistent analysis
- **Contextual Generation**: Context-aware report generation with comprehensive analytical framework
- **Duplicate Detection**: Hash-based duplicate document detection

### AI Report Generation
- **Structured Sections**: Executive Summary, Investment Thesis, Risk Assessment, etc.
- **Context-Aware**: Uses relevant document chunks for accurate analysis
- **Customizable**: Select specific report sections and focus areas
- **Multiple Formats**: Support for different report types (Initiation, Update, Earnings)

### User Interface
- **Responsive Design**: Works on desktop and mobile devices
- **Material Design**: Modern, intuitive interface with Material-UI
- **Real-time Updates**: Progress indicators for uploads and processing
- **Error Handling**: User-friendly error messages and retry mechanisms

## 🛠️ Development

### Adding New Features

1. **Backend**: Add new routes in `backend/app/routes/`
2. **Frontend**: Add new components in `frontend/src/components/`
3. **Services**: Extend business logic in `backend/app/services/`

### Testing

```bash
# Backend testing
cd backend
python -m pytest tests/

# Frontend testing
cd frontend
npm test
```

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions, please create an issue in the repository.
