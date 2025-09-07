# AI Research Draft Generator - Frontend UI Documentation

## 1. UI Overview

The React-based frontend provides an intuitive interface for investment analysts to manage company knowledge bases and generate research report drafts. The UI emphasizes functionality while maintaining clean, professional aesthetics suitable for financial analysis workflows.

## 2. Technology Stack

### 2.1 Core Technologies
- **React**: 18.x with functional components and hooks
- **Create React App**: Project scaffolding and build tools
- **React Router**: Client-side routing
- **Axios**: HTTP client for API communication
- **Material-UI (MUI)**: Component library for consistent design

### 2.2 Additional Libraries
- **React Hook Form**: Form management and validation
- **React Query**: Server state management and caching
- **Date-fns**: Date formatting and manipulation
- **React-PDF**: PDF preview capabilities
- **React-Dropzone**: File upload interface
- **Recharts**: Charts and analytics visualization

## 3. Application Structure

### 3.1 Directory Structure
```
src/
├── components/
│   ├── common/
│   │   ├── Header.jsx
│   │   ├── Navigation.jsx
│   │   ├── LoadingSpinner.jsx
│   │   └── ErrorBoundary.jsx
│   ├── company/
│   │   ├── CompanyCard.jsx
│   │   ├── CompanyStats.jsx
│   │   └── KnowledgeBaseStatus.jsx
│   ├── documents/
│   │   ├── DocumentUpload.jsx
│   │   ├── DocumentList.jsx
│   │   └── DocumentPreview.jsx
│   └── reports/
│       ├── ReportGenerator.jsx
│       ├── ReportPreview.jsx
│       └── ReportHistory.jsx
├── pages/
│   ├── Dashboard.jsx
│   ├── CompanyDetail.jsx
│   ├── DocumentUpload.jsx
│   └── ReportGeneration.jsx
├── services/
│   ├── api.js
│   ├── companyService.js
│   ├── documentService.js
│   └── reportService.js
├── hooks/
│   ├── useCompanies.js
│   ├── useDocuments.js
│   └── useReports.js
├── utils/
│   ├── formatting.js
│   ├── validation.js
│   └── constants.js
└── styles/
    ├── theme.js
    └── globals.css
```

## 4. Page Components

### 4.1 Dashboard Page (`/`)

**Purpose**: Main landing page showing overview of all companies and system statistics.

**Components**:
- System health indicator
- Company grid with stats cards
- Recent activity feed
- Quick action buttons

**Features**:
- Real-time statistics updates
- Filter companies by status
- Sort by last updated, name, etc.
- Quick access to refresh all knowledge bases

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Header Navigation                           │
├─────────────────────────────────────────────┤
│ System Status | Total Companies: 5 | ... │
├─────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│ │ AAPL    │ │ MSFT    │ │ GOOGL   │  ... │
│ │ Active  │ │ Active  │ │ Refresh │      │
│ │ 4 Rpts  │ │ 7 Rpts  │ │ 3 Rpts  │      │
│ └─────────┘ └─────────┘ └─────────┘      │
├─────────────────────────────────────────────┤
│ Recent Activity                             │
│ • AAPL knowledge base refreshed (2m ago)   │
│ • New report generated for MSFT (5m ago)   │
└─────────────────────────────────────────────┘
```

### 4.2 Company Detail Page (`/company/:ticker`)

**Purpose**: Detailed view of a specific company's knowledge base and analytics.

**Components**:
- Company header with key metrics
- Knowledge base statistics
- Investment data summary
- Document management interface
- Processing status display

**Features**:
- Refresh knowledge base
- View processed documents
- Upload new documents
- Generate reports
- Historical processing logs

**Layout**:
```
┌─────────────────────────────────────────────┐
│ ← Back | AAPL - Apple Inc.                 │
├─────────────────────────────────────────────┤
│ ┌─Investment Summary──┐ ┌─KB Statistics──┐ │
│ │ Rating: Overweight  │ │ Documents: 4   │ │
│ │ Target: $240       │ │ Chunks: 156    │ │
│ │ Updated: Sep 7     │ │ Updated: 9:15  │ │
│ └────────────────────┘ └───────────────────┘ │
├─────────────────────────────────────────────┤
│ [Refresh KB] [Upload Doc] [Generate Report]  │
├─────────────────────────────────────────────┤
│ Documents Tab | Reports Tab | Analytics Tab │
│ ┌─────────────────────────────────────────┐ │
│ │ Document list/upload interface          │ │
│ │ or generated reports                    │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 4.3 Document Upload Page (`/company/:ticker/upload`)

**Purpose**: Upload and manage documents for analysis.

**Components**:
- Drag-and-drop file upload
- Document type selector
- Upload progress indicator
- Recently uploaded documents list

**Features**:
- Multi-file upload support
- File type validation
- Upload progress tracking
- Document preview
- Metadata editing

### 4.4 Report Generation Page (`/company/:ticker/report`)

**Purpose**: Generate and preview research report drafts.

**Components**:
- Document selection interface
- Analysis options configuration
- Report generation status
- Report preview and editing
- Export options

**Features**:
- Select source document for analysis
- Configure analysis focus areas
- Real-time generation progress
- Side-by-side comparison with existing research
- Export to PDF/Word formats

## 5. Key UI Components

