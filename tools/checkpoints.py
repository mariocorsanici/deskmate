"""Shared timestamp and Markdown Checkpoint parsing for publication and reads."""
from __future__ import annotations

import datetime as dt
import re


def instant(value, *, require_zone=False, native=False):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO timestamp')
    try:
        stamp = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if require_zone and stamp.tzinfo is None:
            raise ValueError('Timestamp must include a timezone')
        if native and stamp.tzinfo is None:
            # Both native adapters interpret naive runtime times as UTC.
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
        return stamp.astimezone(dt.timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise ValueError('Timestamp must be a representable ISO timestamp with the required timezone') from None


def checkpoint_boundary(text, *, session_id=None):
    status = re.search(r'^## Status\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not status:
        return None
    line = re.search(r'^Checkpoint(?:[ \t][^\r\n]*)?\r?$', status[1], re.M)
    if not line:
        return None
    match = re.match(r'^Checkpoint ([^,\r\n]+), session `([^`]+)`', line[0])
    if not match:
        raise ValueError('Checkpoint must contain an ISO timestamp followed by session `<id>`')
    if session_id is not None and match[2] != session_id:
        return None
    try:
        stamp = instant(match[1])
    except ValueError:
        raise ValueError('Checkpoint timestamp must be ISO 8601, for example 2026-11-11T14:09:00Z') from None
    minute = bool(re.fullmatch(r'\d{4}-\d\d-\d\d[ T]\d\d:\d\d', match[1]))
    return {'timestamp': stamp.isoformat(), 'source': 'project-card',
            'precision': 'minute' if minute else 'second'}
