import sys
import os
from flask import Flask, g
from flask_cors import CORS
import logging
from dotenv import load_dotenv
# Import extensions from the new file
from app.extensions import db, migrate
# Move client and service imports inside create_app
# from app.api.elevenlabs_client import ElevenLabsClient
# import datetime
# from app.services.conversation_service import ConversationService
# from app.services.analysis_service import AnalysisService
# from app.services.export_service import ExportService
from flask_caching import Cache

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Remove global instantiations from here
# db = SQLAlchemy()
# migrate = Migrate()

# Import models here after db initialization
from app.models import Conversation, Message  # noqa

# Initialize services
from app.services.conversation_service import ConversationService
from app.services.analysis_service import AnalysisService
from app.services.data_service import DataService

# Global services
# >>> Remove these global variables as services are attached to the app context <<<
# conversation_service = None
# analysis_service = None
# data_service = None  # New centralized data service

# --- Caching Setup ---
cache = Cache() # Ensure cache is initialized before create_app uses it

def create_app(test_config=None):
    logging.info("Starting create_app...") # Log start
    # Load environment variables from .env file
    load_dotenv()
    logging.info(".env loaded.")
    
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

    # Prevent connection pooling issues
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 60,       # Recycle connections after 1 minute (was 180)
        'pool_pre_ping': True,    # Check connection validity before using
        'pool_size': 5,           # Smaller pool size (was 10)
        'max_overflow': 10,       # More overflow connections (was 5)
        'pool_timeout': 30,       # Timeout after 30 seconds (new)
        'pool_reset_on_return': 'rollback'  # Always rollback on return (new)
    }

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
        db.init_app(app) # Initialize db from extensions
        logging.info("SQLAlchemy (db) initialized.")
        
        logging.info("Attempting migrate.init_app(app, db)...")
        migrate.init_app(app, db) # Initialize migrate from extensions
        logging.info("Migrate initialized.")

        # >>> INITIALIZE CACHE HERE <<<
        logging.info(f"Attempting cache.init_app(app) with type: {app.config.get('CACHE_TYPE')}, dir: {app.config.get('CACHE_DIR')}...")
        cache.init_app(app) # Initialize cache from global object
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
            from app import models 
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
    logging.info("Initializing ElevenLabs client...")
    # Import client here
    from app.api.elevenlabs_client import ElevenLabsClient
    try:
        app.elevenlabs_client = ElevenLabsClient(
            api_key=os.getenv('ELEVENLABS_API_KEY', ''),
            agent_id=os.getenv('ELEVENLABS_AGENT_ID', '')
        )
        logging.info("ElevenLabs client initialized and attached to app context.")
    except Exception as e:
        logging.error(f"Error initializing ElevenLabs client: {e}", exc_info=True)
        app.elevenlabs_client = None # Ensure it's None on failure

    # --- Initialize Services (Revised Logic) ---
    logging.info("Initializing services...")

    # Import services here (inside function)
    from app.services.conversation_service import ConversationService
    # >>> ADD IMPORT FOR SUPABASE SERVICE <<<
    from app.services.supabase_conversation_service import SupabaseConversationService
    from app.services.analysis_service import AnalysisService
    from app.services.export_service import ExportService
    # >>> ADD IMPORT FOR SUPABASE CLIENT <<<
    from tools.supabase_client import SupabaseClient

    # Initialize services within app context
    with app.app_context():
        # >>> START NEW LOGIC <<<
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        supabase_client_instance = None
        conversation_service_instance = None
        service_mode = "Database" # Default

        if supabase_url and supabase_key:
            logging.info("Supabase environment variables found. Attempting Supabase initialization...")
            try:
                logging.info(f"Initializing SupabaseClient with URL: {supabase_url[:20]}... KEY: {supabase_key[:5]}...")
                supabase_client_instance = SupabaseClient(supabase_url, supabase_key)
                if not supabase_client_instance or not supabase_client_instance.client:
                    raise Exception("SupabaseClient object or underlying client failed to initialize.")
                logging.info("SupabaseClient initialized successfully.")

                conversation_service_instance = SupabaseConversationService(supabase_client=supabase_client_instance)
                service_mode = "Supabase"
                logging.info("SupabaseConversationService initialized.")

            except Exception as e:
                logging.error(f"Supabase Initialization FAILED: {e}. Falling back to Database mode.", exc_info=True)
                supabase_client_instance = None
                conversation_service_instance = None

        if conversation_service_instance is None:
            logging.info("Initializing ConversationService (Database Mode)...")
            try:
                # Correct instantiation using the db object from extensions
                conversation_service_instance = ConversationService(db=db)
                logging.info("ConversationService (Database Mode) initialized.")
            except Exception as e:
                 logging.error(f"FATAL: Failed to initialize even the fallback ConversationService: {e}", exc_info=True)
                 conversation_service_instance = None

        app.conversation_service = conversation_service_instance
        app.supabase_client = supabase_client_instance
        logging.info(f"Conversation service initialized in {service_mode} mode.")
        # >>> END NEW LOGIC <<<

        if app.conversation_service:
            try:
                app.analysis_service = AnalysisService(conversation_service=app.conversation_service, lightweight_mode=False, cache=cache) 
                logging.info(f"Analysis service initialized and attached (Full Mode, using {service_mode} backend).")
            except Exception as e:
                logging.error(f"Error initializing full AnalysisService: {e}", exc_info=True)
                try:
                    app.analysis_service = AnalysisService(conversation_service=app.conversation_service, lightweight_mode=True, cache=cache)
                    logging.warning(f"Fallback lightweight analysis service initialized and attached (using {service_mode} backend).")
                except Exception as e_light:
                    logging.error(f"FATAL: Failed to initialize even lightweight AnalysisService: {e_light}", exc_info=True)
                    app.analysis_service = None
        else:
            logging.error("Cannot initialize AnalysisService because ConversationService failed to initialize.")
            app.analysis_service = None

        app.export_service = ExportService()
        logging.info("Export service initialized.")
        
        logging.info(f"Service Status - Conversation: {'OK (' + service_mode + ')' if app.conversation_service else 'Failed'}, Analysis: {'OK' if app.analysis_service else 'Failed'}, Export: {'OK' if app.export_service else 'Failed'}")
        
        if hasattr(app, 'elevenlabs_client') and app.elevenlabs_client and app.elevenlabs_client.api_key and app.elevenlabs_client.agent_id:
            logging.info("Main ElevenLabsClient available on app context with API key and Agent ID.")
        elif hasattr(app, 'elevenlabs_client') and app.elevenlabs_client:
             logging.warning("Main ElevenLabsClient available on app context but MISSING API key or Agent ID.")
        else:
             logging.warning("Main ElevenLabsClient FAILED to initialize or is not attached to app context.")

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