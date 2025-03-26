#!/bin/bash

cd /home/runner/workspace
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Available Python files: $(find . -name "*.py" -type f | sort)"
echo "Running the application..."

# Set environment variables
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Download NLTK resources
python nltk_setup.py

# Run the application
python run.py 