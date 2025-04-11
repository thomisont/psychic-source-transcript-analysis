"""
Conversation service for handling conversation data retrieval and processing using Supabase.
This is a refactored version that prioritizes Supabase access over direct database queries.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
from typing import Dict, List, Optional, Any, Union
from dateutil import parser # For robust date parsing
import time
from collections import Counter
import pytz  # Import pytz

# Add system path to include tools directory
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import Supabase client
try:
    from tools.supabase_client import SupabaseClient
except ImportError:
    logging.error("Could not import SupabaseClient - this is required for Supabase integration")
    SupabaseClient = None

class SupabaseConversationService:
    """Service for handling conversation data retrieval and processing from Supabase."""

    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """
        Initialize the conversation service with Supabase client.
        Accepts an optional pre-initialized SupabaseClient instance.
        """
        self.cache = {}  # Simple in-memory cache
        self.supabase = supabase_client # Store the passed client
        
        # Determine initialization status based on the provided client
        if self.supabase and self.supabase.client:
            self.initialized = True
            logging.info("SupabaseConversationService initialized successfully with provided client.")
        else:
            logging.error("SupabaseConversationService initialized WITHOUT a valid Supabase client.")
            self.initialized = False
        
    def clear_cache(self):
        """Clear all internal caches to ensure fresh data retrieval."""
        self.cache = {}
        logging.info("Conversation service cache cleared")
    
    def get_conversation_count(self, start_date=None, end_date=None) -> int:
        """Gets the count of conversations within a date range using standard client methods."""
        if not self.initialized or not self.supabase or not self.supabase.client:
             logging.error("Supabase client not available in get_conversation_count")
             return 0

        try:
            query = self.supabase.client.table('conversations').select("*", count='exact')
            
            start_dt_iso = None
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                start_dt_iso = start_dt.isoformat()
                query = query.gte('created_at', start_dt_iso)
            
            end_dt_iso = None
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                end_dt_iso = end_dt.isoformat()
                query = query.lte('created_at', end_dt_iso)
                
            # Execute the query to get the count
            response = query.execute()
            
            count = response.count
            logging.info(f"Retrieved count {count} for conversations ({start_dt_iso} to {end_dt_iso}) using standard method.")
            return count if count is not None else 0
            
        except Exception as e:
            logging.error(f"Error in get_conversation_count using standard method: {e}", exc_info=True)
            return 0
    
    def get_conversations(self, start_date=None, end_date=None, limit=100, offset=0) -> Dict[str, Any]:
        """Gets conversations filtered by message timestamp range, using a DB function."""
        if not self.initialized or not self.supabase or not self.supabase.client:
             logging.error("Supabase client not available in get_conversations")
             return {"conversations": [], "total_count": 0, "error": "Supabase client not initialized"}

        try:
            # --- Convert dates to ISO strings for the function --- 
            start_dt_iso = None
            end_dt_iso = None
            try:
                if start_date:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    start_dt_iso = start_dt.isoformat()
                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                    end_dt_iso = end_dt.isoformat()
            except ValueError as date_parse_err:
                 logging.error(f"Invalid date format: {date_parse_err}")
                 return {"conversations": [], "total_count": 0, "error": "Invalid date format provided"}

            # --- Call the RPC function to get relevant conversation IDs --- 
            logging.info(f"Calling RPC get_conversation_ids_in_range with start={start_dt_iso}, end={end_dt_iso}")
            rpc_params = {
                'start_iso': start_dt_iso,
                'end_iso': end_dt_iso
            }
            # Handle None dates - pass them as None/null to the function?
            # Adjust params if the function expects nulls or specific defaults
            if start_dt_iso is None:
                 # Assuming the function handles NULL start, or set a very old date?
                 # For now, let's pass None which should become NULL
                 rpc_params['start_iso'] = None 
            if end_dt_iso is None:
                 # Assuming the function handles NULL end, or set future date?
                 rpc_params['end_iso'] = None 
            
            id_response = self.supabase.client.rpc('get_conversation_ids_in_range', rpc_params).execute()
            
            if not hasattr(id_response, 'data') or id_response.data is None:
                 logging.warning(f"RPC call get_conversation_ids_in_range returned no data or unexpected structure for range {start_date}-{end_date}")
                 return {"conversations": [], "total_count": 0} # Return empty if no IDs found

            conversation_ids_data = id_response.data
            conversation_ids = [item['conversation_id'] for item in conversation_ids_data if 'conversation_id' in item]
            total_count = len(conversation_ids)
            logging.info(f"Found {total_count} matching conversation IDs for range {start_date}-{end_date}")

            if not conversation_ids:
                 return {"conversations": [], "total_count": 0}

            # --- Apply pagination to the list of IDs --- 
            paginated_ids = conversation_ids[offset : offset + limit]
            
            if not paginated_ids:
                logging.info(f"No conversations for the requested page (offset={offset}, limit={limit}) within the date range.")
                return {"conversations": [], "total_count": total_count} # Return total count but empty page

            # --- Fetch full conversation data for the paginated IDs --- 
            logging.info(f"Fetching full data for {len(paginated_ids)} conversations on current page...")
            query = self.supabase.client.table('conversations').select(
                "id, external_id, title, created_at, status, messages(*)"
            ).in_('id', paginated_ids) # Filter by the list of IDs found
            
            # Apply ordering if needed (e.g., by created_at desc for consistency)
            # Note: We can't easily order by message timestamps here anymore
            query = query.order('created_at', desc=True)
            
            # Execute query for full data
            response = query.execute()
            result_data = response.data
            logging.info(f"Fetched {len(result_data)} full conversation records for the current page.")

            # --- Process results (same as before) --- 
            conversations = []
            for row in result_data:
                messages = row.get('messages', [])
                
                # Format transcript similar to get_conversation_details
                transcript = []
                if messages:
                    transcript = [
                        {
                            # Determine role based on speaker or role field
                            'role': 'user' if msg.get('speaker') == 'Curious Caller' or msg.get('role') == 'user' else 'assistant', 
                            # Extract content flexibly
                            'content': msg.get('text') or msg.get('content'), 
                            'timestamp': msg.get('timestamp'),
                            # Include other message fields if needed? e.g., msg.get('id')
                        }
                        for msg in messages
                        if msg.get('text') or msg.get('content') # Ensure message has content
                    ]

                start_time_str = None # Use ISO string from DB
                end_time_str = None
                start_time_dt = None
                end_time_dt = None

                if messages:
                    # Extract and parse timestamps safely from the already fetched messages
                    timestamps = []
                    for m in messages:
                         ts_str = m.get('timestamp')
                         if ts_str:
                              try:
                                   # Ensure timezone info, default to UTC if missing
                                   ts_dt = parser.parse(ts_str)
                                   if ts_dt.tzinfo is None:
                                        ts_dt = ts_dt.replace(tzinfo=timezone.utc)
                                   timestamps.append(ts_dt)
                              except (ValueError, TypeError) as ts_parse_err:
                                   logging.warning(f"Could not parse message timestamp '{ts_str}': {ts_parse_err}")
                                   
                    if timestamps:
                        timestamps.sort()
                        start_time_dt = timestamps[0]
                        end_time_dt = timestamps[-1]
                        # Store as ISO strings for consistency if needed later, or keep as datetime
                        start_time_str = start_time_dt.isoformat()
                        end_time_str = end_time_dt.isoformat()

                
                duration = None
                # Calculate duration ONLY if we have valid datetime objects
                if start_time_dt and end_time_dt:
                    try:
                        duration_delta = end_time_dt - start_time_dt
                        duration = int(duration_delta.total_seconds())
                    except Exception as duration_calc_err:
                         logging.warning(f"Could not calculate duration: {duration_calc_err}")

                # Conversation data now includes the transcript
                conversation_data = {
                    'conversation_id': row.get('external_id'),
                    'title': row.get('title') or "Untitled",
                    'start_time': row.get('created_at'), # Use conversation created_at
                    'status': row.get('status'),
                    'message_count': len(messages), # Count from fetched messages
                    'duration': duration, # Calculated above
                    'sentiment_score': 0.0, # Placeholder for analysis
                    'transcript': transcript # ADDED formatted transcript
                    # Consider adding raw 'messages' if needed elsewhere?
                    # 'messages': messages 
                }
                conversations.append(conversation_data)
            
            return {
                "conversations": conversations,
                "total_count": total_count
            }
            
        except Exception as e:
            logging.error(f"Error in get_conversations using standard method: {e}", exc_info=True)
            return {"conversations": [], "total_count": 0, "error": str(e)}
    
    def get_conversation_details(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details for a specific conversation using standard client methods.
        Uses a two-step query: first fetch conversation, then fetch messages."""
        if not self.initialized or not self.supabase or not self.supabase.client:
             logging.error("Supabase client not available in get_conversation_details")
             return None

        try:
            # Step 1: Fetch the conversation by external_id, including cost_credits AND summary
            logging.info(f"Fetching conversation details for external_id: {conversation_id}")
            conv_response = self.supabase.client.table('conversations') \
                        .select("id, external_id, title, created_at, status, cost_credits, summary") \
                        .eq('external_id', str(conversation_id))\
                        .limit(1)\
                        .maybe_single()\
                        .execute()
                        
            conversation = conv_response.data
            
            # Log the raw conversation data to see available columns
            if not conversation:
                logging.warning(f"Conversation with external_id {conversation_id} not found.")
                return None
            
            # Get the internal primary key ID for fetching messages
            internal_conv_id = conversation.get('id')
            if not internal_conv_id:
                 logging.error(f"Conversation {conversation_id} found but missing internal ID.")
                 return None # Or handle as an error?

            # Step 2: Fetch associated messages, ordered by timestamp
            logging.info(f"Fetching messages for internal conversation ID: {internal_conv_id}")
            messages_response = self.supabase.client.table('messages')\
                                  .select("*")\
                                  .eq('conversation_id', internal_conv_id)\
                                  .order('timestamp', desc=False)\
                                  .execute()
                                  
            messages = messages_response.data if messages_response.data else []
            logging.info(f"Fetched {len(messages)} messages for conversation {conversation_id}")

            # Construct response (same logic as before, but messages are from the second query)
            transcript = [
                {
                    'role': 'user' if msg.get('speaker') == 'Curious Caller' else 'assistant',
                    'content': msg.get('text'),
                    'timestamp': msg.get('timestamp'),
                }
                for msg in messages
            ]
            
            start_time = None
            end_time = None
            if messages:
                timestamps = sorted([m['timestamp'] for m in messages if m.get('timestamp')])
                if timestamps:
                    start_time = timestamps[0]
                    end_time = timestamps[-1]
            
            duration = None
            if start_time and end_time:
                try:
                    # Ensure timestamps are parsed correctly before subtraction
                    start_dt = parser.parse(start_time)
                    end_dt = parser.parse(end_time)
                    # Make timezone-aware if necessary (assuming UTC if naive)
                    if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=timezone.utc)
                    if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=timezone.utc)
                    
                    duration_delta = end_dt - start_dt
                    duration = int(duration_delta.total_seconds())
                except Exception as parse_err:
                     logging.warning(f"Could not parse timestamps for duration calculation: {start_time}, {end_time} - Error: {parse_err}")
            
            conversation_data = {
                'conversation_id': conversation.get('external_id'),
                'id': conversation.get('id'), # Internal ID
                'start_time': conversation.get('created_at'), # Conversation start
                'status': conversation.get('status'),
                'title': conversation.get('title') or "Untitled Conversation",
                'messages': messages, # Fetched separately
                'transcript': transcript,
                'duration': duration,
                'cost': conversation.get('cost_credits'), # Change key to 'cost'
                'summary': conversation.get('summary') # ADD summary field
            }
            
            logging.info(f"Successfully retrieved details for conversation {conversation_id}")
            return conversation_data
            
        except Exception as e:
            logging.error(f"Error in get_conversation_details (two-step query): {e}", exc_info=True)
            return None # Return None on any exception
            
    def get_dashboard_stats(self, start_date: str | None = None, end_date: str | None = None) -> dict:
        """
        Fetches aggregated dashboard statistics by calling the Supabase RPC function
        'get_message_activity_in_range'.

        This function handles the core data aggregation on the database side.

        Args:
            start_date: Optional start date in 'YYYY-MM-DD' format.
            end_date: Optional end date in 'YYYY-MM-DD' format.

        Returns:
            A dictionary containing various aggregated statistics (activity by hour/day,
            daily volume, daily average duration, total conversations, average duration,
            peak hour) or an error dictionary if the RPC call fails.
            Example success structure:
            {
                'activity_by_hour': { '0': 10, '1': 5, ... },
                'activity_by_day': { '0': 50, '1': 60, ... }, // Monday=0
                'daily_volume': { '2023-10-26': 25, '2023-10-27': 30, ... },
                'daily_avg_duration': { '2023-10-26': 120.5, '2023-10-27': 180.0, ... }, // Seconds
                'total_conversations_period': 55,
                'avg_duration_seconds': 150.25,
                'peak_time_hour': 14
            }
            Example error structure:
            { 'error': 'Description of error' }
        """
        try:
            logging.info(f"Calling Supabase RPC get_message_activity_in_range with start: {start_date}, end: {end_date}")
            # Prepare parameters for the RPC call. Pass None directly if dates are not provided.
            params = {'start_iso': start_date, 'end_iso': end_date}

            # Execute the Supabase function
            response = self.supabase.client.rpc('get_message_activity_in_range', params).execute()
            logging.debug(f"Raw response from get_message_activity_in_range: {response}")

            if not response.data:
                logging.warning("Received empty data from get_message_activity_in_range RPC.")
                # Return a default structure indicating no data, matching expected keys by frontend
                return {
                    'activity_by_hour': {}, 'activity_by_day': {}, 'daily_volume': {},
                    'daily_avg_duration': {}, 'total_conversations_period': 0,
                    'avg_duration_seconds': 0, 'peak_time_hour': None,
                    'distinct_conversation_ids': [], # Ensure all expected keys are present
                    'avg_cost_credits': 0.0 # Add missing key with default value
                }


            # The RPC function returns the JSON object directly in response.data
            stats_data = response.data

            # Basic validation/logging of received data
            if not isinstance(stats_data, dict):
                 logging.error(f"Unexpected data type from RPC: {type(stats_data)}. Data: {stats_data}")
                 return {'error': 'Invalid data format received from database function.'}

            logging.info(f"Successfully fetched stats from RPC: {list(stats_data.keys())}")


            # --- Data Cleaning and Defaulting ---
            # Ensure all expected top-level keys exist, providing empty defaults.
            # The frontend JS expects these keys.
            defaults = {
                'activity_by_hour': {}, 'activity_by_day': {}, 'daily_volume': {},
                'daily_avg_duration': {}, 'total_conversations_period': 0,
                'distinct_conversation_ids': [], 'avg_duration_seconds': 0,
                'peak_time_hour': None
            }
            for key, default_value in defaults.items():
                stats_data.setdefault(key, default_value)

            # Ensure numeric types are correct and handle None/null from JSON
            stats_data['total_conversations_period'] = int(stats_data.get('total_conversations_period') or 0)
            stats_data['avg_duration_seconds'] = round(float(stats_data.get('avg_duration_seconds') or 0.0))
            # peak_time_hour can be null if no activity
            peak_hour = stats_data.get('peak_time_hour')
            stats_data['peak_time_hour'] = int(peak_hour) if peak_hour is not None else None

             # Ensure nested dictionaries are actual dictionaries
            for key in ['activity_by_hour', 'activity_by_day', 'daily_volume', 'daily_avg_duration']:
                if not isinstance(stats_data[key], dict):
                    logging.warning(f"Correcting non-dict value for key '{key}': {stats_data[key]}")
                    stats_data[key] = {}


            # --- Calculate Average Cost (Requires separate query) ---
            distinct_ids_for_cost = stats_data.get('distinct_conversation_ids')
            avg_cost_credits = 0.0

            if distinct_ids_for_cost:
                try:
                    logging.debug(f"Fetching cost_credits for {len(distinct_ids_for_cost)} conversation IDs from RPC result.")
                    # Fetch cost_credits for the specific conversations identified by the RPC
                    cost_response = self.supabase.client.table('conversations') \
                        .select('id, cost_credits') \
                        .in_('id', distinct_ids_for_cost) \
                        .execute()

                    if cost_response.data:
                        total_cost = 0
                        num_convs_with_cost = 0
                        for conv in cost_response.data:
                            cost = conv.get('cost_credits')
                            if cost is not None:
                                try:
                                    total_cost += float(cost) # Use float for potential decimal costs
                                    num_convs_with_cost += 1
                                except (ValueError, TypeError):
                                    logging.warning(f"Could not convert cost_credits '{cost}' to float for conv {conv.get('id')}")
                        
                        if num_convs_with_cost > 0:
                            avg_cost_credits = total_cost / num_convs_with_cost
                        logging.info(f"Calculated average cost: {avg_cost_credits} from {num_convs_with_cost} conversations.")
                    else:
                        logging.warning("No cost data found for the specified conversation IDs.")
                except APIError as e:
                     logging.error(f"Supabase API error fetching cost data: {e}", exc_info=True)
                     # Keep avg_cost_credits as 0.0 if cost fetch fails
                except Exception as e:
                     logging.error(f"Unexpected error fetching cost data: {e}", exc_info=True)
                     # Keep avg_cost_credits as 0.0
            else:
                logging.warning("No distinct conversation IDs returned from RPC, cannot calculate average cost.")

            # Add the calculated (or default 0.0) average cost to the results
            stats_data['avg_cost_credits'] = avg_cost_credits

            logging.debug(f"Processed stats data being returned: {stats_data}")
            return stats_data

        except APIError as e:
            logging.error(f"Supabase API error calling get_message_activity_in_range: {e}", exc_info=True)
            return {'error': f"Database API error: {e.message}"}
        except Exception as e:
            logging.error(f"Unexpected error fetching dashboard stats: {e}", exc_info=True)
            # Generic error for unexpected issues
            return {'error': f"An unexpected error occurred: {str(e)}"}

    def _empty_stats(self, error_payload: Optional[Dict] = None) -> Dict[str, Any]:
        """Returns a default empty structure for dashboard stats, optionally including an error."""
        base_stats = {
            "total_conversations_period": 0,
            "avg_duration_seconds": 0,
            "avg_sentiment_score": 0.0,
            "peak_time_hour": None,
            "activity_by_hour": {hour: 0 for hour in range(24)},
            "activity_by_day": {day: 0 for day in range(7)}
        }
        if error_payload:
            base_stats.update(error_payload)
        return base_stats

    # --- Method to Replace Old DB Logic (Keep ONE copy) ---
    def get_filtered_conversations(self, start_date=None, end_date=None, limit=100, offset=0):
        """ New method to fetch paginated conversations matching the old DB service signature."""
        # Use the existing Supabase method
        return self.get_conversations(start_date, end_date, limit, offset) 