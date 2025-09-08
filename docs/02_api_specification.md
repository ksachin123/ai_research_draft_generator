# AI Research Draft Generator - API Specification

## 1. API Overview

The AI Research Draft Generator exposes RESTful APIs for knowledge base management and report generation. All APIs return JSON responses and use standard HTTP status codes.

### 1.1 Base Configuration
- **Base URL**: `http://localhost:5001/api`
- **Content-Type**: `application/json`
- **Documentation**: `http://localhost:5001/swagger` (Swagger UI)

### 1.2 Standard Response Format
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2025-09-07T10:30:00Z"
}
```

### 1.3 Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid ticker format",
    "details": {}
  },
  "timestamp": "2025-09-07T10:30:00Z"
}
```

## 2. Company Management APIs

### 2.1 List All Companies
**Endpoint**: `GET /api/companies`

**Description**: Retrieve list of all companies in the knowledge base with basic statistics.

**Response**:
```json
{
  "success": true,
  "data": {
    "companies": [
      {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "knowledge_base_status": "active",
        "last_updated": "2025-09-07T10:30:00Z",
        "stats": {
          "total_reports": 4,
          "total_chunks": 156,
          "last_refresh": "2025-09-07T09:15:00Z"
        }
      }
    ],
    "total_companies": 1
  }
}
```

**Status Codes**:
- `200`: Success
- `500`: Server error

### 2.2 Get Company Details
**Endpoint**: `GET /api/companies/{ticker}`

**Description**: Get detailed information about a specific company.

**Path Parameters**:
- `ticker` (string): Company ticker symbol (e.g., "AAPL")

**Response**:
```json
{
  "success": true,
  "data": {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "knowledge_base_status": "active",
    "last_updated": "2025-09-07T10:30:00Z",
    "stats": {
      "total_reports": 4,
      "total_chunks": 156,
      "processed_files": [
        "APPLE_20250613_0902.pdf",
        "APPLE_20250709_0418.pdf"
      ],
      "investment_data_files": [
        "investmentthesis.json",
        "investmentdrivers.json",
        "risks.json"
      ]
    },
    "investment_summary": {
      "rating": "Overweight",
      "target_price": "240.00",
      "last_updated": "2025-09-07T10:30:00Z"
    }
  }
}
```

**Status Codes**:
- `200`: Success
- `404`: Company not found
- `500`: Server error

## 3. Knowledge Base Management APIs

### 3.1 Refresh Knowledge Base
**Endpoint**: `POST /api/companies/{ticker}/knowledge-base/refresh`

**Description**: Trigger knowledge base refresh for a company, processing new PDF reports and updating investment data.

**Path Parameters**:
- `ticker` (string): Company ticker symbol

**Request Body**:
```json
{
  "force_reprocess": false,
  "include_investment_data": true
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "job_id": "refresh_aapl_20250907_103000",
    "status": "processing",
    "estimated_duration": "2-5 minutes"
  }
}
```

**Status Codes**:
- `202`: Accepted (processing started)
- `400`: Invalid request
- `404`: Company data not found
- `500`: Server error

### 3.2 Get Knowledge Base Status
**Endpoint**: `GET /api/companies/{ticker}/knowledge-base/status`

**Description**: Get current status of knowledge base for a company.

