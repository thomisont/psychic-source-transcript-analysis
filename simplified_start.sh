#!/bin/bash

echo "Starting Psychic Source Analyzer setup..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for required environment variables
echo "Checking environment variables..."

if [ -z "$SUPABASE_URL" ]; then
  echo "ERROR: SUPABASE_URL environment variable is not set!"
  echo "Please set it in Replit Secrets."
  echo "Using URL format: https://elrjsmvfkiyvzbspwxxf.supabase.co"
  exit 1
fi

if [ -z "$SUPABASE_KEY" ]; then
  echo "ERROR: SUPABASE_KEY environment variable is not set!"
  echo "Please set it in Replit Secrets."
  exit 1
fi

if [ -z "$ELEVENLABS_API_KEY" ]; then
  echo "WARNING: ELEVENLABS_API_KEY environment variable is not set."
  echo "ElevenLabs integration will not function correctly."
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "WARNING: OPENAI_API_KEY environment variable is not set."
  echo "Analysis features requiring OpenAI will not function correctly."
fi

# Start the application
echo "Starting application on port 8080..."
python run.py --port 8080 