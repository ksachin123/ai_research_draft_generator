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
    'include_investment_data': fields.Boolean(default=True, description='Include investment data processing')
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
            
            logger.info(f"Starting knowledge base refresh for {ticker}")
            
            # Trigger refresh
            result = kb_service.refresh_knowledge_base(
                ticker.upper(), 
                force_reprocess=force_reprocess,
                include_investment_data=include_investment_data
            )
            
            return {
                "success": True,
                "data": {
                    "job_id": f"refresh_{ticker.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "status": result["status"],
                    "reports_processed": result["reports_processed"],
                    "investment_data_processed": result["investment_data_processed"],
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
