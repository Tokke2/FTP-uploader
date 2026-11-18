from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backup_storage import backup_root,new_backup,config_backup


class BackupStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app=Path(self.temp.name)/'app'
        self.app.mkdir()
        self.mock=patch('backup_storage.app_dir',return_value=self.app)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def test_categories_and_config_backups_stay_in_app(self):
        for category in ('releases','galleries','editor','config'):
            self.assertTrue(new_backup(category,'../../name').is_relative_to(self.app/'backups'))
        outside=Path(self.temp.name)/'user-config/settings.json'
        self.assertTrue(config_backup(outside).is_relative_to(self.app/'backups/config'))
        self.assertNotEqual(config_backup(outside),config_backup(self.app/'settings.json'))
        self.assertFalse(outside.parent.exists())

    def test_external_backup_symlink_is_rejected(self):
        external=Path(self.temp.name)/'outside';external.mkdir()
        (self.app/'backups').symlink_to(external,target_is_directory=True)
        with self.assertRaises(ValueError): backup_root()
        self.assertEqual(list(external.iterdir()),[])

    def test_external_category_symlink_is_rejected(self):
        root=backup_root()
        external=Path(self.temp.name)/'outside';external.mkdir()
        (root/'releases').symlink_to(external,target_is_directory=True)
        with self.assertRaises(ValueError): new_backup('releases','test')

    def test_gallery_backup_never_goes_beside_external_export(self):
        from export_transaction import ExportTransaction
        destination=Path(self.temp.name)/'another-disk/gallery'
        destination.mkdir(parents=True)
        (destination/'index.html').write_text('old')
        tx=ExportTransaction(destination)
        (tx.stage/'index.html').write_text('new')
        tx.publish({'_gallery_generated':True})
        self.assertTrue(tx.backup.is_relative_to(self.app/'backups/galleries'))
        self.assertEqual((tx.backup/'index.html').read_text(),'old')
        self.assertEqual([p.name for p in destination.parent.iterdir()],['gallery'])

    def test_health_rollback_rejects_legacy_external_backup(self):
        import json
        from release_health import rollback
        external=Path(self.temp.name)/'app.release-backup-old';external.mkdir()
        (self.app/'.release-rollback.json').write_text(json.dumps({'commit':'a'*40,'backup':str(external),'changed':[]}))
        with self.assertRaises(ValueError): rollback(self.app,'a'*40)

    def test_export_cannot_include_backup_root(self):
        from export_transaction import ExportTransaction
        with self.assertRaises(ValueError): ExportTransaction(self.app)
