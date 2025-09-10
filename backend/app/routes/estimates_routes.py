"""
Estimates Routes - API endpoints for managing estimates data processing and comparative analysis
"""

from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.database_service import DatabaseService
from app.services.ai_service import AIService
from app.services.document_service import DocumentProcessingService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.config import Config
import logging
from datetime import datetime
import traceback
import os

logger = logging.getLogger(__name__)

estimates_bp = Namespace('estimates', description='Estimates data processing and comparative analysis operations')

# Initialize services
config = Config()
db_service = DatabaseService(config)
ai_service = AIService(config)
kb_service = KnowledgeBaseService(config, db_service, None)
doc_service = DocumentProcessingService(config, ai_service, kb_service)
kb_service.doc_service = doc_service

# Define request/response models
refresh_request_model = estimates_bp.model('RefreshRequest', {
    'force_reprocess': fields.Boolean(default=False, description='Force reprocessing of all files')
})

refresh_response_model = estimates_bp.model('RefreshResponse', {
    'success': fields.Boolean(required=True, description='Success status'),
    'ticker': fields.String(required=True, description='Company ticker'),
    'result': fields.Raw(description='Refresh operation results'),
    'message': fields.String(description='Response message')
})

estimates_data_model = estimates_bp.model('EstimatesData', {
    'ticker': fields.String(required=True, description='Company ticker'),
    'last_updated': fields.String(description='Last update timestamp'),
    'financial_statements': fields.Raw(description='Financial statements data')
})

compare_request_model = estimates_bp.model('CompareRequest', {
    'document_text': fields.String(required=True, description='Document text to analyze'),
    'document_date': fields.String(description='Document date in ISO format'),
    'analysis_type': fields.String(default='comparative', description='Type of analysis to perform')
})

compare_response_model = estimates_bp.model('CompareResponse', {
    'success': fields.Boolean(required=True, description='Success status'),
    'ticker': fields.String(required=True, description='Company ticker'),
    'analysis': fields.Raw(description='Analysis results'),
    'comparative_data': fields.Raw(description='Comparative analysis data'),
    'document_metrics': fields.Raw(description='Extracted document metrics'),
    'context_documents_count': fields.Integer(description='Number of context documents used')
})

@estimates_bp.route('/<ticker>/refresh')
@estimates_bp.doc('refresh_estimates_data')
class RefreshEstimatesData(Resource):
    @estimates_bp.expect(refresh_request_model)
    @estimates_bp.marshal_with(refresh_response_model)
    def post(self, ticker):
        """Refresh estimates data for a company from SVG files"""
        try:
            logger.info(f"Refreshing estimates data for {ticker}")
            
            # Get request parameters
            force_reprocess = request.json.get('force_reprocess', False) if request.is_json else False
            
            # Refresh knowledge base including estimates data
            result = kb_service.refresh_knowledge_base(
                ticker=ticker.upper(),
                force_reprocess=force_reprocess,
                include_investment_data=True,
                include_estimates=True
            )
            
            return {
                "success": True,
                "ticker": ticker.upper(),
                "result": result,
                "message": f"Successfully refreshed estimates data for {ticker.upper()}"
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh estimates data for {ticker}: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to refresh estimates data for {ticker}"
            }, 500

@estimates_bp.route('/<ticker>/data')
@estimates_bp.doc('get_estimates_data')
class GetEstimatesData(Resource):
    @estimates_bp.marshal_with(estimates_data_model)
    def get(self, ticker):
        """Get current estimates data for a company"""
        try:
            logger.info(f"Getting estimates data for {ticker}")
            
            # Get estimates data
            estimates_data = kb_service.get_estimates_data(ticker.upper())
            
            if not estimates_data:
                # Return empty structure matching model instead of unrelated keys (marshal strips others)
                return {
                    "ticker": ticker.upper(),
                    "last_updated": None,
                    "financial_statements": {}
                }, 404
            
            # Format the response
            formatted_data = {
                "ticker": estimates_data.get("ticker", ticker.upper()),
                "last_updated": datetime.fromtimestamp(estimates_data.get("last_updated", 0)).isoformat() if estimates_data.get("last_updated") else None,
                "financial_statements": {}
            }
            
            # Add financial statement data
            for statement_type in ['income_statement', 'balance_sheet', 'cash_flow']:
                if statement_type in estimates_data:
                    statement_data = estimates_data[statement_type]
                    formatted_data["financial_statements"][statement_type] = {
                        "segment_data": statement_data.get("segment_data", {}),
                        "margins": statement_data.get("margins", {}),
                        "quarterly_data": statement_data.get("quarterly_data", []),
                        "estimates": statement_data.get("estimates", {})
                    }
            # Return the formatted data directly so flask_restx marshalling populates model fields
            return formatted_data
            
        except Exception as e:
            logger.error(f"Failed to get estimates data for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get estimates data for {ticker}"
            }, 500

