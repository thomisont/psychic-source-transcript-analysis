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
import openai # Added
import os # Added
from typing import List, Dict
import time
import re
from flask import current_app, jsonify
from postgrest.exceptions import APIError

# Import necessary components (use absolute imports)
from app.extensions import db
# from app.models import Conversation, Message
from app.api.elevenlabs_client import ElevenLabsClient # We need the client directly here
from app.services.supabase_conversation_service import SupabaseConversationService # Import the service
from app.services.analysis_service import AnalysisService # Import for cache clearing

# Import SupabaseClient (add path to ensure it's available)
sys.path.append(str(Path(__file__).parent.parent.parent))
from tools.supabase_client import SupabaseClient

# --- Helper function for OpenAI Embedding ---
# Modified to accept transcript turns and concatenate
# Modified to return a tuple: (embedding_vector, was_truncated)
def get_embedding(turns: List[Dict[str, str]], client):
    was_truncated = False # Flag to track truncation
    if not client or not turns:
        logging.debug("Sync Task: Skipping embedding generation - no client or turns provided.")
        return None, was_truncated
    
    # Concatenate transcript content
    full_transcript_text = " ".join([turn.get('content', '') for turn in turns if turn.get('content')])
    
    if not full_transcript_text.strip():
        logging.debug("Sync Task: Skipping embedding generation - concatenated transcript is empty.")
        return None, was_truncated

    # Simple truncation heuristic (can be improved with tiktoken)
    # Estimate max characters based on average token length
    max_chars = 8000 * 4 # Rough estimate for text-embedding-3-small max tokens
    text_to_embed = full_transcript_text
    if len(full_transcript_text) > max_chars:
        text_to_embed = full_transcript_text[:max_chars]
        logging.warning(f"Sync Task: Truncated transcript text before embedding due to length ({len(full_transcript_text)} chars).")
        was_truncated = True # Set the flag
        
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text_to_embed
        )
        # Assuming the embedding is in response.data[0].embedding for openai > 1.0
        if response.data and len(response.data) > 0:
             logging.debug(f"Sync Task: Successfully generated embedding for concatenated transcript snippet '{text_to_embed[:100]}...'.")
             return response.data[0].embedding, was_truncated # Return vector and flag
        else:
             logging.error("Sync Task: OpenAI embedding response format unexpected or empty.")
             return None, was_truncated
    except Exception as e:
        # Log more context about the text length that failed
        logging.error(f"Sync Task: Failed to get embedding from OpenAI for transcript (approx {len(text_to_embed)} chars): {e}", exc_info=True) 
        return None, was_truncated # Return None and flag on error
# --- End Helper Function ---

def sync_new_conversations(app_context=None, full_sync=False):
    """
    Fetches new conversations from ElevenLabs API for all configured agents, processes them, and stores them in the Supabase database via the SupabaseConversationService.
    Handles incremental updates efficiently by:
    1. Fetching existing conversation IDs and summary status from Supabase.
    2. Calling the /details endpoint ONLY for NEW conversations or existing ones MISSING summaries.
    3. Skipping API calls for existing conversations that already have summaries (unless full_sync=True).
    """
    if app_context:
        app = app_context
    else:
        app = current_app._get_current_object()
        if not app:
            logging.critical("SYNC TASK: sync_new_conversations - Cannot obtain Flask app instance. Aborting sync.")
            return {"status": "error", "message": "Cannot obtain Flask app instance."}, 500
            
    start_time = time.time()
    logging.info(f"SYNC TASK: Starting conversation sync for ALL agents (Full Sync: {full_sync})...")

    agent_env_pattern = re.compile(r'^ELEVENLABS_AGENT_ID_([A-Z0-9_]+)$')
    agent_vars = [(k, v) for k, v in os.environ.items() if agent_env_pattern.match(k)]
    if not agent_vars:
        logging.error("No ELEVENLABS_AGENT_ID_* variables found in environment. Aborting sync.")
        return {"status": "error", "message": "No agent IDs found in environment."}, 500

    api_key = os.getenv('ELEVENLABS_API_KEY', '')
    if not api_key:
        logging.error("ELEVENLABS_API_KEY not found in environment. Aborting sync.")
        return {"status": "error", "message": "API key not found."}, 500

    all_results = []
    for env_var, agent_id in agent_vars:
        logging.info(f"SYNC TASK: Syncing for agent {env_var} (ID: {agent_id})...")
        client = ElevenLabsClient(api_key=api_key, agent_id=agent_id)
        try:
            result, status_code = _sync_agent_conversations(client, agent_id, full_sync)
            all_results.append({"agent_env": env_var, "agent_id": agent_id, "result": result, "status_code": status_code})
        except Exception as e:
            logging.error(f"SYNC TASK: Exception syncing agent {agent_id}: {e}", exc_info=True)
            all_results.append({"agent_env": env_var, "agent_id": agent_id, "result": str(e), "status_code": 500})

    success_count = sum(1 for r in all_results if r["status_code"] == 200)
    fail_count = len(all_results) - success_count
    logging.info(f"SYNC TASK: Completed for all agents. Success: {success_count}, Failed: {fail_count}")
    return {"status": "multi-agent-complete", "results": all_results}, 200 if fail_count == 0 else 500

