from flask import request
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage
import logging
import os
import uuid
import json
from datetime import datetime

from app.config import config
from app.services.database_service import DatabaseService
from app.services.ai_service import AIService
from app.services.document_service import DocumentProcessingService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.enhanced_svg_parser import create_enhanced_financial_parser

logger = logging.getLogger(__name__)

# Initialize services
app_config = config['default']()
db_service = DatabaseService(app_config)
ai_service = AIService(app_config)
kb_service = KnowledgeBaseService(app_config, db_service, None)
doc_service = DocumentProcessingService(app_config, ai_service, kb_service)
enhanced_parser = create_enhanced_financial_parser(app_config)

# API Namespace
document_bp = Namespace('documents', description='Document management operations')

# Request models
upload_parser = document_bp.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='Document file to upload')
upload_parser.add_argument('document_type', type=str, required=True, help='Type of document', 
                          choices=['10-K', '10-Q', '8-K', 'earnings_call', 'investor_presentation', 'press_release', 'other'])
upload_parser.add_argument('description', type=str, required=False, help='Document description')

# Analysis trigger parser
analyze_parser = document_bp.parser()
analyze_parser.add_argument('upload_ids', type=str, action='append', required=True, 
                           help='List of upload IDs to analyze', location='json')
analyze_parser.add_argument('analysis_options', type=dict, required=False, 
                           help='Analysis options', location='json')

