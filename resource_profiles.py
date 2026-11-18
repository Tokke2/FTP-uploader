# Copyright (c) 2026 Rickard Längkvist
"""Bounded parallelism, not an OS memory/CPU quota."""
import os
from app_paths import config_dir
from workspace_design import load_state, save_state

PROFILES = {'quiet': (1, 1), 'balanced': (2, 3), 'fast': (8, 8)}


def limits(profile=None):
    if profile is None:
        profile = load_state(config_dir() / 'resources.json').get('profile', 'balanced')
    workers, threads = PROFILES.get(profile, PROFILES['balanced'])
    cpu = max(1, os.cpu_count() or 1)
    return min(cpu, workers), min(cpu, threads)


def save_profile(profile):
    if profile not in PROFILES:
        raise ValueError('Okänd resursprofil')
    save_state(config_dir() / 'resources.json', {'profile': profile})


def ffmpeg_args():
    _, threads = limits()
    return ['-threads', str(threads), '-filter_threads', '1', '-filter_complex_threads', '1']
