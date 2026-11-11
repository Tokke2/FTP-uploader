# Copyright (c) 2026 Rickard Längkvist
"""Persistent local-calendar scheduling: Monday 08:00, not startup intervals."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import time


def next_monday(now=None):
    now = datetime.now() if now is None else now
    target = (now - timedelta(days=now.weekday())).replace(hour=8, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=7)
    return target.timestamp()


class WeeklySchedule:
    def __init__(self, path):
        self.path = Path(path)
        try:
            self.tasks = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(self.tasks, dict):
                self.tasks = {}
        except (OSError, ValueError):
            self.tasks = {}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.tasks, indent=2), encoding='utf-8')
        temporary.replace(self.path)

    def due(self, task, now=None):
        now = time.time() if now is None else now
        target = self.tasks.get(task)
        if not isinstance(target, (int, float)):
            # First use schedules a future Monday; never run just because of startup.
            self.tasks[task] = next_monday(datetime.fromtimestamp(now))
            self.save()
            return False
        return now >= target

    def complete(self, task, now=None):
        now = time.time() if now is None else now
        self.tasks[task] = next_monday(datetime.fromtimestamp(now))
        self.save()
