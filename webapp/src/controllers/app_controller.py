"""
App Controller - Handles app-related operations including trace upload and analysis.
"""

import json
import tempfile
import shutil
import uuid
import threading
import time
from pathlib import Path
from werkzeug.utils import secure_filename

from .base_controller import BaseController
from ..services.trace_processor import TraceProcessor
from ..services.app_mapper_service import AppMapperService


class AppController(BaseController):
    """Controller for application-related operations."""
    
    def __init__(self, config_class):
        super().__init__(config_class)
        self.trace_processor = TraceProcessor(config_class)
        self.app_mapper_service = AppMapperService(Path(config_class.PROJECT_ROOT))
        self.processing_status = {}
        self.processing_lock = threading.Lock()
    
    def get_apps(self, category=None, search=None):
        """
        Get all available apps, optionally filtered by category or search term.
        
        Args:
            category: Optional category filter
            search: Optional search term
            
        Returns:
            dict: Apps data or error
        """
        try:
            if search:
                apps = self.app_mapper_service.search_apps(search)
            else:
                apps = self.app_mapper_service.get_all_apps(category)
            
            # Convert AppInfo objects to dictionaries
            apps_data = []
            for app in apps:
                app_dict = self.app_mapper_service.to_dict(app)
                apps_data.append(app_dict)
            
            # Get additional stats
            stats = self.app_mapper_service.get_app_stats()
            categories = self.app_mapper_service.get_categories()
            
            return {
                'success': True,
                'apps': apps_data,
                'stats': stats,
                'categories': categories,
                'total_count': len(apps_data)
            }
            
        except Exception as e:
            return self.handle_error(e, "Getting apps")
    
    def upload_trace(self, file, target_app=None):
        """
        Upload and process a trace file.
        
        Args:
            file: Uploaded file object
            target_app: Optional target app name
            
        Returns:
            dict: Upload result with processing status
        """
        try:
            # Validate file
            if not file or not file.filename:
                return {'error': 'No file provided'}
            
            if not file.filename.endswith('.trace'):
                return {'error': 'File must have .trace extension'}
            
            # Secure the filename
            filename = secure_filename(file.filename)
            if not filename:
                filename = 'uploaded_trace.trace'
            
            # Create temporary file
            temp_dir = Path(tempfile.gettempdir())
            temp_file = temp_dir / f"upload_{uuid.uuid4()}_{filename}"
            
            try:
                # Save uploaded file
                file.save(str(temp_file))
                
                # Move to traces directory
                traces_dir = Path(self.config.TRACES_DIR)
                traces_dir.mkdir(parents=True, exist_ok=True)
                
                final_path = traces_dir / filename
                shutil.move(str(temp_file), str(final_path))
                
                # Start processing in background
                processing_id = str(uuid.uuid4())
                
                with self.processing_lock:
                    self.processing_status[processing_id] = {
                        'status': 'queued',
                        'progress': 0,
                        'message': 'Upload complete, processing queued...',
                        'file_path': str(final_path),
                        'target_app': target_app
                    }
                
                # Start background processing
                thread = threading.Thread(
                    target=self._process_trace_background,
                    args=(processing_id, str(final_path), target_app)
                )
                thread.daemon = True
                thread.start()
                
                return {
                    'success': True,
                    'message': 'File uploaded successfully',
                    'processing_id': processing_id,
                    'filename': filename
                }
                
            except Exception as e:
                # Clean up temp file if it exists
                if temp_file.exists():
                    temp_file.unlink()
                raise e
                
        except Exception as e:
            return self.handle_error(e, "Uploading trace file")
    
    def _process_trace_background(self, processing_id, file_path, target_app=None):
        """
        Process trace file in background thread.
        
        Args:
            processing_id: Unique processing identifier
            file_path: Path to trace file
            target_app: Optional target app name
        """
        def update_progress(progress, message):
            with self.processing_lock:
                if processing_id in self.processing_status:
                    self.processing_status[processing_id].update({
                        'progress': progress,
                        'message': message,
                        'status': 'processing'
                    })
        
        try:
            update_progress(10, "Starting trace processing...")
            
            # Process the trace file
            result = self.trace_processor.process_trace_file(
                file_path,
                progress_callback=update_progress,
                target_app=target_app
            )
            
            with self.processing_lock:
                if processing_id in self.processing_status:
                    if result['success']:
                        self.processing_status[processing_id].update({
                            'status': 'completed',
                            'progress': 100,
                            'message': result['message'],
                            'result': result
                        })
                    else:
                        self.processing_status[processing_id].update({
                            'status': 'failed',
                            'progress': 0,
                            'message': result.get('error', 'Processing failed'),
                            'error': result.get('error')
                        })
            
        except Exception as e:
            with self.processing_lock:
                if processing_id in self.processing_status:
                    self.processing_status[processing_id].update({
                        'status': 'failed',
                        'progress': 0,
                        'message': f'Processing failed: {str(e)}',
                        'error': str(e)
                    })
    
    def get_processing_status(self, processing_id):
        """
        Get processing status for a trace upload.
        
        Args:
            processing_id: Processing identifier
            
        Returns:
            dict: Processing status or error
        """
        try:
            with self.processing_lock:
                if processing_id not in self.processing_status:
                    return {'error': 'Processing ID not found'}
                
                status = self.processing_status[processing_id].copy()
                
                # Clean up completed/failed processes after some time
                if status['status'] in ['completed', 'failed']:
                    # Keep status for 5 minutes after completion
                    if 'completion_time' not in status:
                        status['completion_time'] = time.time()
                        self.processing_status[processing_id]['completion_time'] = status['completion_time']
                    elif time.time() - status['completion_time'] > 300:  # 5 minutes
                        del self.processing_status[processing_id]
                
                return {'success': True, 'status': status}
                
        except Exception as e:
            return self.handle_error(e, "Getting processing status")
    
    def analyze_app(self, app_identifier, events_data=None):
        """
        Analyze a specific app using trace events.
        
        Args:
            app_identifier: App package name or commercial name
            events_data: Optional events data (if not provided, will load from exports)
            
        Returns:
            dict: Analysis results or error
        """
        try:
            # Get app information
            app = self.app_mapper_service.get_app_by_package(app_identifier)
            if not app:
                app = self.app_mapper_service.get_app_by_commercial_name(app_identifier)
            
            if not app:
                return {'error': f'App not found: {app_identifier}'}
            
            # Load events if not provided
            if events_data is None:
                events_file = Path(self.config.EXPORTS_DIR) / 'processed_events.json'
                if not events_file.exists():
                    return {'error': 'No processed events found. Please upload and process a trace file first.'}
                
                try:
                    with open(events_file, 'r', encoding='utf-8') as f:
                        events_data = json.load(f)
                except Exception as e:
                    return {'error': f'Failed to load events data: {str(e)}'}
            
            if not events_data:
                return {'error': 'No events data available'}
            
            # Get PIDs for the app from trace events
            app_pids = self.app_mapper_service.get_pids_for_app(app_identifier, events_data)
            
            # Debug fix: Check if app_pids is a list
            if not isinstance(app_pids, list):
                app_pids = [app_pids] if app_pids is not None else []
            
            if not app_pids:
                return {
                    'error': f'No PIDs found for app {app.commercial_name} in trace events',
                    'app_info': self.app_mapper_service.to_dict(app),
                    'process_names': app.processes
                }
            
            # Filter events for this app
            app_events = []
            for event in events_data:
                if event.get('tgid') in app_pids:
                    app_events.append(event)
            
            if not app_events:
                return {
                    'error': f'No events found for app {app.commercial_name}',
                    'app_info': self.app_mapper_service.to_dict(app),
                    'pids': app_pids
                }
            
            # Analyze app events
            analysis_result = {
                'success': True,
                'app_info': self.app_mapper_service.to_dict(app),
                'pids': app_pids,
                'events_count': len(app_events),
                'total_events_count': len(events_data),
                'analysis': {
                    'event_categories': self._categorize_app_events(app_events),
                    'timeline': self._create_event_timeline(app_events),
                    'summary': self._create_app_summary(app, app_events, app_pids)
                }
            }
            
            return analysis_result
            
        except Exception as e:
            return self.handle_error(e, f"Analyzing app {app_identifier}")
    
    def _categorize_app_events(self, events):
        """
        Categorize events by type for analysis.
        
        Args:
            events: List of events to categorize
            
        Returns:
            dict: Event counts by category
        """
        categories = {}
        for event in events:
            category = event.get('category', 'other')
            categories[category] = categories.get(category, 0) + 1
        
        return categories
    
    def _create_event_timeline(self, events, max_points=100):
        """
        Create a timeline of events for visualization.
        
        Args:
            events: List of events
            max_points: Maximum timeline points to return
            
        Returns:
            list: Timeline data points
        """
        if not events:
            return []
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda x: x.get('timestamp', 0))
        
        # Create timeline buckets
        start_time = sorted_events[0].get('timestamp', 0)
        end_time = sorted_events[-1].get('timestamp', 0)
        
        if start_time == end_time:
            return [{'time': start_time, 'count': len(events)}]
        
        time_span = end_time - start_time
        bucket_size = time_span / max_points
        
        timeline = []
        current_bucket_start = start_time
        
        for i in range(max_points):
            bucket_end = current_bucket_start + bucket_size
            bucket_events = [
                e for e in sorted_events
                if current_bucket_start <= e.get('timestamp', 0) < bucket_end
            ]
            
            if bucket_events or i == 0:  # Always include first bucket
                timeline.append({
                    'time': current_bucket_start,
                    'count': len(bucket_events)
                })
            
            current_bucket_start = bucket_end
        
        return timeline
    
    def _create_app_summary(self, app, events, pids):
        """
        Create a summary of app analysis.
        
        Args:
            app: AppInfo object
            events: List of app events
            pids: List of PIDs for the app
            
        Returns:
            dict: App analysis summary
        """
        if not events:
            return {
                'total_events': 0,
                'time_span': 0,
                'most_active_pid': None,
                'dominant_category': None
            }
        
        # Time span analysis
        timestamps = [e.get('timestamp', 0) for e in events if e.get('timestamp')]
        time_span = max(timestamps) - min(timestamps) if timestamps else 0
        
        # PID activity analysis
        pid_activity = {}
        for event in events:
            pid = event.get('tgid')
            if pid:
                pid_activity[pid] = pid_activity.get(pid, 0) + 1
        
        most_active_pid = max(pid_activity.items(), key=lambda x: x[1])[0] if pid_activity else None
        
        # Category analysis
        categories = self._categorize_app_events(events)
        dominant_category = max(categories.items(), key=lambda x: x[1])[0] if categories else None
        
        return {
            'total_events': len(events),
            'time_span': time_span,
            'time_span_formatted': f"{time_span:.2f}s" if time_span > 0 else "0s",
            'most_active_pid': most_active_pid,
            'dominant_category': dominant_category,
            'pid_count': len(pids),
            'categories': categories
        }
    
    def get_device_status(self):
        """
        Get device connection and mapping status.
        
        Returns:
            dict: Device status information
        """
        try:
            device_status = self.app_mapper_service.get_device_status()
            return {'success': True, 'device_status': device_status}
            
        except Exception as e:
            return self.handle_error(e, "Getting device status")
    
    def refresh_app_mapping(self):
        """
        Refresh app mapping from connected device.
        
        Returns:
            dict: Refresh result
        """
        try:
            result = self.app_mapper_service.refresh_mapping_from_device()
            
            if 'error' in result:
                return {'success': False, 'error': result['error']}
            else:
                return {'success': True, **result}
                
        except Exception as e:
            return self.handle_error(e, "Refreshing app mapping")