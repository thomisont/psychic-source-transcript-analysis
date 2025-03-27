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
            
        # Handle different possible formats returned by the API
        conversations = None
        
        # Check all possible keys where conversations might be stored
        if 'conversations' in conversations_data:
            conversations = conversations_data['conversations']
            logging.info("Using 'conversations' key from API response")
        elif 'history' in conversations_data:
            conversations = conversations_data['history']
            logging.info("Using 'history' key from API response")
        elif 'items' in conversations_data:
            conversations = conversations_data['items']
            logging.info("Using 'items' key from API response")
        else:
            # If no recognized structure, log the available keys
            logging.warning("No recognized conversation data structure, raw data keys: " + str(conversations_data.keys()))
            # Try using the data directly if it's a list
            if isinstance(conversations_data, list):
                conversations = conversations_data
                logging.info("Using list data directly from API response")
            else:
                return pd.DataFrame()
            
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
            
            # Try alternate field names if neither standard field exists
            if not conv_id:
                # Try additional possible fields for ID
                conv_id = conv.get('history_item_id', conv.get('call_id', conv.get('session_id', '')))
            
            # Ensure we have a valid ID before processing
            if not conv_id:
                continue
            
            # Extract timestamp for start time - try multiple possible fields
            start_time = None
            
            # Handle start_time_unix_secs which appears in the actual API response
            if 'start_time_unix_secs' in conv and conv['start_time_unix_secs']:
                try:
                    unix_time = int(conv['start_time_unix_secs'])
                    start_time = datetime.fromtimestamp(unix_time)
                    logging.info(f"Converted start_time_unix_secs {unix_time} to {start_time}")
                except (ValueError, TypeError) as e:
                    logging.warning(f"Failed to convert start_time_unix_secs: {e}")
            
            # Try direct timestamp fields if start_time_unix_secs didn't work
            if start_time is None and 'start_time' in conv and conv['start_time']:
                try:
                    # Handle both string timestamps and objects
                    if isinstance(conv['start_time'], str):
                        start_time = pd.to_datetime(conv['start_time'])
                    else:
                        start_time = conv['start_time']
                    logging.info(f"Used explicit start_time field: {start_time}")
                except Exception as e:
                    logging.warning(f"Failed to parse explicit start_time: {e}")
            
            # Try Unix timestamp fields if no direct timestamp
            if start_time is None:
                # Try multiple possible unix timestamp field names
                unix_fields = ['timestamp', 'created_at_unix', 'start_unix']
                
                for field in unix_fields:
                    unix_time = conv.get(field)
                    if unix_time is not None:
                        try:
                            start_time = datetime.fromtimestamp(int(unix_time))
                            logging.info(f"Converted {field} {unix_time} to {start_time}")
                            break
                        except (ValueError, TypeError) as e:
                            logging.warning(f"Failed to convert timestamp {unix_time} from {field}: {e}")
            
            # Look in metadata as a last resort
            if start_time is None:
                metadata = conv.get('metadata', {})
                for field in unix_fields:
                    unix_time = metadata.get(field)
                    if unix_time is not None:
                        try:
                            start_time = datetime.fromtimestamp(int(unix_time))
                            logging.info(f"Converted metadata.{field} {unix_time} to {start_time}")
                            break
                        except (ValueError, TypeError) as e:
                            logging.warning(f"Failed to convert metadata timestamp {unix_time} from {field}: {e}")
            
            # Get duration and calculate end time - try multiple possible fields
            duration_seconds = None
            
            # First, try call_duration_secs from actual API response
            if 'call_duration_secs' in conv:
                duration_seconds = conv['call_duration_secs']
            else:
                # Fall back to other field names
                duration_fields = ['duration', 'duration_seconds', 'call_duration']
                
                for field in duration_fields:
                    if field in conv and conv[field] is not None:
                        duration_seconds = conv[field]
                        break
                
                # If no duration in main fields, check metadata
                if duration_seconds is None:
                    metadata = conv.get('metadata', {})
                    for field in duration_fields:
                        if field in metadata and metadata[field] is not None:
                            duration_seconds = metadata[field]
                            break
            
            # Convert string durations if needed
            if isinstance(duration_seconds, str):
                try:
                    duration_seconds = int(duration_seconds)
                except (ValueError, TypeError):
                    duration_seconds = 0
            
            # Ensure we have a numeric value
            duration_seconds = int(duration_seconds) if duration_seconds is not None else 0
            
            # Calculate end time based on start time and duration
            end_time = None
            if start_time and duration_seconds:
                end_time = start_time + timedelta(seconds=duration_seconds)
            
            # Count messages or turns if available
            message_count = 0
            
            # Try message_count from actual API response first
            if 'message_count' in conv and conv['message_count'] is not None:
                try:
                    message_count = int(conv['message_count'])
                except (ValueError, TypeError):
                    message_count = 0
            else:
                # Fall back to other field names
                message_fields = ['turn_count', 'messages_count', 'num_messages']
                
                for field in message_fields:
                    if field in conv and conv[field] is not None:
                        try:
                            message_count = int(conv[field])
                            break
                        except (ValueError, TypeError):
                            continue
                
                # Try to count messages directly if available
                if message_count == 0 and 'messages' in conv and isinstance(conv['messages'], list):
                    message_count = len(conv['messages'])
                elif message_count == 0 and 'transcript' in conv and isinstance(conv['transcript'], list):
                    message_count = len(conv['transcript'])
            
            # Get status, try call_successful from actual API response first
            status = None
            
            if 'call_successful' in conv:
                status = 'done' if conv['call_successful'] else 'failed'
            elif 'status' in conv:
                status = conv['status']
            else:
                # Fall back to other status fields
                status_fields = ['call_status', 'state']
                
                for field in status_fields:
                    if field in conv and conv[field] is not None:
                        status = conv[field]
                        break
            
            # Default status if none found
            status = status or 'unknown'
            
            # Try to normalize status values to a standard set
            status = status.lower() if isinstance(status, str) else str(status)
            
            # Map various status values to standard ones
            status_map = {
                'completed': 'done',
                'complete': 'done',
                'finished': 'done',
                'success': 'done',
                'successful': 'done',
                'done': 'done',
                'true': 'done',  # For call_successful=true
                'in_progress': 'in_progress',
                'ongoing': 'in_progress',
                'running': 'in_progress',
                'active': 'in_progress',
                'failed': 'failed',
                'error': 'failed',
                'terminated': 'failed',
                'cancelled': 'failed',
                'aborted': 'failed',
                'false': 'failed'  # For call_successful=false
            }
            
            status = status_map.get(status, status)
            
            # Create a standardized record
            processed_conv = {
                'conversation_id': conv_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration_seconds,
                'turn_count': message_count,
                'status': status,
                # Include additional fields from the actual API response if available
                'agent_id': conv.get('agent_id'),
                'agent_name': conv.get('agent_name')
            }
            processed_data.append(processed_conv)
            
        # Convert to DataFrame
        df = pd.DataFrame(processed_data)
        
        # Remove any rows with missing start_time
        df = df.dropna(subset=['start_time'])
        
        # Sort by start_time in descending order (most recent first)
        if 'start_time' in df.columns and not df.empty:
            df = df.sort_values(by='start_time', ascending=False)
        
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