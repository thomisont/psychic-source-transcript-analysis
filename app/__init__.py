import sys
import os
from flask import Flask
from flask_cors import CORS
import logging
from dotenv import load_dotenv
from app.api.elevenlabs_client import ElevenLabsClient
import datetime

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
    
    # Configure CORS to allow all origins
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
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register API blueprint
    from app.api.routes import api
    app.register_blueprint(api, url_prefix='/api')
    
    return app 