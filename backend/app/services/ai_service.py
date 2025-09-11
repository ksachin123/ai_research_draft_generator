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
        # Logging controls
        self._log_enabled = getattr(config, 'AI_API_LOGGING_ENABLED', True)
        self._log_prompts = getattr(config, 'AI_API_LOG_PROMPTS', False)
        self._log_responses = getattr(config, 'AI_API_LOG_RESPONSES', False)
        self._max_log_chars = getattr(config, 'AI_API_MAX_LOG_CHARS', 1200)

    # ---------------------- Internal Logging Helpers ---------------------- #
    def _truncate(self, text: str) -> str:
        if text is None:
            return ''
        if len(text) <= self._max_log_chars:
            return text
        return text[: self._max_log_chars] + f"... [truncated {len(text)-self._max_log_chars} chars]"

    def _log_api_call(self, operation: str, *, prompt: Optional[str] = None, response_preview: Optional[str] = None, extra: Optional[Dict] = None, error: Optional[Exception] = None):
        if not self._log_enabled:
            return
        payload = {
            "operation": operation,
            "model": self.model if operation != 'embedding' else self.embedding_model,
        }
        if extra:
            payload.update(extra)
        if error:
            payload['status'] = 'error'
            payload['error'] = str(error)
        else:
            payload['status'] = 'ok'
        if self._log_prompts and prompt:
            payload['prompt_preview'] = self._truncate(prompt)
        if self._log_responses and response_preview:
            payload['response_preview'] = self._truncate(response_preview)
        logger.info(f"AI_API_CALL {payload}")
    
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            self._log_api_call('embedding', prompt=text[:200] if self._log_prompts else None, extra={"text_length": len(text)})
            response = openai.Embedding.create(input=text, model=self.embedding_model)
            
            embedding = response['data'][0]['embedding']
            logger.debug(f"Generated embedding for text of length {len(text)}")
            self._log_api_call('embedding', response_preview=f"embedding_length={len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            self._log_api_call('embedding', error=e, extra={"text_length": len(text)})
            raise
    
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def generate_comparative_analysis(self, new_document: str, context_documents: List[Dict],
                                   comparative_data: Dict, analysis_type: str = "comparative", 
                                   analyst_estimates: Optional[str] = None) -> Dict:
        """Generate analysis with comparative insights against estimates data and raw analyst estimates"""
        
        # Prepare context including estimates data and raw analyst estimates
        context = self._prepare_context_with_estimates(context_documents, comparative_data, analyst_estimates)
        
        # Create enhanced prompt for comparative analysis
        prompt = self._create_comparative_analysis_prompt(new_document, context, comparative_data, analysis_type)
        
        logger.info(f"Generating comparative analysis with estimates data")
        
        try:
            self._log_api_call('chat.comparative_analysis', prompt=prompt)
            response = openai.ChatCompletion.create(model=self.model, messages=[
                {"role": "system", "content": "You are an expert investment research analyst specializing in comparative financial analysis. Generate comprehensive analysis comparing actual reported metrics against analyst estimates and historical data. Focus on variance analysis, investment implications, and impact to investment thesis. Provide specific quantitative insights and actionable intelligence."},
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=3000)
            
            analysis_content = response.choices[0].message.content
            
            # Parse structured response for comparative analysis
            structured_analysis = self._parse_comparative_analysis_response(analysis_content)
            
            # Add metadata
            structured_analysis["_generation_metadata"] = {
                "prompt_used": prompt,
                "model": self.model,
                "temperature": 0.3,
                "max_tokens": 3000,
                "analysis_type": analysis_type,
                "context_documents_count": len(context_documents),
                "has_estimates_comparison": bool(comparative_data.get("revenue_comparison") or 
                                               comparative_data.get("margin_comparison") or 
                                               comparative_data.get("segment_comparison")),
                "analyst_estimates_included": bool(analyst_estimates),
                "analyst_estimates_length": len(analyst_estimates) if analyst_estimates else 0
            }
            
            logger.info(f"Generated comparative analysis with {len(comparative_data.get('investment_implications', []))} implications")
            self._log_api_call('chat.comparative_analysis', response_preview=analysis_content)
            return structured_analysis
            
        except Exception as e:
            logger.error(f"Failed to generate comparative analysis: {str(e)}")
            self._log_api_call('chat.comparative_analysis', error=e, extra={"analysis_type": analysis_type})
            raise

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def generate_initial_analysis(self, new_document: str, context_documents: List[Dict], 
                                analysis_type: str = "general", analyst_estimates: Optional[str] = None) -> Dict:
        """Generate initial analysis for document review (Stage 1) with analyst estimates integration"""
        
        # Prepare context
        context = self._prepare_context(context_documents)
        
        # Create prompt for initial analysis with analyst estimates
        prompt = self._create_initial_analysis_prompt(new_document, context, analysis_type, analyst_estimates)
        
        try:
            self._log_api_call('chat.initial_analysis', prompt=prompt)
            response = openai.ChatCompletion.create(model=self.model, messages=[
                {"role": "system", "content": "You are an expert investment research analyst. Generate comprehensive analysis providing detailed insights and actionable investment intelligence. Focus on quantitative findings with specific financial metrics and compare against analyst estimates where available."},
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=3000)  # Increased token limit for enhanced analysis
            
            analysis_content = response.choices[0].message.content
            
            # Parse structured response for initial analysis
            structured_analysis = self._parse_initial_analysis_response(analysis_content)
            
            # Store the raw AI response content in the structured analysis
            structured_analysis["_raw_ai_response"] = analysis_content
            
            # Store structured analysis components for document content JSON
            structured_analysis["_document_content"] = {
                "analysis_sections": {
                    "executive_summary": structured_analysis.get("executive_summary", ""),
                    "analyst_estimates_comparison": structured_analysis.get("analyst_estimates_comparison", []),
                    "financial_performance": structured_analysis.get("financial_performance", []),
                    "business_segments": structured_analysis.get("business_segments", []),
                    "strategic_developments": structured_analysis.get("strategic_developments", []),
                    "forward_looking_insights": structured_analysis.get("forward_looking_insights", []),
                    "estimate_accuracy_assessment": structured_analysis.get("estimate_accuracy_assessment", []),
                    "key_changes": structured_analysis.get("key_changes", []),
                    "new_insights": structured_analysis.get("new_insights", []),
                    "potential_thesis_impact": structured_analysis.get("potential_thesis_impact", ""),
                    "analysis_generation_details": structured_analysis.get("analysis_generation_details", ""),
                    "confidence_assessment": structured_analysis.get("confidence_assessment", ""),
                    "requires_attention": structured_analysis.get("requires_attention", [])
                },
                "content_metadata": {
                    "analysis_type": analysis_type,
                    "has_analyst_estimates": bool(analyst_estimates),
                    "context_documents_used": len(context_documents),
                    "analysis_timestamp": response.get('created', None),
                    "model_used": self.model,
                    "content_version": "1.0"
                }
            }
            
            # Add prompt and generation metadata to the response
            structured_analysis["_generation_metadata"] = {
                "prompt_used": prompt,
                "model": self.model,
                "temperature": 0.3,
                "max_tokens": 3000,
                "analysis_type": analysis_type,
                "context_documents_count": len(context_documents),
                "analyst_estimates_included": bool(analyst_estimates),
                "analyst_estimates_length": len(analyst_estimates) if analyst_estimates else 0
            }
            
            logger.info(f"Generated initial analysis for {analysis_type} with structured content storage")
            self._log_api_call('chat.initial_analysis', response_preview=analysis_content)
            return structured_analysis
            
        except Exception as e:
            logger.error(f"Failed to generate initial analysis: {str(e)}")
            self._log_api_call('chat.initial_analysis', error=e, extra={"analysis_type": analysis_type})
            raise

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def generate_report_draft(self, new_document: str, context_documents: List[Dict], 
                            analysis_type: str = "general", analysis: Optional[Dict] = None) -> Dict:
        """Generate detailed research report draft (Stage 2)"""
        
        # Prepare context
        context = self._prepare_context(context_documents)
        
        # Create prompt for detailed report
        prompt = self._create_report_prompt(new_document, context, analysis_type, analysis)
        
        try:
            self._log_api_call('chat.report_draft', prompt=prompt)
            response = openai.ChatCompletion.create(model=self.model, messages=[
                {"role": "system", "content": "You are an expert investment research analyst. Generate comprehensive, detailed analysis based on the provided analysis findings."},
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=2500)
            
            draft_content = response.choices[0].message.content
            
            # Parse structured response
            structured_draft = self._parse_draft_response(draft_content)
            
            logger.info(f"Generated detailed report draft for {analysis_type} analysis")
            self._log_api_call('chat.report_draft', response_preview=draft_content)
            return structured_draft
            
        except Exception as e:
            logger.error(f"Failed to generate report draft: {str(e)}")
            self._log_api_call('chat.report_draft', error=e, extra={"analysis_type": analysis_type})
            raise
    
    def _prepare_context(self, context_documents: List[Dict]) -> str:
        """Prepare comprehensive context from similar documents with enhanced financial data priority"""
        context_parts = []
        
        # Separate document types for better organization
        financial_docs = []
        analyst_estimate_docs = []
        recent_reports = []
        general_docs = []
        
        for doc in context_documents[:15]:  # Process more docs for better context
            metadata = doc.get("metadata", {})
            if metadata.get("contains_analyst_estimates"):
                analyst_estimate_docs.append(doc)
            elif metadata.get("historical_financial_data"):
                financial_docs.append(doc)
            elif metadata.get("document_type") == "past_report" and metadata.get("report_date", "") >= "2024-01-01":
                recent_reports.append(doc)
            else:
                general_docs.append(doc)
        
        # Prioritize comprehensive context: Analyst estimates + Financial + Recent reports + General
        priority_docs = (analyst_estimate_docs[:3] + 
                        financial_docs[:3] + 
                        recent_reports[:4] + 
                        general_docs[:3])  # Total of up to 13 documents
        
        logger.info(f"Context composition: {len(analyst_estimate_docs)} analyst docs, {len(financial_docs)} financial docs, "
                   f"{len(recent_reports)} recent reports, {len(general_docs)} general docs")
        
        for doc in priority_docs:
            metadata = doc.get("metadata", {})
            document_text = doc.get("document", "")
            
            doc_type = metadata.get("document_type", "unknown")
            file_name = metadata.get("file_name", "unknown")
            report_date = metadata.get("report_date", "")
            
            # Create enhanced context header with more information
            header = f"[{doc_type.upper()} - {file_name}"
            if report_date:
                header += f" - Date: {report_date[:10]}"  # YYYY-MM-DD format
            if metadata.get("contains_analyst_estimates"):
                header += " - CONTAINS ANALYST ESTIMATES"
            if metadata.get("historical_financial_data"):
                header += " - FINANCIAL DATA"
            if metadata.get("is_latest"):
                header += " - LATEST REPORT"
            header += "]"
            
            # Include longer excerpts for better context - especially for financial data
            excerpt_length = 1000 if (metadata.get("historical_financial_data") or 
                                    metadata.get("contains_analyst_estimates")) else 600
            context_parts.append(f"{header}\n{document_text[:excerpt_length]}...")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _create_initial_analysis_prompt(self, new_document: str, context: str, analysis_type: str, analyst_estimates: Optional[str] = None) -> str:
        """Create enhanced prompt for initial analysis (Stage 1) with comprehensive context usage and analyst estimates"""
        
        # Prepare analyst estimates section if available
        estimates_section = ""
        if analyst_estimates:
            estimates_section = f"""

ANALYST ESTIMATES FOR COMPARISON:
{analyst_estimates}

CRITICAL: Use these analyst estimates as a benchmark for your analysis. Compare actual reported numbers against the estimates provided above. Calculate variances (beats/misses) and analyze the significance of these differences for investment thesis and company performance assessment.
"""
        
        base_prompt = f"""
You are performing PROFESSIONAL EQUITY RESEARCH ANALYSIS with enhanced focus on COMPREHENSIVE HISTORICAL CONTEXT, ANALYST ESTIMATES COMPARISON, and TABULAR FINANCIAL DATA. Compare a new financial document against extensive existing research and analyst estimates to identify key changes, variances, and investment implications.

IMPORTANT: You have access to comprehensive historical context including analyst estimates, financial data, and recent reports. Pay special attention to:
- Numerical data in table format (revenue, margins, cash flows)
- Period-over-period comparisons (Q/Q, Y/Y growth rates)
- Segment breakdowns (geographic, product categories)
- Financial ratios and margin analysis
- Historical analyst estimates and how current data compares
- BEATS/MISSES vs analyst estimates with quantified variances

COMPREHENSIVE EXISTING RESEARCH CONTEXT:
{context}{estimates_section}

NEW DOCUMENT TO ANALYZE (with enhanced table extraction):
{new_document}

ANALYSIS TYPE: {analysis_type}

Provide a QUANTITATIVE and SPECIFIC analysis focusing on extracted financial tables, historical context, and ANALYST ESTIMATES COMPARISON:

1. EXECUTIVE SUMMARY (Investment implications with specific metrics from tables and estimate variances)

2. ANALYST ESTIMATES VS ACTUALS COMPARISON:
- Revenue/EPS beats or misses with specific dollar amounts, percentages, and variance analysis
- Compare each key metric against provided analyst estimates
- Quantify the significance of beats/misses (magnitude and percentage variance)
- Assess market expectations vs actual performance
- Identify which estimates were most/least accurate

3. FINANCIAL PERFORMANCE ANALYSIS:
- Detailed variance analysis using exact figures from financial statements vs estimates
- Margin analysis comparing actual margins to estimated margins
- Sequential and Y/Y growth rates vs estimated growth expectations
- Cash flow generation vs estimated cash flow metrics
- Balance sheet changes vs analyst projections where available

4. BUSINESS SEGMENT DEEP-DIVE WITH ESTIMATES COMPARISON:
- Product/service revenue vs segment estimates with specific variance analysis
- Geographic performance vs regional estimates and expectations
- Margin expansion/contraction by segment vs estimated segment margins
- Unit volume and pricing trends vs analyst volume/pricing assumptions
- Segment growth rates vs estimated segment growth expectations

5. KEY FINANCIAL RATIOS AND METRICS VS ESTIMATES:
- Calculate relevant ratios from table data vs estimated ratios
- Working capital changes vs estimated working capital requirements
- Leverage ratios vs estimated debt levels and structure
- Share count changes vs estimated share count assumptions
- Profitability metrics vs estimated profitability targets

6. STRATEGIC DEVELOPMENTS AND ESTIMATE IMPACT:
- Guidance updates vs previous analyst estimates and consensus
- How strategic initiatives compare to analyst assumptions
- Capex/opex trends vs estimated investment levels
- Share buyback activity vs estimated capital return programs
- Management commentary vs analyst expectations and assumptions

7. INVESTMENT THESIS IMPACT FROM ESTIMATE VARIANCES:
- How beats/misses impact investment thesis and valuation models
- Price target implications based on estimate variances
- Rating change drivers with specific variance justification
- Risk-adjusted return scenarios based on estimate performance
- Consensus estimate revision implications

8. FORWARD-LOOKING ANALYSIS WITH ESTIMATE CONTEXT:
- Updated guidance vs analyst forward estimates
- How current performance affects future estimate accuracy
- Margin trajectory analysis vs estimated margin expansion/contraction
- Cash flow projections vs analyst cash flow models
- Competitive positioning based on estimate performance vs peers

9. ESTIMATE ACCURACY AND RELIABILITY ASSESSMENT:
- Which analyst estimates were most accurate and why
- Systematic biases in estimates (consistently high/low)
- Quality of analyst models based on actual vs estimated performance
- Reliability of forward guidance vs historical estimate accuracy
- Market efficiency assessment based on estimate vs actual variances

10. ANALYSIS GENERATION DETAILS:
- Explain HOW analyst estimates were used in this analysis
- Detail which estimate variances were most significant for conclusions
- Specify confidence levels based on estimate accuracy and historical context
- Note any limitations in estimate data that affected analysis quality
- Explain how estimate comparison enhanced traditional analysis

11. CONFIDENCE ASSESSMENT:
- High/Medium/Low confidence ratings for each major finding
- Data quality assessment including estimate reliability
- Key assumptions validity vs actual performance
- Areas requiring additional verification based on estimate variances

12. REQUIRES ATTENTION:
- Critical estimate misses or beats requiring immediate review
- Significant variances that may indicate model/thesis changes needed
- Red flags identified through estimate comparison analysis
- Areas where estimate methodology may need adjustment

RESPONSE FORMAT REQUIREMENTS:
Provide detailed, quantified analysis with specific dollar amounts, percentages, variance calculations, and financial ratios. Each section must be comprehensive and actionable. Use bullet points with specific metrics. Always provide concrete numbers from the financial statements compared against specific analyst estimates with calculated variances.

CRITICAL ESTIMATE COMPARISON: In every relevant section, explicitly compare actual results to analyst estimates with specific variance calculations (e.g., "Revenue of $X beat estimates of $Y by Z% or $A"). Assess the investment significance of each major variance and what it indicates about company performance, analyst model accuracy, and market expectations.

CRITICAL CONTEXT USAGE: Reference how historical context documents and analyst estimates informed your analysis. Mention specific estimate sources, variance patterns, and how this comparison enhanced the investment insights.

CRITICAL: Always cite specific numbers from financial tables AND compare them to specific analyst estimates. Calculate and report variance percentages. Reference estimate sources and assess the reliability and significance of each major beat/miss for investment decision-making.
"""
        
        return base_prompt
    
    def _parse_initial_analysis_response(self, analysis_content: str) -> Dict:
        """Parse the enhanced initial analysis AI response into structured format with analyst estimates support"""
        
        sections = {
            "executive_summary": "",
            "key_changes": [],  # Frontend expects this field
            "new_insights": [],  # Frontend expects this field  
            "potential_thesis_impact": "",  # Frontend expects this field
            "analysis_generation_details": "",  # New section for context explanation
            "confidence_assessment": "",
            "requires_attention": [],
            # Keep internal structure for comprehensive data
            "analyst_estimates_comparison": [],  # New section for estimate analysis
            "financial_performance": [],
            "business_segments": [],
            "strategic_developments": [],
            "forward_looking_insights": [],
            "estimate_accuracy_assessment": []  # New section for estimate reliability
        }
        
        lines = analysis_content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Identify sections with enhanced matching for new sections
            line_upper = line.upper()
            if "EXECUTIVE SUMMARY" in line_upper:
                current_section = "executive_summary"
            elif "ANALYST ESTIMATES VS ACTUALS" in line_upper or "ESTIMATES COMPARISON" in line_upper:
                current_section = "analyst_estimates_comparison"
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
            elif "ESTIMATE ACCURACY" in line_upper or "RELIABILITY ASSESSMENT" in line_upper:
                current_section = "estimate_accuracy_assessment"
            elif "ANALYSIS GENERATION DETAILS" in line_upper:
                current_section = "analysis_generation_details"  # New section
            elif "CONFIDENCE" in line_upper:
                current_section = "confidence_assessment"
            elif "REQUIRES ATTENTION" in line_upper or "CRITICAL ITEMS" in line_upper:
                current_section = "requires_attention"
            elif current_section:
                # Add content to current section
                if current_section in ["analyst_estimates_comparison", "financial_performance", "business_segments", 
                                     "strategic_developments", "forward_looking_insights", "estimate_accuracy_assessment", 
                                     "requires_attention"]:
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
                    # For text sections (executive_summary, potential_thesis_impact, analysis_generation_details, confidence_assessment)
                    if sections[current_section]:
                        sections[current_section] += " " + line
                    else:
                        sections[current_section] = line
        
        # Clean up text sections
        sections["executive_summary"] = sections["executive_summary"].strip()
        sections["potential_thesis_impact"] = sections["potential_thesis_impact"].strip()
        sections["analysis_generation_details"] = sections["analysis_generation_details"].strip()
        sections["confidence_assessment"] = sections["confidence_assessment"].strip()
        
        # Remove empty items from list sections
        for key in ["analyst_estimates_comparison", "financial_performance", "business_segments", 
                   "strategic_developments", "forward_looking_insights", "estimate_accuracy_assessment", 
                   "requires_attention"]:
            sections[key] = [item.strip() for item in sections[key] if item.strip()]
        
        # Combine sections for frontend compatibility with analyst estimates prioritized
        # key_changes = analyst estimates comparison + financial performance + key strategic items
        sections["key_changes"] = []
        if sections["analyst_estimates_comparison"]:
            sections["key_changes"].extend(sections["analyst_estimates_comparison"][:3])  # Top 3 estimate items
        if sections["financial_performance"]:
            sections["key_changes"].extend(sections["financial_performance"][:2])  # Top 2 financial items
        if sections["strategic_developments"]:
            sections["key_changes"].extend(sections["strategic_developments"][:2])  # Top 2 strategic items
            
        # new_insights = business_segments + forward_looking + estimate accuracy insights
        sections["new_insights"] = []
        if sections["business_segments"]:
            sections["new_insights"].extend(sections["business_segments"][:2])
        if sections["forward_looking_insights"]:
            sections["new_insights"].extend(sections["forward_looking_insights"][:2])
        if sections["estimate_accuracy_assessment"]:
            sections["new_insights"].extend(sections["estimate_accuracy_assessment"][:2])
        
        return sections

    def _create_report_prompt(self, new_document: str, context: str, analysis_type: str, analysis: Optional[Dict] = None) -> str:
        """Create enhanced prompt for detailed report generation (Stage 2) with comprehensive context explanation"""
        
        analysis_context = ""
        if analysis:
            analysis_context = f"""

INITIAL ANALYSIS FOR EXPANSION:
Executive Summary: {analysis.get('executive_summary', '')}
Key Changes: {', '.join(analysis.get('key_changes', []))}
New Insights: {', '.join(analysis.get('new_insights', []))}
Thesis Impact: {analysis.get('potential_thesis_impact', '')}
Analysis Generation Details: {analysis.get('analysis_generation_details', '')}
"""
        
        base_prompt = f"""
You are generating a DETAILED RESEARCH REPORT based on initial analysis and comprehensive historical context. Expand significantly on the findings with detailed context and implications.

COMPREHENSIVE EXISTING RESEARCH CONTEXT:
{context}

NEW DOCUMENT TO ANALYZE:
{new_document}
{analysis_context}

ANALYSIS TYPE: {analysis_type}

Please provide a comprehensive structured analysis expanding on the initial findings:

1. EXECUTIVE SUMMARY (4-5 sentences with detailed investment implications)

2. DETAILED ANALYSIS OF CHANGES:
- Expand significantly on identified changes with comprehensive supporting evidence from historical context
- Quantify impact using specific metrics and historical benchmarks
- Provide detailed historical context and trend comparisons
- Reference specific historical reports and analyst estimates where relevant

3. COMPREHENSIVE NEW INSIGHTS:
- Deep dive into new information with extensive historical comparison
- Market impact assessment based on historical patterns
- Competitive implications using historical competitive data
- Long-term trend analysis and implications

4. INVESTMENT THESIS UPDATE:
- Detailed assessment of thesis impact with historical perspective
- Updated investment drivers analysis with supporting historical data
- Comprehensive risk assessment updates (upside/downside scenarios)
- Specific actionable recommendations for investors

5. ANALYSIS GENERATION DETAILS:
- Provide detailed explanation of HOW the comprehensive historical context informed this analysis
- Identify specific historical reports, estimates, and data points that were crucial for the conclusions
- Explain which financial metrics and trends were benchmarked against historical performance
- Detail confidence levels based on depth and quality of available historical context
- Note any limitations in historical data that affected the analysis quality

6. SOURCE CITATIONS AND CONFIDENCE:
- Reference specific data points, sources, and historical benchmarks
- Indicate confidence levels for each major finding based on historical support
- Highlight areas requiring further monitoring with historical context
- Provide historical precedents where applicable

CRITICAL REQUIREMENTS:
- Expand significantly on the approved initial analysis with much greater detail and historical context
- Provide comprehensive actionable investment insights with detailed supporting evidence
- Use the extensive historical context to provide deeper perspective and validation
- In "Analysis Generation Details", explicitly explain how you leveraged the historical research to enhance the analysis quality and confidence
"""
        
        return base_prompt
    
    def _parse_draft_response(self, draft_content: str) -> Dict:
        """Parse the AI response into structured format with enhanced sections"""
        
        sections = {
            "executive_summary": "",
            "key_changes": [],
            "new_insights": [],
            "investment_thesis_impact": "",
            "analysis_generation_details": "",  # New section for reports too
            "source_citations_confidence": ""
        }
        
        lines = draft_content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Identify sections with enhanced matching
            line_upper = line.upper()
            if "EXECUTIVE SUMMARY" in line_upper:
                current_section = "executive_summary"
            elif "DETAILED ANALYSIS OF CHANGES" in line_upper or "KEY CHANGES" in line_upper:
                current_section = "key_changes"
            elif "COMPREHENSIVE NEW INSIGHTS" in line_upper or "NEW INSIGHTS" in line_upper:
                current_section = "new_insights"
            elif "INVESTMENT THESIS UPDATE" in line_upper or "INVESTMENT THESIS IMPACT" in line_upper:
                current_section = "investment_thesis_impact"
            elif "ANALYSIS GENERATION DETAILS" in line_upper:
                current_section = "analysis_generation_details"
            elif "SOURCE CITATIONS" in line_upper or "CONFIDENCE" in line_upper:
                current_section = "source_citations_confidence"
            elif current_section:
                # Add content to current section
                if current_section in ["key_changes", "new_insights"]:
                    if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        sections[current_section].append(line[1:].strip())
                    elif len(line) > 3:  # Add substantial content as new points
                        sections[current_section].append(line)
                else:
                    # For text sections
                    if sections[current_section]:
                        sections[current_section] += " " + line
                    else:
                        sections[current_section] = line
        
        # Clean up text sections
        sections["executive_summary"] = sections["executive_summary"].strip()
        sections["investment_thesis_impact"] = sections["investment_thesis_impact"].strip()
        sections["analysis_generation_details"] = sections["analysis_generation_details"].strip()
        sections["source_citations_confidence"] = sections["source_citations_confidence"].strip()
        
        # Clean up list sections
        sections["key_changes"] = [item.strip() for item in sections["key_changes"] if item.strip()]
        sections["new_insights"] = [item.strip() for item in sections["new_insights"] if item.strip()]
        
        return sections
    
    def _prepare_context_with_estimates(self, context_documents: List[Dict], comparative_data: Dict, analyst_estimates: Optional[str] = None) -> str:
        """Prepare context including estimates data and raw analyst estimates for comparative analysis"""
        context_parts = []
        
        # Add regular document context
        regular_context = self._prepare_context(context_documents)
        if regular_context:
            context_parts.append("HISTORICAL CONTEXT:")
            context_parts.append(regular_context)
        
        # Add raw analyst estimates if available
        if analyst_estimates:
            context_parts.append("\nRAW ANALYST ESTIMATES:")
            context_parts.append(analyst_estimates)
        
        # Add estimates comparison data
        if comparative_data:
            context_parts.append("\nESTIMATES AND COMPARATIVE DATA:")
            
            # Revenue comparisons
            if comparative_data.get("revenue_comparison"):
                context_parts.append("\nRevenue Analysis:")
                for comp in comparative_data["revenue_comparison"]:
                    context_parts.append(f"- {comp.get('metric', 'Revenue')}: {comp.get('actual', 'N/A')} (Actual)")
                    if comp.get('variance_analysis'):
                        context_parts.append(f"  Analysis: {comp['variance_analysis']}")
            
            # Margin comparisons
            if comparative_data.get("margin_comparison"):
                context_parts.append("\nMargin Analysis:")
                for comp in comparative_data["margin_comparison"]:
                    context_parts.append(f"- {comp.get('metric', 'Margin')}: {comp.get('actual', 'N/A')} (Actual)")
                    if comp.get('estimates'):
                        context_parts.append(f"  vs Estimates: {comp['estimates']}")
            
            # Segment comparisons
            if comparative_data.get("segment_comparison"):
                context_parts.append("\nSegment Performance:")
                for comp in comparative_data["segment_comparison"]:
                    context_parts.append(f"- {comp.get('segment', 'Segment')}: {comp.get('actual', 'N/A')} (Actual)")
                    if comp.get('estimates'):
                        context_parts.append(f"  vs Estimates: {comp['estimates']}")
            
            # Investment implications
            if comparative_data.get("investment_implications"):
                context_parts.append("\nInvestment Implications:")
                for impl in comparative_data["investment_implications"]:
                    context_parts.append(f"- {impl.get('category', 'General')}: {impl.get('impact', 'Unknown')} impact")
                    context_parts.append(f"  {impl.get('description', '')}")
                    if impl.get('investment_thesis_impact'):
                        context_parts.append(f"  Thesis Impact: {impl['investment_thesis_impact']}")
            
            # Quarter context
            if comparative_data.get("quarter_context"):
                context_parts.append(f"\nReporting Quarter: {comparative_data['quarter_context']}")
        
        return "\n".join(context_parts)
    
    def _create_comparative_analysis_prompt(self, new_document: str, context: str, 
                                          comparative_data: Dict, analysis_type: str) -> str:
        """Create enhanced prompt for comparative analysis with estimates data"""
        
        base_prompt = f"""
As an expert investment research analyst, analyze the following new document in the context of historical data and analyst estimates. 
Focus particularly on comparative analysis, variance from estimates, and investment thesis implications.

DOCUMENT TO ANALYZE:
{new_document[:4000]}  # Limit to prevent token overflow

HISTORICAL AND ESTIMATES CONTEXT:
{context[:6000]}  # Extended context for comparative analysis

ANALYSIS INSTRUCTIONS:
Generate a comprehensive comparative analysis with the following structure:

1. EXECUTIVE SUMMARY:
- Brief overview of key findings and estimate variances
- Overall assessment of company performance vs expectations
- Critical investment implications

2. ESTIMATES VS ACTUALS ANALYSIS:
- Detailed comparison of actual metrics against analyst estimates
- Quantify variances where possible (beat/miss and by how much)
- Assess significance of variances and their implications

3. SEGMENT PERFORMANCE COMPARISON:
- Compare segment results against historical trends and estimates
- Identify outperforming and underperforming segments
- Assess impact on overall investment thesis

4. MARGIN AND PROFITABILITY ANALYSIS:
- Compare actual margins against estimates and historical performance
- Analyze trends and sustainability of margin performance
- Impact on profitability outlook

5. INVESTMENT THESIS IMPACT:
- How do actual results affect the investment thesis?
- Are there changes to growth assumptions, risk profile, or valuation?
- What are the implications for future quarters and annual performance?

6. RISK ASSESSMENT UPDATE:
- New risks identified from variance analysis
- Changes to existing risk factors
- Mitigation strategies and monitoring points

7. ACTIONABLE INSIGHTS:
- Specific investment recommendations based on comparative analysis
- Key metrics to monitor in future reports
- Catalysts and potential thesis changes

CRITICAL REQUIREMENTS:
- Quantify variances where possible with specific percentages or dollar amounts
- Clearly distinguish between beats/misses vs estimates and their significance
- Provide investment-grade insights with clear thesis implications
- Reference specific data points and historical context
- Focus on actionable intelligence for investment decision-making

"""
        
        return base_prompt
    
    def _parse_comparative_analysis_response(self, analysis_content: str) -> Dict:
        """Parse comparative analysis response into structured format"""
        
        sections = {
            "executive_summary": "",
            "estimates_vs_actuals": "",
            "segment_comparison": "",
            "margin_analysis": "",
            "investment_thesis_impact": "",
            "risk_assessment_update": "",
            "actionable_insights": [],
            "variance_highlights": [],
            "investment_recommendations": []
        }
        
        current_section = None
        
        for line in analysis_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers
            line_lower = line.lower()
            if 'executive summary' in line_lower:
                current_section = "executive_summary"
                continue
            elif 'estimates vs actual' in line_lower or 'actuals analysis' in line_lower:
                current_section = "estimates_vs_actuals"
                continue
            elif 'segment' in line_lower and ('performance' in line_lower or 'comparison' in line_lower):
                current_section = "segment_comparison"
                continue
            elif 'margin' in line_lower and ('profitability' in line_lower or 'analysis' in line_lower):
                current_section = "margin_analysis"
                continue
            elif 'investment thesis' in line_lower and 'impact' in line_lower:
                current_section = "investment_thesis_impact"
                continue
            elif 'risk assessment' in line_lower or 'risk' in line_lower and 'update' in line_lower:
                current_section = "risk_assessment_update"
                continue
            elif 'actionable insights' in line_lower or 'recommendations' in line_lower:
                current_section = "actionable_insights"
                continue
            
            # Add content to current section
            if current_section:
                if current_section == "actionable_insights":
                    if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        sections["actionable_insights"].append(line[1:].strip())
                    elif len(line) > 10:  # Substantial content
                        sections["actionable_insights"].append(line)
                else:
                    # For text sections
                    if sections[current_section]:
                        sections[current_section] += " " + line
                    else:
                        sections[current_section] = line
        
        # Clean up sections
        for key in sections:
            if isinstance(sections[key], str):
                sections[key] = sections[key].strip()
            elif isinstance(sections[key], list):
                sections[key] = [item.strip() for item in sections[key] if item.strip()]
        
        # Extract variance highlights from estimates vs actuals section
        if sections.get("estimates_vs_actuals"):
            variance_text = sections["estimates_vs_actuals"]
            # Look for beat/miss language and percentages
            variance_patterns = [
                r'beat.*?by (\d+(?:\.\d+)?%)',
                r'missed.*?by (\d+(?:\.\d+)?%)',
                r'exceeded.*?by (\d+(?:\.\d+)?%)',
                r'below.*?by (\d+(?:\.\d+)?%)'
            ]
            
            import re
            for pattern in variance_patterns:
                matches = re.findall(pattern, variance_text, re.IGNORECASE)
                for match in matches:
                    sections["variance_highlights"].append(f"Variance: {match}")
        
        return sections

    def generate_batch_report(self, batch_analyses: List[Dict], context_documents: List[Dict], 
                            ticker: str, batch_info: Dict) -> Dict:
        """Generate a comprehensive report for a batch of analyzed documents"""
        
        try:
            # Prepare combined analysis summary
            combined_insights = []
            key_themes = []
            all_actionable_insights = []
            
            for analysis in batch_analyses:
                if analysis.get('executive_summary'):
                    combined_insights.append(analysis['executive_summary'])
                if analysis.get('key_changes'):
                    key_themes.extend(analysis['key_changes'])
                if analysis.get('new_insights'):
                    key_themes.extend(analysis['new_insights'])
                if analysis.get('actionable_insights'):
                    all_actionable_insights.extend(analysis['actionable_insights'])
            
            # Prepare context
            context = self._prepare_context(context_documents)
            
            # Create comprehensive batch report prompt
            prompt = f"""
You are generating a COMPREHENSIVE INVESTMENT RESEARCH REPORT based on analysis of {len(batch_analyses)} documents for {ticker}.

BATCH INFORMATION:
Batch Name: {batch_info.get('name', 'Unknown')}
Description: {batch_info.get('description', 'No description')}
Documents Analyzed: {batch_info.get('document_count', len(batch_analyses))}

HISTORICAL CONTEXT:
{context}

COMBINED ANALYSIS INSIGHTS:
{chr(10).join([f"• {insight}" for insight in combined_insights[:10]])}

KEY THEMES IDENTIFIED:
{chr(10).join([f"• {theme}" for theme in list(set(key_themes))[:15]])}

ACTIONABLE INSIGHTS FROM ALL DOCUMENTS:
{chr(10).join([f"• {insight}" for insight in list(set(all_actionable_insights))[:10]])}

Please provide a comprehensive, professional investment research report with the following sections:

## EXECUTIVE SUMMARY
(4-5 sentences summarizing the most critical investment implications across all documents)

## KEY DEVELOPMENTS ANALYSIS
(Detailed analysis of the most significant changes and developments identified across documents)

## CONSOLIDATED FINANCIAL INSIGHTS
(Combined financial performance analysis and key metrics from all documents)

## STRATEGIC IMPLICATIONS
(Investment thesis impact and strategic considerations)

## RISK ASSESSMENT
(Comprehensive risk analysis based on all analyzed documents)

## INVESTMENT RECOMMENDATION
(Clear investment recommendation with price target if applicable and supporting rationale)

## NEXT STEPS AND MONITORING POINTS
(Key items for ongoing monitoring based on the analysis)

Focus on synthesizing insights across multiple documents to provide a holistic view of the company's current situation and prospects.
"""

            self._log_api_call('chat.batch_report', prompt=prompt)
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert investment research analyst generating comprehensive multi-document research reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            report_content = response.choices[0].message.content
            
            # Parse the response into structured format
            structured_report = self._parse_batch_report_response(report_content)
            
            # Add metadata
            structured_report['metadata'] = {
                'documents_analyzed': len(batch_analyses),
                'batch_info': batch_info,
                'ticker': ticker,
                'generated_at': context_documents[0].get('metadata', {}).get('timestamp') if context_documents else None,
                'model_used': self.model,
                'context_documents_count': len(context_documents)
            }
            
            self._log_api_call('chat.batch_report', response_preview=report_content)
            
            return structured_report
            
        except Exception as e:
            logger.error(f"Error generating batch report: {str(e)}")
            self._log_api_call('chat.batch_report', error=e)
            raise
    
    def _parse_batch_report_response(self, content: str) -> Dict:
        """Parse batch report response into structured format"""
        
        sections = {
            "executive_summary": "",
            "key_developments": "",
            "financial_insights": "",
            "strategic_implications": "",
            "risk_assessment": "",
            "investment_recommendation": "",
            "next_steps": "",
            "full_content": content
        }
        
        # Simple section parsing based on headers
        section_markers = {
            "executive_summary": ["## EXECUTIVE SUMMARY", "EXECUTIVE SUMMARY"],
            "key_developments": ["## KEY DEVELOPMENTS", "KEY DEVELOPMENTS"],
            "financial_insights": ["## CONSOLIDATED FINANCIAL", "FINANCIAL INSIGHTS", "FINANCIAL"],
            "strategic_implications": ["## STRATEGIC IMPLICATIONS", "STRATEGIC"],
            "risk_assessment": ["## RISK ASSESSMENT", "RISK"],
            "investment_recommendation": ["## INVESTMENT RECOMMENDATION", "RECOMMENDATION"],
            "next_steps": ["## NEXT STEPS", "MONITORING POINTS", "NEXT STEPS"]
        }
        
        for section_key, markers in section_markers.items():
            for marker in markers:
                if marker in content:
                    start_idx = content.find(marker)
                    if start_idx != -1:
                        # Find the next section or end
                        next_section_idx = len(content)
                        for other_key, other_markers in section_markers.items():
                            if other_key != section_key:
                                for other_marker in other_markers:
                                    idx = content.find(other_marker, start_idx + len(marker))
                                    if idx != -1 and idx < next_section_idx:
                                        next_section_idx = idx
                        
                        section_content = content[start_idx + len(marker):next_section_idx].strip()
                        if section_content:
                            sections[section_key] = section_content
                            break
        
        return sections
