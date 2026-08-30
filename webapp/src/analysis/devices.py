"""
Device identification, categorization and sensitive-data detection.

Device identifiers follow the cat2devs.txt convention: a non-zero k_dev is
used directly (device nodes), otherwise the compound "s_dev_inode - inode"
string identifies regular files.  Sensitive access detection combines the
device-id match with pathname validation to avoid false positives from
unrelated files on the same device.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

from .slicer import is_filtered

logger = logging.getLogger(__name__)

Event = dict[str, Any]

PROBE_EVENTS = ('read_probe', 'write_probe', 'ioctl_probe')

#: Sensitive data categories tracked by SliceDroid
SENSITIVE_CATEGORIES = ('contacts', 'sms', 'calendar', 'call_logs')

#: Pathname patterns that legitimize a sensitive-device match
_SENSITIVE_PATTERNS = {
    'contacts': ['contacts2.db', 'contacts.db', 'people.db', '/contacts/', 'addressbook'],
    'sms': ['mmssms.db', 'sms.db', 'mms.db', '/sms/', '/messages/', 'telephony.db'],
    'calendar': ['calendar.db', 'calendarconfig.db', '/calendar/', 'events.db'],
    'call_logs': ['calllog.db', 'calls.db', '/calllog/', 'call_log.db'],
}


def get_device_identifier(event: Event) -> Optional[Union[int, str]]:
    """
    Get the device identifier of a probe event.

    Uses k_dev directly for device nodes (k_dev != 0) and the compound
    "s_dev_inode - inode" string for regular files, matching the
    cat2devs.txt mapping format.
    """
    details = event.get('details')
    if not details:
        return None

    kdev = details.get('k_dev')
    if kdev:
        return kdev

    stdev = details.get('s_dev_inode')
    inode = details.get('inode')
    if stdev and inode:
        return f"{stdev} - {inode}"

    return None


def load_category_map(path: Union[str, Path]) -> dict[str, list[str]]:
    """
    Load a cat2devs mapping file (JSON: {category: [device ids]}) and
    normalize all device ids to strings.
    """
    with open(path, 'r') as f:
        raw = json.load(f)
    return {category: [str(dev) for dev in devs] for category, devs in raw.items()}


def invert_category_map(cat2devs: dict[str, list[str]]) -> dict[str, str]:
    """Invert {category: [devices]} into {device: category} with string keys."""
    dev2cat: dict[str, str] = {}
    for category, devs in cat2devs.items():
        for dev in devs:
            dev2cat[str(dev)] = category
    return dev2cat


def is_legitimate_sensitive_access(pathname: str, data_type: str) -> bool:
    """
    Validate that a pathname actually represents access to sensitive data.
    This prevents false positives from regular files on the same device.
    """
    if not pathname:
        return False

    pathname_lower = pathname.lower()

    for pattern in _SENSITIVE_PATTERNS.get(data_type, []):
        if pattern in pathname_lower:
            return True

    # Additional check for Android provider URIs or database files
    if data_type == 'contacts' and ('com.android.contacts' in pathname_lower or 'contacts' in pathname_lower):
        return True
    if data_type == 'sms' and ('com.android.providers.telephony' in pathname_lower or 'telephony' in pathname_lower):
        return True
    if data_type == 'calendar' and ('com.android.providers.calendar' in pathname_lower or 'calendar' in pathname_lower):
        return True
    if data_type == 'call_logs' and ('calllog' in pathname_lower or 'calls' in pathname_lower):
        return True

    # Default to false for unrecognized patterns to reduce false positives
    return False


def sensitive_category(event: Event, cat2devs: dict[str, list[str]]) -> Optional[str]:
    """
    Return the sensitive category ('contacts', 'sms', 'calendar',
    'call_logs') accessed by a probe event, or None.

    An event matches when its device identifier appears in the category's
    device list AND its pathname passes sensitive-access validation.
    """
    if event.get('event') not in PROBE_EVENTS:
        return None

    device_id = get_device_identifier(event)
    if device_id is None:
        return None
    device_id_str = str(device_id)

    pathname = event.get('details', {}).get('pathname', '')
    for category in SENSITIVE_CATEGORIES:
        devices = cat2devs.get(category)
        if devices and device_id_str in devices:
            if is_legitimate_sensitive_access(pathname, category):
                return category

    return None


def detect_sensitive_events(events: list[Event], cat2devs: dict[str, list[str]]) -> dict[str, list[Event]]:
    """Group events by the sensitive category they access."""
    detected: dict[str, list[Event]] = {category: [] for category in SENSITIVE_CATEGORIES}
    for event in events:
        category = sensitive_category(event, cat2devs)
        if category:
            detected[category].append(event)
    return detected


def build_device_summary(events: list[Event], cat2devs: dict[str, list[str]]) -> dict[str, Any]:
    """
    Build the ``devices`` section of the analysis JSON contract from the
    sliced events: per-device pathnames and access counts, category counts,
    and per-category sensitive access reports.
    """
    dev2cat = invert_category_map(cat2devs)

    dev2pathnames: dict[str, list[str]] = {}
    device_counts: dict[str, int] = {}
    categories: dict[str, int] = {}

    for e in events:
        if is_filtered(e):
            continue
        device_id = get_device_identifier(e)
        if device_id is None:
            continue
        device_key = str(device_id)
        pathname = e['details'].get('pathname', 'unknown')

        device_counts[device_key] = device_counts.get(device_key, 0) + 1
        pathnames = dev2pathnames.setdefault(device_key, [])
        if pathname not in pathnames:
            pathnames.append(pathname)

        category = dev2cat.get(device_key)
        if category:
            categories[category] = categories.get(category, 0) + 1

    sensitive_events = detect_sensitive_events(events, cat2devs)
    sensitive: dict[str, Any] = {}
    for category in SENSITIVE_CATEGORIES:
        cat_events = sensitive_events[category]
        devices = []
        pathnames = []
        for e in cat_events:
            device_key = str(get_device_identifier(e))
            if device_key not in devices:
                devices.append(device_key)
            pathname = e['details'].get('pathname', 'unknown')
            if pathname not in pathnames:
                pathnames.append(pathname)
        sensitive[category] = {
            'detected': bool(cat_events),
            'event_count': len(cat_events),
            'devices': devices,
            'pathnames': pathnames,
        }

    return {
        'dev2pathnames': dev2pathnames,
        'device_counts': device_counts,
        'categories': categories,
        'sensitive': sensitive,
    }
