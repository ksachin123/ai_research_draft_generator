import chromadb
from chromadb.config import Settings
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, config):
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client"""
        try:
            # Disable ChromaDB telemetry to prevent telemetry errors
            import os
            import logging
            os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
            
            # Suppress ChromaDB telemetry logging errors
            logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
            logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
            
            self.client = chromadb.PersistentClient(
                path=self.config.CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info(f"ChromaDB client initialized at {self.config.CHROMA_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise
    
    def get_collection(self, ticker: str):
        """Get or create collection for a company"""
        collection_name = f"company_{ticker.lower()}_knowledge_base"
        
        try:
            collection = self.client.get_collection(collection_name)
            logger.debug(f"Retrieved existing collection: {collection_name}")
        except Exception:
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"company_ticker": ticker.upper()}
            )
            logger.info(f"Created new collection: {collection_name}")
        
        return collection
    
    def add_documents(self, ticker: str, documents: List[Dict]):
        """Add documents to company collection"""
        collection = self.get_collection(ticker)
        
        ids = [doc['id'] for doc in documents]
        embeddings = [doc['embedding'] for doc in documents]
        metadatas = [doc['metadata'] for doc in documents]
        documents_text = [doc['document'] for doc in documents]
        
        try:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            logger.info(f"Added {len(documents)} documents to {ticker} collection")
        except Exception as e:
            logger.error(f"Failed to add documents to {ticker} collection: {str(e)}")
            raise
    
    def query_similar_documents(self, ticker: str, query_embedding: List[float], 
                              n_results: int = 10, where_filter: Optional[Dict] = None):
        """Query similar documents from collection"""
        collection = self.get_collection(ticker)
        
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.debug(f"Retrieved {len(results['ids'][0])} similar documents for {ticker}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to query similar documents for {ticker}: {str(e)}")
            raise
    
    def query_historical_financial_data(self, ticker: str, query_embedding: List[float], 
                                      n_results: int = 15, prefer_recent: bool = True) -> Dict:
        """Query with priority for historical financial data and analyst estimates - Enhanced for comprehensive context"""
        try:
            collection = self.get_collection(ticker)
            
            # Step 1: Get recent financial documents with analyst estimates (priority)
            financial_results = None
            if prefer_recent:
                try:
                    financial_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=8,  # Increased from 5 to get more financial context
                        where={
                            "$and": [
                                {"is_historical": True},
                                {"$or": [
                                    {"contains_analyst_estimates": True},
                                    {"historical_financial_data": True}
                                ]}
                            ]
                        }
                    )
                    logger.info(f"Retrieved {len(financial_results['ids'][0])} financial documents with estimates")
                except Exception as e:
                    logger.debug(f"Failed to query financial documents: {str(e)}")
                    financial_results = None
            
            # Step 2: Get recent general documents (investment data, etc.)
            recent_results = None
            try:
                # Query for document_type only, filter by date in Python
                temp_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=30,  # Get more to allow for filtering
                    where={
                        "document_type": {"$in": ["past_report", "investment_data"]}
                    }
                )
                # Filter by report_date >= '2024-01-01' (string compare is safe for ISO format)
                filtered_indices = []
                for i, meta in enumerate(temp_results["metadatas"][0]):
                    report_date = meta.get("report_date")
                    if report_date and report_date >= "2024-01-01":
                        filtered_indices.append(i)
                # Build filtered results
                recent_results = {
                    "ids": [[temp_results["ids"][0][i] for i in filtered_indices]],
                    "distances": [[temp_results["distances"][0][i] for i in filtered_indices]],
                    "metadatas": [[temp_results["metadatas"][0][i] for i in filtered_indices]],
                    "documents": [[temp_results["documents"][0][i] for i in filtered_indices]]
                }
                logger.info(f"Retrieved {len(recent_results['ids'][0])} recent investment documents (filtered by date)")
            except Exception as e:
                logger.error(f"Failed to query recent documents: {str(e)}")
                recent_results = None
            
            # Step 3: Get general similar documents as fallback
            general_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Step 4: Intelligently merge results, prioritizing comprehensive context
            combined_ids, combined_distances, combined_metadatas, combined_documents = [], [], [], []
            seen_ids = set()
            
            # Priority order: Financial documents > Recent reports > General similar
            result_sets = []
            if financial_results and financial_results["ids"][0]:
                result_sets.append(("financial", financial_results))
            if recent_results and recent_results["ids"][0]:
                result_sets.append(("recent", recent_results))
            result_sets.append(("general", general_results))
            
            # Combine results in priority order
            for result_type, results in result_sets:
                for i in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][i]
                    if doc_id not in seen_ids and len(combined_ids) < n_results:
                        seen_ids.add(doc_id)
                        combined_ids.append(doc_id)
                        combined_distances.append(results["distances"][0][i])
                        combined_metadatas.append(results["metadatas"][0][i])
                        combined_documents.append(results["documents"][0][i])
                        logger.debug(f"Added {result_type} doc: {results['metadatas'][0][i].get('file_name', 'Unknown')}")
                        
                        if len(combined_ids) >= n_results:
                            break
                
                if len(combined_ids) >= n_results:
                    break
            
            final_results = {
                "ids": [combined_ids],
                "distances": [combined_distances],
                "metadatas": [combined_metadatas],
                "documents": [combined_documents]
            }
            
            logger.info(f"Enhanced context retrieval: Retrieved {len(combined_ids)} comprehensive context documents for {ticker}")
            return final_results
            
        except Exception as e:
            logger.error(f"Failed to query historical financial data for {ticker}: {str(e)}")
            # Fall back to regular query
            return self.query_similar_documents(ticker, query_embedding, n_results)
    
    def get_company_stats(self, ticker: str) -> Dict:
        """Get statistics for a company collection"""
        try:
            collection = self.get_collection(ticker)
            count = collection.count()
            
            if count == 0:
                return {"status": "empty", "total_documents": 0}
            
            # Get recent documents
            try:
                recent_docs = collection.get(
                    where={"processed_date": {"$gte": "2025-09-06T00:00:00Z"}},
                    limit=1
                )
                has_recent = len(recent_docs["ids"]) > 0
            except:
                has_recent = False
            
            # Get document types
            try:
                investment_data_count = len(collection.get(
                    where={"document_type": "investment_data"}
                )["ids"])
            except:
                investment_data_count = 0
            
            try:
                past_reports_count = len(collection.get(
                    where={"document_type": "past_report"}
                )["ids"])
            except:
                past_reports_count = 0
            
            return {
                "total_documents": count,
                "past_reports": past_reports_count,
                "investment_data": investment_data_count,
                "has_recent_updates": has_recent,
                "status": "active" if count > 0 else "empty"
            }
        
        except Exception as e:
            logger.error(f"Failed to get stats for {ticker}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def update_processing_state(self, ticker: str, state: Dict):
        """Update processing state for a company"""
        state_dir = os.path.join(self.config.CHROMA_DB_PATH, "processing_state")
        os.makedirs(state_dir, exist_ok=True)
        
        state_file = os.path.join(state_dir, f"{ticker.upper()}.json")
        
        state["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Updated processing state for {ticker}")
        except Exception as e:
            logger.error(f"Failed to update processing state for {ticker}: {str(e)}")
            raise
    
    def get_processing_state(self, ticker: str) -> Optional[Dict]:
        """Get processing state for a company"""
        state_file = os.path.join(
            self.config.CHROMA_DB_PATH, 
            "processing_state", 
            f"{ticker.upper()}.json"
        )
        
        if not os.path.exists(state_file):
            return None
        
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load processing state for {ticker}: {str(e)}")
            return None
    
    def get_all_companies(self) -> List[str]:
        """Get list of all companies with collections"""
        try:
            collections = self.client.list_collections()
            tickers = []
            
            for collection in collections:
                if collection.name.startswith("company_") and collection.name.endswith("_knowledge_base"):
                    # Extract ticker from collection name
                    ticker = collection.name.replace("company_", "").replace("_knowledge_base", "").upper()
                    tickers.append(ticker)
            
            return tickers
        except Exception as e:
            logger.error(f"Failed to get companies list: {str(e)}")
            return []
    
    def get_knowledge_base_content(self, ticker: str, page: int = 1, page_size: int = 50, 
                                 document_type: Optional[str] = None, search_query: Optional[str] = None) -> Dict:
        """Get knowledge base content with pagination and filtering"""
        try:
            collection = self.get_collection(ticker)
            
            # Build where filter
            where_filter = {}
            if document_type:
                where_filter["document_type"] = document_type
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            if search_query:
                # If there's a search query, use ChromaDB's text search capability
                # First get all documents that match the filter, then search within them
                if where_filter:
                    all_matching = collection.get(where=where_filter)
                    if not all_matching["ids"]:
                        return {
                            "documents": [],
                            "pagination": {
                                "page": page,
                                "page_size": page_size,
                                "total_items": 0,
                                "total_pages": 0,
                                "has_next": False,
                                "has_prev": page > 1
                            }
                        }
                else:
                    all_matching = collection.get()
                
                # Filter documents that contain the search query (case-insensitive)
                search_lower = search_query.lower()
                filtered_documents = []
                filtered_metadatas = []
                filtered_ids = []
                
                for i, doc in enumerate(all_matching["documents"]):
                    if search_lower in doc.lower():
                        filtered_documents.append(doc)
                        filtered_metadatas.append(all_matching["metadatas"][i])
                        filtered_ids.append(all_matching["ids"][i])
                
                # Apply pagination
                paginated_documents = filtered_documents[offset:offset + page_size]
                paginated_metadatas = filtered_metadatas[offset:offset + page_size]
                paginated_ids = filtered_ids[offset:offset + page_size]
                
                total_items = len(filtered_documents)
            else:
                # No search query, just get all documents with filter
                try:
                    # Get total count first
                    if where_filter:
                        all_docs = collection.get(where=where_filter)
                    else:
                        all_docs = collection.get()
                    
                    total_items = len(all_docs["ids"])
                    
                    # Apply pagination
                    paginated_ids = all_docs["ids"][offset:offset + page_size]
                    paginated_documents = all_docs["documents"][offset:offset + page_size]
                    paginated_metadatas = all_docs["metadatas"][offset:offset + page_size]
                    
                except Exception as e:
                    logger.error(f"Error getting documents for {ticker}: {str(e)}")
                    return {
                        "documents": [],
                        "pagination": {
                            "page": page,
                            "page_size": page_size,
                            "total_items": 0,
                            "total_pages": 0,
                            "has_next": False,
                            "has_prev": page > 1
                        }
                    }
            
            # Format documents
            formatted_documents = []
            for i, doc_id in enumerate(paginated_ids):
                metadata = paginated_metadatas[i]
                document_text = paginated_documents[i]
                
                formatted_doc = {
                    "id": doc_id,
                    "content": document_text,
                    "content_preview": document_text[:300] + "..." if len(document_text) > 300 else document_text,
                    "metadata": {
                        "document_type": metadata.get("document_type", "unknown"),
                        "source_file": metadata.get("source_file", "unknown"),
                        "processed_date": metadata.get("processed_date"),
                        "report_date": metadata.get("report_date"),
                        "page_number": metadata.get("page_number"),
                        "chunk_index": metadata.get("chunk_index"),
                        "contains_analyst_estimates": metadata.get("contains_analyst_estimates", False),
                        "historical_financial_data": metadata.get("historical_financial_data", False),
                        "content_priority": metadata.get("content_priority", 0.0)
                    }
                }
                formatted_documents.append(formatted_doc)
            
            # Calculate pagination info
            total_pages = (total_items + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                "documents": formatted_documents,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base content for {ticker}: {str(e)}")
            raise
    
    def get_financial_data_summary(self, ticker: str) -> Dict:
        """Get a summary of all financial data for a given ticker"""
        try:
            collection = self.get_collection(ticker)
            
            # Query for financial documents
            financial_docs = collection.get(
                where={"$or": [
                    {"contains_analyst_estimates": True},
                    {"historical_financial_data": True},
                    {"document_type": {"$in": ["financial_statement", "earnings_report"]}}
                ]}
            )
            
            # Analyze the financial data
            summary = {
                "ticker": ticker.upper(),
                "total_financial_documents": len(financial_docs["ids"]),
                "document_types": {},
                "date_range": {"earliest": None, "latest": None},
                "contains_estimates": 0,
                "contains_historical": 0
            }
            
            for i, metadata in enumerate(financial_docs["metadatas"]):
                # Count document types
                doc_type = metadata.get("document_type", "unknown")
                summary["document_types"][doc_type] = summary["document_types"].get(doc_type, 0) + 1
                
                # Track date range
                report_date = metadata.get("report_date")
                if report_date:
                    if not summary["date_range"]["earliest"] or report_date < summary["date_range"]["earliest"]:
                        summary["date_range"]["earliest"] = report_date
                    if not summary["date_range"]["latest"] or report_date > summary["date_range"]["latest"]:
                        summary["date_range"]["latest"] = report_date
                
                # Count specific features
                if metadata.get("contains_analyst_estimates"):
                    summary["contains_estimates"] += 1
                if metadata.get("historical_financial_data"):
                    summary["contains_historical"] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get financial data summary for {ticker}: {str(e)}")
            raise
    
    def delete_financial_data(self, ticker: str, delete_all: bool = False, date_filter: Optional[str] = None) -> Dict:
        """Delete financial data for a given ticker with optional filters"""
        try:
            collection = self.get_collection(ticker)
            
            # Build where clause based on parameters
            where_clause = None
            if delete_all:
                # Delete all financial data
                where_clause = {"$or": [
                    {"contains_analyst_estimates": True},
                    {"historical_financial_data": True},
                    {"document_type": {"$in": ["financial_statement", "earnings_report"]}}
                ]}
            elif date_filter:
                # Delete financial data for specific date or before/after a date
                if date_filter.startswith("before:"):
                    target_date = date_filter.replace("before:", "")
                    where_clause = {
                        "$and": [
                            {"$or": [
                                {"contains_analyst_estimates": True},
                                {"historical_financial_data": True},
                                {"document_type": {"$in": ["financial_statement", "earnings_report"]}}
                            ]},
                            {"report_date": {"$lt": target_date}}
                        ]
                    }
                elif date_filter.startswith("after:"):
                    target_date = date_filter.replace("after:", "")
                    where_clause = {
                        "$and": [
                            {"$or": [
                                {"contains_analyst_estimates": True},
                                {"historical_financial_data": True},
                                {"document_type": {"$in": ["financial_statement", "earnings_report"]}}
                            ]},
                            {"report_date": {"$gt": target_date}}
                        ]
                    }
                else:
                    # Exact date match
                    where_clause = {
                        "$and": [
                            {"$or": [
                                {"contains_analyst_estimates": True},
                                {"historical_financial_data": True},
                                {"document_type": {"$in": ["financial_statement", "earnings_report"]}}
                            ]},
                            {"report_date": date_filter}
                        ]
                    }
            else:
                raise ValueError("Must specify either delete_all=True or provide date_filter")
            
            # Get documents to be deleted (for counting)
            docs_to_delete = collection.get(where=where_clause)
            count_to_delete = len(docs_to_delete["ids"])
            
            if count_to_delete == 0:
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "No financial documents found matching the criteria"
                }
            
            # Delete the documents
            collection.delete(where=where_clause)
            
            logger.info(f"Deleted {count_to_delete} financial documents for {ticker}")
            
            return {
                "success": True,
                "deleted_count": count_to_delete,
                "message": f"Successfully deleted {count_to_delete} financial documents for {ticker.upper()}"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete financial data for {ticker}: {str(e)}")
            raise
    
    def get_collection_data(self, ticker: str) -> Dict:
        """Get raw collection data for a ticker as stored in the database"""
        try:
            collection = self.get_collection(ticker)
            
            # Get all raw data from the collection exactly as stored
            all_data = collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
            
            # Return the raw data structure directly from ChromaDB
            return all_data
            
        except Exception as e:
            logger.error(f"Failed to get collection data for {ticker}: {str(e)}")
            raise
    
    def delete_collection(self, ticker: str) -> Dict:
        """Delete entire collection for a ticker"""
        try:
            collection_name = f"company_{ticker.lower()}_knowledge_base"
            
            # Delete the collection
            self.client.delete_collection(collection_name)
            
            # Also clean up processing state
            try:
                self._delete_processing_state(ticker)
            except:
                pass  # Continue even if processing state cleanup fails
            
            logger.info(f"Deleted collection {collection_name}")
            
            return {
                "success": True,
                "collection_name": collection_name,
                "message": f"Successfully deleted collection for {ticker.upper()} "
            }
            
        except Exception as e:
            logger.error(f"Failed to delete collection for {ticker}: {str(e)}")
            raise
    
    def _delete_processing_state(self, ticker: str):
        """Delete processing state file for a ticker"""
        try:
            processing_state_dir = os.path.join(self.config.CHROMA_DB_PATH, "processing_state")
            processing_file = os.path.join(processing_state_dir, f"{ticker.lower()}_state.json")
            
            if os.path.exists(processing_file):
                os.remove(processing_file)
                logger.info(f"Deleted processing state file for {ticker}")
        except Exception as e:
            logger.error(f"Failed to delete processing state for {ticker}: {str(e)}")
            raise
    