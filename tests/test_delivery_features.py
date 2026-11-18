import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from delivery_options import validate
from gallery_delivery import localized_pages, quality_markup
from resource_profiles import limits


class DeliveryTests(unittest.TestCase):
    def test_bounded_options_and_language_codes(self):
        self.assertEqual(validate({})['qualities'], [])
        with self.assertRaises(ValueError): validate({'languages': {'../bad': {}}})
        with self.assertRaises(ValueError): validate({'qualities': [2160]})
        self.assertEqual(validate({'languages': {'ar': {'dir':'rtl'}}})['languages']['ar']['dir'],'rtl')

    def test_locales_preserve_scripts_escape_text_translate_attributes(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('index','slideshow'):
                (Path(folder)/(name+'.html')).write_text('<!doctype html><html lang="sv"><body><h1>A &amp; B</h1><button aria-label="Stäng">Stäng</button><a href="index.html">Hem</a><script>const text="Stäng";</script></body></html>')
            languages = validate({'languages': {'en': {'title':'A < B','labels': {'Stäng':'Close'}},'ar':{'dir':'rtl','title':'عنوان'}}})['languages']
            localized_pages(folder,languages,'A & B','')
            text=(Path(folder)/'index.en.html').read_text()
            self.assertIn('A &lt; B',text)
            self.assertIn('aria-label="Close"',text)
            self.assertIn('const text="Stäng"',text)
            self.assertIn('href="index.en.html"',text)
            self.assertIn('dir="rtl"',(Path(folder)/'index.ar.html').read_text())
            self.assertIn('href="index.html">Svenska',text)

    def test_resource_caps_respect_cpu_count(self):
        with patch('os.cpu_count',return_value=4):
            self.assertEqual(limits('quiet'),(1,1))
            self.assertEqual(limits('balanced'),(2,3))
            self.assertEqual(limits('fast'),(4,4))

    def test_quality_markup_has_controls_and_safe_sources(self):
        text = quality_markup([{'name':'<clip>','relative_path':'video/1.mp4','qualities':{'720p':'video/1.720p.mp4'}}])
        self.assertIn('720p',text)
        self.assertIn('&lt;clip&gt;',text)
        self.assertIn('loadedmetadata',text)

    def test_panorama_export_selects_only_two_to_one_images(self):
        try: from PIL import Image
        except ImportError: self.skipTest('Pillow required')
        from panorama_viewer import export_panoramas
        with tempfile.TemporaryDirectory() as folder:
            entries=[]
            for name,size in [('sphere.jpg',(200,100)),('photo.jpg',(120,100))]:
                path=Path(folder)/name
                with Image.new('RGB',size,'blue') as image: image.save(path)
                entries.append({'full_dst':str(path),'title':name})
            markup=export_panoramas(entries,folder)
            self.assertIn('panorama.html',markup)
            text=(Path(folder)/'panorama.html').read_text()
            self.assertIn('sphere.jpg',text)
            self.assertNotIn('photo.jpg',text)
            self.assertIn("getContext('webgl')",text)

    def test_startup_ack_requires_expected_commit_and_nonce(self):
        from release_health import acknowledge
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            (base/'.release-state.json').write_text(json.dumps({'commit':'a'*40}))
            env={'FTP_UPDATE_HEALTH_FILE':str(base/'ack.json'),'FTP_UPDATE_HEALTH_NONCE':'token','FTP_UPDATE_HEALTH_COMMIT':'a'*40}
            with patch.dict(os.environ,env): acknowledge(base)
            self.assertEqual(json.loads((base/'ack.json').read_text()),{'nonce':'token','commit':'a'*40})
            env['FTP_UPDATE_HEALTH_COMMIT']='b'*40
            with patch.dict(os.environ,env), self.assertRaises(RuntimeError): acknowledge(base)

    def test_rollback_restores_managed_files_not_exports(self):
        from release_health import write_receipt,rollback
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)/'app';base.mkdir()
            backup=Path(folder)/'app.release-backup-test';backup.mkdir()
            (backup/'main.pyw').write_text('old')
            (base/'main.pyw').write_text('new')
            (base/'new_module.py').write_text('new')
            (base/'gallery.html').write_text('user gallery')
            write_receipt(base,backup,[(Path('main.pyw'),True),(Path('new_module.py'),False)],'a'*40)
            rollback(base,'a'*40)
            self.assertEqual((base/'main.pyw').read_text(),'old')
            self.assertFalse((base/'new_module.py').exists())
            self.assertEqual((base/'gallery.html').read_text(),'user gallery')

    def test_unsigned_is_not_marked_verified(self):
        from release_signatures import verify_archive
        with tempfile.TemporaryDirectory() as folder,patch('release_signatures.config_dir',return_value=Path(folder)):
            self.assertEqual(verify_archive('unused',('v1.0.0','a'*40),Mock()),'unsigned')

    def test_signed_archive_verifies_and_rejects_tampering(self):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
        except ImportError: self.skipTest('cryptography required')
        import base64,hashlib
        from release_signatures import verify_archive
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            archive=path/'release.zip';archive.write_bytes(b'archive bytes')
            key=Ed25519PrivateKey.generate()
            public=base64.b64encode(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
            (path/'release-trust.json').write_text(json.dumps({'public_key':public}))
            manifest=json.dumps({'tag':'v1.0.0','commit':'a'*40,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}).encode()
            signature=base64.b64encode(key.sign(manifest))
            fetch=lambda url: signature if url.endswith('.sig') else manifest
            with patch('release_signatures.config_dir',return_value=path):
                self.assertEqual(verify_archive(archive,('v1.0.0','a'*40),fetch),'ed25519-verified')
                archive.write_bytes(b'changed bytes')
                with self.assertRaises(ValueError): verify_archive(archive,('v1.0.0','a'*40),fetch)
                with self.assertRaises(Exception): verify_archive(archive,('v1.0.0','a'*40),lambda url: b'bad')

    def test_health_acknowledgement_accepts_only_live_child(self):
        from release_health import launch_checked
        with tempfile.TemporaryDirectory() as folder:
            child=Mock();child.poll.return_value=None
            def spawn(command,env):
                Path(env['FTP_UPDATE_HEALTH_FILE']).write_text(json.dumps({'nonce':env['FTP_UPDATE_HEALTH_NONCE'],'commit':env['FTP_UPDATE_HEALTH_COMMIT']}))
                return child
            with patch('release_health.rollback') as rollback:
                self.assertTrue(launch_checked(folder,'a'*40,spawn,'python',timeout=1))
                rollback.assert_not_called()
                child.terminate.assert_not_called()

    def test_failed_health_restores_before_relaunch(self):
        from release_health import launch_checked
        order=[]
        child=Mock();child.poll.return_value=1
        def spawn(command,env):
            order.append('spawn')
            return child
        with tempfile.TemporaryDirectory() as folder,patch('release_health.rollback',side_effect=lambda *args:order.append('rollback')):
            self.assertFalse(launch_checked(folder,'a'*40,spawn,'python',timeout=0))
            self.assertEqual(order,['spawn','rollback','spawn'])

    def test_real_delivery_export_includes_locales_panorama_and_video_choices(self):
        try: from PIL import Image
        except ImportError: self.skipTest('Pillow required')
        from media_support import bundled_ffmpeg
        import subprocess
        ffmpeg=bundled_ffmpeg()
        if not ffmpeg: self.skipTest('FFmpeg required')
        from test_web_image_assets import generator_class
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.mkdir()
            with Image.new('RGB',(200,100),'blue') as image: image.save(source/'panorama.jpg')
            subprocess.run([ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-f','lavfi','-i','color=red:s=64x48:d=0.3',
                            '-c:v','libx264','-pix_fmt','yuv420p','-y',str(source/'clip.mp4')],check=True,capture_output=True,timeout=15)
            output=Path(folder)/'gallery'
            generator=generator_class()()
            generator._get_output_format=lambda context:'standard'
            context={'gallery':{'images_path':str(source),'output_path':str(output),'title':'Mitt galleri',
                               'delivery':{'languages':{'en':{'title':'My gallery'},'ar':{'dir':'rtl','title':'معرض'}},
                                           'panorama_auto':True,'qualities':[480]}},'_defer_learning':True}
            result=generator.execute(context)
            self.assertTrue(result['link_report']['ok'])
            for name in ('index.en.html','index.ar.html','slideshow.en.html','panorama.html','video/video1.480p.mp4'):
                self.assertTrue((output/name).is_file(),name)
            self.assertIn('My gallery',(output/'index.en.html').read_text())
            self.assertIn('dir="rtl"',(output/'index.ar.html').read_text())
            self.assertIn('Videospelare med kvalitetsval',(output/'index.html').read_text())
            from ffmpeg_progress import duration_from_ffmpeg
            self.assertGreater(duration_from_ffmpeg(ffmpeg,output/'video/video1.480p.mp4'),0)
            metadata=subprocess.run([ffmpeg,'-hide_banner','-i',str(output/'video/video1.480p.mp4')],capture_output=True,text=True,timeout=10)
            self.assertIn('64x48',metadata.stderr)
