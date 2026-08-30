"""
Canonical ftrace log parser.

Parses ftrace `trace_pipe` / trace file output produced with the record-tgid
option, i.e. lines of the form:

    process-tid (tgid) [cpu] flags timestamp: event: details

Detail key/value pairs are decoded (hex and decimal integers converted to
``int``, quoted strings unquoted).  The kprobe argument ``k__dev`` is
normalized to ``k_dev`` here, exactly once, so no downstream code ever has
to check both spellings.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Regular expression to match ftrace event log lines with TGID inside parentheses
TRACE_PATTERN = re.compile(
    r'\s*(?P<process>((\S|\s)+|\<\.\.\.\>))-(?P<tid>\d+)\s+\(\s*(?P<tgid>(\d+|-------))\)\s+'
    r'\[(?P<cpu>\d+)\]\s+(?P<flags>[\S]+)\s+(?P<timestamp>\d+\.\d+):\s+(?P<event>\S+):\s+(?P<details>.*)'
)

# Regular expression to match key-value pairs inside the 'details' section
DETAIL_PATTERN = re.compile(r'(\S+)=(".*?"|\S+)')

# Lines longer than this are considered corrupt and skipped
MAX_LINE_LENGTH = 1000


def calculate_major_minor(dev_t: int) -> tuple[int, int]:
    """Split a kernel dev_t value into its (major, minor) components."""
    major = (dev_t >> 20) & 0xFFF
    minor = dev_t & 0xFFFFF
    return major, minor


def _parse_details(details: str) -> dict[str, Any]:
    """Parse the details section of a trace line into typed key/value pairs."""
    parsed_details: dict[str, Any] = {}
    for detail_match in DETAIL_PATTERN.finditer(details):
        key, value = detail_match.groups()
        if value.startswith("0x"):  # Handle hexadecimal values
            parsed_details[key] = int(value, 16)
        else:
            try:
                parsed_details[key] = int(value)
            except ValueError:
                parsed_details[key] = value.strip('"')

    # Normalize the kprobe argument name once, at the source.
    # Downstream code only ever sees 'k_dev'.
    if 'k__dev' in parsed_details:
        parsed_details['k_dev'] = parsed_details.pop('k__dev')

    return parsed_details


def parse_ftrace_log(file_path: str | Path) -> list[dict[str, Any]]:
    """
    Parse an ftrace log file into a list of event dictionaries.

    Each event has the keys: process, tid, tgid, cpu, flags, timestamp,
    event, details.  ``details`` is a dict of typed key/value pairs with
    ``k__dev`` normalized to ``k_dev``.
    """
    parsed_events: list[dict[str, Any]] = []

    with open(file_path, 'r') as f:
        for line in f:
            if len(line) > MAX_LINE_LENGTH:
                continue
            match = TRACE_PATTERN.match(line)
            if not match:
                logger.debug("Skipping unparseable trace line: %s", line.rstrip())
                continue

            process = match.group('process')
            tid = int(match.group('tid'))
            try:
                tgid = int(match.group('tgid'))
            except ValueError:
                tgid = -1  # When tgid is not known by the system use -1

            parsed_events.append({
                "process": process,
                "tid": tid,
                "tgid": tgid,
                "cpu": int(match.group('cpu')),
                "flags": match.group('flags'),
                "timestamp": float(match.group('timestamp')),
                "event": match.group('event'),
                "details": _parse_details(match.group('details')),
            })

    logger.info("Parsed %d events from %s", len(parsed_events), file_path)
    return parsed_events


# Lightweight prefix scanner: only the "process-tid (tgid)" columns, no details.
_PREFIX_PATTERN = re.compile(
    r'\s*(?P<process>((\S|\s)+|\<\.\.\.\>))-(?P<tid>\d+)\s+\(\s*(?P<tgid>(\d+|-------))\)\s+\['
)


def scan_processes(file_path: str | Path) -> list[dict[str, Any]]:
    """
    Cheaply enumerate the processes present in a trace, grouped by tgid.

    Reads only the line prefix (never the details), so it is much faster than a
    full parse — enough to populate a target picker before analysis. Returns a
    list of ``{"tgid": int, "name": str, "events": int}`` sorted by event count
    descending. ``name`` is the thread-group leader's comm (the line where
    tid == tgid) when seen, else the most frequent comm for that tgid.
    """
    counts: dict[int, int] = {}
    leader: dict[int, str] = {}
    name_votes: dict[int, dict[str, int]] = {}

    with open(file_path, 'r') as f:
        for line in f:
            if len(line) > MAX_LINE_LENGTH:
                continue
            match = _PREFIX_PATTERN.match(line)
            if not match:
                continue
            try:
                tgid = int(match.group('tgid'))
            except ValueError:
                continue  # unknown tgid ('-------') — not a selectable target
            tid = int(match.group('tid'))
            process = match.group('process').strip()

            counts[tgid] = counts.get(tgid, 0) + 1
            votes = name_votes.setdefault(tgid, {})
            votes[process] = votes.get(process, 0) + 1
            if tid == tgid:
                leader[tgid] = process

    processes = []
    for tgid, n in counts.items():
        name = leader.get(tgid)
        if name is None:
            name = max(name_votes[tgid].items(), key=lambda kv: kv[1])[0]
        processes.append({"tgid": tgid, "name": name, "events": n})

    processes.sort(key=lambda p: p["events"], reverse=True)
    return processes