# Response models
api_response_model = document_bp.model('ApiResponse', {
    'success': fields.Boolean(required=True, description='Operation success status'),
    'data': fields.Raw(description='Response data'),
    'message': fields.String(description='Response message'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

@document_bp.route('/companies/<string:ticker>/documents/upload')
class DocumentUpload(Resource):
    @document_bp.expect(upload_parser)
    @document_bp.marshal_with(api_response_model)
    def post(self, ticker):
        """Upload a new document for analysis"""
        logger.info(f"=== Starting document upload for ticker: {ticker} ===")
        
        try:
            # Parse arguments
            logger.debug("Parsing upload arguments...")
            args = upload_parser.parse_args()
            uploaded_file = args['file']
            document_type = args['document_type']
            description = args.get('description', '')
            
            logger.info(f"Upload request details - Ticker: {ticker}, Document Type: {document_type}, "
                       f"Description: '{description}', File: {uploaded_file.filename if uploaded_file else 'None'}")
            
            if not uploaded_file:
                logger.error("Upload failed: No file provided in request")
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No file uploaded",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            # Validate file size
            logger.debug(f"Validating file size for: {uploaded_file.filename}")
            file_content = uploaded_file.read()
            file_size = len(file_content)
            logger.info(f"File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
            
            if file_size > app_config.MAX_CONTENT_LENGTH:
                logger.error(f"Upload failed: File size {file_size} exceeds limit {app_config.MAX_CONTENT_LENGTH}")
                return {
                    "success": False,
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": "File size exceeds 5MB limit",
                        "details": {"file_size": file_size, "max_size": app_config.MAX_CONTENT_LENGTH}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 413
            
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Generate upload ID with timestamp and save file
            timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            upload_id = f"upload_{ticker.lower()}_{timestamp_str}_{uuid.uuid4().hex[:8]}"
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            
            logger.info(f"Generated upload ID: {upload_id}")
            logger.info(f"Upload directory: {upload_dir}")
            
            try:
                os.makedirs(upload_dir, exist_ok=True)
                logger.debug(f"Created/verified upload directory: {upload_dir}")
            except Exception as dir_error:
                logger.error(f"Failed to create upload directory {upload_dir}: {str(dir_error)}")
                raise
            
            file_path = os.path.join(upload_dir, f"{upload_id}_{uploaded_file.filename}")
            logger.info(f"Saving file to: {file_path}")
            
            try:
                uploaded_file.save(file_path)
                saved_file_size = os.path.getsize(file_path)
                logger.info(f"File saved successfully. Size on disk: {saved_file_size} bytes")
            except Exception as save_error:
                logger.error(f"Failed to save file to {file_path}: {str(save_error)}")
                raise
            
            # Parse and extract document content (but don't add to knowledge base)
            logger.info("=== Starting document content extraction ===")
            document_content = ""
            doc_metadata = {}
            content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
            
            try:
                # Extract text content for analysis/comparison
                logger.debug(f"Extracting text content from: {file_path}")
                document_content, doc_metadata = doc_service.extract_pdf_text(file_path)
                logger.info(f"Content extraction successful. Text length: {len(document_content)} chars, "
                           f"Metadata: {doc_metadata}")
                
                # Save extracted content and metadata to JSON file for later use
                logger.debug(f"Preparing content data for saving to: {content_file_path}")
                content_data = {
                    "upload_id": upload_id,
                    "original_filename": uploaded_file.filename,
                    "file_path": file_path,
                    "ticker": ticker.upper(),
                    "upload_date": datetime.utcnow().isoformat() + "Z",
                    "document_content": document_content,
                    "metadata": doc_metadata,
                    "document_type": document_type,
                    "description": description,
                    "status": "uploaded"  # Initial status
                }
                
                try:
                    with open(content_file_path, 'w', encoding='utf-8') as f:
                        json.dump(content_data, f, indent=2, ensure_ascii=False)
                    logger.info(f"Content data saved to: {content_file_path}")
                except Exception as json_error:
                    logger.error(f"Failed to save content data to {content_file_path}: {str(json_error)}")
                    raise
                
                processing_status = "uploaded"
                logger.info(f"Document uploaded and ready for analysis: {upload_id} ({len(document_content)} chars)")
                
                # Document is now uploaded and ready for analysis when triggered
                # Analysis will be triggered separately via the /analyze endpoint
                
            except Exception as content_error:
                processing_status = "error"
                logger.error(f"Failed to parse/process document {upload_id}: {str(content_error)}")
                logger.error(f"Content error type: {type(content_error).__name__}")
                logger.error(f"Content error details: {str(content_error)}")
            
            # Create document info in expected format
            logger.info("=== Creating response document info ===")
            document_info = {
                "upload_id": upload_id,
                "filename": uploaded_file.filename,
                "file_size": saved_file_size,
                "upload_date": datetime.utcnow().isoformat() + "Z",
                "processing_status": processing_status,
                "content_length": len(document_content) if document_content else 0,
                "metadata": doc_metadata
            }
            
            # Include basic document info in response
            response_data = {
                "uploaded_files": [document_info]
            }
            
            # Since we're not doing immediate analysis, we won't include analysis results in upload response
            # Analysis will be triggered separately via the /analyze endpoint
            
            logger.info(f"Document upload completed successfully: {upload_id}")
            logger.info(f"Final processing status: {processing_status}")
            logger.info(f"Document ready for analysis when requested")
            
            return {
                "success": True,
                "data": response_data,
                "message": "Document uploaded successfully and ready for analysis",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error("=== DOCUMENT UPLOAD FAILED ===")
            logger.error(f"Upload error for ticker {ticker}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            
            # Log additional context
            try:
                logger.error(f"Upload folder config: {app_config.UPLOAD_FOLDER}")
                logger.error(f"OpenAI API key configured: {'Yes' if app_config.OPENAI_API_KEY else 'No'}")
                logger.error(f"OpenAI model: {app_config.OPENAI_MODEL}")
            except:
                logger.error("Failed to log configuration details")
            
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            return {
                "success": False,
                "error": {
                    "code": "UPLOAD_ERROR",
                    "message": "Failed to upload document",
                    "details": {"error_type": type(e).__name__, "error_message": str(e)}
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@document_bp.route('/companies/<string:ticker>/documents/<string:upload_id>/analysis')
class DocumentAnalysis(Resource):
    @document_bp.marshal_with(api_response_model)
    def get(self, ticker, upload_id):
        """Get initial analysis results for an uploaded document"""
        try:
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
            
            if not os.path.exists(content_file_path):
                return {
                    "success": False,
                    "error": {
                        "code": "DOCUMENT_NOT_FOUND",
                        "message": "Document not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            # Load document data with analysis
            with open(content_file_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
            
            if document_data.get("status") not in ["analysis_ready", "analysis_approved"]:
                return {
                    "success": False,
                    "error": {
                        "code": "ANALYSIS_NOT_READY",
                        "message": "Analysis not available for this document",
                        "details": {"status": document_data.get("status", "unknown")}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            analysis_data = {
                "upload_id": upload_id,
                "document_info": {
                    "filename": document_data.get("original_filename"),
                    "upload_date": document_data.get("upload_date"),
                    "document_type": document_data.get("document_type"),
                    "description": document_data.get("description", "")
                },
                "analysis": document_data.get("analysis", {}),
                "analysis_date": document_data.get("analysis_date"),
                "status": document_data.get("status"),
                "context_sources": document_data.get("context_sources", []),
                "generation_metadata": document_data.get("generation_metadata", {})
            }
            
            return {
                "success": True,
                "data": analysis_data,
                "message": "Analysis results retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis for {upload_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve analysis",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

    @document_bp.marshal_with(api_response_model)
    def put(self, ticker, upload_id):
        """Modify analysis parameters and regenerate if needed"""
        try:
            data = request.get_json() or {}
            analysis_type = data.get('analysis_type')
            focus_areas = data.get('focus_areas', [])
            regenerate = data.get('regenerate', False)
            
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
            
            if not os.path.exists(content_file_path):
                return {
                    "success": False,
                    "error": {
                        "code": "DOCUMENT_NOT_FOUND",
                        "message": "Document not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            # Load document data
            with open(content_file_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
            
            if regenerate:
                # Regenerate analysis with new parameters
                document_content = document_data.get('document_content', '')
                
                # Generate embedding for similarity search
                doc_embedding = ai_service.generate_embedding(document_content[:2000])
                
                # Search for similar documents with financial data priority
                results = db_service.query_historical_financial_data(
                    ticker.upper(),
                    doc_embedding,
                    n_results=8,
                    prefer_recent=True
                )
                
                context_documents = []
                if results["documents"]:
                    for i in range(len(results["documents"][0])):
                        context_documents.append({
                            "document": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "distance": results["distances"][0][i]
                        })
                
                # Generate new analysis with updated parameters
                # Use comprehensive financial data for analysis
                try:
                    # Use comprehensive financial data
                    comprehensive_data = kb_service.get_comprehensive_financial_data(ticker.upper())
                    has_comprehensive = bool(comprehensive_data and comprehensive_data.get('has_data'))
                        
                except Exception as e:
                    logger.warning(f"Failed to check comprehensive financial data: {str(e)}")
                    has_comprehensive = False
                    comprehensive_data = {}
                
                if has_comprehensive:
                    # Use comprehensive financial data processing
                    logger.info(f"Using comprehensive financial analysis for {ticker.upper()}")
                    document_metrics = doc_service._extract_document_metrics(document_content, None)
                    comparative_data = doc_service._perform_comprehensive_financial_analysis(
                        ticker.upper(), document_metrics, comprehensive_data or {}, None
                    )
                    
                    new_analysis = ai_service.generate_comparative_analysis(
                        document_content,
                        context_documents,
                        comparative_data,
                        analysis_type or document_data.get("document_type", "general")
                    )
                    
                    new_analysis["comparative_data"] = comparative_data
                    new_analysis["document_metrics"] = document_metrics
                    new_analysis["has_comprehensive_analysis"] = True
                    
                else:
                    # No comprehensive financial data available - generate basic analysis
                    logger.info(f"No comprehensive financial data available for {ticker.upper()}, generating basic analysis")
                    new_analysis = ai_service.generate_report_draft(
                        document_content, 
                        context_documents, 
                        analysis_type or document_data.get("document_type", "general")
                    )
                    new_analysis["has_comprehensive_analysis"] = False
                
                # Update document data
                document_data["analysis"] = new_analysis
                document_data["analysis_date"] = datetime.utcnow().isoformat() + "Z"
                document_data["status"] = "analysis_ready"
                document_data["analysis_parameters"] = {
                    "analysis_type": analysis_type,
                    "focus_areas": focus_areas
                }
            
            # Save updated document data
            with open(content_file_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "data": {
                    "upload_id": upload_id,
                    "status": document_data.get("status"),
                    "analysis": document_data.get("analysis"),
                    "regenerated": regenerate
                },
                "message": "Analysis updated successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to modify analysis for {upload_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "MODIFICATION_ERROR",
                    "message": "Failed to modify analysis",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@document_bp.route('/companies/<string:ticker>/documents')
class DocumentList(Resource):
    @document_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """List uploaded documents for a company"""
        try:
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            
            if not os.path.exists(upload_dir):
                return {
                    "success": True,
                    "data": {
                        "documents": [],
                        "total": 0
                    },
                    "message": "No documents found",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            
            documents = []
            content_files = []
            
            for file_name in os.listdir(upload_dir):
                if file_name.endswith('_content.json'):
                    content_files.append(file_name)
            
            for content_file in content_files:
                content_path = os.path.join(upload_dir, content_file)
                try:
                    with open(content_path, 'r', encoding='utf-8') as f:
                        doc_data = json.load(f)
                    
                    documents.append({
                        "upload_id": doc_data.get("upload_id"),
                        "filename": doc_data.get("original_filename"),
                        "upload_date": doc_data.get("upload_date"),
                        "document_type": doc_data.get("document_type"),
                        "status": doc_data.get("status", "unknown"),
                        "analysis_ready": doc_data.get("status") == "analysis_ready",
                        "analysis_approved": doc_data.get("status") == "analysis_approved", 
                        "report_generated": doc_data.get("status") == "report_generated",
                        "content_length": len(doc_data.get("document_content", "")),
                        "analysis_date": doc_data.get("analysis_date"),
                        "approval_date": doc_data.get("approval_date"),
                        "metadata": doc_data.get("metadata", {})
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to read content file {content_file}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "data": {
                    "documents": documents,
                    "total": len(documents)
                },
                "message": f"Documents for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to list documents for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve documents for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@document_bp.route('/companies/<string:ticker>/documents/analyze')
class DocumentBatchAnalysis(Resource):
    @document_bp.marshal_with(api_response_model)
    def post(self, ticker):
        """Trigger analysis for multiple uploaded documents"""
        logger.info(f"=== Starting batch analysis for ticker: {ticker} ===")
        
        try:
            # Parse request data
            data = request.get_json() or {}
            upload_ids = data.get('upload_ids', [])
            analysis_options = data.get('analysis_options', {})
            
            logger.info(f"Batch analysis request - Ticker: {ticker}, Upload IDs: {upload_ids}")
            
            if not upload_ids:
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No upload IDs provided",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            analysis_results = []
            failed_analyses = []
            
            # Process each document for analysis
            for upload_id in upload_ids:
                try:
                    logger.info(f"Starting analysis for upload_id: {upload_id}")
                    content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
                    
                    if not os.path.exists(content_file_path):
                        logger.warning(f"Content file not found for upload_id: {upload_id}")
                        failed_analyses.append({
                            "upload_id": upload_id,
                            "error": "Document not found"
                        })
                        continue
                    
                    # Load document data
                    with open(content_file_path, 'r', encoding='utf-8') as f:
                        content_data = json.load(f)
                    
                    # Skip if already analyzed (unless force re-analysis)
                    if content_data.get("status") == "analysis_ready" and not analysis_options.get("force_reanalysis", False):
                        logger.info(f"Skipping already analyzed document: {upload_id}")
                        # Still include the existing analysis in results
                        analysis_results.append({
                            "upload_id": upload_id,
                            "status": "already_analyzed",
                            "analysis": content_data.get("analysis", {}),
                            "analysis_date": content_data.get("analysis_date"),
                            "generation_metadata": content_data.get("generation_metadata", {}),
                            "context_sources": content_data.get("context_sources", [])
                        })
                        continue
                    
                    # Extract document info
                    document_content = content_data.get("document_content", "")
                    document_type = content_data.get("document_type", "other")
                    
                    if not document_content:
                        logger.warning(f"No document content found for upload_id: {upload_id}")
                        failed_analyses.append({
                            "upload_id": upload_id,
                            "error": "No document content available"
                        })
                        continue
                    
                    # Generate analysis (same logic as before but now triggered separately)
                    logger.info(f"Generating analysis for {upload_id}...")
                    
                    # Generate embedding for similarity search
                    doc_text_for_embedding = document_content[:2000]
                    doc_embedding = ai_service.generate_embedding(doc_text_for_embedding)
                    logger.debug(f"Document embedding generated for {upload_id}")
                    
                    # Search for similar documents with enhanced context retrieval
                    results = db_service.query_historical_financial_data(
                        ticker.upper(),
                        doc_embedding,
                        n_results=15,
                        prefer_recent=True
                    )
                    
                    context_documents = []
                    if results["documents"]:
                        for i in range(len(results["documents"][0])):
                            context_doc = {
                                "document": results["documents"][0][i],
                                "metadata": results["metadatas"][0][i],
                                "distance": results["distances"][0][i]
                            }
                            context_documents.append(context_doc)
                    
                    # Check for comprehensive financial data
                    try:
                        # Use comprehensive financial data for analysis
                        comprehensive_data = kb_service.get_comprehensive_financial_data(ticker.upper())
                        has_comprehensive = bool(comprehensive_data and comprehensive_data.get('has_data'))
                        logger.info(f"Comprehensive financial data available for {ticker}: {has_comprehensive}")
                    except Exception as e:
                        logger.warning(f"Failed to check comprehensive financial data: {str(e)}")
                        has_comprehensive = False
                        comprehensive_data = {}
                    
                    if has_comprehensive:
                        # Use comprehensive financial analysis with analyst estimates
                        logger.info(f"Using comprehensive financial analysis with analyst estimates for {upload_id}")
                        
                        # Get analyst estimates for this ticker
                        analyst_estimates = None
                        try:
                            targetDate = datetime(2025, 7, 30)
                            analyst_estimates = enhanced_parser.get_current_quarter_estimates_for_ai(ticker.upper(), targetDate)
                            logger.info(f"Successfully retrieved analyst estimates for comprehensive analysis of {ticker} ({len(analyst_estimates) if analyst_estimates else 0} characters), date {targetDate}")
                        except Exception as e:
                            logger.warning(f"Failed to retrieve analyst estimates for comprehensive analysis of {ticker}: {str(e)}")
                        
                        document_metrics = doc_service._extract_document_metrics(document_content, None)
                        comparative_data = doc_service._perform_comprehensive_financial_analysis(
                            ticker.upper(), document_metrics, comprehensive_data or {}, None
                        )
                        
                        initial_analysis = ai_service.generate_comparative_analysis(
                            document_content,
                            context_documents,
                            comparative_data,
                            content_data.get("document_type", "general"),
                            analyst_estimates  # Pass analyst estimates to comparative analysis
                        )
                        
                        initial_analysis["comparative_data"] = comparative_data
                        initial_analysis["document_metrics"] = document_metrics
                        initial_analysis["has_comprehensive_analysis"] = True
                        initial_analysis["has_analyst_estimates"] = bool(analyst_estimates)
                        
                        # Add analyst estimates to metadata for potential future use
                        if analyst_estimates:
                            initial_analysis["analyst_estimates_preview"] = analyst_estimates[:200] + "..." if len(analyst_estimates) > 200 else analyst_estimates
                        
                    else:
                        # No comprehensive financial data available - generate basic analysis with analyst estimates
                        logger.info(f"No comprehensive financial data available for {ticker}, generating basic analysis with analyst estimates for {upload_id}")
                        
                        # Get analyst estimates for this ticker
                        analyst_estimates = None
                        try:
                            targetDate = datetime(2025, 5, 30)
                            analyst_estimates = enhanced_parser.get_current_quarter_estimates_for_ai(ticker.upper(), targetDate)
                            logger.info(f"Successfully retrieved analyst estimates for {ticker} ({len(analyst_estimates) if analyst_estimates else 0} characters)")
                        except Exception as e:
                            logger.warning(f"Failed to retrieve analyst estimates for {ticker}: {str(e)}")
                        
                        initial_analysis = ai_service.generate_initial_analysis(
                            document_content, 
                            context_documents, 
                            content_data.get("document_type", "general"),
                            analyst_estimates  # Pass analyst estimates to AI service
                        )
                        initial_analysis["has_comprehensive_analysis"] = False
                        initial_analysis["has_analyst_estimates"] = bool(analyst_estimates)
                    
                    # Extract generation metadata
                    generation_metadata = initial_analysis.pop("_generation_metadata", {})
                    
                    # Update content data with analysis
                    content_data["analysis"] = initial_analysis
                    content_data["analysis_date"] = datetime.utcnow().isoformat() + "Z"
                    content_data["status"] = "analysis_ready"
                    content_data["generation_metadata"] = {
                        "prompt_used": generation_metadata.get("prompt_used", ""),
                        "model": generation_metadata.get("model", ""),
                        "temperature": generation_metadata.get("temperature", 0.3),
                        "max_tokens": generation_metadata.get("max_tokens", 2500),
                        "analysis_type": generation_metadata.get("analysis_type", "general"),
                        "context_documents_count": generation_metadata.get("context_documents_count", 0),
                        "generation_timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    content_data["context_sources"] = [
                        {
                            "type": "knowledge_base",
                            "document": doc["metadata"].get("file_name", "Unknown"),
                            "relevance_score": round(1.0 - doc["distance"], 2)
                        }
                        for doc in context_documents[:3]
                    ]
                    
                    # Save updated content with analysis
                    with open(content_file_path, 'w', encoding='utf-8') as f:
                        json.dump(content_data, f, indent=2, ensure_ascii=False)
                    
                    # Add to successful analysis results
                    analysis_results.append({
                        "upload_id": upload_id,
                        "status": "analysis_completed",
                        "analysis": initial_analysis,
                        "analysis_date": content_data["analysis_date"],
                        "generation_metadata": content_data["generation_metadata"],
                        "context_sources": content_data["context_sources"],
                        "document_info": {
                            "filename": content_data.get("original_filename"),
                            "document_type": content_data.get("document_type"),
                            "upload_date": content_data.get("upload_date")
                        }
                    })
                    
                    logger.info(f"Analysis completed successfully for {upload_id}")
                    
                except Exception as doc_error:
                    logger.error(f"Failed to analyze document {upload_id}: {str(doc_error)}")
                    failed_analyses.append({
                        "upload_id": upload_id,
                        "error": str(doc_error)
                    })
            
            # Prepare response
            response_data = {
                "analyzed_documents": analysis_results,
                "failed_analyses": failed_analyses,
                "total_requested": len(upload_ids),
                "successful_analyses": len(analysis_results),
                "failed_analyses_count": len(failed_analyses)
            }
            
            success_message = f"Batch analysis completed. {len(analysis_results)} successful, {len(failed_analyses)} failed."
            logger.info(f"Batch analysis results for {ticker}: {success_message}")
            
            return {
                "success": True,
                "data": response_data,
                "message": success_message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Batch analysis failed for {ticker}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            return {
                "success": False,
                "error": {
                    "code": "BATCH_ANALYSIS_ERROR",
                    "message": "Failed to perform batch analysis",
                    "details": {"error_type": type(e).__name__, "error_message": str(e)}
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500
