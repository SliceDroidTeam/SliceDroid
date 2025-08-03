"""
Advanced Analytics Module
Provides centralized logging configuration for all advanced analytics components
"""

import logging


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a configured logger for the advanced analytics module.
    
    Args:
        name: Logger name (typically the class name)
        
    Returns:
        Configured logger instance
    """
    if name:
        logger_name = f"AdvancedAnalytics.{name}"
    else:
        logger_name = "AdvancedAnalytics"
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Only add handler if it doesn't already exist
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# Module-level logger for general use
logger = get_logger()
