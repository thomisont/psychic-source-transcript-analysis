#!/usr/bin/env python3
"""
Test script to verify Supabase connection and check for expected tables.
"""
import os
import sys
import traceback
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

print("--- Script starting ---")

# Explicitly load .env file from the current directory
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"Looking for .env file at: {dotenv_path}")

if os.path.exists(dotenv_path):
    print(".env file found. Loading environment variables...")
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    print(".env file not found at the specified path.")

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"DATABASE_URL loaded from environment: {DATABASE_URL}")

# Get database connection parameters from environment variables
db_url = DATABASE_URL

if not db_url:
    print("ERROR: DATABASE_URL environment variable not found")
    exit(1)

print(f"Database URL found: {db_url[:10]}...")
print("Attempting to connect to database...")

def check_supabase_connection():
    """Checks the connection to Supabase and lists tables."""
    print("\n--- Checking Supabase Connection ---")
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        print("Please ensure it is set in your .env file or environment.")
        # Print relevant env vars for debugging
        print(f"  ELEVENLABS_API_KEY set: {'Yes' if os.getenv('ELEVENLABS_API_KEY') else 'No'}")
        print(f"  OPENAI_API_KEY set: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
        print(f"  DATABASE_URL set: {'Yes' if DATABASE_URL else 'No'}")
        return False

    conn = None
    try:
        print(f"Attempting to connect to database using URL: {DATABASE_URL[:15]}...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        
        # Create a cursor
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("Connected to database successfully!")
        
        # Query to get all tables in the public schema
        cur.execute("""
        SELECT table_name, 
               (SELECT count(*) FROM information_schema.columns WHERE table_name=t.table_name) as column_count
        FROM information_schema.tables t
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"- {table['table_name']} ({table['column_count']} columns)")
            
        # For conversations and messages tables, count rows
        if any(table['table_name'] == 'conversations' for table in tables):
            print("\nChecking conversations table...")
            cur.execute("SELECT COUNT(*) as count FROM conversations")
            count = cur.fetchone()['count']
            print(f"Conversations table contains {count} rows")
            
            if count > 0:
                cur.execute("SELECT * FROM conversations LIMIT 1")
                sample = cur.fetchone()
                print("Sample conversation record:")
                for key, value in sample.items():
                    print(f"  {key}: {value}")
        
        if any(table['table_name'] == 'messages' for table in tables):
            print("\nChecking messages table...")
            cur.execute("SELECT COUNT(*) as count FROM messages")
            count = cur.fetchone()['count']
            print(f"Messages table contains {count} rows")
        
        # Close the connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print("Exception details:")
        print(f"Type: {type(e).__name__}")
        print(f"Exception: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        # Print environment variables for debugging (omitting sensitive data)
        env_keys = [key for key in os.environ.keys() if 'DATABASE' in key or 'SUPABASE' in key]
        print(f"Found environment variables: {env_keys}")
        for key in env_keys:
            if 'KEY' in key or 'URL' in key:
                value = os.environ.get(key)
                print(f"  {key}: {value[:10]}..." if value else f"  {key}: None")
        return False

    return True

if check_supabase_connection():
    print("\n--- Supabase connection successful! ---")
else:
    print("\n--- Supabase connection failed. ---")
    exit(1) 