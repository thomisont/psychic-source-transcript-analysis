#!/usr/bin/env python3
"""
Test script for Supabase connection and database inspection.
This script verifies connectivity and displays database schema information.
"""
import os
import sys
from pathlib import Path
import json
print("Script started")  # Debug
print(f"Working directory: {os.getcwd()}")  # Debug

try:
    from prettytable import PrettyTable
    print("Imported PrettyTable successfully")  # Debug
except ImportError as e:
    print(f"Error importing PrettyTable: {e}")  # Debug
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("Imported dotenv successfully")  # Debug
except ImportError as e:
    print(f"Error importing dotenv: {e}")  # Debug
    sys.exit(1)

# Add the parent directory to the path so we can import the supabase_client
print(f"Adding {str(Path(__file__).parent.parent)} to path")  # Debug
sys.path.append(str(Path(__file__).parent.parent))

try:
    from tools.supabase_client import SupabaseClient
    print("Imported SupabaseClient successfully")  # Debug
except ImportError as e:
    print(f"Error importing SupabaseClient: {e}")  # Debug
    sys.exit(1)

print("Loading environment variables")  # Debug
load_dotenv()
print(f"SUPABASE_URL exists: {bool(os.environ.get('SUPABASE_URL'))}")  # Debug
print(f"SUPABASE_SERVICE_KEY exists: {bool(os.environ.get('SUPABASE_SERVICE_KEY'))}")  # Debug

def test_connection():
    """Test connection to Supabase"""
    print("Testing connection to Supabase...")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Check environment variables
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Error: Missing Supabase environment variables (SUPABASE_URL, SUPABASE_SERVICE_KEY)")
            return False
        
        # Initialize client
        supabase = SupabaseClient()
        
        # Try running a simple query
        result = supabase.execute_sql("SELECT version()")
        
        if result and len(result) > 0:
            print(f"✅ Successfully connected to Supabase PostgreSQL: {result[0]['version']}")
            return supabase
        else:
            print("❌ Error: Could connect but received no result from version query")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return False

def list_tables(supabase):
    """List all tables in the database"""
    try:
        print("\n📋 Listing tables in the database...")
        tables = supabase.get_tables()
        
        if not tables:
            print("No tables found in the database.")
            return []
        
        # Create a table for display
        table = PrettyTable()
        table.field_names = ["Table Name", "Row Count"]
        
        # Get row count for each table
        for table_name in tables:
            try:
                count_result = supabase.execute_sql(f"SELECT COUNT(*) FROM {table_name}")
                row_count = count_result[0]['count'] if count_result else 0
                table.add_row([table_name, row_count])
            except Exception as e:
                table.add_row([table_name, f"Error: {e}"])
        
        print(table)
        return tables
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return []

def show_table_schema(supabase, table_name):
    """Show schema for a specific table"""
    try:
        print(f"\n📝 Schema for table '{table_name}':")
        
        # Get column information
        schema = supabase.get_schema(table_name)
        
        if not schema:
            print(f"No schema information found for table '{table_name}'.")
            return
        
        # Create a table for display
        table = PrettyTable()
        table.field_names = ["Column Name", "Data Type", "Nullable", "Primary Key"]
        
        # Get primary key information
        pk_query = f"""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = '{table_name}'::regclass
        AND i.indisprimary;
        """
        
        try:
            primary_keys = supabase.execute_sql(pk_query)
            pk_columns = [pk['attname'] for pk in primary_keys] if primary_keys else []
        except:
            pk_columns = []
        
        # Add rows
        for column in schema:
            is_pk = column['column_name'] in pk_columns
            table.add_row([
                column['column_name'],
                column['data_type'],
                "YES" if column['is_nullable'] == 'YES' else "NO",
                "✓" if is_pk else ""
            ])
        
        print(table)
        
        # Get index information
        print(f"\n📊 Indexes for table '{table_name}':")
        
        index_query = f"""
        SELECT
            i.relname AS index_name,
            array_agg(a.attname) AS column_names,
            ix.indisunique AS is_unique
        FROM
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_attribute a
        WHERE
            t.oid = ix.indrelid
            AND i.oid = ix.indexrelid
            AND a.attrelid = t.oid
            AND a.attnum = ANY(ix.indkey)
            AND t.relkind = 'r'
            AND t.relname = '{table_name}'
        GROUP BY
            i.relname,
            ix.indisunique
        ORDER BY
            i.relname;
        """
        
        try:
            indexes = supabase.execute_sql(index_query)
            
            if not indexes:
                print("No indexes found.")
                return
            
            # Create a table for display
            index_table = PrettyTable()
            index_table.field_names = ["Index Name", "Columns", "Unique"]
            
            for idx in indexes:
                index_table.add_row([
                    idx['index_name'],
                    ", ".join(idx['column_names']),
                    "✓" if idx['is_unique'] else ""
                ])
            
            print(index_table)
            
        except Exception as e:
            print(f"Could not retrieve index information: {e}")
        
    except Exception as e:
        print(f"❌ Error showing schema for table '{table_name}': {e}")