**Path Parameters**:
- `ticker` (string): Company ticker symbol

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "active",
    "last_refresh": "2025-09-07T09:15:00Z",
    "processing_jobs": [
      {
        "job_id": "refresh_aapl_20250907_103000",
        "status": "completed",
        "started_at": "2025-09-07T10:30:00Z",
        "completed_at": "2025-09-07T10:33:00Z"
      }
    ],
    "stats": {
      "total_documents": 4,
      "total_chunks": 156,
      "new_files_processed": 0,
      "updated_files": 3
    }
  }
}
```

**Status Codes**:
- `200`: Success
- `404`: Company not found
- `500`: Server error

### 3.3 Get Investment Data
**Endpoint**: `GET /api/companies/{ticker}/investment-data`

**Description**: Retrieve current investment data for a company.

**Path Parameters**:
- `ticker` (string): Company ticker symbol

**Response**:
```json
{
  "success": true,
  "data": {
    "investment_thesis": {
      "content": "With the largest base of pent up iPhone demand ever...",
      "target_price": "240.00",
      "rating": "Overweight",
      "last_updated": "2025-09-07T10:30:00Z"
    },
    "investment_drivers": [
      "Positive iPhone build revisions / clearer signs of accelerating replacement cycles",
      "Services revenue growth reacceleration"
    ],
    "risks": {
      "upside": [
        "iPhone 17 outperforms expectations",
        "Apple Intelligence adoption surprises to the upside"
      ],
      "downside": [
        "Weak consumer spending limits iPhone upgrade rates",
        "Limited progress on AI features"
      ]
    }
  }
}
```

**Status Codes**:
- `200`: Success
- `404`: Company or data not found
- `500`: Server error

## 4. Document Management APIs

### 4.1 Upload New Document
**Endpoint**: `POST /api/companies/{ticker}/documents/upload`

**Description**: Upload a new document (earnings transcript, press release, etc.) for analysis.

**Path Parameters**:
- `ticker` (string): Company ticker symbol

**Request**: Multipart form data
- `file` (file): Document file (PDF, TXT, or DOCX)
- `document_type` (string): Type of document ("earnings_transcript", "press_release", "analyst_note", "other")
- `description` (string, optional): Description of the document

**Response**:
```json
{
  "success": true,
  "data": {
    "upload_id": "upload_aapl_20250907_103500",
    "file_name": "AAPL_Q3_2025_Earnings_Transcript.pdf",
    "file_size": 2048576,
    "document_type": "earnings_transcript",
    "status": "uploaded"
  }
}
```

**Status Codes**:
- `201`: Created
- `400`: Invalid file or request
- `413`: File too large (>5MB)
- `500`: Server error

### 4.2 List Uploaded Documents
**Endpoint**: `GET /api/companies/{ticker}/documents`

**Description**: List all uploaded documents for analysis.

**Path Parameters**:
- `ticker` (string): Company ticker symbol

**Query Parameters**:
- `document_type` (string, optional): Filter by document type
- `limit` (integer, optional): Number of results (default: 50)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response**:
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "upload_id": "upload_aapl_20250907_103500",
        "file_name": "AAPL_Q3_2025_Earnings_Transcript.pdf",
        "document_type": "earnings_transcript",
        "uploaded_at": "2025-09-07T10:35:00Z",
        "processed": true,
        "analysis_status": "completed"
      }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
  }
}
```

**Status Codes**:
- `200`: Success
- `404`: Company not found
- `500`: Server error

## 5. Report Generation APIs

### 5.1 Generate Draft Report
**Endpoint**: `POST /api/companies/{ticker}/reports/generate`

**Description**: Generate a draft research report based on uploaded document and existing knowledge base.

**Path Parameters**:
- `ticker` (string): Company ticker symbol

**Request Body**:
```json
{
  "upload_id": "upload_aapl_20250907_103500",
  "analysis_type": "earnings_update",
  "focus_areas": [
    "revenue_guidance",
    "margin_trends",
    "new_products"
  ],
  "include_context": true
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "report_id": "report_aapl_20250907_104000",
    "status": "generated",
    "analysis_type": "earnings_update",
    "generated_at": "2025-09-07T10:40:00Z",
    "content": {
      "executive_summary": "Apple's Q3 2025 results showed...",
      "key_changes": [
        {
          "category": "Revenue Guidance",
          "current": "Updated Q4 guidance to $92-95B vs prior $90-93B",
          "previous": "Q4 guidance of $90-93B",
          "impact": "positive",
          "confidence": "high"
        }
      ],
      "new_insights": [
        "Services revenue acceleration driven by App Store growth",
        "iPhone 16 pre-orders exceeding expectations"
      ],
      "risks_updates": {
        "new_risks": [],
        "mitigated_risks": ["Supply chain constraints have been resolved"]
      },
      "investment_thesis_impact": {
        "rating_change": "none",
        "target_price_change": "none",
        "key_drivers_affected": ["Services revenue growth reacceleration"]
      }
    },
    "sources": [
      {
        "type": "uploaded_document",
        "file_name": "AAPL_Q3_2025_Earnings_Transcript.pdf",
        "relevance_score": 0.95
      },
      {
        "type": "knowledge_base",
        "document": "APPLE_20250721_0552.pdf",
        "relevance_score": 0.87
      }
    ]
  }
}
```

**Status Codes**:
- `201`: Created
- `400`: Invalid request or missing document
- `404`: Company or upload not found
- `500`: Server error

### 5.2 Get Report Status
**Endpoint**: `GET /api/companies/{ticker}/reports/{report_id}`

**Description**: Get status and content of a generated report.

**Path Parameters**:
- `ticker` (string): Company ticker symbol
- `report_id` (string): Report identifier

**Response**: Same as Generate Draft Report response

**Status Codes**:
- `200`: Success
- `404`: Report not found
- `500`: Server error

### 5.3 List Generated Reports
**Endpoint**: `GET /api/companies/{ticker}/reports`

**Description**: List all generated reports for a company.

**Path Parameters**:
- `ticker` (string): Company ticker symbol

