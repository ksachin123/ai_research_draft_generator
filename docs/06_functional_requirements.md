# AI Research Draft Generator - Functional Requirements Document

## 1. Project Overview

### 1.1 Purpose
The AI Research Draft Generator is a Gen AI-powered solution designed to assist investment research analysts in authoring research reports in reaction to new company updates. The system leverages existing research knowledge and current investment thesis to generate draft content highlighting changes and new insights.

### 1.2 Scope
The system encompasses:
- Knowledge base management for company research
- Document ingestion and processing pipeline
- AI-powered draft report generation
- React-based user interface for analyst workflow
- REST API architecture for system integration

### 1.3 Business Objectives
- **Efficiency**: Reduce time required to draft research updates
- **Quality**: Ensure comprehensive coverage of new vs. existing information
- **Accuracy**: Prevent hallucination by using only provided source material
- **Consistency**: Maintain consistent analysis framework across reports

## 2. User Personas & Roles

### 2.1 Primary User: Investment Research Analyst
**Profile**:
- Finance/investment professional with 3+ years experience
- Responsible for publishing equity research reports
- Covers 5-15 companies across specific sectors
- Technology-comfortable but not technical expert

**Goals**:
- Quickly identify what's new in company announcements
- Draft coherent analysis comparing new vs. existing information
- Maintain comprehensive knowledge base per company
- Reduce manual effort in report preparation

**Pain Points**:
- Time-consuming to cross-reference new information with past research
- Risk of missing important changes or updates
- Manual effort in organizing and structuring analysis
- Difficulty maintaining context across multiple reports and timeframes

### 2.2 Secondary User: Research Team Manager
**Profile**:
- Senior analyst or team lead overseeing research output
- Responsible for quality control and team productivity
- Manages research coverage and resource allocation

**Goals**:
- Monitor team productivity and research quality
- Ensure consistent research standards across analysts
- Track knowledge base completeness and currency
- Optimize research workflow efficiency

## 3. Functional Requirements

### 3.1 Knowledge Base Management

#### FR-001: Company Knowledge Base Creation
**Requirement**: The system shall create and maintain a knowledge base for each company identified by its stock ticker.

**Acceptance Criteria**:
- System creates separate knowledge base per company ticker
- Knowledge base persists across application restarts
- System supports minimum 10-15 companies simultaneously
- Each knowledge base tracks creation date and last update timestamp

**Priority**: Must Have

#### FR-002: PDF Research Report Ingestion
**Requirement**: The system shall ingest existing PDF research reports to build company knowledge base.

**Acceptance Criteria**:
- System processes PDF files from designated folder structure (`data/research/{TICKER}/past_reports/`)
- System extracts text content from PDF files using PyPDF2
- System chunks extracted text into meaningful segments
- System generates embeddings for text chunks using OpenAI
- System stores processed content in ChromaDB with metadata
- System handles PDF files up to 5MB in size
- System logs processing success/failure for each file

**Priority**: Must Have

#### FR-003: Investment Data Integration
**Requirement**: The system shall ingest and integrate structured investment data from JSON files.

**Acceptance Criteria**:
- System processes JSON files from `data/research/{TICKER}/investment_data/` folder
- System handles investment thesis, drivers, and risks data structures
- System extracts meaningful text from JSON structure for embedding generation
- System maintains structured metadata for investment data
- System marks latest investment data as current/active
- System supports updating investment data without losing historical context

**Priority**: Must Have

#### FR-004: Incremental Knowledge Base Updates
**Requirement**: The system shall support incremental updates to avoid reprocessing unchanged content.

**Acceptance Criteria**:
- System tracks processed files using file hashes
- System skips reprocessing of unchanged PDF files
- System always reprocesses investment data JSON files to capture latest changes
- System maintains processing state across application restarts
- System provides clear indication of what was processed vs. skipped
- System updates processing timestamps and statistics

**Priority**: Must Have

#### FR-005: Knowledge Base Refresh Trigger
**Requirement**: The system shall provide UI capability to trigger knowledge base refresh on demand.

