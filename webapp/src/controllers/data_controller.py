"""
Data Controller - Handles data loading, processing, and export operations.
"""

import json
import pandas as pd
from io import StringIO
from pathlib import Path

from .base_controller import BaseController
from src.services.data_manager import DataManager


class DataController(BaseController):
    """Controller for data operations."""
    
    def __init__(self, config_class):
        super().__init__(config_class)
        self.data_manager = DataManager(config_class)
    
    def load_events_data(self):
        """
        Load events data with caching.
        
        Returns:
            list: Events data or empty list if error
        """
        return self.data_manager.load_events()
    
    def get_unique_pids(self, events=None):
        """
        Get unique PIDs from events with caching.
        
        Args:
            events: Optional events list, otherwise loads from cache
            
        Returns:
            list: Sorted list of unique PIDs
        """
        if events is None:
            events = self.load_events_data()
            
        # Check cache first
        cached_pids = self.data_manager.get_cached_metadata('pids')
        if cached_pids is not None:
            return cached_pids

        pids = set()
        for event in events:
            if 'tgid' in event:
                pids.add(event['tgid'])

        sorted_pids = sorted(list(pids))
        self.data_manager.set_cached_metadata('pids', sorted_pids)
        return sorted_pids
    
    def get_unique_devices(self, events=None):
        """
        Get unique devices from events with caching.
        
        Args:
            events: Optional events list, otherwise loads from cache
            
        Returns:
            list: Sorted list of unique device IDs
        """
        if events is None:
            events = self.load_events_data()
            
        # Check cache first
        cached_devices = self.data_manager.get_cached_metadata('devices')
        if cached_devices is not None:
            return cached_devices

        devices = set()
        for event in events:
            details = event.get('details')
            if details:
                device_id = details.get('k_dev') or details.get('k__dev')
                if device_id and device_id != 0:
                    devices.add(device_id)

        sorted_devices = sorted(list(devices))
        self.data_manager.set_cached_metadata('devices', sorted_devices)
        return sorted_devices
    
    def create_timeline_data(self, events):
        """
        Create timeline data for visualization.
        
        Args:
            events: List of events
            
        Returns:
            list: Timeline data for frontend
        """
        timeline_data = []

        for idx, event in enumerate(events):
            if not isinstance(event, dict):
                continue

            event_type = event.get('event', 'unknown')
            category = self.config.get_event_category(event_type)

            # Get device info
            device = None
            pathname = None
            if 'details' in event and isinstance(event['details'], dict):
                device = event['details'].get('k_dev') or event['details'].get('k__dev')
                pathname = event['details'].get('pathname', None)

            timeline_data.append({
                'id': idx,
                'time': idx,
                'event': event_type,
                'category': category,
                'device': device,
                'pathname': pathname,
                'pid': event.get('tgid', None),
                'tid': event.get('tid', None),
            })

        return timeline_data
    
    def create_device_stats(self, events):
        """
        Create device usage statistics.
        
        Args:
            events: List of events
            
        Returns:
            list: Device statistics
        """
        device_counts = {}
        device_paths = {}

        for event in events:
            if 'details' in event:
                device = event['details'].get('k_dev') or event['details'].get('k__dev')
                if not device or device == 0:
                    continue

                # Count device usage
                if device not in device_counts:
                    device_counts[device] = 0
                device_counts[device] += 1

                # Track pathnames for each device
                if 'pathname' in event['details'] and event['details']['pathname']:
                    if device not in device_paths:
                        device_paths[device] = set()
                    device_paths[device].add(event['details']['pathname'])

        # Convert to list of dictionaries
        device_stats = []
        for device, count in sorted(device_counts.items(), key=lambda x: x[1], reverse=True):
            paths = list(device_paths.get(device, []))
            device_stats.append({
                'device': device,
                'count': count,
                'paths': paths,
                'path_count': len(paths)
            })

        return device_stats
    
    def create_event_stats(self, events):
        """
        Create event type statistics.
        
        Args:
            events: List of events
            
        Returns:
            list: Event type statistics
        """
        event_counts = {}

        for event in events:
            event_type = event.get('event', 'unknown')
            if event_type not in event_counts:
                event_counts[event_type] = 0
            event_counts[event_type] += 1

        return [{'event': k, 'count': v} for k, v in
                sorted(event_counts.items(), key=lambda x: x[1], reverse=True)]
    
    
    def export_events(self, events, format_type='json', limit=None):
        """
        Export events in specified format.
        
        Args:
            events: Events to export
            format_type: 'json' or 'csv'
            limit: Optional limit on number of events
            
        Returns:
            dict: Export result with content and metadata
        """
        try:
            # Apply limit if specified
            export_events = events
            if limit:
                try:
                    limit_int = int(limit)
                    export_events = events[:limit_int]
                except ValueError:
                    return {'error': 'Invalid limit parameter'}

            # Generate timestamp for filename
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            filename_parts = ['events', timestamp]

            if format_type.lower() == 'csv':
                # Create CSV
                df = pd.DataFrame(export_events)
                output = StringIO()
                df.to_csv(output, index=False)
                
                filename = '_'.join(filename_parts) + '.csv'
                return {
                    'content': output.getvalue(),
                    'filename': filename,
                    'content_type': 'text/csv'
                }
            else:
                # JSON format
                filename = '_'.join(filename_parts) + '.json'
                return {
                    'content': json.dumps(export_events, indent=2),
                    'filename': filename,
                    'content_type': 'application/json'
                }
                
        except Exception as e:
            return self.handle_error(e, "Export events")
    
    def process_tcp_events(self, events):
        """
        Extract and process TCP state events.
        
        Args:
            events: List of events
            
        Returns:
            list: TCP events data
        """
        tcp_events = []
        for event in events:
            if event.get('event') == "inet_sock_set_state":
                tcp_events.append({
                    'time': tcp_events[-1]['time'] + 1 if tcp_events else 0,
                    'state': event['details'].get('newstate', 'unknown'),
                    'daddr': event['details'].get('daddr', 'unknown'),
                    'saddr': event['details'].get('saddr', 'unknown'),
                    'sport': event['details'].get('sport', 'unknown'),
                    'dport': event['details'].get('dport', 'unknown'),
                    'pid': event.get('tgid', None),
                    'tid': event.get('tid', None),
                })
        return tcp_events