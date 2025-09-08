from flask_restx import Namespace, Resource, fields
import logging
from datetime import datetime

from app.config import config
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

# Initialize services
app_config = config['default']()
db_service = DatabaseService(app_config)

# API Namespace
health_bp = Namespace('health', description='System health operations')

# Response models
health_response_model = health_bp.model('HealthResponse', {
    'success': fields.Boolean(required=True, description='Health check success'),
    'data': fields.Raw(description='Health data'),
    'timestamp': fields.DateTime(description='Response timestamp')
})

@health_bp.route('/health')
class HealthCheck(Resource):
    @health_bp.marshal_with(health_response_model)
    def get(self):
        """Check system health and dependencies"""
        try:
            health_data = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0",
                "dependencies": {
                    "chroma_db": "unknown",
                    "openai_api": "unknown",
                    "file_system": "accessible"
                }
            }
            
            # Check ChromaDB
            try:
                # Try to list collections
                if hasattr(db_service, 'client') and db_service.client:
                    db_service.client.list_collections()
                    health_data["dependencies"]["chroma_db"] = "connected"
                else:
                    health_data["dependencies"]["chroma_db"] = "disconnected"
            except Exception as e:
                logger.warning(f"ChromaDB health check failed: {str(e)}")
                health_data["dependencies"]["chroma_db"] = "error"
            
            # Check OpenAI API
            try:
                import openai
                if app_config.OPENAI_API_KEY:
                    health_data["dependencies"]["openai_api"] = "configured"
                else:
                    health_data["dependencies"]["openai_api"] = "not_configured"
            except Exception as e:
                logger.warning(f"OpenAI health check failed: {str(e)}")
                health_data["dependencies"]["openai_api"] = "error"
            
            # Check file system
            import os
            try:
                if os.path.exists(app_config.DATA_ROOT_PATH):
                    health_data["dependencies"]["file_system"] = "accessible"
                else:
                    health_data["dependencies"]["file_system"] = "path_not_found"
            except Exception as e:
                logger.warning(f"File system health check failed: {str(e)}")
                health_data["dependencies"]["file_system"] = "error"
            
            # Determine overall status
            if any(dep in ["error", "disconnected", "not_configured"] for dep in health_data["dependencies"].values()):
                health_data["status"] = "degraded"
            
            return {
                "success": True,
                "data": health_data,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "success": False,
                "data": {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 503
