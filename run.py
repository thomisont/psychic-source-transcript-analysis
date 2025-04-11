from app import create_app
import os
import logging
import sys
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Parse command line arguments 
parser = argparse.ArgumentParser(description='Run the Psychic Source Analyzer application')
parser.add_argument('-p', '--port', type=int, default=int(os.environ.get('FLASK_RUN_PORT', 8080)),
                   help='Port to run the application on')
parser.add_argument('-d', '--debug', action='store_true', default=True,
                   help='Run in debug mode')
args = parser.parse_args()

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Show the port we're using
    logging.info(f"Starting server on port {args.port}...")
    
    # Run the app with the specified port
    app.run(host='0.0.0.0', port=args.port, debug=args.debug, use_reloader=args.debug) 