#!/bin/bash
# Startup script for running the application with Supabase integration

# Kill any running Flask servers
echo "Stopping any existing Flask servers..."
pkill -f "python.*run.py" || true
sleep 1

# Make sure we have all dependencies installed
echo "Installing dependencies..."
pip install -r requirements.txt

# Set up PYTHONPATH to include the current directory
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Check Supabase connection
echo "Testing Supabase connection..."
python test_supabase_tables.py

# Run initial sync to populate the database
echo "Running initial data sync..."
python run_sync_task.py

# Start the Flask server
echo "Starting Flask server..."
python run.py 