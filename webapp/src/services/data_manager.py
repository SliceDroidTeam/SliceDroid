"""
Data Manager Service - Centralized data loading and caching.
"""

import json
from pathlib import Path


class DataManager:
    """Centralized data management with caching."""
    
    def __init__(self, config_class):
        self.config = config_class
        self._data_cache = {}
        self._cache_timestamp = None
        self._metadata_cache = {}
    
    def load_events(self):
        """
        Load events data with intelligent caching.
        
        Returns:
            list: Events data
        """
        events_file = self.config.PROCESSED_EVENTS_JSON

        try:
            if not Path(events_file).exists():
                return []

            file_mtime = Path(events_file).stat().st_mtime

            # Use cache if file hasn't changed
            if self._cache_timestamp == file_mtime and 'events' in self._data_cache:
                return self._data_cache['events']

            # Load fresh data
            with open(events_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []

            # Update cache and clear metadata cache when file changes
            self._data_cache['events'] = data
            self._cache_timestamp = file_mtime
            self._metadata_cache.clear()

            return data
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading data from {events_file}: {e}")
            return []
    
    def save_events(self, events):
        """
        Save events data to file.
        
        Args:
            events: Events data to save
        """
        events_file = self.config.PROCESSED_EVENTS_JSON
        
        try:
            # Ensure directory exists
            events_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self._data_cache['events'] = events
            self._cache_timestamp = Path(events_file).stat().st_mtime
            self._metadata_cache.clear()
            
        except Exception as e:
            print(f"Error saving events to {events_file}: {e}")
            raise
    
    def get_cached_metadata(self, key):
        """
        Get cached metadata.
        
        Args:
            key: Metadata key
            
        Returns:
            Cached value or None
        """
        return self._metadata_cache.get(key)
    
    def set_cached_metadata(self, key, value):
        """
        Set cached metadata.
        
        Args:
            key: Metadata key
            value: Value to cache
        """
        self._metadata_cache[key] = value
    
    def clear_cache(self):
        """Clear all cached data."""
        self._data_cache.clear()
        self._metadata_cache.clear()
        self._cache_timestamp = None
    
    def get_cache_info(self):
        """
        Get cache information.
        
        Returns:
            dict: Cache status information
        """
        return {
            'has_events': 'events' in self._data_cache,
            'events_count': len(self._data_cache.get('events', [])),
            'cache_timestamp': self._cache_timestamp,
            'metadata_keys': list(self._metadata_cache.keys())
        }