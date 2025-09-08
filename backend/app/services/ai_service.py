import openai
from typing import List, Dict, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_random_exponential

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, config):
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
    def generate_initial_analysis(self, new_document: str, context_documents: List[Dict], 
                                analysis_type: str = "general") -> Dict:
        """Generate initial analysis for document review (Stage 1)"""
        
        # Prepare context
        context = self._prepare_context(context_documents)
        
        # Create prompt for initial analysis
        prompt = self._create_initial_analysis_prompt(new_document, context, analysis_type)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert investment research analyst. Generate comprehensive analysis providing detailed insights and actionable investment intelligence. Focus on quantitative findings with specific financial metrics."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2500  # Increased for comprehensive analysis without truncation
            )
            
            analysis_content = response.choices[0].message.content
            
            # Parse structured response for initial analysis
            structured_analysis = self._parse_initial_analysis_response(analysis_content)
            
            logger.info(f"Generated initial analysis for {analysis_type}")
            return structured_analysis
            
        except Exception as e:
            logger.error(f"Failed to generate initial analysis: {str(e)}")
            raise

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def generate_report_draft(self, new_document: str, context_documents: List[Dict], 
                            analysis_type: str = "general", approved_analysis: Optional[Dict] = None) -> Dict:
        """Generate detailed research report draft (Stage 2)"""
        
        # Prepare context
        context = self._prepare_context(context_documents)
        
        # Create prompt for detailed report
        prompt = self._create_report_prompt(new_document, context, analysis_type, approved_analysis)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert investment research analyst. Generate comprehensive, detailed analysis expanding on approved initial findings."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2500  # Longer detailed report
            )
            
            draft_content = response.choices[0].message.content
            
            # Parse structured response
            structured_draft = self._parse_draft_response(draft_content)
            
            logger.info(f"Generated detailed report draft for {analysis_type} analysis")
            return structured_draft
            
        except Exception as e:
            logger.error(f"Failed to generate report draft: {str(e)}")
            raise
    
    def _prepare_context(self, context_documents: List[Dict]) -> str:
        """Prepare context from similar documents with priority for historical financial data"""
        context_parts = []
        
        # Separate historical financial data from general context
        financial_docs = []
        general_docs = []
        
        for doc in context_documents[:10]:  # Process more docs to separate types
            metadata = doc.get("metadata", {})
            if metadata.get("contains_analyst_estimates") or metadata.get("historical_financial_data"):
                financial_docs.append(doc)
            else:
                general_docs.append(doc)
        
        # Prioritize financial documents
        priority_docs = financial_docs[:3] + general_docs[:2]  # Top 3 financial + 2 general
        
        for doc in priority_docs:
            metadata = doc.get("metadata", {})
            document_text = doc.get("document", "")
            
            doc_type = metadata.get("document_type", "unknown")
            file_name = metadata.get("file_name", "unknown")
            report_date = metadata.get("report_date", "")
            
            # Create context header with date information
            header = f"[{doc_type.upper()} - {file_name}"
            if report_date:
                header += f" - Date: {report_date[:10]}"  # YYYY-MM-DD format
            if metadata.get("contains_analyst_estimates"):
                header += " - CONTAINS ANALYST ESTIMATES"
            header += "]"
            
            # Include longer excerpts for financial data
            excerpt_length = 800 if metadata.get("historical_financial_data") else 500
            context_parts.append(f"{header}\n{document_text[:excerpt_length]}...")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _create_initial_analysis_prompt(self, new_document: str, context: str, analysis_type: str) -> str:
        """Create prompt for initial analysis (Stage 1)"""
        
        base_prompt = f"""
You are performing PROFESSIONAL EQUITY RESEARCH ANALYSIS with enhanced focus on TABULAR FINANCIAL DATA. Compare a new financial document against existing research to identify key changes and investment implications.

IMPORTANT: The document contains structured financial tables and key metrics sections. Pay special attention to:
- Numerical data in table format (revenue, margins, cash flows)
- Period-over-period comparisons (Q/Q, Y/Y growth rates)
- Segment breakdowns (geographic, product categories)
- Financial ratios and margin analysis

EXISTING RESEARCH CONTEXT:
{context}

NEW DOCUMENT TO ANALYZE (with enhanced table extraction):
{new_document}

ANALYSIS TYPE: {analysis_type}

Provide a QUANTITATIVE and SPECIFIC analysis focusing on the extracted financial tables:

1. EXECUTIVE SUMMARY (Investment implications with specific metrics from tables)

2. FINANCIAL PERFORMANCE VS EXPECTATIONS:
- Revenue/EPS beats or misses (cite specific table values with $ amounts and %)
- Margin analysis using exact figures from financial statements
- Sequential and Y/Y growth rates from comparative periods
- Cash flow generation and balance sheet changes

3. BUSINESS SEGMENT DEEP-DIVE (using segment tables):
- Product/service revenue with specific dollar amounts and growth rates
- Geographic performance with regional breakdowns
- Margin expansion/contraction by segment with basis point changes
- Unit volume and pricing trends where available

4. KEY FINANCIAL RATIOS AND METRICS:
- Calculate relevant ratios from table data (ROE, margins, efficiency)
- Working capital changes and cash conversion
- Leverage ratios and debt service metrics
- Share count changes and dilution impact

5. STRATEGIC DEVELOPMENTS:
- Guidance updates with specific forward-looking metrics
- Capex/opex trends from cash flow statements
- Share buyback activity with dollar amounts and timing
- Dividend policy changes

6. INVESTMENT THESIS IMPACT:
- Quantitative price target implications using financial data
- Valuation metrics (P/E, EV/EBITDA) based on reported numbers
- Rating change drivers with specific financial justification
- Risk-adjusted return scenarios

7. FORWARD-LOOKING ANALYSIS:
- Implied growth rates from guidance vs. historical trends
- Margin trajectory analysis using multi-period data
- Cash flow projections based on working capital trends
- Competitive positioning using financial benchmarks

8. CONFIDENCE ASSESSMENT:
- High/Medium/Low confidence ratings for each major finding
- Data quality assessment and source reliability
- Key assumptions and their validity
- Areas requiring additional verification

9. REQUIRES ATTENTION:
- Critical items needing immediate analyst review
- Data inconsistencies or anomalies found
- Potential red flags or warning signals
- Areas where additional research is needed

RESPONSE FORMAT REQUIREMENTS:
Provide detailed, quantified analysis with specific dollar amounts, percentages, and financial ratios. Each section must be comprehensive and actionable. Use bullet points with specific metrics. Always provide concrete numbers from the financial statements rather than qualitative descriptions.

CRITICAL: Always cite specific numbers from the financial tables. Use exact dollar amounts, percentages, and growth rates. Reference table titles and page numbers where possible. Compare current period data to prior periods using the structured table data provided.
"""
        
        return base_prompt
    
    def _parse_initial_analysis_response(self, analysis_content: str) -> Dict:
        """Parse the initial analysis AI response into structured format"""
        
        sections = {
            "executive_summary": "",
            "key_changes": [],  # Frontend expects this field
            "new_insights": [],  # Frontend expects this field  
            "potential_thesis_impact": "",  # Frontend expects this field
            "confidence_assessment": "",
            "requires_attention": [],
            # Keep internal structure for comprehensive data
            "financial_performance": [],
            "business_segments": [],
            "strategic_developments": [],
            "forward_looking_insights": []
        }
        
        lines = analysis_content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Identify sections with more comprehensive matching
            line_upper = line.upper()
            if "EXECUTIVE SUMMARY" in line_upper:
                current_section = "executive_summary"
            elif "FINANCIAL PERFORMANCE" in line_upper or "VS EXPECTATIONS" in line_upper or "KEY FINANCIAL RATIOS" in line_upper:
                current_section = "financial_performance"
            elif "BUSINESS SEGMENT" in line_upper or "DEEP-DIVE" in line_upper:
                current_section = "business_segments"
            elif "STRATEGIC DEVELOPMENTS" in line_upper:
                current_section = "strategic_developments"
            elif "INVESTMENT THESIS IMPACT" in line_upper or "THESIS IMPACT" in line_upper:
                current_section = "potential_thesis_impact"  # Map to frontend field
            elif "FORWARD-LOOKING" in line_upper or "FORWARD LOOKING" in line_upper:
                current_section = "forward_looking_insights"
            elif "CONFIDENCE" in line_upper:
                current_section = "confidence_assessment"
            elif "REQUIRES ATTENTION" in line_upper or "CRITICAL ITEMS" in line_upper:
                current_section = "requires_attention"
            elif current_section:
                # Add content to current section
                if current_section in ["financial_performance", "business_segments", "strategic_developments", "forward_looking_insights", "requires_attention"]:
                    if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        # Clean bullet point and add to list
                        clean_line = line[1:].strip()
                        if clean_line:  # Only add non-empty lines
                            sections[current_section].append(clean_line)
                    elif line.startswith('**') and line.endswith('**'):
                        # Section headers within categories
                        sections[current_section].append(line)
                    elif current_section in sections and len(line) > 3:  # Avoid adding very short lines
                        # Add as continuation of previous bullet or new item
                        sections[current_section].append(line)
                else:
                    # For text sections (executive_summary, potential_thesis_impact, confidence_assessment)
                    if sections[current_section]:
                        sections[current_section] += " " + line
                    else:
                        sections[current_section] = line
        
        # Clean up text sections
        sections["executive_summary"] = sections["executive_summary"].strip()
        sections["potential_thesis_impact"] = sections["potential_thesis_impact"].strip()
        sections["confidence_assessment"] = sections["confidence_assessment"].strip()
        
        # Remove empty items from list sections
        for key in ["financial_performance", "business_segments", "strategic_developments", "forward_looking_insights", "requires_attention"]:
            sections[key] = [item.strip() for item in sections[key] if item.strip()]
        
        # Combine sections for frontend compatibility
        # key_changes = financial_performance + key strategic items
        sections["key_changes"] = []
        if sections["financial_performance"]:
            sections["key_changes"].extend(sections["financial_performance"][:3])  # Top 3 financial items
        if sections["strategic_developments"]:
            sections["key_changes"].extend(sections["strategic_developments"][:2])  # Top 2 strategic items
            
        # new_insights = business_segments + forward_looking + some strategic items
        sections["new_insights"] = []
        if sections["business_segments"]:
            sections["new_insights"].extend(sections["business_segments"][:3])
        if sections["forward_looking_insights"]:
            sections["new_insights"].extend(sections["forward_looking_insights"][:2])
        
        return sections

    def _create_report_prompt(self, new_document: str, context: str, analysis_type: str, approved_analysis: Optional[Dict] = None) -> str:
        """Create prompt for detailed report generation (Stage 2)"""
        
        approved_context = ""
        if approved_analysis:
            approved_context = f"""

APPROVED INITIAL ANALYSIS FOR EXPANSION:
Executive Summary: {approved_analysis.get('executive_summary', '')}
Key Changes: {', '.join(approved_analysis.get('key_changes', []))}
New Insights: {', '.join(approved_analysis.get('new_insights', []))}
Thesis Impact: {approved_analysis.get('potential_thesis_impact', '')}
"""
        
        base_prompt = f"""
You are generating a DETAILED RESEARCH REPORT based on approved initial analysis. Expand on the approved findings with comprehensive context and implications.

EXISTING RESEARCH CONTEXT:
{context}

NEW DOCUMENT TO ANALYZE:
{new_document}
{approved_context}

ANALYSIS TYPE: {analysis_type}

Please provide a comprehensive structured analysis with the following sections:

1. EXECUTIVE SUMMARY (3-4 sentences with investment implications)

2. DETAILED ANALYSIS OF CHANGES:
- Expand on identified changes with supporting evidence
- Quantify impact where possible
- Provide historical context and comparisons

3. COMPREHENSIVE NEW INSIGHTS:
- Deep dive into new information not previously covered
- Market impact assessment
- Competitive implications

4. INVESTMENT THESIS UPDATE:
- Detailed assessment of thesis impact
- Updated investment drivers analysis
- Risk assessment updates (upside/downside scenarios)
- Specific recommendations for investors

5. SOURCE CITATIONS AND CONFIDENCE:
- Reference specific data points and sources
- Indicate confidence levels for each major finding
- Highlight areas requiring further monitoring

Expand significantly on the approved initial analysis. Provide actionable investment insights with detailed supporting evidence.
"""
        
        return base_prompt
    
    def _parse_draft_response(self, draft_content: str) -> Dict:
        """Parse the AI response into structured format"""
        
        sections = {
            "executive_summary": "",
            "key_changes": [],
            "new_insights": [],
            "investment_thesis_impact": ""
        }
        
        lines = draft_content.split('\n')
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
