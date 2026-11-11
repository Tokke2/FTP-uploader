# Copyright (c) 2026 Rickard Längkvist
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from plugins.logo_watermark import validate, apply_logo
from plugins.visitor_tools import TOOLS_HTML, TOOLS_JS
try:
    from PIL import Image
    import resvg_py
    import defusedxml
except ImportError:
    Image = None


@unittest.skipIf(Image is None, 'Pillow required for logo tests')
class WatermarkTests(unittest.TestCase):
    def test_transparent_logo_opacity_position_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'logo.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 40"><rect width="80" height="40" fill="red" fill-opacity="0.5"/></svg>')
            options = validate({'watermark_enabled': True, 'watermark_logo': str(path), 'watermark_opacity': 50})
            with Image.new('RGB', (1000, 800), 'white') as source:
                marked = apply_logo(source, options)
                try:
                    self.assertEqual(marked.size, source.size)
                    self.assertEqual(source.getpixel((950, 750)), (255, 255, 255))
                    self.assertEqual(marked.getpixel((5, 5)), (255, 255, 255))
                    red, green, blue = marked.getpixel((950, 750))
                    self.assertEqual(red, 255)
                    self.assertTrue(185 < green < 200)
                    self.assertEqual(green, blue)
                finally:
                    marked.close()

    def test_disabled_and_validation(self):
        self.assertIsNone(validate({}))
        with Image.new('RGB', (100, 100)) as image:
            self.assertIs(apply_logo(image, None), image)
        with self.assertRaises(ValueError):
            validate({'watermark_enabled': True, 'watermark_logo': '/missing/logo.svg'})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'logo.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><rect width="20" height="20" fill="red"/></svg>')
            for opacity in (0, 101):
                with self.assertRaises(ValueError):
                    validate({'watermark_enabled': True, 'watermark_logo': str(path), 'watermark_opacity': opacity})

    def test_oversize_logo_fits_small_image(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'logo.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2000 1000"><rect width="2000" height="1000" fill="red"/></svg>')
            with Image.new('RGB', (100, 100), 'white') as source:
                marked = apply_logo(source, validate({'watermark_enabled': True, 'watermark_logo': str(path), 'watermark_opacity': 100}))
                try:
                    self.assertEqual(marked.getpixel((80, 90)), (255, 0, 0))
                    self.assertEqual(marked.getpixel((70, 70)), (255, 255, 255))
                finally:
                    marked.close()

    def test_remembered_file_does_not_enable_watermark(self):
        for enabled in (None, False, 'true', 1):
            self.assertIsNone(validate({'watermark_enabled': enabled, 'watermark_logo': '/missing/remembered.svg'}))

    def test_external_resources_scripts_and_entities_are_rejected(self):
        samples = [
            '<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///private.png"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.se/a.svg#logo"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><style>@import "https://example.se/a.css";</style></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(file:///private.png)"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///secret">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>',
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'logo.svg'
            for sample in samples:
                with self.subTest(sample=sample):
                    path.write_text(sample)
                    with self.assertRaises(ValueError):
                        validate({'watermark_enabled': True, 'watermark_logo': str(path)})

    def test_internal_gradient_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'logo.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><defs><linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient></defs><rect width="100" height="50" fill="url(#g)"/></svg>')
            self.assertTrue(validate({'watermark_enabled': True, 'watermark_logo': str(path)})[0].startswith(b'\x89PNG'))


@unittest.skipUnless(shutil.which('node'), 'Node required for web behavior tests')
class VisitorToolsTests(unittest.TestCase):
    def node(self, script):
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_controls_help_focus_typing_and_fullscreen(self):
        script = r'''
const vm=require('vm'), assert=require('assert');
function el(tag='BUTTON') { return {tagName:tag, style:{}, attrs:{}, listeners:{}, children:[],
 classList:{toggle(){}}, setAttribute(k,v){this.attrs[k]=v}, appendChild(c){this.children.push(c)},
 addEventListener(k,fn){(this.listeners[k] ||= []).push(fn)}, focus(){this.focused=true}}; }
const root=el('HTML'), host=el('NAV'), help=el('DIALOG'), close=el(), previous=el();
help.open=false; help.inert=true; help.showModal=function(){this.open=true};help.close=function(){this.open=false};
const ids={'visitor-help':help,'visitor-help-close':close};
const doc={documentElement:root, body:host, hidden:false, activeElement:previous,listeners:{},
 getElementById(id){return ids[id]||null},querySelector(){return host},createElement:el,
 addEventListener(k,fn){(this.listeners[k] ||= []).push(fn)}};
root.requestFullscreen=function(){doc.fullscreenElement=root; return Promise.resolve()};
const ctx={document:doc,window:{alert(){throw Error('unexpected fallback')}}};
vm.runInNewContext(CODE,ctx);
const helpButton=host.children[0], full=host.children[2];
assert.strictEqual(full.hidden,false);
helpButton.listeners.click[0]();assert.strictEqual(help.open,true);assert.strictEqual(help.inert,false);
function key(k,target=el('DIV')) {const e={key:k,target,preventDefault(){this.prevented=true},stopImmediatePropagation(){this.stopped=true}};doc.listeners.keydown[0](e);return e;}
const escape=key('Escape');assert(escape.stopped && escape.prevented);assert(!help.open);assert(previous.focused);
const typed=key('f',el('INPUT'));assert(typed.stopped);assert(!typed.prevented);assert(!doc.fullscreenElement);
const f=key('f');assert(f.prevented && f.stopped);assert.strictEqual(doc.fullscreenElement,root);
key('?');assert(help.open);
'''.replace('CODE', json.dumps(TOOLS_JS))
        self.node(script)

    def test_hidden_tab_does_not_advance_or_override_manual_pause(self):
        from plugins.html_generator_js import SLIDESHOW_JS
        from plugins.html_generator_templates import _MINI_SLIDESHOW_JS
        for source in (SLIDESHOW_JS, _MINI_SLIDESHOW_JS):
            start = source.index('    function tick(ts)')
            end = source.index('    function setPlaying', start)
            function = source[start:end]
            script = r'''
const vm=require('vm'),assert=require('assert');
const ctx={playing:true,document:{hidden:false},total:2,lastTs:0,elapsed:40,speed:100,idx:0,
 progress:{style:{}},window:{requestAnimationFrame(){}},show(){throw Error('unexpected advance')}};
vm.createContext(ctx);vm.runInContext(CODE,ctx);
vm.runInContext('tick(100);tick(116)',ctx);assert.strictEqual(ctx.elapsed,56);
ctx.document.hidden=true;vm.runInContext('tick(132);tick(148)',ctx);assert.strictEqual(ctx.elapsed,56);
ctx.lastTs=0;ctx.document.hidden=false;vm.runInContext('tick(90000)',ctx);assert.strictEqual(ctx.elapsed,56);
ctx.playing=false;vm.runInContext('tick(90016)',ctx);assert.strictEqual(ctx.elapsed,56);
'''.replace('CODE', json.dumps(function))
            self.node(script)
        self.assertIn('visibilitychange', _MINI_SLIDESHOW_JS)
        self.assertIn('visitor-hidden', TOOLS_HTML)