**Acceptance Criteria**:
- UI provides "Refresh Knowledge Base" button per company
- System processes refresh request asynchronously
- System provides real-time progress indicators during processing
- System displays estimated completion time
- System handles multiple concurrent refresh requests (max 3)
- System provides detailed status updates and error handling

**Priority**: Must Have

### 3.2 Document Upload and Management

#### FR-006: New Document Upload
**Requirement**: The system shall allow users to upload new documents for analysis.

**Acceptance Criteria**:
- System provides file upload interface supporting PDF, TXT, and DOCX formats
- System enforces 5MB maximum file size limit
- System validates file format before processing
- System provides file upload progress indicators
- System generates unique upload ID for each document
- System stores uploaded documents securely with metadata
- System supports document type categorization (earnings_transcript, press_release, etc.)

**Priority**: Must Have

#### FR-007: Uploaded Document Processing
**Requirement**: The system shall process uploaded documents for analysis readiness.

**Acceptance Criteria**:
- System extracts text content from uploaded documents
- System chunks document text appropriately for analysis
- System generates embeddings for document content
- System stores processed document with temporary retention (30 days)
- System provides processing status updates to user
- System handles processing failures gracefully with clear error messages

**Priority**: Must Have

#### FR-008: Document Management Interface
**Requirement**: The system shall provide interface to manage uploaded documents.

**Acceptance Criteria**:
- UI displays list of uploaded documents per company
- UI shows upload date, file name, document type, and processing status
- UI provides document preview capability when possible
- UI allows deletion of uploaded documents
- UI filters documents by type and date range
- System maintains audit trail of document operations

**Priority**: Should Have

### 3.3 Report Generation

#### FR-009: Draft Report Generation
**Requirement**: The system shall generate research report drafts based on uploaded documents and existing knowledge base.

**Acceptance Criteria**:
- System performs similarity search against existing knowledge base
- System identifies most relevant historical research content
- System uses OpenAI GPT-4o-mini to generate structured analysis
- System focuses output on NEW information and CHANGES vs. existing research
- System provides structured output with key sections (summary, changes, insights, thesis impact)
- System cites sources for all generated content
- System prevents hallucination by using only provided source material
- System completes generation within 2-3 minutes for typical documents

**Priority**: Must Have

#### FR-010: Analysis Configuration
**Requirement**: The system shall allow users to configure analysis parameters for report generation.

**Acceptance Criteria**:
- UI provides selection of analysis type (earnings_update, press_release_analysis, etc.)
- UI allows specification of focus areas (revenue_guidance, margin_trends, new_products, etc.)
- System adjusts analysis prompts based on selected configuration
- System applies appropriate context filtering based on analysis type
- System provides preview of configuration before generation
- System saves analysis configurations for reuse

**Priority**: Should Have

#### FR-011: Report Preview and Export
**Requirement**: The system shall provide capability to preview and export generated reports.

**Acceptance Criteria**:
- UI displays generated report in structured, readable format
- UI highlights source citations and confidence levels
- UI provides side-by-side comparison with source documents
- System supports export to PDF format
- System supports export to text/markdown format
- System maintains report history per company
- UI allows editing of generated content before export

**Priority**: Should Have

### 3.4 System Management and Analytics

#### FR-012: Company Dashboard
**Requirement**: The system shall provide dashboard view of all companies and their status.

**Acceptance Criteria**:
- UI displays grid/list view of all companies with key statistics
- UI shows knowledge base status (active, processing, error) per company
- UI displays last update timestamp and document counts
- UI provides quick access to refresh and manage functions
- UI shows system-wide statistics and health indicators
- Dashboard updates automatically with latest information

**Priority**: Must Have

#### FR-013: Company Detail Analytics
**Requirement**: The system shall provide detailed analytics for individual companies.

**Acceptance Criteria**:
- UI displays comprehensive company information and statistics
- UI shows processed documents count and types
- UI displays knowledge base size and last refresh information
- UI shows recent activity log and processing history
- UI provides charts/graphs for document processing trends
- Analytics update in real-time during processing operations

**Priority**: Should Have

#### FR-014: System Health Monitoring
**Requirement**: The system shall provide health monitoring and status reporting.