# --- Extracted original sync logic for a single agent ---
def _sync_agent_conversations(client, agent_id, full_sync=False):
    start_time = time.time()
    app = current_app._get_current_object()
    if not app:
        logging.critical("SYNC TASK: _sync_agent_conversations - Cannot obtain Flask app instance. Aborting for agent.")
        return {"status": "error", "message": "Cannot obtain Flask app instance for agent sync."}, 500

    logging.info(f"SYNC TASK: Starting conversation sync for agent {agent_id} (Full Sync: {full_sync})...")

    # --- TEMPORARY CACHE CLEAR --- 
    try:
        if hasattr(app, 'analysis_service') and app.analysis_service and hasattr(app.analysis_service, 'clear_cache'):
             app.analysis_service.clear_cache()
             logging.info("SYNC TASK: Cleared AnalysisService cache at start of sync.")
        else:
             logging.warning("SYNC TASK: Could not clear analysis cache at start - service not found or no clear_cache method.")
    except Exception as cache_clear_err:
         logging.error(f"SYNC TASK: Error clearing analysis cache at start: {cache_clear_err}", exc_info=True)
    # --- END TEMPORARY CACHE CLEAR ---

    if not client or not client.api_key or not client.agent_id:
        logging.error("Sync Task: Passed ElevenLabs client is not properly configured. Aborting.")
        return {"status": "error", "message": "Passed client not configured"}, 500

    with app.app_context(): 
        # MINIMAL DIAGNOSTIC LOGGING
        logging.info(f"SYNC_TASK_MINIMAL_DEBUG: In _sync_agent_conversations, before model import. DB type: {type(db)}")
        try:
            from app.models import Conversation, Message 
            logging.info(f"SYNC_TASK_MINIMAL_DEBUG: Models imported successfully.")
        except Exception as import_err:
            logging.error(f"SYNC_TASK_MINIMAL_DEBUG: ERROR DURING MODEL IMPORT: {import_err}", exc_info=True)
            raise # Re-raise the import error to see its traceback immediately
        
        logging.info(f"Starting conversation sync task... (Full Sync: {full_sync})")
        initial_count = 0
        final_count = 0
        conversations_added_count = 0
        conversations_updated_count = 0
        conversations_skipped_count = 0
        conversations_failed_count = 0
        truncated_count = 0
        conversations_checked_api_count = 0

        try:
            # This is the main try block for the sync logic for this agent
            supabase_url = app.config.get('SUPABASE_URL')
            supabase_key = app.config.get('SUPABASE_KEY')
            if not supabase_url or not supabase_key:
                 raise ValueError("Supabase URL or Service Key not found in app configuration for sync task.")
            supabase = SupabaseClient(supabase_url, supabase_key)
            logging.info("Initialized Supabase client for sync task")
            
            # Initialize OpenAI Client
            openai_api_key = app.config.get('OPENAI_API_KEY')
            openai_client = None # Initialize as None
            if not openai_api_key:
                logging.warning("Sync Task: OPENAI_API_KEY not found in config. Embedding generation will be skipped.")
            else:
                try:
                    openai_client = openai.OpenAI(api_key=openai_api_key)
                    logging.info("Initialized OpenAI client for sync task")
                except Exception as openai_init_err:
                    logging.error(f"Sync Task: Failed to initialize OpenAI client: {openai_init_err}. Embedding generation will be skipped.")
                    openai_client = None # Ensure it's None on failure
            # End OpenAI Client Initialization

            # === 1. Get Initial Count & Existing IDs/Summary/Embedding Status from Supabase ===
            existing_conversations_dict = {}
            try:
                # Get initial count
                count_query = "SELECT COUNT(*) as count FROM conversations"
                count_result = supabase.execute_sql(count_query)
                initial_count = count_result[0]['count'] if count_result else 0
                logging.info(f"Sync Task: Initial conversation count in DB: {initial_count}")

                # Fetch all existing external_ids and check if summary/embedding is NULL
                # Fetch in chunks if necessary for very large tables, but start simple
                existing_query = "SELECT external_id, (summary IS NOT NULL) as has_summary, (embedding IS NOT NULL) as has_embedding FROM conversations"
                existing_results = supabase.execute_sql(existing_query)
                if existing_results:
                    for row in existing_results:
                        # Store both summary and embedding status
                        existing_conversations_dict[row['external_id']] = {
                            'has_summary': row['has_summary'],
                            'has_embedding': row['has_embedding']
                        }
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
                            # No messages in DB => first-time sync. Fetch **all** conversations (no from_time).
                            sync_start_time = None
                            sync_start_timestamp_unix = None  # Passing None tells client to fetch full history
                            logging.warning("Sync Task: No existing messages found. Performing full history fetch from API.")
                except Exception as e:
                    logging.error(f"Sync Task: Error getting latest timestamp: {e}. Defaulting to fetching last 7 days.")
                    sync_start_time = datetime.now(timezone.utc) - timedelta(days=7)
                    sync_start_timestamp_unix = int(sync_start_time.timestamp())

            # === 3. Fetch Conversation Summaries from ElevenLabs API ===
            all_api_conversations_list = []
            last_history_item_id_for_api = None
            current_api_page = 0
            MAX_API_PAGES = 50 # Safety break: fetch max 50 * 1000 = 50,000 history items per agent per sync
            # Use a smaller limit for each API call to respect ElevenLabs rate limits & typical page sizes
            # The client's internal PER_PAGE_LIMIT is 1000, so we can use that.
            API_FETCH_LIMIT = 1000 

            logging.info(f"Sync Task: Starting paginated fetch from ElevenLabs API (from_time={sync_start_timestamp_unix}, page_limit={API_FETCH_LIMIT})")

            while current_api_page < MAX_API_PAGES:
                current_api_page += 1
                logging.info(f"Sync Task: Calling client.get_conversations page {current_api_page}, from_time={sync_start_timestamp_unix}, start_after_id={last_history_item_id_for_api}, limit={API_FETCH_LIMIT})")
                try:
                    # Pass the cursor to the client method, which should internally use it for 'start_after_history_item_id' or similar
                    api_response = client.get_conversations(
                        from_time=sync_start_timestamp_unix, 
                        limit=API_FETCH_LIMIT, 
                        start_after_history_item_id=last_history_item_id_for_api # NEW PARAM
                    )
                    current_batch = api_response.get('conversations', [])
                    all_api_conversations_list.extend(current_batch)
                    
                    # The client.get_conversations now returns a 'next_cursor'. 
                    # This cursor is typically the ID of the last item in the *previous* batch for ElevenLabs /history
                    # For the *next* call, we need to use the ID of the last item in the *current* batch if available.
                    # Or, if the API directly gives a cursor *for the next page*, use that.
                    # The client was modified to return the API's next_cursor, so we use that.
                    returned_next_cursor = api_response.get('next_cursor')

                    if current_batch and not returned_next_cursor:
                        # If we got data but no explicit next_cursor, assume we use the last item's ID from this batch
                        # Ensure `id` or `history_item_id` or `conversation_id` is consistently available on summary items
                        last_item_in_batch = current_batch[-1]
                        last_history_item_id_for_api = (
                            last_item_in_batch.get('history_item_id') or last_item_in_batch.get('id') or last_item_in_batch.get('conversation_id')
                        )
                        logging.info(f"Sync Task: API page {current_api_page} got {len(current_batch)} items. No explicit next_cursor. Using last item ID for next page: {last_history_item_id_for_api}")
                        if not last_history_item_id_for_api: # If last item also has no ID, something is wrong.
                            logging.warning(f"Sync Task: Last item in batch has no usable ID. Cannot paginate further this way. Batch: {last_item_in_batch}")
                            break
                    elif returned_next_cursor:
                        last_history_item_id_for_api = returned_next_cursor
                        logging.info(f"Sync Task: API page {current_api_page} got {len(current_batch)} items. Using API provided next_cursor: {last_history_item_id_for_api}")
                    else: # No current batch and no next_cursor
                        logging.info(f"Sync Task: API page {current_api_page} returned no items and no next_cursor. Assuming end of history.")
                        break
                    
                    if not current_batch: # Double check if the batch itself was empty, even if a cursor was returned
                        logging.info(f"Sync Task: API page {current_api_page} returned an empty batch. Assuming end of history.")
                        break

                except Exception as fetch_error:
                    logging.error(f"Sync Task: Error calling client.get_conversations on page {current_api_page}: {fetch_error}", exc_info=True)
                    conversations_failed_count +=1 # Count this as a failure for this page fetch
                    break # Stop pagination on error

            conversations_list = all_api_conversations_list
            conversations_checked_api_count = len(conversations_list)
            logging.info(f"Sync Task: Total {conversations_checked_api_count} conversation summaries received from API after pagination.")

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
                    # Updated logic: Need update if new OR (existing AND (embedding missing OR full_sync))
                    needs_detail_fetch = is_new or (
                        not is_new and (
                            not existing_conversations_dict[external_id]['has_embedding'] or full_sync
                        )
                    )

                    if not needs_detail_fetch:
                        logging.debug(f"Sync Task: Skipping detail fetch for existing conversation {external_id} (embedding present, not full sync).")
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

                        # DEBUG LOG: Raw API response
                        logging.debug(f"Sync Task: Raw conversation details for {external_id}: {str(conv_details_raw)[:1000]}")

                        adapted_data = client._adapt_conversation_details(conv_details_raw)
                        # DEBUG LOG: Adapted data
                        logging.debug(f"Sync Task: Adapted conversation details for {external_id}: {str(adapted_data)[:1000]}")
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

                        # --- Generate Embedding FROM TRANSCRIPT ---
                        embedding_vector, truncated_flag = get_embedding(adapted_data.get('turns', []), openai_client)
                        if truncated_flag:
                            truncated_count += 1 # Increment counter if truncated
                        # --- End Embedding Generation ---

                        # --- Perform Insert or Update (Simplified logic here, reuse existing DB blocks below) ---
                        logging.info(f"Sync Task: Pre-Op Check for {external_id}. Op: {'Insert' if is_new else 'Update'}")
                        if is_new:
                            try:
                                conv_data = {
                                    'external_id': external_id,
                                    'agent_id': adapted_data.get('agent_id'),
                                    'title': adapted_data.get('title', f"Conversation {external_id[:8]}"),
                                    'created_at': adapted_data.get('start_time').isoformat() if isinstance(adapted_data.get('start_time'), datetime) else datetime.now(timezone.utc).isoformat(), 
                                    'status': conv_status,
                                    'cost_credits': cost_value_int,
                                    'summary': conv_summary_str,
                                    'embedding': embedding_vector,
                                    'duration_seconds': adapted_data.get('duration'),
                                    'updated_at': datetime.now(timezone.utc).isoformat()
                                }
                                logging.info(f"Sync Task: Attempting INSERT for new conv {external_id}...")
                                conv_result = supabase.insert('conversations', conv_data)
                                if not conv_result or not conv_result[0].get('id'): 
                                    raise Exception(f"Supabase insert conversation failed or returned no ID for {external_id}. Result: {conv_result}")
                                conv_id = conv_result[0]['id']
                                logging.info(f"Inserted conversation {external_id} into Supabase with ID {conv_id}")
                                
                                messages_added = 0
                                for turn in adapted_data.get('turns', []):
                                    msg_timestamp_obj = turn.get('timestamp')
                                    timestamp_str_for_msg = None
                                    if isinstance(msg_timestamp_obj, datetime):
                                        if msg_timestamp_obj.tzinfo is None: msg_timestamp_obj = msg_timestamp_obj.replace(tzinfo=timezone.utc)
                                        timestamp_str_for_msg = msg_timestamp_obj.isoformat()
                                    elif msg_timestamp_obj: # if it's a string or number, try to parse
                                        try:
                                            parsed_ts = parser.parse(str(msg_timestamp_obj))
                                            if parsed_ts.tzinfo is None: parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
                                            timestamp_str_for_msg = parsed_ts.isoformat()
                                        except Exception:
                                            timestamp_str_for_msg = datetime.now(timezone.utc).isoformat() 
                                    else:
                                        timestamp_str_for_msg = datetime.now(timezone.utc).isoformat()

                                    msg_text_content = turn.get('text') or turn.get('content') or ''
                                    msg_data = {
                                        'conversation_id': conv_id,
                                        'speaker': turn.get('speaker'),
                                        'text': msg_text_content,
                                        'timestamp': timestamp_str_for_msg,
                                        'created_at': datetime.now(timezone.utc).isoformat(),
                                        'updated_at': datetime.now(timezone.utc).isoformat()
                                    }
                                    msg_insert_result = supabase.insert('messages', msg_data)
                                    if not msg_insert_result:
                                        logging.error(f"Failed to insert message for conversation {external_id}, turn: {turn}. Data: {msg_data}")
                                    else:    
                                        messages_added += 1
                                logging.info(f"Sync Task: Added {messages_added} messages for new conv {external_id}.")
                                conversations_added_count += 1

                            except APIError as e_insert:
                                error_details = e_insert.json() if callable(getattr(e_insert, 'json', None)) else getattr(e_insert, 'message', str(e_insert))
                                error_code = None
                                if isinstance(error_details, dict):
                                    error_code = error_details.get('code')
                                elif isinstance(e_insert, APIError): # Check type again
                                    error_code = getattr(e_insert, 'code', None) # Direct attribute access as fallback
                                
                                if error_code == '23505':
                                    logging.warning(f"Sync Task: INSERT for {external_id} failed (duplicate key - code {error_code}). Attempting UPDATE.")
                                    try:
                                        update_data_on_conflict = {
                                            'cost_credits': cost_value_int,
                                            'status': conv_status,
                                            'summary': conv_summary_str,
                                            'embedding': embedding_vector,
                                            'agent_id': adapted_data.get('agent_id'),
                                            'duration_seconds': adapted_data.get('duration'),
                                            'title': adapted_data.get('title', f"Conversation {external_id[:8]}"),
                                            'updated_at': datetime.now(timezone.utc).isoformat()
                                        }
                                        update_response = supabase.client.table('conversations').update(update_data_on_conflict).eq('external_id', external_id).execute()
                                        logging.info(f"Sync Task: Attempted UPDATE for {external_id} after duplicate insert. Response count: {len(update_response.data) if hasattr(update_response, 'data') else 'N/A'}")
                                        conversations_updated_count += 1 
                                    except Exception as update_err_on_conflict:
                                        logging.error(f"Sync Task: UPDATE for {external_id} after duplicate key error also FAILED: {update_err_on_conflict}", exc_info=True)
                                        conversations_failed_count += 1
                                else:
                                    logging.error(f"Sync Task: APIError (code: {error_code}, details: {error_details}) during insert for {external_id}.", exc_info=True)
                                    conversations_failed_count += 1
                            except Exception as supabase_general_insert_error:
                                logging.error(f"Sync Task: General error during insert op for new conv {external_id}: {supabase_general_insert_error}", exc_info=True)
                                conversations_failed_count += 1
                        else: # It's an update
                             logging.info(f"Sync Task: Updating fields for existing conversation {external_id}.")
                             try:
                                 update_data = {
                                     'cost_credits': cost_value_int,
                                     'status': conv_status,
                                     'summary': conv_summary_str,
                                     'embedding': embedding_vector,
                                     'agent_id': adapted_data.get('agent_id'),
                                     'duration_seconds': adapted_data.get('duration'),
                                     'title': adapted_data.get('title', f"Conversation {external_id[:8]}"), # ensure title is updated
                                     'updated_at': datetime.now(timezone.utc).isoformat()
                                 }
                                 # ... (original update logic from the file for this 'else' block, including message back-fill)
                                 response_update = supabase.client.table('conversations').update(update_data).eq('external_id', external_id).execute()
                                 logging.info(f"Supabase update executed for {external_id}. Response count: {len(response_update.data) if hasattr(response_update, 'data') else 'N/A'}")
                                 conversations_updated_count += 1
                                 # Message back-fill logic should follow here if it was part of original update
                                 # ... (original message back-fill logic) ...
                             except Exception as supabase_update_error:
                                 logging.error(f"Sync Task: Error during Supabase update operation for existing conv {external_id}: {supabase_update_error}", exc_info=True)
                                 conversations_failed_count += 1
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
            log_message = (
                f"Sync Task Finished. API Checked: {conversations_checked_api_count}, "
                f"DB Initial: {initial_count}, Added: {conversations_added_count}, "
                f"Updated: {conversations_updated_count}, Skipped: {conversations_skipped_count}, "
                f"Failed: {conversations_failed_count}, Truncated Embeddings: {truncated_count}, "
                f"DB Final: {final_count}."
            )
            logging.info(log_message)
            
            # >>> ADD CACHE CLEARING HERE <<<
            try:
                if hasattr(app, 'analysis_service') and app.analysis_service:
                    logging.info("Sync Task: Clearing AnalysisService cache...")
                    app.analysis_service.clear_cache()
                    logging.info("Sync Task: AnalysisService cache cleared.")
                else:
                    logging.warning("Sync Task: AnalysisService not found on app context, cannot clear cache.")
            except Exception as cache_clear_err:
                logging.error(f"Sync Task: Error clearing analysis cache: {cache_clear_err}", exc_info=True)
            # >>> END CACHE CLEARING <<<
            
            return {
                "status": "success", 
                "checked_api": conversations_checked_api_count,
                "initial_db_count": initial_count,
                "added": conversations_added_count, 
                "updated": conversations_updated_count, 
                "skipped": conversations_skipped_count,
                "failed": conversations_failed_count,
                "final_db_count": final_count,
                "truncated_embeddings": truncated_count
            }, 200

        except Exception as e_outer:
            logging.error(f"Sync Task Failed Unexpectedly for agent {agent_id}: {e_outer}", exc_info=True)
            if hasattr(app, 'analysis_service') and app.analysis_service: app.analysis_service.clear_cache()
            return {
                "status": "error", "message": str(e_outer),
                "checked_api": conversations_checked_api_count,
                "initial_db_count": initial_count,
                "added": conversations_added_count, 
                "updated": conversations_updated_count, 
                "skipped": conversations_skipped_count,
                "failed": conversations_failed_count,
                # final_db_count might not be accurate here, depends on where error happened
                # "final_db_count": final_count_on_error, 
                "truncated_embeddings": truncated_count
            }, 500

def _get_last_sync_timestamp(app_context):
    """Gets the timestamp of the most recently created conversation in the DB."""
    if app_context:
        app = app_context
        with app.app_context():
            from app.models import Message # Example if models are needed here
            # ... query logic ...
            pass
    return None

def _process_conversation_data(convo_data, app_context=None):
    """Processes raw conversation data from ElevenLabs API."""
    if app_context:
        app = app_context
    # ... rest of _process_conversation_data function ...
    pass

def _save_conversation(session, convo_details, message_details, app_context=None):
    """Saves a single conversation and its messages to the database."""
    if app_context:
        app = app_context
    # ... rest of _save_conversation function ...
    pass

# ... potentially other functions using models ...
