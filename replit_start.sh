#!/bin/bash

# Set default port - pick a high random port to avoid conflicts
DEFAULT_PORT=$((10000 + RANDOM % 50000))
echo "================================================================="
echo "REPLIT STARTUP SCRIPT FOR PSYCHIC SOURCE ANALYZER"
echo "================================================================="

# Kill ALL Python processes regardless of owner (more aggressive)
echo "Killing ALL Python processes..."
pkill -9 python || true
pkill -9 python3 || true
pkill -9 flask || true
pkill -9 gunicorn || true

# Wait longer for processes to fully terminate
echo "Waiting for processes to terminate completely (5 seconds)..."
sleep 5

# Clear any port bindings - this requires netstat to be installed
echo "Checking port availability..."
for PORT in 8080 5000 3000 3001 8000; do
  if lsof -ti:$PORT; then
    echo "Force-killing process on port $PORT"
    lsof -ti:$PORT | xargs kill -9 || true
  else
    echo "Port $PORT is available"
  fi
done

# Wait again to ensure ports are released
sleep 2

# Set environment variable to use the high random port
export FLASK_RUN_PORT=$DEFAULT_PORT
echo "Setting Flask to use port $DEFAULT_PORT"

# Go to the workspace directory
cd /home/runner/workspace

# Start the application - use the high random port explicitly
echo "Starting application on port $DEFAULT_PORT..."
echo "================================================================="
python run.py --port $DEFAULT_PORT 