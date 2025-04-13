"""
Script to backfill vector embeddings for existing conversations in Supabase
that are missing them.
"""
import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
import openai
from typing import List, Dict

# Add project root to sys.path to allow importing tools.supabase_client
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from tools.supabase_client import SupabaseClient

# Re-define the helper function here to avoid dependency on the task module
# --- Helper function for OpenAI Embedding ---
# Modified to accept transcript turns and concatenate
# Modified to return a tuple: (embedding_vector, was_truncated)
def get_embedding(turns: List[Dict[str, str]], client):
    was_truncated = False # Flag to track truncation
    if not client or not turns:
        logging.debug("Backfill: Skipping embedding generation - no client or turns provided.")
        return None, was_truncated

    # Concatenate transcript content
    full_transcript_text = " ".join([turn.get('text', '') for turn in turns if turn.get('text')])
    
    if not full_transcript_text.strip():
        logging.debug("Backfill: Skipping embedding generation - concatenated transcript is empty.")
        return None, was_truncated
        
    # Ensure text is not excessively long for the embedding model
    max_tokens = 8191 # text-embedding-3-small limit
    # Simple truncation heuristic (can be improved with tiktoken)
    max_chars = max_tokens * 4 # Estimate max bytes
    text_to_embed = full_transcript_text
    if len(full_transcript_text.encode('utf-8')) > max_chars:
        # Truncate based on bytes, then decode safely
        truncated_bytes = full_transcript_text.encode('utf-8')[:max_chars]
        text_to_embed = truncated_bytes.decode('utf-8', errors='ignore')
        logging.warning(f"Backfill: Truncated transcript text before embedding due to length ({len(full_transcript_text)} chars -> {len(text_to_embed)} chars).")
        was_truncated = True # Set flag

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text_to_embed
        )
        if response.data and len(response.data) > 0:
            logging.debug(f"Backfill: Successfully generated embedding for transcript snippet '{text_to_embed[:100]}...'.")
            return response.data[0].embedding, was_truncated # Return vector and flag
        else:
            logging.error("Backfill: OpenAI embedding response format unexpected or empty.")
            return None, was_truncated
    except Exception as e:
        logging.error(f"Backfill: Failed to get embedding from OpenAI for transcript snippet '{text_to_embed[:100]}...': {e}", exc_info=True)
        return None, was_truncated # Return None and flag on error
# --- End Helper Function ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
BATCH_SIZE = 100  # Number of conversations to process per batch
RATE_LIMIT_DELAY = 0.1 # Optional delay in seconds between OpenAI calls
# --- End Configuration ---

def backfill():
    logging.info("Starting backfill embeddings script...")
    # Load .env file from project root
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loading .env file from: {dotenv_path}")


    # --- Initialize Clients ---
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not supabase_url or not supabase_key:
        logging.error("Supabase URL or Service Key not found in .env file. Exiting.")
        sys.exit(1)
    if not openai_api_key:
        logging.error("OPENAI_API_KEY not found in .env file. Exiting.")
        sys.exit(1)

    logging.info(f"Supabase URL: {supabase_url[:20]}...") # Avoid logging full URL/key
    logging.info("Supabase Key: Present")
    logging.info("OpenAI Key: Present")


    try:
        supabase = SupabaseClient(supabase_url, supabase_key)
        logging.info("Supabase client initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
        sys.exit(1)

    try:
        openai_client = openai.OpenAI(api_key=openai_api_key)
        logging.info("OpenAI client initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        sys.exit(1)
    # --- End Client Initialization ---

    processed_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    truncated_count = 0 # ADDED: Counter for truncated embeddings
    offset = 0

    while True:
        logging.info(f"Fetching ALL conversations batch (size {BATCH_SIZE}) with messages, starting from offset {offset}...")
        try:
            # Fetch conversations needing embeddings
            # *Also fetch messages for these conversations*
            # MODIFIED: Fetch ALL conversations with messages, not just those with NULL embeddings
            response = (
                supabase.client.table('conversations')
                # Select needed fields, including messages FK to filter
                .select('id, external_id, summary, messages!inner(text, speaker)') 
                # REMOVED: .is_('embedding', 'NULL') 
                # Filter implicitly by requiring messages via !inner
                .order('id') # Order for consistent pagination
                .range(offset, offset + BATCH_SIZE - 1)
                .execute()
            )

            if not response.data:
                logging.info("No more conversations found to process.") # Updated message
                break

            conversations_batch = response.data
            logging.info(f"Processing batch of {len(conversations_batch)} conversations.")

            for conv in conversations_batch:
                processed_count += 1
                conv_id = conv.get('id')
                external_id = conv.get('external_id')
                # messages are guaranteed by the '!inner' join
                messages = conv.get('messages', []) 
                
                # --- Embed based on MESSAGES (transcript) --- 
                # No need for the 'if not messages' check anymore due to the query filter
                
                logging.info(f"Generating transcript embedding for conv_id {conv_id} (external: {external_id}) using {len(messages)} messages...")
                # Pass the messages list to the modified get_embedding function
                embedding_vector, truncated_flag = get_embedding(messages, openai_client) 
                if truncated_flag:
                    truncated_count += 1 # Increment counter
                # --- End Embedding --- 

                if embedding_vector:
                    try:
                        # Update record, overwriting existing embedding if present
                        logging.info(f"Updating embedding for conv_id {conv_id}...")
                        update_response = supabase.client.table('conversations')\
                            .update({'embedding': embedding_vector})\
                            .eq('id', conv_id)\
                            .execute()

                        # Check for errors in update_response if needed, Supabase client might raise exceptions
                        # Check response.data or response.error if applicable for your supabase-py version
                        # Example check (adjust based on actual response structure):
                        # if hasattr(update_response, 'error') and update_response.error:
                        #     raise Exception(f"Supabase update error: {update_response.error}")
                        
                        logging.info(f"Successfully updated embedding for conv_id {conv_id}.")
                        updated_count += 1

                    except Exception as update_error:
                        logging.error(f"Failed to update embedding for conv_id {conv_id}: {update_error}")
                        failed_count += 1
                else:
                    logging.warning(f"Failed to generate transcript embedding for conv_id {conv_id}. Skipping update.")
                    failed_count += 1 # Count as failed if embedding generation fails

                # Optional delay to avoid hitting rate limits
                if RATE_LIMIT_DELAY > 0:
                    time.sleep(RATE_LIMIT_DELAY)

            # Check if we processed less than the batch size, indicating the end
            if len(conversations_batch) < BATCH_SIZE:
                logging.info("Processed the last batch.")
                break
            
            # Move to the next batch
            offset += BATCH_SIZE

        except Exception as fetch_error:
            logging.error(f"Error fetching or processing batch starting at offset {offset}: {fetch_error}")
            # Decide whether to retry, skip batch, or abort
            logging.warning("Aborting script due to fetch/processing error.")
            break # Abort on error for now

    logging.info("--- Backfill Summary ---")
    logging.info(f"Total conversations checked: {processed_count}")
    logging.info(f"Successfully updated: {updated_count}")
    logging.info(f"Skipped (missing messages): {skipped_count}") # Updated reason
    logging.info(f"Failed (embedding/update): {failed_count}")
    logging.info(f"Truncated Embeddings: {truncated_count}") # Added truncated count
    logging.info("Backfill script finished.")

if __name__ == "__main__":
    backfill()