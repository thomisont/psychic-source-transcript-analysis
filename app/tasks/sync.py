"""
Task for synchronizing conversations from ElevenLabs API to the database.
"""
# ==============================================================================
# == WARNING: CRITICAL SYNC LOGIC ==
# ==============================================================================
# This task handles the core data synchronization between ElevenLabs and the 
# Supabase database. It has been carefully optimized for efficiency and 
# reliability.
# 
# !! DO NOT MODIFY THIS FILE without explicit request and careful review !!
# 
# Changes can impact data integrity, API usage costs, and sync performance.
# Discuss any required changes thoroughly before implementation.
# ==============================================================================

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy import desc, func, cast, Text
from dateutil import parser
from postgrest import APIResponse # Add this import if not already present

# Import necessary components (use absolute imports)
from app.extensions import db
from app.models import Conversation, Message
from app.api.elevenlabs_client import ElevenLabsClient # We need the client directly here

# Import SupabaseClient (add path to ensure it's available)
sys.path.append(str(Path(__file__).parent.parent.parent))
from tools.supabase_client import SupabaseClient

def sync_new_conversations(app, full_sync=False):
    """
    Fetches recent conversations from ElevenLabs and adds any new ones 
    or updates existing ones missing summaries to the database. 
    Requires app context.
    Optimized to reduce API detail calls.
    """
    with app.app_context():
        logging.info(f"Starting conversation sync task... (Full Sync: {full_sync})")
        initial_count = 0
        final_count = 0
        conversations_added_count = 0
        conversations_updated_count = 0
        conversations_skipped_count = 0
        conversations_failed_count = 0
        conversations_checked_api_count = 0 # How many summaries we got from API

        try:
            # Initialize Supabase client
            supabase_url = app.config.get('SUPABASE_URL')
            supabase_key = app.config.get('SUPABASE_SERVICE_KEY')
            if not supabase_url or not supabase_key:
                 raise ValueError("Supabase URL or Service Key not found in app configuration for sync task.")
            supabase = SupabaseClient(supabase_url, supabase_key)
            logging.info("Initialized Supabase client for sync task")
            
            client: ElevenLabsClient = app.elevenlabs_client
            if not client or not client.api_key or not client.agent_id:
                logging.error("Sync Task: ElevenLabs client is not properly configured. Aborting.")
                return {"status": "error", "message": "Client not configured"}, 500

            # === 1. Get Initial Count & Existing IDs/Summary Status from Supabase ===
            existing_conversations_dict = {}
            try:
                # Get initial count
                count_query = "SELECT COUNT(*) as count FROM conversations"
                count_result = supabase.execute_sql(count_query)
                initial_count = count_result[0]['count'] if count_result else 0
                logging.info(f"Sync Task: Initial conversation count in DB: {initial_count}")

                # Fetch all existing external_ids and check if summary is NULL
                # Fetch in chunks if necessary for very large tables, but start simple
                existing_query = "SELECT external_id, (summary IS NOT NULL) as has_summary FROM conversations"
                existing_results = supabase.execute_sql(existing_query)
                if existing_results:
                    for row in existing_results:
                        existing_conversations_dict[row['external_id']] = row['has_summary']
                logging.info(f"Sync Task: Fetched status for {len(existing_conversations_dict)} existing conversations from DB.")
            except Exception as db_fetch_err:
                 logging.error(f"Sync Task: Failed to fetch initial data from Supabase: {db_fetch_err}. Aborting.")
                 # Consider fallback to SQLAlchemy if needed, but abort for now
                 return {"status": "error", "message": "Failed to query existing data"}, 500

            # === 2. Determine Sync Start Time (for API call) ===
            sync_start_time = None
            sync_start_timestamp_unix = None
            if full_sync:
                logging.warning("Sync Task: Performing FULL sync. Fetching all conversations from API.")
                sync_start_timestamp_unix = None # Fetch all
            else:
                logging.info("Sync Task: Performing incremental sync. Finding latest message timestamp...")
                try:
                    latest_msg_query = "SELECT MAX(timestamp) as latest_timestamp FROM messages"
                    latest_msg_result = supabase.execute_sql(latest_msg_query)
                    latest_message_timestamp = None
                    if latest_msg_result and latest_msg_result[0]['latest_timestamp']:
                        latest_message_timestamp = latest_msg_result[0]['latest_timestamp']
                        if isinstance(latest_message_timestamp, str):
                            latest_message_timestamp = datetime.fromisoformat(latest_message_timestamp.replace('Z', '+00:00'))
                    
                    if latest_message_timestamp:
                        if latest_message_timestamp.tzinfo is None:
                            latest_message_timestamp = latest_message_timestamp.replace(tzinfo=timezone.utc)
                        sync_start_time = latest_message_timestamp - timedelta(minutes=5) # Widen buffer slightly
                        sync_start_timestamp_unix = int(sync_start_time.timestamp())
                        logging.info(f"Sync Task: Found latest message timestamp: {latest_message_timestamp}. Fetching API since {sync_start_time} (Unix: {sync_start_timestamp_unix}).")
                    else:
                        sync_start_time = datetime.now(timezone.utc) - timedelta(days=7)
                        sync_start_timestamp_unix = int(sync_start_time.timestamp())
                        logging.warning(f"Sync Task: No existing messages found. Fetching API since {sync_start_time} (Unix: {sync_start_timestamp_unix}).")
                except Exception as e:
                    logging.error(f"Sync Task: Error getting latest timestamp: {e}. Defaulting to fetching last 7 days.")
                    sync_start_time = datetime.now(timezone.utc) - timedelta(days=7)
                    sync_start_timestamp_unix = int(sync_start_time.timestamp())

            # === 3. Fetch Conversation Summaries from ElevenLabs API ===
            conversations_list = []
            try:
                logging.info(f"Sync Task: Calling client.get_conversations(from_time={sync_start_timestamp_unix})...")
                api_response = client.get_conversations(from_time=sync_start_timestamp_unix, limit=2000) 
                conversations_list = api_response.get('conversations', [])
                conversations_checked_api_count = len(conversations_list)
                logging.info(f"Sync Task: Received {conversations_checked_api_count} conversation summaries from API.")
            except Exception as fetch_error:
                logging.error(f"Sync Task: Error calling client.get_conversations: {fetch_error}", exc_info=True)
                # Allow task to continue, but report 0 checked API count
                conversations_checked_api_count = 0

            # === 4. Process Fetched Summaries ===
            if not conversations_list:
                logging.info(f"Sync Task: No new conversation summaries returned by API to process.")
            else:
                for conv_summary in conversations_list:
                    external_id = conv_summary.get('conversation_id') or conv_summary.get('id') # Use adapted ID
                    if not external_id:
                        logging.warning("Sync Task: Skipping conversation summary with missing ID.")
                        conversations_failed_count += 1
                        continue

                    # Determine if new or existing, and if update is needed
                    is_new = external_id not in existing_conversations_dict
                    # Need update if: new OR (existing AND (summary missing OR full_sync))
                    needs_detail_fetch = is_new or (not is_new and (not existing_conversations_dict[external_id] or full_sync))

                    if not needs_detail_fetch:
                        logging.debug(f"Sync Task: Skipping detail fetch for existing conversation {external_id} (summary present, not full sync).")
                        conversations_skipped_count += 1
                        continue
                    
                    # --- Fetch Details & Perform DB Operation --- 
                    logging.info(f"Sync Task: Fetching details for {external_id} for {'insert' if is_new else 'update'}.")
                    try:
                        conv_details_raw = client.get_conversation_details(external_id)
                        if not conv_details_raw or conv_details_raw.get('error'):
                            logging.warning(f"Sync Task: get_conversation_details failed or returned error for {external_id}. Details: {conv_details_raw}. Skipping.")
                            conversations_failed_count += 1
                            continue

                        adapted_data = client._adapt_conversation_details(conv_details_raw)
                        if not adapted_data:
                            logging.error(f"Sync Task: Failed to adapt conversation details for {external_id}. Raw: {str(conv_details_raw)[:200]}. Skipping.")
                            conversations_failed_count += 1
                            continue

                        # Extract data needed for DB (cost, status, summary, timestamp, title)
                        cost_value = adapted_data.get('cost')
                        cost_value_int = None
                        if cost_value is not None: 
                            try: 
                                cost_value_int = int(cost_value) 
                            except (ValueError, TypeError): 
                                logging.warning(f"Sync Task: Could not convert cost '{cost_value}' to int for {external_id}")
                        
                        conv_status = str(adapted_data.get('status', 'unknown')).lower()
                        conv_summary_str = str(summary) if (summary := adapted_data.get('summary')) is not None else None
                        
                        # --- Perform Insert or Update (Simplified logic here, reuse existing DB blocks below) ---
                        logging.info(f"Sync Task: Pre-Op Check for {external_id}. Op: {'Insert' if is_new else 'Update'}")
                        if is_new:
                            # --- INSERT LOGIC (Remove ORM Fallback) ---
                            try:
                                # Get start_time, default to None if missing/empty
                                created_at_val = adapted_data.get('start_time')
                                created_at_iso = None
                                if isinstance(created_at_val, datetime):
                                    created_at_iso = created_at_val.isoformat()
                                elif created_at_val: 
                                    try:
                                        dt_obj = parser.parse(str(created_at_val))
                                        if dt_obj.tzinfo is None: dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                                        created_at_iso = dt_obj.isoformat()
                                    except Exception as date_parse_err:
                                        logging.warning(f"Could not parse created_at '{created_at_val}' for {external_id}. Error: {date_parse_err}")
                                
                                if created_at_iso is None:
                                    logging.warning(f"Setting created_at to current time for {external_id} due to parsing failure or missing source data.")
                                    created_at_iso = datetime.now(timezone.utc).isoformat()
                                
                                # Insert Conversation directly 
                                conv_data = {
                                    'external_id': external_id,
                                    'title': adapted_data.get('title', f"Conversation {external_id[:8]}"),
                                    'created_at': created_at_iso, 
                                    'status': conv_status,
                                    'cost_credits': cost_value_int,
                                    'summary': conv_summary_str
                                }
                                conv_result = supabase.insert('conversations', conv_data)
                                if not conv_result: 
                                    raise Exception(f"Supabase insert conversation failed for {external_id}, no result returned.")
                                conv_id = conv_result[0]['id']
                                logging.info(f"Inserted conversation {external_id} into Supabase with ID {conv_id}")
                                
                                # Insert Messages
                                messages_added = 0
                                for turn in adapted_data.get('turns', []):
                                    msg_timestamp = turn.get('timestamp')
                                    timestamp_str = None
                                    if isinstance(msg_timestamp, datetime):
                                        if msg_timestamp.tzinfo is None: msg_timestamp = msg_timestamp.replace(tzinfo=timezone.utc)
                                        timestamp_str = msg_timestamp.isoformat()
                                    elif msg_timestamp:
                                         try:
                                             parsed_ts = parser.parse(str(msg_timestamp))
                                             if parsed_ts.tzinfo is None: parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
                                             timestamp_str = parsed_ts.isoformat()
                                         except Exception: 
                                             logging.warning(f"Could not parse turn timestamp {msg_timestamp} for {external_id}")
                                             timestamp_str = datetime.now(timezone.utc).isoformat() # Fallback
                                    else:
                                        timestamp_str = datetime.now(timezone.utc).isoformat() # Fallback if None

                                    # --- Fix: Handle None text --- 
                                    msg_text = turn.get('text')
                                    if msg_text is None:
                                        logging.warning(f"Message text is None for turn in {external_id}. Setting to empty string.")
                                        msg_text = '' # Use empty string to satisfy NOT NULL constraint
                                    # --- End Fix ---
                                        
                                    msg_data = {
                                        'conversation_id': conv_id,
                                        'speaker': turn.get('speaker'),
                                        'text': msg_text, # Use potentially modified text
                                        'timestamp': timestamp_str,
                                        'created_at': datetime.now(timezone.utc).isoformat(),
                                        'updated_at': datetime.now(timezone.utc).isoformat()
                                    }
                                    msg_insert_result = supabase.insert('messages', msg_data)
                                    # Add check if message insert failed
                                    if not msg_insert_result:
                                        logging.error(f"Failed to insert message for conversation {external_id}. Data: {msg_data}")
                                        # Optionally raise an exception here if one failed message should abort the whole conversation insert?
                                        # For now, just log and continue adding other messages.
                                    else:    
                                        messages_added += 1
                                        
                                logging.info(f"Sync Task: Added {messages_added} messages for new conv {external_id}.")
                                conversations_added_count += 1
                                
                            # Catch ONLY Supabase errors related to this insert block
                            except Exception as supabase_insert_error:
                                logging.error(f"Sync Task: Error during Supabase insert operation for new conv {external_id}: {supabase_insert_error}", exc_info=True)
                                conversations_failed_count += 1 # Increment failure count for this conversation
                                # DO NOT FALLBACK TO ORM
                            # --- END INSERT LOGIC ---
                        else: # It's an update
                            # --- UPDATE LOGIC (Remove ORM Fallback) ---
                             logging.info(f"Sync Task: Updating fields for existing conversation {external_id}.")
                             try:
                                 update_data = {
                                     'cost_credits': cost_value_int,
                                     'status': conv_status,
                                     'summary': conv_summary_str
                                     # Add other fields if they can change and should be updated
                                 }
                                 response: APIResponse = supabase.client.table('conversations') \
                                                     .update(update_data) \
                                                     .eq('external_id', external_id) \
                                                     .execute()
                                 
                                 # Check if update was successful (response.data might be empty if no change needed)
                                 # Rely on absence of exception as success indicator for updates
                                 logging.info(f"Supabase update executed for {external_id}.")
                                 # We only increment if an actual API call for details was made for the update
                                 conversations_updated_count += 1 
                                 
                             # Catch ONLY Supabase errors related to this update block
                             except Exception as supabase_update_error:
                                 logging.error(f"Sync Task: Error during Supabase update operation for {external_id}: {supabase_update_error}", exc_info=True)
                                 conversations_failed_count += 1 # Increment failure count for this conversation
                                 # DO NOT FALLBACK TO ORM
                            # --- END UPDATE LOGIC ---

                    except Exception as detail_error:
                        logging.error(f"Sync Task: Error processing details/DB op for {external_id}: {detail_error}", exc_info=True)
                        db.session.rollback() # Rollback potential ORM changes
                        conversations_failed_count += 1
                        continue # Skip to next summary
            
            # === 5. Get Final Count ===
            try:
                count_query = "SELECT COUNT(*) as count FROM conversations"
                count_result = supabase.execute_sql(count_query)
                final_count = count_result[0]['count'] if count_result else initial_count # Fallback to initial if query fails
            except Exception as final_count_err:
                 logging.error(f"Sync Task: Failed to get final count: {final_count_err}")
                 final_count = initial_count # Use initial as best guess

            # === 6. Log Summary & Return ===
            logging.info(f"Sync Task Finished. API Checked: {conversations_checked_api_count}, DB Initial: {initial_count}, Added: {conversations_added_count}, Updated: {conversations_updated_count}, Skipped: {conversations_skipped_count}, Failed: {conversations_failed_count}, DB Final: {final_count}.")
            return {
                "status": "success", 
                "checked_api": conversations_checked_api_count,
                "initial_db_count": initial_count,
                "added": conversations_added_count, 
                "updated": conversations_updated_count, 
                "skipped": conversations_skipped_count,
                "failed": conversations_failed_count,
                "final_db_count": final_count
            }, 200

        except Exception as e: 
            logging.error(f"Sync Task Failed Unexpectedly: {e}", exc_info=True)
            db.session.rollback() 
            # Try to get a final count even on error
            final_count_on_error = initial_count
            try: final_count_on_error = supabase.execute_sql("SELECT COUNT(*) as count FROM conversations")[0]['count']
            except: pass 
            return {
                "status": "error", 
                "message": str(e),
                "checked_api": conversations_checked_api_count,
                "initial_db_count": initial_count,
                "added": conversations_added_count, 
                "updated": conversations_updated_count, 
                "skipped": conversations_skipped_count,
                "failed": conversations_failed_count,
                "final_db_count": final_count_on_error # Report count even on failure
            }, 500
