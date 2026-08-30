from collections import defaultdict, Counter

def make_json_serializable(obj):
        """Convert sets and other non-serializable objects to JSON-serializable format"""
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, (dict, defaultdict, Counter)):
            # Convert ALL keys to strings to prevent mixed int/str key errors during JSON serialization
            return {str(key): make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [ make_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Handle objects with attributes
            return make_json_serializable(obj.__dict__)
        else:
            return obj
