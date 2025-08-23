import os
from pathlib import Path

class Config:
    """Configuration class for the web application"""
    
    # Base directories
    BASE_DIR = Path(__file__).parent.absolute()
    PROJECT_ROOT = BASE_DIR.parent.parent
    
    # Data paths - can be overridden by environment variables
    DATA_DIR = Path(os.getenv('SYSDROID_DATA_DIR', PROJECT_ROOT / 'data'))
    EXPORTS_DIR = Path(os.getenv('SYSDROID_EXPORTS_DIR', PROJECT_ROOT / 'data' / 'Exports'))
    MAPPINGS_DIR = Path(os.getenv('SYSDROID_MAPPINGS_DIR', DATA_DIR / 'mappings'))
    TRACES_DIR = Path(os.getenv('SYSDROID_TRACES_DIR', DATA_DIR / 'traces'))
    
    # File paths
    PROCESSED_EVENTS_JSON = Path(os.getenv('SYSDROID_EVENTS_FILE', EXPORTS_DIR / 'processed_events.json'))
    SLICED_EVENTS_JSON = Path(os.getenv('SYSDROID_SLICED_EVENTS_FILE', EXPORTS_DIR / 'sliced_events.json'))
    
    # App configuration
    DEBUG = os.getenv('SYSDROID_DEBUG', 'False').lower() in ('true', '1', 'yes')
    HOST = os.getenv('SYSDROID_HOST', '0.0.0.0')
    PORT = int(os.getenv('SYSDROID_PORT', '5000'))
    
    # Chart configuration
    CHART_TOP_N_DEVICES = int(os.getenv('SYSDROID_TOP_DEVICES', '10'))
    CHART_TOP_N_EVENTS = int(os.getenv('SYSDROID_TOP_EVENTS', '10'))
    
    # Timeline configuration
    TIMELINE_MAX_EVENTS = int(os.getenv('SYSDROID_MAX_TIMELINE_EVENTS', '1000'))
    TIMELINE_DEFAULT_ZOOM = float(os.getenv('SYSDROID_DEFAULT_ZOOM', '1.0'))
    
    # Event categories and their colors
    EVENT_CATEGORIES = {
        'read': '#28a745',
        'write': '#007bff', 
        'ioctl': '#6f42c1',
        'binder': '#fd7e14',
        'network': '#17a2b8',
        'other': '#6c757d'
    }
    
    # Event type mappings to categories
    EVENT_TYPE_MAPPINGS = {
        'read': ['read', 'pread', 'readv', 'preadv'],
        'write': ['write', 'pwrite', 'writev', 'pwritev'],
        'ioctl': ['ioctl'],
        'binder': ['binder'],
        'network': ['unix', 'sock', 'inet', 'tcp', 'udp', 'inet_sock_set_state']
    }
    
    @classmethod
    def get_event_category(cls, event_type):
        """Determine event category based on event type"""
        if not event_type:
            return 'other'
            
        event_type_lower = event_type.lower()
        
        for category, keywords in cls.EVENT_TYPE_MAPPINGS.items():
            if any(keyword in event_type_lower for keyword in keywords):
                return category
                
        return 'other'
    
    @classmethod
    def validate_paths(cls):
        """Validate that required directories exist"""
        errors = []
        
        # Check if data directories exist
        for attr_name in ['DATA_DIR', 'EXPORTS_DIR', 'MAPPINGS_DIR', 'TRACES_DIR']:
            path = getattr(cls, attr_name)
            if not Path(path).exists():
                errors.append(f"{attr_name} does not exist: {path}")
        
        # Check if events file exists
        if not Path(cls.PROCESSED_EVENTS_JSON).exists():
            errors.append(f"Events file does not exist: {cls.PROCESSED_EVENTS_JSON}")
            
        return errors

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}