import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
import logging
from .estimates_parser import create_estimates_parser

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    def __init__(self, config, database_service, document_service):
        self.config = config
        self.db_service = database_service
        self.doc_service = document_service
        self.estimates_parser = create_estimates_parser(config)
    
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
                    "estimates_data": []
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
                
            # Process estimates data if requested
            estimates_processed = 0
            if include_estimates:
                estimates_processed = self._process_estimates_data(ticker, current_state, force_reprocess)
            
            # Update statistics
            stats = self.db_service.get_company_stats(ticker)
            current_state["statistics"] = stats
            
            # Save processing state
            self.db_service.update_processing_state(ticker, current_state)
            
            result = {
                "status": "completed",
                "reports_processed": reports_processed,
                "investment_data_processed": investment_processed,
                "estimates_processed": estimates_processed,
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
    
    def _process_estimates_data(self, ticker: str, state: Dict, force_reprocess: bool = False) -> int:
        """Process estimates data from SVG files for a company"""
        try:
            logger.info(f"Processing estimates data for {ticker}")
            
            # Parse estimates data from SVG files
            estimates_data = self.estimates_parser.parse_estimates_folder(ticker)
            
            if not estimates_data or not estimates_data.get('last_updated'):
                logger.warning(f"No estimates data found for {ticker}")
                return 0
            
            # Check if already processed and up-to-date
            processed_estimates = state["processed_files"].get("estimates_data", [])
            if not force_reprocess and processed_estimates:
                last_processed = processed_estimates[0].get("last_updated")
                if last_processed and float(last_processed) >= estimates_data['last_updated']:
                    logger.debug(f"Estimates data already up-to-date for {ticker}")
                    return 0
            
            # Create embeddings for estimates data
            embedded_docs = self._create_estimates_embeddings(ticker, estimates_data)
            
            # Remove old estimates data from database
            self._remove_old_estimates_data(ticker)
            
            # Add new estimates data to database
            self.db_service.add_documents(ticker, embedded_docs)
            
            # Update processing state
            estimates_info = {
                "data_type": "estimates",
                "last_updated": estimates_data['last_updated'],
                "processed_date": datetime.utcnow().timestamp(),
                "chunk_count": len(embedded_docs),
                "status": "completed"
            }
            
            state["processed_files"]["estimates_data"] = [estimates_info]
            
            logger.info(f"Successfully processed estimates data for {ticker}: {len(embedded_docs)} chunks")
            return len(embedded_docs)
            
        except Exception as e:
            logger.error(f"Failed to process estimates data for {ticker}: {str(e)}")
            return 0
    
    def _create_estimates_embeddings(self, ticker: str, estimates_data: Dict) -> List[Dict]:
        """Create embeddings for estimates data"""
        embedded_docs = []
        
        # Process each financial statement
        for statement_type in ['income_statement', 'balance_sheet', 'cash_flow']:
            statement_data = estimates_data.get(statement_type, {})
            if not statement_data:
                continue
                
            # Create comprehensive text representation of the data
            content_parts = []
            content_parts.append(f"Financial Estimates Data - {statement_type.replace('_', ' ').title()}")
            content_parts.append(f"Company: {ticker}")
            content_parts.append(f"Last Updated: {datetime.fromtimestamp(estimates_data.get('last_updated', 0)).strftime('%Y-%m-%d')}")
            
            # Add segment data
            if 'segment_data' in statement_data:
                content_parts.append("\nSegment Performance Data:")
                for segment, data in statement_data['segment_data'].items():
                    content_parts.append(f"- {segment}:")
                    if 'actuals' in data:
                        content_parts.append(f"  Historical: {', '.join([item['value'] for item in data['actuals']])}")
                    if 'estimates' in data:
                        content_parts.append(f"  Estimates: {', '.join([item['value'] for item in data['estimates']])}")
            
            # Add margins data
            if 'margins' in statement_data:
                content_parts.append("\nMargin Data:")
                for margin_type, data in statement_data['margins'].items():
                    content_parts.append(f"- {margin_type.replace('_', ' ').title()}:")
                    if 'actuals' in data:
                        content_parts.append(f"  Historical: {', '.join([item['value'] for item in data['actuals']])}")
                    if 'estimates' in data:
                        content_parts.append(f"  Estimates: {', '.join([item['value'] for item in data['estimates']])}")
            
            # Add quarterly data if available
            if 'quarterly_data' in statement_data and statement_data['quarterly_data']:
                content_parts.append(f"\nQuarterly Data: {len(statement_data['quarterly_data'])} quarters available")
            
            content = "\n".join(content_parts)
            
            # Create embedding document
            doc = {
                "content": content,
                "metadata": {
                    "document_type": "estimates_data",
                    "statement_type": statement_type,
                    "company_ticker": ticker.upper(),
                    "data_source": "estimates_svg",
                    "last_updated": estimates_data.get('last_updated'),
                    "processed_date": datetime.utcnow().isoformat() + "Z",
                    "priority": 0.9  # High priority for estimates data
                }
            }
            
            embedded_docs.append(doc)
            
            # Create separate documents for major segments if they have substantial data
            if 'segment_data' in statement_data:
                for segment, data in statement_data['segment_data'].items():
                    if data.get('actuals') or data.get('estimates'):
                        segment_content = f"Segment Analysis - {segment}\n"
                        segment_content += f"Company: {ticker}\n"
                        segment_content += f"Statement Type: {statement_type.replace('_', ' ').title()}\n\n"
                        
                        if data.get('actuals'):
                            segment_content += f"Historical Performance: {', '.join([item['value'] for item in data['actuals']])}\n"
                        
                        if data.get('estimates'):
                            segment_content += f"Analyst Estimates: {', '.join([item['value'] for item in data['estimates']])}\n"
                        
                        segment_doc = {
                            "content": segment_content,
                            "metadata": {
                                "document_type": "segment_estimates",
                                "segment_name": segment,
                                "statement_type": statement_type,
                                "company_ticker": ticker.upper(),
                                "data_source": "estimates_svg",
                                "last_updated": estimates_data.get('last_updated'),
                                "processed_date": datetime.utcnow().isoformat() + "Z",
                                "priority": 0.8
                            }
                        }
                        
                        embedded_docs.append(segment_doc)
        
        return embedded_docs
    
    def _remove_old_estimates_data(self, ticker: str):
        """Remove old estimates data from the database"""
        try:
            collection = self.db_service.get_collection(ticker)
            
            # Get all documents
            all_docs = collection.get()
            
            # Find documents with estimates data
            ids_to_delete = []
            for i, metadata in enumerate(all_docs["metadatas"]):
                if metadata.get("document_type") in ["estimates_data", "segment_estimates"]:
                    ids_to_delete.append(all_docs["ids"][i])
            
            # Delete old estimates documents
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                logger.info(f"Removed {len(ids_to_delete)} old estimates documents for {ticker}")
                
        except Exception as e:
            logger.error(f"Failed to remove old estimates data for {ticker}: {str(e)}")
    
    def get_estimates_data(self, ticker: str) -> Dict:
        """Get estimates data for a company"""
        try:
            estimates_data = self.estimates_parser.parse_estimates_folder(ticker)
            return estimates_data
        except Exception as e:
            logger.error(f"Failed to get estimates data for {ticker}: {str(e)}")
            return {}
