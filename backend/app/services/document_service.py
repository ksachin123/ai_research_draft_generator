import PyPDF2
import hashlib
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
import re

from langchain.text_splitter import RecursiveCharacterTextSplitter
from .enhanced_pdf_processor import EnhancedPDFProcessor

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    def __init__(self, config, ai_service, knowledge_base_service=None):
        self.config = config
        self.ai_service = ai_service
        self.kb_service = knowledge_base_service
        self.enhanced_processor = EnhancedPDFProcessor()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
        )
    
    def extract_pdf_text(self, file_path: str) -> Tuple[str, Dict]:
        """Enhanced PDF text extraction with table processing"""
        try:
            # Use enhanced processor for better table extraction
            text, extracted_tables, metadata = self.enhanced_processor.extract_pdf_with_tables(file_path)
            
            # If enhanced extraction fails, fall back to basic extraction
            if not text:
                logger.warning("Enhanced extraction failed, falling back to basic PyPDF2")
                return self._basic_pdf_extraction(file_path)
            
            # Convert tables to structured text and append
            if extracted_tables:
                structured_tables = self.enhanced_processor.convert_tables_to_structured_text(extracted_tables)
                text += "\n\n=== EXTRACTED FINANCIAL TABLES ===\n" + structured_tables
                
                # Extract key financial metrics
                financial_metrics = self.enhanced_processor.extract_key_financial_metrics(extracted_tables)
                if financial_metrics:
                    metrics_text = self._format_financial_metrics(financial_metrics)
                    text += "\n\n=== KEY FINANCIAL METRICS ===\n" + metrics_text
                    
                # Add table metadata
                metadata["extracted_tables"] = len(extracted_tables)
                metadata["financial_tables"] = len([t for t in extracted_tables if t.table_type == 'financial'])
                metadata["table_confidence"] = sum(t.confidence_score for t in extracted_tables) / len(extracted_tables) if extracted_tables else 0
            
            logger.info(f"Enhanced extraction from {file_path}: {metadata}")
            return text, metadata
            
        except Exception as e:
            logger.error(f"Enhanced PDF extraction failed for {file_path}: {str(e)}")
            # Fall back to basic extraction
            return self._basic_pdf_extraction(file_path)
    
    def _basic_pdf_extraction(self, file_path: str) -> Tuple[str, Dict]:
        """Fallback basic PDF extraction using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                
                metadata = {
                    "total_pages": page_count,
                    "character_count": len(text),
                    "word_count": len(text.split()),
                    "extraction_method": "basic_pypdf2"
                }
                
                logger.info(f"Basic extraction from {file_path}: {page_count} pages, {len(text)} characters")
                return text, metadata
                
        except Exception as e:
            logger.error(f"Failed basic extraction from {file_path}: {str(e)}")
            raise
    
    def _format_financial_metrics(self, metrics: Dict) -> str:
        """Format financial metrics into readable text"""
        formatted_text = ""
        
        for category, data in metrics.items():
            if not data:
                continue
                
            formatted_text += f"\n{category.upper()} METRICS:\n"
            for metric_name, values in data.items():
                if values:
                    formatted_text += f"  {metric_name}: {', '.join(str(v) for v in values if v)}\n"
        
        return formatted_text
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return f"sha256:{hash_sha256.hexdigest()}"
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {str(e)}")
            raise
    
    def chunk_document(self, text: str, metadata: Dict) -> List[Dict]:
        """Split document into chunks with metadata"""
        try:
            chunks = self.text_splitter.split_text(text)
            
            chunked_docs = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i + 1,
                    "total_chunks": len(chunks),
                    "word_count": len(chunk.split()),
                    "character_count": len(chunk)
                })
                
                chunked_docs.append({
                    "text": chunk,
                    "metadata": chunk_metadata
                })
            
            logger.info(f"Created {len(chunks)} chunks from document")
            return chunked_docs
            
        except Exception as e:
            logger.error(f"Failed to chunk document: {str(e)}")
            raise
    
    def process_pdf_report(self, ticker: str, file_path: str) -> List[Dict]:
        """Process a PDF report into embeddings"""
        file_name = os.path.basename(file_path)
        file_hash = self.calculate_file_hash(file_path)
        
        # Extract text
        text, pdf_metadata = self.extract_pdf_text(file_path)
        
        # Create base metadata
        base_metadata = {
            "company_ticker": ticker.upper(),
            "document_type": "past_report",
            "file_name": file_name,
            "file_path": file_path,
            "file_hash": file_hash,
            "processed_date": datetime.utcnow().isoformat() + "Z",
            "content_type": "research_analysis",
            "processing_version": "1.0"
        }
        base_metadata.update(pdf_metadata)
        
        # Chunk document
        chunks = self.chunk_document(text, base_metadata)
        
        # Generate embeddings
        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                embedding = self.ai_service.generate_embedding(chunk["text"])
                
                embedded_chunks.append({
                    "id": f"{ticker.lower()}_report_{file_name}_{i+1:03d}",
                    "embedding": embedding,
                    "metadata": chunk["metadata"],
                    "document": chunk["text"]
                })
                
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {i+1}: {str(e)}")
                raise
        
        logger.info(f"Processed {file_name}: {len(embedded_chunks)} embedded chunks")
        return embedded_chunks
    
    def process_investment_data(self, ticker: str, data_type: str, file_path: str) -> List[Dict]:
        """Process investment data JSON files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_name = os.path.basename(file_path)
            
            # Extract readable text from JSON
            if data_type == "investmentthesis" or "thesis" in data_type.lower():
                text = self._extract_investment_thesis_text(data)
            elif data_type == "investmentdrivers" or "drivers" in data_type.lower():
                text = self._extract_investment_drivers_text(data)
            elif data_type == "risks":
                text = self._extract_risks_text(data)
            else:
                text = json.dumps(data, indent=2)
            
            # Generate embedding
            embedding = self.ai_service.generate_embedding(text)
            
            # Create metadata
            metadata = {
                "company_ticker": ticker.upper(),
                "document_type": "investment_data",
                "data_type": data_type,
                "file_name": file_name,
                "processed_date": datetime.utcnow().isoformat() + "Z",
                "content_type": "structured_data",
                "is_current": True,
                "processing_version": "1.0"
            }
            
            # Add specific fields based on data type
            if ("thesis" in data_type.lower() or data_type == "investmentthesis") and "rating" in data:
                metadata["rating"] = data.get("rating")
                metadata["target_price"] = data.get("targetPrice")
            
            document = {
                "id": f"{ticker.lower()}_{data_type}_{datetime.now().strftime('%Y%m%d')}",
                "embedding": embedding,
                "metadata": metadata,
                "document": text
            }
            
            logger.info(f"Processed investment data: {file_name}")
            return [document]
            
        except Exception as e:
            logger.error(f"Failed to process investment data {file_path}: {str(e)}")
            raise
    
    def _extract_investment_thesis_text(self, data: Dict) -> str:
        """Extract readable text from investment thesis JSON"""
        thesis = data.get("investmentThesis", "")
        # Remove HTML tags for cleaner text
        clean_thesis = re.sub('<.*?>', '', thesis)
        
        parts = [f"Investment Thesis: {clean_thesis}"]
        
        if data.get("targetPrice"):
            parts.append(f"Target Price: ${data['targetPrice']}")
        if data.get("rating"):
            parts.append(f"Rating: {data['rating']}")
        
        return "\n".join(parts)
    
    def _extract_investment_drivers_text(self, data: Dict) -> str:
        """Extract readable text from investment drivers JSON"""
        drivers = data.get("investmentDrivers", "")
        # Remove HTML tags
        clean_drivers = re.sub('<.*?>', '', drivers)
        clean_drivers = re.sub('<li>', '• ', clean_drivers)
        
        return f"Investment Drivers:\n{clean_drivers}"
    
    def _extract_risks_text(self, data: Dict) -> str:
        """Extract readable text from risks JSON"""
        upside = data.get("risksToUpside", "")
        downside = data.get("riskToDownside", "")
        
        # Clean HTML tags
        clean_upside = re.sub('<.*?>', '', upside)
        clean_upside = re.sub('<li>', '• ', clean_upside)
        
        clean_downside = re.sub('<.*?>', '', downside)
        clean_downside = re.sub('<li>', '• ', clean_downside)
        
        parts = []
        if clean_upside:
            parts.append(f"Risks to Upside:\n{clean_upside}")
        if clean_downside:
            parts.append(f"Risks to Downside:\n{clean_downside}")
        
        return "\n\n".join(parts)
    
    def process_uploaded_document_with_comparison(self, ticker: str, file_path: str, 
                                                document_date: Optional[datetime] = None) -> Dict:
        """
        Process uploaded document and perform comparison with estimates data
        
        Args:
            ticker: Company ticker symbol
            file_path: Path to the uploaded document
            document_date: Date of the document (extracted or provided)
            
        Returns:
            Dictionary containing processed document data and comparative analysis
        """
        try:
            logger.info(f"Processing document with comparison for {ticker}: {file_path}")
            
            # Process the document normally
            embedded_chunks = self.process_pdf_report(ticker, file_path)
            
            # Extract full document text for analysis
            full_text, pdf_metadata = self.extract_pdf_text(file_path)
            
            # Extract document date if not provided
            if not document_date:
                document_date = self._extract_document_date(full_text, file_path)
            
            # Extract financial metrics from the document
            document_metrics = self._extract_document_metrics(full_text, document_date)
            
            # Get estimates data for comparison
            comparative_analysis = {}
            if self.kb_service:
                estimates_data = self.kb_service.get_estimates_data(ticker)
                if estimates_data:
                    # Perform comparative analysis
                    comparative_analysis = self._perform_comparative_analysis(
                        ticker, document_metrics, estimates_data, document_date
                    )
            
            return {
                "embedded_chunks": embedded_chunks,
                "document_metrics": document_metrics,
                "comparative_analysis": comparative_analysis,
                "document_date": document_date.isoformat() if document_date else None,
                "processing_metadata": pdf_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to process document with comparison: {str(e)}")
            raise
    
    def _extract_document_date(self, text: str, file_path: str) -> Optional[datetime]:
        """Extract document date from text or filename"""
        try:
            # Try to extract from filename first (common patterns)
            filename = os.path.basename(file_path)
            filename_patterns = [
                r'(\d{4})[-_]?Q?(\d{1})',  # 2024Q3, 2024-Q3, 2024_3
                r'Q(\d{1})[-_]?(\d{4})',   # Q3-2024, Q3_2024
                r'(\d{4})[-_](\d{2})[-_](\d{2})',  # 2024-09-30
                r'(\d{2})[-_](\d{2})[-_](\d{4})'   # 09-30-2024
            ]
            
            for pattern in filename_patterns:
                match = re.search(pattern, filename)
                if match:
                    groups = match.groups()
                    try:
                        if len(groups) == 2:
                            # Year and quarter
                            year, quarter = int(groups[0]), int(groups[1])
                            if year > 2000 and quarter <= 4:
                                # Convert quarter to approximate month
                                month = quarter * 3
                                return datetime(year, month, 1)
                    except ValueError:
                        continue
            
            # Try to extract from document text
            text_patterns = [
                r'for\s+the\s+quarter\s+ended\s+(\w+\s+\d{1,2},?\s+\d{4})',
                r'quarter\s+ended\s+(\w+\s+\d{1,2},?\s+\d{4})',
                r'fiscal\s+(\d{4})\s+third\s+quarter',
                r'Q([1-4])\s+(\d{4})',
                r'(\d{4})\s+Q([1-4])'
            ]
            
            for pattern in text_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Take the first match and try to parse it
                    match = matches[0]
                    if isinstance(match, tuple):
                        if len(match) == 2:
                            try:
                                quarter, year = int(match[0]), int(match[1])
                                if quarter <= 4 and year > 2000:
                                    month = quarter * 3
                                    return datetime(year, month, 1)
                            except ValueError:
                                continue
                    else:
                        # Try to parse date string
                        try:
                            from dateutil.parser import parse
                            return parse(match)
                        except:
                            continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract document date: {str(e)}")
            return None
    
    def _extract_document_metrics(self, text: str, document_date: Optional[datetime]) -> Dict:
        """Extract key financial metrics from document text"""
        metrics = {
            "revenue": {},
            "margins": {},
            "segments": {},
            "growth_rates": {},
            "key_figures": {},
            "document_quarter": None
        }
        
        try:
            # Determine document quarter
            if document_date:
                quarter = ((document_date.month - 1) // 3) + 1
                metrics["document_quarter"] = f"Q{quarter} {document_date.year}"
            
            # Extract revenue figures
            revenue_patterns = [
                r'revenue\s+of\s+\$?(\d+(?:\.\d+)?)\s*(billion|million|b|m)',
                r'net\s+sales\s+of\s+\$?(\d+(?:\.\d+)?)\s*(billion|million|b|m)',
                r'total\s+revenue\s+\$?(\d+(?:\.\d+)?)\s*(billion|million|b|m)'
            ]
            
            for pattern in revenue_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for value, unit in matches:
                        multiplier = 1000000000 if unit.lower() in ['billion', 'b'] else 1000000
                        revenue_value = float(value) * multiplier
                        metrics["revenue"][f"total_revenue_{unit}"] = {
                            "value": revenue_value,
                            "raw_text": f"${value} {unit}"
                        }
            
            # Extract margin information
            margin_patterns = [
                r'gross\s+margin\s+of\s+(\d+(?:\.\d+)?)\s*%',
                r'operating\s+margin\s+of\s+(\d+(?:\.\d+)?)\s*%',
                r'net\s+margin\s+of\s+(\d+(?:\.\d+)?)\s*%'
            ]
            
            for pattern in margin_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    margin_type = pattern.split('\\')[0].replace('s+', ' ')
                    for value in matches:
                        metrics["margins"][f"{margin_type}_margin"] = {
                            "value": float(value),
                            "raw_text": f"{value}%"
                        }
            
            # Extract segment revenue
            segment_patterns = [
                r'iPhone\s+revenue\s+of\s+\$?(\d+(?:\.\d+)?)\s*(billion|million)',
                r'Mac\s+revenue\s+of\s+\$?(\d+(?:\.\d+)?)\s*(billion|million)',
                r'iPad\s+revenue\s+of\s+\$?(\d+(?:\.\d+)?)\s*(billion|million)',
                r'Services\s+revenue\s+of\s+\$?(\d+(?:\.\d+)?)\s*(billion|million)',
                r'Wearables.*revenue\s+of\s+\$?(\d+(?:\.\d+)?)\s*(billion|million)'
            ]
            
            for pattern in segment_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    segment_name = pattern.split('\\')[0].replace('s+', ' ')
                    for value, unit in matches:
                        multiplier = 1000000000 if unit.lower() == 'billion' else 1000000
                        segment_value = float(value) * multiplier
                        metrics["segments"][segment_name] = {
                            "value": segment_value,
                            "raw_text": f"${value} {unit}"
                        }
            
            # Extract growth rates
            growth_patterns = [
                r'revenue\s+(?:grew|increased|grew)\s+(\d+(?:\.\d+)?)\s*%',
                r'(\d+(?:\.\d+)?)\s*%\s+revenue\s+growth',
                r'year-over-year\s+growth\s+of\s+(\d+(?:\.\d+)?)\s*%'
            ]
            
            for pattern in growth_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for value in matches:
                        metrics["growth_rates"]["revenue_yoy"] = {
                            "value": float(value),
                            "raw_text": f"{value}% growth"
                        }
            
            logger.info(f"Extracted metrics: {len(metrics['revenue'])} revenue, {len(metrics['segments'])} segments")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to extract document metrics: {str(e)}")
            return metrics
    
    def _perform_comparative_analysis(self, ticker: str, document_metrics: Dict, 
                                    estimates_data: Dict, document_date: Optional[datetime]) -> Dict:
        """Perform comparative analysis between document metrics and estimates data"""
        analysis = {
            "revenue_comparison": [],
            "margin_comparison": [],
            "segment_comparison": [],
            "estimate_vs_actual": [],
            "investment_implications": [],
            "quarter_context": None
        }
        
        try:
            # Set quarter context
            if document_date:
                quarter = ((document_date.month - 1) // 3) + 1
                analysis["quarter_context"] = f"Q{quarter} {document_date.year}"
            
            # Compare revenue metrics
            if document_metrics.get("revenue") and estimates_data.get("income_statement"):
                revenue_comparison = self._compare_revenue_with_estimates(
                    document_metrics["revenue"], 
                    estimates_data["income_statement"]
                )
                analysis["revenue_comparison"].extend(revenue_comparison)
            
            # Compare margins
            if document_metrics.get("margins") and estimates_data.get("income_statement", {}).get("margins"):
                margin_comparison = self._compare_margins_with_estimates(
                    document_metrics["margins"],
                    estimates_data["income_statement"]["margins"]
                )
                analysis["margin_comparison"].extend(margin_comparison)
            
            # Compare segment performance
            if document_metrics.get("segments") and estimates_data.get("income_statement", {}).get("segment_data"):
                segment_comparison = self._compare_segments_with_estimates(
                    document_metrics["segments"],
                    estimates_data["income_statement"]["segment_data"]
                )
                analysis["segment_comparison"].extend(segment_comparison)
            
            # Generate investment implications
            analysis["investment_implications"] = self._generate_investment_implications(
                ticker, analysis, document_metrics
            )
            
            logger.info(f"Generated comparative analysis with {len(analysis['investment_implications'])} implications")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to perform comparative analysis: {str(e)}")
            return analysis
    
    def _compare_revenue_with_estimates(self, document_revenue: Dict, estimates_income: Dict) -> List[Dict]:
        """Compare actual revenue with estimates"""
        comparisons = []
        
        for revenue_key, revenue_data in document_revenue.items():
            actual_value = revenue_data.get("value", 0)
            
            # Look for comparable estimates
            # This would be enhanced with more sophisticated matching
            if "total_revenue" in revenue_key.lower():
                comparison = {
                    "metric": "Total Revenue",
                    "actual": revenue_data.get("raw_text", str(actual_value)),
                    "variance_analysis": "Compare with quarterly estimates",
                    "significance": "high"
                }
                comparisons.append(comparison)
        
        return comparisons
    
    def _compare_margins_with_estimates(self, document_margins: Dict, estimates_margins: Dict) -> List[Dict]:
        """Compare actual margins with estimates"""
        comparisons = []
        
        for margin_key, margin_data in document_margins.items():
            actual_value = margin_data.get("value", 0)
            
            # Find comparable margin in estimates
            for est_margin_key, est_margin_data in estimates_margins.items():
                if self._are_comparable_margins(margin_key, est_margin_key):
                    comparison = {
                        "metric": margin_key.replace("_", " ").title(),
                        "actual": margin_data.get("raw_text", f"{actual_value}%"),
                        "estimates": est_margin_data,
                        "variance": "To be calculated based on estimates",
                        "significance": "medium"
                    }
                    comparisons.append(comparison)
        
        return comparisons
    
    def _compare_segments_with_estimates(self, document_segments: Dict, estimates_segments: Dict) -> List[Dict]:
        """Compare actual segment performance with estimates"""
        comparisons = []
        
        for segment_key, segment_data in document_segments.items():
            # Find matching segment in estimates
            for est_segment_key, est_segment_data in estimates_segments.items():
                if self._are_comparable_segments(segment_key, est_segment_key):
                    comparison = {
                        "segment": segment_key,
                        "actual": segment_data.get("raw_text", str(segment_data.get("value", 0))),
                        "estimates": est_segment_data,
                        "variance": "To be calculated",
                        "significance": "high"
                    }
                    comparisons.append(comparison)
        
        return comparisons
    
    def _are_comparable_margins(self, doc_margin: str, est_margin: str) -> bool:
        """Check if two margin metrics are comparable"""
        doc_type = doc_margin.lower().replace("_", "")
        est_type = est_margin.lower().replace("_", "")
        
        comparable_pairs = [
            ("gross", "gross"),
            ("operating", "operating"),
            ("net", "net")
        ]
        
        for doc_key, est_key in comparable_pairs:
            if doc_key in doc_type and est_key in est_type:
                return True
        
        return False
    
    def _are_comparable_segments(self, doc_segment: str, est_segment: str) -> bool:
        """Check if two segment names are comparable"""
        doc_name = doc_segment.lower().replace(" ", "")
        est_name = est_segment.lower().replace(" ", "")
        
        return doc_name in est_name or est_name in doc_name
    
    def _generate_investment_implications(self, ticker: str, analysis: Dict, document_metrics: Dict) -> List[Dict]:
        """Generate investment implications based on comparative analysis"""
        implications = []
        
        # Analyze revenue performance
        if analysis.get("revenue_comparison"):
            implications.append({
                "category": "Revenue Performance",
                "impact": "Positive" if len(analysis["revenue_comparison"]) > 0 else "Neutral",
                "description": "Revenue metrics indicate performance relative to estimates",
                "investment_thesis_impact": "Monitor quarterly trends and estimate accuracy"
            })
        
        # Analyze margin trends
        if analysis.get("margin_comparison"):
            implications.append({
                "category": "Margin Analysis", 
                "impact": "Monitor",
                "description": "Margin performance comparison with analyst expectations",
                "investment_thesis_impact": "Margin trends affect profitability outlook"
            })
        
        # Analyze segment performance
        if analysis.get("segment_comparison"):
            implications.append({
                "category": "Segment Performance",
                "impact": "Strategic",
                "description": "Individual segment performance vs estimates",
                "investment_thesis_impact": "Segment mix changes can drive overall performance"
            })
        
        return implications
