# Utils package initialization 
import logging

def configure_logging():
    """
    Configure logging for the application
    """
    # Set up basic logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set third-party library logging to WARNING level to reduce noise
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('chardet').setLevel(logging.WARNING)
    
    # Create an application logger
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)
    
    return logger 