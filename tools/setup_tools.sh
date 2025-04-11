#!/bin/bash
# Setup script for Supabase Tools

# Set up colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Supabase Tools...${NC}"

# Check if Python 3 is installed
if command -v python3 &>/dev/null; then
    python_cmd="python3"
elif command -v python &>/dev/null; then
    # Check if python is Python 3
    python_version=$(python --version 2>&1 | awk '{print $2}' | cut -d. -f1)
    if [ "$python_version" -eq 3 ]; then
        python_cmd="python"
    else
        echo -e "${RED}Python 3 is required but not found${NC}"
        exit 1
    fi
else
    echo -e "${RED}Python 3 is required but not found${NC}"
    exit 1
fi

echo -e "${GREEN}Using Python command: $python_cmd${NC}"

# Check if pip is installed
if command -v pip3 &>/dev/null; then
    pip_cmd="pip3"
elif command -v pip &>/dev/null; then
    pip_cmd="pip"
else
    echo -e "${RED}pip is required but not found${NC}"
    exit 1
fi

echo -e "${GREEN}Using pip command: $pip_cmd${NC}"

# Create directory for generated files
mkdir -p ./generated/types
mkdir -p ./generated/schema
mkdir -p ./generated/migrations

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
$pip_cmd install -r $(dirname "$0")/requirements.txt

# Check for environment variables
echo -e "${YELLOW}Checking for required environment variables...${NC}"
MISSING_ENV_VARS=0

if [ -z "$SUPABASE_URL" ]; then
    echo -e "${RED}SUPABASE_URL environment variable is not set${NC}"
    MISSING_ENV_VARS=1
fi

if [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo -e "${RED}SUPABASE_SERVICE_KEY environment variable is not set${NC}"
    MISSING_ENV_VARS=1
fi

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}DATABASE_URL environment variable is not set${NC}"
    MISSING_ENV_VARS=1
fi

if [ $MISSING_ENV_VARS -eq 1 ]; then
    echo -e "${YELLOW}Please set the required environment variables in your .env file:${NC}"
    echo "SUPABASE_URL=https://your-project.supabase.co"
    echo "SUPABASE_SERVICE_KEY=your-service-key"
    echo "DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres"
fi

# Test Supabase connection
echo -e "${GREEN}Testing Supabase connection...${NC}"
$python_cmd $(dirname "$0")/test_supabase.py --check-only

# Check if the tests passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Setup completed successfully!${NC}"
    echo -e "${GREEN}Available commands:${NC}"
    echo -e "  ${YELLOW}$python_cmd tools/test_supabase.py${NC} - Test connection and explore database"
    echo -e "  ${YELLOW}$python_cmd tools/generate_types.py${NC} - Generate TypeScript types"
    echo -e "  ${YELLOW}$python_cmd tools/migrate_to_supabase.py${NC} - Migrate data to Supabase"
    echo -e "  ${YELLOW}$python_cmd tools/supabase_vectors.py${NC} - Work with vector embeddings"
else
    echo -e "${RED}Setup failed due to connection issues.${NC}"
    echo -e "${YELLOW}Please check your environment variables and Supabase settings.${NC}"
    exit 1
fi 