def sample_data(supabase, table_name, limit=5):
    """Show sample data from a table"""
    try:
        print(f"\n📊 Sample data from table '{table_name}' (top {limit} rows):")
        
        result = supabase.query(table_name, limit=limit)
        
        if not result or len(result) == 0:
            print(f"No data found in table '{table_name}'.")
            return
        
        # Create a table for display
        table = PrettyTable()
        
        # Get column names from the first row
        columns = list(result[0].keys())
        table.field_names = columns
        
        # Add data rows
        for row in result:
            # Format large fields for display
            row_values = []
            for col in columns:
                value = row[col]
                
                if isinstance(value, dict) or isinstance(value, list):
                    # Format JSON objects
                    value = json.dumps(value)[:50] + "..." if len(json.dumps(value)) > 50 else json.dumps(value)
                elif isinstance(value, str) and len(value) > 50:
                    # Truncate long strings
                    value = value[:50] + "..."
                
                row_values.append(value)
                
            table.add_row(row_values)
        
        print(table)
        
    except Exception as e:
        print(f"❌ Error fetching sample data from table '{table_name}': {e}")

def run_test_query(supabase, query):
    """Run a custom SQL query"""
    try:
        print(f"\n🔍 Running custom query: {query}")
        
        result = supabase.execute_sql(query)
        
        if not result or len(result) == 0:
            print("Query returned no results.")
            return
        
        # Create a table for display
        table = PrettyTable()
        
        # Get column names from the first row
        columns = list(result[0].keys())
        table.field_names = columns
        
        # Add data rows
        for row in result:
            # Format large fields for display
            row_values = []
            for col in columns:
                value = row[col]
                
                if isinstance(value, dict) or isinstance(value, list):
                    # Format JSON objects
                    value = json.dumps(value)[:50] + "..." if len(json.dumps(value)) > 50 else json.dumps(value)
                elif isinstance(value, str) and len(value) > 50:
                    # Truncate long strings
                    value = value[:50] + "..."
                
                row_values.append(value)
                
            table.add_row(row_values)
        
        print(table)
        print(f"Query returned {len(result)} rows.")
        
    except Exception as e:
        print(f"❌ Error running custom query: {e}")

def check_pgvector(supabase):
    """Check if pgvector extension is enabled"""
    try:
        print("\n🔍 Checking for pgvector extension...")
        
        result = supabase.execute_sql("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        
        if result and len(result) > 0:
            print("✅ pgvector extension is enabled")
            return True
        else:
            print("❌ pgvector extension is not enabled")
            return False
            
    except Exception as e:
        print(f"❌ Error checking for pgvector extension: {e}")
        return False

def main():
    """Main function"""
    # Test connection
    supabase = test_connection()
    
    if not supabase:
        print("Exiting due to connection issues.")
        return 1
    
    # Get tables
    tables = list_tables(supabase)
    
    # Check for pgvector
    check_pgvector(supabase)
    
    if tables:
        while True:
            print("\n🔧 Available commands:")
            print("  1. Show schema for a table")
            print("  2. Show sample data from a table")
            print("  3. Run a custom SQL query")
            print("  4. Check pgvector extension")
            print("  5. Exit")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == '1':
                table_name = input("Enter table name: ")
                if table_name in tables:
                    show_table_schema(supabase, table_name)
                else:
                    print(f"Table '{table_name}' not found.")
            
            elif choice == '2':
                table_name = input("Enter table name: ")
                if table_name in tables:
                    limit = input("Enter number of rows to show (default: 5): ")
                    try:
                        limit = int(limit) if limit else 5
                    except:
                        limit = 5
                    sample_data(supabase, table_name, limit)
                else:
                    print(f"Table '{table_name}' not found.")
            
            elif choice == '3':
                query = input("Enter SQL query: ")
                if query:
                    run_test_query(supabase, query)
                else:
                    print("No query provided.")
            
            elif choice == '4':
                check_pgvector(supabase)
            
            elif choice == '5':
                print("Exiting.")
                break
            
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 