import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-dev-secret-key-change-me'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem' # Consider changing for production if needed
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    # Default Cache settings (can be overridden)
    CACHE_TYPE = 'SimpleCache' 
    CACHE_DEFAULT_TIMEOUT = 300
    
    # App specific configs loaded from env
    ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
    ELEVENLABS_AGENT_ID = os.environ.get('ELEVENLABS_AGENT_ID') or '3HFVw3nTZfIivPaHr3ne'
    ELEVENLABS_API_URL = os.environ.get('ELEVENLABS_API_URL', "https://api.elevenlabs.io")
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY') # Use SERVICE key for backend
    DATABASE_URL = os.environ.get('DATABASE_URL') # For SQLAlchemy

    # Default base URL, can be overridden
    BASE_URL = os.environ.get('BASE_URL') or 'http://localhost:8080' # Changed default port

    # Database configuration using DATABASE_URL
    @staticmethod
    def init_app(app):
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # Ensure the URL scheme is postgresql for SQLAlchemy
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        else:
            # Optionally, set a default local DB or raise an error
            # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dev.db' 
            print("WARNING: DATABASE_URL not set in environment variables.")
            # Consider raising an error if DB is essential: 
            # raise ValueError("DATABASE_URL environment variable is required.")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'
    # Example: Override base URL for dev if needed
    # BASE_URL = os.environ.get('DEV_BASE_URL', 'http://localhost:8080') 
    # Optionally use a different cache for dev
    # CACHE_TYPE = 'NullCache' 

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    # Ensure SECRET_KEY is set securely in production environment
    SECRET_KEY = os.environ.get('SECRET_KEY') 
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for production configuration.")

    # Example: Use Redis for session/cache in production
    # SESSION_TYPE = 'redis'
    # SESSION_REDIS = redis.from_url(os.environ.get('SESSION_REDIS_URL'))
    # CACHE_TYPE = 'RedisCache'
    # CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL')
    
    # Production base URL
    BASE_URL = os.environ.get('BASE_URL') or 'https://howislilydoing.org' 
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app) # Call base class init_app first
        
        # Production specific initializations can go here
        # Example: Configure logging for production
        import logging
        from logging.handlers import SysLogHandler # Or other appropriate handler
        # Configure production logging handler...
        pass

# Dictionary to map FLASK_ENV to configuration class
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # Fallback to development
} 