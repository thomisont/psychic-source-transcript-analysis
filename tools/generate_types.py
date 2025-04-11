#!/usr/bin/env python3
"""
Script to generate TypeScript types from Supabase schema.
This helps maintain consistency between backend and frontend data structures.
"""
import os
import sys
from pathlib import Path
import json

# Add the parent directory to the path so we can import the supabase_client
sys.path.append(str(Path(__file__).parent.parent))
from tools.supabase_client import SupabaseClient

def python_to_typescript_type(pg_type):
    """Convert PostgreSQL type to TypeScript type"""
    type_map = {
        'integer': 'number',
        'bigint': 'number',
        'smallint': 'number',
        'decimal': 'number',
        'numeric': 'number',
        'real': 'number',
        'double precision': 'number',
        'character varying': 'string',
        'character': 'string',
        'text': 'string',
        'varchar': 'string',
        'date': 'string', # or 'Date' if using Date objects
        'timestamp': 'string', # or 'Date' if using Date objects
        'timestamp with time zone': 'string', # or 'Date' if using Date objects
        'timestamp without time zone': 'string', # or 'Date' if using Date objects
        'boolean': 'boolean',
        'json': 'Record<string, any>',
        'jsonb': 'Record<string, any>',
        'uuid': 'string',
        'ARRAY': 'any[]', # Will be refined based on the array element type
        'USER-DEFINED': 'any', # Custom types will need manual attention
        'vector': 'number[]', # For pgvector
    }
    
    return type_map.get(pg_type, 'any')

def generate_typescript_interfaces(supabase_client, output_path='./types'):
    """
    Generate TypeScript interfaces from Supabase schema
    
    Args:
        supabase_client: SupabaseClient instance
        output_path: Directory to save the TypeScript files
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    try:
        # Get the list of tables
        tables = supabase_client.get_tables()
        
        # Create index.ts file to export all types
        index_exports = []
        
        # Process each table
        for table_name in tables:
            # Get the schema for this table
            schema = supabase_client.get_schema(table_name)
            
            # Start building the interface
            interface_name = ''.join(word.title() for word in table_name.split('_'))
            ts_interface = f"export interface {interface_name} {{\n"
            
            # Add each column as a property
            for column in schema:
                column_name = column['column_name']
                data_type = column['data_type']
                is_nullable = column['is_nullable'] == 'YES'
                
                ts_type = python_to_typescript_type(data_type)
                nullable_suffix = ' | null' if is_nullable else ''
                
                ts_interface += f"  {column_name}: {ts_type}{nullable_suffix};\n"
            
            # Close the interface
            ts_interface += "}\n"
            
            # Write the interface to a file
            file_path = os.path.join(output_path, f"{table_name}.ts")
            with open(file_path, 'w') as f:
                f.write(ts_interface)
            
            # Add to index exports
            index_exports.append(f"export * from './{table_name}';")
            
            print(f"Generated interface for table '{table_name}'")
        
        # Write the index.ts file
        with open(os.path.join(output_path, 'index.ts'), 'w') as f:
            f.write('\n'.join(index_exports))
        
        print(f"Generated {len(tables)} TypeScript interfaces in '{output_path}'")
        
    except Exception as e:
        print(f"Error generating TypeScript interfaces: {e}")
        return False
    
    return True

def generate_json_schema(supabase_client, output_path='./schema'):
    """
    Generate JSON Schema from Supabase database schema
    
    Args:
        supabase_client: SupabaseClient instance
        output_path: Directory to save the JSON Schema files
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    try:
        # Get the list of tables
        tables = supabase_client.get_tables()
        
        # Process each table
        schemas = {}
        for table_name in tables:
            # Get the schema for this table
            schema = supabase_client.get_schema(table_name)
            
            # Build JSON Schema object
            json_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "title": table_name,
                "properties": {},
                "required": []
            }
            
            # Add each column as a property
            for column in schema:
                column_name = column['column_name']
                data_type = column['data_type']
                is_nullable = column['is_nullable'] == 'YES'
                
                # Map PostgreSQL types to JSON Schema types
                if data_type in ('integer', 'bigint', 'smallint', 'decimal', 'numeric', 'real', 'double precision'):
                    prop_type = "number"
                elif data_type in ('character varying', 'character', 'text', 'varchar', 'uuid'):
                    prop_type = "string"
                elif data_type == 'boolean':
                    prop_type = "boolean"
                elif data_type in ('json', 'jsonb'):
                    prop_type = "object"
                elif data_type.startswith('timestamp') or data_type == 'date':
                    prop_type = "string"
                    # Could add format: "date-time" for ISO date strings
                elif data_type == 'ARRAY':
                    prop_type = "array"
                elif data_type == 'vector':
                    prop_type = "array"
                    # Add items type for vector
                    json_schema["properties"][column_name] = {
                        "type": prop_type,
                        "items": {"type": "number"}
                    }
                    continue
                else:
                    prop_type = "string"  # Default fallback
                
                # Add the property to the schema
                json_schema["properties"][column_name] = {"type": prop_type}
                
                # If not nullable, add to required list
                if not is_nullable:
                    json_schema["required"].append(column_name)
            
            # Add this schema to the collection
            schemas[table_name] = json_schema
            
            # Write individual schema file
            file_path = os.path.join(output_path, f"{table_name}.json")
            with open(file_path, 'w') as f:
                json.dump(json_schema, f, indent=2)
            
            print(f"Generated JSON Schema for table '{table_name}'")
        
        # Write a combined schema file
        combined_path = os.path.join(output_path, "all_tables.json")
        with open(combined_path, 'w') as f:
            json.dump(schemas, f, indent=2)
        
        print(f"Generated JSON Schema for {len(tables)} tables in '{output_path}'")
        
    except Exception as e:
        print(f"Error generating JSON Schema: {e}")
        return False
    
    return True

