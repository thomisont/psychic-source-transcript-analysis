"""
Supabase client utility for interacting with Supabase from Replit.
This module provides functions to query and manipulate data in Supabase.
Now uses the official supabase-py client.
"""
import os
import json
import requests # Keep for potential direct calls if needed
import pandas as pd
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

# Import official Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    logging.error("supabase-py library not found. Please install it: pip install supabase")
    Client = None # Define Client as None if import fails
    create_client = None

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and/or service key not found in environment variables")

class SupabaseClient:
    """Client wrapping the official supabase-py library."""
    
    def __init__(self, url: str, key: str):
        """Initialize Supabase client using supabase-py."""
        self.url = url # Use passed URL
        self.key = key   # Use passed Key
        self.client: Client | None = None # Type hint for the official client
        
        if not self.url or not self.key:
            # Add check here in case empty strings are passed
            raise ValueError("Supabase URL and Key must be provided during initialization")

        self.headers = { # Keep headers for potential direct requests
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        
        try:
            if create_client:
                self.client = create_client(self.url, self.key)
                # Log the type AND available methods/attributes of the created client
                logging.info(f"Type of self.client after initialization: {type(self.client)}") 
                logging.info(f"Attributes/Methods available on self.client: {dir(self.client)}")
                logging.info("Official Supabase client initialized successfully.")
            else:
                raise ImportError("create_client function not available from supabase library.")
        except Exception as e:
            logging.error(f"Failed to initialize official Supabase client: {e}", exc_info=True)
            self.client = None # Ensure client is None on failure

    # --- Standard Table Operations (using supabase-py) ---
    def query(self, table_name, select="*", filters=None, limit=None, order=None):
        if not self.client:
            raise Exception("Supabase client not initialized")
        try:
            query = self.client.table(table_name).select(select)
            if filters: # Assuming filters is { 'column': 'eq.value' } format
                for col, filt in filters.items():
                    op, val = filt.split('.', 1)
                    query = query.filter(col, op, val)
            if order: # Assuming order is 'column.desc' or 'column.asc'
                col, direction = order.split('.')
                query = query.order(col, desc=(direction == 'desc'))
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logging.error(f"Error querying table {table_name} via supabase-py: {e}", exc_info=True)
            raise

    def insert(self, table_name, data):
        if not self.client:
            raise Exception("Supabase client not initialized")
        try:
            response = self.client.table(table_name).insert(data).execute()
            return response.data
        except Exception as e:
            logging.error(f"Error inserting into table {table_name} via supabase-py: {e}", exc_info=True)
            raise

    def update(self, table_name, data, filters):
        if not self.client:
            raise Exception("Supabase client not initialized")
        try:
            query = self.client.table(table_name).update(data)
            if filters: # Assuming filters is { 'column': 'eq.value' } format
                for col, filt in filters.items():
                    op, val = filt.split('.', 1)
                    query = query.filter(col, op, val)
            response = query.execute()
            return response.data
        except Exception as e:
            logging.error(f"Error updating table {table_name} via supabase-py: {e}", exc_info=True)
            raise

    def delete(self, table_name, filters):
        if not self.client:
            raise Exception("Supabase client not initialized")
        try:
            query = self.client.table(table_name).delete()
            if filters: # Assuming filters is { 'column': 'eq.value' } format
                for col, filt in filters.items():
                    op, val = filt.split('.', 1)
                    query = query.filter(col, op, val)
            response = query.execute()
            return response.data
        except Exception as e:
            logging.error(f"Error deleting from table {table_name} via supabase-py: {e}", exc_info=True)
            raise

    def execute_sql(self, sql: str, params: dict = None):
        """Executes a raw SQL query using the 'execute_sql' RPC function in Supabase."""
        if not self.client:
            raise Exception("Supabase client not initialized")
            
        # Our RPC function 'execute_sql' expects 'query_sql' and 'query_params'
        rpc_params = {'query_sql': sql, 'query_params': None}
        
        if params:
            # If params are provided, try to JSON encode them for the RPC function
            try:
                 rpc_params['query_params'] = json.dumps(params)
            except TypeError as json_err:
                 logging.error(f"Failed to JSON encode params for execute_sql RPC: {params}, Error: {json_err}")
                 raise ValueError(f"Invalid parameters for execute_sql RPC: {json_err}")
        
        logging.debug(f"Calling Supabase RPC 'execute_sql' with SQL: {sql[:150]}... Params: {rpc_params['query_params']}")
        
        try:
            # Call the RPC function WE CREATED named 'execute_sql'
            response = self.client.rpc('execute_sql', rpc_params).execute()
            
            logging.debug(f"RPC execute_sql raw response: {response}")

            # Check response structure
            if hasattr(response, 'data'):
                response_data = response.data
                # Check if the RPC returned an error structure (as defined in our function)
                if isinstance(response_data, dict) and response_data.get('error'):
                     error_info = response_data['error']
                     sqlstate = response_data.get('sqlstate', 'N/A')
                     logging.error(f"Supabase function 'execute_sql' returned error object: {error_info} (SQLSTATE: {sqlstate})")
                     raise Exception(f"Supabase Function Error: {error_info} (SQLSTATE: {sqlstate})")
                # Assume success if no error structure found
                return response_data
            else:
                logging.error(f"Supabase RPC response did not contain 'data'. Response: {response}")
                raise Exception("Unexpected response format from Supabase RPC execution.")

        except Exception as e:
            # Catch errors during RPC call or re-raised errors
            logging.error(f"Error during RPC call 'execute_sql': {e}\nSQL: {sql}\nParams: {params}", exc_info=True)
            # Re-raise a generic error for the route handler
            raise Exception(f"Database query execution failed: {e}")

    # --- RPC Function Calls (using supabase-py) ---
    def get_tables(self): 
        logging.debug("Attempting Supabase connection test via sql('SELECT 1')...")
        try:
            # Use the CORRECTED execute_sql method for the connection test
            result = self.execute_sql('SELECT 1') 
            if result is not None:
                logging.debug("Supabase connection test successful.")
                # Return an empty list for now, as the purpose is just the check
                return [] 
            else:
                logging.warning("Supabase connection test (execute_sql) returned None or empty result.")
                raise ConnectionError("Supabase connection test returned unexpected data.")
        except Exception as e:
            logging.error(f"Supabase connection test failed: {e}", exc_info=True)
            raise ConnectionError(f"Supabase connection check failed: {e}")

    def get_schema(self, table_name):
        logging.warning(f"get_schema for {table_name} is not implemented with the standard client. Returning empty list.")
        return [] 

    # ... (DataFrame methods can be adapted or removed if not used) ...
    def query_to_dataframe(self, table_name, select="*", filters=None, limit=None, order=None):
        data = self.query(table_name, select, filters, limit, order)
        return pd.DataFrame(data)
    
    def dataframe_to_supabase(self, df, table_name, upsert=False, on_conflict=None):
        records = df.to_dict(orient='records')
        if upsert:
             if not self.client: raise Exception("Supabase client not initialized")
             response = self.client.table(table_name).upsert(records, on_conflict=on_conflict).execute()
             return response.data
        else:
             return self.insert(table_name, records)


# Simple usage examples if run directly
if __name__ == "__main__":
    # Load directly for example
    load_dotenv()
    SUPABASE_URL_EXAMPLE = os.getenv('SUPABASE_URL')
    SUPABASE_KEY_EXAMPLE = os.getenv('SUPABASE_SERVICE_KEY')

    if not SUPABASE_URL_EXAMPLE or not SUPABASE_KEY_EXAMPLE:
        print("Supabase URL/Key not found in .env for example run.")
        exit()

    # Initialize client with URL/Key
    supabase_wrapper = SupabaseClient(SUPABASE_URL_EXAMPLE, SUPABASE_KEY_EXAMPLE)
    
    if not supabase_wrapper.client:
         print("Failed to initialize Supabase client. Exiting example.")
         exit()

    # Example: List tables
    try:
        tables = supabase_wrapper.get_tables()
        print("Tables in the database:")
        if isinstance(tables, list):
             for table in tables:
                  print(f"- {table}")
        else:
             print(f"Unexpected result for get_tables: {tables}")
    except Exception as e:
        print(f"Error listing tables: {e}")
    
    # Example: Get schema of a table (This will now return empty or raise error)
    try:
        table_name = "conversations"  # Replace with an actual table name
        schema = supabase_wrapper.get_schema(table_name)
        print(f"\nSchema for table '{table_name}': {schema}")
        # Original print loop commented out as schema is empty now
        # for column in schema:
        #     print(f"- {column['column_name']} ({column['data_type']}) {'NULL' if column['is_nullable'] == 'YES' else 'NOT NULL'}")
    except Exception as e:
        print(f"Error getting schema for {table_name}: {e}") 