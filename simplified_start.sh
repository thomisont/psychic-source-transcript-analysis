
#!/bin/bash

echo "Starting application setup..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

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

# Start the application
echo "Starting application..."
python run.py --host 0.0.0.0 --port 8080