@estimates_bp.route('/<ticker>/compare')
@estimates_bp.doc('generate_comparative_analysis')
class GenerateComparativeAnalysis(Resource):
    @estimates_bp.expect(compare_request_model)
    @estimates_bp.marshal_with(compare_response_model)
    def post(self, ticker):
        """Generate comparative analysis for uploaded document against estimates data"""
        try:
            logger.info(f"Generating comparative analysis for {ticker}")
            
            # Get request data
            document_text = request.json.get('document_text', '')
            document_date = request.json.get('document_date')
            analysis_type = request.json.get('analysis_type', 'comparative')
            
            if not document_text:
                return {
                    "success": False,
                    "message": "document_text is required"
                }, 400
            
            # Parse document date if provided
            parsed_date = None
            if document_date:
                try:
                    parsed_date = datetime.fromisoformat(document_date.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid date format: {document_date}")
            
            # Get relevant context documents
            query_embedding = ai_service.generate_embedding(document_text)
            context_documents = db_service.query_similar_documents(
                ticker.upper(), 
                query_embedding, 
                n_results=10
            )
            
            # Extract document metrics and get comparative data
            document_metrics = doc_service._extract_document_metrics(document_text, parsed_date)
            estimates_data = kb_service.get_estimates_data(ticker.upper())
            
            comparative_data = {}
            if estimates_data:
                comparative_data = doc_service._perform_comparative_analysis(
                    ticker.upper(), document_metrics, estimates_data, parsed_date
                )
            
            # Generate AI analysis with comparative insights
            if comparative_data:
                analysis_result = ai_service.generate_comparative_analysis(
                    document_text,
                    context_documents,
                    comparative_data,
                    analysis_type
                )
            else:
                # Fall back to regular analysis if no estimates data  
                analysis_result = ai_service.generate_report_draft(
                    document_text,
                    context_documents,
                    analysis_type
                )
            
            # Check if comprehensive financial data is also available
            has_comprehensive_data = False
            try:
                comprehensive_data = kb_service.get_comprehensive_financial_data(ticker.upper())
                has_comprehensive_data = bool(comprehensive_data and comprehensive_data.get('has_data'))
            except Exception:
                pass
            
            return {
                "success": True,
                "ticker": ticker.upper(),
                "analysis": analysis_result,
                "comparative_data": comparative_data,
                "document_metrics": document_metrics,
                "context_documents_count": len(context_documents),
                "has_estimates_comparison": bool(comparative_data),
                "has_comprehensive_analysis": has_comprehensive_data
            }
            
        except Exception as e:
            logger.error(f"Failed to generate comparative analysis for {ticker}: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to generate comparative analysis for {ticker}"
            }, 500

@estimates_bp.route('/<ticker>/segments')
@estimates_bp.doc('get_segment_estimates')
class GetSegmentEstimates(Resource):
    def get(self, ticker):
        """Get segment-specific estimates data for a company"""
        try:
            logger.info(f"Getting segment estimates for {ticker}")
            
            # Get estimates data
            estimates_data = kb_service.get_estimates_data(ticker.upper())
            
            if not estimates_data:
                return {
                    "success": False,
                    "message": f"No estimates data found for {ticker.upper()}",
                    "segments": {}
                }, 404
            
            # Extract segment data from all financial statements
            segments = {}
            for statement_type in ['income_statement', 'balance_sheet', 'cash_flow']:
                if statement_type in estimates_data:
                    segment_data = estimates_data[statement_type].get("segment_data", {})
                    for segment_name, segment_info in segment_data.items():
                        if segment_name not in segments:
                            segments[segment_name] = {}
                        segments[segment_name][statement_type] = segment_info
            
            return {
                "success": True,
                "ticker": ticker.upper(),
                "segments": segments
            }
            
        except Exception as e:
            logger.error(f"Failed to get segment estimates for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get segment estimates for {ticker}"
            }, 500

@estimates_bp.route('/<ticker>/margins')
@estimates_bp.doc('get_margin_estimates')
class GetMarginEstimates(Resource):
    def get(self, ticker):
        """Get margin estimates data for a company"""
        try:
            logger.info(f"Getting margin estimates for {ticker}")
            
            # Get estimates data
            estimates_data = kb_service.get_estimates_data(ticker.upper())
            
            if not estimates_data:
                return {
                    "success": False,
                    "message": f"No estimates data found for {ticker.upper()}",
                    "margins": {}
                }, 404
            
            # Extract margin data
            margins = {}
            income_statement = estimates_data.get("income_statement", {})
            if "margins" in income_statement:
                margins = income_statement["margins"]
            
            return {
                "success": True,
                "ticker": ticker.upper(),
                "margins": margins
            }
            
        except Exception as e:
            logger.error(f"Failed to get margin estimates for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get margin estimates for {ticker}"
            }, 500

@estimates_bp.route('/available-tickers')
@estimates_bp.doc('get_available_tickers')
class GetAvailableTickers(Resource):
    def get(self):
        """Get list of tickers that have estimates data available"""
        try:
            logger.info("Getting available tickers with estimates data")
            
            research_path = os.path.join(config.DATA_ROOT_PATH, "research")
            tickers = []
            
            if os.path.exists(research_path):
                for item in os.listdir(research_path):
                    estimates_path = os.path.join(research_path, item, "estimates")
                    if os.path.isdir(estimates_path):
                        # Check if estimates folder has SVG files
                        svg_files = [f for f in os.listdir(estimates_path) if f.endswith('.svg')]
                        if svg_files:
                            tickers.append({
                                "ticker": item,
                                "estimates_files": svg_files,
                                "last_updated": max([
                                    os.path.getmtime(os.path.join(estimates_path, f)) 
                                    for f in svg_files
                                ])
                            })
            
            # Sort by last updated (most recent first)
            tickers.sort(key=lambda x: x["last_updated"], reverse=True)
            
            return {
                "success": True,
                "tickers": tickers,
                "count": len(tickers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get available tickers: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get available tickers"
            }, 500


# Import enhanced parser for current quarter estimates
from app.services.enhanced_svg_parser import create_enhanced_financial_parser

# Initialize enhanced parser
enhanced_parser = create_enhanced_financial_parser(config)


@estimates_bp.route('/<string:ticker>/current-quarter')
@estimates_bp.doc('get_current_quarter_estimates')
class CurrentQuarterEstimates(Resource):
    @estimates_bp.doc('get_current_quarter_estimates',
                     description='Get current quarter analyst estimates for a ticker')
    def get(self, ticker):
        """Get current quarter estimates for a ticker"""
        try:
            logger.info(f"Getting current quarter estimates for {ticker}")
            
            # Get estimates data
            estimates = enhanced_parser.get_current_quarter_estimates(ticker)
            
            if not estimates:
                return {
                    "success": False,
                    "error": {
                        "code": "NO_ESTIMATES_FOUND",
                        "message": f"No current quarter estimates found for {ticker.upper()}",
                        "details": "Check if SVG files exist in the estimates folder"
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            return {
                "success": True,
                "data": estimates,
                "message": f"Current quarter estimates for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get current quarter estimates for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "ESTIMATES_EXTRACTION_ERROR",
                    "message": f"Failed to retrieve current quarter estimates for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500


@estimates_bp.route('/<string:ticker>/current-quarter/ai-format')
@estimates_bp.doc('get_current_quarter_estimates_ai')
class CurrentQuarterEstimatesAIFormat(Resource):
    @estimates_bp.doc('get_current_quarter_estimates_ai',
                     description='Get current quarter estimates formatted for AI prompts')
    def get(self, ticker):
        """Get current quarter estimates formatted for AI prompts"""
        try:
            targetDate = datetime(2025, 5, 30)
            logger.info(f"Getting AI-formatted current quarter estimates for {ticker}, target date {targetDate}")
            
            # Get AI-formatted estimates
            ai_formatted_text = enhanced_parser.get_current_quarter_estimates_for_ai(ticker, targetDate)
            
            if not ai_formatted_text or ai_formatted_text.startswith("Error"):
                return {
                    "success": False,
                    "error": {
                        "code": "NO_AI_FORMAT_AVAILABLE",
                        "message": f"No AI-formatted estimates available for {ticker.upper()}",
                        "details": ai_formatted_text if ai_formatted_text.startswith("Error") else "No estimates data found"
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, 404
            
            return {
                "success": True,
                "data": {
                    "ticker": ticker.upper(),
                    "ai_formatted_text": ai_formatted_text,
                    "text_length": len(ai_formatted_text),
                    "ready_for_prompt": True
                },
                "message": f"AI-formatted current quarter estimates for {ticker.upper()} retrieved successfully",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get AI-formatted current quarter estimates for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "AI_FORMAT_ERROR",
                    "message": f"Failed to retrieve AI-formatted estimates for {ticker.upper()}",
                    "details": str(e)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 500