def generate_migration_sql(supabase_client, output_path='./migrations'):
    """
    Generate SQL migration files based on the current schema
    This is helpful for setting up new Supabase projects with the same schema
    
    Args:
        supabase_client: SupabaseClient instance
        output_path: Directory to save the SQL migration files
    """
    os.makedirs(output_path, exist_ok=True)
    
    try:
        # Get the list of tables
        tables = supabase_client.get_tables()
        
        # Create a timestamp for the migration
        timestamp = supabase_client.execute_sql("SELECT NOW()::timestamp::text")
        migration_timestamp = timestamp[0]['now'].split('.')[0].replace(':', '').replace(' ', '_')
        
        # Generate SQL for each table
        sql = f"-- Migration generated at {timestamp[0]['now']}\n\n"
        
        for table_name in tables:
            # Get the schema for this table
            columns = supabase_client.get_schema(table_name)
            
            # Get primary key information
            pk_query = f"""
            SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS data_type
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = '{table_name}'::regclass
            AND i.indisprimary;
            """
            primary_keys = supabase_client.execute_sql(pk_query)
            
            # Generate CREATE TABLE statement
            sql += f"-- Table: {table_name}\n"
            sql += f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            
            # Add columns
            column_sql = []
            for column in columns:
                column_name = column['column_name']
                data_type = column['data_type']
                is_nullable = "NULL" if column['is_nullable'] == 'YES' else "NOT NULL"
                
                # Check if this column is a primary key
                is_primary_key = any(pk['attname'] == column_name for pk in primary_keys)
                pk_suffix = " PRIMARY KEY" if is_primary_key else ""
                
                column_sql.append(f"    {column_name} {data_type} {is_nullable}{pk_suffix}")
            
            sql += ",\n".join(column_sql)
            sql += "\n);\n\n"
            
            # Add indexes (excluding primary key as it's already indexed)
            index_query = f"""
            SELECT
                i.relname AS index_name,
                a.attname AS column_name,
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
                AND NOT ix.indisprimary;
            """
            
            try:
                indexes = supabase_client.execute_sql(index_query)
                processed_indexes = {}
                
                for idx in indexes:
                    index_name = idx['index_name']
                    column_name = idx['column_name']
                    is_unique = idx['is_unique']
                    
                    if index_name not in processed_indexes:
                        processed_indexes[index_name] = {
                            'columns': [column_name],
                            'unique': is_unique
                        }
                    else:
                        processed_indexes[index_name]['columns'].append(column_name)
                
                for index_name, index_info in processed_indexes.items():
                    unique_str = "UNIQUE " if index_info['unique'] else ""
                    columns_str = ", ".join(index_info['columns'])
                    sql += f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_str});\n"
                
                sql += "\n"
            except Exception as e:
                print(f"Warning: Could not retrieve indexes for {table_name}: {e}")
        
        # Write the SQL to a file
        file_path = os.path.join(output_path, f"{migration_timestamp}_schema.sql")
        with open(file_path, 'w') as f:
            f.write(sql)
        
        print(f"Generated SQL migration file: {file_path}")
        
    except Exception as e:
        print(f"Error generating SQL migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate TypeScript types from Supabase schema')
    parser.add_argument('--format', choices=['typescript', 'json', 'sql', 'all'], default='all',
                        help='Output format: typescript, json, sql, or all')
    parser.add_argument('--output-dir', default='./generated',
                        help='Directory to save the generated files')
    
    args = parser.parse_args()
    
    # Create SupabaseClient
    supabase = SupabaseClient()
    
    # Generate files based on format
    if args.format in ('typescript', 'all'):
        ts_output = os.path.join(args.output_dir, 'types')
        generate_typescript_interfaces(supabase, ts_output)
    
    if args.format in ('json', 'all'):
        json_output = os.path.join(args.output_dir, 'schema')
        generate_json_schema(supabase, json_output)
    
    if args.format in ('sql', 'all'):
        sql_output = os.path.join(args.output_dir, 'migrations')
        generate_migration_sql(supabase, sql_output) 