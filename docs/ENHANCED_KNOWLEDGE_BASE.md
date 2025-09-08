# Enhanced Knowledge Base Processing for Historical Financial Data

## Overview

The knowledge base processing has been significantly enhanced to better handle historical research reports containing analyst estimates, financial metrics, and tabular data. This ensures that when analyzing new documents, the AI has access to the most relevant and recent analyst views and financial baselines.

## Key Enhancements

### 1. Enhanced PDF Table Extraction (`enhanced_pdf_processor.py`)

**Applied to both new documents AND historical knowledge base reports**

- **Advanced Table Detection**: Uses `pdfplumber` instead of basic PyPDF2 for superior table extraction
- **Financial Table Classification**: Automatically identifies income statements, balance sheets, cash flows
- **Structured Data Preservation**: Maintains table formatting and relationships
- **Key Metrics Extraction**: Extracts specific financial ratios, growth rates, and analyst estimates

### 2. Historical Report Date Processing (`knowledge_base_service.py`)

**New Capabilities**:
- **Filename Date Parsing**: Extracts dates from common formats (YYYYMMDD, YYYY-MM-DD)
- **Chronological Processing**: Processes reports newest-first to prioritize recent analyst views  
- **Latest Report Flagging**: Marks the most recent report for each company
- **Age-Based Prioritization**: Assigns priority scores based on report recency

**Supported Date Formats**:
```
AAPL_20240721_analysis.pdf    → 2024-07-21
report_20240315.pdf           → 2024-03-15  
AAPL-2024-01-15-update.pdf   → 2024-01-15
```

### 3. Content Priority System

**Priority Factors**:
- **Recency Boost**: Reports from last 30/90/365 days get higher priority
- **Content Type Weighting**:
  - Target prices & analyst estimates: +0.3 priority
  - Financial statements & metrics: +0.2 priority  
  - Investment thesis & catalysts: +0.1 priority

**Special Metadata Flags**:
- `contains_analyst_estimates`: Target prices, EPS estimates, ratings
- `historical_financial_data`: Contains structured financial metrics
- `is_latest`: Most recent report for the company
- `content_priority`: Calculated priority score (0.0 - 1.0)

### 4. Enhanced Database Querying (`database_service.py`)

**New Method**: `query_historical_financial_data()`

**Query Strategy**:
1. **Priority Search**: First looks for recent analyst estimates and financial data
2. **General Search**: Gets broader similar content
3. **Smart Merging**: Combines results while prioritizing financial content
4. **Deduplication**: Removes duplicates while preserving priority order

### 5. Improved AI Context Preparation (`ai_service.py`)

**Context Enhancement**:
- **Financial Data Prioritization**: Top 3 financial docs + 2 general docs
- **Extended Excerpts**: Longer excerpts (800 chars) for financial content
- **Date-Aware Headers**: Includes report dates in context headers
- **Estimate Flagging**: Clearly marks content containing analyst estimates

**Example Context Header**:
```
[PAST_REPORT - AAPL_20240721_analysis.pdf - Date: 2024-07-21 - CONTAINS ANALYST ESTIMATES]
```

## Impact on Analysis Quality

### Before Enhancement
```
"iPhone sales increased" (generic)
"Services growth was strong" (vague)
"Margins improved" (no specifics)
```

### After Enhancement
```  
"iPhone revenue $44.6B (+13.5% Y/Y vs. our $42.1B estimate)" (specific vs. historical estimate)
"Services gross margin 75.6% vs. 74.0% in our July 2024 model" (vs. historical baseline)
"Operating margin 30.0% beat our 29.2% forecast from Q2 report" (vs. dated analyst view)
```

## Knowledge Base Refresh Workflow

1. **Scan Historical Reports**: Find all PDFs in `past_reports/` folder
2. **Extract Dates**: Parse dates from filenames using regex patterns  
3. **Sort by Recency**: Process newest reports first
4. **Enhanced Extraction**: Use `pdfplumber` for table-aware processing
5. **Metadata Enhancement**: Add priority scores, estimate flags, date context
6. **Database Storage**: Store with enhanced metadata for smart retrieval

## Financial Metrics Captured

From historical reports, the system now captures:

### Analyst Estimates
- Target prices and price ranges
- EPS estimates (quarterly/annual)
- Revenue forecasts by segment
- Margin expectations

### Financial Baselines  
- Historical performance metrics
- Year-over-year comparisons
- Seasonal patterns
- Competitive benchmarks

### Investment Views
- Buy/Hold/Sell ratings with dates
- Catalyst timelines
- Risk assessments  
- Valuation methodologies

This enhanced processing ensures that new document analysis can reference specific historical analyst views and financial baselines, resulting in more sophisticated and contextually aware investment research.
