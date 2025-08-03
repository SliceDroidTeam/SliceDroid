from collections import defaultdict, Counter

def get_device_identifier(e):
        """Get device identifier - use stdev+inode for regular files, kdev for device nodes"""
        if 'details' not in e:
            return None

        kdev = e['details'].get('k_dev') or e['details'].get('k__dev')

        # For device nodes (kdev != 0), use kdev directly as integer
        if kdev and kdev != 0:
            return kdev

        # For regular files (kdev = 0), use stdev + inode combination
        stdev = e['details'].get('s_dev_inode')
        inode = e['details'].get('inode')

        if stdev and inode:
            # Create compound identifier matching cat2devs.txt format: "stdev - inode"
            return f"{stdev} - {inode}"

        return None

def is_legitimate_sensitive_access(pathname, data_type):
        """
        Validate that the pathname actually represents access to sensitive data
        This helps prevent false positives from regular files on the same device
        """
        if not pathname:
            return False
            
        pathname_lower = pathname.lower()
        
        # Define sensitive patterns for each data type
        sensitive_patterns = {
            'contacts': ['contacts2.db', 'contacts.db', 'people.db', '/contacts/', 'addressbook'],
            'sms': ['mmssms.db', 'sms.db', 'mms.db', '/sms/', '/messages/', 'telephony.db'],
            'calendar': ['calendar.db', 'calendarconfig.db', '/calendar/', 'events.db'],
            'callogger': ['calllog.db', 'calls.db', '/calllog/', 'call_log.db'],
            'call_logs': ['calllog.db', 'calls.db', '/calllog/', 'call_log.db']
        }
        
        # Check if pathname contains sensitive patterns for this data type
        patterns = sensitive_patterns.get(data_type, [])
        for pattern in patterns:
            if pattern in pathname_lower:
                return True
        
        # Additional check for Android provider URIs or database files
        if data_type == 'contacts' and ('com.android.contacts' in pathname_lower or 'contacts' in pathname_lower):
            return True
        elif data_type == 'sms' and ('com.android.providers.telephony' in pathname_lower or 'telephony' in pathname_lower):
            return True
        elif data_type == 'calendar' and ('com.android.providers.calendar' in pathname_lower or 'calendar' in pathname_lower):
            return True
        elif data_type in ['callogger', 'call_logs'] and ('calllog' in pathname_lower or 'calls' in pathname_lower):
            return True
        
        # If pathname is just a device node like '/dev/something', it might not be sensitive data
        if pathname_lower.startswith('/dev/') and data_type not in pathname_lower:
            return False
            
        # Default to false for unrecognized patterns to reduce false positives
        return False

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
