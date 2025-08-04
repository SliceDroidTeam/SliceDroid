"""
Base controller class with common functionality.
"""

class BaseController:
    """Base controller with common methods and error handling."""
    
    def __init__(self, config_class):
        self.config = config_class
    
    def handle_error(self, error, context="Operation"):
        """Standardized error handling."""
        error_msg = f"{context} failed: {str(error)}"
        print(f"[ERROR] {error_msg}")
        return {'error': error_msg}
    
    def validate_pid(self, pid_str):
        """Validate PID parameter."""
        if not pid_str:
            return None
        if not pid_str.isdigit():
            raise ValueError('Invalid PID parameter')
        return int(pid_str)
    
    def validate_parameters(self, **params):
        """Validate common parameters."""
        validated = {}
        
        for param_name, param_value in params.items():
            if param_name == 'pid' and param_value:
                validated['pid'] = self.validate_pid(param_value)
            elif param_name in ['window_size', 'overlap'] and param_value:
                try:
                    validated[param_name] = int(param_value)
                except ValueError:
                    raise ValueError(f'Invalid {param_name} parameter')
            else:
                validated[param_name] = param_value
        
        return validated