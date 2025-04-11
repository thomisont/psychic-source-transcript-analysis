"""
Centralized data service responsible for all database access operations.
Provides optimized data fetching, caching, and incremental processing capabilities.
"""
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
import threading

from sqlalchemy import text, func, distinct, cast, String
from sqlalchemy.exc import SQLAlchemyError

class LRUCache:
    """Simple LRU (Least Recently Used) cache implementation."""
    
    def __init__(self, capacity: int = 1000):
        """Initialize a new LRU cache with the given capacity."""
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = threading.RLock()  # Thread-safe lock
        
    def get(self, key: str) -> Any:
        """Get an item from the cache, or None if not found."""
        with self.lock:
            if key not in self.cache:
                return None
            # Move to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
            
    def put(self, key: str, value: Any) -> None:
        """Add or update an item in the cache."""
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
            elif len(self.cache) >= self.capacity:
                # Remove least recently used item
                self.cache.popitem(last=False)
            self.cache[key] = value
            
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
            
    def size(self) -> int:
        """Return the current number of items in the cache."""
        with self.lock:
            return len(self.cache)
            
    def has(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self.lock:
            return key in self.cache
            
    def keys(self) -> List[str]:
        """Return a list of all keys in the cache."""
        with self.lock:
            return list(self.cache.keys())

class DataService:
    """
    Centralized service for all data access operations.
    Handles database queries, efficient caching, and provides a unified API for data access.
    """
    
    def __init__(self, db):
        """
        Initialize the DataService.
        
        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
        self.initialized = False
        self.conversation_metadata_cache = LRUCache(capacity=5000)  # Cache for conversation metadata
        self.conversation_full_cache = LRUCache(capacity=100)       # Cache for full conversation data
        self.query_results_cache = LRUCache(capacity=50)            # Cache for query results
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        self.last_sync_time = None
        self.total_conversation_count = 0
        self.metadata_load_lock = threading.Lock()
        self.query_locks = {}  # Locks for concurrent queries
        self._loaded_conversation_ids = set()  # Track loaded conversation IDs
        
    def initialize(self):
        """
        Initialize the data service by loading core metadata.
        This should be called once during application startup.
        """
        if self.initialized:
            logging.info("DataService already initialized, skipping initialization")
            return
            
        with self.metadata_load_lock:
            try:
                logging.info("Initializing DataService and loading core metadata...")
                start_time = time.time()
                
                # Get total conversation count
                self.total_conversation_count = self._get_total_conversation_count()
                logging.info(f"Found {self.total_conversation_count} total conversations in database")
                
                # Load initial conversation metadata (limit to prevent memory issues)
                self._load_conversation_metadata(limit=1000)
                
                self.initialized = True
                self.last_sync_time = datetime.now(timezone.utc)
                
                logging.info(f"DataService initialization completed in {time.time() - start_time:.2f}s")
                
                # Start background loader if needed
                # self._start_background_loader()
                
            except Exception as e:
                logging.error(f"Error initializing DataService: {e}", exc_info=True)
                # Still mark as initialized to prevent repeated init attempts
                self.initialized = True
    
    def _get_total_conversation_count(self) -> int:
        """
        Get the total number of conversations in the database.
        Uses a dedicated session to avoid transaction conflicts.
        """
        try:
            session = self.db.session()
            try:
                query = text("SELECT COUNT(*) FROM conversations")
                result = session.execute(query)
                count = result.scalar() or 0
                session.commit()
                return count
            except Exception as e:
                logging.error(f"Error getting total conversation count: {e}", exc_info=True)
                session.rollback()
                return 0
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error creating session for conversation count: {e}", exc_info=True)
            return 0
    
    def _load_conversation_metadata(self, limit=1000, offset=0, clear_existing=False):
        """
        Load conversation metadata into cache.
        
        Args:
            limit: Maximum number of conversations to load
            offset: Offset for pagination
            clear_existing: Whether to clear existing cache before loading
        """
        if clear_existing:
            self.conversation_metadata_cache.clear()
            self._loaded_conversation_ids = set()
            
        try:
            session = self.db.session()
            try:
                # Use efficient raw SQL with explicit columns to minimize memory usage
                query = text("""
                    SELECT c.id, c.external_id, c.created_at,
                           MIN(m.timestamp) as start_time, 
                           MAX(m.timestamp) as end_time,
                           COUNT(m.id) as message_count
                    FROM conversations c
                    JOIN messages m ON c.id = m.conversation_id
                    GROUP BY c.id, c.external_id, c.created_at
                    ORDER BY MIN(m.timestamp) DESC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = session.execute(query, {"limit": limit, "offset": offset})
                
                count = 0
                for row in result:
                    # Convert to a dictionary for easier handling
                    conv_data = {
                        "id": row[0],
                        "external_id": row[1],
                        "created_at": row[2],
                        "start_time": row[3],
                        "end_time": row[4],
                        "message_count": row[5],
                        "cached_at": time.time()
                    }
                    
                    # Calculate duration if possible
                    if row[3] and row[4]:
                        duration_seconds = int((row[4] - row[3]).total_seconds())
                        conv_data["duration"] = duration_seconds
                    
                    # Add to cache
                    cache_key = f"conv_meta_{row[1]}"  # external_id as key
                    self.conversation_metadata_cache.put(cache_key, conv_data)
                    self._loaded_conversation_ids.add(row[1])  # external_id
                    count += 1
                
                session.commit()
                logging.info(f"Loaded metadata for {count} conversations into cache")
                
                return count
                
            except Exception as e:
                logging.error(f"Error loading conversation metadata: {e}", exc_info=True)
                session.rollback()
                return 0
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error creating session for metadata loading: {e}", exc_info=True)
            return 0
    
    def get_conversation_count(self, start_date=None, end_date=None, use_cache=True):
        """
        Get the count of conversations, optionally filtered by date range.
        Uses cached value for total count if no date filtering is applied.
        
        Args:
            start_date: Optional start date (string YYYY-MM-DD or datetime)
            end_date: Optional end date (string YYYY-MM-DD or datetime)
            use_cache: Whether to use cached values when possible
            
        Returns:
            int: Number of conversations
        """
        # If no date filtering and using cache, return cached total
        if not start_date and not end_date and use_cache and self.total_conversation_count > 0:
            return self.total_conversation_count
            
        # Generate cache key if using cache
        cache_key = None
        if use_cache:
            cache_key = f"count_{start_date}_{end_date}"
            cached_result = self.query_results_cache.get(cache_key)
            if cached_result and (time.time() - cached_result.get('timestamp', 0) < self.cache_ttl):
                return cached_result.get('value', 0)
        
        try:
            session = self.db.session()
            try:
                if start_date or end_date:
                    # Convert date strings to datetime objects if needed
                    start_dt = None
                    if start_date:
                        if isinstance(start_date, str):
                            start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                        else:
                            start_dt = start_date
                    
                    end_dt = None
                    if end_date:
                        if isinstance(end_date, str):
                            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                        else:
                            end_dt = end_date
                    
                    # Efficient raw SQL query for date filtered count
                    query = text("""
                        SELECT COUNT(DISTINCT conversation_id) 
                        FROM messages 
                        WHERE (:start_dt IS NULL OR timestamp >= :start_dt)
                        AND (:end_dt IS NULL OR timestamp <= :end_dt)
                    """)
                    
                    result = session.execute(query, {
                        "start_dt": start_dt,
                        "end_dt": end_dt
                    })
                    
                    count = result.scalar() or 0
                else:
                    # Get total count
                    count = self._get_total_conversation_count()
                
                session.commit()
                
                # Cache the result if using cache
                if use_cache and cache_key:
                    self.query_results_cache.put(cache_key, {
                        'value': count,
                        'timestamp': time.time()
                    })
                
                return count
                
            except Exception as e:
                logging.error(f"Error getting conversation count: {e}", exc_info=True)
                session.rollback()
                return 0
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error creating session for conversation count: {e}", exc_info=True)
            return 0
    
    def get_conversations(self, start_date=None, end_date=None, limit=100, offset=0, use_cache=True):
        """
        Get conversations with pagination and optional date filtering.
        Returns just the metadata (not full transcripts) for efficiency.
        
        Args:
            start_date: Optional start date (string YYYY-MM-DD or datetime)
            end_date: Optional end date (string YYYY-MM-DD or datetime)
            limit: Maximum number of conversations to return
            offset: Offset for pagination
            use_cache: Whether to use cached values when possible
            
        Returns:
            dict: Contains conversations (list) and total_count (int)
        """
        # Generate cache key if using cache
        cache_key = None
        if use_cache:
            cache_key = f"convs_{start_date}_{end_date}_{limit}_{offset}"
            cached_result = self.query_results_cache.get(cache_key)
            if cached_result and (time.time() - cached_result.get('timestamp', 0) < self.cache_ttl):
                return cached_result.get('value', {'conversations': [], 'total_count': 0})
        
        try:
            # Get total count for the query
            total_count = self.get_conversation_count(start_date, end_date, use_cache)
            
            # Fetch conversations with date filtering
            session = self.db.session()
            try:
                # Convert date strings to datetime objects if needed
                start_dt = None
                if start_date:
                    if isinstance(start_date, str):
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    else:
                        start_dt = start_date
                
                end_dt = None
                if end_date:
                    if isinstance(end_date, str):
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                    else:
                        end_dt = end_date
                
                # Query for conversations in date range with efficient pagination
                query = text("""
                    WITH filtered_convs AS (
                        SELECT DISTINCT c.id, c.external_id, c.created_at, c.status
                        FROM conversations c
                        JOIN messages m ON c.id = m.conversation_id
                        WHERE (:start_dt IS NULL OR m.timestamp >= :start_dt)
                        AND (:end_dt IS NULL OR m.timestamp <= :end_dt)
                    )
                    SELECT f.id, f.external_id, f.created_at, f.status,
                           MIN(m.timestamp) as start_time,
                           MAX(m.timestamp) as end_time,
                           COUNT(m.id) as message_count
                    FROM filtered_convs f
                    JOIN messages m ON f.id = m.conversation_id
                    GROUP BY f.id, f.external_id, f.created_at, f.status
                    ORDER BY MIN(m.timestamp) DESC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = session.execute(query, {
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "limit": limit,
                    "offset": offset
                })
                
                conversations = []
                for row in result:
                    # Convert to a dictionary for the response
                    conv_data = {
                        "id": row[0],
                        "conversation_id": row[1],  # external_id
                        "created_at": row[2].isoformat() if row[2] else None,
                        "status": row[3],
                        "start_time": row[4].isoformat() if row[4] else None,
                        "end_time": row[5].isoformat() if row[5] else None,
                        "message_count": row[6]
                    }
                    
                    # Calculate duration if possible
                    if row[4] and row[5]:
                        duration_seconds = int((row[5] - row[4]).total_seconds())
                        conv_data["duration"] = duration_seconds
                    
                    conversations.append(conv_data)
                    
                    # Also update cache while we're at it
                    if use_cache:
                        cache_key = f"conv_meta_{row[1]}"  # external_id as key
                        self.conversation_metadata_cache.put(cache_key, {
                            "id": row[0],
                            "external_id": row[1],
                            "created_at": row[2],
                            "start_time": row[4],
                            "end_time": row[5],
                            "message_count": row[6],
                            "duration": conv_data.get("duration"),
                            "cached_at": time.time()
                        })
                        self._loaded_conversation_ids.add(row[1])  # external_id
                
                session.commit()
                
                result = {
                    'conversations': conversations,
                    'total_count': total_count
                }
                
                # Cache the result if using cache
                if use_cache and cache_key:
                    self.query_results_cache.put(cache_key, {
                        'value': result,
                        'timestamp': time.time()
                    })
                
                return result
                
            except Exception as e:
                logging.error(f"Error getting conversations: {e}", exc_info=True)
                session.rollback()
                return {'conversations': [], 'total_count': 0}
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error creating session for getting conversations: {e}", exc_info=True)
            return {'conversations': [], 'total_count': 0}
    
    def get_conversation_details(self, conversation_id, use_cache=True):
        """
        Get full details for a specific conversation including transcript.
        
        Args:
            conversation_id: The conversation ID (external_id)
            use_cache: Whether to use cached values when possible
            
        Returns:
            dict: Full conversation data with transcript
        """
        # Check cache first if using cache
        if use_cache:
            cache_key = f"conv_full_{conversation_id}"
            cached_result = self.conversation_full_cache.get(cache_key)
            if cached_result and (time.time() - cached_result.get('cached_at', 0) < self.cache_ttl):
                return cached_result
        
        try:
            session = self.db.session()
            try:
                # First get the conversation metadata
                conv_query = text("""
                    SELECT c.id, c.external_id, c.created_at, c.status
                    FROM conversations c
                    WHERE CAST(c.external_id AS VARCHAR) = CAST(:external_id AS VARCHAR)
                """)
                
                conv_result = session.execute(conv_query, {"external_id": conversation_id})
                conv_row = conv_result.fetchone()
                
                if not conv_row:
                    logging.warning(f"Conversation {conversation_id} not found")
                    return None
                
                # Now get all messages for this conversation
                msg_query = text("""
                    SELECT m.id, m.speaker, m.text, m.timestamp
                    FROM messages m
                    WHERE m.conversation_id = :conv_id
                    ORDER BY m.timestamp
                """)
                
                msg_result = session.execute(msg_query, {"conv_id": conv_row[0]})
                
                messages = []
                for msg_row in msg_result:
                    message = {
                        "id": msg_row[0],
                        "speaker": msg_row[1],
                        "text": msg_row[2],
                        "timestamp": msg_row[3].isoformat() if msg_row[3] else None
                    }
                    messages.append(message)
                
                # Calculate start time, end time, and duration
                timestamps = sorted([msg["timestamp"] for msg in messages if msg["timestamp"]])
                start_time = timestamps[0] if timestamps else None
                end_time = timestamps[-1] if len(timestamps) > 0 else None
                duration = None
                
                if start_time and end_time:
                    start_dt = datetime.fromisoformat(start_time)
                    end_dt = datetime.fromisoformat(end_time)
                    duration = int((end_dt - start_dt).total_seconds())
                
                # Format transcript for consistent structure
                transcript = []
                for msg in messages:
                    transcript.append({
                        "role": "user" if msg["speaker"] == "Curious Caller" else "assistant",
                        "content": msg["text"],
                        "timestamp": msg["timestamp"]
                    })
                
                # Build the final conversation object
                conversation = {
                    "conversation_id": conv_row[1],  # external_id
                    "id": conv_row[0],  # internal id
                    "created_at": conv_row[2].isoformat() if conv_row[2] else None,
                    "status": conv_row[3],
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "message_count": len(messages),
                    "transcript": transcript,
                    "messages": messages,  # Include raw messages for compatibility
                    "cached_at": time.time()
                }
                
                session.commit()
                
                # Cache the result if using cache
                if use_cache:
                    cache_key = f"conv_full_{conversation_id}"
                    self.conversation_full_cache.put(cache_key, conversation)
                    
                    # Also update metadata cache
                    meta_key = f"conv_meta_{conversation_id}"
                    self.conversation_metadata_cache.put(meta_key, {
                        "id": conv_row[0],
                        "external_id": conv_row[1],
                        "created_at": conv_row[2],
                        "start_time": start_time,
                        "end_time": end_time,
                        "message_count": len(messages),
                        "duration": duration,
                        "cached_at": time.time()
                    })
                    self._loaded_conversation_ids.add(conv_row[1])  # external_id
                
                return conversation
                
            except Exception as e:
                logging.error(f"Error getting conversation details for {conversation_id}: {e}", exc_info=True)
                session.rollback()
                return None
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error creating session for conversation details: {e}", exc_info=True)
            return None
    
    def get_conversation_ids(self, start_date=None, end_date=None, limit=1000, offset=0):
        """
        Get conversation IDs with optional date filtering.
        
        Args:
            start_date: Optional start date (string YYYY-MM-DD or datetime)
            end_date: Optional end date (string YYYY-MM-DD or datetime)
            limit: Maximum number of IDs to return
            offset: Pagination offset
            
        Returns:
            dict: Contains conversation_ids (list) and total_count (int)
        """
        # Generate cache key
        cache_key = f"ids_{start_date}_{end_date}_{limit}_{offset}"
        cached_result = self.query_results_cache.get(cache_key)
        if cached_result and (time.time() - cached_result.get('timestamp', 0) < self.cache_ttl):
            return cached_result.get('value', {'conversation_ids': [], 'total_count': 0})
        
        try:
            # Get total count for the query
            total_count = self.get_conversation_count(start_date, end_date)
            
            # Fetch conversation IDs with date filtering
            session = self.db.session()
            try:
                # Convert date strings to datetime objects if needed
                start_dt = None
                if start_date:
                    if isinstance(start_date, str):
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    else:
                        start_dt = start_date
                
                end_dt = None
                if end_date:
                    if isinstance(end_date, str):
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                    else:
                        end_dt = end_date
                
                # Use a more efficient query with proper joining
                query = text("""
                    SELECT DISTINCT c.id, c.external_id
                    FROM conversations c
                    JOIN messages m ON c.id = m.conversation_id
                    WHERE (:start_dt IS NULL OR m.timestamp >= :start_dt)
                    AND (:end_dt IS NULL OR m.timestamp <= :end_dt)
                    ORDER BY c.id
                    LIMIT :limit OFFSET :offset
                """)
                
                result = session.execute(query, {
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "limit": limit,
                    "offset": offset
                })
                
                # Extract conversation IDs (both internal and external)
                conversation_ids = []
                for row in result:
                    conversation_ids.append({
                        'id': row[0],
                        'external_id': row[1]
                    })
                
                session.commit()
                
                # Create the result structure
                result = {
                    'conversation_ids': conversation_ids,
                    'total_count': total_count
                }
                
                # Cache the result
                self.query_results_cache.put(cache_key, {
                    'value': result,
                    'timestamp': time.time()
                })
                
                return result
                
            except Exception as e:
                logging.error(f"Error getting conversation IDs: {e}", exc_info=True)
                session.rollback()
                return {'conversation_ids': [], 'total_count': 0}
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error creating session for conversation IDs: {e}", exc_info=True)
            return {'conversation_ids': [], 'total_count': 0}
    
    def get_conversations_with_transcripts(self, start_date=None, end_date=None, limit=100, batch_size=20):
        """
        Get conversations with full transcripts using efficient batch processing.
        
        Args:
            start_date: Optional start date (string YYYY-MM-DD or datetime)
            end_date: Optional end date (string YYYY-MM-DD or datetime)
            limit: Maximum total conversations to return
            batch_size: Number of conversations to process at once
            
        Returns:
            list: List of conversation objects with transcripts
        """
        # Get conversation IDs first
        result = self.get_conversation_ids(start_date, end_date, limit=limit)
        
        if not result or not result.get('conversation_ids'):
            logging.warning(f"No conversation IDs found for date range: {start_date} to {end_date}")
            return []
        
        conversation_ids = result.get('conversation_ids', [])
        logging.info(f"Found {len(conversation_ids)} conversation IDs, fetching details in batches of {batch_size}")
        
        # Process in batches for efficiency
        conversations = []
        total_processed = 0
        
        for i in range(0, len(conversation_ids), batch_size):
            batch = conversation_ids[i:i+batch_size]
            batch_size = len(batch)
            
            logging.info(f"Processing batch {i//batch_size + 1}/{(len(conversation_ids) + batch_size - 1)//batch_size} with {batch_size} conversations")
            
            # Fetch each conversation in the batch
            for conv_id_obj in batch:
                conv_id = conv_id_obj.get('external_id')
                conversation = self.get_conversation_details(conv_id)
                
                if conversation:
                    conversations.append(conversation)
                    total_processed += 1
                    
                    # Check if we've reached the limit
                    if total_processed >= limit:
                        break
            
            # Check if we've reached the limit
            if total_processed >= limit:
                break
        
        logging.info(f"Successfully fetched {len(conversations)} conversations with transcripts")
        
        return conversations
    
    def clear_cache(self, cache_type=None):
        """
        Clear the cache.
        
        Args:
            cache_type: Type of cache to clear (metadata, full, query, or all)
        """
        if cache_type == "metadata" or cache_type is None or cache_type == "all":
            self.conversation_metadata_cache.clear()
            self._loaded_conversation_ids = set()
            logging.info("Cleared conversation metadata cache")
            
        if cache_type == "full" or cache_type is None or cache_type == "all":
            self.conversation_full_cache.clear()
            logging.info("Cleared conversation full data cache")
            
        if cache_type == "query" or cache_type is None or cache_type == "all":
            self.query_results_cache.clear()
            logging.info("Cleared query results cache")
    
    def get_cache_stats(self):
        """Get statistics about the cache."""
        return {
            "metadata_cache_size": self.conversation_metadata_cache.size(),
            "full_cache_size": self.conversation_full_cache.size(),
            "query_results_cache_size": self.query_results_cache.size(),
            "loaded_conversation_ids": len(self._loaded_conversation_ids),
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "total_conversation_count": self.total_conversation_count,
            "initialized": self.initialized
        }
    
    def sync(self, force=False):
        """
        Sync the cache with the database.
        
        Args:
            force: Whether to force a full sync regardless of last sync time
            
        Returns:
            dict: Sync statistics
        """
        start_time = time.time()
        
        # Check if sync is needed
        if not force and self.last_sync_time:
            time_since_last_sync = datetime.now(timezone.utc) - self.last_sync_time
            if time_since_last_sync < timedelta(minutes=5):
                logging.info(f"Sync not needed, last sync was {time_since_last_sync.total_seconds():.1f}s ago")
                return {
                    "synced": False,
                    "reason": "Recent sync",
                    "last_sync_time": self.last_sync_time.isoformat(),
                    "time_since_last_sync": time_since_last_sync.total_seconds()
                }
        
        with self.metadata_load_lock:
            try:
                # Update total conversation count
                new_count = self._get_total_conversation_count()
                count_changed = new_count != self.total_conversation_count
                self.total_conversation_count = new_count
                
                # Reload metadata if count changed or forced
                if count_changed or force:
                    self._load_conversation_metadata(limit=1000, clear_existing=(force))
                
                self.last_sync_time = datetime.now(timezone.utc)
                
                return {
                    "synced": True,
                    "count_changed": count_changed,
                    "old_count": self.total_conversation_count,
                    "new_count": new_count,
                    "force": force,
                    "duration_seconds": time.time() - start_time,
                    "last_sync_time": self.last_sync_time.isoformat()
                }
                
            except Exception as e:
                logging.error(f"Error syncing cache: {e}", exc_info=True)
                return {
                    "synced": False,
                    "error": str(e),
                    "duration_seconds": time.time() - start_time
                } 