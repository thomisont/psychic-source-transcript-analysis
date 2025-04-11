#!/usr/bin/env python
"""Entry point script for running the conversation sync task.

This script is intended to be executed by the Replit Scheduled Deployment.
It creates a Flask app instance to provide context for the task.
"""

import logging
import sys
import os
import argparse # Import argparse

# Add project root to path to allow imports like 'from app import create_app'
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging early
logging.basicConfig(
    level=logging.INFO, # Adjust level as needed (DEBUG for more detail)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout # Log to stdout for Replit Scheduled Deployment logs
)

logging.info("run_sync_task.py: Script started.")

try:
    from app import create_app
    from app.tasks.sync import sync_new_conversations
except ImportError as e:
    logging.error(f"run_sync_task.py: Failed to import required modules: {e}", exc_info=True)
    sys.exit(1)

if __name__ == '__main__':
    # --- Add Argument Parsing --- 
    parser = argparse.ArgumentParser(description='Run ElevenLabs conversation sync task.')
    parser.add_argument('--full', action='store_true', 
                        help='Perform a full sync, fetching all conversations instead of just recent ones.')
    args = parser.parse_args()
    # --- End Argument Parsing --- 

    logging.info("run_sync_task.py: Creating Flask app instance for context...")
    try:
        # Create the app instance (loads config, initializes extensions, etc.)
        app = create_app()
        logging.info("run_sync_task.py: Flask app instance created.")
    except Exception as e:
        logging.error(f"run_sync_task.py: Failed to create Flask app instance: {e}", exc_info=True)
        sys.exit(1)

    logging.info("run_sync_task.py: Attempting to call sync_new_conversations task...")
    try:
        # Run the sync task, passing the app context and the full sync flag
        logging.info(f"Calling sync_new_conversations with full_sync={args.full}")
        result, status_code = sync_new_conversations(app, full_sync=args.full)
        
        # Log the outcome
        logging.info(f"run_sync_task.py: Sync task call completed. Status: {status_code}. Result: {result}")
        
        # Check the status code returned by the sync function
        if status_code >= 400:
            logging.error(f"run_sync_task.py: Sync task reported failure (status code {status_code}). Exiting with error code 2.")
            sys.exit(2) # Use a different error code for task failure vs script error
        else:
            logging.info("run_sync_task.py: Sync task reported success. Exiting with success code 0.")
            sys.exit(0) # Explicit success exit

    except Exception as e:
        logging.error(f"run_sync_task.py: Unhandled exception during sync task execution: {e}", exc_info=True)
        # Exit with failure code 1 for script-level errors
        sys.exit(1) 