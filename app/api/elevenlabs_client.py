import requests
from flask import current_app
import json
from datetime import datetime, timedelta
import random
import logging
import os
from urllib.parse import quote

class ElevenLabsClient:
    def __init__(self, api_key, agent_id=None, api_url="https://api.elevenlabs.io", demo_mode=False):
        """
        Initialize the ElevenLabs API client
        
        Args:
            api_key (str): API key for authentication
            agent_id (str, optional): Agent ID for accessing specific agent data
            api_url (str, optional): Base URL for the API
            demo_mode (bool, optional): Whether to use demo data instead of making real API calls
        """
        self.api_key = api_key
        self.agent_id = agent_id
        self.api_url = api_url
        self.demo_mode = demo_mode
        
        # Create a session for connection pooling with only xi-api-key header
        # Explicitly avoid using Authorization header to prevent API errors
        self.session = requests.Session()
        self.session.headers.update({
            'xi-api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Debug logging
        print(f"DEBUG: ELEVENLABS_API_KEY (first 5 chars): {api_key[:5] if api_key else 'None'}")
        print(f"DEBUG: ELEVENLABS_AGENT_ID: {agent_id}")
        print(f"DEBUG: ELEVENLABS_API_URL: {api_url}")
        print(f"DEBUG: DEMO_MODE: {demo_mode}")
        print(f"DEBUG: Using headers: {self.session.headers}")
    
    def test_connection(self):
        """Test the connection to the ElevenLabs API"""
        try:
            # Try getting the voices as a simple API test
            response = self.session.get(f"{self.api_url}/v1/voices")
            print(f"DEBUG: Test API response status: {response.status_code}")
            
            if response.status_code == 200:
                voices = response.json().get('voices', [])
                print(f"DEBUG: Available voices: {len(voices)}")
                for voice in voices[:3]:  # Just show first few to avoid cluttering logs
                    print(f"DEBUG: - {voice.get('name')}")
                return True
            else:
                print(f"DEBUG: Failed to connect to ElevenLabs API. Status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"DEBUG: Error testing ElevenLabs API connection: {e}")
            return False
    
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
        # If in demo mode, return demo data
        if self.demo_mode:
            return self._get_demo_conversations()
            
        # Format dates for API - convert to Unix timestamps
        formatted_start = self._format_date(start_date) if start_date else None
        formatted_end = self._format_date(end_date, end_of_day=True) if end_date else None
        
        # Print the formatted dates for debugging
        print(f"DEBUG: Processing dates: {start_date} → {formatted_start}, {end_date} → {formatted_end}")
        
        # Set up parameters for the request
        params = {
            'limit': limit,
            'order_by': 'start_time_unix_secs',  # Always sort by start time
            'order_direction': 'asc'  # Always sort ascending (earliest first)
        }
        
        # Add date filters if provided - use Unix timestamp format (seconds)
        if formatted_start is not None:
            params['from_time'] = formatted_start
        if formatted_end is not None:
            params['to_time'] = formatted_end
            
        # Add agent ID if provided
        if self.agent_id:
            params['agent_id'] = self.agent_id
            
        # Debug logging
        print(f"DEBUG: Attempting API request to {self.api_url}/v1/convai/conversations")
        print(f"DEBUG: Headers being sent: {self.session.headers}")
        print(f"DEBUG: Params being sent: {params}")
        
        # Build the URL with parameters
        url = f"{self.api_url}/v1/convai/conversations"
        query_string = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        full_url = f"{url}?{query_string}"
        print(f"DEBUG: Request URL: {full_url}")
        
        # Storage for all conversations
        all_conversations = []
        next_cursor = None
        max_pages = 10  # Increasing page limit to ensure we get all data
        current_page = 0
        
        while current_page < max_pages:
            try:
                # Create a copy of params for this request
                request_params = params.copy()
                
                # Add cursor to params if we have one
                if next_cursor:
                    request_params['cursor'] = next_cursor
                    
                # Make the request
                response = self.session.get(url, params=request_params)
                response_status = response.status_code
                
                # Log the response status
                print(f"DEBUG: Response status: {response_status}")
                
                # If we got an auth error about using both headers, retry with just xi-api-key
                if response_status == 400 and 'authorization_header' in response.text.lower():
                    print(f"DEBUG: Got authorization header error, retrying with only xi-api-key header")
                    
                    # Create a new session with only xi-api-key header
                    retry_session = requests.Session()
                    retry_session.headers.update({
                        'xi-api-key': self.api_key,
                        'Content-Type': 'application/json'
                    })
                    
                    # Retry the request
                    response = retry_session.get(url, params=request_params)
                    response_status = response.status_code
                    print(f"DEBUG: Retry response status: {response_status}")
                
                # If we still have issues, try with bearer token
                if response_status != 200 and response_status != 404:
                    print(f"DEBUG: Still having issues, trying with bearer token")
                    
                    # Create a new session with bearer token
                    bearer_session = requests.Session()
                    bearer_session.headers.update({
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json'
                    })
                    
                    # Retry the request
                    response = bearer_session.get(url, params=request_params)
                    response_status = response.status_code
                    print(f"DEBUG: Bearer token retry response status: {response_status}")
                
                # Handle successful response
                if response_status == 200:
                    data = response.json()
                    print(f"DEBUG: Successfully retrieved data from {url}")
                    print(f"DEBUG: Response data keys: {list(data.keys())}")
                    
                    # Get conversations from this page
                    conversations = data.get('conversations', [])
                    print(f"DEBUG: Retrieved {len(conversations)} conversations on page {current_page+1}")
                    
                    # Add the conversations to our collected list
                    all_conversations.extend(conversations)
                    
                    # Check for next page indicator
                    next_cursor = data.get('next_cursor')
                    has_more = data.get('has_more', False)
                    
                    if not next_cursor or not has_more:
                        print(f"DEBUG: No more pages available")
                        break  # No more pages
                        
                    # Increment page counter and continue to next page
                    current_page += 1
                    print(f"DEBUG: Moving to page {current_page+1} with cursor {next_cursor}")
                else:
                    # Try to parse the error response
                    error_detail = "Unknown error"
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('detail', error_json)
                        print(f"DEBUG: Error response from API: {error_detail}")
                    except:
                        error_detail = response.text[:200]  # Limit the error text
                        print(f"DEBUG: Error response (non-JSON): {error_detail}")
                    
                    print(f"DEBUG: Error fetching conversations: {response_status} - {error_detail}")
                    
                    # Fall back to demo data in case of API errors
                    print(f"DEBUG: Falling back to demo data for conversations")
                    return self._get_demo_conversations()
                    
            except Exception as e:
                print(f"DEBUG: Exception fetching conversations: {e}")
                # Fall back to demo data in case of exception
                print(f"DEBUG: Falling back to demo data for conversations due to exception")
                return self._get_demo_conversations()
        
        # Handle case where we may have hit the page limit
        if current_page == max_pages and has_more:
            print(f"WARNING: Reached maximum page limit ({max_pages}) but there are more results available")
        
        # Return the combined results
        result = {
            'conversations': all_conversations,
            'total': len(all_conversations)
        }
        
        print(f"DEBUG: Returning combined results with {len(all_conversations)} conversations")
        return result
    
    def get_conversation_details(self, conversation_id):
        """
        Get details for a specific conversation
        
        Args:
            conversation_id (str): ID of the conversation to fetch
            
        Returns:
            dict: API response with conversation details
        """
        # If in demo mode, return demo data
        if self.demo_mode:
            return self._get_demo_conversation_details(conversation_id)
        
        print(f"DEBUG: Attempting to get real conversation details for ID {conversation_id}")
        
        # Build the URL
        url = f"{self.api_url}/v1/convai/conversations/{conversation_id}"
        
        # Debug info
        print(f"DEBUG: Attempting to get conversation details from {url}")
        print(f"DEBUG: Headers being sent: {self.session.headers}")
        
        # Try with regular headers first
        try:
            # Make the request
            response = self.session.get(url)
            response_status = response.status_code
            
            # Log the response status and headers
            print(f"DEBUG: Response status: {response_status}")
            print(f"DEBUG: Response headers: {response.headers}")
            
            # If we got an auth error about using both headers, retry with just xi-api-key
            if response_status == 400 and 'authorization_header' in response.text.lower():
                print(f"DEBUG: Got authorization header error, retrying with only xi-api-key header")
                
                # Create a new session with only xi-api-key header
                retry_session = requests.Session()
                retry_session.headers.update({
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json'
                })
                
                # Retry the request
                response = retry_session.get(url)
                response_status = response.status_code
                print(f"DEBUG: Retry response status: {response_status}")
            
            # If we still have issues, try with bearer token
            if response_status != 200 and response_status != 404:
                print(f"DEBUG: Still having issues, trying with bearer token")
                
                # Create a new session with bearer token
                bearer_session = requests.Session()
                bearer_session.headers.update({
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                })
                
                # Retry the request
                response = bearer_session.get(url)
                response_status = response.status_code
                print(f"DEBUG: Bearer token retry response status: {response_status}")
            
            # Handle successful response
            if response_status == 200:
                data = response.json()
                print(f"DEBUG: Successfully retrieved conversation details from {url}")
                print(f"DEBUG: Response data keys: {list(data.keys())}")
                
                # Append 'turns' to match expected format from demo mode
                # This is just for backwards compatibility and consistency
                if 'transcript' in data and isinstance(data['transcript'], list):
                    data['turns'] = data['transcript']
                
                # Print the raw conversation data for debugging
                print(f"DEBUG: Raw conversation data from API: {data.keys()}")
                
                return data
            else:
                # Try to parse the error response
                error_detail = "Unknown error"
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_json)
                    print(f"DEBUG: Error response from API: {error_detail}")
                except:
                    error_detail = response.text[:200]  # Limit the error text
                    print(f"DEBUG: Error response (non-JSON): {error_detail}")
                
                print(f"DEBUG: Error fetching conversation details: {response_status} - {error_detail}")
                
                # Fall back to demo/mock data in case of error
                print(f"DEBUG: Falling back to demo data for conversation {conversation_id}")
                return self._get_demo_conversation_details(conversation_id)
                
        except Exception as e:
            print(f"DEBUG: Exception fetching conversation details: {e}")
            # Fall back to demo/mock data in case of error
            print(f"DEBUG: Falling back to demo data for conversation {conversation_id} due to exception")
            return self._get_demo_conversation_details(conversation_id)
            
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
    
    # Demo data methods below - for development without API access
    def _get_demo_conversations(self):
        # For demo mode, return mock data
        # ... (existing code for demo mode)
        pass
        
    def _get_demo_conversation_details(self, conversation_id):
        # For demo mode, return mock data for conversation details
        # ... (existing code for demo mode)
        pass

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
    
    def _get_mock_conversations(self, start_date=None, end_date=None, limit=100, offset=0):
        """Generate mock conversation data for demo purposes"""
        print("DEBUG: Generating mock conversation data for demo mode")
        conversations = []
        
        # Generate random data
        for i in range(min(limit, 20)):
            start_time = datetime.now() - timedelta(days=random.randint(1, 30), 
                                                    hours=random.randint(1, 24),
                                                    minutes=random.randint(1, 60))
            duration = random.randint(30, 600)  # between 30 seconds and 10 minutes
            end_time = start_time + timedelta(seconds=duration)
            
            conv_id = f"mock-conversation-{i+1+offset}"
            turn_count = random.randint(5, 20)
            
            # Random status
            status = random.choice(["completed", "completed", "completed", "interrupted", "in_progress"])
            
            # Create mock conversation
            mock_conversation = {
                "id": conv_id,
                "conversation_id": conv_id,  # Add both ID formats to ensure compatibility
                "start_time": start_time.isoformat() + "Z",
                "end_time": end_time.isoformat() + "Z",
                "duration": duration,
                "turn_count": turn_count,
                "turns": [{"is_agent": i % 2 == 0, "text": "Sample text"} for i in range(turn_count)],
                "status": status
            }
            
            conversations.append(mock_conversation)
        
        mock_data = {"conversations": conversations, "total": len(conversations)}
        print(f"DEBUG: Generated {len(conversations)} mock conversations successfully")
        
        # Print a sample of the data for debugging
        if conversations:
            print(f"DEBUG: Sample mock conversation: {conversations[0]}")
            
        return mock_data
        
    def _get_mock_conversation_details(self, conversation_id):
        """Generate mock conversation details for demo purposes"""
        start_time = datetime.now() - timedelta(days=random.randint(1, 5), 
                                              hours=random.randint(1, 12))
        duration = random.randint(30, 600)  # between 30 seconds and 10 minutes
        end_time = start_time + timedelta(seconds=duration)
        
        # Generate a conversation with alternating turns
        turns = []
        num_turns = random.randint(5, 15)
        
        topics = ["career", "love", "family", "health", "money", "spirituality", "future"]
        
        current_time = start_time
        for i in range(num_turns):
            # Add a bit of time between messages
            current_time += timedelta(seconds=random.randint(3, 20))
            
            if i % 2 == 0:  # User turn
                text = random.choice([
                    "I'm curious about my career path. What do you see for me?",
                    "Will I find love this year?",
                    "I'm worried about my family situation. Any insights?",
                    "How can I improve my health?",
                    "I'm having financial troubles. What should I do?",
                    "I feel disconnected spiritually. How can I reconnect?",
                    "What does my future hold?",
                    "I've been feeling lost lately. Can you help me find direction?",
                    "I'm thinking about changing jobs. Is that a good idea?",
                    "Should I move to a new city?"
                ])
            else:  # Agent turn
                chosen_topic = random.choice(topics)
                if chosen_topic == "career":
                    text = random.choice([
                        "I sense a new opportunity coming your way in your career. Stay open to change.",
                        "Your professional life will take an unexpected turn soon, but it will be for the better.",
                        "I see you excelling in a leadership role in the near future.",
                        "Your creative talents will soon be recognized in your workplace."
                    ])
                elif chosen_topic == "love":
                    text = random.choice([
                        "Love is coming into your life when you least expect it.",
                        "I sense a deeper connection forming in your current relationship.",
                        "Pay attention to someone who keeps appearing in your life - there's a reason.",
                        "Your heart will heal from past wounds and open to new possibilities."
                    ])
                elif chosen_topic == "family":
                    text = random.choice([
                        "A family reconciliation is on the horizon.",
                        "You'll soon strengthen bonds with a family member you've been distant from.",
                        "Family support will be crucial in the coming months.",
                        "I sense a family celebration or gathering bringing joy soon."
                    ])
                else:
                    text = random.choice([
                        "I sense positive energy surrounding your question.",
                        "The cards are showing a period of transformation ahead.",
                        "Trust your intuition on this matter.",
                        "I'm seeing a positive outcome if you remain patient.",
                        "This is a time for reflection before taking action."
                    ])
            
            turns.append({
                "text": text,
                "is_agent": i % 2 != 0,
                "timestamp": current_time.isoformat() + "Z"
            })
        
        return {
            "id": conversation_id,
            "conversation_id": conversation_id,  # Add conversation_id field to match expectations
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
            "duration": duration,
            "turns": turns,
            "status": "completed",
            "transcript": [
                {"speaker": "User" if not turn["is_agent"] else "Agent", 
                 "text": turn["text"], 
                 "timestamp": turn["timestamp"]} 
                for turn in turns
            ]
        }
    
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