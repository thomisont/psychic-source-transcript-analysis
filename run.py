from app import create_app
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('FLASK_RUN_PORT', 3000))
    
    # Run the app - the host and port will be overridden by the Flask CLI when run with flask run
    app.run(host='0.0.0.0', port=port) 