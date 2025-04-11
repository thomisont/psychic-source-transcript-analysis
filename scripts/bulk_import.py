import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from dateutil import parser # Import parser for flexible date handling

# Ensure the app directory is in the Python path for model imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Import models and ElevenLabs client relative to the project root
from app.models import Conversation, Message
from app.api.elevenlabs_client import ElevenLabsClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Ensure logs go to stdout
    ]
)
logger = logging.getLogger(__name__)

# Set specific logger level to DEBUG if basicConfig doesn't override existing loggers
logger.setLevel(logging.DEBUG)

def setup_database_session():
    """Sets up the database connection and returns a session."""
    logger.info("Setting up database session...")
    load_dotenv(os.path.join(project_root, '.env')) # Ensure .env is loaded from project root
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not found.")
        sys.exit(1)
    
    try:
        # Use the direct connection string
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database engine and session created successfully.")
        # Test connection explicitly
        with engine.connect() as connection:
            logger.info("Successfully connected to the database.")
        return SessionLocal()
    except Exception as e:
        logger.error(f"Failed to create database engine, session, or connect: {e}", exc_info=True)
        sys.exit(1)

def get_elevenlabs_client():
    """Initializes and returns the ElevenLabs client."""
    logger.info("Initializing ElevenLabs client...")
    load_dotenv(os.path.join(project_root, '.env')) # Ensure .env is loaded from project root
    api_key = os.environ.get('ELEVENLABS_API_KEY')
    agent_id = os.environ.get('ELEVENLABS_AGENT_ID') # Optional, client might handle its absence
    
    if not api_key:
        logger.error("ELEVENLABS_API_KEY not found in .env file.")
        sys.exit(1)
    if not agent_id:
        logger.warning("ELEVENLABS_AGENT_ID not found in .env file, proceeding without it.")

    try:
        # Pass agent_id=None if not found, client constructor handles default
        client = ElevenLabsClient(api_key=api_key, agent_id=agent_id if agent_id else None)
        logger.info("ElevenLabs client initialized successfully.")
        # Optional: Add a connection test if the client has one
        # if hasattr(client, 'test_connection') and not client.test_connection():
        #     logger.error("ElevenLabs client connection test failed.")
        #     sys.exit(1)
        return client
    except Exception as e:
        logger.error(f"Failed to initialize ElevenLabs client: {e}", exc_info=True)
        sys.exit(1)

def fetch_existing_external_ids(db_session):
    """Fetches all existing external_ids from the conversations table."""
    logger.info("Fetching existing external conversation IDs from database...")
    try:
        result = db_session.execute(select(Conversation.external_id))
        existing_ids = {row[0] for row in result.scalars()}
        logger.info(f"Found {len(existing_ids)} existing external IDs.")
        return existing_ids
    except Exception as e:
        logger.error(f"Failed to fetch existing external IDs: {e}", exc_info=True)
        # Exit if we cannot verify existing IDs to prevent duplicates
        logger.error("Exiting due to failure fetching existing IDs.")
        sys.exit(1)

def parse_timestamp(timestamp_data):
    """Safely parses timestamp data which might be int, string, or already datetime."""
    if timestamp_data is None:
        return None
    
    # +++ Handle if it's already a datetime object +++
    if isinstance(timestamp_data, datetime):
        # Ensure it's timezone-aware (UTC) for consistency, if not already
        if timestamp_data.tzinfo is None:
            return timestamp_data.replace(tzinfo=timezone.utc) 
        else:
            return timestamp_data # Return as is if already timezone-aware

    try:
        # If it's numeric (likely Unix timestamp)
        if isinstance(timestamp_data, (int, float)):
            # Check magnitude: if it's very small, it might be seconds, else milliseconds
            if timestamp_data > 1e11: # Heuristic for milliseconds
                 return datetime.fromtimestamp(timestamp_data / 1000)
            else: # Assume seconds
                 return datetime.fromtimestamp(timestamp_data)
        # If it's a string, use dateutil.parser
        elif isinstance(timestamp_data, str):
            return parser.parse(timestamp_data)
        else:
            logger.warning(f"Unparseable timestamp type: {type(timestamp_data)}, value: {timestamp_data}")
            return None
    except (ValueError, TypeError, parser.ParserError) as e:
        logger.warning(f"Could not parse timestamp '{timestamp_data}': {e}")
        return None

