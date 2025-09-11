# Enhanced GenAI Report Generation Implementation

## Overview

This document describes the enhanced GenAI implementation for report generation that uses the `_raw_ai_response` field from all uploaded documents within a batch to create comprehensive investment research reports with specific sections.

## Key Changes

### 1. New Enhanced Report Generation Method

**File:** `backend/app/services/ai_service.py`

Added `generate_enhanced_batch_report()` method that:
- Takes raw AI responses from all documents in a batch as context
- Uses analyst estimates when available
- Generates reports with the following sections:
  - **Title**: Concise, client-facing title (6–12 words)
  - **Key Takeaways**: 3–6 bullets with metrics and variances vs estimates
  - **Bottomline**: Short summary paragraph (≤200 words) 
  - **Synopsis**: 1–2 paragraphs describing key message for clients
  - **Narrative**: Detailed analysis with subsections

### 2. Section-Specific Prompts

Added `generate_section_specific_content()` method with tailored prompts for each section:

#### Title Prompt
- Task: Write concise H1 title (6–12 words) highlighting quarter's key angle

#### Key Takeaways Prompt  
- Include metric + variance vs estimate ($ and %)
- End each bullet with source tags like [src:10Q:stmt_rev]

#### Bottomline Prompt
- Write ≤200 words summarizing material beats/misses and thesis impact

#### Synopsis Prompt
- 1–2 short paragraphs (3–6 sentences) explaining what changed and why it matters

#### Narrative Prompt
- Professional sell-side analyst voice
- Includes subsections:
  - Financial Summary
  - Business Segments  
  - Guidance & Management Commentary
  - Margins & Costs
  - Cash Flow & Capital Allocation
  - Risks & Sensitivities
  - Investment Thesis Impact
- Ends with Action Items (3 bullets for analyst next steps)

### 3. Enhanced Report Parser

**Method:** `_parse_enhanced_report_response()`

Parses Markdown-formatted reports into structured sections:
- Extracts title from H1 heading
- Parses each H2 section (Key Takeaways, Bottomline, Synopsis, Narrative)
- Handles nested subsections within Narrative
- Preserves full content for display

### 4. Updated Batch Routes

**File:** `backend/app/routes/batch_routes.py`

Modified batch report generation endpoint to:
- Collect `_raw_ai_response` from all documents in batch
- Extract analyst estimates from first available document
- Use `generate_enhanced_batch_report()` instead of legacy method
- Return structured report with new sections

### 5. Frontend Interface Updates

**File:** `frontend/src/services/batchService.ts`

Updated `BatchReport` interface to include new sections:
- `title: string`
- `key_takeaways: string` 
- `bottomline: string`
- `synopsis: string`
- `narrative: string`
- Maintains backward compatibility with legacy fields

## System Message Requirements

The implementation uses this system message for professional output:

```
You are a professional equity research assistant trained to generate concise, factual, and investor-grade research updates.

Rules:
- Output must be in MARKDOWN format, not JSON.
- Each section must use Markdown headings (#, ##, ###).
- Every numeric claim must cite its source using [src:<id>] inline.
- When comparing vs analyst estimates, show both absolute ($) and % variances.
- Keep tone professional, precise, and suitable for institutional investors.
- Keep Bottomline ≤ 200 words.
```

## User Message Template

The main user prompt follows this structure:

```
CONTEXT:
{combined_raw_ai_responses}

ANALYST ESTIMATES:
{analyst_estimates}

NEW DOCUMENT (with extracted financial tables and transcript chunks):
Based on the context and analysis provided above.

TASK:
Write a Markdown-formatted research update with the following sections:
[detailed section requirements...]
```

## Data Flow

1. **Document Upload & Analysis**: Documents are uploaded and analyzed, generating `_raw_ai_response` for each
2. **Batch Creation**: Multiple documents are grouped into a batch  
3. **Enhanced Report Generation**: 
   - Collect all `_raw_ai_response` fields from batch documents
   - Extract analyst estimates from available documents
   - Combine as context for enhanced report generation
   - Generate report using section-specific prompts
4. **Report Parsing**: Parse Markdown output into structured sections
5. **Frontend Display**: Present structured report with new sections

## Testing

A test script `test_enhanced_report.py` has been created to verify:
- Data structure access from uploaded documents
- Raw AI response extraction
- Report parsing functionality
- Integration with existing codebase

## Benefits

1. **Context Aggregation**: Uses comprehensive analysis from all documents in batch
2. **Professional Format**: Generates investor-grade reports with proper structure
3. **Analyst Estimates Integration**: Incorporates variance analysis against estimates
4. **Flexible Architecture**: Section-specific prompts allow for targeted content generation
5. **Backward Compatibility**: Maintains existing interfaces while adding enhanced functionality

## Usage Example

```python
# In batch report generation
raw_ai_responses = [doc['analysis']['_raw_ai_response'] for doc in batch_documents]
analyst_estimates = get_analyst_estimates_from_batch(batch_documents)

report = ai_service.generate_enhanced_batch_report(
    raw_ai_responses=raw_ai_responses,
    analyst_estimates=analyst_estimates,
    ticker="AAPL",
    batch_info={"name": "Q3 2025 Earnings", "document_count": 3}
)

# Access structured sections
title = report['title']
key_takeaways = report['key_takeaways'] 
bottomline = report['bottomline']
synopsis = report['synopsis']
narrative = report['narrative']
```

## Implementation Status

✅ Enhanced report generation method  
✅ Section-specific prompts  
✅ Report parsing functionality  
✅ Batch routes integration  
✅ Frontend interface updates  
✅ Testing framework  

## Next Steps

1. Deploy and test with live backend server
2. Create batches with multiple documents
3. Generate enhanced reports and verify output quality
4. Gather user feedback on report structure and content
5. Iterate on prompts based on analyst requirements
