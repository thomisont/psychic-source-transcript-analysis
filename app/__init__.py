import sys
import os
from flask import Flask, g, current_app, redirect, url_for, request
from flask_cors import CORS
import logging
from dotenv import load_dotenv
# Import extensions from the new file
from app.extensions import db, migrate, cache, server_session
# Move client and service imports inside create_app
# from app.api.elevenlabs_client import ElevenLabsClient
# import datetime
# from app.services.conversation_service import ConversationService
# from app.services.analysis_service import AnalysisService
# from app.services.export_service import ExportService
from flask_caching import Cache
from tools.supabase_client import SupabaseClient
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import config # Import the config dictionary

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Remove global instantiations from here
# db = SQLAlchemy()
# migrate = Migrate()

# Import models here after db initialization
# from app.models import Conversation, Message  # noqa

# # Initialize services  <-- REMOVE THIS BLOCK
# from app.services.analysis_service import AnalysisService # <-- REMOVE
# from app.services.data_service import DataService # <-- REMOVE

# Global services
# >>> Remove these global variables as services are attached to the app context <<<
# conversation_service = None
# analysis_service = None
# data_service = None  # New centralized data service

# --- Caching Setup ---
cache = Cache() # Ensure cache is initialized before create_app uses it

# --- Ensure NLTK Data ---
def ensure_nltk_data():
    import nltk  # <-- Move import here, not global
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
    ensure_nltk_data()
    logging.info("Starting create_app...")
    load_dotenv()
    logging.info(".env loaded.")

    config_name = os.getenv('FLASK_ENV', 'default')
    logging.info(f"Loading config for environment: {config_name}")

    flask_instance = Flask(__name__, instance_relative_config=True)
    logging.info("Flask app instance created.")

    try:
        flask_instance.config.from_object(config[config_name])
        logging.info(f"Loaded configuration from {config_name} object.")
    except KeyError:
        logging.warning(f"Invalid FLASK_ENV '{config_name}'. Using default config.")
        flask_instance.config.from_object(config['default'])
        logging.info("Loaded configuration from default object.")
    
    if hasattr(config[config_name], 'init_app'):
        config[config_name].init_app(flask_instance)
        logging.info(f"Executed init_app for {config_name}.")

    if test_config:
        flask_instance.config.from_mapping(test_config)
        logging.info("Overwrote with test configuration.")

    logging.info(f"DEBUG mode: {flask_instance.config.get('DEBUG')}")
    db_uri = flask_instance.config.get('SQLALCHEMY_DATABASE_URI', 'Not Set')
    logging.info(f"Database URI configured: {db_uri[:15]}..." if db_uri != 'Not Set' else "Database URI: Not Set")
    logging.info(f"Supabase URL configured: {flask_instance.config.get('SUPABASE_URL')}")
    logging.info("Configuration loading complete.")

    logging.info("Initializing extensions...")
    try:
        db.init_app(flask_instance)
        logging.info("SQLAlchemy (db) initialized.")
        migrate.init_app(flask_instance, db)
        logging.info("Migrate initialized.")
        cache.init_app(flask_instance)
        logging.info("Cache initialized.")
        server_session.init_app(flask_instance)
        logging.info("Server session initialized.")
    except Exception as e:
        import traceback
        print(f"ERROR during Extension initialization: {e}", file=sys.stderr)
        traceback.print_exc()
        logging.error(f"Error initializing Extensions: {e}", exc_info=True)
        raise # Halt app creation
    logging.info("Extensions initialized.")

    logging.info("Configuring CORS...")
    if flask_instance.config.get('FLASK_ENV') == 'production':
        allowed_origins = [flask_instance.config.get('BASE_URL')]
        logging.info(f"Production mode: CORS configured for {allowed_origins}")
        CORS(flask_instance, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)
    else:
        logging.info("Development mode: CORS configured for all origins")
        CORS(flask_instance, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    logging.info("CORS configured.")

    api_key_config = flask_instance.config.get('ELEVENLABS_API_KEY')
    if api_key_config:
        logging.info(f"Loaded ElevenLabs API key: {api_key_config[:5]}...")
    else:
        logging.warning("No ElevenLabs API key found")

    # Log if OpenAI key is available
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        logging.info(f"Loaded OpenAI API key: {openai_key[:5]}...")
    else:
        logging.warning("No OpenAI API key found, analysis features will use fallbacks")

    try:
        os.makedirs(flask_instance.instance_path, exist_ok=True)
        os.makedirs(os.path.join(flask_instance.instance_path, 'sessions'), exist_ok=True)
    except OSError:
        pass

    @flask_instance.context_processor
    def inject_now():
        # Import datetime inside function if not imported globally
        import datetime 
        return {'now': datetime.datetime.now()}

    from app.api.elevenlabs_client import ElevenLabsClient
    try:
        el_api_key = flask_instance.config.get('ELEVENLABS_API_KEY')
        el_agent_id = flask_instance.config.get('ELEVENLABS_AGENT_ID')

        if el_api_key:
            flask_instance.elevenlabs_client = ElevenLabsClient(api_key=el_api_key, agent_id=el_agent_id)
            logging.info(f"ElevenLabs client initialized from config. Agent ID: {el_agent_id if el_agent_id else 'None'}")
        else:
            logging.warning("ELEVENLABS_API_KEY missing in config; ElevenLabs client not initialized.")
            flask_instance.elevenlabs_client = None
    except Exception as e:
        logging.error(f"Error initializing ElevenLabs client: {e}", exc_info=True)
        flask_instance.elevenlabs_client = None

    logging.info("Initializing Supabase client...")
    sb_url = flask_instance.config.get('SUPABASE_URL')
    sb_key = flask_instance.config.get('SUPABASE_KEY')
    if sb_url and sb_key:
        try:
            flask_instance.supabase_client = SupabaseClient(sb_url, sb_key)
            logging.info("Supabase client initialized and attached to app context.")
        except Exception as e:
            flask_instance.supabase_client = None
            logging.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
    else:
        flask_instance.supabase_client = None
        logging.warning("Supabase URL or key missing in config; Supabase client not initialized.")

    logging.info("Initializing core services...")
    try:
        from app.services.supabase_conversation_service import SupabaseConversationService
        from app.services.analysis_service import AnalysisService
        from app.services.export_service import ExportService

        if flask_instance.supabase_client:
            flask_instance.conversation_service = SupabaseConversationService(supabase_client=flask_instance.supabase_client)
            logging.info("SupabaseConversationService initialized and attached.")
        else:
            logging.error("Supabase client unavailable; cannot initialize ConversationService.")
            flask_instance.conversation_service = None

        if flask_instance.conversation_service:
            # Determine lightweight mode based on OpenAI key *in config/env*
            lightweight_flag = not bool(os.getenv("OPENAI_API_KEY"))
            flask_instance.analysis_service = AnalysisService(
                conversation_service=flask_instance.conversation_service,
                cache=cache,
                lightweight_mode=lightweight_flag,
            )
            mode_label = "Lightweight" if lightweight_flag else "Full‑LLM"
            logging.info(f"AnalysisService initialized and attached. Mode: {mode_label}")
        else:
            logging.warning("ConversationService not available; AnalysisService not initialized.")
            flask_instance.analysis_service = None

        flask_instance.export_service = ExportService()
        logging.info("ExportService initialized and attached.")

    except Exception as svc_err:
        logging.error(f"Failed to initialize core services: {svc_err}", exc_info=True)
        flask_instance.conversation_service = None
        flask_instance.analysis_service = None
        flask_instance.export_service = None

    @flask_instance.before_request
    def attach_supabase_to_g():
        if hasattr(flask_instance, 'supabase_client') and flask_instance.supabase_client:
            g.supabase_client = flask_instance.supabase_client

    logging.info("Registering blueprints...")
    from app.routes import main_bp
    from app.api.routes import api as api_bp
    from app.auth import auth_bp
    try:
        flask_instance.register_blueprint(main_bp)
        logging.info("Registered main_bp.")
        flask_instance.register_blueprint(api_bp, url_prefix='/api')
        logging.info("Registered api blueprint.")
        flask_instance.register_blueprint(auth_bp)
        logging.info("Registered auth blueprint.")
    except Exception as e:
        logging.error(f"Error registering blueprints: {e}", exc_info=True)
        raise # Reraise blueprint registration errors as they are critical

    if flask_instance.config.get('FLASK_ENV') == 'production':
        @flask_instance.after_request
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

    @flask_instance.before_request
    def enforce_login():
        if request.path.startswith('/api/'):
            return  # Allow API endpoints to handle their own auth or be public
        open_paths = ['/login', '/static', '/favicon', '/logout']
        if any(request.path.startswith(p) for p in open_paths):
            return  # Allow unauthenticated access
        # Skip if blueprint is api and we may allow public (adjust later)
        if getattr(g, 'user', None) is None:
            return redirect(url_for('auth.login', next=request.path))

    logging.info("create_app finished successfully.")

    # Register CLI Commands
    # Import the sync function
    from app.tasks.sync import sync_new_conversations
    import click

    @flask_instance.cli.command("sync")
    @click.option('--force', is_flag=True, help='Force sync even if recently completed.')
    def sync_command(force):
        """Run the ElevenLabs conversation sync task."""
        logging.info(f"CLI: Starting manual sync (Force={force})...")
        try:
            result, status_code = sync_new_conversations(flask_instance)
            logging.info(f"CLI: Sync finished with status {status_code}. Result: {result}")
            if status_code >= 400:
                sys.exit(2) # Exit with error code if sync failed
        except Exception as e:
            logging.error(f"CLI: Unhandled exception during sync command: {e}", exc_info=True)
            sys.exit(1) # Exit with error code
        logging.info("CLI: Sync command finished.")

    @flask_instance.cli.command("clear-cache")
    def clear_cache_command():
        """Clear the application cache."""
        try:
            cache.clear()
            click.echo("Cache cleared successfully")
        except Exception as e:
            click.echo(f"Failed to clear cache: {e}", err=True)
            sys.exit(1)

    # Attach GlassFrog client & service
    try:
        from tools.glassfrog_client import GlassFrogClient
        from app.services.glassfrog_service import GlassFrogService
        gf_client = GlassFrogClient()
        flask_instance.glassfrog_client = gf_client
        flask_instance.glassfrog_service = GlassFrogService(client=gf_client, cache=cache)
        logging.info("GlassFrog client & service initialised.")
    except Exception as e:
        logging.error(f"Failed to initialise GlassFrog integration: {e}", exc_info=True)
        flask_instance.glassfrog_client = None
        flask_instance.glassfrog_service = None

    # Configure production logging
    if not flask_instance.debug and not flask_instance.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        flask_instance.logger.addHandler(file_handler)

        flask_instance.logger.setLevel(logging.INFO)
        flask_instance.logger.info('Application startup')

    return flask_instance

# Remove global error handlers or register them within create_app/blueprints
# ...