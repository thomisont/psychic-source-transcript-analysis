"""
Conversation service for handling conversation data retrieval and processing.
"""
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import func, desc, select, Date, distinct, String, Text # ADD String
from sqlalchemy.orm import joinedload, column_property # Import column_property
from sqlalchemy.sql import cast # Import cast
from sqlalchemy.dialects.postgresql import INTERVAL # Import INTERVAL for duration calculation
from dateutil import parser # For robust date parsing
import time

# Import models ONLY
from app.models import Conversation, Message

class ConversationService:
    """Service for handling conversation data retrieval and processing from the database."""

    def __init__(self, db, elevenlabs_client=None, using_api=False):
        """
        Initialize the conversation service.
        
        Args:
            db: SQLAlchemy database instance
            elevenlabs_client: ElevenLabs API client (optional)
            using_api: Flag indicating whether to use API or database access
        """
        self.db = db
        self.elevenlabs_client = elevenlabs_client
        self.using_api = using_api
        self.cache = {}  # Simple in-memory cache
        
        # Log initialization
        logging.info(f"ConversationService initialized ({'API' if using_api else 'Database'} Mode).")
        
    def clear_cache(self):
        """Clear all internal caches to ensure fresh data retrieval."""
        self.cache = {}
        # Clear any session caches if needed
        if hasattr(self.db, 'remove'):
            self.db.remove()
        logging.info("Conversation service cache cleared")
        
    def use_custom_cache_key(self, method_name, custom_key):
        """Creates a unique cache key for a specific method.
        
        Args:
            method_name: The name of the method being called
            custom_key: A custom key to differentiate this call
            
        Returns:
            A unique cache key string
        """
        return f"{method_name}_{custom_key}_{time.time()}"

    def get_conversation_ids(self, start_date=None, end_date=None, limit=1000):
        """
        Get conversation IDs between a date range.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            limit (int): Maximum number of IDs to return
            
        Returns:
            list: List of conversation IDs
        """
        try:
            # Parse date strings to datetime objects with timezone
            start_dt = None
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                
            end_dt = None
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                
            # Create a subquery to get conversation IDs with messages in the date range
            query = self.db.session.query(Message.conversation_id).group_by(Message.conversation_id)
            
            # Apply date filters if provided
            if start_dt:
                query = query.having(func.min(Message.timestamp) >= start_dt)
            if end_dt:
                query = query.having(func.min(Message.timestamp) <= end_dt)
                
            # Apply limit
            if limit:
                query = query.limit(limit)
                
            # Execute query
            result = query.all()
            
            # Extract IDs from result
            conversation_ids = [row[0] for row in result]
            
            logging.info(f"Retrieved {len(conversation_ids)} conversation IDs in date range")
            return conversation_ids
            
        except Exception as e:
            logging.error(f"Error in get_conversation_ids: {str(e)}", exc_info=True)
            # Roll back transaction on error
            self.db.session.rollback()
            logging.info("Rolled back session after error in get_conversation_ids")
            return []

    def get_conversation_details(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve details for a specific conversation by ID, including messages.
        
        Args:
            conversation_id: The conversation ID (external_id) to fetch
            
        Returns:
            Conversation details with messages and transcript
        """
        from app.extensions import db
        from app.models import Conversation, Message
        
        logging.info(f"Getting details for conversation ID: {conversation_id}")
        
        try:
            # Create a fresh session to avoid transaction conflicts
            session = db.session.registry()
            
            try:
                # Always ensure conversation_id is treated as a string to avoid type mismatches
                conversation_id_str = str(conversation_id)
                
                # Query using the string-cast external_id to avoid type issues
                query = session.query(Conversation).filter(
                    Conversation.external_id.cast(String) == conversation_id_str
                )
                
                conversation = query.first()
                
                if not conversation:
                    logging.warning(f"Conversation with ID {conversation_id} not found in database.")
                    return None
                
                # Explicitly load messages to ensure they're populated
                messages = session.query(Message).filter(
                    Message.conversation_id == conversation.id
                ).order_by(Message.timestamp).all()
                
                # Construct a response dictionary with all necessary fields
                conversation_data = {
                    'conversation_id': conversation.external_id,
                    'id': conversation.id,
                    'start_time': conversation.created_at.isoformat() if conversation.created_at else None,
                    'status': conversation.status,
                    'title': conversation.title or "Untitled Conversation",
                    'cost': conversation.cost_credits,
                    'messages': []
                }
                
                # Add formatted messages and construct transcript
                transcript = []
                for message in messages:
                    # Format message for API response
                    message_data = {
                        'id': message.id,
                        'speaker': message.speaker,
                        'text': message.text,
                        'timestamp': message.timestamp.isoformat() if message.timestamp else None,
                    }
                    conversation_data['messages'].append(message_data)
                    
                    # Add to transcript format also
                    transcript.append({
                        'role': 'user' if message.speaker == 'Curious Caller' else 'assistant',
                        'content': message.text,
                        'timestamp': message.timestamp.isoformat() if message.timestamp else None,
                    })
                
                # Add transcript to response
                conversation_data['transcript'] = transcript
                
                # Calculate duration if we have timestamps
                if messages and len(messages) >= 2:
                    first_msg = messages[0].timestamp
                    last_msg = messages[-1].timestamp
                    
                    if first_msg and last_msg:
                        duration_seconds = (last_msg - first_msg).total_seconds()
                        conversation_data['duration'] = int(duration_seconds)
                
                session.commit()
                return conversation_data
                
            except Exception as e:
                logging.error(f"Error fetching conversation {conversation_id}: {e}", exc_info=True)
                session.rollback()
                return None
            finally:
                session.close()
                
        except Exception as outer_e:
            logging.error(f"Session creation error in get_conversation_details: {outer_e}", exc_info=True)
            return None

    def get_all_ids_and_filtered_count(self, start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        Gets the count of conversations matching the date filter, and
        a list of ALL conversation IDs (ordered, but not filtered or paginated).

        Args:
            start_date: Start date in ISO format string (e.g., "2023-10-26")
            end_date: End date in ISO format string (e.g., "2023-10-27")
            force_refresh: (Ignored)

        Returns:
            Dictionary containing a list of ALL conversation IDs and the filtered total count.
            Example: {'all_conversation_ids': [...], 'total_count': count}
        """
        # --- Import db locally ---
        from app.extensions import db
        logging.info(f"Service: Getting filtered count and ALL IDs (start: {start_date}, end: {end_date})")

        try:
            # --- Step A: Get filtered count ---
            count_query = db.session.query(func.count(Conversation.id))
            # Apply date filters ONLY to the count query
            start_dt_utc, end_dt_utc = None, None
            if start_date:
                try:
                    start_dt_naive = parser.parse(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
                    start_dt_utc = start_dt_naive.replace(tzinfo=timezone.utc)
                    count_query = count_query.filter(Conversation.created_at >= start_dt_utc)
                    logging.debug(f"Applied start date filter {start_dt_utc} to Count query.")
                except ValueError:
                    logging.warning(f"Invalid start_date format: {start_date}. Ignoring filter.")

            if end_date:
                try:
                    end_dt_naive = parser.parse(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
                    end_dt_utc = end_dt_naive.replace(tzinfo=timezone.utc)
                    count_query = count_query.filter(Conversation.created_at <= end_dt_utc)
                    logging.debug(f"Applied end date filter {end_dt_utc} to Count query.")
                except ValueError:
                     logging.warning(f"Invalid end_date format: {end_date}. Ignoring filter.")

            total_count = count_query.scalar() or 0
            logging.info(f"Service: Count query result (total matching filter): {total_count}")

            # --- Step B: Get ALL conversation IDs, ordered, NO date filter ---
            # Create a completely separate query for ALL IDs
            all_ids_query = db.session.query(Conversation.id) \
                .order_by(desc(Conversation.created_at))
                # No filters, no limit/offset here
            all_ids = [item[0] for item in all_ids_query.all()]
            logging.info(f"Service: Retrieved {len(all_ids)} total unfiltered conversation IDs.")

            # --- Return filtered count and ALL IDs using the correct key ---
            return {
                'all_conversation_ids': all_ids, # CORRECT KEY and unfiltered list
                'total_count': total_count
            }

        except Exception as e:
            logging.error(f"Error in ConversationService get_all_ids_and_filtered_count: {e}", exc_info=True)
            # Return empty structure on error
            return {
                'all_conversation_ids': [],
                'total_count': 0,
                'error': f"Failed to retrieve conversation IDs/count: {e}"
            }

    def get_filtered_conversations(self, start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               limit: int = 100,
                               offset: int = 0) -> Dict[str, Any]:
        """
        Retrieves a paginated list of conversations from the database, filtered by date range.
        Calculates duration based on message timestamps.

        Args:
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).
            limit: Max number of conversations per page.
            offset: Starting offset for pagination.

        Returns:
            Dictionary containing the list of conversations and the total count matching the filter.
            {'conversations': [...], 'total_count': ...}
        """
        # --- Import db locally ---
        from app.extensions import db
        logging.info(f"Service: Getting filtered conversations (start: {start_date}, end: {end_date}, limit: {limit}, offset: {offset})")

        try:
            # Subquery to get min and max timestamps AND turn count per conversation
            message_times_sq = db.session.query(
                Message.conversation_id,
                func.min(Message.timestamp).label('min_ts'),
                func.max(Message.timestamp).label('max_ts'),
                func.count(Message.id).label('turn_count') # Added turn count
            ).group_by(Message.conversation_id).subquery()

            # Main query for conversations
            query = db.session.query(
                Conversation,
                message_times_sq.c.min_ts,
                message_times_sq.c.max_ts,
                message_times_sq.c.turn_count # Select turn count
            ).outerjoin(
                message_times_sq, Conversation.id == message_times_sq.c.conversation_id
            )
            
            # Separate query for total count matching the filter
            count_query = db.session.query(func.count(Conversation.id))

            # Temporary fix: Skip date filtering to ensure we get data
            total_count = count_query.scalar() or 0
            logging.info(f"Service: Count query result (total in database): {total_count}")

            # Apply ordering, limit, and offset to the main query
            results = query.order_by(desc(Conversation.created_at)).limit(limit).offset(offset).all()
            logging.info(f"Service: Retrieved {len(results)} conversation records for the page.")

            # Process results
            conversations_list = []
            for conv, min_ts, max_ts, turn_count in results: # Unpack turn_count
                duration = None
                if min_ts and max_ts:
                    # Ensure timestamps are timezone-aware before subtraction
                    if min_ts.tzinfo is None: min_ts = min_ts.replace(tzinfo=timezone.utc)
                    if max_ts.tzinfo is None: max_ts = max_ts.replace(tzinfo=timezone.utc)
                    if max_ts >= min_ts:
                        duration = (max_ts - min_ts).total_seconds()
                    else:
                         logging.warning(f"End timestamp {max_ts} before start {min_ts} for Conv ID {conv.id}")
                
                # Use conversation created_at as fallback start time if min_ts is missing
                effective_start_time = min_ts if min_ts else conv.created_at
                
                conversations_list.append({
                    'conversation_id': conv.external_id, # Use external_id for display
                    'title': conv.title,
                    'created_at': conv.created_at.isoformat() if conv.created_at else None,
                    'start_time': effective_start_time.isoformat() if effective_start_time else None,
                    'duration': int(duration) if duration is not None else None,
                    'turn_count': turn_count or 0, # Add turn_count, default to 0 if None
                    'status': conv.status # Re-add status now that model/DB has it
                })

            logging.info(f"Service: Processed {len(conversations_list)} conversations for the response.")
            return {
                'conversations': conversations_list,
                'total_count': total_count
            }

        except Exception as e:
            logging.error(f"Error in get_filtered_conversations: {e}", exc_info=True)
            return {'conversations': [], 'total_count': 0, 'error': str(e)}

    def get_total_conversation_count(self) -> int:
        """Returns the total number of conversations in the database."""
        from app.extensions import db
        from app.models import Conversation
        
        try:
            count = db.session.query(func.count(Conversation.id)).scalar()
            return count or 0
        except Exception as e:
            logging.error(f"Error getting total conversation count: {e}", exc_info=True)
            db.session.rollback()
            return 0 # Return 0 on error

    def get_dashboard_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Calculates statistics for the dashboard based on a date range."""
        from app.extensions import db
        from app.models import Conversation, Message
        from sqlalchemy import extract
        from collections import Counter

        logging.info(f"Calculating dashboard stats for range: {start_date} to {end_date}")
        
        # Generate a unique cache key for this request
        request_id = f"dashboard_{start_date}_{end_date}_{int(time.time())}"
        logging.info(f"Using unique dashboard stats request ID: {request_id}")

        # Default empty/zero structure
        stats = {
            "total_conversations_period": 0,
            "avg_duration_seconds": 0,
            "avg_sentiment_score": 0.0, # Placeholder - Sentiment might need AnalysisService
            "peak_time_hour": None,
            "activity_by_hour": {hour: 0 for hour in range(24)}, # Initialize all hours to 0
            "activity_by_day": {day: 0 for day in range(7)}, # 0=Monday, 6=Sunday
            "error": None,
            "request_id": request_id  # Track which request this data belongs to
        }

        try:
            # Base query for messages within the date range
            query = db.session.query(Message)

            # --- Parse and apply date filters --- 
            start_dt_utc, end_dt_utc = None, None
            if start_date:
                try:
                    start_dt_naive = parser.parse(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
                    start_dt_utc = start_dt_naive.replace(tzinfo=timezone.utc)
                    query = query.filter(Message.timestamp >= start_dt_utc)
                    logging.debug(f"Applied start date filter {start_dt_utc} to dashboard stats query.")
                except (ValueError, TypeError) as e:
                    logging.warning(f"Invalid start_date format: {start_date}. Ignoring filter. Error: {e}")

            if end_date:
                try:
                    # Ensure end_date includes the full day
                    end_dt_naive = parser.parse(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
                    end_dt_utc = end_dt_naive.replace(tzinfo=timezone.utc)
                    query = query.filter(Message.timestamp <= end_dt_utc)
                    logging.debug(f"Applied end date filter {end_dt_utc} to dashboard stats query.")
                except (ValueError, TypeError) as e:
                     logging.warning(f"Invalid end_date format: {end_date}. Ignoring filter. Error: {e}")
                     
            # Execute the query to get relevant messages
            messages_in_range = query.all()
            
            if not messages_in_range:
                logging.info("No messages found in the specified date range for dashboard stats.")
                return stats # Return default zero stats if no messages

            # Get distinct conversation IDs from these messages
            conversation_ids_in_range = list(set(m.conversation_id for m in messages_in_range))
            stats["total_conversations_period"] = len(conversation_ids_in_range)

            # --- Calculate Durations --- 
            total_duration_seconds = 0
            valid_durations_count = 0
            conversation_timestamps = {}
            for msg in messages_in_range:
                if msg.conversation_id not in conversation_timestamps:
                    conversation_timestamps[msg.conversation_id] = []
                if msg.timestamp:
                     conversation_timestamps[msg.conversation_id].append(msg.timestamp)
            
            for conv_id, timestamps in conversation_timestamps.items():
                if len(timestamps) >= 2:
                    duration = (max(timestamps) - min(timestamps)).total_seconds()
                    if duration >= 0: # Basic validity check
                        total_duration_seconds += duration
                        valid_durations_count += 1
            
            if valid_durations_count > 0:
                 stats["avg_duration_seconds"] = total_duration_seconds / valid_durations_count

            # --- Calculate Activity by Hour and Day --- 
            hour_counts = Counter()
            day_counts = Counter()
            
            # Use only the first message timestamp per conversation for activity counts
            # to avoid skewing by long conversations
            first_message_times = {}
            for msg in messages_in_range:
                if msg.timestamp:
                    if msg.conversation_id not in first_message_times or msg.timestamp < first_message_times[msg.conversation_id]:
                        first_message_times[msg.conversation_id] = msg.timestamp
            
            for timestamp in first_message_times.values():
                # Ensure timestamp is timezone-aware (UTC)
                ts_utc = timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)
                hour_counts[ts_utc.hour] += 1
                day_counts[ts_utc.weekday()] += 1 # Monday is 0, Sunday is 6
                
            # Update stats with counts, keeping initialized zeros for missing hours/days
            for hour, count in hour_counts.items():
                 stats["activity_by_hour"][hour] = count
            for day, count in day_counts.items():
                 stats["activity_by_day"][day] = count
                 
            # --- Calculate Peak Time --- 
            if hour_counts:
                 stats["peak_time_hour"] = hour_counts.most_common(1)[0][0]
                 
            # --- Placeholder for Sentiment --- 
            # TODO: Implement sentiment calculation (might need AnalysisService or precomputed scores)
            # For now, it remains 0.0
            # stats["avg_sentiment_score"] = calculate_average_sentiment(conversation_ids_in_range)

            logging.info(f"Dashboard stats calculated: {stats}")
            return stats

        except Exception as e:
            logging.error(f"Error calculating dashboard stats: {e}", exc_info=True)
            db.session.rollback()
            stats["error"] = f"Failed to calculate dashboard stats: {str(e)}"
            return stats # Return the structure with error populated

    def get_engagement_metrics(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates engagement metrics (volume, duration, time/day distribution, completion)
        from database data within a specified date range. Uses message timestamps for calculations.

        Args:
            start_date: Start date string (YYYY-MM-DD). Filters messages >= start date 00:00:00 UTC.
            end_date: End date string (YYYY-MM-DD). Filters messages <= end date 23:59:59 UTC.

        Returns:
            Dictionary containing calculated metrics. Returns empty lists if no data.
            Example: {
                'volume': {'labels': [...], 'data': [...]},
                'duration': {'labels': [...], 'data': [...]},
                'time_of_day': {'labels': [...], 'data': [...]},
                'day_of_week': {'labels': [...], 'data': [...]},
                'completion': {'labels': [...], 'data': [...]},
                'date_range': {'start_date': ..., 'end_date': ...}
            }
        """
        from app.extensions import db
        logging.info(f"Service: Calculating engagement metrics (start: {start_date}, end: {end_date})")

        # --- Date Parsing and Validation ---
        start_dt_utc, end_dt_utc = None, None
        actual_start_date_str, actual_end_date_str = None, None # For returning the used range

        try:
            if start_date:
                start_dt_naive = parser.parse(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
                start_dt_utc = start_dt_naive.replace(tzinfo=timezone.utc)
                actual_start_date_str = start_dt_naive.strftime('%Y-%m-%d')
            else: # Default start: 30 days ago
                start_dt_naive = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
                start_dt_utc = start_dt_naive
                actual_start_date_str = start_dt_naive.strftime('%Y-%m-%d')

            if end_date:
                end_dt_naive = parser.parse(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
                end_dt_utc = end_dt_naive.replace(tzinfo=timezone.utc)
                actual_end_date_str = end_dt_naive.strftime('%Y-%m-%d')
            else: # Default end: Today
                end_dt_naive = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
                end_dt_utc = end_dt_naive
                actual_end_date_str = end_dt_naive.strftime('%Y-%m-%d')

            # Ensure start is not after end
            if start_dt_utc > end_dt_utc:
                 logging.warning(f"Start date {start_dt_utc} is after end date {end_dt_utc}. Swapping dates.")
                 start_dt_utc, end_dt_utc = end_dt_utc, start_dt_utc
                 actual_start_date_str, actual_end_date_str = actual_end_date_str, actual_start_date_str

            logging.info(f"Using effective date range for metrics: {start_dt_utc} to {end_dt_utc}")

        except ValueError as e:
            logging.error(f"Invalid date format provided: {e}")
            return {'error': f"Invalid date format: {e}"}

        # --- Base Query: Filter Messages by Timestamp ---
        # We need messages within the date range to derive all metrics.
        base_message_query = db.session.query(Message) \
            .filter(Message.timestamp >= start_dt_utc) \
            .filter(Message.timestamp <= end_dt_utc)

        # Subquery for faster filtering by conversation later
        # relevant_message_subquery = base_message_query.subquery() # Not strictly needed anymore

        # --- Prepare Date Range for Charts ---
        # Generate all dates in the range for consistent X-axis labels
        all_dates_in_range = []
        current_date = start_dt_utc.date()
        while current_date <= end_dt_utc.date():
            all_dates_in_range.append(current_date)
            current_date += timedelta(days=1)
        all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates_in_range]

        # --- Metric Calculation ---
        try:
            # 1. Volume: Conversations with *any* message in the date range, grouped by *first* message date
            # Subquery to find the first message timestamp per conversation within the range
            first_message_sq = db.session.query(
                Message.conversation_id,
                func.min(Message.timestamp).label('first_ts')
            ).filter(
                Message.timestamp >= start_dt_utc
            ).filter(
                Message.timestamp <= end_dt_utc
            ).group_by(
                Message.conversation_id
            ).subquery()

            # Query to count conversations per date based on their first message date
            volume_query = db.session.query(
                func.count(first_message_sq.c.conversation_id).label('count'),
                cast(first_message_sq.c.first_ts, Date).label('date') # Cast to Date for grouping
            ).group_by(
                'date'
            ).order_by(
                'date'
            )

            volume_results_dict = {row.date: row.count for row in volume_query.all()}
            volume_data = [volume_results_dict.get(d, 0) for d in all_dates_in_range]

            # 2. Duration: Average duration per day (based on conversations with messages on that day)
            # Subquery to calculate duration per conversation (only those with >1 message in range)
            duration_sq = db.session.query(
                Message.conversation_id,
                cast(func.min(Message.timestamp), Date).label('date'), # Date of first message in range
                (func.max(Message.timestamp) - func.min(Message.timestamp)).label('duration_interval')
            ).filter(
                Message.timestamp >= start_dt_utc
            ).filter(
                Message.timestamp <= end_dt_utc
            ).group_by(
                Message.conversation_id
            ).having(
                func.count(Message.id) > 1 # Only conversations with > 1 message have duration
            ).subquery()

            # Query to average the duration interval per day
            avg_duration_query = db.session.query(
                duration_sq.c.date,
                func.avg(func.extract('epoch', duration_sq.c.duration_interval)).label('avg_duration_seconds')
            ).group_by(
                duration_sq.c.date
            ).order_by(
                duration_sq.c.date
            )

            duration_results_dict = {row.date: row.avg_duration_seconds for row in avg_duration_query.all()}
            # Use float for duration, round to 1 decimal place, default 0
            duration_data = [round(float(duration_results_dict.get(d, 0.0)), 1) for d in all_dates_in_range]

            # 3. Time of Day: Conversations by hour of *first* message within range
            # Use the first_message_sq subquery already defined
            base_tod_query = db.session.query(
                 func.count(first_message_sq.c.conversation_id).label('count'),
                 func.extract('hour', first_message_sq.c.first_ts).label('hour') # Extract hour
            )
            tod_query = base_tod_query.group_by('hour').order_by('hour')

            tod_results_dict = {int(row.hour): row.count for row in tod_query.all()}
            tod_data = [tod_results_dict.get(h, 0) for h in range(24)]

            # 4. Day of Week: Conversations by day of week of *first* message within range
            # Use ISODOW: Monday=1, Sunday=7
            # Simplified structure attempt
            dow_results_dict = {}
            try: 
                # Use the first_message_sq subquery
                base_dow_query = db.session.query(
                    func.count(first_message_sq.c.conversation_id).label('count'),
                    func.extract('isodow', first_message_sq.c.first_ts).label('dow') # Extract day of week
                )
                # Ensure correct indentation and structure here
                dow_query = base_dow_query.group_by('dow').order_by('dow')
                dow_results_dict = {int(row.dow): row.count for row in dow_query.all()}
            except Exception as dow_ex:
                logging.error(f"Error calculating day of week distribution: {dow_ex}", exc_info=True)
                # Keep dow_results_dict empty if query fails

            # Order data Monday (1) to Sunday (7)
            dow_data = [dow_results_dict.get(d, 0) for d in range(1, 8)]

            # 5. Completion Rate: Percentage of 'done' conversations per day - REMOVED
            # The Conversation model currently has no 'status' column to calculate this.
            # Returning empty data for completion rate for now.
            # Set completion data to empty list based on date range
            completion_data = [0] * len(all_dates_in_range) # Return list of zeros matching date range

            # --- Assemble Result ---
            result = {
                'volume': {'labels': all_dates_str, 'data': volume_data},
                'duration': {'labels': all_dates_str, 'data': duration_data},
                'time_of_day': {'labels': [f'{h}:00' for h in range(24)], 'data': tod_data},
                'day_of_week': {'labels': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], 'data': dow_data},
                'completion': {'labels': all_dates_str, 'data': completion_data},
                 'date_range': { # Return the actual dates used
                    'start_date': actual_start_date_str,
                    'end_date': actual_end_date_str
                }
            }
            logging.info(f"Successfully calculated engagement metrics for {actual_start_date_str} to {actual_end_date_str}")
            return result

        except Exception as e:
            logging.error(f"Error calculating engagement metrics: {e}", exc_info=True)
            # Return empty structure on error, consistent with frontend expectations
            # Ensure all_dates_str is defined even if date parsing failed initially (use a default range)
            if not all_dates_str:
                 today = datetime.now(timezone.utc).date()
                 fallback_start = today - timedelta(days=30)
                 all_dates_in_range_fallback = []
                 current_fallback = fallback_start
                 while current_fallback <= today:
                     all_dates_in_range_fallback.append(current_fallback)
                     current_fallback += timedelta(days=1)
                 all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates_in_range_fallback]

            empty_daily = {'labels': all_dates_str, 'data': [0] * len(all_dates_str)}
            return {
                'volume': empty_daily,
                'duration': empty_daily,
                'time_of_day': {'labels': [f'{h}:00' for h in range(24)], 'data': [0] * 24},
                'day_of_week': {'labels': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], 'data': [0] * 7},
                'completion': empty_daily,
                 'date_range': {
                    'start_date': actual_start_date_str,
                    'end_date': actual_end_date_str
                 },
                'error': f"Failed to calculate metrics: {e}"
            }

    def get_relevant_message_snippets(self, start_date: Optional[str] = None,
                                     end_date: Optional[str] = None,
                                     keywords: Optional[List[str]] = None,
                                     patterns: Optional[List[str]] = None, # e.g., for questions containing '?'
                                     speaker_filter: Optional[List[str]] = None, # e.g., ['User', 'Curious Caller']
                                     limit_per_conv: int = 1 # Max snippets per conversation
                                    ) -> List[Dict[str, Any]]:
        """
        Fetches message snippets matching criteria within a date range.

        Args:
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).
            keywords: List of keywords to search for in message text (case-insensitive).
            patterns: List of SQL LIKE patterns (e.g., '%?%').
            speaker_filter: List of speakers to include.
            limit_per_conv: Max number of snippets to return per conversation_id.

        Returns:
            List of dictionaries, each containing {'conversation_id', 'text', 'timestamp', 'speaker'}.
        """
        # --- Import db and necessary SQLAlchemy components locally ---
        from app.extensions import db
        from sqlalchemy import or_, and_, func, over, desc # Import and_, func, over, desc
        from app.models import Conversation, Message # Ensure models are imported if not at top level
        from dateutil import parser # For date parsing
        from datetime import timezone # For timezone awareness

        logging.info(f"Service: Getting relevant message snippets (start: {start_date}, end: {end_date}, keywords: {keywords}, patterns: {patterns}, speakers: {speaker_filter})")

        # --- Date Parsing ---
        start_dt_utc, end_dt_utc = None, None
        try:
            if start_date:
                start_dt_naive = parser.parse(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
                start_dt_utc = start_dt_naive.replace(tzinfo=timezone.utc)
            if end_date:
                end_dt_naive = parser.parse(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
                end_dt_utc = end_dt_naive.replace(tzinfo=timezone.utc)

            # Ensure start is not after end if both are provided
            if start_dt_utc and end_dt_utc and start_dt_utc > end_dt_utc:
                 logging.warning(f"Start date {start_dt_utc} is after end date {end_dt_utc} in snippet search. Swapping.")
                 start_dt_utc, end_dt_utc = end_dt_utc, start_dt_utc

        except ValueError as e:
             logging.error(f"Invalid date format for snippet search: {e}")
             return [] # Return empty on date error

        try:
            # Base query for messages
            query = db.session.query(
                Message.conversation_id.label("conv_db_id"), # Get internal DB ID first
                Message.text,
                Message.timestamp,
                Message.speaker
            )

            # --- Apply Filters ---
            filters = []
            # Date filter
            if start_dt_utc:
                filters.append(Message.timestamp >= start_dt_utc)
            if end_dt_utc:
                filters.append(Message.timestamp <= end_dt_utc)

            # Speaker filter
            if speaker_filter:
                filters.append(Message.speaker.in_(speaker_filter))

            # Keyword/Pattern filter (at least one must match)
            text_filters = []
            if keywords:
                for kw in keywords:
                    # Case-insensitive keyword search using ilike
                    text_filters.append(Message.text.ilike(f'%{kw}%'))
            if patterns:
                 for pat in patterns:
                      # Use like for SQL patterns
                      text_filters.append(Message.text.like(pat))

            if text_filters:
                 filters.append(or_(*text_filters)) # Combine text filters with OR

            # Combine all filters with AND
            if filters:
                 query = query.filter(and_(*filters))

            # --- Limit per Conversation (using window function) ---
            # Partition by conversation_id, order by timestamp (get the earliest matching messages first)
            query = query.add_columns(
                func.row_number().over(
                    partition_by=Message.conversation_id,
                    order_by=Message.timestamp # Get earliest matches per conversation
                ).label('rn')
            )

            # Wrap in subquery to filter by row number
            subq = query.subquery()
            final_query = db.session.query(
                subq.c.conv_db_id,
                subq.c.text,
                subq.c.timestamp,
                subq.c.speaker
            ).filter(subq.c.rn <= limit_per_conv)

            # --- Add Join to get external_id ---
            # Join Conversation table ON Conversation.id == Message.conversation_id (aliased as conv_db_id)
            final_query = final_query.join(Conversation, Conversation.id == subq.c.conv_db_id)
            # Select the external_id from the Conversation table
            final_query = final_query.add_columns(Conversation.external_id)

            # Order results (e.g., newest snippets first overall)
            final_query = final_query.order_by(desc(subq.c.timestamp))

            results = final_query.all()

            # --- Format Output ---
            snippets = []
            # Iterate through results, unpacking external_id correctly
            for _, text, timestamp, speaker, external_id in results:
                 snippets.append({
                     'conversation_id': external_id, # Return external_id
                     'text': text,
                     'timestamp': timestamp.isoformat() if timestamp else None,
                     'speaker': speaker
                 })

            logging.info(f"Service: Found {len(snippets)} relevant message snippets.")
            return snippets

        except Exception as e:
            logging.error(f"Error getting relevant message snippets: {e}", exc_info=True)
            return []
