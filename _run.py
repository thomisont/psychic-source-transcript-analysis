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
# Remove port argument from parser, we will get it from environment
# parser.add_argument('-p', '--port', type=int, default=int(os.environ.get('FLASK_RUN_PORT', 8080)),
#                    help='Port to run the application on')
parser.add_argument('-d', '--debug', action='store_true', default=False,
                   help='Run in debug mode')
args = parser.parse_args()

# Determine the port to use
# Priority: PORT env var (from Replit deployment) > FLASK_RUN_PORT env var > Default (8080)
port_to_use = int(os.environ.get('PORT', os.environ.get('FLASK_RUN_PORT', 8080)))

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Show the port we're using
    logging.info(f"Starting server on port {port_to_use}...")
    
    # Run the app with the determined port
    app.run(host='0.0.0.0', port=port_to_use, debug=args.debug, use_reloader=False) 