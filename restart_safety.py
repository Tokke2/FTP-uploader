# Copyright (c) 2026 Rickard Längkvist
"""Explicit unsaved-work checks; an uncertain state blocks automatic restart."""


def unsaved_reasons(app):
    reasons = []
    for name, plugin in getattr(app, 'plugins', {}).items():
        try:
            check = getattr(plugin, 'has_unsaved_changes', None)
            dirty = check() if callable(check) else False
            dirty = dirty or bool(getattr(plugin, 'sort_changed', False))
            dirty = dirty or bool(getattr(plugin, 'image_rotations', {}))
            if dirty:
                reasons.append(str(name))
        except Exception:
            reasons.append(str(name) + ' (kan inte verifiera sparstatus)')

    def inspect(widget):
        for child in widget.winfo_children():
            try:
                check = getattr(child, '_has_unsaved_changes', None)
                if callable(check) and check():
                    reasons.append('osparad redigeringsdialog')
                inspect(child)
            except Exception:
                reasons.append('redigeringsstatus kan inte verifieras')
    try:
        inspect(app)
    except Exception:
        reasons.append('fönsterstatus kan inte verifieras')
    return reasons


def active_job_reasons(app):
    """Use actual job flags/processes, not words in permanent service-thread names."""
    import threading
    reasons = []
    if getattr(app, '_pipeline_busy', 0):
        reasons.append('pipeline körs')
    for name, plugin in getattr(app, 'plugins', {}).items():
        flags = [getattr(plugin, attr, False) for attr in
                 ('is_generating', 'is_processing', 'is_uploading', 'processing')]
        if any(isinstance(value, (bool, int)) and value for value in flags):
            reasons.append(str(name) + ' arbetar')
        process = getattr(plugin, 'current_process', None)
        if process is not None:
            try:
                if process.poll() is None:
                    reasons.append(str(name) + ' kör extern process')
            except (OSError, AttributeError):
                reasons.append(str(name) + ' processstatus kan inte verifieras')
    known_names = {'PipelineThread', 'GenerateThread', 'MediaProcessingThread'}
    for thread in threading.enumerate():
        if thread is threading.main_thread() or not thread.is_alive():
            continue
        if (thread.name in known_names
                or thread.name.endswith('(_process_all_worker)')
                or thread.name.endswith('(_generate_thread)')):
            reasons.append(thread.name)
    return list(dict.fromkeys(reasons))
