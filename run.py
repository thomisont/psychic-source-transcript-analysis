from app import create_app
import os
import nltk
from nltk_setup import download_nltk_resources

# Ensure NLTK resources are downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    download_nltk_resources()

app = create_app()

if __name__ == '__main__':
    # Determine if we're running on Replit
    is_replit = 'REPLIT_DB_URL' in os.environ
    
    if is_replit:
        # For Replit deployment
        app.run(host='0.0.0.0', port=8080)
    else:
        # For local development
        app.run(debug=True, host='0.0.0.0', port=3000) 