def import_conversations():
    """Main function to orchestrate the bulk import."""
    logger.info("Starting bulk import process...")
    
    db_session = setup_database_session()
    elevenlabs_client = get_elevenlabs_client()
    existing_external_ids = fetch_existing_external_ids(db_session)
    
    conversations_to_import = []
    logger.info("Fetching conversations list from ElevenLabs...")
    try:
        # Fetch initial list - use a large limit. Adjust date range as needed.
        # Client handles pagination internally up to its max_pages limit.
        # If more needed, client/this logic needs adjustment.
        fetched_data = elevenlabs_client.get_conversations(
            start_date='2020-01-01', # Fetch all history
            limit=2000 # Request a large number
        )
        # The client adapts various response structures. Let's assume 'conversations' key.
        conversations_to_import = fetched_data.get('conversations', [])
        logger.info(f"Fetched {len(conversations_to_import)} conversation metadata entries from ElevenLabs.")
        if not conversations_to_import:
             logger.warning("No conversations found from ElevenLabs API call.")

    except Exception as e:
        logger.error(f"Failed to fetch conversations list from ElevenLabs: {e}", exc_info=True)
        db_session.close()
        sys.exit(1)

    new_conversations_count = 0
    processed_count = 0
    skipped_count = 0
    error_count = 0

    # --- Restore Original Loop --- 
    logger.info(f"Processing {len(conversations_to_import)} potential conversations...")
    for i, conv_summary in enumerate(conversations_to_import):
        processed_count += 1
        # Assume the client normalization provides a consistent 'id' field
        external_id = conv_summary.get('id') or conv_summary.get('conversation_id')

        if not external_id:
            logger.warning(f"Skipping entry {i+1} due to missing external ID: {conv_summary}")
            skipped_count += 1
            continue
            
        if external_id in existing_external_ids:
            # logger.debug(f"Skipping already existing conversation: {external_id}")
            skipped_count += 1
            continue

        logger.info(f"Processing new conversation {external_id} ({i+1}/{len(conversations_to_import)})...")

        try:
            # Fetch full details including transcript
            conv_details = elevenlabs_client.get_conversation_details(external_id)
            
            if not conv_details:
                 logger.warning(f"Failed to fetch details for {external_id}. Skipping.")
                 skipped_count += 1
                 continue

            title = conv_details.get('title') or conv_summary.get('title') or f'Conversation {external_id}'
            created_at = parse_timestamp(conv_details.get('created_at_unix') or conv_summary.get('start_time_unix'))
            
            logger.debug(f"Creating Conversation object for {external_id}")
            new_conversation = Conversation(
                external_id=external_id,
                title=title,
                created_at=created_at # Use parsed or None
            )
            db_session.add(new_conversation) # Add conversation first

            # +++ Log the keys returned by the client +++
            logger.debug(f"Keys in conv_details from client: {list(conv_details.keys())}")
            
            message_source_key = None
            if 'turns' in conv_details:
                message_list = conv_details.get('turns', [])
                message_source_key = 'turns'
            elif 'transcript' in conv_details:
                 message_list = conv_details.get('transcript', [])
                 message_source_key = 'transcript'
            elif 'messages' in conv_details:
                 message_list = conv_details.get('messages', [])
                 message_source_key = 'messages'
            else:
                message_list = []
                message_source_key = 'None'
                
            # +++ Log the source key used +++
            logger.debug(f"Using key '{message_source_key}' for message list.")

            logger.debug(f"Found {len(message_list)} potential messages for {external_id}")
            if not message_list:
                logger.warning(f"Message list is empty for {external_id}.")

            messages_added_this_conv = [] # Keep track of messages for this conversation
            for msg_index, msg_data in enumerate(message_list):
                # +++ Log the entire message data dictionary +++
                logger.debug(f"Processing msg_data: {msg_data}") 
                
                speaker = msg_data.get('speaker') or msg_data.get('role')
                text = msg_data.get('text') or msg_data.get('content') or msg_data.get('message')
                raw_timestamp = msg_data.get('timestamp') or msg_data.get('time')
                logger.debug(f"Raw timestamp for msg {msg_index} in conv {external_id}: {raw_timestamp} (Type: {type(raw_timestamp)})")
                timestamp = parse_timestamp(raw_timestamp)
                logger.debug(f"Parsed timestamp for msg {msg_index} in conv {external_id}: {timestamp} (Type: {type(timestamp)})")
                
                if not text:
                    logger.warning(f"Skipping message {msg_index} in {external_id} due to missing text/content/message. Data received: {msg_data}")
                    continue

                try:
                    message = Message(
                        speaker=speaker,
                        text=text,
                        timestamp=timestamp
                    )
                    # Explicitly link message to conversation
                    message.conversation = new_conversation 
                    # Explicitly add the message object
                    db_session.add(message)
                    messages_added_this_conv.append(message) # Add to list for logging
                except Exception as msg_create_err:
                    logger.error(f"Failed to create/add Message object {msg_index} for {external_id}. Data: {msg_data}, Error: {msg_create_err}", exc_info=True)
                    continue

            new_conversations_count += 1 # Increment count only if processing didn't error out before commit attempt

            # --- Restore Batching --- 
            if new_conversations_count % 50 == 0: # Use batch_size variable if defined earlier, or hardcode
                 logger.info(f"Committing batch of conversations (Total added so far: {new_conversations_count})...")
                 try:
                     db_session.commit()
                     logger.info("Batch committed successfully.")
                 except Exception as e_commit:
                     logger.error(f"Failed to commit batch ending around conversation {external_id}: {e_commit}", exc_info=True)
                     db_session.rollback()
                     logger.info("Rolled back current batch. Trying to continue...")
                     # Adjust counts? Maybe just log error count
                     error_count += 50 # Approximate error count for batch
            # --- End Restore Batching --- 

        except Exception as e_detail:
            logger.error(f"Failed processing conversation {external_id}: {e_detail}", exc_info=True)
            db_session.rollback() # Rollback this specific conversation
            error_count += 1
            continue # Continue processing other conversations
    # --- End Original Loop --- 

    # --- Final Commit for any remaining items --- 
    try:
        logger.info("Committing final batch...")
        db_session.commit()
        logger.info("Final batch committed successfully.")
    except Exception as e_final:
        logger.error(f"Failed to commit final batch: {e_final}", exc_info=True)
        db_session.rollback()
        error_count += 1 # Add to error count
        logger.error("Final batch commit failed.")
    # --- End Final Commit --- 

    logger.info(f"--- Bulk Import Summary ---")
    logger.info(f"Total conversations processed: {processed_count}")
    logger.info(f"Total conversations skipped: {skipped_count}")
    logger.info(f"Total conversations imported: {new_conversations_count}")
    logger.info(f"Total errors encountered: {error_count}")

    # --- Final Check: Query message count --- 
    try:
        # Remove code referencing TARGET_EXTERNAL_ID
        # target_conv = db_session.query(Conversation).filter(Conversation.external_id == TARGET_EXTERNAL_ID).first()
        # if target_conv:
        #     final_message_count = db_session.query(func.count(Message.id)).filter(Message.conversation_id == target_conv.id).scalar() or 0
        #     logger.info(f"FINAL CHECK: Found {final_message_count} messages in the database for conversation {TARGET_EXTERNAL_ID} (DB ID: {target_conv.id}).")
        # else:
        #     logger.info(f"FINAL CHECK: Conversation {TARGET_EXTERNAL_ID} not found in DB for final check.")
        
        # Correctly query the total count
        final_message_count = db_session.query(func.count(Message.id)).scalar() or 0
        logger.info(f"FINAL CHECK: Found {final_message_count} total messages in the messages table.")

    except Exception as final_check_err:
        logger.error(f"FINAL CHECK failed: Could not query message count: {final_check_err}")

    db_session.close()
    logger.info("Database session closed.")

if __name__ == "__main__":
    import_conversations() 