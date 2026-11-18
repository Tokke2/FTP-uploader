# Copyright (c) 2026 Rickard Längkvist
"""Sibling staging with rollback; keep the previous gallery as a backup."""
from pathlib import Path
import shutil
import tempfile


class ExportTransaction:
    def __init__(self, destination):
        self.destination = Path(destination).resolve()
        from backup_storage import backup_root
        root = backup_root()
        if root.is_relative_to(self.destination):
            raise ValueError('Exportmappen får inte innehålla appens backupmapp.')
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self.stage = Path(tempfile.mkdtemp(prefix='.' + self.destination.name + '-export-', dir=self.destination.parent))
        self.backup = None
        self.committed = False
        try:
            if self.destination.exists():
                shutil.copytree(self.destination, self.stage, dirs_exist_ok=True)
        except BaseException:
            self.abort()
            raise

    def publish(self, context):
        if context.get('_processing_image_failures'):
            raise RuntimeError('Bildbearbetningen misslyckades; tidigare galleri behålls.')
        if not context.get('_gallery_generated') or not (self.stage / 'index.html').is_file():
            raise RuntimeError('Ingen verifierad galleri-export att publicera.')
        check = context.get('cancel_check')
        if callable(check) and check():
            raise RuntimeError('Exporten avbröts före publicering.')
        from plugins.gallery_checks import check_links
        if not check_links(self.stage)['ok']:
            raise ValueError('Exporten har trasiga länkar; tidigare galleri behålls.')
        if self.destination.exists():
            from backup_storage import new_backup, move_directory_to_backup
            self.backup = new_backup('galleries',self.destination.name)
            move_directory_to_backup(self.destination,self.backup)
        try:
            self.stage.rename(self.destination)
        except BaseException:
            if self.backup is not None:
                from backup_storage import restore_directory
                restore_directory(self.backup,self.destination)
            raise
        self.committed = True
        self.relocate(context, self.stage, self.destination)

    @classmethod
    def relocate(cls, value, old, new):
        if isinstance(value, dict):
            for key, item in list(value.items()):
                value[key] = cls.relocate(item, old, new)
        elif isinstance(value, list):
            value[:] = [cls.relocate(item, old, new) for item in value]
        elif isinstance(value, (str, Path)):
            try:
                relative = Path(value).relative_to(old)
                return new / relative if isinstance(value, Path) else str(new / relative)
            except (ValueError, OSError):
                pass
        return value

    def abort(self):
        if not self.committed and self.stage.exists():
            shutil.rmtree(self.stage)
