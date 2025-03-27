import nltk
import ssl

def download_nltk_resources():
    """Download required NLTK resources for the application."""
    print("Downloading required NLTK resources...")
    
    # Handle SSL certificate verification issues
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    resources = [
        'punkt',           # For tokenization
        'stopwords',       # Common stopwords
        'wordnet',         # For lemmatization
        'vader_lexicon',   # For sentiment analysis
        'averaged_perceptron_tagger', # For POS tagging
        'maxent_ne_chunker', # For named entity recognition
        'words'            # Common words corpus
    ]
    
    for resource in resources:
        print(f"Downloading {resource}...")
        nltk.download(resource)
    
    # Special case for punkt data
    try:
        print("Setting up sentence tokenization...")
        import nltk.tokenize
        from nltk.tokenize import sent_tokenize
        test_text = "This is a test. This is only a test."
        sentences = sent_tokenize(test_text)
        print(f"Sentence tokenization is working: {sentences}")
    except Exception as e:
        print(f"Error with sentence tokenization: {e}")
        print("Downloading additional tokenization data...")
        nltk.download('punkt')
    
    print("All resources downloaded successfully!")

if __name__ == "__main__":
    download_nltk_resources() 