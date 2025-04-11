#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite/PostgreSQL to Supabase.
This script transfers conversations, messages, and analysis results.
"""
import os
import sys
from pathlib import Path
import argparse
import logging
import time
from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the supabase_client
sys.path.append(str(Path(__file__).parent.parent))
from tools.supabase_client import SupabaseClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)

def get_source_engine(source_url):
    """Create SQLAlchemy engine for the source database"""
    try:
        engine = create_engine(source_url)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logging.info(f"Successfully connected to source database")
        return engine
    except Exception as e:
        logging.error(f"Error connecting to source database: {e}")
        raise

def get_table_names(engine):
    """Get all table names from the source database"""
    try:
        # This works for SQLite and PostgreSQL
        with engine.connect() as conn:
            if 'sqlite' in engine.url.drivername:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result if not row[0].startswith('sqlite_')]
            else:
                result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
                tables = [row[0] for row in result]
        
        logging.info(f"Found {len(tables)} tables in source database: {', '.join(tables)}")
        return tables
    except Exception as e:
        logging.error(f"Error getting table names: {e}")
        raise

def get_table_schema(engine, table_name):
    """Get schema information for a table"""
    try:
        # Query column information
        with engine.connect() as conn:
            if 'sqlite' in engine.url.drivername:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [
                    {
                        'name': row[1],
                        'type': row[2],
                        'nullable': not row[3],
                        'primary_key': bool(row[5])
                    }
                    for row in result
                ]
            else:
                query = text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    (SELECT TRUE FROM pg_constraint c 
                     WHERE c.conrelid = t.oid AND c.contype = 'p' 
                     AND a.attnum = ANY(c.conkey)) AS primary_key
                FROM
                    pg_attribute a
                JOIN
                    pg_class t ON a.attrelid = t.oid
                JOIN
                    pg_namespace s ON t.relnamespace = s.oid
                JOIN
                    information_schema.columns isc ON isc.column_name = a.attname AND isc.table_name = t.relname
                WHERE
                    a.attnum > 0
                    AND NOT a.attisdropped
                    AND t.relname = :table_name
                    AND s.nspname = 'public'
                ORDER BY a.attnum
                """)
                result = conn.execute(query, {"table_name": table_name})
                columns = [
                    {
                        'name': row[0],
                        'type': row[1],
                        'nullable': row[2] == 'YES',
                        'primary_key': row[3] or False
                    }
                    for row in result
                ]
        
        logging.info(f"Schema for table '{table_name}': {len(columns)} columns")
        return columns
    except Exception as e:
        logging.error(f"Error getting schema for table '{table_name}': {e}")
        raise

def get_table_data(engine, table_name, batch_size=1000):
    """Get data from a table in batches"""
    try:
        # Get total count first
        with engine.connect() as conn:
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            total_count = count_result.scalar()
        
        logging.info(f"Table '{table_name}' has {total_count} rows, fetching in batches of {batch_size}")
        
        # Use pandas to read in batches
        offsets = range(0, total_count, batch_size)
        
        for offset in offsets:
            query = f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
            batch_df = pd.read_sql(query, engine)
            
            yield batch_df, offset, total_count
            
    except Exception as e:
        logging.error(f"Error fetching data from table '{table_name}': {e}")
        raise

def create_table_in_supabase(supabase, table_name, columns):
    """Create a table in Supabase based on source schema"""
    # SQL type conversion from SQLite/Postgres to PostgreSQL (Supabase)
    type_map = {
        'INTEGER': 'integer',
        'BIGINT': 'bigint',
        'SMALLINT': 'smallint',
        'INT': 'integer',
        'REAL': 'real',
        'FLOAT': 'double precision',
        'DOUBLE': 'double precision',
        'TEXT': 'text',
        'VARCHAR': 'varchar',
        'CHARACTER VARYING': 'varchar',
        'CHAR': 'char',
        'BOOLEAN': 'boolean',
        'TIMESTAMP': 'timestamp',
        'TIMESTAMP WITH TIME ZONE': 'timestamp with time zone',
        'DATE': 'date',
        'TIME': 'time',
        'BLOB': 'bytea',
        'UUID': 'uuid',
        'JSONB': 'jsonb',
        'JSON': 'json'
    }
    
    # Generate CREATE TABLE SQL
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    
    column_defs = []
    primary_key_cols = []
    
    for col in columns:
        col_name = col['name']
        # Try to map the type, default to TEXT if not found
        col_type = type_map.get(col['type'].upper(), 'text')
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        
        column_def = f"    {col_name} {col_type} {nullable}"
        column_defs.append(column_def)
        
        if col['primary_key']:
            primary_key_cols.append(col_name)
    
    # Add primary key constraint if there are primary key columns
    if primary_key_cols:
        pk_constraint = f"    PRIMARY KEY ({', '.join(primary_key_cols)})"
        column_defs.append(pk_constraint)
    
    create_sql += ",\n".join(column_defs)
    create_sql += "\n);"
    
    try:
        # Execute the CREATE TABLE statement
        result = supabase.execute_sql(create_sql)
        logging.info(f"Created table '{table_name}' in Supabase")
        
        # Add an index on external_id if it exists and isn't already the primary key
        if 'external_id' in [col['name'] for col in columns] and 'external_id' not in primary_key_cols:
            index_sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_external_id ON {table_name} (external_id);"
            supabase.execute_sql(index_sql)
            logging.info(f"Created index on {table_name}(external_id)")
            
        # Add timestamp index if there's a timestamp column
        timestamp_cols = [col['name'] for col in columns if col['name'] in ('timestamp', 'created_at', 'updated_at')]
        for ts_col in timestamp_cols:
            index_sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{ts_col} ON {table_name} ({ts_col});"
            supabase.execute_sql(index_sql)
            logging.info(f"Created index on {table_name}({ts_col})")
        
        return True
    except Exception as e:
        logging.error(f"Error creating table '{table_name}' in Supabase: {e}")
        return False

