import os
import sys
import psycopg2
from dotenv import load_dotenv

print("Attempting to load .env file...")
if load_dotenv():
    print(".env file loaded successfully.")
else:
    print("Warning: .env file not found or failed to load.")

db_url = os.environ.get('DATABASE_URL')

if not db_url:
    print("ERROR: DATABASE_URL environment variable not found.")
    sys.exit(1)

print(f"Found DATABASE_URL: {db_url[:25]}...") # Print prefix for confirmation

try:
    print("Attempting to connect to the database...")
    conn = psycopg2.connect(db_url)
    print("SUCCESS: Database connection established successfully!")
    conn.close()
    print("Connection closed.")
    sys.exit(0) # Exit with success code
except psycopg2.OperationalError as e:
    print("\nERROR: Failed to connect to the database.")
    print("Potential causes:")
    print("- Incorrect DATABASE_URL (hostname, port, user, password, dbname).")
    print("- Database server is not running or reachable.")
    print("- Network restrictions/firewall blocking the connection.")
    print("- Missing SSL configuration (if required by server).")
    print(f"\nDetails: {e}")
    sys.exit(1) # Exit with failure code
except Exception as e:
    print(f"\nUNEXPECTED ERROR: An unexpected error occurred: {e}")
    sys.exit(1) # Exit with failure code 