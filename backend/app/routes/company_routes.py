from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
import logging
import os
import threading
import time
from datetime import datetime

from app.config import config
from app.services.database_service import DatabaseService
from app.services.ai_service import AIService
from app.services.document_service import DocumentProcessingService
from app.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)

# In-memory job store for tracking background tasks
job_store = {}
job_store_lock = threading.Lock()

def update_job_status(job_id, status, progress=None, results=None, error=None):
    with job_store_lock:
        if job_id not in job_store:
            job_store[job_id] = {
                "job_id": job_id,
                "status": "pending",
                "progress": {"current": 0, "total": 0, "current_company": None},
                "results": [],
                "error": None,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        job_store[job_id]["status"] = status
        job_store[job_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        if progress:
            job_store[job_id]["progress"].update(progress)
        if results:
            job_store[job_id]["results"] = results
        if error:
            job_store[job_id]["error"] = error

# Initialize services
app_config = config['default']()
db_service = DatabaseService(app_config)
ai_service = AIService(app_config)
doc_service = DocumentProcessingService(app_config, ai_service)
kb_service = KnowledgeBaseService(app_config, db_service, doc_service)

# API Namespace
company_bp = Namespace('companies', description='Company management operations')

# Response models
company_stats_model = company_bp.model('CompanyStats', {
    'total_reports': fields.Integer(description='Number of processed reports'),
    'total_chunks': fields.Integer(description='Total document chunks'),
    'last_refresh': fields.DateTime(description='Last refresh timestamp')
})

company_model = company_bp.model('Company', {
    'ticker': fields.String(required=True, description='Company ticker symbol'),
    'company_name': fields.String(description='Company name'),
    'knowledge_base_status': fields.String(description='Knowledge base status'),
    'last_updated': fields.DateTime(description='Last update timestamp'),
    'stats': fields.Nested(company_stats_model, description='Company statistics')
})

api_response_model = company_bp.model('ApiResponse', {
    'success': fields.Boolean(required=True, description='Operation success status'),
    'data': fields.Raw(description='Response data'),
    'message': fields.String(description='Response message'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

error_response_model = company_bp.model('ErrorResponse', {
    'success': fields.Boolean(required=True, description='Operation success status'),
    'error': fields.Raw(description='Error details'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

@company_bp.route('/')
class CompanyList(Resource):
    @company_bp.marshal_with(api_response_model)
    def get(self):
        """Get list of all companies with statistics"""
        try:
            companies = kb_service.get_all_companies()
            
            response_data = {
                "companies": companies,
                "total_companies": len(companies)
            }
            
            return {
                "success": True,
                "data": response_data,
                "message": "Companies retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get companies: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve companies",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@company_bp.route('/<string:ticker>')
class CompanyDetail(Resource):
    @company_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """Get detailed information about a specific company"""
        try:
            company_data = kb_service.get_company_detail(ticker.upper())
            
            if not company_data:
                return {
                    "success": False,
                    "error": {
                        "code": "COMPANY_NOT_FOUND",
                        "message": f"Company {ticker.upper()} not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            return {
                "success": True,
                "data": company_data,
                "message": f"Company {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get company {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve company {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@company_bp.route('/<string:ticker>/investment-data')
class CompanyInvestmentData(Resource):
    @company_bp.marshal_with(api_response_model)
    def get(self, ticker):
        """Get investment data for a company"""
        try:
            # Query investment data from knowledge base
            investment_data = {}
            
            # Get investment thesis
            thesis_results = db_service.query_similar_documents(
                ticker.upper(), 
                [0.0] * 1536,  # Dummy embedding
                n_results=1,
                where_filter={"document_type": "investment_data", "data_type": "investmentthesis"}
            )
            
            if thesis_results["documents"] and len(thesis_results["documents"][0]) > 0:
                investment_data["investment_thesis"] = {
                    "content": thesis_results["documents"][0][0],
                    "last_updated": thesis_results["metadatas"][0][0].get("processed_date")
                }
            
            # Get investment drivers
            drivers_results = db_service.query_similar_documents(
                ticker.upper(),
                [0.0] * 1536,  # Dummy embedding
                n_results=1,
                where_filter={"document_type": "investment_data", "data_type": "investmentdrivers"}
            )
            
            if drivers_results["documents"] and len(drivers_results["documents"][0]) > 0:
                investment_data["investment_drivers"] = drivers_results["documents"][0][0]
            
            # Get risks
            risks_results = db_service.query_similar_documents(
                ticker.upper(),
                [0.0] * 1536,  # Dummy embedding
                n_results=1,
                where_filter={"document_type": "investment_data", "data_type": "risks"}
            )
            
            if risks_results["documents"] and len(risks_results["documents"][0]) > 0:
                investment_data["risks"] = risks_results["documents"][0][0]
            
            return {
                "success": True,
                "data": investment_data,
                "message": f"Investment data for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get investment data for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to retrieve investment data for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@company_bp.route('/refresh-all')
class RefreshAllCompanies(Resource):
    @company_bp.marshal_with(api_response_model)
    def post(self):
        """Start background refresh of knowledge base for all companies in the data folder"""
        try:
            # Generate unique job ID
            job_id = f"refresh_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 10000}"
            
            # Scan the research folder for company directories using DATA_ROOT_PATH from config
            data_research_path = os.path.join(app_config.DATA_ROOT_PATH, "research")
            company_tickers = []

            if os.path.exists(data_research_path):
                for item in os.listdir(data_research_path):
                    item_path = os.path.join(data_research_path, item)
                    # Only process directories (company folders) and skip hidden files
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        company_tickers.append(item.upper())

            logger.info(f"[Job {job_id}] Found {len(company_tickers)} companies in data folder: {company_tickers}")
            
            # Initialize job status
            update_job_status(job_id, "starting", progress={"current": 0, "total": len(company_tickers)})
            
            def background_refresh():
                """Background thread function to process all companies"""
                refresh_results = []
                total_processed = 0
                start_time = time.time()
                
                update_job_status(job_id, "running", progress={"current": 0, "total": len(company_tickers)})
                
                for i, ticker in enumerate(company_tickers, 1):
                    company_start_time = time.time()
                    
                    try:
                        logger.info(f"[Job {job_id}] Processing company {i}/{len(company_tickers)}: {ticker}")
                        update_job_status(job_id, "running", progress={
                            "current": i - 1, 
                            "total": len(company_tickers),
                            "current_company": ticker
                        })
                        
                        result = kb_service.refresh_knowledge_base(
                            ticker, 
                            force_reprocess=False,
                            include_investment_data=True
                        )
                        
                        company_duration = time.time() - company_start_time
                        logger.info(f"[Job {job_id}] Completed {ticker} in {company_duration:.2f}s - "
                                  f"Reports: {result.get('reports_processed', 0)}, "
                                  f"Documents: {result.get('total_documents', 0)}")
                        
                        refresh_results.append({
                            "ticker": ticker,
                            "status": "success",
                            "reports_processed": result.get("reports_processed", 0),
                            "investment_data_processed": result.get("investment_data_processed", False),
                            "total_documents": result.get("total_documents", 0),
                            "processing_time_seconds": round(company_duration, 2)
                        })
                        total_processed += 1
                        
                    except Exception as e:
                        company_duration = time.time() - company_start_time
                        logger.error(f"[Job {job_id}] Failed to refresh KB for {ticker} after {company_duration:.2f}s: {str(e)}")
                        refresh_results.append({
                            "ticker": ticker,
                            "status": "error",
                            "error": str(e),
                            "processing_time_seconds": round(company_duration, 2)
                        })
                    
                    # Update progress after each company
                    update_job_status(job_id, "running", progress={
                        "current": i, 
                        "total": len(company_tickers),
                        "current_company": None
                    })
                
                total_duration = time.time() - start_time
                logger.info(f"[Job {job_id}] Knowledge base refresh completed in {total_duration:.2f}s - "
                          f"Processed: {total_processed}/{len(company_tickers)}")
                
                # Mark job as completed
                update_job_status(job_id, "completed", results=refresh_results)
            
            # Start background thread
            thread = threading.Thread(target=background_refresh, daemon=True)
            thread.start()
            
            return {
                "success": True,
                "data": {
                    "job_id": job_id,
                    "total_companies": len(company_tickers),
                    "companies_found": company_tickers
                },
                "message": f"Knowledge base refresh started for {len(company_tickers)} companies",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to start knowledge base refresh: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": "Failed to start knowledge base refresh",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500

@company_bp.route('/refresh-status/<string:job_id>')
class RefreshJobStatus(Resource):
    @company_bp.marshal_with(api_response_model)
    def get(self, job_id):
        """Get the status of a refresh job"""
        try:
            with job_store_lock:
                job_data = job_store.get(job_id)
            
            if not job_data:
                return {
                    "success": False,
                    "error": {
                        "code": "JOB_NOT_FOUND",
                        "message": f"Job {job_id} not found",
                        "details": {}
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            return {
                "success": True,
                "data": job_data,
                "message": f"Job status retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": "Failed to retrieve job status",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500
