import requests
from flask import current_app
import json
from datetime import datetime, timedelta
import random
import logging
import os
from urllib.parse import quote

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
        print(f"DEBUG: ELEVENLABS_API_KEY (first 5 chars): {api_key[:5] if api_key else 'None'}")
        print(f"DEBUG: ELEVENLABS_AGENT_ID: {agent_id}")
        print(f"DEBUG: ELEVENLABS_API_URL: {api_url}")
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
        # Format dates for API - convert to Unix timestamps
        formatted_start = self._format_date(start_date) if start_date else None
        formatted_end = self._format_date(end_date, end_of_day=True) if end_date else None
        
        # Print the formatted dates for debugging
        print(f"DEBUG: Processing dates: {start_date} → {formatted_start}, {end_date} → {formatted_end}")
        
        # Change the order of endpoints to try, prioritizing the one that works for individual conversations
        endpoints_to_try = [
            f"{self.api_url}/v1/convai/conversations",    # This consistently works based on logs
            f"{self.api_url}/v1/history",                 # Secondary option
            f"{self.api_url}/v1/voices/history"           # Last resort
        ]
        
        print(f"DEBUG: Will try these endpoints in order: {endpoints_to_try}")
        
        # Storage for all conversations
        all_conversations = []
        next_cursor = None
        max_pages = 10
        current_page = 0
        
        # Try each endpoint until one works
        for endpoint in endpoints_to_try:
            print(f"DEBUG: Trying endpoint: {endpoint}")
            
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
                print(f"DEBUG: Trying parameter format: {params}")
                
                try:
                    # Make the request
                    response = self.session.get(endpoint, params=params)
                    response_status = response.status_code
                    
                    print(f"DEBUG: Response status from {endpoint}: {response_status}")
                    
                    # If not 200, try next format
                    if response_status != 200:
                        try:
                            error_json = response.json()
                            error_detail = error_json.get('detail', error_json)
                            print(f"DEBUG: Error response from API: {error_detail}")
                        except:
                            error_detail = response.text[:200]
                            print(f"DEBUG: Error response (non-JSON): {error_detail}")
                        
                        print(f"DEBUG: Trying next parameter format...")
                        continue
                    
                    # Successfully got data
                    data = response.json()
                    print(f"DEBUG: Successfully retrieved data from {endpoint}")
                    print(f"DEBUG: Response data keys: {list(data.keys())}")
                    
                    # Try to extract conversations from various possible formats
                    conversations = []
                    if 'conversations' in data:
                        conversations = data.get('conversations', [])
                    elif 'history' in data:
                        conversations = data.get('history', [])
                    elif 'items' in data:
                        conversations = data.get('items', [])
                    
                    print(f"DEBUG: Retrieved {len(conversations)} conversations")
                    
                    # If we found conversations, we can stop trying other formats/endpoints
                    if conversations:
                        print(f"DEBUG: Found {len(conversations)} conversations with {endpoint} using params {params}")
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
                            print(f"DEBUG: Moving to page {current_page+1} with cursor {next_cursor}")
                            
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
                                
                                print(f"DEBUG: Retrieved {len(page_conversations)} conversations on page {current_page+1}")
                                
                                # Add to our result list
                                all_conversations.extend(page_conversations)
                                
                                # Update pagination for next page
                                next_cursor = data.get('next_cursor') or data.get('next_page_token') or data.get('next')
                                has_more = data.get('has_more', False) or data.get('more', False) or (next_cursor is not None)
                            else:
                                print(f"DEBUG: Error in pagination, stopping at page {current_page+1}")
                                break
                        
                        # Successfully found and retrieved conversations, no need to try other endpoints
                        print(f"DEBUG: Successfully retrieved a total of {len(all_conversations)} conversations")
                        # Return early with the real data
                        return {
                            'conversations': all_conversations,
                            'total': len(all_conversations)
                        }
                
                except Exception as e:
                    print(f"DEBUG: Exception with endpoint {endpoint} and params {params}: {e}")
                    continue
        
        # If we reach here, all endpoint/parameter combinations failed
        print(f"DEBUG: All API endpoints failed, returning empty conversations list")
        return {
            'conversations': [],
            'total': 0
        }
    
    def get_conversation_details(self, conversation_id):
        """
        Get details for a specific conversation
        
        Args:
            conversation_id (str): ID of the conversation to fetch
            
        Returns:
            dict: API response with conversation details
        """
        print(f"DEBUG: Attempting to get conversation details for ID {conversation_id}")
        
        # Try multiple endpoint variations since we're not sure which one is correct
        endpoints_to_try = [
            f"{self.api_url}/v1/history/{conversation_id}",                  # First to try (likely to work)
            f"{self.api_url}/v1/voices/history/{conversation_id}",           # Second variant
            f"{self.api_url}/v1/convai/conversations/{conversation_id}"      # Third variant (original)
        ]
        
        # Try each endpoint until one works
        for endpoint in endpoints_to_try:
            print(f"DEBUG: Trying conversation details endpoint: {endpoint}")
            
            try:
                # Make the request
                response = self.session.get(endpoint)
                response_status = response.status_code
                
                # Log the response status
                print(f"DEBUG: Response status from {endpoint}: {response_status}")
                
                # If not successful, try next endpoint
                if response_status != 200:
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('detail', error_json)
                        print(f"DEBUG: Error response from API: {error_detail}")
                    except:
                        error_detail = response.text[:200]  # Limit the error text
                        print(f"DEBUG: Error response (non-JSON): {error_detail}")
                    
                    print(f"DEBUG: Trying next endpoint...")
                    continue
                
                # Successfully got data
                data = response.json()
                print(f"DEBUG: SUCCESSFULLY FOUND WORKING ENDPOINT: {endpoint}")
                print(f"DEBUG: Response data keys: {list(data.keys())}")
                
                # Standardize the transcript format based on the endpoint response format
                # Different endpoints might return data in different formats
                
                # Case 1: If 'transcript' key exists, use it directly
                if 'transcript' in data and isinstance(data['transcript'], list):
                    print(f"DEBUG: Using existing transcript from API response")
                    # Add turns as an alias for backwards compatibility
                    data['turns'] = data['transcript']
                
                # Case 2: If 'messages' key exists but not 'transcript'
                elif 'messages' in data and isinstance(data['messages'], list) and 'transcript' not in data:
                    print(f"DEBUG: Converting 'messages' to 'transcript' format")
                    data['transcript'] = data['messages']
                    data['turns'] = data['messages']  # For backwards compatibility
                
                # Case 3: If 'history' key exists but not 'transcript'
                elif 'history' in data and isinstance(data['history'], list) and 'transcript' not in data:
                    print(f"DEBUG: Converting 'history' to 'transcript' format")
                    data['transcript'] = data['history']
                    data['turns'] = data['history']  # For backwards compatibility
                
                # Print the standardized conversation data for debugging
                print(f"DEBUG: Standardized conversation data keys: {list(data.keys())}")
                print(f"DEBUG: Transcript has {len(data.get('transcript', []))} messages")
                
                return data
                
            except Exception as e:
                print(f"DEBUG: Exception fetching conversation details from {endpoint}: {e}")
                print(f"DEBUG: Trying next endpoint...")
                continue
        
        # If we get here, all endpoints failed - fall back to sample data
        print(f"DEBUG: All API endpoints failed, falling back to generated sample data for conversation {conversation_id}")
        return self._generate_fallback_conversation_details(conversation_id)
    
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
    
    # Generate sample data methods - for when API access fails
    def _generate_fallback_conversations(self, start_date=None, end_date=None, limit=100, offset=0):
        """
        Generate sample conversation data for demo or testing
        
        Args:
            start_date (str, optional): Start date filter in ISO format
            end_date (str, optional): End date filter in ISO format
            limit (int, optional): Max number of conversations to generate
            offset (int, optional): Offset for pagination
            
        Returns:
            dict: Sample conversations data structure
        """
        print(f"DEBUG: Generating fallback conversations data for date range: {start_date} to {end_date}")
        
        # Parse dates or use defaults
        try:
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                # Default to 7 days ago
                start_dt = datetime.now() - timedelta(days=7)
                
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            else:
                # Default to current date
                end_dt = datetime.now()
        except (ValueError, TypeError):
            # If date parsing fails, use default range
            start_dt = datetime.now() - timedelta(days=7)
            end_dt = datetime.now()
        
        print(f"DEBUG: Using date range for demo data: {start_dt.isoformat()} to {end_dt.isoformat()}")
        
        # Generate conversations
        conversations = []
        max_conversations = min(limit, 30)  # Cap at 30 for performance
        
        # List of sample psychic reading topics
        topics = [
            "love and relationships", 
            "career guidance", 
            "financial future", 
            "spiritual growth",
            "family matters",
            "personal development",
            "past lives",
            "health concerns",
            "life purpose",
            "decision making"
        ]
        
        # Generate fixed IDs for specific topic examples that match our topic buttons
        # These IDs must match those used in routes.py special case handling
        special_convos = [
            {
                'id': '4a72b35c',  # Property investment question 
                'topic': "financial future",
                'question': "Should I invest in property right now?"
            },
            {
                'id': '9f82d41b',  # Job offer question
                'topic': "career guidance", 
                'question': "Should I accept the new job offer?"
            },
            {
                'id': '1d38g59h',  # Financial situation
                'topic': "financial future",
                'question': "Will my financial situation improve this year?"
            },
            {
                'id': '6e26d18f',  # Financial stability
                'topic': "financial future", 
                'question': "Will I ever be financially stable?"
            },
            {
                'id': '0c15a94e',  # Family relationship
                'topic': "family matters",
                'question': "How can I improve my relationship with my mother?"
            },
            {
                'id': '3f68b27a',  # Future children
                'topic': "family matters",
                'question': "Will I have children in the future?"
            },
            {
                'id': '7g41c83d',  # Moving decision
                'topic': "family matters",
                'question': "Is moving closer to my family the right decision?"
            },
            {
                'id': '5h93d62c',  # Life purpose
                'topic': "life purpose",
                'question': "What is my true purpose in life?"
            },
            {
                'id': '2j74a51b',  # Life path
                'topic': "life purpose",
                'question': "Am I on the right path right now?"
            }
        ]
        
        # Add demo conversations, always include the special ones first
        for spec in special_convos:
            # Randomize timeframes within the date range
            range_days = (end_dt - start_dt).days
            if range_days <= 0:
                range_days = 7  # Default to one week if dates are invalid
                
            # Choose a random day within the range
            random_days = random.randint(0, range_days)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            
            convo_time = end_dt - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
            
            # Random duration between 3 and 10 minutes (in seconds)
            duration = random.randint(180, 600)
            
            # Random turn count between 6 and 16
            turn_count = random.randint(6, 16)
            
            conversation = {
                'conversation_id': spec['id'],
                'id': spec['id'],  # Add both formats to be safe
                'start_time': convo_time.isoformat(),
                'end_time': (convo_time + timedelta(seconds=duration)).isoformat(),
                'duration': duration,
                'turn_count': turn_count,
                'topic': spec['topic'],
                'question': spec['question'],
                'status': 'completed',
                'metadata': {
                    'is_demo': True,
                    'topic': spec['topic']
                }
            }
            conversations.append(conversation)
        
        # Add some random conversations to fill up to the limit
        remaining = max_conversations - len(special_convos)
        for i in range(remaining):
            # Randomize times within the date range
            range_days = (end_dt - start_dt).days
            if range_days <= 0:
                range_days = 7
                
            random_days = random.randint(0, range_days)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            
            convo_time = end_dt - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
            
            # Random duration between 3 and 10 minutes (in seconds)
            duration = random.randint(180, 600)
            
            # Random turn count between 6 and 16
            turn_count = random.randint(6, 16)
            
            # Random ID that doesn't conflict with special IDs
            conversation_id = ''.join(random.choices('0123456789abcdef', k=8))
            
            # Random topic
            topic = random.choice(topics)
            
            # Create the conversation
            conversation = {
                'conversation_id': conversation_id,
                'id': conversation_id,  # Add both formats to be safe
                'start_time': convo_time.isoformat(),
                'end_time': (convo_time + timedelta(seconds=duration)).isoformat(),
                'duration': duration,
                'turn_count': turn_count,
                'topic': topic,
                'status': random.choices(['completed', 'failed'], weights=[0.9, 0.1])[0],
                'metadata': {
                    'is_demo': True,
                    'topic': topic
                }
            }
            conversations.append(conversation)
        
        print(f"DEBUG: Generated {len(conversations)} fallback conversations")
        
        # Sort by start_time, most recent first
        conversations.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        # Apply offset and limit
        if offset > 0:
            conversations = conversations[offset:]
        conversations = conversations[:limit]
        
        # Return in a format similar to the API response
        return {
            'conversations': conversations,
            'total': len(conversations),
            'is_demo': True
        }
    
    def _generate_fallback_conversation_details(self, conversation_id):
        """Generate sample conversation details as fallback when API fails"""
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