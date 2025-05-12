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
    """Generate a unique key for the cache based on the function name and arguments"""
    safe_args_parts = []
    for arg in args:
        if hasattr(arg, '__dict__'):
            safe_args_parts.append(f"{arg.__class__.__name__}_{id(arg)}")
        else:
            try:
                json.dumps(arg) # Check if serializable
                safe_args_parts.append(repr(arg)) # Use repr for more uniqueness than str for some types
            except (TypeError, OverflowError):
                safe_args_parts.append(str(arg))
    
    safe_kwargs_parts = []
    for key, value in sorted(kwargs.items()):
        if hasattr(value, '__dict__'):
            safe_kwargs_parts.append(f"{key}={value.__class__.__name__}_{id(value)}")
        else:
            try:
                json.dumps(value) # Check if serializable
                safe_kwargs_parts.append(f"{key}={repr(value)}") # Use repr
            except (TypeError, OverflowError):
                safe_kwargs_parts.append(f"{key}={str(value)}")
    
    # Combine all parts for the full argument signature string
    full_args_signature = "_".join(safe_args_parts) + "__" + "_".join(safe_kwargs_parts)
    
    # Limit the length of the unhashed signature part to avoid overly long filenames
    # If the signature itself is very long, hash it.
    MAX_SIG_LEN = 180 # Max length for the signature part of the key
    if len(full_args_signature) > MAX_SIG_LEN:
        hashed_signature = hashlib.md5(full_args_signature.encode('utf-8')).hexdigest()
        key_suffix = f"hashed_{hashed_signature}"
    elif not full_args_signature: # Handle case with no args/kwargs
        key_suffix = "noargs"
    else:
        # Sanitize the signature string to be filename-safe (basic sanitization)
        # Remove/replace characters that are problematic in filenames
        sanitized_signature = full_args_signature.replace("[", "_").replace("]", "_") \
                                                .replace("{", "_").replace("}", "_") \
                                                .replace("\"", "").replace("'", "") \
                                                .replace(",", "-").replace(": ", "=") \
                                                .replace(" ", "")
        key_suffix = sanitized_signature[:MAX_SIG_LEN] # Truncate if slightly over after sanitizing

    final_key = f"{func_name}_{key_suffix}"
    
    # This final length check is mostly a safeguard; primary length control is MAX_SIG_LEN
    if len(final_key) > 240:
        # If even after truncation/hashing the func_name makes it too long, hash the whole thing
        logging.warning(f"Cache key for {func_name} still too long, fully hashing. Key: {final_key[:100]}")
        return hashlib.md5(f"{func_name}_{full_args_signature}".encode('utf-8')).hexdigest()
        
    return final_key

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