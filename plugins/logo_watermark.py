# Copyright (c) 2026 Rickard Längkvist
"""Optional logo overlay on processed web images only; source files stay untouched."""
from pathlib import Path


def validate(gallery):
    # A remembered filename alone must NEVER enable the watermark.
    if gallery.get('watermark_enabled') is not True:
        return None
    path = Path(str(gallery.get('watermark_logo') or '').strip())
    if not path.is_file() or path.suffix.lower() != '.svg':
        raise ValueError('Välj en befintlig SVG-fil för vattenstämpeln eller avmarkera kryssrutan.')
    opacity = int(gallery.get('watermark_opacity', 70))
    if not 1 <= opacity <= 100:
        raise ValueError('Vattenstämpelns opacitet måste vara 1–100 %.')
    # Reject external resources before handing markup to the renderer. No network,
    # local file references, scripts, entities or linked CSS are permitted.
    from defusedxml import ElementTree
    import re
    with path.open('rb') as source:
        raw = source.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('SVG-logotypen får vara högst 2 MiB.')
    try:
        tree = ElementTree.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        if tree.tag != '{http://www.w3.org/2000/svg}svg':
            raise ValueError('Filen saknar ett giltigt SVG-rotelement.')
        for element in tree.iter():
            tag = element.tag.split('}')[-1].lower()
            if tag in ('text', 'tspan', 'textpath'):
                raise ValueError('Omvandla SVG-logotypens text till banor före import, så att inga lokala typsnitt behövs.')
            if tag in ('script', 'foreignobject', 'image'):
                raise ValueError('SVG-logotypen måste vara fristående vektorgrafik utan skript eller inbäddade bilder.')
            values = list(element.attrib.values())
            if tag == 'style':
                values.append(element.text or '')
            for key, value in element.attrib.items():
                if key.split('}')[-1].lower() in ('href', 'base') and value and not value.startswith('#'):
                    raise ValueError('SVG får inte referera till externa resurser.')
            for value in values:
                value = re.sub(r'/\*.*?\*/', '', value, flags=re.S)
                if chr(92) in value or '@' in value:
                    raise ValueError('SVG får inte innehålla importer eller CSS-escape-sekvenser.')
                for reference in re.findall(r'url\(\s*([^)]*)\)', value, flags=re.I):
                    if not reference.strip().strip('\"\'').startswith('#'):
                        raise ValueError('SVG får bara använda interna url(#...) referenser.')
        from resvg_py import svg_to_bytes
        # Serialize the validated XML, not a second read of a changeable source file.
        markup = ElementTree.tostring(tree, encoding='unicode')
        rendered = svg_to_bytes(svg_string=markup, width=2048, height=2048,
                                skip_system_fonts=True, log_information=False)
    except ImportError as exc:
        raise ValueError('SVG-stöd saknas. Installera appens beroenden resvg-py och defusedxml.') from exc
    except Exception as exc:
        raise ValueError('SVG-logotypen kunde inte läsas säkert: %s' % exc) from exc
    return rendered, opacity


def apply_logo(image, options):
    """Return a new RGB image. At most 20% of either dimension, bottom right."""
    from PIL import Image
    if not options:
        return image
    from io import BytesIO
    rendered, opacity = options
    with Image.open(BytesIO(rendered)) as source:
        logo = source.convert('RGBA')
    try:
        logo.thumbnail((max(1, image.width // 5), max(1, image.height // 5)), Image.Resampling.LANCZOS)
        alpha = logo.getchannel('A').point(lambda value: round(value * opacity / 100))
        logo.putalpha(alpha)
        alpha.close()
        output = image.convert('RGB')
        margin = max(1, round(min(image.size) * .03))
        output.paste(logo, (max(0, output.width - logo.width - margin),
                            max(0, output.height - logo.height - margin)), logo)
        return output
    finally:
        logo.close()


def create_controls(parent):
    import tkinter as tk
    from tkinter import ttk, filedialog
    frame = ttk.Frame(parent)
    frame.pack(fill='x', pady=8)
    enabled = tk.BooleanVar(master=parent, value=False)
    path = tk.StringVar(master=parent, value='')
    opacity = tk.IntVar(master=parent, value=70)
    ttk.Checkbutton(frame, text='Inkludera vattenstämpel från SVG-logotyp', variable=enabled).pack(anchor='w')
    row = ttk.Frame(frame)
    row.pack(fill='x')
    ttk.Entry(row, textvariable=path).pack(side='left', fill='x', expand=True)
    def browse():
        chosen = filedialog.askopenfilename(parent=parent, title='Välj logotyp',
                 filetypes=[('SVG-logotyp', '*.svg')])
        if chosen:
            path.set(chosen)
    ttk.Button(row, text='Välj…', command=browse).pack(side='left', padx=4)
    ttk.Label(frame, text='Opacitet 1–100 %:').pack(anchor='w')
    ttk.Spinbox(frame, from_=1, to=100, textvariable=opacity, width=8).pack(anchor='w')
    ttk.Label(frame, text='Endast när kryssrutan är markerad. Välj fristående SVG-vektorgrafik med text omvandlad till banor. '
              'Originalnedladdningar får ingen vattenstämpel. Äldre exporter får ingen ny '
              'stämpel vid omsparning; generera om från källbilderna för att byta logotyp.',
              wraplength=650).pack(anchor='w')
    return enabled, path, opacity
