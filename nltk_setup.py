import nltk

def download_nltk_resources():
    """Download required NLTK resources for the application."""
    print("Downloading required NLTK resources...")
    
    resources = [
        'punkt',           # For tokenization
        'stopwords',       # Common stopwords
        'wordnet',         # For lemmatization
        'vader_lexicon'    # For sentiment analysis
    ]
    
    for resource in resources:
        print(f"Downloading {resource}...")
        nltk.download(resource)
    
    print("All resources downloaded successfully!")

if __name__ == "__main__":
    download_nltk_resources() 