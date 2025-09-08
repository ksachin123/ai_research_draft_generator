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
                              n_results: int = 10, where_filter: Dict = None):
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
                                      n_results: int = 10, prefer_recent: bool = True) -> Dict:
        """Query with priority for historical financial data and analyst estimates"""
        try:
            collection = self.get_collection(ticker)
            
            # First, try to get recent analyst estimates and financial metrics
            priority_results = None
            if prefer_recent:
                try:
                    priority_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(n_results // 2, 5),
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
                except:
                    priority_results = None
            
            # Get general similar documents
            general_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where_document=None
            )
            
            # Merge results, prioritizing historical financial data
            if priority_results and priority_results["ids"][0]:
                # Combine and deduplicate
                combined_ids = priority_results["ids"][0] + general_results["ids"][0]
                combined_distances = priority_results["distances"][0] + general_results["distances"][0]
                combined_metadatas = priority_results["metadatas"][0] + general_results["metadatas"][0]
                combined_documents = priority_results["documents"][0] + general_results["documents"][0]
                
                # Remove duplicates while preserving priority order
                seen_ids = set()
                final_ids, final_distances, final_metadatas, final_documents = [], [], [], []
                
                for i, doc_id in enumerate(combined_ids):
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        final_ids.append(doc_id)
                        final_distances.append(combined_distances[i])
                        final_metadatas.append(combined_metadatas[i])
                        final_documents.append(combined_documents[i])
                        
                        if len(final_ids) >= n_results:
                            break
                
                results = {
                    "ids": [final_ids],
                    "distances": [final_distances],
                    "metadatas": [final_metadatas],
                    "documents": [final_documents]
                }
            else:
                results = general_results
            
            logger.debug(f"Retrieved {len(results['ids'][0])} documents with financial data priority for {ticker}")
            return results
            
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