**Query Parameters**:
- `analysis_type` (string, optional): Filter by analysis type
- `limit` (integer, optional): Number of results (default: 20)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response**:
```json
{
  "success": true,
  "data": {
    "reports": [
      {
        "report_id": "report_aapl_20250907_104000",
        "analysis_type": "earnings_update",
        "generated_at": "2025-09-07T10:40:00Z",
        "source_document": "AAPL_Q3_2025_Earnings_Transcript.pdf",
        "status": "generated"
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

**Status Codes**:
- `200`: Success
- `404`: Company not found
- `500`: Server error

## 6. Financial Estimates APIs

### 6.1 Refresh Estimates Data
**Endpoint**: `POST /api/estimates/{ticker}/refresh`

**Description**: Refresh estimates data from SVG files for a specific company.

**Parameters**:
- `ticker` (path): Company ticker symbol (e.g., "AAPL")

**Request Body**:
```json
{
  "force_reprocess": false
}
```

**Response**:
```json
{
  "success": true,
  "ticker": "AAPL",
  "result": {
    "status": "completed",
    "reports_processed": 5,
    "investment_data_processed": 3,
    "estimates_processed": 12,
    "total_documents": 20
  },
  "message": "Successfully refreshed estimates data for AAPL"
}
```

**Status Codes**:
- `200`: Success
- `400`: Invalid request
- `404`: Ticker not found
- `500`: Server error

### 6.2 Get Estimates Data
**Endpoint**: `GET /api/estimates/{ticker}/data`

**Description**: Retrieve current estimates data for a company.

**Parameters**:
- `ticker` (path): Company ticker symbol (e.g., "AAPL")

**Response**:
```json
{
  "success": true,
  "ticker": "AAPL",
  "data": {
    "ticker": "AAPL",
    "last_updated": "2025-09-07T15:30:00Z",
    "financial_statements": {
      "income_statement": {
        "segment_data": {
          "iPhone": {
            "actuals": [
              {"value": "25.0%", "position": {"x": 451.97, "y": 546.7}},
              {"value": "26.0%", "position": {"x": 491.69, "y": 546.7}}
            ],
            "estimates": [
              {"value": "27.5%", "position": {"x": 571.15, "y": 546.7}}
            ]
          },
          "Mac": {
            "actuals": [
              {"value": "32.0%", "position": {"x": 173.9, "y": 537.58}}
            ],
            "estimates": [
              {"value": "30.0%", "position": {"x": 293.06, "y": 537.58}}
            ]
          }
        },
        "margins": {
          "gross_margin": {
            "actuals": [
              {"value": "36%", "position": {"x": 180.5, "y": 181.85}}
            ],
            "estimates": [
              {"value": "35%", "position": {"x": 498.29, "y": 181.85}}
            ]
          }
        },
        "quarterly_data": [],
        "estimates": {}
      },
      "balance_sheet": {
        "segment_data": {},
        "margins": {},
        "quarterly_data": [],
        "estimates": {}
      },
      "cash_flow": {
        "segment_data": {},
        "margins": {},
        "quarterly_data": [],
        "estimates": {}
      }
    }
  }
}
```

**Status Codes**:
- `200`: Success
- `404`: Estimates data not found
- `500`: Server error

### 6.3 Generate Comparative Analysis
**Endpoint**: `POST /api/estimates/{ticker}/compare`

**Description**: Generate comparative analysis between uploaded document and estimates data.

**Parameters**:
- `ticker` (path): Company ticker symbol (e.g., "AAPL")

**Request Body**:
```json
{
  "document_text": "Apple reported iPhone revenue of $43.8 billion for the quarter...",
  "document_date": "2025-07-31T00:00:00Z",
  "analysis_type": "comparative"
}
```

**Response**:
```json
{
  "success": true,
  "ticker": "AAPL",
  "analysis": {
    "executive_summary": "iPhone revenue of $43.8B exceeded estimates by 2.3%, driven by strong Services growth...",
    "estimates_vs_actuals": "Revenue beat consensus by $1.1B with particularly strong iPhone performance...",
    "segment_comparison": "iPhone segment outperformed with 8.2% YoY growth vs 5.5% estimated...",
    "margin_analysis": "Gross margin of 46.2% matched estimates, showing consistent profitability trends...",
    "investment_thesis_impact": "Strong iPhone performance validates premium pricing strategy and market position...",
    "risk_assessment_update": "Supply chain risks remain monitored; margin sustainability confirmed...",
    "actionable_insights": [
      "Monitor iPhone ASP trends in upcoming quarters",
      "Services growth trajectory supports recurring revenue thesis",
      "Margin expansion opportunities in emerging markets"
    ],
    "variance_highlights": [
      "Variance: 2.3%"
    ]
  },
  "comparative_data": {
    "revenue_comparison": [
      {
        "metric": "Total Revenue",
        "actual": "$43.8 billion",
        "variance_analysis": "Beat estimates by $1.1B (2.6%)",
        "significance": "high"
      }
    ],
    "margin_comparison": [
      {
        "metric": "Gross Margin",
        "actual": "46.2%",
        "estimates": {"actuals": [{"value": "45.8%"}]},
        "variance": "40 bps beat",
        "significance": "medium"
      }
    ],
    "segment_comparison": [
      {
        "segment": "iPhone",
        "actual": "$43.8 billion",
        "estimates": {"actuals": [{"value": "$42.7B"}]},
        "variance": "$1.1B beat",
        "significance": "high"
      }
    ],
    "investment_implications": [
      {
        "category": "Revenue Performance",
        "impact": "Positive",
        "description": "Strong iPhone performance validates premium positioning",
        "investment_thesis_impact": "Supports sustainable growth narrative"
      }
    ],
    "quarter_context": "Q3 2025"
  },
  "document_metrics": {
    "revenue": {
      "iphone_revenue_billion": {
        "value": 43800000000,
        "raw_text": "$43.8 billion"
      }
    },
    "margins": {},
    "segments": {
      "iPhone revenue": {
        "value": 43800000000,
        "raw_text": "$43.8 billion"
      }
    },
    "growth_rates": {},
    "key_figures": {},
    "document_quarter": "Q3 2025"
  },
  "context_documents_count": 10
}
```

**Status Codes**:
- `200`: Success
- `400`: Invalid request body
- `404`: Ticker not found
- `500`: Server error

### 6.4 Get Segment Estimates
**Endpoint**: `GET /api/estimates/{ticker}/segments`

**Description**: Retrieve segment-specific estimates data for a company.

**Parameters**:
- `ticker` (path): Company ticker symbol (e.g., "AAPL")

**Response**:
```json
{
  "success": true,
  "ticker": "AAPL",
  "segments": {
    "iPhone": {
      "income_statement": {
        "actuals": [
          {"value": "25.0%", "position": {"x": 451.97, "y": 546.7}}
        ],
        "estimates": [
          {"value": "27.5%", "position": {"x": 571.15, "y": 546.7}}
        ]
      }
    },
    "Mac": {
      "income_statement": {
        "actuals": [
          {"value": "32.0%", "position": {"x": 173.9, "y": 537.58}}
        ],
        "estimates": [
          {"value": "30.0%", "position": {"x": 293.06, "y": 537.58}}
        ]
      }
    },
    "Services": {
      "income_statement": {
        "actuals": [],
        "estimates": []
      }
    }
  }
}
```

**Status Codes**:
- `200`: Success
- `404`: Estimates data not found
- `500`: Server error

### 6.5 Get Available Tickers
**Endpoint**: `GET /api/estimates/available-tickers`

**Description**: Retrieve list of tickers that have estimates data available.

**Response**:
```json
{
  "success": true,
  "tickers": [
    {
      "ticker": "AAPL",
      "estimates_files": ["BalanceSheet.svg", "CashFlow.svg", "IncomeStatement.svg"],
      "last_updated": 1725716400.0
    },
    {
      "ticker": "MSFT", 
      "estimates_files": ["BalanceSheet.svg", "IncomeStatement.svg"],
      "last_updated": 1725630000.0
    }
  ],
  "count": 2
}
```

**Status Codes**:
- `200`: Success
- `500`: Server error

## 7. System Health APIs

### 7.1 Health Check
**Endpoint**: `GET /api/health`

**Description**: Check system health and dependencies.

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-09-07T10:30:00Z",
    "version": "1.0.0",
    "dependencies": {
      "chroma_db": "connected",
      "openai_api": "available",
      "file_system": "accessible"
    }
  }
}
```

**Status Codes**:
- `200`: Healthy
- `503`: Unhealthy

## 8. Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `FILE_TOO_LARGE` | 413 | Uploaded file exceeds 5MB limit |
| `UNSUPPORTED_FORMAT` | 400 | Unsupported file format |
| `COMPANY_NOT_FOUND` | 404 | Company ticker not found |
| `DOCUMENT_NOT_FOUND` | 404 | Document or upload not found |
| `PROCESSING_ERROR` | 500 | Error in document processing |
| `AI_SERVICE_ERROR` | 502 | OpenAI API error |
| `DATABASE_ERROR` | 500 | Chroma database error |
| `INSUFFICIENT_DATA` | 400 | Insufficient knowledge base data |

## 9. Rate Limits & Constraints

- **File Upload**: Max 5MB per file
- **Concurrent Processing**: Max 3 knowledge base refreshes
- **API Rate Limit**: 100 requests per minute per client
- **Document Retention**: Uploaded documents retained for 30 days
- **Report History**: Last 100 reports per company