### 5.1 CompanyCard Component

**Purpose**: Display company information in grid/list format.

**Props**:
```javascript
{
  company: {
    ticker: string,
    name: string,
    status: 'active' | 'processing' | 'error',
    stats: {
      totalReports: number,
      lastUpdated: string,
      totalChunks: number
    }
  },
  onRefresh: function,
  onViewDetails: function
}
```

**Features**:
- Status indicators (green/yellow/red)
- Quick action buttons
- Loading states
- Error handling display

### 5.2 DocumentUpload Component

**Purpose**: Handle file uploads with drag-and-drop interface.

**Props**:
```javascript
{
  ticker: string,
  allowedTypes: ['pdf', 'txt', 'docx'],
  maxFileSize: 5242880, // 5MB
  onUploadComplete: function,
  onUploadError: function
}
```

**Features**:
- Drag-and-drop zone
- File validation
- Progress bars
- Multiple file support
- Error handling

### 5.3 KnowledgeBaseStatus Component

**Purpose**: Display knowledge base processing status and statistics.

**Props**:
```javascript
{
  ticker: string,
  status: 'active' | 'processing' | 'error',
  stats: {
    totalDocuments: number,
    totalChunks: number,
    lastRefresh: string,
    processingJobs: array
  },
  onRefresh: function
}
```

**Features**:
- Real-time status updates
- Processing progress indicators
- Refresh controls
- Statistics display

### 5.4 ReportGenerator Component

**Purpose**: Interface for generating research report drafts.

**Props**:
```javascript
{
  ticker: string,
  uploadedDocuments: array,
  onGenerateReport: function,
  onReportGenerated: function
}
```

**Features**:
- Document selection
- Analysis type configuration
- Focus area selection
- Generation progress tracking
- Error handling

## 6. User Workflows

### 6.1 New Company Setup Workflow

1. **Access Dashboard** → View existing companies
2. **Prepare Data** → Ensure PDF reports and JSON files are in correct folders
3. **Navigate to Company** → Go to `/company/TICKER`
4. **Refresh Knowledge Base** → Click "Refresh KB" button
5. **Monitor Progress** → Watch processing status
6. **Verify Completion** → Check statistics and document counts

### 6.2 Document Analysis Workflow

1. **Upload Document** → Navigate to upload page
2. **Select Document Type** → Choose from dropdown
3. **Upload File** → Drag-and-drop or browse
4. **Wait for Processing** → Monitor upload progress
5. **Generate Report** → Go to report generation
6. **Configure Analysis** → Select focus areas
7. **Review Draft** → Preview generated content
8. **Export/Save** → Download or save draft

### 6.3 Knowledge Base Management Workflow

1. **Review Company Status** → Check dashboard overview
2. **Identify Updates Needed** → Check last refresh dates
3. **Add New Documents** → Place in appropriate folders
4. **Trigger Refresh** → Use refresh buttons
5. **Monitor Processing** → Check processing logs
6. **Validate Results** → Review updated statistics

## 7. UI State Management

### 7.1 Global State (Context)
- User preferences
- Theme settings
- Error notifications
- Loading states

### 7.2 Component State (useState)
- Form inputs
- UI interactions
- Local loading states
- Modal visibility

### 7.3 Server State (React Query)
- API data caching
- Background refetching
- Optimistic updates
- Error handling

## 8. Responsive Design

### 8.1 Breakpoints
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

### 8.2 Responsive Behaviors
- **Dashboard**: Grid layout adapts from 3 columns to 1
- **Company Detail**: Tabs become collapsible accordion on mobile
- **Document Upload**: Drag zone resizes appropriately
- **Report Preview**: Side-by-side becomes stacked view

## 9. Error Handling & User Feedback

### 9.1 Error States
- **API Errors**: Toast notifications with retry options
- **Upload Errors**: Inline error messages with specific guidance
- **Processing Errors**: Status updates with troubleshooting tips
- **Network Errors**: Offline indicators with reconnection attempts

### 9.2 Loading States
- **Skeleton Screens**: For initial data loading
- **Progress Bars**: For file uploads and processing
- **Spinners**: For quick actions and API calls
- **Status Indicators**: For background operations

### 9.3 Success Feedback
- **Toast Notifications**: For completed actions
- **Status Updates**: For processing completion
- **Visual Indicators**: For successful uploads
- **Progress Tracking**: For multi-step workflows

## 10. Accessibility & Usability

### 10.1 Accessibility Features
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Support**: ARIA labels and roles
- **Color Contrast**: WCAG 2.1 AA compliance
- **Focus Management**: Clear focus indicators

### 10.2 Usability Enhancements
- **Tooltips**: Contextual help for complex features
- **Confirmation Dialogs**: For destructive actions
- **Auto-save**: For form inputs
- **Undo/Redo**: For content modifications

## 11. Performance Optimization

### 11.1 Code Splitting
- Route-based splitting for pages
- Component-based splitting for heavy components
- Library splitting for vendor code

### 11.2 Data Optimization
- React Query for efficient caching
- Pagination for large lists
- Debounced search inputs
- Lazy loading for images/PDFs

### 11.3 Rendering Optimization
- React.memo for expensive components
- useMemo/useCallback for heavy computations
- Virtual scrolling for large lists
- Image optimization for assets
