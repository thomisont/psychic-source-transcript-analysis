#!/bin/bash

echo "Restarting Psychic Source Analyzer..."

# Ensure we're in the correct directory
if [[ "$PWD" != *"/home/runner/workspace"* ]]; then
  echo "Changing to workspace directory..."
  cd /home/runner/workspace || { echo "Failed to change to workspace directory"; exit 1; }
fi

# Stop existing processes
pkill -9 python || echo "No Python processes to kill"
pkill -9 python3 || echo "No Python3 processes to kill" 
pkill -9 flask || echo "No Flask processes to kill"

# Clear port usage information
rm -f .replit.port || echo "No port file to remove"

# Start the application using our simplified script
bash /home/runner/workspace/simplified_start.sh

echo "Restart complete!" 