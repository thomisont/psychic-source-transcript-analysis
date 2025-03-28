import os
from dotenv import load_dotenv

load_dotenv()

# Environment detection
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
IS_PRODUCTION = FLASK_ENV == 'production'

# Configuration settings
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development'
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_AGENT_ID = os.environ.get('ELEVENLABS_AGENT_ID') or '3HFVw3nTZfIivPaHr3ne'
ELEVENLABS_API_URL = "https://api.elevenlabs.io"  # Removed /v1 to allow more flexibility in endpoint construction

# Base URL configuration - can be overridden by environment variable
if IS_PRODUCTION:
    BASE_URL = os.environ.get('BASE_URL') or 'https://howislilydoing.org'
else:
    # Default development URL
    BASE_URL = os.environ.get('BASE_URL') or 'http://localhost:5000'

# Debug mode - always off in production
DEBUG = not IS_PRODUCTION 