def insert_batch_to_supabase(supabase, table_name, batch_df, unique_cols=None):
    """Insert a batch of data into Supabase"""
    try:
        if batch_df.empty:
            logging.warning(f"Empty batch for table '{table_name}', skipping")
            return 0
        
        # Convert DataFrame to list of records
        records = batch_df.where(pd.notnull(batch_df), None).to_dict(orient='records')
        
        # Prepare for upsert if unique columns are specified
        if unique_cols:
            # Use upsert via the dataframe_to_supabase method
            response = supabase.dataframe_to_supabase(
                batch_df, 
                table_name, 
                upsert=True, 
                on_conflict=','.join(unique_cols)
            )
        else:
            # Use regular insert
            response = supabase.insert(table_name, records)
        
        return len(records)
    except Exception as e:
        logging.error(f"Error inserting batch to table '{table_name}': {e}")
        raise

def migrate_table(supabase, engine, table_name, batch_size=1000, unique_cols=None):
    """Migrate a single table from source to Supabase"""
    try:
        # Get schema
        columns = get_table_schema(engine, table_name)
        
        # Create table in Supabase
        create_success = create_table_in_supabase(supabase, table_name, columns)
        if not create_success:
            logging.error(f"Failed to create table '{table_name}' in Supabase, skipping migration")
            return False
        
        # Migrate data in batches
        total_inserted = 0
        start_time = time.time()
        
        for batch_df, offset, total_count in get_table_data(engine, table_name, batch_size):
            batch_start = time.time()
            
            if len(batch_df) > 0:
                # Handle SQLite-specific data type conversions if needed
                if 'sqlite' in engine.url.drivername:
                    # Convert datetime columns
                    for col in batch_df.columns:
                        if 'timestamp' in col.lower() or 'date' in col.lower() or col in ('created_at', 'updated_at'):
                            try:
                                batch_df[col] = pd.to_datetime(batch_df[col])
                            except:
                                pass
                
                # Insert batch to Supabase
                inserted = insert_batch_to_supabase(supabase, table_name, batch_df, unique_cols)
                total_inserted += inserted
                
                batch_time = time.time() - batch_start
                progress = min(100, (offset + len(batch_df)) / total_count * 100)
                logging.info(f"Migrated batch for '{table_name}': {inserted} rows, {progress:.1f}% complete, {batch_time:.2f}s")
            
            # Small delay to avoid overwhelming the Supabase API
            time.sleep(0.5)
        
        total_time = time.time() - start_time
        logging.info(f"Completed migration for table '{table_name}': {total_inserted} rows in {total_time:.2f}s")
        return True
        
    except Exception as e:
        logging.error(f"Error migrating table '{table_name}': {e}")
        return False

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Migrate data from source database to Supabase')
    parser.add_argument('--source-url', required=True, help='Source database URL (SQLite or PostgreSQL)')
    parser.add_argument('--tables', nargs='+', help='Specific tables to migrate (default: all)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for data transfer (default: 1000)')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Create clients
    try:
        source_engine = get_source_engine(args.source_url)
        supabase = SupabaseClient()
    except Exception as e:
        logging.error(f"Failed to initialize clients: {e}")
        return 1
    
    # Get all tables from source if not specified
    table_names = args.tables or get_table_names(source_engine)
    
    # Prioritize main tables first (conversations, messages)
    priority_tables = ['conversations', 'messages']
    table_names = sorted(table_names, key=lambda x: (x not in priority_tables, x))
    
    # Run the migration
    for table_name in table_names:
        # Skip SQLite system tables
        if table_name.startswith('sqlite_'):
            continue
            
        logging.info(f"Starting migration for table '{table_name}'")
        
        # Determine unique columns for upsert based on table
        unique_cols = None
        if table_name == 'conversations':
            unique_cols = ['external_id']
            
        success = migrate_table(
            supabase=supabase,
            engine=source_engine,
            table_name=table_name,
            batch_size=args.batch_size,
            unique_cols=unique_cols
        )
        
        if success:
            logging.info(f"Successfully migrated table '{table_name}'")
        else:
            logging.error(f"Failed to migrate table '{table_name}'")
    
    logging.info("Migration completed")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 