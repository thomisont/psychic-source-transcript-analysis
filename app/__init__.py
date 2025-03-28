import sys
import os
from flask import Flask
from flask_cors import CORS
import logging
from dotenv import load_dotenv
from app.api.elevenlabs_client import ElevenLabsClient
import datetime
from app.services.conversation_service import ConversationService
from app.services.analysis_service import AnalysisService
from app.services.export_service import ExportService

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_app(test_config=None):
    # Load environment variables from .env file
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create app instance
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure CORS based on environment
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, only allow the production domain
        # If using a custom domain, it will come from BASE_URL
        from app.config import BASE_URL
        allowed_origins = [BASE_URL]
        app.logger.info(f"Production mode: CORS configured for {BASE_URL}")
        CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)
    else:
        # In development, allow all origins for easier testing
        app.logger.info("Development mode: CORS configured for all origins")
        CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    
    # Load configuration
    if test_config is None:
        # Load configuration from environment variables or config.py
        app.config.from_pyfile('config.py', silent=True)
        
        # Load additional configuration from the project config
        try:
            from config import Config
            app.config.from_object(Config)
        except ImportError:
            logging.warning("Could not import main config.py, using only environment variables")
    else:
        # Load test config if provided
        app.config.from_mapping(test_config)
    
    # Log the API key (just first few chars for security)
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if api_key:
        logging.info(f"Loaded ElevenLabs API key: {api_key[:5]}...")
    else:
        logging.warning("No ElevenLabs API key found")
        
    # Log if OpenAI key is available
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        logging.info(f"Loaded OpenAI API key: {openai_key[:5]}...")
    else:
        logging.warning("No OpenAI API key found, analysis features will use fallbacks")
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    
    # Add current date to context for templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now()}
    
    # Create and attach ElevenLabs client
    app.elevenlabs_client = ElevenLabsClient(
        api_key=os.getenv('ELEVENLABS_API_KEY', ''),
        agent_id=os.getenv('ELEVENLABS_AGENT_ID', '')
    )
    
    # Initialize and attach services
    app.conversation_service = ConversationService(app.elevenlabs_client)
    app.analysis_service = AnalysisService(lightweight_mode=False)
    app.export_service = ExportService()
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register API blueprint
    from app.api.routes import api
    app.register_blueprint(api, url_prefix='/api')
    
    # Add security headers in production
    if os.environ.get('FLASK_ENV') == 'production':
        @app.after_request
        def add_security_headers(response):
            # Strict-Transport-Security: Ensures the browser only uses HTTPS
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            # X-Content-Type-Options: Prevents browser from MIME-sniffing 
            response.headers['X-Content-Type-Options'] = 'nosniff'
            # X-Frame-Options: Prevents clickjacking by disallowing framing
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            # X-XSS-Protection: Browser's built-in XSS filtering
            response.headers['X-XSS-Protection'] = '1; mode=block'
            # Content Security Policy: Prevents various injection attacks
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com https://cdnjs.cloudflare.com; style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data:;"
            return response
        
        app.logger.info("Production security headers enabled")

    return app 