import os
from pathlib import Path

class Config:
    """Configuration class for the web application"""

    # Base directories
    BASE_DIR = Path(__file__).parent.absolute()
    PROJECT_ROOT = BASE_DIR.parent.parent

    # Data paths - can be overridden by environment variables
    DATA_DIR = Path(os.getenv('SLICEDROID_DATA_DIR', PROJECT_ROOT / 'data'))
    EXPORTS_DIR = Path(os.getenv('SLICEDROID_EXPORTS_DIR', PROJECT_ROOT / 'data' / 'Exports'))
    MAPPINGS_DIR = Path(os.getenv('SLICEDROID_MAPPINGS_DIR', DATA_DIR / 'mappings'))
    TRACES_DIR = Path(os.getenv('SLICEDROID_TRACES_DIR', DATA_DIR / 'traces'))

    # File paths
    SLICED_EVENTS_JSON = Path(os.getenv('SLICEDROID_SLICED_EVENTS_FILE', EXPORTS_DIR / 'sliced_events.json'))
    ANALYSIS_JSON = Path(os.getenv('SLICEDROID_ANALYSIS_FILE', EXPORTS_DIR / 'analysis.json'))

    # App configuration
    DEBUG = os.getenv('SLICEDROID_DEBUG', 'False').lower() in ('true', '1', 'yes')
    HOST = os.getenv('SLICEDROID_HOST', '0.0.0.0')
    PORT = int(os.getenv('SLICEDROID_PORT', '5000'))

    @classmethod
    def validate_paths(cls):
        """Validate that required directories exist"""
        errors = []

        for attr_name in ['DATA_DIR', 'EXPORTS_DIR', 'MAPPINGS_DIR', 'TRACES_DIR']:
            path = getattr(cls, attr_name)
            if not Path(path).exists():
                errors.append(f"{attr_name} does not exist: {path}")

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
