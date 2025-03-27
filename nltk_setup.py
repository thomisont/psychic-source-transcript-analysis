"""
Setup script to download required NLTK resources.
"""
import sys
import os
import nltk
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def download_nltk_resources():
    """Download required NLTK resources for the application."""
    # Create data directory if it doesn't exist
    data_dir = Path(os.environ.get('NLTK_DATA', os.path.join(os.path.expanduser("~"), 'nltk_data')))
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # List of required NLTK resources
    resources = [
        'punkt',            # Tokenizer
        'stopwords',        # Common stopwords
        'wordnet',          # Lexical database
        'averaged_perceptron_tagger'  # Part-of-speech tagger
    ]
    
    # Download each resource
    for resource in resources:
        try:
            logging.info(f"Downloading {resource}...")
            nltk.download(resource)
            logging.info(f"Successfully downloaded {resource}")
        except Exception as e:
            logging.error(f"Error downloading {resource}: {e}")
    
    logging.info("NLTK resource setup complete")

if __name__ == "__main__":
    logging.info("Downloading required NLTK resources...")
    download_nltk_resources()
    logging.info("NLTK setup complete.") 