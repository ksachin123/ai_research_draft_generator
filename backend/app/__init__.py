from flask import Flask
from flask_restx import Api
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import os

# Disable ChromaDB telemetry to prevent telemetry errors
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
# Suppress ChromaDB telemetry logging errors
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

from app.config import config

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # CORS
    CORS(app, origins=['http://localhost:3000'])
    
    # API Documentation
    api = Api(
        app,
        version='1.0',
        title='AI Research Draft Generator API',
        description='REST API for investment research draft generation',
        doc='/swagger/'
    )
    
    # Register Blueprints - Import here to avoid circular imports
    from app.routes.company_routes import company_bp
    from app.routes.knowledge_base_routes import knowledge_base_bp
    from app.routes.document_routes import document_bp
    from app.routes.report_routes import report_bp
    from app.routes.health_routes import health_bp
    from app.routes.estimates_routes import estimates_bp
    from app.routes.batch_routes import batch_bp
    
    api.add_namespace(company_bp, path='/api/companies')
    api.add_namespace(knowledge_base_bp, path='/api')
    api.add_namespace(document_bp, path='/api')
    api.add_namespace(report_bp, path='/api')
    api.add_namespace(health_bp, path='/api')
    api.add_namespace(estimates_bp, path='/api/estimates')
    api.add_namespace(batch_bp, path='/api')
    
    # Configure Logging
    configure_logging(app)
    
    # Create required directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHROMA_DB_PATH'], exist_ok=True)
    
    return app

def configure_logging(app):
    # Always set up logging regardless of debug mode for development debugging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Set up file logging
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10240000, 
        backupCount=10
    )
    
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # Set log level based on configuration
    log_level = getattr(app.config, 'LOG_LEVEL', 'INFO')
    if log_level == 'DEBUG':
        file_handler.setLevel(logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
        app.logger.setLevel(logging.INFO)
    
    app.logger.addHandler(file_handler)
    
    # Add console handler for development
    if app.debug or os.environ.get('FLASK_ENV') == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        ))
        console_handler.setLevel(logging.DEBUG if log_level == 'DEBUG' else logging.INFO)
        
        # Add console handler to root logger to catch all module logs
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.DEBUG if log_level == 'DEBUG' else logging.INFO)
    
    app.logger.info('AI Research Draft Generator startup')
    app.logger.info(f'Log level set to: {log_level}')
    app.logger.info(f'Debug mode: {app.debug}')
    app.logger.info(f'Environment: {os.environ.get("FLASK_ENV", "not set")}')
    
    # Log configuration details for debugging
    app.logger.info(f'Upload folder: {getattr(app.config, "UPLOAD_FOLDER", "not configured")}')
    app.logger.info(f'OpenAI API key configured: {"Yes" if getattr(app.config, "OPENAI_API_KEY", None) else "No"}')
