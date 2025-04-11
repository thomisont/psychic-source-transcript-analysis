"""
Caching utilities for API responses.
"""
import time
import json
import hashlib
import logging
import os
from datetime import datetime, timedelta
from functools import wraps

# Helper function to serialize datetime objects for JSON
def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

class SimpleCache:
    """Simple in-memory cache with expiration."""
    
    def __init__(self, cache_dir=None, max_size=100):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files (None for in-memory only)
            max_size: Maximum number of items to keep in memory
        """
        self.cache = {}
        self.cache_dir = cache_dir
        self.max_size = max_size
        
        # Create cache directory if it doesn't exist
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
    
    def get(self, key, default=None):
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if key not found or expired
            
        Returns:
            Cached value or default
        """
        # Try in-memory cache first
        cache_item = self.cache.get(key)
        if cache_item:
            # Check if expired
            if cache_item['expires'] > time.time():
                logging.debug(f"Cache hit for key: {key}")
                return cache_item['value']
            else:
                # Remove expired item
                logging.debug(f"Cache expired for key: {key}")
                del self.cache[key]
        
        # If cache_dir is set, try to load from file
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        cache_item = json.load(f)
                        
                    # Check if expired
                    if cache_item['expires'] > time.time():
                        # Restore to in-memory cache
                        self.cache[key] = cache_item
                        logging.debug(f"File cache hit for key: {key}")
                        return cache_item['value']
                    else:
                        # Remove expired file
                        logging.debug(f"File cache expired for key: {key}")
                        os.remove(cache_file)
                except Exception as e:
                    logging.warning(f"Error reading cache file {cache_file}: {e}")
        
        return default
    
    def set(self, key, value, ttl=3600):
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        # Create cache item with expiration
        cache_item = {
            'value': value,
            'expires': time.time() + ttl
        }
        
        # Store in memory
        self.cache[key] = cache_item
        
        # Ensure cache doesn't exceed max size
        if len(self.cache) > self.max_size:
            # Remove oldest items
            items = sorted(self.cache.items(), key=lambda x: x[1]['expires'])
            self.cache = dict(items[-(self.max_size):])
        
        # Write to file cache if directory is set
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            try:
                with open(cache_file, 'w') as f:
                    # Use the custom serializer for datetime objects
                    json.dump(cache_item, f, default=datetime_serializer)
                logging.debug(f"Wrote item to file cache: {key}")
            except Exception as e:
                # Log the specific key and error
                logging.warning(f"Error writing cache file for key '{key}' ({cache_file}): {e}")
    
    def delete(self, key):
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        # Remove from memory
        if key in self.cache:
            del self.cache[key]
        
        # Remove from file system
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                    logging.debug(f"Deleted cache file: {cache_file}")
                except Exception as e:
                    logging.warning(f"Error deleting cache file {cache_file}: {e}")
    
    def clear(self):
        """Clear all cached values."""
        # Clear memory cache
        self.cache = {}
        
        # Clear file cache
        if self.cache_dir and os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                    except Exception as e:
                        logging.warning(f"Error deleting cache file {filename}: {e}")

# Create a global cache instance
cache = SimpleCache(cache_dir='instance/cache', max_size=500)

def cache_key(func_name, *args, **kwargs):
    """Generate a unique key for the cache based on the function name and arguments

    Args:
        func_name (str): Name of the function being called
        *args: Positional arguments to the function
        **kwargs: Keyword arguments to the function

    Returns:
        str: A unique key for the cache
    """
    # Convert args to a JSON-safe format
    safe_args = []
    for arg in args:
        if hasattr(arg, '__dict__'):
            # For objects, use their class name and id as a unique identifier
            arg_class = arg.__class__.__name__
            arg_id = id(arg)
            safe_args.append(f"{arg_class}_{arg_id}")
        else:
            # For primitive types, use them directly
            try:
                # Check if JSON serializable
                json.dumps(arg)
                safe_args.append(arg)
            except (TypeError, OverflowError):
                # If not serializable, use string representation
                safe_args.append(str(arg))
    
    # Convert kwargs to a JSON-safe format
    safe_kwargs = {}
    for key, value in sorted(kwargs.items()):
        if hasattr(value, '__dict__'):
            # For objects, use their class name and id as a unique identifier
            value_class = value.__class__.__name__
            value_id = id(value)
            safe_kwargs[key] = f"{value_class}_{value_id}"
        else:
            # For primitive types, use them directly
            try:
                # Check if JSON serializable
                json.dumps(value)
                safe_kwargs[key] = value
            except (TypeError, OverflowError):
                # If not serializable, use string representation
                safe_kwargs[key] = str(value)
    
    # Create a string with the function name and safe args/kwargs
    try:
        arg_string = json.dumps(safe_args, sort_keys=True) if safe_args else ''
        kwarg_string = json.dumps(safe_kwargs, sort_keys=True) if safe_kwargs else ''
        return f"{func_name}_{arg_string}_{kwarg_string}"
    except Exception as e:
        # Fallback if JSON serialization fails
        logging.error(f"Error creating cache key: {e}")
        return f"{func_name}_{hash(str(safe_args))}_{hash(str(safe_kwargs))}"

def cache_api_response(ttl=3600):
    """
    Decorator to cache API responses.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check for force_refresh parameter
            force_refresh = kwargs.pop('force_refresh', False) if 'force_refresh' in kwargs else False
            
            # Generate cache key (excluding force_refresh parameter)
            key = cache_key(func.__name__, *args, **kwargs)
            
            # If force_refresh is True, skip cache lookup
            if not force_refresh:
                # Try to get from cache
                cached_value = cache.get(key)
                if cached_value is not None:
                    return cached_value
            
            # Call function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator 