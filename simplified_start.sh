#!/bin/bash

echo "==================================================================="
echo "STREAMLINED STARTUP SCRIPT FOR PSYCHIC SOURCE ANALYZER"
echo "==================================================================="

# Ensure we're in the correct directory
if [[ "$PWD" != *"/home/runner/workspace"* ]]; then
  echo "Changing to workspace directory..."
  cd /home/runner/workspace || { echo "Failed to change to workspace directory"; exit 1; }
fi

# Kill any existing Python processes
pkill -9 python || echo "No Python processes to kill"
pkill -9 python3 || echo "No Python3 processes to kill"
pkill -9 flask || echo "No Flask processes to kill"

# Check if port 8080 is in use
PORT_PID=$(lsof -t -i:8080 2>/dev/null)
if [ -n "$PORT_PID" ]; then
  echo "Port 8080 is in use by process $PORT_PID. Attempting to terminate..."
  kill -9 $PORT_PID
  sleep 1
  # Verify port is now free
  if lsof -i:8080 >/dev/null 2>&1; then
    echo "Warning: Port 8080 is still in use. Application may fail to start."
  else
    echo "Port 8080 is now free."
  fi
else
  echo "Port 8080 is available."
fi

# Install NLTK data
echo "Ensuring NLTK data is available..."
python -c "
import nltk
import ssl

# Handle SSL certificate verification issues
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download required resources
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('vader_lexicon', quiet=True)
"

# Create a named session for better process management
SESSION_NAME="psychic_analyzer"

# Set up environment
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Set port directly to 8080 which is the primary web port for Replit
export FLASK_RUN_PORT=8080
export PORT=8080  # This is what Replit looks for
echo "Using Replit standard port 8080..."
echo "Access the application at: https://${REPL_SLUG}.${REPL_OWNER}.repl.co"

# Launch Flask with explicit host and port
python -m flask run --host=0.0.0.0 --port=8080 