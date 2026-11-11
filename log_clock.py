# Copyright (c) 2026 Rickard Längkvist
"""Local full-date timestamps for log records (including legacy callers)."""
from datetime import datetime
import re


def timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def dated(value):
    value = str(value)
    if re.match(r'^\d{4}-\d{2}-\d{2}[ T]', value):
        return value
    return datetime.now().strftime('%Y-%m-%d ') + value
