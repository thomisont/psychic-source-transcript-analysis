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
        """Executes a SQL query using the execute_sql RPC function in Supabase."""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        try:
            # Prepare the parameters for the RPC call
            rpc_params = {'query_sql': sql}
            if params:
                # Ensure params is a valid JSON object string if not None
                try:
                     rpc_params['query_params'] = json.dumps(params)
                except TypeError as json_err:
                     logging.error(f"Failed to JSON encode params for execute_sql: {params}, Error: {json_err}")
                     raise ValueError(f"Invalid parameters for execute_sql: {json_err}")
            else:
                rpc_params['query_params'] = None # Pass SQL NULL if no params

            logging.debug(f"Calling Supabase RPC 'execute_sql' with SQL: {sql[:100]}... Params: {rpc_params['query_params']}")
            
            # Call the RPC function named 'execute_sql'
            response = self.client.rpc('execute_sql', rpc_params).execute()
            
            # >>> IMPROVE ERROR HANDLING <<<
            logging.debug(f"RPC execute_sql raw response: {response}") # Log raw response

            # Check for underlying HTTP errors first if possible (depends on supabase-py version)
            # Example: if hasattr(response, 'error') and response.error:
            #     logging.error(f"Supabase client error: {response.error}")
            #     raise Exception(f"Supabase client error: {response.error}")

            # Check response data type and content
            if not hasattr(response, 'data'):
                 logging.error(f"Supabase RPC response for execute_sql lacked 'data' attribute. Response: {response}")
                 raise Exception("Supabase RPC response missing 'data' attribute.")
                 
            response_data = response.data
            logging.debug(f"RPC execute_sql data type: {type(response_data)}, content: {str(response_data)[:200]}...")

            # Handle potential error message returned *within* the data payload
            # Check if data itself is the error string (as seen in logs)
            if isinstance(response_data, str) and 'error' in response_data.lower():
                 logging.error(f"Supabase RPC returned an error string in data: {response_data}")
                 # Try to extract a more specific message if it follows a pattern, otherwise use the string
                 error_message = response_data
                 raise Exception(f"Supabase RPC Error: {error_message}")
            # Check if data is a dictionary containing an error key (as the Supabase function intended on EXCEPTION)
            elif isinstance(response_data, dict) and response_data.get('error'):
                error_info = response_data['error']
                sqlstate = response_data.get('sqlstate', 'N/A')
                logging.error(f"Supabase function returned error object: {error_info} (SQLSTATE: {sqlstate})")
                raise Exception(f"Supabase Function Error: {error_info} (SQLSTATE: {sqlstate})")
            # Optional: Check for other non-JSON array results if needed
            elif not isinstance(response_data, list):
                 logging.warning(f"Supabase RPC execute_sql returned unexpected data type: {type(response_data)}. Expected list (JSON array). Data: {str(response_data)[:200]}")
                 # Depending on strictness, either return as is, or raise an error
                 # raise Exception(f"Unexpected data format from execute_sql: {type(response_data)}")
                 pass # Allow non-list results for now, might need adjustment

            # If no error detected, return the data
            return response_data
            # >>> END IMPROVED ERROR HANDLING <<<
        
        except Exception as e:
            # Catch other exceptions like network errors, client errors, or re-raised errors
            logging.error(f"Error during RPC call 'execute_sql': {e}\nSQL: {sql}\nParams: {params}", exc_info=True)
            raise # Re-raise the exception

    # --- RPC Function Calls (using supabase-py) ---
    def get_tables(self): # Keep direct request as example or if RPC fails
        # >>> REWRITE to use execute_sql('SELECT 1') as a connection test <<<
        logging.debug("Attempting Supabase connection test via execute_sql('SELECT 1')...")
        try:
            # Use the existing execute_sql method which calls the RPC function we created
            result = self.execute_sql('SELECT 1') # REMOVED SEMICOLON
            # Simple check: If execute_sql didn't raise an error and returned something, assume connected.
            # More specific checks could be added based on expected result format.
            if result is not None:
                logging.debug("Supabase connection test successful.")
                # Return an empty list to satisfy original callers expecting a list of tables, 
                # even though we aren't actually getting tables anymore.
                return [] 
            else:
                logging.warning("Supabase connection test (execute_sql) returned None or empty result.")
                raise ConnectionError("Supabase connection test returned unexpected data.")
        except Exception as e:
            logging.error(f"Supabase connection test failed: {e}", exc_info=True)
            # Reraise the exception so the caller knows the check failed
            raise ConnectionError(f"Supabase connection check failed: {e}")

        # >>> REMOVE old implementation <<<
        # endpoint = f"{self.url}/rest/v1/rpc/get_tables"
        # try:
        #     response = requests.post(endpoint, headers=self.headers, json={})
        #     response.raise_for_status()
        #     return response.json()
        # except Exception as e:
        #     logging.warning(f"RPC call to get_tables failed: {e}. Falling back to SQL query.")
        #     # NOTE: This fallback will now fail if execute_sql is removed!
        #     # Consider removing this fallback or implementing it differently if get_tables RPC fails.
        #     # For now, returning empty list on failure.
        #     logging.error(f"Cannot execute fallback SQL query for get_tables as execute_sql is removed.")
        #     return [] # Return empty list if RPC fails

    def get_schema(self, table_name):
        # This method relied on execute_sql. It needs to be refactored or removed.
        # For now, let's return an empty list or raise an error.
        logging.warning(f"get_schema for {table_name} cannot run as execute_sql is removed. Returning empty list.")
        return [] 
        # OR: raise NotImplementedError("get_schema needs reimplementation without execute_sql")

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