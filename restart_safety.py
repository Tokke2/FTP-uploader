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
