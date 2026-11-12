# Copyright (c) 2026 Rickard Längkvist
"""Rebuild outlined SVG and app assets. Build-only: fonttools, resvg-py, Pillow.
Uses DejaVu Sans Bold (see branding/FONT-LICENSE.txt), no runtime font dependency.
"""
from pathlib import Path
import argparse
import io

ROOT = Path(__file__).resolve().parents[1]
SHAPES = '''<path fill="#26dce0" d="M20 58H138L110 88H50V158L20 188Z"/>
<path fill="#12acc9" d="M35 73H123L110 88H50V158L35 173Z"/>
<path fill="#8e2ed2" d="M60 240L139 170L119 208H219V125L249 155V240Z"/>
<path fill="#b735d8" d="M95 225L139 170L119 208H219V125L234 140V225Z"/>
<path fill="#f445a4" d="M234 64L241 73V162L226 147Z"/>
<path fill="#23dfe0" d="M20 213L160 56L134 35L232 8L221 108L193 86L20 248Z"/>
<path fill="#19b9d0" d="M20 213L174 92L20 248Z"/>
<path fill="#9632cf" d="M20 248L232 8L221 108L193 86Z"/>'''


def svg(width, height, content):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" viewBox="0 0 %s %s">'
            '<title>FTP Uploader</title>%s</svg>\n') % (width, height, width, height, content)


def build(font_path):
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    import resvg_py
    from PIL import Image
    brand = ROOT / 'branding'
    icon = ROOT / 'icon'
    brand.mkdir(exist_ok=True)
    font = TTFont(font_path)
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    x = 0
    paths = []
    for char in 'FTP Uploader':
        name = cmap[ord(char)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        paths.append('<path transform="translate(%s 0)" d="%s"/>' % (x, pen.getCommands()))
        x += glyphs[name].width
    scale = 660 / x
    word = '<g transform="translate(70 405) scale(%s -%s)">%s</g>' % (scale, scale, ''.join(paths))
    symbol = '<g transform="translate(260 25) scale(1.1)">%s</g>' % SHAPES
    for filename, bg, ink in [('logo.svg', '', '#10172f'), ('logo-dark.svg', '<path fill="#090f26" d="M0 0H800V480H0Z"/>', '#ffffff')]:
        (brand / filename).write_text(svg(800, 480, bg + symbol + '<g fill="%s">%s</g>' % (ink, word)), encoding='utf-8')
    (brand / 'symbol.svg').write_text(svg(268, 260, SHAPES), encoding='utf-8')
    mono = __import__('re').sub(r'fill="#[0-9a-f]+"', 'fill="#000000"', symbol)
    (brand / 'logo-monochrome.svg').write_text(svg(800, 480, mono + '<g fill="#000000">%s</g>' % word), encoding='utf-8')
    app_svg = svg(288, 288, '<rect width="288" height="288" rx="60" fill="#090f26"/><g transform="translate(10 14)">%s</g>' % SHAPES)
    (icon / 'icon.svg').write_text(app_svg, encoding='utf-8')
    master = Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=app_svg, width=1024, height=1024))).convert('RGBA')
    master.save(icon / 'icon.png')
    master.save(icon / 'app_master.png')
    for size in (16, 32, 64, 256):
        master.resize((size, size), Image.Resampling.LANCZOS).save(icon / ('icon_%d.png' % size))
    master.save(icon / 'icon.ico', sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    master.save(icon / 'icon.icns', format='ICNS')
    (brand / 'logo-preview.png').write_bytes(resvg_py.svg_to_bytes(svg_string=(brand / 'logo-dark.svg').read_text(), width=1600, height=960))
    # Keep the existing overview asset in sync rather than displaying old branding.
    Image.open(brand / 'logo-preview.png').save(icon / 'ikon_oversikt.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', required=True, help='Path to DejaVuSans-Bold.ttf')
    build(parser.parse_args().font)
