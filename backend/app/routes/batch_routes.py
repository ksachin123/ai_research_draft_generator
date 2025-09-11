from flask import request
from flask_restx import Namespace, Resource, fields
import logging
import os
import uuid
import json
from datetime import datetime
from typing import List, Dict

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
batch_bp = Namespace('batches', description='Document batch management operations')

# Response models
api_response_model = batch_bp.model('ApiResponse', {
    'success': fields.Boolean(required=True, description='Operation success status'),
    'data': fields.Raw(description='Response data'),
    'message': fields.String(description='Response message'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

@batch_bp.route('/companies/<string:ticker>/batches')
class BatchList(Resource):
    @batch_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """List all document batches for a company"""
        try:
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            batches = []
            
            if os.path.exists(upload_dir):
                # Look for batch files
                for filename in os.listdir(upload_dir):
                    if filename.startswith('batch_') and filename.endswith('.json'):
                        batch_path = os.path.join(upload_dir, filename)
                        try:
                            with open(batch_path, 'r', encoding='utf-8') as f:
                                batch_data = json.load(f)
                            
                            # Enrich batch data with analyzed documents if analysis is completed
                            if batch_data.get('analysis_status') == 'completed' and batch_data.get('upload_ids'):
                                analyzed_documents_data = []
                                for upload_id in batch_data.get('upload_ids', []):
                                    content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
                                    if os.path.exists(content_file_path):
                                        try:
                                            with open(content_file_path, 'r', encoding='utf-8') as content_file:
                                                content_data = json.load(content_file)
                                            
                                            if content_data.get('status') == 'analysis_ready' and content_data.get('analysis'):
                                                analyzed_doc = {
                                                    "upload_id": upload_id,
                                                    "document_info": {
                                                        "filename": content_data.get('original_filename', ''),
                                                        "upload_date": content_data.get('upload_date', ''),
                                                        "document_type": content_data.get('document_type', ''),
                                                        "description": content_data.get('description', '')
                                                    },
                                                    "analysis": content_data.get('analysis', {}),
                                                    "analysis_date": content_data.get('analysis_date', ''),
                                                    "status": content_data.get('status', ''),
                                                    "generation_metadata": content_data.get('generation_metadata', {}),
                                                    "context_sources": content_data.get('context_sources', [])
                                                }
                                                analyzed_documents_data.append(analyzed_doc)
                                        except Exception as e:
                                            logger.warning(f"Failed to load analyzed document {upload_id}: {str(e)}")
                                
                                # Add analyzed documents data to batch
                                batch_data["analyzed_documents_data"] = analyzed_documents_data
                            
                            batches.append(batch_data)
                        except Exception as e:
                            logger.warning(f"Failed to load batch file {filename}: {str(e)}")
                            continue
            
            # Sort batches by creation date (newest first)
            batches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return {
                "success": True,
                "data": {"batches": batches},
                "message": f"Found {len(batches)} batches for {ticker}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to list batches for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "BATCH_LIST_ERROR",
                    "message": "Failed to list batches",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

    @batch_bp.marshal_with(api_response_model)
    def post(self, ticker):
        """Create a new document batch"""
        try:
            data = request.get_json() or {}
            upload_ids = data.get('upload_ids', [])
            batch_name = data.get('name', '')
            description = data.get('description', '')
            
            if not upload_ids:
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No upload IDs provided for batch",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            # Generate batch ID with timestamp
            timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            batch_id = f"batch_{ticker.lower()}_{timestamp_str}_{uuid.uuid4().hex[:8]}"
            
            # Create batch directory
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            os.makedirs(upload_dir, exist_ok=True)
            
            # Validate that all upload_ids exist
            valid_uploads = []
            for upload_id in upload_ids:
                content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
                if os.path.exists(content_file_path):
                    try:
                        with open(content_file_path, 'r', encoding='utf-8') as f:
                            upload_data = json.load(f)
                        valid_uploads.append({
                            "upload_id": upload_id,
                            "filename": upload_data.get('original_filename', 'unknown'),
                            "document_type": upload_data.get('document_type', 'unknown'),
                            "upload_date": upload_data.get('upload_date', ''),
                            "status": upload_data.get('status', 'unknown')
                        })
                    except Exception as e:
                        logger.warning(f"Failed to load upload {upload_id}: {str(e)}")
                        continue
            
            if not valid_uploads:
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No valid uploads found for batch creation",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            # Create batch metadata
            batch_data = {
                "batch_id": batch_id,
                "ticker": ticker.upper(),
                "name": batch_name or f"Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                "description": description,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "status": "created",
                "upload_ids": upload_ids,
                "documents": valid_uploads,
                "analysis_status": "pending",
                "report_status": "pending"
            }
            
            # Save batch file
            batch_file_path = os.path.join(upload_dir, f"{batch_id}.json")
            with open(batch_file_path, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created batch {batch_id} for {ticker} with {len(valid_uploads)} documents")
            
            return {
                "success": True,
                "data": {"batch": batch_data},
                "message": f"Batch created successfully with {len(valid_uploads)} documents",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to create batch for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "BATCH_CREATE_ERROR",
                    "message": "Failed to create batch",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@batch_bp.route('/companies/<string:ticker>/batches/<string:batch_id>')
class BatchDetail(Resource):
    @batch_bp.marshal_with(api_response_model)
    def get(self, ticker, batch_id):
        """Get details of a specific batch"""
        try:
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            batch_file_path = os.path.join(upload_dir, f"{batch_id}.json")
            
            if not os.path.exists(batch_file_path):
                return {
                    "success": False,
                    "error": {
                        "code": "BATCH_NOT_FOUND",
                        "message": "Batch not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            with open(batch_file_path, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            # Enrich batch data with analyzed documents if analysis is completed
            if batch_data.get('analysis_status') == 'completed' and batch_data.get('upload_ids'):
                analyzed_documents_data = []
                for upload_id in batch_data.get('upload_ids', []):
                    content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
                    if os.path.exists(content_file_path):
                        try:
                            with open(content_file_path, 'r', encoding='utf-8') as content_file:
                                content_data = json.load(content_file)
                            
                            if content_data.get('status') == 'analysis_ready' and content_data.get('analysis'):
                                analyzed_doc = {
                                    "upload_id": upload_id,
                                    "document_info": {
                                        "filename": content_data.get('original_filename', ''),
                                        "upload_date": content_data.get('upload_date', ''),
                                        "document_type": content_data.get('document_type', ''),
                                        "description": content_data.get('description', '')
                                    },
                                    "analysis": content_data.get('analysis', {}),
                                    "analysis_date": content_data.get('analysis_date', ''),
                                    "status": content_data.get('status', ''),
                                    "generation_metadata": content_data.get('generation_metadata', {}),
                                    "context_sources": content_data.get('context_sources', [])
                                }
                                analyzed_documents_data.append(analyzed_doc)
                        except Exception as e:
                            logger.warning(f"Failed to load analyzed document {upload_id}: {str(e)}")
                
                # Add analyzed documents data to batch
                batch_data["analyzed_documents_data"] = analyzed_documents_data
            
            return {
                "success": True,
                "data": {"batch": batch_data},
                "message": "Batch retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get batch {batch_id} for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "BATCH_GET_ERROR",
                    "message": "Failed to retrieve batch",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

    @batch_bp.marshal_with(api_response_model)
    def delete(self, ticker, batch_id):
        """Delete a specific batch"""
        try:
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            batch_file_path = os.path.join(upload_dir, f"{batch_id}.json")
            
            if not os.path.exists(batch_file_path):
                return {
                    "success": False,
                    "error": {
                        "code": "BATCH_NOT_FOUND",
                        "message": "Batch not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            # Remove the batch file
            os.remove(batch_file_path)
            
            logger.info(f"Deleted batch {batch_id} for {ticker}")
            
            return {
                "success": True,
                "data": {"deleted_batch_id": batch_id},
                "message": "Batch deleted successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete batch {batch_id} for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "BATCH_DELETE_ERROR",
                    "message": "Failed to delete batch",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@batch_bp.route('/companies/<string:ticker>/batches/<string:batch_id>/analyze')
class BatchAnalysis(Resource):
    @batch_bp.marshal_with(api_response_model)
    def post(self, ticker, batch_id):
        """Trigger analysis for a document batch"""
        try:
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            batch_file_path = os.path.join(upload_dir, f"{batch_id}.json")
            
            if not os.path.exists(batch_file_path):
                return {
                    "success": False,
                    "error": {
                        "code": "BATCH_NOT_FOUND",
                        "message": "Batch not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            # Load batch data
            with open(batch_file_path, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            upload_ids = batch_data.get('upload_ids', [])
            if not upload_ids:
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No documents in batch to analyze",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            logger.info(f"Starting batch analysis for {batch_id} with {len(upload_ids)} documents")
            
            # Update batch status
            batch_data["analysis_status"] = "in_progress"
            batch_data["analysis_started_at"] = datetime.utcnow().isoformat() + "Z"
            
            # Save updated batch
            with open(batch_file_path, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2, ensure_ascii=False)
            
            # Process each document in the batch (similar to existing batch analysis)
            analysis_results = []
            failed_analyses = []
            
            for upload_id in upload_ids:
                try:
                    # Load document content
                    content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
                    if not os.path.exists(content_file_path):
                        failed_analyses.append({
                            "upload_id": upload_id,
                            "error": "Document content file not found"
                        })
                        continue
                    
                    with open(content_file_path, 'r', encoding='utf-8') as f:
                        document_data = json.load(f)
                    
                    document_text = document_data.get('document_content', '')
                    if not document_text:
                        failed_analyses.append({
                            "upload_id": upload_id,
                            "error": "Document content is empty"
                        })
                        continue
                    
                    # Generate analysis (reusing existing logic)
                    logger.info(f"Analyzing document {upload_id} in batch {batch_id}")
                    
                    # Get analyst estimates for this ticker
                    analyst_estimates = None
                    try:
                        targetDate = datetime(2025, 5, 30)
                        analyst_estimates = enhanced_parser.get_current_quarter_estimates_for_ai(ticker.upper(), targetDate)
                        logger.info(f"Successfully retrieved analyst estimates for batch analysis of {ticker} ({len(analyst_estimates) if analyst_estimates else 0} characters)")
                    except Exception as e:
                        logger.warning(f"Failed to retrieve analyst estimates for batch analysis of {ticker}: {str(e)}")
                    
                    # Generate embedding for similarity search
                    doc_embedding = ai_service.generate_embedding(document_text[:2000])
                    
                    # Query historical financial data with priority
                    results = db_service.query_historical_financial_data(
                        ticker.upper(),
                        doc_embedding,
                        n_results=10,
                        prefer_recent=True
                    )
                    
                    context_documents = []
                    if results and results.get("documents"):
                        for i in range(len(results["documents"][0])):
                            context_documents.append({
                                "content": results["documents"][0][i],
                                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                                "distance": results["distances"][0][i] if results.get("distances") else 0
                            })
                    
                    # Generate initial analysis for batch document with analyst estimates
                    analysis = ai_service.generate_initial_analysis(
                        document_text,
                        context_documents,
                        "comprehensive",
                        analyst_estimates
                    )
                    
                    # Add analyst estimates metadata to analysis
                    analysis["has_analyst_estimates"] = bool(analyst_estimates)
                    if analyst_estimates:
                        analysis["analyst_estimates_preview"] = analyst_estimates[:200] + "..." if len(analyst_estimates) > 200 else analyst_estimates
                    
                    # Extract generation metadata and ensure it's properly structured
                    generation_metadata = analysis.pop("_generation_metadata", {})
                    
                    # Update document with analysis
                    document_data["analysis"] = analysis
                    document_data["analysis_date"] = datetime.utcnow().isoformat() + "Z"
                    document_data["status"] = "analysis_ready"
                    document_data["batch_id"] = batch_id
                    document_data["generation_metadata"] = {
                        "prompt_used": generation_metadata.get("prompt_used", ""),
                        "model": generation_metadata.get("model", ""),
                        "temperature": generation_metadata.get("temperature", 0.3),
                        "max_tokens": generation_metadata.get("max_tokens", 3000),
                        "analysis_type": generation_metadata.get("analysis_type", "comprehensive"),
                        "context_documents_count": generation_metadata.get("context_documents_count", 0),
                        "analyst_estimates_included": generation_metadata.get("analyst_estimates_included", False),
                        "analyst_estimates_length": generation_metadata.get("analyst_estimates_length", 0),
                        "generation_timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    document_data["context_sources"] = context_documents
                    
                    # Save updated document
                    with open(content_file_path, 'w', encoding='utf-8') as f:
                        json.dump(document_data, f, indent=2, ensure_ascii=False)
                    
                    # Add to results
                    analysis_results.append({
                        "upload_id": upload_id,
                        "document_info": {
                            "filename": document_data.get('original_filename', ''),
                            "upload_date": document_data.get('upload_date', ''),
                            "document_type": document_data.get('document_type', ''),
                            "description": document_data.get('description', '')
                        },
                        "analysis": analysis,
                        "analysis_date": document_data["analysis_date"],
                        "status": "analysis_ready",
                        "generation_metadata": document_data["generation_metadata"],
                        "context_sources": context_documents
                    })
                    
                    logger.info(f"Analysis completed for document {upload_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to analyze document {upload_id}: {str(e)}")
                    failed_analyses.append({
                        "upload_id": upload_id,
                        "error": str(e)
                    })
            
            # Update batch with analysis results
            batch_data["analysis_status"] = "completed" if not failed_analyses else "partial"
            batch_data["analysis_completed_at"] = datetime.utcnow().isoformat() + "Z"
            batch_data["analyzed_documents"] = len(analysis_results)
            batch_data["failed_documents"] = len(failed_analyses)
            
            # Save final batch state
            with open(batch_file_path, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2, ensure_ascii=False)
            
            success_message = f"Batch analysis completed. {len(analysis_results)} successful, {len(failed_analyses)} failed."
            logger.info(f"Batch analysis results for {batch_id}: {success_message}")
            
            return {
                "success": True,
                "data": {
                    "batch_id": batch_id,
                    "analyzed_documents": analysis_results,
                    "failed_analyses": failed_analyses,
                    "successful_analyses": len(analysis_results),
                    "total_documents": len(upload_ids),
                    "batch_status": batch_data["analysis_status"]
                },
                "message": success_message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Batch analysis failed for {batch_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "BATCH_ANALYSIS_ERROR",
                    "message": "Failed to perform batch analysis",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@batch_bp.route('/companies/<string:ticker>/batches/<string:batch_id>/report')
class BatchReportGeneration(Resource):
    @batch_bp.marshal_with(api_response_model) 
    def post(self, ticker, batch_id):
        """Generate a comprehensive report for the entire batch"""
        try:
            upload_dir = os.path.join(app_config.UPLOAD_FOLDER, ticker.upper())
            batch_file_path = os.path.join(upload_dir, f"{batch_id}.json")
            
            if not os.path.exists(batch_file_path):
                return {
                    "success": False,
                    "error": {
                        "code": "BATCH_NOT_FOUND",
                        "message": "Batch not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            # Load batch data
            with open(batch_file_path, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            # Check if batch analysis is complete
            if batch_data.get("analysis_status") not in ["completed", "partial"]:
                return {
                    "success": False,
                    "error": {
                        "code": "ANALYSIS_NOT_READY",
                        "message": "Batch analysis must be completed before report generation",
                        "details": {"current_status": batch_data.get("analysis_status", "unknown")}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            # Collect raw AI responses and analyst estimates from the batch
            raw_ai_responses = []
            analyst_estimates = None
            
            for upload_id in batch_data.get('upload_ids', []):
                content_file_path = os.path.join(upload_dir, f"{upload_id}_content.json")
                if os.path.exists(content_file_path):
                    try:
                        with open(content_file_path, 'r', encoding='utf-8') as f:
                            document_data = json.load(f)
                        
                        # Get the raw AI response
                        analysis = document_data.get('analysis', {})
                        if analysis.get('_raw_ai_response'):
                            raw_ai_responses.append(analysis['_raw_ai_response'])
                        
                        # Get analyst estimates from the first document that has them
                        if analyst_estimates is None and analysis.get('analyst_estimates_preview'):
                            analyst_estimates = analysis['analyst_estimates_preview']
                            
                    except Exception as e:
                        logger.warning(f"Failed to load analysis for {upload_id}: {str(e)}")
                        continue
            
            if not raw_ai_responses:
                return {
                    "success": False,
                    "error": {
                        "code": "NO_RAW_AI_RESPONSE_DATA",
                        "message": "No raw AI response data found for enhanced batch report generation",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 400
            
            # Generate enhanced batch report using raw AI responses
            logger.info(f"Generating enhanced batch report for {batch_id} with {len(raw_ai_responses)} raw AI responses")
            
            # Use analyst estimates or empty string if not available
            if analyst_estimates is None:
                analyst_estimates = ""
            
            # Generate the enhanced batch report using raw AI responses as context
            report_content = ai_service.generate_enhanced_batch_report(
                raw_ai_responses=raw_ai_responses,
                analyst_estimates=analyst_estimates,
                ticker=ticker,
                batch_info={
                    "name": batch_data.get("name", ""),
                    "description": batch_data.get("description", ""),
                    "document_count": len(batch_data.get("upload_ids", []))
                }
            )
            
            # Update batch with report information
            batch_data["report_status"] = "generated"
            batch_data["report_generated_at"] = datetime.utcnow().isoformat() + "Z"
            batch_data["report_content"] = report_content
            
            # Save updated batch
            with open(batch_file_path, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Batch report generated successfully for {batch_id}")
            
            return {
                "success": True,
                "data": {
                    "batch_id": batch_id,
                    "report": report_content,
                    "generated_at": batch_data["report_generated_at"],
                    "documents_analyzed": len(raw_ai_responses)
                },
                "message": "Batch report generated successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate batch report for {batch_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "BATCH_REPORT_ERROR",
                    "message": "Failed to generate batch report",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500
