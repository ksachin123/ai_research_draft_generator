import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    OPENAI_EMBEDDING_MODEL = os.environ.get('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002')
    
    # ChromaDB Configuration
    CHROMA_DB_PATH = os.environ.get('CHROMA_DB_PATH', './chroma_db')
    
    # File System Configuration
    # Use environment variables if set, otherwise default to project root relative paths
    env_data_path = os.environ.get('DATA_ROOT_PATH')
    if env_data_path:
        DATA_ROOT_PATH = os.path.abspath(env_data_path)
    else:
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        DATA_ROOT_PATH = os.path.join(PROJECT_ROOT, 'data')
    
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(DATA_ROOT_PATH, 'uploads'))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './data/uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    
    # Processing Configuration
    CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '1000'))
    CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', '200'))
    MAX_CONCURRENT_PROCESSING = int(os.environ.get('MAX_CONCURRENT_PROCESSING', '3'))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
