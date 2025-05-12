"""
Client for interacting with the ElevenLabs API, specifically for the
Conversational Voice Agent data.
"""
# ==============================================================================
# == WARNING: CORE API CLIENT & ADAPTER LOGIC ==
# ==============================================================================
# This client handles communication with the ElevenLabs API and includes
# critical data adaptation logic (_adapt_conversation_details, 
# _adapt_data_structure) relied upon by the sync task (app/tasks/sync.py).
# 
# !! DO NOT MODIFY THIS FILE without explicit request and careful review !!
# 
# Changes can break API calls, data parsing, and impact data integrity.
# Discuss any required changes thoroughly before implementation.
# ==============================================================================

import requests
from flask import current_app
import json
from datetime import datetime, timedelta, timezone
import random
import logging
import os
from urllib.parse import quote
from app.utils.cache import cache_api_response
import traceback
from dateutil import parser

class ElevenLabsClient:
    def __init__(self, api_key, agent_id=None, api_url="https://api.elevenlabs.io"):
        """
        Initialize the ElevenLabs API client
        
        Args:
            api_key (str): API key for authentication
            agent_id (str, optional): Agent ID for accessing specific agent data
            api_url (str, optional): Base URL for the API
        """
        self.api_key = api_key
        self.agent_id = agent_id
        self.api_url = api_url
        
        # Create a session for connection pooling with only xi-api-key header
        # Explicitly avoid using Authorization header to prevent API errors
        self.session = requests.Session()
        self.session.headers.update({
            'xi-api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Debug logging
        logging.info(f"ElevenLabs API Key (first 5 chars): {api_key[:5] if api_key else 'None'}")
        logging.info(f"ElevenLabs Agent ID: {agent_id}")
        logging.info(f"ElevenLabs API URL: {api_url}")
        logging.debug(f"Using headers: {self.session.headers}")
    
    @cache_api_response(ttl=600)  # Cache for 10 minutes
    def test_connection(self):
        """Test the connection to the ElevenLabs API"""
        try:
            # Try getting the voices as a simple API test
            response = self.session.get(f"{self.api_url}/v1/voices")
            logging.info(f"Test API response status: {response.status_code}")
            
            if response.status_code == 200:
                voices = response.json().get('voices', [])
                logging.info(f"Available voices: {len(voices)}")
                for voice in voices[:3]:  # Just show first few to avoid cluttering logs
                    logging.info(f"- {voice.get('name')}")
                return True
            else:
                logging.warning(f"Failed to connect to ElevenLabs API. Status code: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"Error testing ElevenLabs API connection: {e}")
            return False
    
    @cache_api_response(ttl=1)  # Cache for 1 second only
    def count_total_conversations(self):
        """
        Count the total number of conversations available in the system regardless of date filters.
        
        Returns:
            int: Total number of conversations available
        """
        logging.info("Getting actual total conversations count...")
        
        try:
            # Use all_time date range to get all conversations
            result = self.get_conversations(
                start_date='2020-01-01',  # Very old date to get all conversations
                end_date=datetime.now().strftime('%Y-%m-%d'),  # Today
                limit=2000  # Very high limit to get as many as possible
            )
            
            # Count the total conversations
            total = len(result.get('conversations', []))
            logging.info(f"Actual total conversations count: {total}")
            
            return total
        except Exception as e:
            logging.error(f"Error getting total conversations count: {e}")
            return 0
    
    @cache_api_response(ttl=3600)  # Cache for 1 hour
    def get_conversations(self, 
                        start_date: str = None, 
                        end_date: str = None, 
                        from_time: int = None, # Unix timestamp
                        to_time: int = None,   # Unix timestamp
                        limit: int = 100, 
                        offset: int = 0, # Offset is likely ignored by API but kept for signature consistency
                        force_refresh: bool = False,
                        start_after_history_item_id: str = None):
        logging.info(f"ELEVENLABS_CLIENT.get_conversations CALLED. All kwargs: {locals()}") # DIAGNOSTIC PRINT
        """
        Get conversations from the ElevenLabs API.
        Prioritizes from_time/to_time (Unix timestamps) if provided.
        Falls back to start_date/end_date (ISO string) if timestamps are not given.
        
        Args:
            start_date (str, optional): Start date filter (YYYY-MM-DD)
            end_date (str, optional): End date filter (YYYY-MM-DD)
            from_time (int, optional): Start Unix timestamp filter.
            to_time (int, optional): End Unix timestamp filter.
            limit (int, optional): Max number of conversations PER PAGE (API max is usually 1000).
            offset (int, optional): Ignored by API, pagination handled by cursor.
            force_refresh (bool, optional): Force refresh data, bypass cache.
            start_after_history_item_id (str, optional): ID to start fetching after (for pagination).
            
        Returns:
            dict: API response containing 'conversations' list and potentially 'next_cursor'/'has_more'.
        """
        # --- Parameter Prioritization --- 
        # Use from_time/to_time directly if provided
        use_timestamps = from_time is not None or to_time is not None
        
        # Fallback: Format start_date/end_date to timestamps ONLY if from_time/to_time were NOT provided
        formatted_start_from_date = None
        formatted_end_from_date = None
        if not use_timestamps:
            formatted_start_from_date = self._format_date(start_date) if start_date else None
            formatted_end_from_date = self._format_date(end_date, end_of_day=True) if end_date else None
        
        # Log the effective time parameters being used
        effective_start = from_time if use_timestamps else formatted_start_from_date
        effective_end = to_time if use_timestamps else formatted_end_from_date
        logging.info(f"Effective time filter: from_time={effective_start}, to_time={effective_end}")
        
        # Define endpoints to try
        # --- REVERT ENDPOINT ORDER --- 
        endpoints_to_try = [
            f"{self.api_url}/v1/convai/conversations",    # Primary
            f"{self.api_url}/v1/history",                 # Fallback
            f"{self.api_url}/v1/voices/history"           # Last resort
        ]
        # --- END REVERT --- 
        
        logging.info(f"Will try these endpoints in order: {endpoints_to_try}")
        
        # Collect conversations from *all* endpoints then deduplicate by conversation_id / id
        all_results_conversations = []
        
        # Choose a large per‑page limit to minimize page count (API may cap at 1000)
        PER_PAGE_LIMIT = limit # Use the passed limit for API calls, default 100, sync.py passes 1000
        
        final_next_cursor_for_return = None # To store the cursor for the very next page after all operations

        for endpoint in endpoints_to_try:
            logging.info(f"=== Trying Endpoint: {endpoint} ===")
            endpoint_succeeded_at_all = False 
            current_endpoint_conversations = []
            pagination_complete = False
            
            # --- Construct Parameter Formats --- 
            parameter_formats_to_try = []
            # Initial params setup - apply start_after_history_item_id if this is the first page fetch using it
            initial_api_params = {'limit': PER_PAGE_LIMIT}
            if start_after_history_item_id:
                # This assumes the API uses 'start_after_history_item_id'. Adjust if API uses a different name.
                initial_api_params['start_after_history_item_id'] = start_after_history_item_id

            # Format 1: Unix timestamps (add to initial_api_params)
            if use_timestamps:
                params_ts = initial_api_params.copy()
                if from_time is not None: params_ts['from_time'] = from_time
                if to_time is not None: params_ts['to_time'] = to_time
                parameter_formats_to_try.append(params_ts)
            # Format 2: Derived timestamps (add to initial_api_params)
            elif formatted_start_from_date is not None or formatted_end_from_date is not None:
                params_derived_ts = initial_api_params.copy()
                if formatted_start_from_date is not None: params_derived_ts['from_time'] = formatted_start_from_date
                if formatted_end_from_date is not None: params_derived_ts['to_time'] = formatted_end_from_date
                parameter_formats_to_try.append(params_derived_ts)
            # Format 3: ISO dates (add to initial_api_params)
            if not use_timestamps and (start_date or end_date):
                params_iso = initial_api_params.copy()
                if start_date: params_iso['start_date'] = start_date
                if end_date: params_iso['end_date'] = end_date
                if len(params_iso) > (1 + (1 if start_after_history_item_id else 0)) and params_iso not in parameter_formats_to_try: # ensure more than just limit and cursor
                    parameter_formats_to_try.append(params_iso)
            
            # Format 4: Limit and potentially start_after_history_item_id only
            # This ensures that if only start_after_history_item_id is passed (with limit), it's tried.
            # And if no time filters AND no start_after_history_item_id, it tries with just limit.
            if initial_api_params not in parameter_formats_to_try:
                 parameter_formats_to_try.append(initial_api_params.copy())
            
            logging.debug(f"Endpoint {endpoint}: Parameter formats to try: {parameter_formats_to_try}")

            # --- Loop through Parameter Formats for this endpoint --- 
            for params_for_first_call in parameter_formats_to_try:
                if pagination_complete: continue 
                logging.info(f"Endpoint {endpoint}: Trying parameter format for first call: {params_for_first_call}")
                try:
                    response = self.session.get(endpoint, params=params_for_first_call)
                    response_status = response.status_code
                    logging.info(f"Endpoint {endpoint}, Params {params_for_first_call}: Initial response status: {response_status}")
                    if response_status != 200:
                        # Log error detail if possible
                        try: logging.info(f"Error detail: {response.json().get('detail', response.text[:100])}")
                        except: pass
                        continue # Try next parameter format for this endpoint

                    # --- Process Initial Data & Start Pagination --- 
                    data = response.json()
                    initial_conversations = []
                    if 'conversations' in data: initial_conversations = data.get('conversations', [])
                    elif 'history' in data: initial_conversations = data.get('history', [])
                    elif 'items' in data: initial_conversations = data.get('items', [])
                    
                    if not initial_conversations and not data.get('next_cursor'): # Check if response is empty AND no cursor
                        logging.info(f"Endpoint {endpoint}, Params {params_for_first_call}: No conversations found and no cursor. Trying next format.")
                        continue # Try next parameter format
                    
                    logging.info(f"Endpoint {endpoint}, Params {params_for_first_call}: Found {len(initial_conversations)} initial conversations. Starting pagination if cursor exists...")
                    endpoint_succeeded_at_all = True
                    current_endpoint_conversations = list(initial_conversations)
                    successful_params_base = params_for_first_call.copy()
                    # Remove time/date params for subsequent pagination calls if API uses a pure cursor
                    # However, some APIs might require time filters to remain for cursor pagination.
                    # For now, assume cursor is enough for subsequent pages.
                    # Keep only 'limit' and the cursor param for pagination calls.
                    pagination_base_params = {'limit': PER_PAGE_LIMIT}

                    current_page_next_cursor = data.get('next_cursor') or data.get('next_page_token') or data.get('next')
                    current_page = 0
                    max_pages = 100 

                    while current_page_next_cursor and current_page < max_pages:
                        current_page += 1
                        logging.info(f"PAGINATION ({endpoint}): Page {current_page+1}/{max_pages}. Cursor: {current_page_next_cursor}")
                        
                        page_params = pagination_base_params.copy()
                        # This needs to align with what the API expects for its cursor parameter name.
                        # Common names: 'cursor', 'page_token', 'start_after_history_item_id', 'offset' (though offset is different)
                        # Assuming a generic 'cursor' or the specific 'start_after_history_item_id' if that's what API uses for subsequent pages.
                        # The parameter name might be different for the *first* call vs subsequent calls.
                        page_params['start_after_history_item_id'] = current_page_next_cursor # Try with the known param name
                        # Or, if the API uses a different name like 'cursor': page_params['cursor'] = current_page_next_cursor
                        
                        logging.debug(f"PAGINATION ({endpoint}): Requesting page {current_page+1} with params: {page_params}")
                        response_page = self.session.get(endpoint, params=page_params)
                        
                        if response_page.status_code == 200:
                            data_page = response_page.json()
                            page_conversations = []
                            if 'conversations' in data_page: page_conversations = data_page.get('conversations', [])
                            elif 'history' in data_page: page_conversations = data_page.get('history', [])
                            elif 'items' in data_page: page_conversations = data_page.get('items', [])
                            logging.info(f"PAGINATION ({endpoint}): Retrieved {len(page_conversations)} conversations on page {current_page+1}")
                            current_endpoint_conversations.extend(page_conversations)
                            
                            current_page_next_cursor = data_page.get('next_cursor') or data_page.get('next_page_token') or data_page.get('next')
                            has_more_from_api = data_page.get('has_more', False) or (current_page_next_cursor is not None)
                            
                            if not has_more_from_api:
                                logging.info(f"PAGINATION ({endpoint}): Stopping - API reports no more data.")
                                pagination_complete = True
                                break
                        else:
                            logging.error(f"PAGINATION ({endpoint}): Error fetching page {current_page+1}. Status: {response_page.status_code}. Stopping pagination.")
                            current_page_next_cursor = None # Stop pagination
                            break
                    
                    final_next_cursor_for_return = current_page_next_cursor # Store the last known next cursor for the return value
                    if not current_page_next_cursor: pagination_complete = True
                    break # Exit parameter format loop as this one succeeded
                except Exception as e:
                    logging.error(f"Endpoint {endpoint}, Params {params_for_first_call}: Error during fetch/pagination: {e}")
                    # Do not set pagination_complete = True on error, allow next format to be tried
                    continue # Try next parameter format

            # --- After trying all parameter formats for the endpoint --- 
            if endpoint_succeeded_at_all:
                logging.info(f"Endpoint {endpoint}: Succeeded. Total conversations fetched: {len(current_endpoint_conversations)}")
                # Always extend the aggregate list; we'll deduplicate later
                all_results_conversations.extend(current_endpoint_conversations)
            else:
                 logging.warning(f"Endpoint {endpoint}: Failed to retrieve any data after trying all formats.")
            # --- Continue to the next endpoint --- 

        # --- After trying all endpoints, deduplicate aggregated results ---
        deduped = []
        seen_ids = set()
        for conv in all_results_conversations:
            cid = conv.get('conversation_id') or conv.get('id')
            if cid is None:
                # Include conversations without an ID but log once
                logging.debug("Conversation without ID encountered while deduplicating; including anyway.")
                deduped.append(conv)
                continue
            if cid not in seen_ids:
                deduped.append(conv)
                seen_ids.add(cid)

        total_found = len(deduped)
        logging.info(f"Finished trying all endpoints. Total unique conversations gathered: {total_found}")

        if total_found == 0:
            logging.error("CRITICAL: No endpoints were able to successfully retrieve any conversation data.")

        # Return deduplicated result, optionally limited for caller convenience
        limited_convs = deduped[:limit] if (limit and limit > 0) else deduped
        # +++ Add next_cursor to the return value +++
        # This is a bit heuristic: we return the next_cursor found during the last successful pagination attempt.
        # The caller (sync.py) will need to be aware of this.
        # If multiple endpoints were tried, this `next_cursor` belongs to the last one that successfully paginated.
        # For robust API-level pagination, sync.py should ideally handle calling this method iteratively.
        # However, for now, let's return what the client found internally.
        return {
            'conversations': limited_convs,
            'total_count': total_found,
            'next_cursor': final_next_cursor_for_return # Return the stored next cursor
        }
    
    def _apply_date_filtering(self, conversations, start_date=None, end_date=None):
        """
        Apply manual date filtering to conversation data
        
        Args:
            conversations (list): List of conversation dictionaries
            start_date (str, optional): Start date in ISO format (YYYY-MM-DD)
            end_date (str, optional): End date in ISO format (YYYY-MM-DD)
            
        Returns:
            list: Filtered list of conversations
        """
        if not start_date and not end_date:
            return conversations
        
        # Parse dates for comparison
        try:
            start_datetime = datetime.fromisoformat(start_date) if start_date else None
            # Set end date to end of day
            if end_date:
                end_datetime = datetime.fromisoformat(end_date)
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            else:
                end_datetime = None
        except ValueError as e:
            logging.error(f"Error parsing dates for filtering: {e}")
            return conversations
        
        filtered = []
        for conv in conversations:
            # Try different timestamp fields that might exist
            timestamp = None
            
            # Check for Unix timestamp fields
            if 'start_time_unix_secs' in conv:
                try:
                    timestamp = datetime.fromtimestamp(int(conv['start_time_unix_secs']))
                except (ValueError, TypeError):
                    pass
            
            # Check for ISO timestamp fields
            if not timestamp and 'start_time' in conv:
                try:
                    if isinstance(conv['start_time'], str):
                        timestamp = datetime.fromisoformat(conv['start_time'].replace('Z', '+00:00'))
                    elif isinstance(conv['start_time'], int):
                        timestamp = datetime.fromtimestamp(conv['start_time'])
                except (ValueError, TypeError):
                    pass
            
            # Check for other timestamp fields
            if not timestamp and 'created_at' in conv:
                try:
                    if isinstance(conv['created_at'], str):
                        timestamp = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
                    elif isinstance(conv['created_at'], int):
                        timestamp = datetime.fromtimestamp(conv['created_at'])
                except (ValueError, TypeError):
                    pass
            
            # If we couldn't find a valid timestamp, include by default
            if not timestamp:
                filtered.append(conv)
                continue
            
            # Compare with start and end dates
            include = True
            if start_datetime and timestamp < start_datetime:
                include = False
            if end_datetime and timestamp > end_datetime:
                include = False
            
            if include:
                filtered.append(conv)
        
        return filtered
    
    @cache_api_response(ttl=86400)  # Cache for 24 hours
    def get_conversation_details(self, conversation_id):
        """
        Get details for a specific conversation
        
        Args:
            conversation_id (str): ID of the conversation to fetch
            
        Returns:
            dict: API response with conversation details
        """
        if not conversation_id:
            logging.warning("No conversation ID provided for details lookup")
            return {'conversation_id': '', 'transcript': []}
            
        logging.info(f"Getting details for conversation ID: {conversation_id}")
        
        # Try different endpoints in order of preference
        endpoints_to_try = [
            f"{self.api_url}/v1/convai/conversations/{conversation_id}",
            f"{self.api_url}/v1/history/{conversation_id}",
            f"{self.api_url}/v1/voices/history/{conversation_id}"
        ]
        
        # Try each endpoint
        for endpoint in endpoints_to_try:
            logging.info(f"Trying endpoint for conversation details: {endpoint}")
            
            try:
                # Make the request
                response = self.session.get(endpoint)
                status = response.status_code
                
                logging.info(f"Response status from {endpoint}: {status}")
                
                # If not found, try next endpoint
                if status == 404:
                    logging.info(f"Conversation {conversation_id} not found at {endpoint}")
                    continue
                
                # If other error, try next endpoint
                if status != 200:
                    try:
                        error_detail = response.json().get('detail', 'Unknown error')
                    except:
                        error_detail = response.text[:200]
                    logging.info(f"Error response from {endpoint}: {error_detail}")
                    continue
                
                # Parse the response
                data = response.json()
                
                # Check if we got valid data
                if not data:
                    logging.warning(f"Empty response from {endpoint}")
                    continue
                    
                logging.info(f"Successfully retrieved conversation details from {endpoint}")
                logging.info(f"Response keys: {list(data.keys())}")
                
                # Try different data formats
                if 'conversation' in data:
                    # Format 1: Conversation in a nested key
                    conversation = data['conversation']
                    if conversation and isinstance(conversation, dict):
                        return conversation
                elif 'history_item' in data:
                    # Format 2: History item format
                    history_item = data['history_item']
                    if history_item and isinstance(history_item, dict):
                        return history_item
                elif 'id' in data or 'conversation_id' in data:
                    # Format 3: Direct conversation object

                    # +++ ADD LOGGING BEFORE ADAPTATION +++
                    try:
                        log_keys = list(data.keys()) if isinstance(data, dict) else "Not a dict"
                        analysis_block = data.get('analysis') if isinstance(data, dict) else "N/A"
                        logging.error(f"PRE-ADAPT KEYS: {log_keys}")
                        logging.error(f"PRE-ADAPT ANALYSIS: {str(analysis_block)[:500]}")
                    except Exception as log_err:
                        logging.error(f"Error logging PRE-ADAPT data: {log_err}")
                    # +++ END LOGGING BEFORE ADAPTATION +++

                    adapted_data = self._adapt_conversation_details(data)
                    return adapted_data
                
                # If we reach here, the response didn't match any known format
                logging.warning(f"Unknown response format from {endpoint}")
                
            except Exception as e:
                logging.error(f"Error fetching conversation details from {endpoint}: {e}")
                continue
                
        # If we reach here, all endpoint attempts failed
        logging.warning(f"Failed to retrieve conversation {conversation_id} from any endpoint")
        return {
            'conversation_id': conversation_id,
            'transcript': [],
            'error': 'Conversation not found'
        }
    
    def _format_date(self, date_str, end_of_day=False):
        """
        Format date string for API requests
        
        Args:
            date_str (str): Date string in format "YYYY-MM-DD"
            end_of_day (bool): Whether to set time to end of day
            
        Returns:
            int: Unix timestamp in seconds
        """
        if not date_str:
            return None
            
        try:
            # Parse the date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Set time to start of day (midnight) or end of day based on parameter
            if end_of_day:
                date_obj = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                
            # Convert to Unix timestamp (seconds)
            return int(date_obj.timestamp())
            
        except Exception as e:
            print(f"DEBUG: Error formatting date {date_str}: {e}")
            return None
    
    def _process_date(self, date_str):
        """Process date string to format expected by the API"""
        if not date_str:
            return None
            
        try:
            # Parse the date string - removed 2025 check since it's now the current year
            
            # Parse the date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Format into ISO-8601 format
            formatted_date = date_obj.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            return formatted_date
        except Exception as e:
            print(f"DEBUG: Error processing date {date_str}: {str(e)}")
            return date_str  # Return original if there's an error
               
    def _adapt_history_to_conversations(self, data):
        """Convert history data format to conversations format"""
        if 'history' not in data:
            return {'conversations': [], 'total': 0}
            
        conversations = []
        for item in data['history']:
            # Extract the necessary fields and convert them to our expected format
            conv = {
                'id': item.get('id', ''),
                'start_time': item.get('start_time', ''),
                'end_time': item.get('end_time', ''),
                'duration': item.get('duration', 0),
                'status': item.get('status', 'completed')
            }
            
            # If the item has a 'turns' key, include it
            if 'turns' in item:
                conv['turns'] = item['turns']
            # Or messages, or exchanges, depending on what the API returns
            elif 'messages' in item:
                conv['turns'] = [{'is_agent': msg.get('is_agent', False), 'text': msg.get('text', '')} 
                               for msg in item['messages']]
            
            conversations.append(conv)
            
        return {
            'conversations': conversations,
            'total': len(conversations)
        }
    
    def _adapt_data_structure(self, data):
        """Try to adapt any data structure to our expected format"""
        print(f"DEBUG: Adapting API response data structure")
        
        # If we have the ElevenLabs convai/conversations endpoint response
        if 'conversations' in data and isinstance(data['conversations'], list):
            print(f"DEBUG: Processing convai API conversations list with {len(data['conversations'])} items")
            conversations = []
            
            for conv in data['conversations']:
                # Extract key fields from the ElevenLabs API format
                conversation_id = conv.get('conversation_id', '')
                
                # Get metadata
                metadata = conv.get('metadata', {})
                start_time = metadata.get('created_at', '')
                end_time = metadata.get('last_updated_at', '')
                
                # Get status
                status = conv.get('status', 'unknown')
                
                # Calculate duration if available in metadata
                duration = 0
                if 'duration_seconds' in metadata:
                    duration = metadata.get('duration_seconds', 0)
                
                # Count turns if available
                turns_count = 0
                transcript = conv.get('transcript', [])
                if isinstance(transcript, list):
                    turns_count = len(transcript)
                
                # Create normalized conversation object
                normalized_conv = {
                    'id': conversation_id,
                    'conversation_id': conversation_id,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'status': status,
                    'turn_count': turns_count
                }
                
                conversations.append(normalized_conv)
            
            result = {
                'conversations': conversations,
                'total': len(conversations)
            }
            
            print(f"DEBUG: Returning adapted list with {len(conversations)} conversations")
            return result
            
        # Fall back to original behavior for other formats
        if isinstance(data, list):
            return {
                'conversations': [self._normalize_conversation(item) for item in data],
                'total': len(data)
            }
        elif isinstance(data, dict):
            for key in ['calls', 'conversations', 'history', 'items', 'results', 'data']:
                if key in data and isinstance(data[key], list):
                    return {
                        'conversations': [self._normalize_conversation(item) for item in data[key]],
                        'total': len(data[key])
                    }
        
        # Fallback: just return original data
        return data
    
    def _normalize_conversation(self, conv_data):
        """Normalize a conversation object to our expected format"""
        # Create a basic structure with defaults
        normalized = {
            'id': '',
            'conversation_id': '',  # Add conversation_id field
            'start_time': '',
            'end_time': '',
            'duration': 0,
            'status': 'completed',
            'turns': [],
            'turn_count': 0  # Add turn_count field
        }
        
        # Copy over all values that exist in the original data
        for key in normalized.keys():
            if key in conv_data:
                normalized[key] = conv_data[key]
        
        # Extract ID if it exists in different formats
        for id_key in ['id', 'conversation_id', 'call_id', 'session_id']:
            if id_key in conv_data:
                normalized['id'] = conv_data[id_key]
                normalized['conversation_id'] = conv_data[id_key]  # Set both id and conversation_id
                break
        
        # Calculate turn_count if turns are available but turn_count isn't
        if 'turns' in conv_data and 'turn_count' not in conv_data:
            normalized['turn_count'] = len(conv_data['turns'])
        
        return normalized
    
    def _adapt_conversation_details(self, data):
        """Adapt conversation details to the format our app expects"""
        # --- REMOVE SAFER RAW DATA LOGGING --- 
        # if not hasattr(self, '_safe_log_count'): self._safe_log_count = 0
        # if self._safe_log_count < 5: 
        #     try:
        #         log_keys = list(data.keys()) if isinstance(data, dict) else "Not a dict"
        #         analysis_block = data.get('analysis') if isinstance(data, dict) else "N/A"
        #         # Log keys and analysis block using ERROR level for visibility
        #         logging.error(f"SAFELOG RAW KEYS (call {self._safe_log_count + 1}): {log_keys}")
        #         logging.error(f"SAFELOG ANALYSIS BLOCK (call {self._safe_log_count + 1}): {str(analysis_block)[:500]}") # Log analysis content
        #     except Exception as log_err:
        #          logging.error(f"Could not perform safe logging: {log_err}")
        #     self._safe_log_count += 1
        # --- END REMOVE SAFER RAW DATA LOGGING ---
        
        # Handle ElevenLabs convai/conversations/{id} format
        if 'conversation_id' in data and 'transcript' in data:
            print(f"DEBUG: Processing ElevenLabs conversation detail format")
            
            # Extract key fields
            conversation_id = data.get('conversation_id', '')
            status = data.get('status', 'completed')
            
            # Extract metadata
            metadata = data.get('metadata', {})
            # DEBUG: Log metadata['created_at'] value and type
            created_at_val = metadata.get('created_at', None)
            logging.debug(f"_adapt_conversation_details: metadata['created_at'] for conversation_id={conversation_id}: value={created_at_val}, type={type(created_at_val)}")
            start_time = None
            end_time = ''
            duration = 0
            # Use start_time_unix_secs if present
            if 'start_time_unix_secs' in metadata:
                try:
                    start_time = datetime.fromtimestamp(metadata['start_time_unix_secs'], tz=timezone.utc)
                except Exception as e:
                    logging.warning(f"Could not parse start_time_unix_secs: {metadata['start_time_unix_secs']} for conversation_id={conversation_id}: {e}")

            # Fallback: parse metadata.created_at (ISO string) if start_time is still None
            if start_time is None:
                created_at_raw = metadata.get('created_at') or data.get('created_at')
                if created_at_raw:
                    try:
                        parsed_dt = parser.parse(str(created_at_raw))
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        start_time = parsed_dt
                        logging.debug(f"_adapt_conversation_details: Parsed fallback created_at {created_at_raw} -> {start_time} for conv {conversation_id}")
                    except Exception as created_at_err:
                        logging.warning(f"Could not parse created_at '{created_at_raw}' for conversation_id={conversation_id}: {created_at_err}")

            # Use call_duration_secs if present, else fallback to duration_seconds
            if 'call_duration_secs' in metadata:
                duration = metadata['call_duration_secs']
            elif 'duration_seconds' in metadata:
                duration = metadata['duration_seconds']
            # Calculate end_time if possible
            if start_time and duration:
                try:
                    end_time = start_time + timedelta(seconds=duration)
                except Exception as e:
                    logging.warning(f"Could not calculate end_time for conversation_id={conversation_id}: {e}")
            # Debug print/log for calculated values
            print(f"_adapt_conversation_details: Calculated start_time={start_time}, duration={duration}, end_time={end_time} for conversation_id={conversation_id}")

            # +++ Extract agent_id robustly +++
            agent_id = data.get('agent_id') or metadata.get('agent_id')

            # +++ Extract Summary (Revised - Check analysis block) +++
            summary = None
            analysis_data = data.get('analysis') # Get analysis data again
            if analysis_data and isinstance(analysis_data, dict):
                summary = analysis_data.get('transcript_summary') # Check this first!
                if summary is None:
                    summary = analysis_data.get('summary')
                if summary is None:
                    summary = analysis_data.get('generated_summary')
                if summary is None:
                    summary = analysis_data.get('abstractive_summary')
            
            # Fallback checks (as before)
            if summary is None: 
                 summary = data.get('summary') # Check root level
            if summary is None:
                 summary = metadata.get('summary') # Check metadata
            if summary is None:
                 summary = data.get('call_summary') # Check other common key
            # +++ End Summary Extraction +++

            # +++ Extract cost information from metadata +++
            cost = metadata.get('cost_in_credits') # Check metadata first
            if cost is None: # Fallback check directly on data if not in metadata
                cost = data.get('cost_in_credits')
            if cost is None: # Fallback check for other potential keys
                 cost = metadata.get('cost') or data.get('cost')
            if cost is None:
                 cost = metadata.get('total_tokens') or data.get('total_tokens')
            # +++ End Cost Extraction +++
            
            # Process transcript into turns
            transcript = data.get('transcript', [])
            turns = []

            # +++ Get start_time_unix_secs for timestamp calculation +++
            start_time_unix_secs = metadata.get('start_time_unix_secs')

            if start_time_unix_secs is None:
                logging.error(f"Missing start_time_unix_secs in metadata for conv {conversation_id}, cannot calculate message timestamps.")
                # Set to None to indicate failure downstream
                calculated_timestamp = None 
            
            # Determine base datetime for timestamp calculation
            base_datetime = None
            if start_time_unix_secs is not None:
                try:
                    base_datetime = datetime.fromtimestamp(float(start_time_unix_secs), tz=timezone.utc)
                except Exception:
                    base_datetime = None
            elif isinstance(start_time, datetime):
                base_datetime = start_time

            for message in transcript:
                # Determine role and if agent
                role = message.get('role', 'unknown') # Use 'role' key as per docs
                is_agent = (role == 'agent')
                
                # +++ Determine Speaker Name +++
                speaker_name = 'agent' if is_agent else 'user'
                if role == 'unknown': # Handle unknown role case
                    # You might decide on a different default or logic here
                    speaker_name = 'unknown' 
                    logging.warning(f"Unknown role found in transcript for {conversation_id}. Defaulting speaker to 'unknown'. Message: {str(message)[:100]}")
                # +++ End Speaker Name Determination +++

                # Get the message text
                text = message.get('message', '') # Use 'message' key as per docs
                
                # +++ Calculate timestamp +++
                calculated_timestamp = None # Default to None
                time_in_call_secs = message.get('time_in_call_secs')
                if base_datetime is not None and time_in_call_secs is not None:
                    try:
                        if isinstance(time_in_call_secs, (int, float)):
                            calculated_timestamp = base_datetime + timedelta(seconds=float(time_in_call_secs))
                        else:
                            logging.warning(f"Non-numeric time_in_call_secs type ({type(time_in_call_secs)}) for msg in conv {conversation_id}")
                    except Exception as ts_err:
                        logging.warning(f"Error calculating timestamp for conv {conversation_id}: {ts_err}. Base: {base_datetime}, Offset: {time_in_call_secs}")
                else:
                    if base_datetime is None:
                        logging.error(f"Cannot calculate timestamp for message in conv {conversation_id}: base_datetime is None.")
                    elif time_in_call_secs is None:
                        logging.warning(f"Missing time_in_call_secs for message in conv {conversation_id}: {message}")

                # Get timestamp if available (REMOVED - we calculate it now)
                # timestamp = message.get('created_at', '')
                
                # Create turn object
                turn = {
                    'text': text,
                    'is_agent': is_agent,
                    'role': role, # Add role for potential future use
                    'timestamp': calculated_timestamp, # Use the calculated timestamp (datetime object or None)
                    'speaker': speaker_name # Add the determined speaker name
                }
                
                turns.append(turn)
            
            # Create the result object
            result = {
                'id': conversation_id,
                'agent_id': agent_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'status': status,
                'turns': turns,
                'cost': cost,
                'summary': summary 
            }
            
            # Final adapted data
            adapted = {
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "status": status,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "summary": summary,
                "cost": cost,
                "turns": turns,
                "metadata": metadata,
            }

            # DEBUG LOG: Log full adapted data
            logging.debug(f"_adapt_conversation_details: FULL adapted data for conversation_id={conversation_id}: {adapted}")
            print(f"_adapt_conversation_details: FULL adapted data for conversation_id={conversation_id}: {adapted}")

            return adapted
        
        # Create a basic structure (fallback)
        result = {
            'id': data.get('id', ''),
            'agent_id': data.get('agent_id'),
            'start_time': data.get('start_time', ''),
            'end_time': data.get('end_time', ''),
            'duration': data.get('duration', 0),
            'status': data.get('status', 'completed'),
            'turns': [],
            'summary': (data.get('analysis', {}).get('summary') if isinstance(data, dict) else None) or data.get('summary') or data.get('call_summary') 
        }
        
        # Extract turns/messages from different possible formats
        if 'turns' in data:
            result['turns'] = data['turns']
        elif 'messages' in data:
            result['turns'] = [
                {
                    'text': msg.get('text', ''),
                    'is_agent': msg.get('is_agent', False) or msg.get('role', '').lower() == 'assistant',
                    'timestamp': msg.get('timestamp', '')
                }
                for msg in data['messages']
            ]
        elif 'transcript' in data:
            # Some APIs might return a transcript format
            if isinstance(data['transcript'], list):
                result['turns'] = [
                    {
                        'text': entry.get('text', ''),
                        'is_agent': entry.get('speaker', '').lower() == 'agent',
                        'timestamp': entry.get('timestamp', '')
                    }
                    for entry in data['transcript']
                ]
            elif isinstance(data['transcript'], str):
                # If it's just a string, create a single turn
                result['turns'] = [
                    {
                        'text': data['transcript'],
                        'is_agent': True,
                        'timestamp': data.get('timestamp', '')
                    }
                ]
        
        # +++ Add cost extraction to fallback structure +++
        cost = data.get('cost_in_credits') or data.get('cost') or data.get('total_tokens')
        result['cost'] = cost
        # +++ End Cost Extraction +++

        return result
    
    def _adapt_calls_to_conversations(self, data):
        """Convert calls data format to conversations format"""
        if 'calls' not in data:
            return {'conversations': [], 'total': 0}
            
        conversations = []
        for item in data['calls']:
            # Extract the necessary fields and convert them to our expected format
            conv = {
                'id': item.get('id', ''),
                'start_time': item.get('start_time', item.get('created_at', '')),
                'end_time': item.get('end_time', item.get('updated_at', '')),
                'duration': item.get('duration', 0),
                'status': item.get('status', 'completed')
            }
            
            # If the item has message-related keys
            if 'turns' in item:
                conv['turns'] = item['turns']
            elif 'messages' in item:
                conv['turns'] = [{'is_agent': msg.get('is_agent', False), 'text': msg.get('text', '')} 
                               for msg in item['messages']]
            elif 'transcript' in item:
                conv['turns'] = [{'is_agent': msg.get('is_agent', False), 'text': msg.get('content', '')} 
                               for msg in item.get('transcript', [])]
            
            conversations.append(conv)
            
        return {
            'conversations': conversations,
            'total': len(conversations)
        }
    
    def _adapt_messages_to_turns(self, data):
        """Convert messages format to turns format"""
        if 'messages' not in data:
            return data
            
        # Create a copy of the data
        result = data.copy()
        
        # Convert messages to turns
        result['turns'] = [
            {
                'is_agent': msg.get('is_agent', msg.get('role', '') == 'assistant'),
                'text': msg.get('text', msg.get('content', '')),
                'timestamp': msg.get('timestamp', msg.get('created_at', ''))
            }
            for msg in data['messages']
        ]
        
        return result
        
    def _adapt_transcript_to_turns(self, data):
        """Convert transcript format to turns format"""
        if 'transcript' not in data:
            return data
            
        # Create a copy of the data
        result = data.copy()
        
        # Convert transcript to turns
        result['turns'] = [
            {
                'is_agent': entry.get('is_agent', entry.get('role', '') == 'assistant'),
                'text': entry.get('text', entry.get('content', '')),
                'timestamp': entry.get('timestamp', entry.get('created_at', ''))
            }
            for entry in data['transcript']
        ]
        
        return result 