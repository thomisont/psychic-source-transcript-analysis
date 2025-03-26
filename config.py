import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development'
    ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
    ELEVENLABS_AGENT_ID = os.environ.get('ELEVENLABS_AGENT_ID') or '3HFVw3nTZfIivPaHr3ne'
    ELEVENLABS_API_URL = "https://api.elevenlabs.io"  # Removed /v1 to allow more flexibility in endpoint construction 