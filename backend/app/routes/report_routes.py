from flask import request
from flask_restx import Namespace, Resource, fields
import logging
import os
import uuid
import json
from datetime import datetime

from app.config import config
from app.services.database_service import DatabaseService
from app.services.ai_service import AIService
from app.services.document_service import DocumentProcessingService

logger = logging.getLogger(__name__)

# Initialize services
app_config = config['default']()
db_service = DatabaseService(app_config)
ai_service = AIService(app_config)
doc_service = DocumentProcessingService(app_config, ai_service)

# API Namespace
report_bp = Namespace('reports', description='Report generation operations')

# Request models
generate_request_model = report_bp.model('GenerateReportRequest', {
    'upload_id': fields.String(required=True, description='Upload ID of document to analyze'),
    'analysis_type': fields.String(default='general', description='Type of analysis to perform'),
    'focus_areas': fields.List(fields.String, description='Areas to focus analysis on'),
    'include_context': fields.Boolean(default=True, description='Include knowledge base context')
})

# Response models
api_response_model = report_bp.model('ApiResponse', {
    'success': fields.Boolean(required=True, description='Operation success status'),
    'data': fields.Raw(description='Response data'),
    'message': fields.String(description='Response message'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

@report_bp.route('/companies/<string:ticker>/reports/generate')
class ReportGenerate(Resource):
    @report_bp.expect(generate_request_model)
    @report_bp.marshal_with(api_response_model)
    def post(self, ticker):
        """Generate draft report based on uploaded document and knowledge base"""
        try:
            data = request.get_json()
            upload_id = data.get('upload_id')
            analysis_type = data.get('analysis_type', 'general')
            focus_areas = data.get('focus_areas', [])
            include_context = data.get('include_context', True)
            
            if not upload_id:
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Upload ID is required",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            # Find uploaded document content file
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
            
            if not os.path.exists(content_file_path):
                return {
                    "success": False,
                    "error": {
                        "code": "DOCUMENT_NOT_FOUND",
                        "message": "Uploaded document content not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            # Load the persisted document content and metadata
            try:
                with open(content_file_path, 'r', encoding='utf-8') as f:
                    document_data = json.load(f)
                
                document_text = document_data.get('document_content', '')
                document_metadata = document_data.get('metadata', {})
                original_filename = document_data.get('original_filename', 'unknown')
                document_status = document_data.get('status', 'unknown')
                
                # Check if analysis has been approved for report generation
                if document_status != "analysis_approved":
                    return {
                        "success": False,
                        "error": {
                            "code": "ANALYSIS_NOT_APPROVED",
                            "message": "Document analysis must be reviewed and approved before report generation",
                            "details": {"current_status": document_status}
                        },
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }, 400
                
                # Get approved analysis for expansion
                approved_analysis = document_data.get('analysis', {})
                context_sources = document_data.get('context_sources', [])
                
                if not document_text:
                    return {
                        "success": False,
                        "error": {
                            "code": "DOCUMENT_EMPTY",
                            "message": "Document content is empty or corrupted",
                            "details": {}
                        },
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }, 400
                    
                logger.info(f"Loaded approved analysis for detailed report generation: {upload_id}")
                
            except Exception as e:
                logger.error(f"Failed to load document content {upload_id}: {str(e)}")
                return {
                    "success": False,
                    "error": {
                        "code": "CONTENT_LOAD_ERROR",
                        "message": "Failed to load document content",
                        "details": str(e)
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 500
            
            # Get context from knowledge base using saved context sources
            context_documents = []
            if include_context and context_sources:
                # Use the context sources from initial analysis
                for source in context_sources:
                    if source.get("type") == "knowledge_base":
                        # We'll reconstruct context documents from the stored sources
                        # In a full implementation, we'd store more complete context
                        context_documents.append({
                            "document": f"Relevant content from {source.get('document', 'Unknown')}",
                            "metadata": {"file_name": source.get("document", "Unknown")},
                            "distance": 1.0 - source.get("relevance_score", 0.5)
                        })
            elif include_context:
                # Enhanced context retrieval for comprehensive report generation
                doc_embedding = ai_service.generate_embedding(document_text[:2000])
                
                results = db_service.query_historical_financial_data(
                    ticker.upper(),
                    doc_embedding,
                    n_results=15,  # Comprehensive context for detailed reports
                    prefer_recent=True
                )
                
                if results["documents"]:
                    for i in range(len(results["documents"][0])):
                        context_documents.append({
                            "document": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "distance": results["distances"][0][i]
                        })
            
            # Generate detailed report draft using approved analysis
            draft = ai_service.generate_report_draft(
                document_text, 
                context_documents, 
                analysis_type,
                approved_analysis
            )
            
            # Generate report ID
            report_id = f"report_{ticker.lower()}_{uuid.uuid4().hex[:8]}"
            
            # Update document status to indicate report generation
            document_data["status"] = "report_generated"
            document_data["report_generated_date"] = datetime.utcnow().isoformat() + "Z"
            document_data["latest_report_id"] = report_id
            
            # Save updated document data
            with open(content_file_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=2, ensure_ascii=False)
            
            # Prepare sources information
            sources = [
                {
                    "type": "uploaded_document",
                    "file_name": original_filename,
                    "relevance_score": 1.0,
                    "upload_id": upload_id
                }
            ]
            
            # Add context sources from initial analysis
            for source in context_sources[:3]:  # Top 3 sources
                sources.append(source)
            
            response_data = {
                "report_id": report_id,
                "status": "generated",
                "analysis_type": analysis_type,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "content": draft,
                "sources": sources
            }
            
            logger.info(f"Generated report {report_id} for {ticker}")
            
            return {
                "success": True,
                "data": response_data,
                "message": "Report generated successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "GENERATION_ERROR",
                    "message": "Failed to generate report",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@report_bp.route('/companies/<string:ticker>/reports')
class ReportList(Resource):
    @report_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """List generated reports for a company"""
        try:
            # For this implementation, we'll return empty list
            # In a full implementation, reports would be stored and tracked
            
            return {
                "success": True,
                "data": {
                    "reports": [],
                    "total": 0,
                    "limit": 20,
                    "offset": 0
                },
                "message": f"Reports for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to list reports for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve reports for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500
