from flask import request
from flask_restx import Namespace, Resource, fields
import logging
from datetime import datetime

from app.config import config
from app.services.database_service import DatabaseService
from app.services.ai_service import AIService
from app.services.document_service import DocumentProcessingService
from app.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)

# Initialize services
app_config = config['default']()
db_service = DatabaseService(app_config)
ai_service = AIService(app_config)
doc_service = DocumentProcessingService(app_config, ai_service)
kb_service = KnowledgeBaseService(app_config, db_service, doc_service)

# API Namespace
knowledge_base_bp = Namespace('knowledge-base', description='Knowledge base management operations')

# Request models
refresh_request_model = knowledge_base_bp.model('RefreshRequest', {
    'force_reprocess': fields.Boolean(default=False, description='Force reprocessing of all files'),
    'include_investment_data': fields.Boolean(default=True, description='Include investment data processing'),
    'include_financial_statements': fields.Boolean(default=True, description='Include financial statements processing')
})

# Response models
api_response_model = knowledge_base_bp.model('ApiResponse', {
    'success': fields.Boolean(required=True, description='Operation success status'),
    'data': fields.Raw(description='Response data'),
    'message': fields.String(description='Response message'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

@knowledge_base_bp.route('/companies/<string:ticker>/knowledge-base/refresh')
class KnowledgeBaseRefresh(Resource):
    @knowledge_base_bp.expect(refresh_request_model, validate=False)
    @knowledge_base_bp.marshal_with(api_response_model)
    def post(self, ticker):
        """Trigger knowledge base refresh for a company"""
        try:
            data = request.get_json() or {}
            force_reprocess = data.get('force_reprocess', False)
            include_investment_data = data.get('include_investment_data', True)
            include_financial_statements = data.get('include_financial_statements', True)
            
            logger.info(f"Starting knowledge base refresh for {ticker}")
            
            # Trigger refresh
            result = kb_service.refresh_knowledge_base(
                ticker.upper(), 
                force_reprocess=force_reprocess,
                include_investment_data=include_investment_data,
                include_estimates=include_financial_statements
            )
            
            return {
                "success": True,
                "data": {
                    "job_id": f"refresh_{ticker.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "status": result["status"],
                    "reports_processed": result["reports_processed"],
                    "investment_data_processed": result["investment_data_processed"],
                    "financial_statements_processed": result["financial_statements_processed"],
                    "total_documents": result["total_documents"]
                },
                "message": f"Knowledge base refresh completed for {ticker.upper()}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh knowledge base for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": f"Failed to refresh knowledge base for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@knowledge_base_bp.route('/companies/<string:ticker>/knowledge-base/status')
class KnowledgeBaseStatus(Resource):
    @knowledge_base_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """Get knowledge base status for a company"""
        try:
            stats = db_service.get_company_stats(ticker.upper())
            processing_state = db_service.get_processing_state(ticker.upper())
            
            status_data = {
                "status": stats.get("status", "unknown"),
                "last_refresh": processing_state.get("last_updated") if processing_state else None,
                "processing_jobs": [],  # Would be expanded for async processing
                "stats": {
                    "total_documents": stats.get("total_documents", 0),
                    "total_chunks": stats.get("total_documents", 0),  # Approximation
                    "new_files_processed": 0,  # Would track in real implementation
                    "updated_files": len(processing_state.get("processed_files", {}).get("past_reports", [])) if processing_state else 0
                }
            }
            
            return {
                "success": True,
                "data": status_data,
                "message": f"Knowledge base status for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base status for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve knowledge base status for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@knowledge_base_bp.route('/companies/<string:ticker>/knowledge-base/content')
class KnowledgeBaseContent(Resource):
    @knowledge_base_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """Get knowledge base content for a company with pagination and filtering"""
        try:
            # Parse query parameters
            page = int(request.args.get('page', 1))
            page_size = min(int(request.args.get('page_size', 20)), 100)  # Limit max page size
            document_type = request.args.get('document_type')
            search_query = request.args.get('search')
            
            logger.info(f"Getting knowledge base content for {ticker} - page: {page}, size: {page_size}")
            
            # Get content from database service
            content_data = db_service.get_knowledge_base_content(
                ticker.upper(), 
                page=page, 
                page_size=page_size,
                document_type=document_type,
                search_query=search_query
            )
            
            return {
                "success": True,
                "data": {
                    "ticker": ticker.upper(),
                    "documents": content_data["documents"],
                    "pagination": content_data["pagination"],
                    "filters": {
                        "document_type": document_type,
                        "search_query": search_query
                    }
                },
                "message": f"Knowledge base content for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except ValueError as e:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETERS",
                    "message": "Invalid query parameters",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 400
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base content for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve knowledge base content for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@knowledge_base_bp.route('/companies/<string:ticker>/knowledge-base/document-types')
class KnowledgeBaseDocumentTypes(Resource):
    @knowledge_base_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """Get available document types in the knowledge base"""
        try:
            document_types = kb_service.get_knowledge_base_document_types(ticker.upper())
            
            return {
                "success": True,
                "data": {
                    "ticker": ticker.upper(),
                    "document_types": document_types
                },
                "message": f"Document types for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get document types for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve document types for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500


@knowledge_base_bp.route('/<string:ticker>/financial-data')
@knowledge_base_bp.doc('get_financial_data_summary')
class FinancialDataSummary(Resource):
    @knowledge_base_bp.doc('get_financial_data_summary', 
                          description='Get summary of all financial data for a ticker')
    def get(self, ticker):
        """Get summary of financial data for a ticker"""
        try:
            logger.info(f"Getting financial data summary for {ticker}")
            
            # Get financial data summary
            summary = db_service.get_financial_data_summary(ticker)
            
            return {
                "success": True,
                "data": summary,
                "message": f"Financial data summary for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get financial data summary for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR", 
                    "message": f"Failed to retrieve financial data summary for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500


@knowledge_base_bp.route('/<string:ticker>/financial-data/delete')
@knowledge_base_bp.doc('delete_financial_data')
class FinancialDataDelete(Resource):
    
    delete_request_model = knowledge_base_bp.model('DeleteFinancialDataRequest', {
        'delete_all': fields.Boolean(default=False, description='Delete all financial data for the ticker'),
        'date_filter': fields.String(required=False, description='Date filter: exact date (YYYY-MM-DD), before:YYYY-MM-DD, or after:YYYY-MM-DD')
    })
    
    @knowledge_base_bp.expect(delete_request_model)
    @knowledge_base_bp.doc('delete_financial_data',
                          description='Delete financial data for a ticker with optional filters')
    def post(self, ticker):
        """Delete financial data for a ticker"""
        try:
            data = request.get_json() or {}
            delete_all = data.get('delete_all', False)
            date_filter = data.get('date_filter')
            
            logger.info(f"Deleting financial data for {ticker} with delete_all={delete_all}, date_filter={date_filter}")
            
            # Validate input
            if not delete_all and not date_filter:
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Must specify either 'delete_all=true' or provide 'date_filter'",
                        "details": "Use delete_all=true to delete all financial data, or provide date_filter with format: YYYY-MM-DD, before:YYYY-MM-DD, or after:YYYY-MM-DD"
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            # Delete financial data
            result = db_service.delete_financial_data(ticker, delete_all, date_filter)
            
            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Financial data deletion completed for {ticker.upper()}"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except ValueError as e:
            logger.error(f"Validation error deleting financial data for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e),
                    "details": "Check the date_filter format. Use: YYYY-MM-DD, before:YYYY-MM-DD, or after:YYYY-MM-DD"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 400
            
        except Exception as e:
            logger.error(f"Failed to delete financial data for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to delete financial data for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500


@knowledge_base_bp.route('/<string:ticker>/collection')
@knowledge_base_bp.doc('get_collection_data')
class CollectionData(Resource):
    @knowledge_base_bp.doc('get_collection_data',
                          description='Get raw collection data as stored in database for a ticker')
    def get(self, ticker):
        """Get raw collection data for a ticker"""
        try:
            logger.info(f"Getting raw collection data for {ticker}")
            
            # Get raw collection data exactly as stored
            collection_data = db_service.get_collection_data(ticker)
            
            return {
                "success": True,
                "data": collection_data,
                "message": f"Raw collection data for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection data for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve collection data for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500


@knowledge_base_bp.route('/<string:ticker>/collection/delete')
@knowledge_base_bp.doc('delete_collection')
class CollectionDelete(Resource):
    @knowledge_base_bp.doc('delete_collection',
                          description='Delete entire collection for a ticker')
    def post(self, ticker):
        """Delete entire collection for a ticker"""
        try:
            logger.info(f"Deleting collection for {ticker}")
            
            # Delete the collection
            result = db_service.delete_collection(ticker)
            
            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Collection for {ticker.upper()} deleted successfully"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete collection for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to delete collection for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500
