import sys
import os
from flask import Flask, g, current_app
from flask_cors import CORS
import logging
from dotenv import load_dotenv
import nltk
# Import extensions from the new file
from app.extensions import db, migrate
# Move client and service imports inside create_app
# from app.api.elevenlabs_client import ElevenLabsClient
# import datetime
# from app.services.conversation_service import ConversationService
# from app.services.analysis_service import AnalysisService
# from app.services.export_service import ExportService
from flask_caching import Cache
from tools.supabase_client import SupabaseClient

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Remove global instantiations from here
# db = SQLAlchemy()
# migrate = Migrate()

# Import models here after db initialization
# from app.models import Conversation, Message  # noqa

# Initialize services
from app.services.analysis_service import AnalysisService
from app.services.data_service import DataService

# Global services
# >>> Remove these global variables as services are attached to the app context <<<
# conversation_service = None
# analysis_service = None
# data_service = None  # New centralized data service

# --- Caching Setup ---
cache = Cache() # Ensure cache is initialized before create_app uses it

# --- Ensure NLTK Data ---
def ensure_nltk_data():
    required = [
        ('tokenizers/punkt', 'punkt'),
        ('corpora/stopwords', 'stopwords'),
        ('corpora/wordnet', 'wordnet'),
        ('sentiment/vader_lexicon', 'vader_lexicon'),
    ]
    for path, pkg in required:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg)

def get_supabase_client():
    """Helper to get the Supabase client from flask.g or current_app."""
    if hasattr(g, 'supabase_client'):
        return g.supabase_client
    elif hasattr(current_app, 'supabase_client'):
        return current_app.supabase_client
    else:
        raise RuntimeError("Supabase client is not initialized")