**Acceptance Criteria**:
- System provides health check API endpoint
- System monitors ChromaDB connection status
- System monitors OpenAI API availability and usage
- System tracks file system accessibility and storage usage
- UI displays system health indicators and alerts
- System logs health metrics for troubleshooting

**Priority**: Must Have

## 4. Non-Functional Requirements

### 4.1 Performance Requirements

#### NFR-001: Response Time
- API endpoints respond within 2 seconds for standard operations
- Knowledge base refresh completes within 5 minutes for typical company (4 reports)
- Report generation completes within 3 minutes for standard documents
- UI loads and renders within 1 second on modern browsers

#### NFR-002: Throughput
- System supports concurrent access by single user (no multi-user requirement)
- System processes maximum 3 concurrent knowledge base refreshes
- System handles up to 100 API requests per minute
- System processes documents up to 5MB in size efficiently

#### NFR-003: Scalability
- System supports 10-15 companies simultaneously
- System handles up to 1000 document chunks per company
- ChromaDB performs efficiently with up to 15K total documents
- System maintains performance with 100MB total knowledge base size

### 4.2 Reliability Requirements

#### NFR-004: Availability
- System available 95% during business hours (8 AM - 8 PM local time)
- System recovers automatically from temporary failures
- System maintains data integrity during unexpected shutdowns
- System provides graceful degradation when dependencies unavailable

#### NFR-005: Data Integrity
- System prevents data loss during processing operations
- System maintains consistent state across application restarts
- System provides transaction-like behavior for knowledge base updates
- System validates data integrity after processing operations

### 4.3 Usability Requirements

#### NFR-006: User Interface
- UI follows modern design principles with Material-UI components
- UI provides clear visual feedback for all operations
- UI handles errors gracefully with actionable error messages
- UI supports standard browser functions (back button, bookmarks, etc.)

#### NFR-007: Learning Curve
- New users can complete basic operations within 15 minutes of training
- UI provides contextual help and tooltips for complex features
- System provides clear documentation and user guides
- Error messages provide specific guidance for resolution

### 4.4 Security Requirements

#### NFR-008: Data Security
- System stores all data locally (no cloud dependencies except OpenAI API)
- System protects OpenAI API key through environment variables
- System validates and sanitizes all user inputs
- System prevents unauthorized access to file system resources

#### NFR-009: API Security
- System validates all API requests for proper format and parameters
- System implements rate limiting to prevent abuse
- System logs all significant operations for audit purposes
- System handles file uploads securely with type and size validation

### 4.5 Maintainability Requirements

#### NFR-010: Code Quality
- Backend code follows Python PEP 8 standards
- Frontend code follows React best practices and ESLint rules
- System provides comprehensive logging for troubleshooting
- System includes inline documentation and comments

#### NFR-011: Monitoring
- System provides detailed logging of all operations
- System tracks performance metrics and processing statistics
- System alerts on error conditions and failures
- Logs include sufficient detail for troubleshooting without sensitive data

## 5. User Stories

### 5.1 Epic: Knowledge Base Management

#### US-001: Initial Company Setup
**As an** investment analyst  
**I want to** set up a knowledge base for a new company  
**So that** I can start tracking and analyzing their research history

**Acceptance Criteria**:
- I can place PDF reports in the correct folder structure
- I can place investment data JSON files in the correct location
- I can trigger initial knowledge base creation through the UI
- I can see progress as the system processes my documents
- I receive confirmation when setup is complete with statistics

#### US-002: Adding New Research
**As an** investment analyst  
**I want to** add new research reports to an existing company knowledge base  
**So that** the system stays current with my latest analysis

**Acceptance Criteria**:
- I can add new PDF files to the company's past_reports folder
- I can update investment data JSON files with latest information
- I can trigger knowledge base refresh through the UI
- The system only processes new/changed files to save time
- I can see what was processed vs. what was skipped

#### US-003: Monitoring Knowledge Base Health
**As an** investment analyst  
**I want to** monitor the health and currency of my company knowledge bases  
**So that** I can ensure they're up-to-date and complete

