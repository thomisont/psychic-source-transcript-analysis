#!/bin/bash

echo "Starting application in production mode..."

# Install only production dependencies
pip install -r requirements-prod.txt

# Check for required environment variables
echo "Checking environment variables..."

if [ -z "$SUPABASE_URL" ]; then
  echo "ERROR: SUPABASE_URL environment variable is not set!"
  echo "Please set it in Deployment Secrets."
  exit 1
fi

if [ -z "$SUPABASE_SERVICE_KEY" ]; then
  echo "ERROR: SUPABASE_SERVICE_KEY environment variable is not set!"
  echo "Please set it in Deployment Secrets."
  exit 1
fi

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set!"
  echo "Please set it in Deployment Secrets."
  exit 1
fi

# Start with gunicorn for better production performance
gunicorn --bind 0.0.0.0:8080 run:app