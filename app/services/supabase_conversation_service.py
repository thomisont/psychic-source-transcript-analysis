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
from flask import current_app # *** ADD IMPORT ***

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
        Initializes the service with a Supabase client instance.
        The client is expected to be pre-configured and passed in.
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
    
    def get_conversation_count(self, start_date=None, end_date=None, agent_id: Optional[str] = None) -> int:
        """
        Gets the count of conversations within an optional date range, filtered by agent_id.
        Uses the 'created_at' field and 'agent_id' of the conversations table for filtering.
        NOTE: This counts conversations records, which might differ slightly from counts
        based on message activity if conversations exist without messages.
        """
        if not self.initialized or not self.supabase or not self.supabase.client:
             logging.error("Supabase client not available in get_conversation_count")
             return 0

        try:
            query = self.supabase.client.table('conversations').select("id") # Select only ID
            
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
                
            # +++ Apply agent_id filter +++
            if agent_id:
                query = query.eq('agent_id', agent_id)
                logging.info(f"Applying agent_id filter: {agent_id}")
            # +++ End agent_id filter +++

            # Execute the query to get IDs
            response = query.execute()
            
            # --- Log the raw data and the full response --- 
            logging.debug(f"Supabase count query (ID fetch) RAW RESPONSE DATA (first 10): {response.data[:10] if response.data else 'None'}")
            logging.debug(f"Supabase count query (ID fetch) FULL RESPONSE OBJECT: {response}")
            # --- End Log ---
            
            # Count the number of rows returned
            count = len(response.data) if response.data else 0
            logging.info(f"Retrieved count {count} via ID fetch for conversations ({start_dt_iso} to {end_dt_iso}, agent: {agent_id}).")
            return count
            
        except Exception as e:
            logging.error(f"Error in get_conversation_count (agent: {agent_id}): {e}", exc_info=True)
            return 0
    
    def get_conversations(self, start_date=None, end_date=None, limit=100, offset=0, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves a paginated list of conversations, filtered by message timestamps
        within the specified date range AND by agent_id.
        
        Process:
        1. Calls the Supabase RPC function `get_conversation_ids_in_range` to get IDs
           of conversations having messages within the start/end date AND matching agent_id.
        2. Fetches the full conversation data (including nested messages) for ALL matching IDs.
        3. Processes the fetched data, calculating duration and formatting transcripts.
        4. Sorts the processed conversations by start time (created_at) in Python.
        5. Applies pagination (limit/offset) to the sorted list in Python.
        6. Returns the paginated list and the total count found by the RPC function.
        """
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
            logging.info(f"Calling RPC get_conversation_ids_in_range with start={start_dt_iso}, end={end_dt_iso}, agent_id={agent_id}")
            rpc_params = {
                'start_iso': start_dt_iso,
                'end_iso': end_dt_iso,
                'target_agent_id': agent_id # Pass agent_id to RPC
            }
            # Handle None dates/agent_id
            if start_dt_iso is None: rpc_params['start_iso'] = None
            if end_dt_iso is None: rpc_params['end_iso'] = None
            if agent_id is None: rpc_params['target_agent_id'] = None # Pass None if not specified

            id_response = self.supabase.client.rpc('get_conversation_ids_in_range', rpc_params).execute()
            
            if not hasattr(id_response, 'data') or id_response.data is None:
                 logging.warning(f"RPC call get_conversation_ids_in_range returned no data for range {start_date}-{end_date}, agent: {agent_id}")
                 return {"conversations": [], "total_count": 0}

            conversation_ids_data = id_response.data
            conversation_ids = [item['conversation_id'] for item in conversation_ids_data if 'conversation_id' in item]
            total_count = len(conversation_ids)
            logging.info(f"Found {total_count} matching conversation IDs for range {start_date}-{end_date}, agent: {agent_id}")

            if not conversation_ids:
                 return {"conversations": [], "total_count": 0}

            # --- Apply pagination to the list of IDs --- 
            # paginated_ids = conversation_ids[offset : offset + limit]
            # Fetch ALL conversations matching the IDs first
            paginated_ids = conversation_ids # Use all IDs for the fetch
            
            if not paginated_ids:
                logging.info(f"No conversations for the requested page (offset={offset}, limit={limit}) within the date range.")
                return {"conversations": [], "total_count": total_count} # Return total count but empty page

            # --- Fetch full conversation data for ALL matching IDs --- 
            logging.info(f"Fetching full data for {len(paginated_ids)} conversations (agent: {agent_id})...")
            query = self.supabase.client.table('conversations').select(
                "id, external_id, title, created_at, status, agent_id, messages(*)" # Added agent_id to select
            ).in_('id', paginated_ids)
            
            # REMOVED ordering at the Supabase query level
            # query = query.order('created_at', desc=True)
            
            # Execute query for full data
            response = query.execute()
            result_data = response.data
            logging.info(f"Fetched {len(result_data)} full conversation records (agent: {agent_id}).")

            # --- Process results --- 
            conversations = []
            for row in result_data:
                messages = row.get('messages', [])
                
                # Format transcript similar to get_conversation_details
                transcript = []
                if messages:
                    for i, msg in enumerate(messages): 
                        speaker = msg.get('speaker')
                        role_field = msg.get('role')
                        message_content = msg.get('text') or msg.get('content') or ''
                        
                        # Explicitly determine role
                        current_role = 'agent' # Default to agent
                        if speaker == 'user' or role_field == 'user':
                            current_role = 'user'
                        
                        # Now 'i' is defined for this log message
                        logging.debug(f"  Msg {i}: speaker='{speaker}', role_field='{role_field}', ASSIGNED_ROLE='{current_role}'")

                        transcript.append({
                            'role': current_role, 
                            'content': message_content,
                            'timestamp': msg.get('timestamp'),
                        })

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

                # Ensure start_time is parsed for sorting
                start_time_for_sort = None
                created_at_str = row.get('created_at')
                if created_at_str:
                    try:
                        start_time_for_sort = parser.parse(created_at_str)
                        if start_time_for_sort.tzinfo is None:
                            start_time_for_sort = start_time_for_sort.replace(tzinfo=timezone.utc)
                    except Exception as parse_err:
                        logging.warning(f"Could not parse created_at '{created_at_str}' for sorting: {parse_err}")

                # Conversation data now includes the transcript
                conversation_data = {
                    'conversation_id': row.get('external_id'),
                    'agent_id': row.get('agent_id'), # Include agent_id in response
                    'title': row.get('title') or "Untitled",
                    'start_time': created_at_str, # Keep original string for response
                    'status': row.get('status'),
                    'message_count': len(messages),
                    'duration': duration,
                    'sentiment_score': 0.0,
                    'transcript': transcript,
                    # Add the parsed datetime object for sorting (won't be in JSON response)
                    '_sort_time': start_time_for_sort 
                }
                conversations.append(conversation_data)
            
            # --- Sort the fetched conversations in Python --- 
            # Sort by the parsed datetime object, descending (most recent first)
            # Handle cases where _sort_time might be None
            conversations.sort(key=lambda x: x.get('_sort_time') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            
            # --- Apply pagination to the sorted Python list --- 
            paginated_conversations = conversations[offset : offset + limit]
            
            # Remove the temporary sort key before returning
            for conv in paginated_conversations:
                conv.pop('_sort_time', None)

            logging.info(f"Returning {len(paginated_conversations)} conversations for page (offset={offset}, limit={limit}, agent: {agent_id}). Total: {total_count}")

            return {
                "conversations": paginated_conversations, # Return the paginated list
                "total_count": total_count
            }
            
        except Exception as e:
            logging.error(f"Error in get_conversations (agent: {agent_id}): {e}", exc_info=True)
            return {"conversations": [], "total_count": 0, "error": str(e)}
    
    def get_conversation_details(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed information for a single conversation by its external_id.
        Includes agent_id in the returned data.
        
        Process:
        1. Fetches the main conversation record (including cost, summary) using external_id.
        2. Fetches all associated messages using the internal conversation primary key ID.
        3. Constructs a formatted transcript array, determining user/agent roles.
        4. Calculates duration based on message timestamps.
        5. Returns a dictionary containing conversation details, messages, and transcript.
        """
        if not self.initialized or not self.supabase or not self.supabase.client:
             logging.error("Supabase client not available in get_conversation_details")
             return None

        try:
            # Step 1: Fetch the conversation by external_id, including cost_credits AND summary
            logging.info(f"Fetching conversation details for external_id: {conversation_id}")
            conv_response = self.supabase.client.table('conversations') \
                        .select("id, external_id, title, created_at, status, cost_credits, summary, agent_id") \
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

            # Construct response (more robust role/content handling) - REPLACEMENT v2
            transcript = []
            logging.debug(f"--- Building Transcript for {conversation_id} ---") 
            for i, msg in enumerate(messages):
                speaker = msg.get('speaker')
                role_field = msg.get('role')
                message_content = msg.get('text') or msg.get('content') or ''
                
                # Explicitly determine role
                current_role = 'agent' # Default to agent
                if speaker == 'user' or role_field == 'user':
                    current_role = 'user'
                
                logging.debug(f"  Msg {i}: speaker='{speaker}', role_field='{role_field}', ASSIGNED_ROLE='{current_role}'")

                transcript.append({
                    'role': current_role, # Use the explicitly determined role
                    'content': message_content,
                    'timestamp': msg.get('timestamp'),
                })
            logging.debug(f"--- Finished Building Transcript for {conversation_id} ---")
            # End of REPLACEMENT block v2
            
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
                'agent_id': conversation.get('agent_id'), # Include agent_id
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
            logging.error(f"Error in get_conversation_details: {e}", exc_info=True)
            return None # Return None on any exception
            
    def get_dashboard_stats(self, start_date: str | None = None, end_date: str | None = None, agent_id: Optional[str] = None) -> dict:
        """
        Fetches aggregated statistics for the main dashboard based on message activity
        within the specified date range AND filtered by agent_id.

        Process:
        1. Calls the Supabase RPC function `get_message_activity_in_range` (updated to accept agent_id)
           which performs the primary aggregation based on message timestamps and agent_id.
        2. Performs secondary queries using the returned distinct IDs (already filtered by agent)
           to calculate average cost and completion rate.
        3. Cleans and combines the results into a dictionary for the dashboard API.
        """
        try:
            logging.info(f"Calling Supabase RPC get_message_activity_in_range with start: {start_date}, end: {end_date}, agent_id: {agent_id}")
            # Prepare parameters for the RPC call, including agent_id
            params = {
                'start_iso': start_date,
                'end_iso': end_date,
                'target_agent_id': agent_id # Pass agent_id to RPC
            }
            if agent_id is None: params['target_agent_id'] = None # Ensure None is passed if not specified

            # Execute the Supabase function
            response = self.supabase.client.rpc('get_message_activity_in_range', params).execute()
            logging.debug(f"Raw response from get_message_activity_in_range: {response}")

            # *** CORRECTED CHECK FOR VALID RESPONSE DATA ***
            # Check if response.data exists and is either a dict (single row) or a non-empty list
            valid_response = False
            if response.data:
                 if isinstance(response.data, dict):
                     valid_response = True
                 elif isinstance(response.data, list) and len(response.data) > 0:
                     valid_response = True
            
            if not valid_response:
                logging.warning(f"RPC call get_message_activity_in_range returned invalid or empty data for range {start_date}-{end_date}, agent: {agent_id}. Response: {response.data}")
                # Return a default structure indicating no data, matching expected keys by frontend
                return {
                    'activity_by_hour': {}, 'activity_by_day': {}, 'daily_volume': {},
                    'daily_avg_duration': {}, 'total_conversations_period': 0,
                    'avg_duration_seconds': 0, 'peak_time_hour': None,
                    'distinct_conversation_ids': [], 
                    'avg_cost_credits': 0.0, 
                    'completion_rate': 0.0,
                    'month_to_date_cost': None,
                    'monthly_credit_budget': current_app.config.get('MONTHLY_CREDIT_BUDGET', 2000000) 
                }
            # *** END CORRECTED CHECK ***

            # The RPC function might return the dict directly or in a list
            stats_data = response.data[0] if isinstance(response.data, list) else response.data 

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


            # --- Calculate Average Cost (Uses IDs already filtered by agent in RPC) ---
            distinct_ids_for_cost = stats_data.get('distinct_conversation_ids')
            avg_cost_credits = 0.0

            if distinct_ids_for_cost:
                try:
                    logging.debug(f"Fetching cost_credits for {len(distinct_ids_for_cost)} conversation IDs (agent: {agent_id}).")
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
                except Exception as e:
                    logging.error(f"Unexpected error fetching cost data (agent: {agent_id}): {e}", exc_info=True)
            else:
                logging.warning(f"No distinct conversation IDs returned from RPC (agent: {agent_id}), cannot calculate average cost.")

            stats_data['avg_cost_credits'] = avg_cost_credits

            # --- Calculate Completion Rate (Uses IDs already filtered by agent in RPC) ---
            completed_count = 0
            completion_rate = 0.0
            total_conversations_in_period = stats_data.get('total_conversations_period', 0)

            if distinct_ids_for_cost and total_conversations_in_period > 0:
                try:
                    logging.debug(f"Fetching count of completed conversations for {len(distinct_ids_for_cost)} IDs (agent: {agent_id}).")
                    # Count completed conversations among those identified by the RPC
                    completed_response = self.supabase.client.table('conversations') \
                        .select('id', count='exact') \
                        .in_('id', distinct_ids_for_cost) \
                        .eq('status', 'completed') \
                        .execute()

                    if completed_response.count is not None:
                        completed_count = completed_response.count
                        completion_rate = (completed_count / total_conversations_in_period) # Keep as fraction 0.0-1.0
                        logging.info(f"Calculated completion rate: {completion_rate} ({completed_count}/{total_conversations_in_period})")
                    else:
                         logging.warning("Could not retrieve count of completed conversations.")

                except Exception as e:
                    logging.error(f"Unexpected error fetching completed conversation count (agent: {agent_id}): {e}", exc_info=True)
            elif total_conversations_in_period == 0:
                 logging.info(f"Total conversations period is 0 (agent: {agent_id}), completion rate is 0.")
            else: # distinct_ids_for_cost is empty
                logging.warning(f"No distinct conversation IDs returned from RPC (agent: {agent_id}), cannot calculate completion rate.")

            stats_data['completion_rate'] = completion_rate

            # --- NEW: Calculate Month-to-Date Cost --- 
            month_to_date_cost = 0
            try:
                now = datetime.now(timezone.utc)
                start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Query conversations created this month (using created_at)
                # Apply agent_id filter here too!
                query = self.supabase.client.table('conversations') \
                    .select('cost_credits', count='exact') \
                    .gte('created_at', start_of_month.isoformat())
                    # .lte('created_at', now.isoformat()) # Don't strictly need end date
                
                if agent_id:
                    query = query.eq('agent_id', agent_id)
                    
                monthly_cost_response = query.execute()
                
                if monthly_cost_response.data:
                    for conv in monthly_cost_response.data:
                        cost = conv.get('cost_credits')
                        if cost is not None and isinstance(cost, (int, float)):
                            month_to_date_cost += cost
                logging.info(f"Calculated month-to-date cost ({start_of_month.strftime('%Y-%m-%d')} to now, agent: {agent_id}): {month_to_date_cost}")
            except Exception as mtd_err:
                 logging.error(f"Error calculating month-to-date cost: {mtd_err}", exc_info=True)
                 month_to_date_cost = None # Indicate error

            stats_data['month_to_date_cost'] = month_to_date_cost
            # --- END NEW MTD COST --- 
            
            # --- Get Budget from Config --- 
            monthly_budget = current_app.config.get('MONTHLY_CREDIT_BUDGET', 2000000) # Default if not set
            stats_data['monthly_credit_budget'] = monthly_budget
            # --- End Get Budget --- 

            logging.debug(f"Processed stats data being returned (agent: {agent_id}): {stats_data}")
            return stats_data

        except Exception as e:
            logging.error(f"Supabase error calling RPC or processing stats (agent: {agent_id}): {e}", exc_info=True)
            # Return dict with error key
            return {'error': f"Database function error: {str(e)}"}

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

    # --- Vector Search Method ---
    def find_similar_conversations(self, query_vector: List[float], start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 10, similarity_threshold: float = 0.75) -> Dict[str, Any]:
        """
        Finds conversations with embeddings semantically similar to the query vector,
        filtered by date range.

        Args:
            query_vector: The vector embedding of the user's query.
            start_date: Optional start date string (YYYY-MM-DD).
            end_date: Optional end date string (YYYY-MM-DD).
            limit: The maximum number of similar conversations to return.
            similarity_threshold: The minimum similarity score (cosine distance) for a match.

        Returns:
            A dictionary containing:
            - 'conversations': A list of dictionaries, each containing info about a similar conversation
                               (e.g., id, external_id, summary, score).
            - 'error': An error message string if an issue occurred, otherwise None.
        """
        if not self.initialized or not self.supabase or not self.supabase.client:
            logging.error("Supabase client not available in find_similar_conversations")
            return {'conversations': [], 'error': "Supabase client not initialized"} # Return dict
        if not query_vector:
            logging.error("No query vector provided for similarity search.")
            return {'conversations': [], 'error': "No query vector provided"} # Return dict

        try:
            # Convert dates to ISO strings for the function
            start_dt_iso = None
            end_dt_iso = None
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                start_dt_iso = start_dt.isoformat()
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                end_dt_iso = end_dt.isoformat()

            # Parameters for the RPC function
            params = {
                'query_embedding': query_vector,
                'similarity_threshold': similarity_threshold,
                'match_count': limit,
                'start_iso': start_dt_iso, # Pass None if not provided
                'end_iso': end_dt_iso # Pass None if not provided
            }

            # --- LOWER THE THRESHOLD FOR TESTING --- 
            test_threshold = 0.35 # Lowered from 0.75
            params['similarity_threshold'] = test_threshold
            logging.info(f"Calling RPC match_conversations with limit={limit}, threshold={test_threshold}, start={start_date}, end={end_date}")
            # --- END THRESHOLD ADJUSTMENT ---
            
            # Execute the RPC function (assumes it exists in Supabase)
            response = self.supabase.client.rpc('match_conversations', params).execute()

            if response.data:
                logging.info(f"Found {len(response.data)} similar conversations.")
                # The RPC function should return a list of dicts with id, external_id, summary, score
                return {'conversations': response.data} # Return dict
            else:
                logging.info("No similar conversations found matching the criteria.")
                return {'conversations': []} # Return dict with empty list

        except Exception as e:
            logging.error(f"Error calling RPC match_conversations: {e}", exc_info=True)
            return {'conversations': [], 'error': f"Error during similarity search: {e}"} # Return dict with error

    # --- Method to Replace Old DB Logic (Keep ONE copy) ---
    def get_filtered_conversations(self, start_date=None, end_date=None, limit=100, offset=0):
        """ New method to fetch paginated conversations matching the old DB service signature."""
        # Use the existing Supabase method
        return self.get_conversations(start_date, end_date, limit, offset) 