import requests
from flask import current_app
import json
from datetime import datetime, timedelta
import random
import logging
import os
from urllib.parse import quote
from app.utils.cache import cache_api_response

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
    
    @cache_api_response(ttl=600)  # Cache for 10 minutes
    def count_total_conversations(self):
        """
        Count the total number of conversations available in the system regardless of date filters.
        
        Returns:
            int: Total number of conversations available
        """
        try:
            # Use the same endpoint that works for get_conversations but with minimal data
            endpoint = f"{self.api_url}/v1/convai/conversations" 
            
            # Request with large limit but minimal fields
            params = {
                'limit': 1000,  # Request a large number to get a better count
                'minimal': True  # If API supports minimal data mode
            }
            
            # Make the request
            response = self.session.get(endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check different possible response formats
                if 'total' in data:
                    # Direct total count in response
                    total = data.get('total', 0)
                    logging.info(f"API provided total count: {total}")
                    return total
                elif 'conversations' in data:
                    # Count conversations in response
                    conversations = data.get('conversations', [])
                    total = len(conversations)
                    
                    # Check if there's pagination indicating more
                    has_more = data.get('has_more', False) or data.get('next_cursor') is not None
                    
                    if has_more:
                        logging.info(f"API returned {total} conversations but indicates there are more")
                        # If there are more, add a buffer to the estimate
                        return total + 1000  # Rough estimate that there are more
                    
                    logging.info(f"Counted {total} total conversations")
                    return total
            
            # If we couldn't get a direct count, fall back to a reasonable default
            logging.warning(f"Could not determine total count, API status: {response.status_code}")
            return 1000  # Default estimated total
            
        except Exception as e:
            logging.error(f"Error counting total conversations: {e}")
            return 0
    
    @cache_api_response(ttl=3600)  # Cache for 1 hour
    def get_conversations(self, start_date=None, end_date=None, limit=100, offset=0):
        """
        Get conversations from the ElevenLabs API
        
        Args:
            start_date (str, optional): Start date filter (ISO format)
            end_date (str, optional): End date filter (ISO format)
            limit (int, optional): Max number of conversations to return
            offset (int, optional): Offset for pagination
            
        Returns:
            dict: API response with conversations
        """
        # Format dates for API - convert to Unix timestamps
        formatted_start = self._format_date(start_date) if start_date else None
        formatted_end = self._format_date(end_date, end_of_day=True) if end_date else None
        
        # Log the formatted dates for debugging
        logging.info(f"Processing dates: {start_date} → {formatted_start}, {end_date} → {formatted_end}")
        
        # Define endpoints to try, prioritizing the one that works for individual conversations
        endpoints_to_try = [
            f"{self.api_url}/v1/convai/conversations",    # This consistently works based on logs
            f"{self.api_url}/v1/history",                 # Secondary option
            f"{self.api_url}/v1/voices/history"           # Last resort
        ]
        
        logging.info(f"Will try these endpoints in order: {endpoints_to_try}")
        
        # Storage for all conversations
        all_conversations = []
        next_cursor = None
        max_pages = 10
        current_page = 0
        
        # Try each endpoint until one works
        for endpoint in endpoints_to_try:
            logging.info(f"Trying endpoint: {endpoint}")
            
            # Try multiple parameter formats for date filtering
            parameter_formats_to_try = [
                # Format 1: Simple from_time/to_time (Unix timestamps)
                {
                    'limit': limit,
                    'from_time': formatted_start,
                    'to_time': formatted_end
                } if formatted_start and formatted_end else None,
                
                # Format 2: ISO string dates
                {
                    'limit': limit,
                    'start_date': start_date,
                    'end_date': end_date
                } if start_date and end_date else None,
                
                # Format 3: No date filters, just get recent conversations
                {
                    'limit': limit
                }
            ]
            
            # Remove None entries (if dates weren't provided)
            parameter_formats_to_try = [p for p in parameter_formats_to_try if p is not None]
            
            # Try each parameter format
            for params in parameter_formats_to_try:
                logging.info(f"Trying parameter format: {params}")
                
                try:
                    # Make the request
                    response = self.session.get(endpoint, params=params)
                    response_status = response.status_code
                    
                    logging.info(f"Response status from {endpoint}: {response_status}")
                    
                    # If not 200, try next format
                    if response_status != 200:
                        try:
                            error_json = response.json()
                            error_detail = error_json.get('detail', error_json)
                            logging.info(f"Error response from API: {error_detail}")
                        except:
                            error_detail = response.text[:200]
                            logging.info(f"Error response (non-JSON): {error_detail}")
                        
                        logging.info(f"Trying next parameter format...")
                        continue
                    
                    # Successfully got data
                    data = response.json()
                    logging.info(f"Successfully retrieved data from {endpoint}")
                    logging.info(f"Response data keys: {list(data.keys())}")
                    
                    # Try to extract conversations from various possible formats
                    conversations = []
                    if 'conversations' in data:
                        conversations = data.get('conversations', [])
                    elif 'history' in data:
                        conversations = data.get('history', [])
                    elif 'items' in data:
                        conversations = data.get('items', [])
                    
                    logging.info(f"Retrieved {len(conversations)} conversations from API")
                    
                    # If we found conversations, we can stop trying other formats/endpoints
                    if conversations:
                        logging.info(f"Found {len(conversations)} conversations with {endpoint} using params {params}")
                        # Store these for pagination
                        successful_endpoint = endpoint
                        successful_params = params
                        
                        # Add to our collected list
                        all_conversations.extend(conversations)
                        
                        # Check for pagination options
                        next_cursor = data.get('next_cursor') or data.get('next_page_token') or data.get('next')
                        has_more = data.get('has_more', False) or data.get('more', False) or (next_cursor is not None)
                        
                        # Handle pagination if available
                        while next_cursor and has_more and current_page < max_pages:
                            current_page += 1
                            logging.info(f"Moving to page {current_page+1} with cursor {next_cursor}")
                            
                            # Update pagination parameter
                            pagination_params = successful_params.copy()
                            if 'next_cursor' in data:
                                pagination_params['cursor'] = next_cursor
                            elif 'next_page_token' in data:
                                pagination_params['page_token'] = next_cursor
                            else:
                                pagination_params['cursor'] = next_cursor
                            
                            # Make the paginated request
                            response = self.session.get(successful_endpoint, params=pagination_params)
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                # Get conversations from this page
                                if 'conversations' in data:
                                    page_conversations = data.get('conversations', [])
                                elif 'history' in data:
                                    page_conversations = data.get('history', [])
                                elif 'items' in data:
                                    page_conversations = data.get('items', [])
                                else:
                                    page_conversations = []
                                
                                logging.info(f"Retrieved {len(page_conversations)} conversations on page {current_page+1}")
                                
                                # Add to our result list
                                all_conversations.extend(page_conversations)
                                
                                # Update pagination for next page
                                next_cursor = data.get('next_cursor') or data.get('next_page_token') or data.get('next')
                                has_more = data.get('has_more', False) or data.get('more', False) or (next_cursor is not None)
                            else:
                                logging.info(f"Error in pagination, stopping at page {current_page+1}")
                                break
                        
                        # Successfully found and retrieved conversations
                        logging.info(f"Successfully retrieved a total of {len(all_conversations)} conversations from API")
                        
                        # Apply date filtering manually if API didn't do it correctly
                        if start_date or end_date:
                            filtered_conversations = self._apply_date_filtering(all_conversations, start_date, end_date)
                            logging.info(f"After manual date filtering: {len(filtered_conversations)} conversations (from {len(all_conversations)})")
                            
                            # Return filtered data
                            return {
                                'conversations': filtered_conversations,
                                'total': len(filtered_conversations)
                            }
                        else:
                            # Return all conversations if no date filter
                            return {
                                'conversations': all_conversations,
                                'total': len(all_conversations)
                            }
                
                except Exception as e:
                    logging.error(f"Exception with endpoint {endpoint} and params {params}: {e}")
                    continue
        
        # If we reach here, all endpoint/parameter combinations failed
        logging.warning("All API endpoints failed, returning empty results")
        return {
            'conversations': [],
            'total': 0
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
                    return data
                
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
        print(f"DEBUG: Adapting conversation details from ElevenLabs format")
        
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
            
            # Process transcript into turns
            transcript = data.get('transcript', [])
            turns = []
            
            for message in transcript:
                # Determine if message is from agent or user
                is_agent = message.get('sender_type', '') == 'agent'
                
                # Get the message text
                text = message.get('text', '')
                
                # Get timestamp if available
                timestamp = message.get('created_at', '')
                
                # Create turn object
                turn = {
                    'text': text,
                    'is_agent': is_agent,
                    'timestamp': timestamp
                }
                
                turns.append(turn)
            
            # Create the result object
            result = {
                'id': conversation_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'status': status,
                'turns': turns
            }
            
            print(f"DEBUG: Returning adapted conversation with {len(turns)} turns")
            return result
        
        # Create a basic structure (fallback)
        result = {
            'id': data.get('id', ''),
            'start_time': data.get('start_time', ''),
            'end_time': data.get('end_time', ''),
            'duration': data.get('duration', 0),
            'status': data.get('status', 'completed'),
            'turns': []
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