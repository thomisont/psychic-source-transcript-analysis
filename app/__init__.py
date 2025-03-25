from flask import Flask
from flask_cors import CORS
import datetime
from flask_wtf import CSRFProtect
from app.utils import configure_logging
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the ElevenLabsClient after adjusting the path
from app.api.elevenlabs_client import ElevenLabsClient

def create_app():
    # Create the app with explicit template_folder
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    print(f"DEBUG: Template directory: {template_dir}")
    print(f"DEBUG: Template files: {[f for f in os.listdir(template_dir) if f.endswith('.html')]}")
    
    # Configure application
    app.config.from_pyfile('config.py')
    
    # Configure CORS to allow all origins
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    
    # Set up CSRF protection
    csrf = CSRFProtect(app)
    
    # Configure logging
    configure_logging()
    
    # Add current date to context for templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now()}
    
    # Initialize the ElevenLabs client
    api_key = app.config.get('ELEVENLABS_API_KEY')
    agent_id = app.config.get('ELEVENLABS_AGENT_ID')
    api_url = app.config.get('ELEVENLABS_API_URL', 'https://api.elevenlabs.io')
    demo_mode = app.config.get('DEMO_MODE', '0') == '1'
    
    print(f"DEBUG: About to initialize ElevenLabsClient with: api_key={api_key[:5] if api_key else 'None'}..., agent_id={agent_id}")
    
    # Initialize the client with the updated constructor
    elevenlabs_client = ElevenLabsClient(
        api_key=api_key,
        agent_id=agent_id,
        api_url=api_url,
        demo_mode=demo_mode
    )
    
    # Test the connection
    elevenlabs_client.test_connection()
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register API routes
    from app.api.routes import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Make client available to routes
    app.elevenlabs_client = elevenlabs_client
    
    return app 