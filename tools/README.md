# Supabase Integration Tools

This directory contains utilities to help with the migration from SQLite to Supabase PostgreSQL and integrating Supabase into the application.

## Available Tools

### 1. Supabase Client (`supabase_client.py`)

A Python client for interacting with Supabase REST API.

**Features:**
- Query, insert, update, and delete data in Supabase tables
- Execute SQL queries directly
- Get table schemas and metadata
- Convert between pandas DataFrames and Supabase data

**Example usage:**
```python
from tools.supabase_client import SupabaseClient

# Initialize client
supabase = SupabaseClient()

# Query data
conversations = supabase.query(
    table_name="conversations",
    select="id,external_id,title,created_at",
    limit=10,
    order="created_at.desc"
)

# Insert data
result = supabase.insert("conversations", {
    "external_id": "123456",
    "title": "New conversation",
    "created_at": "2025-04-08T12:00:00Z"
})
```

### 2. Type Generator (`generate_types.py`) 

Generates TypeScript type definitions and JSON schema from your Supabase database schema.

**Features:**
- Create TypeScript interfaces matching your database tables
- Generate JSON Schema definitions
- Create SQL migration scripts for schema replication

**Usage:**
```bash
# Generate all types
python tools/generate_types.py --output-dir ./generated

# Generate only TypeScript types
python tools/generate_types.py --format typescript --output-dir ./generated/types

# Generate only SQL migration
python tools/generate_types.py --format sql --output-dir ./migrations
```

### 3. Migration Tool (`migrate_to_supabase.py`)

Migrates data from an existing database (SQLite or PostgreSQL) to Supabase.

**Features:**
- Transfers schema and data for all tables
- Handles batching for large datasets
- Creates appropriate indexes
- Supports upsert for idempotent migrations

**Usage:**
```bash
# Migrate all tables
python tools/migrate_to_supabase.py --source-url "postgresql://user:pass@localhost:5432/app_db"

# Migrate specific tables with batch size
python tools/migrate_to_supabase.py \
  --source-url "sqlite:///instance/app.db" \
  --tables conversations messages \
  --batch-size 500
```

### 4. Vector Embeddings (`supabase_vectors.py`)

Utilizes Supabase's pgvector extension for semantic search across conversation transcripts.

**Features:**
- Create embeddings from conversation text
- Store and index embeddings in Supabase
- Perform similarity searches
- Support for OpenAI or local embedding models

**Usage:**
```bash
# Create the embeddings table
python tools/supabase_vectors.py --action create-table

# Process conversations and generate embeddings
python tools/supabase_vectors.py --action process --limit 100

# Search for similar conversations
python tools/supabase_vectors.py --action search --query "What are good meditation techniques?"
```

## Setup Instructions

1. Ensure your `.env` file contains the necessary Supabase credentials:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key
   DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
   ```

2. Install required dependencies:
   ```bash
   pip install requests pandas psycopg2-binary sqlalchemy openai tqdm python-dotenv
   ```

3. For vector embeddings with local models, install:
   ```bash
   pip install sentence-transformers
   ```

## Workflow Example

Here's a complete workflow for migrating to Supabase:

1. Generate schema from existing database:
   ```bash
   python tools/generate_types.py --format sql
   ```

2. Migrate data to Supabase:
   ```bash
   python tools/migrate_to_supabase.py --source-url "sqlite:///instance/app.db"
   ```

3. Generate TypeScript types for frontend:
   ```bash
   python tools/generate_types.py --format typescript
   ```

4. Create vector embeddings for semantic search:
   ```bash
   python tools/supabase_vectors.py --action create-table
   python tools/supabase_vectors.py --action process
   ```

## Troubleshooting

- If you encounter permission issues with Supabase, make sure your service key has the necessary permissions.
- For large migrations, consider increasing the batch size to speed up the process.
- Vector embeddings require the pgvector extension to be enabled in your Supabase project.
- When running in Replit, be aware of timeout constraints for long-running operations. 