def create_app(test_config=None):
    # Ensure NLTK data is present before any NLTK-dependent code runs
    ensure_nltk_data()
    logging.info("Starting create_app...") # Log start
    # Load environment variables from .env file
    load_dotenv()
    logging.info(".env loaded.")
    # Log the ElevenLabs env variables for debugging
    logging.info(f"ELEVENLABS_API_KEY: {os.getenv('ELEVENLABS_API_KEY')}")
    logging.info(f"ELEVENLABS_AGENT_ID: {os.getenv('ELEVENLABS_AGENT_ID')}")
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG, # Set log level to DEBUG
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Creating Flask app instance...")
    app = Flask(__name__, instance_relative_config=True)
    logging.info("Flask app instance created.")
    
    # Load configuration from environment variables first
    logging.info("Loading configuration...")
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True # Enable SQLAlchemy query logging
    
    # >>> ADD Supabase config explicitly from env vars <<<
    app.config['SUPABASE_URL'] = os.environ.get('SUPABASE_URL')
    app.config['SUPABASE_SERVICE_KEY'] = os.environ.get('SUPABASE_SERVICE_KEY')

    # >>> ADD Cache Configuration <<<
    app.config['CACHE_TYPE'] = 'FileSystemCache'  # Use file system for caching
    app.config['CACHE_DIR'] = os.path.join(app.instance_path, 'cache') # Cache directory inside instance folder
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300 # Default timeout 5 minutes

    # Load remaining configuration from config.py or test_config
    if test_config is None:
        try:
            app.config.from_pyfile('config.py', silent=True)
            logging.info("Loaded config from config.py.")
        except Exception as e:
            logging.warning(f"Could not load config.py: {e}")
        try:
            from config import Config
            app.config.from_object(Config)
            logging.info("Loaded config from Config object.")
        except ImportError:
            logging.info("Main config.py (Config object) not found or import failed, using defaults/env vars.")
        except Exception as e:
            logging.warning(f"Error loading Config object: {e}")

    else:
        # Load test config if provided
        app.config.from_mapping(test_config)
        logging.info("Loaded test configuration.")

    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not Set')
    logging.info(f"Database URI configured: {db_uri[:15]}...")
    logging.info("Configuration loading complete.")

    # --- Initialize Extensions from app.extensions --- #
    logging.info("Initializing extensions...")
    try:
        logging.info("Attempting db.init_app(app)...")
        db.init_app(app)
        logging.info("SQLAlchemy (db) initialized.")
        
        logging.info("Attempting migrate.init_app(app, db)...")
        migrate.init_app(app, db)
        logging.info("Migrate initialized.")

        # >>> INITIALIZE CACHE HERE <<<
        logging.info(f"Attempting cache.init_app(app) with type: {app.config.get('CACHE_TYPE')}, dir: {app.config.get('CACHE_DIR')}...")
        cache.init_app(app)
        logging.info("Cache initialized.")

    except Exception as e:
        # Print the full exception details to stderr for visibility, especially in CLI context
        import traceback
        print(f"ERROR during DB/Migrate initialization: {e}", file=sys.stderr)
        traceback.print_exc()
        logging.error(f"Error initializing DB or Migrate: {e}", exc_info=True)
        raise # Re-raise exception to halt app creation if DB fails
    logging.info("Extensions initialized.")

    # --- Import Models (after db init) --- #
    # This still needs to happen AFTER db.init_app
    logging.info("Importing models...")
    try:
        with app.app_context(): # Ensure context for model definition
            # from app import models 
            logging.info("Models imported successfully.")
    except Exception as e:
        logging.error(f"Error importing models: {e}", exc_info=True)
        # Decide if this should halt app creation
        raise

    # Configure CORS based on environment
    logging.info("Configuring CORS...")
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
    logging.info("CORS configured.")
    
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
        # Import datetime inside function if not imported globally
        import datetime 
        return {'now': datetime.datetime.now()}
    
    # Create and attach ElevenLabs client
    from app.api.elevenlabs_client import ElevenLabsClient
    try:
        api_key = os.getenv('ELEVENLABS_API_KEY', '')
        agent_id = os.getenv('ELEVENLABS_AGENT_ID', '')
        if api_key and agent_id:
            app.elevenlabs_client = ElevenLabsClient(api_key=api_key, agent_id=agent_id)
            logging.info("ElevenLabs client initialized and attached to app context.")
        else:
            logging.warning("ELEVENLABS_API_KEY or ELEVENLABS_AGENT_ID missing; ElevenLabs client not initialized.")
            app.elevenlabs_client = None
    except Exception as e:
        logging.error(f"Error initializing ElevenLabs client: {e}", exc_info=True)
        app.elevenlabs_client = None # Ensure it's None on failure

    # --- Initialize Services (Supabase Only) ---
    logging.info("Initializing services...")
    # supabase_url = os.getenv('SUPABASE_URL')
    # supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    # supabase_client_instance = None
    # conversation_service_instance = None
    # service_mode = "Supabase"

    # if supabase_url and supabase_key:
    #     logging.info("Supabase environment variables found. Attempting Supabase initialization...")
    #     try:
    #         logging.info(f"Initializing SupabaseClient with URL: {supabase_url[:20]}... KEY: {supabase_key[:5]}...")
    #         supabase_client_instance = SupabaseClient(supabase_url, supabase_key)
    #         if not supabase_client_instance or not supabase_client_instance.client:
    #             raise Exception("SupabaseClient object or underlying client failed to initialize.")
    #         logging.info("SupabaseClient initialized successfully.")

    #         conversation_service_instance = SupabaseConversationService(supabase_client=supabase_client_instance)
    #         logging.info("SupabaseConversationService initialized.")

    #     except Exception as e:
    #         logging.error(f"Supabase Initialization FAILED: {e}.", exc_info=True)
    #         supabase_client_instance = None
    #         conversation_service_instance = None

    # if conversation_service_instance is None:
    #     logging.error("FATAL: Failed to initialize SupabaseConversationService. Application cannot continue.")
    #     raise RuntimeError("SupabaseConversationService could not be initialized. Check Supabase configuration.")

    # app.conversation_service = conversation_service_instance
    # app.supabase_client = supabase_client_instance
    # logging.info(f"Conversation service initialized in {service_mode} mode.")

    # app.export_service = ExportService()
    logging.info("Export service initialized.")
    
    # logging.info(f"Service Status - Conversation: {'OK (' + service_mode + ')' if app.conversation_service else 'Failed'}, Analysis: {'OK' if app.analysis_service else 'Failed'}, Export: {'OK' if app.export_service else 'Failed'}")
    
    if hasattr(app, 'elevenlabs_client') and app.elevenlabs_client and app.elevenlabs_client.api_key:
        logging.info("Main ElevenLabsClient available on app context with API key.")
    elif hasattr(app, 'elevenlabs_client') and app.elevenlabs_client:
         logging.warning("Main ElevenLabsClient available on app context but MISSING API key.")
    else:
         logging.warning("Main ElevenLabsClient FAILED to initialize or is not attached to app context.")

    # After loading config and before registering blueprints:
    # --- Initialize Supabase Client and attach to app context ---
    supabase_url = app.config.get('SUPABASE_URL')
    supabase_key = app.config.get('SUPABASE_SERVICE_KEY')
    if supabase_url and supabase_key:
        try:
            app.supabase_client = SupabaseClient(supabase_url, supabase_key)
            logging.info("Supabase client initialized and attached to app context.")
        except Exception as e:
            app.supabase_client = None
            logging.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
    else:
        app.supabase_client = None
        logging.warning("Supabase URL or key missing; Supabase client not initialized.")

    # After Supabase client initialization
    @app.before_request
    def attach_supabase_to_g():
        if hasattr(app, 'supabase_client') and app.supabase_client:
            g.supabase_client = app.supabase_client

    # Register blueprints
    logging.info("Registering blueprints...")
    # Import blueprints here
    from app.routes import main_bp
    from app.api.routes import api as api_bp # Use alias to avoid name clash
    try:
        app.register_blueprint(main_bp)
        logging.info("Registered main_bp.")

        app.register_blueprint(api_bp, url_prefix='/api')
        logging.info("Registered api blueprint.")
    except Exception as e:
        logging.error(f"Error registering blueprints: {e}", exc_info=True)
        raise # Reraise blueprint registration errors as they are critical

    # Add security headers in production
    if os.environ.get('FLASK_ENV') == 'production':
        @app.after_request
        def add_security_headers(response):
            # Strict-Transport-Security: Ensures the browser only uses HTTPS
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            # X-Content-Type-Options: Prevents browser from MIME-sniffing 
            response.headers['X-Content-Type-Options'] = 'nosniff'
            # Referrer-Policy: Controls how much referrer info is sent
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            # Permissions-Policy: Controls browser features
            # Example: Disable microphone and geolocation
            # response.headers['Permissions-Policy'] = 'microphone=(), geolocation=()'
            return response
        logging.info("Security headers configured for production.")

    logging.info("create_app finished successfully.")

    # --- Register CLI Commands --- #
    # Import the sync function
    from app.tasks.sync import sync_new_conversations
    import click # Import click

    @app.cli.command("sync")
    @click.option('--force', is_flag=True, help='Force sync even if recently completed.') # Example option
    def sync_command(force):
        """Run the ElevenLabs conversation sync task."""
        logging.info(f"CLI: Starting manual sync (Force={force})...")
        try:
            # Pass the app instance to the sync function
            # Note: sync_new_conversations currently doesn't use 'force', but we pass it for future use.
            result, status_code = sync_new_conversations(app)
            logging.info(f"CLI: Sync finished with status {status_code}. Result: {result}")
            if status_code >= 400:
                sys.exit(2) # Exit with error code if sync failed
        except Exception as e:
            logging.error(f"CLI: Unhandled exception during sync command: {e}", exc_info=True)
            sys.exit(1) # Exit with error code
        logging.info("CLI: Sync command finished.")

    return app

# --- Global error handlers ---
# Example: Add a generic error handler
# @app.errorhandler(Exception)
# def handle_exception(e):
#     # pass through HTTP errors
#     if isinstance(e, HTTPException):
#         return e
#     # now you're handling non-HTTP exceptions only
#     logging.error(f"Unhandled exception: {e}", exc_info=True)
#     # Render a generic error page or return JSON
#     # return render_template("500.html"), 500 
#     return jsonify(error="An unexpected error occurred."), 500

# This pattern requires the error handler to be registered *after* app creation.
# Consider moving error handlers into create_app or registering them on the blueprint level.

# >>> REMOVED GLOBAL SERVICE INSTANTIATIONS <<<
# >>> MOVED INITIALIZATION INSIDE create_app <<< 