#!/usr/bin/env python3
"""
Debug script to identify server startup issues
"""
import sys
import os
import traceback

print("Current Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("PYTHONPATH:", sys.path)

try:
    print("Attempting to import key modules...")
    import flask
    print("Flask imported successfully:", flask.__version__)
    
    import sqlalchemy
    print("SQLAlchemy imported successfully:", sqlalchemy.__version__)
    
    from dotenv import load_dotenv
    print("python-dotenv imported successfully")
    
    # Try to import our application modules
    print("\nAttempting to import application modules...")
    from app import create_app
    print("create_app imported successfully")
    
    # Try to create the app
    print("\nAttempting to create Flask app...")
    app = create_app()
    print("Flask app created successfully")
    
    # If we get here, we can try running the app
    print("\nAttempting to run Flask app...")
    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=8080, debug=True)
    
except Exception as e:
    print("\nError:", e)
    print("\nTraceback:")
    traceback.print_exc() 