**Acceptance Criteria**:
- I can see last update date for each company knowledge base
- I can view statistics on number of reports and data points
- I can identify companies that need knowledge base updates
- I can see processing errors and take corrective action
- I can view processing history and logs

### 5.2 Epic: Document Analysis and Report Generation

#### US-004: Analyzing New Company Information
**As an** investment analyst  
**I want to** upload and analyze new company documents  
**So that** I can quickly understand what's new vs. my existing research

**Acceptance Criteria**:
- I can upload earnings transcripts, press releases, and other documents
- I can specify the type of document I'm uploading
- The system processes the document and shows progress
- I can see when processing is complete and successful
- I receive error messages if processing fails

#### US-005: Generating Draft Analysis
**As an** investment analyst  
**I want to** generate draft analysis of new information  
**So that** I can quickly create research updates

**Acceptance Criteria**:
- I can select a processed document for analysis
- I can specify the type of analysis I want (earnings update, etc.)
- I can select focus areas for the analysis
- The system generates structured draft content within 3 minutes
- The draft highlights only NEW and CHANGED information
- I can see source citations for all generated content

#### US-006: Reviewing and Refining Drafts
**As an** investment analyst  
**I want to** review and edit generated drafts  
**So that** I can ensure accuracy and add my professional judgment

**Acceptance Criteria**:
- I can preview the generated draft in a readable format
- I can see side-by-side comparison with source documents
- I can edit the draft content before saving
- I can export the draft to PDF or text format
- I can save drafts for future reference and editing

### 5.3 Epic: System Overview and Management

#### US-007: Company Portfolio Overview
**As an** investment analyst  
**I want to** see an overview of all my companies and their status  
**So that** I can prioritize my work and identify what needs attention

**Acceptance Criteria**:
- I can see a dashboard with all companies I cover
- Each company shows key statistics and last update information
- I can quickly identify which companies need knowledge base updates
- I can access detailed company information with one click
- I can perform bulk operations like refreshing multiple knowledge bases

#### US-008: Tracking Analysis History
**As an** investment analyst  
**I want to** track my analysis history per company  
**So that** I can reference past work and maintain consistency

**Acceptance Criteria**:
- I can see list of all reports I've generated per company
- I can view details of past reports including source documents
- I can search and filter reports by date and type
- I can re-export or reference past analysis
- I can see evolution of my analysis over time

## 6. System Constraints

### 6.1 Technical Constraints
- **Local Deployment**: System must run entirely on local infrastructure
- **Storage Limits**: System designed for 10-15 companies maximum
- **File Size Limits**: PDF files limited to 5MB each
- **Processing Power**: Single-threaded processing for document ingestion
- **OpenAI Dependency**: Requires active OpenAI API subscription

### 6.2 Operational Constraints
- **Single User**: No multi-user authentication or access control
- **Manual File Management**: Users must manually place files in correct folders
- **Network Dependency**: Requires internet connection for OpenAI API calls
- **Data Retention**: Uploaded documents retained for 30 days only

### 6.3 Business Constraints
- **Cost Management**: Must use cost-effective OpenAI model (GPT-4o-mini)
- **Data Privacy**: All research data must remain on local infrastructure
- **Compliance**: Must not violate any financial data handling regulations
- **Professional Use**: Designed for professional investment research use only

## 7. Success Criteria

### 7.1 Functional Success
- System successfully processes and maintains knowledge bases for 10+ companies
- System generates accurate, relevant draft analysis in under 3 minutes
- System correctly identifies new vs. existing information with 90% accuracy
- System operates reliably with <5% processing failure rate

### 7.2 User Adoption Success
- User can complete end-to-end workflow (upload → analyze → export) in under 10 minutes
- User reports 50%+ time savings compared to manual analysis
- User achieves proficiency with core features within 2 hours of training
- System generates actionable draft content requiring minimal manual editing

### 7.3 Technical Success
- System maintains 95% uptime during business hours
- Knowledge base refresh completes within 5 minutes for typical company
- API responses maintain <2 second average response time
- System handles planned data volumes without performance degradation
