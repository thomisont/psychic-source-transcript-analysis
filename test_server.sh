#!/bin/bash

echo "==================================================================="
echo "TESTING REPLIT WEB SERVER CONFIGURATION"
echo "==================================================================="

# Kill any existing Python processes
pkill -9 python || echo "No Python processes to kill"
pkill -9 python3 || echo "No Python3 processes to kill"
pkill -9 flask || echo "No Flask processes to kill"

# Set up environment for test
export PORT=8080
echo "Testing server on port 8080..."
echo "Access the test page at: https://${REPL_SLUG}.${REPL_OWNER}.repl.co"

# Run the test server
python replit_test.py 