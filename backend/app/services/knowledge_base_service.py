import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
import logging
from .enhanced_svg_parser import create_enhanced_financial_parser

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    def __init__(self, config, database_service, document_service):
        self.config = config
        self.db_service = database_service
        self.doc_service = document_service
        self.financial_parser = create_enhanced_financial_parser(config)
    
    def refresh_knowledge_base(self, ticker: str, force_reprocess: bool = False, 
                              include_investment_data: bool = True, include_estimates: bool = True) -> Dict:
        """Refresh knowledge base for a company"""
        try:
            logger.info(f"Starting knowledge base refresh for {ticker}")
            
            # Get current processing state
            current_state = self.db_service.get_processing_state(ticker) or {
                "company_ticker": ticker.upper(),
                "processed_files": {
                    "past_reports": [],
                    "investment_data": [],
                    "uploaded_documents": [],
                    "financial_statements": []
                },
                "statistics": {
                    "total_chunks": 0,
                    "total_documents": 0
                }
            }
            
            # Process past reports
            reports_processed = self._process_past_reports(ticker, current_state, force_reprocess)
            
            # Process investment data if requested
            investment_processed = 0
            if include_investment_data:
                investment_processed = self._process_investment_data(ticker, current_state)
                
            # Process financial data if requested
            financial_processed = 0
            if include_estimates:
                financial_processed = self._process_financial_data(ticker, current_state, force_reprocess)
            
            # Update statistics
            stats = self.db_service.get_company_stats(ticker)
            current_state["statistics"] = stats
            
            # Save processing state
            self.db_service.update_processing_state(ticker, current_state)
            
            result = {
                "status": "completed",
                "reports_processed": reports_processed,
                "investment_data_processed": investment_processed,
                "financial_statements_processed": financial_processed,
                "total_documents": stats.get("total_documents", 0)
            }
            
            logger.info(f"Completed knowledge base refresh for {ticker}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get investment summary for {ticker}: {str(e)}")
            return {}
    
    def get_knowledge_base_content(self, ticker: str, page: int = 1, page_size: int = 20, 
                                 document_type: Optional[str] = None, search_query: Optional[str] = None) -> Dict:
        """Get knowledge base content with pagination and filtering"""
        try:
            return self.db_service.get_knowledge_base_content(
                ticker, page, page_size, document_type, search_query
            )
        except Exception as e:
            logger.error(f"Failed to get knowledge base content for {ticker}: {str(e)}")
            raise
    
    def get_knowledge_base_document_types(self, ticker: str) -> List[str]:
        """Get available document types in the knowledge base"""
        try:
            collection = self.db_service.get_collection(ticker)
            all_docs = collection.get()
            
            document_types = set()
            for metadata in all_docs["metadatas"]:
                doc_type = metadata.get("document_type")
                if doc_type:
                    document_types.add(doc_type)
            
            return sorted(list(document_types))
        except Exception as e:
            logger.error(f"Failed to get document types for {ticker}: {str(e)}")
            return []
    
    def _process_past_reports(self, ticker: str, state: Dict, force_reprocess: bool) -> int:
        """Process past reports for a company with enhanced table extraction and date parsing"""
        reports_folder = os.path.join(self.config.DATA_ROOT_PATH, "research", ticker.upper(), "past_reports")
        
        if not os.path.exists(reports_folder):
            logger.warning(f"Past reports folder not found: {reports_folder}")
            return 0
        
        processed_files = {item["file_name"]: item for item in state["processed_files"]["past_reports"]}
        newly_processed = 0
        
        # Get all PDF files and sort by date (newest first)
        pdf_files = [f for f in os.listdir(reports_folder) if f.lower().endswith('.pdf')]
        pdf_files_with_dates = []
        
        for file_name in pdf_files:
            report_date = self._extract_report_date(file_name)
            pdf_files_with_dates.append((file_name, report_date))
        
        # Sort by date (newest first)
        pdf_files_with_dates.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
        
        for file_name, report_date in pdf_files_with_dates:
            file_path = os.path.join(reports_folder, file_name)
            file_hash = self.doc_service.calculate_file_hash(file_path)
            
            # Check if already processed
            if not force_reprocess and file_name in processed_files:
                existing_hash = processed_files[file_name].get("file_hash")
                if existing_hash == file_hash:
                    logger.debug(f"Skipping already processed file: {file_name}")
                    continue
            
            try:
                # Process the PDF with enhanced table extraction
                embedded_docs = self._process_historical_report(ticker, file_path, report_date)
                
                # Add to database
                self.db_service.add_documents(ticker, embedded_docs)
                
                # Update state
                file_info = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_hash": file_hash,
                    "report_date": report_date.isoformat() if report_date else None,
                    "processed_date": datetime.utcnow().isoformat() + "Z",
                    "chunk_count": len(embedded_docs),
                    "status": "completed",
                    "is_latest": file_name == pdf_files_with_dates[0][0]  # Mark latest report
                }
                
                # Add or update in state
                updated_files = [item for item in state["processed_files"]["past_reports"] 
                               if item["file_name"] != file_name]
                updated_files.append(file_info)
                state["processed_files"]["past_reports"] = updated_files
                
                newly_processed += 1
                logger.info(f"Processed historical report: {file_name} (date: {report_date}, {len(embedded_docs)} chunks)")
                
            except Exception as e:
                logger.error(f"Failed to process report {file_name}: {str(e)}")
                # Continue processing other files
                continue
        
        return newly_processed
    
    def _process_investment_data(self, ticker: str, state: Dict) -> int:
        """Process investment data JSON files"""
        investment_folder = os.path.join(self.config.DATA_ROOT_PATH, "research", ticker.upper(), "investment_data")
        
        if not os.path.exists(investment_folder):
            logger.warning(f"Investment data folder not found: {investment_folder}")
            return 0
        
        newly_processed = 0
        
        # Mark old investment data as not current
        try:
            collection = self.db_service.get_collection(ticker)
            # This would require updating existing documents, which ChromaDB doesn't support directly
            # For now, we'll rely on timestamps to identify current data
        except:
            pass
        
        for file_name in os.listdir(investment_folder):
            if not file_name.lower().endswith('.json'):
                continue
                
            file_path = os.path.join(investment_folder, file_name)
            
            # Determine data type from filename
            data_type = file_name.replace('.json', '').lower()
            
            try:
                # Process the JSON file
                embedded_docs = self.doc_service.process_investment_data(ticker, data_type, file_path)
                
                # Add to database
                self.db_service.add_documents(ticker, embedded_docs)
                
                # Update state
                file_info = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "processed_date": datetime.utcnow().isoformat() + "Z",
                    "status": "completed"
                }
                
                # Add or update in state
                updated_files = [item for item in state["processed_files"]["investment_data"] 
                               if item["file_name"] != file_name]
                updated_files.append(file_info)
                state["processed_files"]["investment_data"] = updated_files
                
                newly_processed += 1
                logger.info(f"Processed investment data: {file_name}")
                
            except Exception as e:
                logger.error(f"Failed to process investment data {file_name}: {str(e)}")
                continue
        
        return newly_processed
    
    def get_all_companies(self) -> List[Dict]:
        """Get all companies with their statistics"""
        tickers = self.db_service.get_all_companies()
        companies = []
        
        for ticker in tickers:
            try:
                stats = self.db_service.get_company_stats(ticker)
                processing_state = self.db_service.get_processing_state(ticker)
                
                # Get actual count of historical report files from processing state
                historical_reports_count = 0
                if processing_state and "processed_files" in processing_state:
                    past_reports = processing_state["processed_files"].get("past_reports", [])
                    historical_reports_count = len(past_reports)
                
                company_info = {
                    "ticker": ticker,
                    "company_name": f"{ticker} Inc.",  # Could be enhanced with actual company names
                    "knowledge_base_status": stats.get("status", "unknown"),
                    "last_updated": processing_state.get("last_updated") if processing_state else None,
                    "stats": {
                        "total_reports": historical_reports_count,  # Number of historical report files
                        "total_chunks": stats.get("total_documents", 0),  # Total document chunks
                        "last_refresh": processing_state.get("last_updated") if processing_state else None
                    }
                }
                
                companies.append(company_info)
                
            except Exception as e:
                logger.error(f"Failed to get company info for {ticker}: {str(e)}")
                continue
        
        return companies
    
    def get_company_detail(self, ticker: str) -> Optional[Dict]:
        """Get detailed information for a company"""
        try:
            stats = self.db_service.get_company_stats(ticker)
            processing_state = self.db_service.get_processing_state(ticker)
            
            if stats.get("status") == "empty":
                return None
            
            # Get investment data
            investment_summary = self._get_investment_summary(ticker)
            
            company_detail = {
                "ticker": ticker,
                "company_name": f"{ticker} Inc.",
                "knowledge_base_status": stats.get("status", "unknown"),
                "last_updated": processing_state.get("last_updated") if processing_state else None,
                "stats": {
                    "total_documents": stats.get("total_documents", 0),
                    "processed_files": [item["file_name"] for item in processing_state.get("processed_files", {}).get("past_reports", [])] if processing_state else [],
                    "investment_data_files": [item["file_name"] for item in processing_state.get("processed_files", {}).get("investment_data", [])] if processing_state else []
                },
                "investment_summary": investment_summary
            }
            
            return company_detail
            
        except Exception as e:
            logger.error(f"Failed to get company detail for {ticker}: {str(e)}")
            return None
    
    def _get_investment_summary(self, ticker: str) -> Dict:
        """Get investment summary for a company"""
        try:
            # Query for investment thesis data
            results = self.db_service.query_similar_documents(
                ticker, 
                [0.0] * 1536,  # Dummy embedding for metadata-only query
                n_results=1,
                where_filter={"$and": [
                    {"document_type": "investment_data"},
                    {"data_type": "investmentthesis"}
                ]}
            )
            
            if results["ids"] and len(results["ids"][0]) > 0:
                metadata = results["metadatas"][0][0]
                return {
                    "rating": metadata.get("rating", "N/A"),
                    "target_price": metadata.get("target_price", "N/A"),
                    "last_updated": metadata.get("processed_date", "N/A")
                }
            else:
                return {
                    "rating": "N/A",
                    "target_price": "N/A", 
                    "last_updated": "N/A"
                }
                
        except Exception as e:
            logger.error(f"Failed to get investment summary for {ticker}: {str(e)}")
            return {"rating": "N/A", "target_price": "N/A", "last_updated": "N/A"}
    
    def _extract_report_date(self, file_name: str) -> Optional[datetime]:
        """Extract report date from filename
        
        Supports formats like:
        - AAPL_20240721_1234.pdf (YYYYMMDD)
        - AAPL_2024-07-21_analysis.pdf
        - report_20240721.pdf
        """
        # Common date patterns in filenames
        date_patterns = [
            r'(\d{4})(\d{2})(\d{2})',  # YYYYMMDD
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{4})_(\d{2})_(\d{2})',  # YYYY_MM_DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, file_name)
            if match:
                try:
                    year, month, day = match.groups()
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue
        
        logger.warning(f"Could not extract date from filename: {file_name}")
        return None
    
    def _process_historical_report(self, ticker: str, file_path: str, report_date: Optional[datetime]) -> List[Dict]:
        """Process historical report with enhanced metadata and table extraction"""
        file_name = os.path.basename(file_path)
        
        # Use the enhanced PDF processing
        embedded_docs = self.doc_service.process_pdf_report(ticker, file_path)
        
        # Enhance metadata with historical context
        for doc in embedded_docs:
            doc["metadata"].update({
                "report_date": report_date.isoformat() if report_date else None,
                "document_age_days": (datetime.utcnow() - report_date).days if report_date else None,
                "is_historical": True,
                "historical_financial_data": True,  # Flag for containing analyst estimates/metrics
                "content_priority": self._calculate_content_priority(doc["document"], report_date)
            })
            
            # Add special handling for financial tables in historical reports
            if any(keyword in doc["document"].lower() for keyword in [
                "target price", "price target", "rating", "buy", "sell", "hold",
                "estimates", "consensus", "forecast", "guidance"
            ]):
                doc["metadata"]["contains_analyst_estimates"] = True
                doc["metadata"]["content_priority"] += 0.2  # Boost priority for estimate content
        
        return embedded_docs
    
    def _calculate_content_priority(self, content: str, report_date: Optional[datetime]) -> float:
        """Calculate content priority based on recency and content type"""
        base_priority = 0.5
        
        # Recency boost (newer reports get higher priority)
        if report_date:
            days_old = (datetime.utcnow() - report_date).days
            if days_old <= 30:  # Last month
                base_priority += 0.3
            elif days_old <= 90:  # Last quarter
                base_priority += 0.2
            elif days_old <= 365:  # Last year
                base_priority += 0.1
        
        # Content type boosts
        content_lower = content.lower()
        
        # Financial metrics and estimates
        if any(keyword in content_lower for keyword in [
            "target price", "eps estimate", "revenue estimate", "rating",
            "valuation", "dcf", "price target", "fair value"
        ]):
            base_priority += 0.3
        
        # Key financial tables
        if any(keyword in content_lower for keyword in [
            "income statement", "balance sheet", "cash flow",
            "financial metrics", "key metrics"
        ]):
            base_priority += 0.2
        
        # Strategic insights
        if any(keyword in content_lower for keyword in [
            "investment thesis", "key risks", "catalysts",
            "competitive advantage", "moat"
        ]):
            base_priority += 0.1
        
        return min(base_priority, 1.0)
    
    def _process_financial_data(self, ticker: str, state: Dict, force_reprocess: bool = False) -> int:
        """Process comprehensive financial data from SVG files for a company"""
        try:
            logger.info(f"Processing financial statements for {ticker}")
            
            # Parse comprehensive financial data using enhanced parser
            financial_data = self.financial_parser.parse_financial_statements(ticker)
            
            if not financial_data or not financial_data.get('last_updated'):
                logger.warning(f"No financial data found for {ticker}")
                return 0
            
            # Check if already processed and up-to-date
            processed_financial = state["processed_files"].get("financial_statements", [])
            if not force_reprocess and processed_financial:
                last_processed = processed_financial[0].get("last_updated")
                if last_processed and float(last_processed) >= financial_data['last_updated']:
                    logger.debug(f"Financial data already up-to-date for {ticker}")
                    return 0
            
            # Create embeddings for comprehensive financial data
            raw_docs = self._create_financial_embeddings(ticker, financial_data)
            
            # Convert to proper format and generate embeddings
            embedded_docs = []
            for i, doc in enumerate(raw_docs):
                try:
                    # Generate embedding for the content using document service
                    embedding = self.doc_service.ai_service.generate_embedding(doc["content"])
                    
                    # Create properly formatted document
                    formatted_doc = {
                        "id": f"{ticker.lower()}_financial_{i}_{int(datetime.utcnow().timestamp())}",
                        "embedding": embedding,
                        "metadata": doc["metadata"],
                        "document": doc["content"]
                    }
                    
                    embedded_docs.append(formatted_doc)
                    
                except Exception as e:
                    logger.error(f"Failed to create embedding for financial document {i}: {str(e)}")
                    continue
            
            if not embedded_docs:
                logger.error(f"No valid embeddings created for {ticker} financial data")
                return 0
            
            # Remove old financial data from database
            self._remove_old_financial_data(ticker)
            
            # Add new financial data to database
            self.db_service.add_documents(ticker, embedded_docs)
            
            # Update processing state
            financial_info = {
                "data_type": "financial_statements",
                "last_updated": financial_data['last_updated'],
                "processed_date": datetime.utcnow().timestamp(),
                "chunk_count": len(embedded_docs),
                "statements_parsed": financial_data['parsing_summary']['statements_parsed'],
                "total_metrics": financial_data['parsing_summary']['total_metrics'],
                "status": "completed"
            }
            
            # Replace financial statements in processed files list
            state["processed_files"]["financial_statements"] = [financial_info]
            
            logger.info(f"Successfully processed financial data for {ticker}: {len(embedded_docs)} chunks")
            return len(embedded_docs)
            
        except Exception as e:
            logger.error(f"Failed to process financial data for {ticker}: {str(e)}")
            return 0
    
    def _create_financial_embeddings(self, ticker: str, financial_data: Dict) -> List[Dict]:
        """
        Create embeddings for comprehensive financial data.
        Optimized for embedding token limits while maintaining GenAI analysis capability.
        Creates focused, compact documents suitable for quarterly analysis context.
        """
        embedded_docs = []
        
        # Process each financial statement type
        statement_types = {
            'balance_sheet': 'Balance Sheet',
            'income_statement': 'Income Statement',
            'cash_flow': 'Cash Flow Statement', 
            'margin_analysis': 'Margin Analysis'
        }
        
        for statement_key, statement_name in statement_types.items():
            statement_data = financial_data.get(statement_key, {})
            if not statement_data or not statement_data.get('metrics'):
                continue
            
            # Extract key information
            periods = statement_data.get('periods', [])
            metrics = statement_data.get('metrics', {})
            analysis = statement_data.get('analysis', {})
            
            # Create focused summary for embedding (token-optimized, estimates-prioritized)
            key_metrics = self._extract_key_metrics_for_embedding(metrics, statement_key)
            recent_periods = periods[-8:] if len(periods) > 8 else periods  # Last 8 periods
            
            # Separate estimates from actual data for better GenAI context
            estimates_data, actual_data = self._separate_estimates_and_actuals(key_metrics, recent_periods)
            
            # Create compact structured content optimized for quarterly comparison
            structured_content = {
                "statement_type": statement_name,
                "ticker": ticker,
                "last_updated": datetime.fromtimestamp(financial_data.get('last_updated', 0)).strftime('%Y-%m-%d'),
                "recent_periods": recent_periods,
                "estimates_data": estimates_data,  # Critical for quarterly comparison
                "actual_data": actual_data,       # Historical actuals for context
                "summary_stats": {
                    "total_periods_available": len(periods),
                    "estimates_metrics_count": len([m for m in key_metrics.keys() if self._has_estimates_periods(key_metrics[m])]),
                    "actual_metrics_count": len([m for m in key_metrics.keys() if not self._has_estimates_periods(key_metrics[m])]),
                    "latest_period": periods[-1] if periods else None,
                    "estimates_periods": [p for p in recent_periods if p.endswith('E') or 'estimate' in p.lower()],
                    "actual_periods": [p for p in recent_periods if not (p.endswith('E') or 'estimate' in p.lower())],
                    "years_covered": list(set([p[-4:] for p in recent_periods if p[-4:].isdigit()]))
                }
            }
            
            # Add trend analysis for key metrics (compact format)
            if analysis:
                structured_content["trends"] = self._create_compact_trend_analysis(key_metrics, recent_periods)
            
            # Add comparative insights (limited to avoid token overflow)
            if statement_key in financial_data.get('comparative_analysis', {}):
                comp_data = financial_data['comparative_analysis'][statement_key]
                structured_content["insights"] = self._extract_key_insights(comp_data)
            
            # Store as compact JSON
            document = {
                "content": json.dumps(structured_content, separators=(',', ':'), default=str),  # Compact JSON
                "metadata": {
                    "ticker": ticker,
                    "document_type": f"financial_statement_{statement_key}",
                    "statement_type": statement_name,
                    "source": "enhanced_svg_parser",
                    "periods_count": len(recent_periods),
                    "metrics_count": len(key_metrics),
                    "last_updated": financial_data.get('last_updated'),
                    "parsing_timestamp": datetime.utcnow().isoformat(),
                    "content_format": "compact_json",
                    "genai_optimized": True,
                    "embedding_optimized": True
                }
            }
            
            logger.info(f"Created compact JSON document for {ticker} {statement_name} with {len(recent_periods)} periods and {len(key_metrics)} key metrics")
            embedded_docs.append(document)
        
        # Add overall comparative analysis as a separate compact document
        if financial_data.get('comparative_analysis'):
            parsing_summary = financial_data.get('parsing_summary', {})
            
            # Create highly summarized comparative analysis
            comp_structured_content = {
                "analysis_type": "financial_summary", 
                "ticker": ticker,
                "last_updated": datetime.fromtimestamp(financial_data.get('last_updated', 0)).strftime('%Y-%m-%d'),
                "overview": {
                    "statements": parsing_summary.get('statements_parsed', []),
                    "total_metrics": parsing_summary.get('total_metrics', 0),
                    "total_periods": parsing_summary.get('total_periods', 0)
                },
                "key_insights": self._extract_top_financial_insights(financial_data['comparative_analysis'])
            }
            
            comp_document = {
                "content": json.dumps(comp_structured_content, separators=(',', ':'), default=str),
                "metadata": {
                    "ticker": ticker,
                    "document_type": "financial_comparative_analysis",
                    "source": "enhanced_svg_parser",
                    "last_updated": financial_data.get('last_updated'),
                    "parsing_timestamp": datetime.utcnow().isoformat(),
                    "content_format": "compact_json",
                    "genai_optimized": True,
                    "embedding_optimized": True
                }
            }
            
            logger.info(f"Created compact comparative analysis document for {ticker}")
            embedded_docs.append(comp_document)
        
        logger.info(f"Created {len(embedded_docs)} embedding-optimized financial documents for {ticker}")
        return embedded_docs
    
    def _remove_old_financial_data(self, ticker: str):
        """Remove old financial data from the database"""
        try:
            collection = self.db_service.get_collection(ticker)
            
            # Get all documents
            all_docs = collection.get()
            
            # Find documents with financial statement data
            ids_to_delete = []
            for i, metadata in enumerate(all_docs["metadatas"]):
                doc_type = metadata.get("document_type", "")
                if (doc_type.startswith("financial_statement_") or 
                    doc_type == "financial_comparative_analysis" or
                    doc_type in ["estimates_data", "segment_estimates"]):  # Remove old estimates too
                    ids_to_delete.append(all_docs["ids"][i])
            
            # Delete old financial documents
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                logger.info(f"Removed {len(ids_to_delete)} old financial documents for {ticker}")
            else:
                logger.info(f"No old financial documents found for {ticker}")
                
        except Exception as e:
            logger.error(f"Error removing old financial data for {ticker}: {str(e)}")
            # Continue processing even if cleanup fails

    
    def get_financial_data(self, ticker: str) -> Dict:
        """Get comprehensive financial data for a company from stored embeddings (enhanced parser format)"""
        try:
            # Get financial documents from database
            collection = self.db_service.get_collection(ticker)
            
            # Fetch all financial statement documents and comparative analysis
            financial_docs = collection.get(
                where={"document_type": {"$in": [
                    "financial_statement_balance_sheet",
                    "financial_statement_income_statement", 
                    "financial_statement_cash_flow",
                    "financial_statement_margin_analysis",
                    "financial_comparative_analysis"
                ]}}
            )
            
            if not financial_docs["ids"]:
                logger.warning(f"No processed financial data found for {ticker}")
                return {}
            
            # Reconstruct financial data from stored documents
            financial_data = {
                "ticker": ticker.upper(),
                "last_updated": None,
                "balance_sheet": {},
                "income_statement": {},
                "cash_flow": {},
                "margin_analysis": {},
                "comparative_analysis": {}
            }
            
            # Process each document to rebuild the financial data structure
            for i, metadata in enumerate(financial_docs["metadatas"]):
                doc_content = financial_docs["documents"][i]
                doc_type = metadata.get("document_type")
                statement_type = metadata.get("statement_type")
                
                # Update last_updated with the most recent timestamp
                doc_last_updated = metadata.get("last_updated")
                if doc_last_updated and (not financial_data["last_updated"] or doc_last_updated > financial_data["last_updated"]):
                    financial_data["last_updated"] = doc_last_updated
                
                # Parse the content to extract structured data
                if doc_type == "financial_comparative_analysis":
                    # This contains the comprehensive analysis
                    financial_data["comparative_analysis"] = {
                        "content": doc_content,
                        "metadata": metadata,
                        "analysis_types": metadata.get("analysis_types", "").split(",") if metadata.get("analysis_types") else [],
                        "statements_included": metadata.get("statements_included", "").split(",") if metadata.get("statements_included") else []
                    }
                elif doc_type.startswith("financial_statement_"):
                    # Individual financial statement
                    statement_key = doc_type.replace("financial_statement_", "")
                    financial_data[statement_key] = {
                        "content": doc_content,
                        "metadata": metadata,
                        "statement_type": statement_type,
                        "periods_count": metadata.get("periods_count", 0),
                        "metrics_count": metadata.get("metrics_count", 0)
                    }
            
            return financial_data
            
        except Exception as e:
            logger.error(f"Failed to get financial data for {ticker}: {str(e)}")
            return {}

    def get_estimates_data(self, ticker: str) -> Dict:
        """Get estimates data for a company (legacy method for backward compatibility)"""
        try:
            collection = self.db_service.get_collection(ticker)
            
            # Query for estimates documents (legacy format only)
            estimates_docs = collection.get(
                where={"document_type": {"$in": ["estimates_data", "segment_estimates"]}}
            )
            
            if not estimates_docs["ids"]:
                logger.warning(f"No processed estimates data found for {ticker}")
                return {}
            
            # Reconstruct estimates data from stored documents
            estimates_data = {
                "ticker": ticker.upper(),
                "last_updated": None,
                "income_statement": {},
                "balance_sheet": {},
                "cash_flow": {}
            }
            
            # Process each document to rebuild the estimates structure
            for i, metadata in enumerate(estimates_docs["metadatas"]):
                doc_content = estimates_docs["documents"][i]
                doc_type = metadata.get("document_type")
                statement_type = metadata.get("statement_type")
                
                # Update last_updated with the most recent timestamp
                doc_last_updated = metadata.get("last_updated")
                if doc_last_updated and (not estimates_data["last_updated"] or doc_last_updated > estimates_data["last_updated"]):
                    estimates_data["last_updated"] = doc_last_updated
                
                # Initialize statement data if not exists
                if statement_type and statement_type not in estimates_data:
                    estimates_data[statement_type] = {
                        "segment_data": {},
                        "margins": {},
                        "quarterly_data": [],
                        "estimates": {}
                    }
                
                # Process document content to extract structured data
                if doc_type == "estimates_data" and statement_type:
                    # This is a main estimates document - extract general info
                    estimates_data[statement_type]["document_content"] = doc_content
                    
                elif doc_type == "segment_estimates" and statement_type:
                    # This is a segment-specific document
                    segment_name = metadata.get("segment_name")
                    if segment_name:
                        if "segment_data" not in estimates_data[statement_type]:
                            estimates_data[statement_type]["segment_data"] = {}
                        estimates_data[statement_type]["segment_data"][segment_name] = {
                            "content": doc_content,
                            "metadata": metadata
                        }
            
            return estimates_data
            
        except Exception as e:
            logger.error(f"Failed to get estimates data for {ticker}: {str(e)}")
            return {}
    
    def get_available_financial_document_types(self, ticker: str) -> Dict[str, List[str]]:
        """Get available financial document types for debugging and verification"""
        try:
            collection = self.db_service.get_collection(ticker)
            all_docs = collection.get()
            
            # Group documents by type
            document_types = {
                "enhanced_financial": [],
                "old_estimates": [],
                "other": []
            }
            
            enhanced_types = [
                "financial_statement_balance_sheet",
                "financial_statement_income_statement", 
                "financial_statement_cash_flow",
                "financial_statement_margin_analysis",
                "financial_comparative_analysis"
            ]
            
            old_types = ["estimates_data", "segment_estimates"]
            
            for metadata in all_docs["metadatas"]:
                doc_type = metadata.get("document_type")
                if doc_type in enhanced_types:
                    document_types["enhanced_financial"].append(doc_type)
                elif doc_type in old_types:
                    document_types["old_estimates"].append(doc_type)
                elif doc_type:
                    document_types["other"].append(doc_type)
            
            # Remove duplicates
            for key in document_types:
                document_types[key] = list(set(document_types[key]))
            
            logger.info(f"Available financial document types for {ticker}: {document_types}")
            return document_types
            
        except Exception as e:
            logger.error(f"Failed to get document types for {ticker}: {str(e)}")
            return {"enhanced_financial": [], "old_estimates": [], "other": []}

    def get_comprehensive_financial_data(self, ticker: str) -> Optional[Dict]:
        """
        Get comprehensive financial data for document analysis.
        This method retrieves enhanced financial statement data (Balance Sheet, Income Statement, 
        Cash Flow, Margin Analysis) to be used directly for GenAI-based earnings analysis and comparisons.
        """
        try:
            logger.info(f"Retrieving comprehensive financial data for {ticker}")
            collection = self.db_service.get_collection(ticker)
            
            # Define enhanced financial document types
            financial_doc_types = [
                "financial_statement_balance_sheet",
                "financial_statement_income_statement", 
                "financial_statement_cash_flow",
                "financial_statement_margin_analysis",
                "financial_comparative_analysis"
            ]
            
            comprehensive_data = {
                "ticker": ticker,
                "last_updated": None,
                "balance_sheet": {},
                "income_statement": {},
                "cash_flow": {},
                "margin_analysis": {},
                "comparative_analysis": {},
                "has_data": False,
                "data_format": "structured_json"
            }
            
            # Retrieve each type of financial statement
            for doc_type in financial_doc_types:
                try:
                    results = collection.get(
                        where={"document_type": doc_type}
                    )
                    
                    if results["documents"] and results["documents"]:
                        document_content = results["documents"][0]
                        metadata = results["metadatas"][0]
                        
                        # Parse the JSON content
                        try:
                            if metadata.get("content_format") in ["structured_json", "compact_json"]:
                                # New structured JSON format
                                financial_content = json.loads(document_content)
                            else:
                                # Fallback for old text format - skip or convert
                                logger.warning(f"Old text format found for {doc_type}, skipping...")
                                continue
                            
                            # Update last_updated with the most recent timestamp
                            doc_last_updated = metadata.get("last_updated")
                            if doc_last_updated and (not comprehensive_data["last_updated"] or 
                                                   doc_last_updated > comprehensive_data["last_updated"]):
                                comprehensive_data["last_updated"] = doc_last_updated
                            
                            # Store data by statement type
                            if doc_type == "financial_statement_balance_sheet":
                                comprehensive_data["balance_sheet"] = financial_content
                                comprehensive_data["has_data"] = True
                            elif doc_type == "financial_statement_income_statement":
                                comprehensive_data["income_statement"] = financial_content
                                comprehensive_data["has_data"] = True
                            elif doc_type == "financial_statement_cash_flow":
                                comprehensive_data["cash_flow"] = financial_content
                                comprehensive_data["has_data"] = True
                            elif doc_type == "financial_statement_margin_analysis":
                                comprehensive_data["margin_analysis"] = financial_content
                                comprehensive_data["has_data"] = True
                            elif doc_type == "financial_comparative_analysis":
                                comprehensive_data["comparative_analysis"] = financial_content
                                comprehensive_data["has_data"] = True
                            
                            logger.info(f"Successfully retrieved structured {doc_type} data for {ticker}")
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse {doc_type} content as JSON: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Failed to retrieve {doc_type} for {ticker}: {str(e)}")
                    continue
            
            if comprehensive_data["has_data"]:
                logger.info(f"Successfully retrieved comprehensive structured financial data for {ticker}")
                return comprehensive_data
            else:
                logger.warning(f"No comprehensive financial data found for {ticker}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get comprehensive financial data for {ticker}: {str(e)}")
            return None

    def _extract_key_metrics_for_embedding(self, metrics: Dict, statement_type: str) -> Dict:
        """
        Extract metrics for embedding, prioritizing estimates data and including all metrics.
        Uses smart period limiting and data compression instead of metric filtering.
        """
        optimized_metrics = {}
        estimates_metrics = {}
        actual_metrics = {}
        
        # First, separate estimates from actuals for all metrics (no filtering by name)
        for metric_name, metric_data in metrics.items():
            if isinstance(metric_data, dict):
                # Check if this metric has estimates periods
                has_estimates = any(
                    period.endswith('E') or 'estimate' in period.lower() or 'E' in period
                    for period in metric_data.keys()
                )
                
                if has_estimates:
                    estimates_metrics[metric_name] = metric_data
                else:
                    actual_metrics[metric_name] = metric_data
        
        token_budget = 6500  # Conservative budget for embeddings
        current_tokens = 0
        
        # ALWAYS include ALL estimates metrics (with period limiting if needed)
        for metric_name, metric_data in estimates_metrics.items():
            # For estimates, include all estimate periods but limit actual historical data
            optimized_metric_data = {}
            estimate_periods = {}
            actual_periods = {}
            
            # Separate estimate and actual periods
            for period, value in metric_data.items():
                if period.endswith('E') or 'estimate' in period.lower() or 'E' in period:
                    estimate_periods[period] = value
                else:
                    actual_periods[period] = value
            
            # Include ALL estimate periods (these are critical)
            optimized_metric_data.update(estimate_periods)
            
            # For actual periods in estimates metrics, keep recent ones for context
            if actual_periods:
                sorted_actual_periods = sorted(actual_periods.keys(), reverse=True)
                # Keep last 4 actual periods for context with estimates
                for period in sorted_actual_periods[:4]:
                    optimized_metric_data[period] = actual_periods[period]
            
            optimized_metrics[metric_name] = optimized_metric_data
            
            # Rough token estimation
            estimated_tokens = len(str(metric_name)) + len(str(optimized_metric_data)) // 4
            current_tokens += estimated_tokens
        
        logger.info(f"Included ALL {len(estimates_metrics)} estimates metrics, estimated tokens: {current_tokens}")
        
        # Include ALL actual metrics with smart period limiting
        remaining_budget = token_budget - current_tokens
        
        for metric_name, metric_data in actual_metrics.items():
            # For pure actual metrics, limit periods more aggressively to save tokens
            if isinstance(metric_data, dict):
                # Keep last 6 periods for actual-only metrics
                sorted_periods = sorted(metric_data.keys(), reverse=True)
                limited_periods = sorted_periods[:6] if len(sorted_periods) > 6 else sorted_periods
                
                optimized_metric_data = {
                    period: metric_data[period] for period in limited_periods
                }
            else:
                optimized_metric_data = metric_data
            
            # Estimate token usage for this metric
            estimated_tokens = len(str(metric_name)) + len(str(optimized_metric_data)) // 4
            
            # Include if within budget, or if it's a small metric
            if current_tokens + estimated_tokens < remaining_budget or estimated_tokens < 100:
                optimized_metrics[metric_name] = optimized_metric_data
                current_tokens += estimated_tokens
            else:
                # If we're over budget, include with even more limited periods
                if isinstance(metric_data, dict) and len(metric_data) > 2:
                    sorted_periods = sorted(metric_data.keys(), reverse=True)
                    very_limited_periods = sorted_periods[:2]  # Just last 2 periods
                    minimal_data = {period: metric_data[period] for period in very_limited_periods}
                    minimal_tokens = len(str(metric_name)) + len(str(minimal_data)) // 4
                    
                    if current_tokens + minimal_tokens < token_budget:
                        optimized_metrics[metric_name] = minimal_data
                        current_tokens += minimal_tokens
                else:
                    # Very small metric, include as-is
                    optimized_metrics[metric_name] = optimized_metric_data
                    current_tokens += estimated_tokens
        
        logger.info(f"Final: ALL {len(optimized_metrics)} metrics included (estimates: {len(estimates_metrics)}, actual: {len(optimized_metrics) - len(estimates_metrics)}), estimated tokens: {current_tokens}")
        return optimized_metrics

    def _create_compact_trend_analysis(self, metrics: Dict, periods: List) -> Dict:
        """Create compact trend analysis for all metrics, prioritizing estimates data"""
        trends = {}
        
        # Process ALL metrics but prioritize those with estimates
        estimates_metrics = []
        other_metrics = []
        
        for metric_name, metric_data in metrics.items():
            if self._has_estimates_periods(metric_data):
                estimates_metrics.append((metric_name, metric_data))
            else:
                other_metrics.append((metric_name, metric_data))
        
        # Process estimates metrics first (most important for quarterly comparison)
        processed_count = 0
        token_budget = 1500  # Budget for trend analysis section
        current_tokens = 0
        
        for metric_name, metric_data in estimates_metrics:
            if current_tokens > token_budget:  # Use token budget instead of count limit
                break
                
            if isinstance(metric_data, dict) and len(metric_data) >= 2:
                trend_info = self._calculate_metric_trends(metric_name, metric_data)
                if trend_info:
                    trends[metric_name] = trend_info
                    current_tokens += len(str(trend_info)) // 4
                    processed_count += 1
        
        # Process remaining actual metrics with available budget
        remaining_budget = token_budget - current_tokens
        for metric_name, metric_data in other_metrics:
            if current_tokens > token_budget:
                break
                
            if isinstance(metric_data, dict) and len(metric_data) >= 2:
                trend_info = self._calculate_metric_trends(metric_name, metric_data)
                if trend_info:
                    trend_size = len(str(trend_info)) // 4
                    if current_tokens + trend_size <= token_budget:
                        trends[metric_name] = trend_info
                        current_tokens += trend_size
                        processed_count += 1
        
        logger.info(f"Created trends for {processed_count} metrics (estimates priority), estimated tokens: {current_tokens}")
        return trends

    def _calculate_metric_trends(self, metric_name: str, metric_data: Dict) -> Dict:
        """Calculate trends for a single metric, handling estimates and actuals separately"""
        # Separate estimates and actual values for trend analysis
        est_values = []
        est_periods = []
        actual_values = []
        actual_periods = []
        
        for period in sorted(metric_data.keys()):
            if period in metric_data:
                value_info = metric_data[period]
                value = None
                if isinstance(value_info, dict) and 'value' in value_info:
                    value = value_info['value']
                elif isinstance(value_info, (int, float)):
                    value = value_info
                
                if value is not None and isinstance(value, (int, float)):
                    if period.endswith('E') or 'estimate' in period.lower():
                        est_values.append(value)
                        est_periods.append(period)
                    else:
                        actual_values.append(value)
                        actual_periods.append(period)
        
        trend_info = {}
        
        # Add estimates trend if available
        if len(est_values) >= 2:
            trend_info["estimates"] = {
                "direction": "up" if est_values[-1] > est_values[0] else "down",
                "latest": est_values[-1],
                "change_pct": round(((est_values[-1] - est_values[0]) / abs(est_values[0])) * 100, 1) if est_values[0] != 0 else 0,
                "periods": len(est_periods)
            }
        
        # Add actual trend if available
        if len(actual_values) >= 2:
            trend_info["actual"] = {
                "direction": "up" if actual_values[-1] > actual_values[0] else "down", 
                "latest": actual_values[-1],
                "change_pct": round(((actual_values[-1] - actual_values[0]) / abs(actual_values[0])) * 100, 1) if actual_values[0] != 0 else 0,
                "periods": len(actual_periods)
            }
        
        # If neither estimates nor actuals, try all values together
        if not trend_info:
            all_values = []
            for period in sorted(metric_data.keys()):
                if period in metric_data:
                    value_info = metric_data[period]
                    if isinstance(value_info, dict) and 'value' in value_info:
                        all_values.append(value_info['value'])
                    elif isinstance(value_info, (int, float)):
                        all_values.append(value_info)
            
            if len(all_values) >= 2 and all(isinstance(v, (int, float)) for v in all_values):
                trend_info["combined"] = {
                    "direction": "up" if all_values[-1] > all_values[0] else "down",
                    "latest": all_values[-1],
                    "change_pct": round(((all_values[-1] - all_values[0]) / abs(all_values[0])) * 100, 1) if all_values[0] != 0 else 0
                }
        
        return trend_info if trend_info else None

    def _extract_key_insights(self, comp_analysis: Dict) -> Dict:
        """Extract key insights from comparative analysis, keeping it compact"""
        insights = {}
        
        # Extract top 3 insights only to stay within token limits
        insight_count = 0
        for key, value in comp_analysis.items():
            if insight_count >= 3:
                break
            
            if isinstance(value, dict) and 'summary' in value:
                insights[key] = value['summary']
                insight_count += 1
            elif isinstance(value, str) and len(value) < 200:  # Only short insights
                insights[key] = value
                insight_count += 1
        
        return insights

    def _extract_top_financial_insights(self, comparative_analysis: Dict) -> Dict:
        """Extract top-level financial insights for comparative analysis document"""
        insights = {}
        
        # Extract key insights from different analysis types
        for analysis_type, analysis_data in list(comparative_analysis.items())[:3]:  # Limit to 3 types
            if isinstance(analysis_data, dict):
                # Extract summary or key metrics
                if 'key_metrics' in analysis_data:
                    insights[analysis_type] = {
                        "type": analysis_type.replace('_', ' ').title(),
                        "metrics_count": len(analysis_data['key_metrics']) if isinstance(analysis_data['key_metrics'], dict) else 0
                    }
                elif 'summary' in analysis_data:
                    insights[analysis_type] = {
                        "type": analysis_type.replace('_', ' ').title(), 
                        "summary": str(analysis_data['summary'])[:100] + "..." if len(str(analysis_data['summary'])) > 100 else str(analysis_data['summary'])
                    }
        
        return insights

    def _separate_estimates_and_actuals(self, metrics: Dict, periods: List) -> tuple:
        """Separate estimates data from actual data for better GenAI context"""
        estimates_data = {}
        actual_data = {}
        
        for metric_name, metric_data in metrics.items():
            if isinstance(metric_data, dict):
                estimates_periods = {}
                actual_periods = {}
                
                for period, value in metric_data.items():
                    if period.endswith('E') or 'estimate' in period.lower() or 'E' in period:
                        estimates_periods[period] = value
                    else:
                        actual_periods[period] = value
                
                if estimates_periods:
                    estimates_data[metric_name] = estimates_periods
                if actual_periods:
                    actual_data[metric_name] = actual_periods
        
        return estimates_data, actual_data
    
    def _has_estimates_periods(self, metric_data: Dict) -> bool:
        """Check if a metric has any estimates periods"""
        if not isinstance(metric_data, dict):
            return False
        
        return any(
            period.endswith('E') or 'estimate' in period.lower() or 'E' in period
            for period in metric_data.keys()
        )
