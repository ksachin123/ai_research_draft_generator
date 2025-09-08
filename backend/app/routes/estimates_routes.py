"""
Estimates Routes - API endpoints for managing estimates data processing and comparative analysis
"""

from flask import Blueprint, request, jsonify
from app.services.database_service import DatabaseService
from app.services.ai_service import AIService
from app.services.document_service import DocumentProcessingService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.config import Config
import logging
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

estimates_bp = Blueprint('estimates', __name__, url_prefix='/api/estimates')

# Initialize services
config = Config()
db_service = DatabaseService(config)
ai_service = AIService(config)
kb_service = KnowledgeBaseService(config, db_service, None)  # Will be updated with doc_service
doc_service = DocumentProcessingService(config, ai_service, kb_service)
# Update the knowledge base service with document service reference
kb_service.doc_service = doc_service

@estimates_bp.route('/<ticker>/refresh', methods=['POST'])
def refresh_estimates_data(ticker):
    """
    Refresh estimates data for a company from SVG files
    """
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
        
        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "result": result,
            "message": f"Successfully refreshed estimates data for {ticker.upper()}"
        })
        
    except Exception as e:
        logger.error(f"Failed to refresh estimates data for {ticker}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to refresh estimates data for {ticker}"
        }), 500

@estimates_bp.route('/<ticker>/data', methods=['GET'])
def get_estimates_data(ticker):
    """
    Get current estimates data for a company
    """
    try:
        logger.info(f"Getting estimates data for {ticker}")
        
        # Get estimates data
        estimates_data = kb_service.get_estimates_data(ticker.upper())
        
        if not estimates_data:
            return jsonify({
                "success": False,
                "message": f"No estimates data found for {ticker.upper()}",
                "data": {}
            })
        
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
        
        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "data": formatted_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get estimates data for {ticker}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to get estimates data for {ticker}"
        }), 500

@estimates_bp.route('/<ticker>/compare', methods=['POST'])
def generate_comparative_analysis(ticker):
    """
    Generate comparative analysis for uploaded document against estimates data
    """
    try:
        logger.info(f"Generating comparative analysis for {ticker}")
        
        if not request.is_json:
            return jsonify({
                "success": False,
                "message": "Request must be JSON"
            }), 400
        
        # Get request data
        document_text = request.json.get('document_text', '')
        document_date = request.json.get('document_date')
        analysis_type = request.json.get('analysis_type', 'comparative')
        
        if not document_text:
            return jsonify({
                "success": False,
                "message": "document_text is required"
            }), 400
        
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
        
        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "analysis": analysis_result,
            "comparative_data": comparative_data,
            "document_metrics": document_metrics,
            "context_documents_count": len(context_documents)
        })
        
    except Exception as e:
        logger.error(f"Failed to generate comparative analysis for {ticker}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to generate comparative analysis for {ticker}"
        }), 500

@estimates_bp.route('/<ticker>/segments', methods=['GET'])
def get_segment_estimates(ticker):
    """
    Get segment-specific estimates data for a company
    """
    try:
        logger.info(f"Getting segment estimates for {ticker}")
        
        # Get estimates data
        estimates_data = kb_service.get_estimates_data(ticker.upper())
        
        if not estimates_data:
            return jsonify({
                "success": False,
                "message": f"No estimates data found for {ticker.upper()}",
                "segments": {}
            })
        
        # Extract segment data from all financial statements
        segments = {}
        for statement_type in ['income_statement', 'balance_sheet', 'cash_flow']:
            if statement_type in estimates_data:
                segment_data = estimates_data[statement_type].get("segment_data", {})
                for segment_name, segment_info in segment_data.items():
                    if segment_name not in segments:
                        segments[segment_name] = {}
                    segments[segment_name][statement_type] = segment_info
        
        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "segments": segments
        })
        
    except Exception as e:
        logger.error(f"Failed to get segment estimates for {ticker}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to get segment estimates for {ticker}"
        }), 500

@estimates_bp.route('/<ticker>/margins', methods=['GET'])
def get_margin_estimates(ticker):
    """
    Get margin estimates data for a company
    """
    try:
        logger.info(f"Getting margin estimates for {ticker}")
        
        # Get estimates data
        estimates_data = kb_service.get_estimates_data(ticker.upper())
        
        if not estimates_data:
            return jsonify({
                "success": False,
                "message": f"No estimates data found for {ticker.upper()}",
                "margins": {}
            })
        
        # Extract margin data
        margins = {}
        income_statement = estimates_data.get("income_statement", {})
        if "margins" in income_statement:
            margins = income_statement["margins"]
        
        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "margins": margins
        })
        
    except Exception as e:
        logger.error(f"Failed to get margin estimates for {ticker}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to get margin estimates for {ticker}"
        }), 500

@estimates_bp.route('/available-tickers', methods=['GET'])
def get_available_tickers():
    """
    Get list of tickers that have estimates data available
    """
    try:
        logger.info("Getting available tickers with estimates data")
        
        import os
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
        
        return jsonify({
            "success": True,
            "tickers": tickers,
            "count": len(tickers)
        })
        
    except Exception as e:
        logger.error(f"Failed to get available tickers: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get available tickers"
        }), 500

@estimates_bp.errorhandler(404)
def estimates_not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "message": "The requested estimates endpoint does not exist"
    }), 404

@estimates_bp.errorhandler(500)
def estimates_server_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "An internal server error occurred while processing estimates request"
    }), 500
