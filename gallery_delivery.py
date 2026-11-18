# Copyright (c) 2026 Rickard Längkvist
"""Static, shared-media language pages and explicit MP4 quality choices."""
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re


BUILTIN = {
'en': dict(zip(('Galleri','Bildspel','Filtrera bilder','Filtrera bilder…','Rensa filter','Radjämnt','Tema','Densitet','Standard','Bildgalleri','Ingen bild matchar filtret.','Stang','Stäng','Foregaende','Nasta','Helskarm','Helskärm (F)','Tangentbordshjälp (?)','Videor','bilder','Videospelare med kvalitetsval'),
               ('Gallery','Slideshow','Filter images','Filter images…','Clear filter','Justified','Theme','Density','Standard','Image gallery','No image matches the filter.','Close','Close','Previous','Next','Fullscreen','Fullscreen (F)','Keyboard help (?)','Videos','images','Video quality player'))),
'de': {'Galleri':'Galerie','Bildspel':'Diashow','Filtrera bilder':'Bilder filtern','Filtrera bilder…':'Bilder filtern…','Rensa filter':'Filter löschen','Stäng':'Schließen','Stang':'Schließen','Videor':'Videos','bilder':'Bilder'},
'ar': {'Galleri':'المعرض','Bildspel':'عرض الشرائح','Filtrera bilder':'تصفية الصور','Filtrera bilder…':'تصفية الصور…','Rensa filter':'مسح التصفية','Stäng':'إغلاق','Stang':'إغلاق','Videor':'مقاطع الفيديو','bilder':'صور'}
}


def runtime_translation(labels):
    return '<script>(function(){const labels='+script_json(labels)+r""";const last=new WeakMap();
function translated(s){let t=s.trim();if(Object.prototype.hasOwnProperty.call(labels,t))return s.replace(t,labels[t]);let m=t.match(/^(\d+) bilder$/);if(m&&labels.bilder)return m[1]+' '+labels.bilder;for(let word of ['Galleri','Videor'])if(labels[word]&&t.endsWith(' '+word))return s.slice(0,s.lastIndexOf(word))+labels[word];return s;}
function visit(node){if(node.nodeType===3){if(last.get(node)===node.nodeValue)return;if(node.parentElement&&node.parentElement.closest('script,style,textarea'))return;let t=translated(node.nodeValue);if(t!==node.nodeValue)node.nodeValue=t;last.set(node,node.nodeValue);}else if(node.nodeType===1){if(node.matches('script,style,textarea'))return;for(let a of ['title','aria-label','placeholder','alt'])if(node.hasAttribute(a)){let old=node.getAttribute(a),next=translated(old);if(old!==next)node.setAttribute(a,next);}Array.from(node.childNodes).forEach(visit);}}
visit(document.body);new MutationObserver(ms=>{for(let m of ms){if(m.type==='childList')m.addedNodes.forEach(visit);else visit(m.target);}}).observe(document.body,{childList:true,subtree:true,characterData:true});})();</script>"""


def script_json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


class Translate(HTMLParser):
    def __init__(self, labels):
        super().__init__(convert_charrefs=True)
        self.labels, self.parts, self.raw = labels, [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.raw += 1
        if tag in ('script', 'style'):
            self.parts.append(self.get_starttag_text())
        else:
            translated = []
            for key,value in attrs:
                if key in ('aria-label','title','placeholder','alt','content') and value in self.labels:
                    value = self.labels[value]
                translated.append(key if value is None else '%s="%s"' % (key,html.escape(value,quote=True)))
            self.parts.append('<'+tag+(' '+' '.join(translated) if translated else '')+'>')

    def handle_endtag(self, tag):
        self.parts.append('</%s>' % tag)
        if tag in ('script', 'style'):
            self.raw = max(0, self.raw-1)

    def handle_data(self, data):
        stripped = data.strip()
        if self.raw:
            self.parts.append(data)
        else:
            self.parts.append(html.escape(data.replace(stripped,self.labels[stripped]) if stripped in self.labels else data))

    def handle_entityref(self, name): self.parts.append('&%s;' % name)
    def handle_charref(self, name): self.parts.append('&#%s;' % name)
    def handle_comment(self, data): self.parts.append('<!--%s-->' % data)
    def handle_decl(self, data): self.parts.append('<!%s>' % data)
    def handle_startendtag(self, tag, attrs): self.parts.append(self.get_starttag_text())


def localized_pages(output, languages, title, description):
    output = Path(output)
    if not languages:
        return
    # Links stay beside index.html, so media is never duplicated.
    for stem in ('index', 'slideshow'):
        source = (output / (stem + '.html')).read_text(encoding='utf-8')
        links = '<nav aria-label="Languages" style="padding:12px;text-align:center"><a href="%s.html">Svenska</a> ' % stem
        links += ' '.join('<a hreflang="%s" href="%s.%s.html">%s</a>' % (code, stem, code, code) for code in languages) + '</nav>'
        base = re.sub(r'(<body\b[^>]*>)', lambda m: m[1]+links, source, count=1, flags=re.I)
        (output / (stem+'.html')).write_text(base, encoding='utf-8')
        for code, item in languages.items():
            labels = dict(BUILTIN.get(code.split('-')[0], {}))
            labels.update(item['labels'])
            if title and item['title']: labels[title] = item['title']
            if description and item['description']: labels[description] = item['description']
            parser = Translate(labels)
            parser.feed(base)
            text = ''.join(parser.parts)
            text = re.sub(r'<html\b[^>]*>', '<html lang="%s" dir="%s">' % (code,item['dir']), text, count=1, flags=re.I)
            if item['title']:
                text = re.sub(r'<title>.*?</title>', lambda m:'<title>'+html.escape(item['title'])+(' - Slideshow' if stem=='slideshow' else '')+'</title>',text,count=1,flags=re.S)
            text = text.replace('href="index.html"', 'href="index.%s.html"' % code).replace('href="slideshow.html"', 'href="slideshow.%s.html"' % code)
            # Keep Svenska pointing to the original, not the current locale.
            text = text.replace('href="%s.%s.html">Svenska' % (stem,code), 'href="%s.html">Svenska' % stem)
            text = text.replace('</body>',runtime_translation(labels)+'</body>')
            (output / ('%s.%s.html' % (stem,code))).write_text(text, encoding='utf-8')


def quality_markup(videos):
    sections = []
    for video in videos:
        if not video.get('qualities'): continue
        sources = {'Standard': video['relative_path'], **video['qualities']}
        buttons = ''.join('<button type="button" data-src="%s">%s</button>' % (html.escape(src,quote=True),html.escape(label)) for label,src in sources.items())
        sections.append('<section class="quality-player"><h3>%s</h3><div>%s</div><video controls playsinline preload="none" src="%s" style="max-width:100%%"></video></section>' %
                        (html.escape(video['name']),buttons,html.escape(video['relative_path'],quote=True)))
    if not sections: return ''
    return '<details style="padding:16px"><summary>Videospelare med kvalitetsval</summary>'+''.join(sections)+'''</details><script>
document.querySelectorAll('.quality-player').forEach(function(p){p.querySelectorAll('button[data-src]').forEach(function(b){b.onclick=function(){var v=p.querySelector('video'),t=v.currentTime,playing=!v.paused;v.pause();v.src=b.dataset.src;v.addEventListener('loadedmetadata',function(){v.currentTime=Math.min(t,v.duration||t);if(playing)v.play().catch(function(){});},{once:true});v.load();};});});</script>'''
