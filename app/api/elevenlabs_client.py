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
                        force_refresh: bool = False):
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
        
        # Storage for the best result found across all endpoints
        best_result_conversations = []
        best_result_count = 0
        
        # --- Loop through Endpoints --- 
        for endpoint in endpoints_to_try:
            logging.info(f"=== Trying Endpoint: {endpoint} ===")
            # Reset vars for this endpoint attempt
            endpoint_succeeded_at_all = False 
            current_endpoint_conversations = []
            pagination_complete = False

            # --- Construct Parameter Formats (same as before) --- 
            parameter_formats_to_try = []
            # Format 1: Unix timestamps
            if use_timestamps:
                params_ts = {'limit': 50} # Use fixed page size for reliability
                if from_time is not None: params_ts['from_time'] = from_time
                if to_time is not None: params_ts['to_time'] = to_time
                parameter_formats_to_try.append(params_ts)
            # Format 2: Derived timestamps
            elif formatted_start_from_date is not None or formatted_end_from_date is not None:
                params_derived_ts = {'limit': 50}
                if formatted_start_from_date is not None: params_derived_ts['from_time'] = formatted_start_from_date
                if formatted_end_from_date is not None: params_derived_ts['to_time'] = formatted_end_from_date
                parameter_formats_to_try.append(params_derived_ts)
            # Format 3: ISO dates
            if not use_timestamps and (start_date or end_date):
                params_iso = {'limit': 50}
                if start_date: params_iso['start_date'] = start_date
                if end_date: params_iso['end_date'] = end_date
                if len(params_iso) > 1 and params_iso not in parameter_formats_to_try:
                    parameter_formats_to_try.append(params_iso)
            # Format 4: Limit only
            params_limit_only = {'limit': 50}
            if params_limit_only not in parameter_formats_to_try:
                 parameter_formats_to_try.append(params_limit_only)
            logging.debug(f"Endpoint {endpoint}: Parameter formats to try: {parameter_formats_to_try}")

            # --- Loop through Parameter Formats for this endpoint --- 
            for params in parameter_formats_to_try:
                # Skip to next format if we already completed pagination with a previous format for this endpoint
                if pagination_complete: continue 

                logging.info(f"Endpoint {endpoint}: Trying parameter format: {params}")
                try:
                    # --- Initial Request --- 
                    response = self.session.get(endpoint, params=params)
                    response_status = response.status_code
                    logging.info(f"Endpoint {endpoint}, Params {params}: Initial response status: {response_status}")
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
                        logging.info(f"Endpoint {endpoint}, Params {params}: No conversations found and no cursor. Trying next format.")
                        continue # Try next parameter format
                    
                    logging.info(f"Endpoint {endpoint}, Params {params}: Found {len(initial_conversations)} initial conversations. Starting pagination...")
                    endpoint_succeeded_at_all = True # Mark this endpoint as having worked at least once
                    current_endpoint_conversations = list(initial_conversations) # Reset list for this attempt
                    successful_params = params 
                    next_cursor = data.get('next_cursor') or data.get('next_page_token') or data.get('next')
                    has_more = data.get('has_more', False) or data.get('more', False) or (next_cursor is not None)
                    current_page = 0
                    max_pages = 30 # Increase max pages slightly just in case

                    # --- Pagination Loop (for this endpoint/param format) --- 
                    while next_cursor and current_page < max_pages:
                        current_page += 1
                        logging.info(f"PAGINATION ({endpoint}): Entering page {current_page+1}/{max_pages}. Cursor: {next_cursor}")
                        pagination_params = successful_params.copy()
                        
                        # Detect cursor param name (simplified)
                        cursor_param_name = 'cursor' # Default guess
                        if 'next_page_token' in data: cursor_param_name = 'page_token'
                        elif 'after_id' in data: cursor_param_name = 'after_id'
                        pagination_params[cursor_param_name] = next_cursor
                        logging.debug(f"PAGINATION ({endpoint}): Requesting page {current_page+1} with params: {pagination_params}")
                        
                        response = self.session.get(endpoint, params=pagination_params)
                        
                        if response.status_code == 200:
                            data = response.json() # Update data for next cursor check
                            page_conversations = []
                            if 'conversations' in data: page_conversations = data.get('conversations', [])
                            elif 'history' in data: page_conversations = data.get('history', [])
                            elif 'items' in data: page_conversations = data.get('items', [])
                            logging.info(f"PAGINATION ({endpoint}): Retrieved {len(page_conversations)} conversations on page {current_page+1}")
                            current_endpoint_conversations.extend(page_conversations)
                            
                            next_cursor = data.get('next_cursor') or data.get('next_page_token') or data.get('next')
                            has_more = data.get('has_more', False) or data.get('more', False) or (next_cursor is not None)
                            logging.info(f"PAGINATION ({endpoint}): After page {current_page+1} - next_cursor: {next_cursor}, has_more: {has_more}")
                            
                            if not has_more and not next_cursor:
                                logging.info(f"PAGINATION ({endpoint}): Stopping - API reports no more data.")
                                pagination_complete = True # Mark pagination as complete for this endpoint
                                break
                        else:
                            logging.error(f"PAGINATION ({endpoint}): Error fetching page {current_page+1}. Status: {response.status_code}. Stopping pagination for this attempt.")
                            break # Stop pagination for this endpoint/param attempt

                    # Mark pagination complete if loop finished naturally or hit max pages
                    if not pagination_complete: 
                         pagination_complete = True 
                         logging.info(f"PAGINATION ({endpoint}): Finished (max pages reached or no more cursor).")

                    # Since this parameter format worked and pagination completed, break from parameter format loop
                    logging.info(f"Endpoint {endpoint}: Successfully completed fetch/pagination with params {successful_params}.")
                    break # Exit the parameter format loop

                except Exception as e:
                    logging.error(f"Endpoint {endpoint}, Params {params}: Error during fetch/pagination: {e}")
                    # Do not set pagination_complete = True on error, allow next format to be tried
                    continue # Try next parameter format

            # --- After trying all parameter formats for the endpoint --- 
            if endpoint_succeeded_at_all:
                logging.info(f"Endpoint {endpoint}: Succeeded. Total conversations fetched: {len(current_endpoint_conversations)}")
                # Check if this endpoint gave us more results than previous ones
                if len(current_endpoint_conversations) > best_result_count:
                    logging.info(f"Endpoint {endpoint}: Found more conversations ({len(current_endpoint_conversations)}) than previous best ({best_result_count}). Updating best result.")
                    best_result_conversations = current_endpoint_conversations
                    best_result_count = len(current_endpoint_conversations)
            else:
                 logging.warning(f"Endpoint {endpoint}: Failed to retrieve any data after trying all formats.")
            # --- Continue to the next endpoint --- 

        # --- After trying all endpoints --- 
        logging.info(f"Finished trying all endpoints. Best result count: {best_result_count}")
        if best_result_count == 0:
            logging.error("CRITICAL: No endpoints were able to successfully retrieve any conversation data.")

        # Return the best result found
        return {
            'conversations': best_result_conversations[:limit] if limit > 0 else best_result_conversations,
            'total_count': best_result_count
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
            start_time = metadata.get('created_at', '')
            end_time = metadata.get('last_updated_at', '')
            duration = metadata.get('duration_seconds', 0)

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
                if start_time_unix_secs is not None:
                    time_in_call_secs = message.get('time_in_call_secs')
                    if time_in_call_secs is not None:
                        try:
                            # Ensure both are numbers before adding
                            if isinstance(start_time_unix_secs, (int, float)) and isinstance(time_in_call_secs, (int, float)):
                                message_unix_ts = float(start_time_unix_secs) + float(time_in_call_secs)
                                # Convert to timezone-aware UTC datetime object
                                calculated_timestamp = datetime.fromtimestamp(message_unix_ts, tz=timezone.utc) 
                            else:
                                logging.warning(f"Non-numeric type for start_time ({type(start_time_unix_secs)}) or time_in_call ({type(time_in_call_secs)}) for msg in conv {conversation_id}")
                        except (ValueError, TypeError, OverflowError) as ts_err:
                            logging.warning(f"Error calculating timestamp for conv {conversation_id}: {ts_err}. Start: {start_time_unix_secs}, Offset: {time_in_call_secs}")
                    else:
                         logging.warning(f"Missing time_in_call_secs for message in conv {conversation_id}: {message}")
                # else: start_time_unix_secs was None - error already logged

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
                'agent_id': data.get('agent_id') or metadata.get('agent_id'),
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'status': status,
                'turns': turns,
                'cost': cost,
                'summary': summary 
            }
            
            return result
        
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