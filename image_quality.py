# Copyright (c) 2026 Rickard Längkvist
"""Advisory resolution checks, never claim to measure optical sharpness."""
import html
import json
from pathlib import Path


def assess_size(width, height, target=1920):
    longest = max(width, height)
    return {'width': width, 'height': height, 'target_long_edge': target,
            'scale_to_target': round(target / longest, 2) if longest else None,
            'small_image': longest < 1280,
            'upscale_risk': longest < target}


def write_quality_report(entries, output, target=1920):
    from PIL import Image, ImageOps
    results = []
    for entry in entries:
        name = str(entry.get('filename') or Path(entry['full_dst']).name)
        try:
            with Image.open(entry['full_dst']) as image:
                oriented = ImageOps.exif_transpose(image)
                try:
                    result = assess_size(*oriented.size, target)
                finally:
                    if oriented is not image:
                        oriented.close()
            result['name'] = name
        except (OSError, ValueError) as exc:
            result = {'name': name, 'error': type(exc).__name__}
        results.append(result)
    report = {'reference_long_edge': target, 'images': results,
              'note': 'Rådgivande upplösningskontroll, inte mätning av fokus. Jämförelse: långsida 1920 px. Faktisk CSS, skärm och DPI avgör visningsbehovet. Ingen bild ändras eller skalas upp av kontrollen.'}
    root = Path(output)
    (root/'image-quality.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = []
    for item in results:
        status = ('Kunde inte läsa bildmått' if 'error' in item else
                  ('Liten bild; ' if item['small_image'] else '') +
                  ('Risk för grumlighet vid förstoring till 1920 px' if item['upscale_risk'] else 'Tillräcklig upplösning för referensstorleken'))
        rows.append('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (html.escape(item['name']),
                    '%s × %s' % (item.get('width','?'), item.get('height','?')), status))
    (root/'image-quality.html').write_text('<!doctype html><html lang="sv"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Bildkvalitet</title><style>body{font:1rem system-ui;max-width:70rem;margin:2rem auto;padding:1rem}td,th{text-align:left;padding:.7rem;border-bottom:1px solid #aaa}table{width:100%}</style><h1>Bildstorlek och uppskalningsrisk</h1><p>'+html.escape(report['note'])+'</p><table><tr><th>Bild</th><th>Pixlar</th><th>Bedömning</th></tr>'+''.join(rows)+'</table></html>',encoding='utf-8')
    return report
