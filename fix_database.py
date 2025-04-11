import os
import sys
import logging
from flask import Flask
from sqlalchemy import text, inspect
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path to allow running directly
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

def create_diagnostic_app():
    """Create a minimal Flask app for database diagnostics"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Import db from extensions to ensure it's the same one used by the app
    from app.extensions import db
    db.init_app(app)
    
    return app, db

def inspect_database(app, db):
    """Inspect the database structure"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check if conversations table exists
        if 'conversations' not in inspector.get_table_names():
            logger.error("Conversations table does not exist in the database")
            return False
            
        # Check external_id column
        columns = inspector.get_columns('conversations')
        external_id_col = next((c for c in columns if c['name'] == 'external_id'), None)
        
        if not external_id_col:
            logger.error("external_id column not found in conversations table")
            return False
            
        logger.info(f"external_id column found with type: {external_id_col['type']}")
        
        # Execute SQL to get more detailed type info
        try:
            result = db.session.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'conversations' AND column_name = 'external_id'"
            ))
            data_type = result.scalar()
            logger.info(f"Information schema reports external_id type as: {data_type}")
            
            # Check if we need to fix the type
            if data_type and 'int' in data_type.lower():
                return 'fix_needed'
                
            return 'ok'
        except Exception as e:
            logger.error(f"Error querying information schema: {e}")
            return 'error'

def fix_column_type(app, db):
    """Fix the external_id column type if needed"""
    with app.app_context():
        try:
            logger.info("Attempting to fix external_id column type...")
            db.session.execute(text('ALTER TABLE conversations ALTER COLUMN external_id TYPE VARCHAR;'))
            db.session.commit()
            logger.info("Column type updated successfully")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update column type: {e}")
            return False

def main():
    """Main function to diagnose and fix database issues"""
    logger.info("Starting database diagnostic")
    
    app, db = create_diagnostic_app()
    
    # First inspect the database
    status = inspect_database(app, db)
    
    if status == 'fix_needed':
        logger.info("Database needs fixing - external_id column is not VARCHAR")
        if fix_column_type(app, db):
            logger.info("Database fix applied successfully")
            
            # Verify the fix
            new_status = inspect_database(app, db)
            if new_status == 'ok':
                logger.info("Verification successful - database schema is now correct")
            else:
                logger.error("Verification failed - database schema is still incorrect")
                
    elif status == 'ok':
        logger.info("Database schema is already correct - no fix needed")
    else:
        logger.error("Couldn't determine database status or there was an error")
        
    logger.info("Database diagnostic complete")

if __name__ == "__main__":
    main() 