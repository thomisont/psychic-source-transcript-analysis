import pandas as pd
from datetime import datetime, timedelta
import logging

class DataProcessor:
    @staticmethod
    def process_conversations(conversations_data):
        """
        Process the raw conversation data from the API into a pandas DataFrame
        
        Args:
            conversations_data (dict): Raw conversation data from the API
            
        Returns:
            DataFrame: Processed conversation data
        """
        if not conversations_data:
            logging.warning("Received empty conversations_data")
            return pd.DataFrame()
            
        if 'conversations' not in conversations_data:
            logging.warning("No 'conversations' key in data, raw data keys: " + str(conversations_data.keys()))
            return pd.DataFrame()
            
        conversations = conversations_data['conversations']
        
        if not conversations:
            logging.warning("Empty conversations list received")
            return pd.DataFrame()
            
        # Log data for debugging
        logging.info(f"Processing {len(conversations)} conversations")
        if conversations:
            logging.info(f"First conversation keys: {list(conversations[0].keys())}")
            
        # Extract relevant fields
        processed_data = []
        for conv in conversations:
            # Handle both id and conversation_id fields
            conv_id = conv.get('conversation_id', conv.get('id', ''))
            
            # Ensure we have a valid ID before processing
            if not conv_id:
                continue
            
            # Extract Unix timestamp for start time
            unix_start_time = conv.get('start_time_unix_secs')
            if unix_start_time is None:
                # Look for timestamp in metadata as fallback
                metadata = conv.get('metadata', {})
                unix_start_time = metadata.get('start_time_unix_secs')
            
            # Convert Unix timestamp to datetime
            start_time = None
            if unix_start_time:
                try:
                    start_time = datetime.fromtimestamp(unix_start_time)
                    logging.info(f"Converted start_time_unix_secs {unix_start_time} to {start_time}")
                except (ValueError, TypeError) as e:
                    logging.warning(f"Failed to convert timestamp {unix_start_time}: {e}")
                    start_time = None
            
            # Get duration and calculate end time
            duration_seconds = conv.get('call_duration_secs', 0)
            if duration_seconds is None:
                # Look in metadata as fallback
                metadata = conv.get('metadata', {})
                duration_seconds = metadata.get('call_duration_secs', 0)
            
            # Calculate end time based on start time and duration
            end_time = None
            if start_time and duration_seconds:
                end_time = start_time + timedelta(seconds=duration_seconds)
            
            # Count messages or turns if available
            message_count = conv.get('message_count', 0)
            turn_count = conv.get('turn_count', message_count)
            
            # Get status, converting API-specific status values if needed
            status = conv.get('status', 'unknown')
            
            # Create a standardized record
            processed_conv = {
                'conversation_id': conv_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration_seconds,
                'turn_count': turn_count,
                'status': status,
            }
            processed_data.append(processed_conv)
            
        # Convert to DataFrame
        df = pd.DataFrame(processed_data)
        
        # Remove any rows with missing start_time
        df = df.dropna(subset=['start_time'])
        
        # Sort by start_time in ascending order
        if 'start_time' in df.columns and not df.empty:
            df = df.sort_values(by='start_time', ascending=True)
        
        logging.info(f"Processed {len(df)} conversations successfully")
        
        if not df.empty:
            logging.info(f"DataFrame columns: {list(df.columns)}")
            logging.info(f"First row: {df.iloc[0].to_dict() if len(df) > 0 else 'No rows'}")
            
        return df
        
    @staticmethod
    def process_conversation_details(conversation_details):
        """
        Process the detailed conversation data from the API into a structured format
        
        Args:
            conversation_details (dict): Raw conversation details from the API
            
        Returns:
            dict: Processed conversation details with transcript
        """
        if not conversation_details:
            return {}
            
        # Log the keys for debugging
        print(f"DEBUG: Conversation details keys: {list(conversation_details.keys())}")
        
        # Handle ElevenLabs API format
        if 'conversation_id' in conversation_details and 'transcript' in conversation_details:
            print(f"DEBUG: Processing ElevenLabs conversation details format")
            
            # Extract key fields
            conversation_id = conversation_details.get('conversation_id', '')
            status = conversation_details.get('status', 'completed')
            
            # Extract metadata
            metadata = conversation_details.get('metadata', {})
            print(f"DEBUG: Conversation metadata: {metadata.keys() if isinstance(metadata, dict) else 'Not a dict'}")
            
            # Convert UNIX timestamp to datetime if available
            start_time = None
            if 'start_time_unix_secs' in metadata:
                start_time_unix = metadata.get('start_time_unix_secs')
                if start_time_unix:
                    start_time = datetime.fromtimestamp(start_time_unix)
                    print(f"DEBUG: Converted start_time_unix_secs {start_time_unix} to {start_time}")
                
            # Calculate end time based on start time and duration
            end_time = None
            duration = metadata.get('call_duration_secs', 0)
            if start_time and duration:
                end_time = start_time + timedelta(seconds=duration)
                print(f"DEBUG: Calculated end_time as {end_time} based on duration {duration}")
            
            # Extract additional metadata - handle cost which can be either an integer or a dictionary
            cost = metadata.get('cost', 0)
            if isinstance(cost, dict):
                cost = cost.get('amount', 0)
            print(f"DEBUG: Extracted cost: {cost} credits")
            
            # Get analysis summary if available
            analysis = conversation_details.get('analysis', {})
            print(f"DEBUG: Analysis data keys: {list(analysis.keys()) if isinstance(analysis, dict) else 'Not a dict'}")
            
            # Try to extract summary from multiple possible fields
            summary = ''
            if isinstance(analysis, dict):
                # Check both possible field names for summary
                if 'transcript_summary' in analysis:
                    summary = analysis.get('transcript_summary', '')
                elif 'summary' in analysis:
                    summary = analysis.get('summary', '')
                
                print(f"DEBUG: Extracted summary: {summary[:100]}..." if summary else "DEBUG: No summary available")
            
            print(f"DEBUG: Extracted timestamps: start={start_time}, end={end_time}, duration={duration}")
            
            # Process transcript into turns format
            transcript_data = conversation_details.get('transcript', [])
            print(f"DEBUG: Processing transcript with {len(transcript_data)} messages")
            
            # Log first transcript message for debugging
            if transcript_data and len(transcript_data) > 0:
                first_msg = transcript_data[0]
                print(f"DEBUG: First transcript message keys: {list(first_msg.keys()) if isinstance(first_msg, dict) else 'Not a dict'}")
                
                # Get the role or sender_type to determine if it's the agent or user
                if 'role' in first_msg:
                    print(f"DEBUG: First message role: {first_msg.get('role', 'unknown')}")
                elif 'sender_type' in first_msg:
                    print(f"DEBUG: First message sender_type: {first_msg.get('sender_type', 'unknown')}")
                
                # Try to extract the message content
                text = first_msg.get('text', '')
                message_content = first_msg.get('message', '')
                if isinstance(message_content, dict) and 'content' in message_content:
                    message_content = message_content.get('content', '')
                elif isinstance(message_content, str):
                    pass  # Keep as is
                else:
                    message_content = ''
                    
                content = first_msg.get('content', '')
                print(f"DEBUG: First message text extraction attempts: text={bool(text)}, message={bool(message_content)}, content={bool(content)}")
                
                final_text = text or message_content or content or 'No text found'
                print(f"DEBUG: First message text: {final_text[:100]}...")
            
            transcript = []
            
            for i, message in enumerate(transcript_data):
                # Determine if message is from agent or user
                is_agent = False
                if 'role' in message:
                    is_agent = message.get('role') == 'assistant' or message.get('role') == 'agent'
                elif 'sender_type' in message:
                    is_agent = message.get('sender_type') == 'agent'
                
                # Check for more explicit agent/assistant indicators
                text_content = message.get('text', '') or message.get('message', '') or message.get('content', '')
                if isinstance(text_content, str) and text_content.startswith("Welcome to Psychic Source"):
                    is_agent = True
                
                # Use custom names for better readability
                speaker = "Lily" if is_agent else "Curious Caller"
                
                # Get the message text - try multiple possible fields
                text = message.get('text', '')
                
                # Try to get text from message field which might be a string or dict
                message_content = message.get('message', '')
                if isinstance(message_content, dict) and 'content' in message_content:
                    message_content = message_content.get('content', '')
                elif isinstance(message_content, str):
                    pass  # Keep as is
                else:
                    message_content = ''
                
                # Try content field directly
                content = message.get('content', '')
                
                # Combine the possible sources with fallbacks
                final_text = text or message_content or content or 'No message content'
                
                # Get timestamp if available (try multiple formats)
                timestamp = None
                if 'created_at' in message:
                    timestamp = message.get('created_at')
                elif 'timestamp' in message:
                    timestamp = message.get('timestamp')
                elif 'time' in message:
                    timestamp = message.get('time')
                elif 'unix_time' in message:
                    unix_time = message.get('unix_time')
                    if unix_time:
                        timestamp = datetime.fromtimestamp(unix_time)
                elif 'time_in_call_secs' in message:
                    # If only relative time is available and we have a start time
                    time_in_call = message.get('time_in_call_secs')
                    if time_in_call is not None and start_time:
                        timestamp = start_time + timedelta(seconds=time_in_call)
                
                turn = {
                    'speaker': speaker,
                    'is_agent': is_agent,  # Add explicit is_agent field
                    'text': final_text,
                    'timestamp': timestamp
                }
                
                transcript.append(turn)
                
                # Debug log for each message
                print(f"DEBUG: Message {i+1}: speaker={speaker}, is_agent={is_agent}, text_length={len(final_text)}, has_timestamp={timestamp is not None}")
            
            # Extract client data from metadata
            client_data = {}
            user_info = metadata.get('user_info', {})
            if isinstance(user_info, dict):
                client_data.update(user_info)
            
            # Look for any client-related fields in the metadata
            for key, value in metadata.items():
                if any(term in key.lower() for term in ['user', 'client', 'customer', 'caller']):
                    client_data[key] = value
            
            # Look for client data in the conversation_details directly
            client_data_direct = conversation_details.get('client_data', {})
            if isinstance(client_data_direct, dict):
                client_data.update(client_data_direct)
            
            # Create structured response
            processed_details = {
                'conversation_id': conversation_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'status': status,
                'cost': cost,
                'summary': summary,
                'transcript': transcript,
                'metadata': metadata,
                'client_data': client_data
            }
            
            print(f"DEBUG: Processed conversation: ID={conversation_id}, {len(transcript)} turns, cost={cost} credits")
            return processed_details
            
        # Fall back to original format
        turns = conversation_details.get('turns', [])
        
        # Extract transcript
        transcript = []
        for turn in turns:
            speaker = "Agent" if turn.get('is_agent') else "User"
            transcript.append({
                'speaker': speaker,
                'text': turn.get('text', ''),
                'timestamp': DataProcessor._parse_timestamp(turn.get('timestamp'))
            })
            
        # Create structured response
        processed_details = {
            'conversation_id': conversation_details.get('id'),
            'start_time': DataProcessor._parse_timestamp(conversation_details.get('start_time')),
            'end_time': DataProcessor._parse_timestamp(conversation_details.get('end_time')),
            'duration': conversation_details.get('duration'),
            'status': conversation_details.get('status'),
            'transcript': transcript
        }
        
        return processed_details
    
    @staticmethod
    def _parse_timestamp(timestamp_str):
        """Helper method to parse API timestamps"""
        if not timestamp_str:
            return None
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                return None 