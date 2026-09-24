"""Publish the native town-prose rendering preflight with its actual pages."""
import html
import json
from tools.rom import ROOT, digest, require
from tools.verify_town_prose_preflight import OUT, CATALOG


def run():
    report = json.loads((OUT / 'report.json').read_text())
    build = json.loads((OUT / 'build.json').read_text())
    require(report['passed'] and report['rom_sha256'] == build['output_sha256'], 'Stale town prose report')
    require(build['preflight']['catalog_sha256'] == digest(CATALOG.read_bytes()), 'Town prose review changed')
    rows = {r['id']: r for r in build['preflight']['entries']}
    cards, images = [], {}
    escape = html.escape
    for relative in report['case_reports']:
        path = ROOT / relative
        case = json.loads(path.read_text())
        row = rows[case['cache_key']['id']]
        pictures = []
        for name, expected in case['images'].items():
            image = path.parent / name
            require(digest(image.read_bytes()) == expected, 'Town prose screenshot changed')
            link = str(image.relative_to(OUT))
            images[link] = expected
            pictures.append(f'<img loading="lazy" width="480" height="320" src="{escape(link)}" alt="{escape(row["id"] + " " + name)}">')
        cards.append('<details><summary>' + escape(row['id'] + ' · ' + case['cache_key']['case']) +
                     '</summary><pre>' + escape(row['japanese']) + '</pre><pre>' + escape(row['english']) +
                     '</pre><p>Compiled line widths: ' + escape(str(row['layout']['line_widths'])) +
                     'px. Budget: 216px.</p>' + ''.join(pictures) + '</details>')
    require(len(cards) == report['cases'], 'Town prose cases missing')
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 town prose preflight</title>'
            '<style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}'
            'details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}'
            'img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}a{color:#bce}</style>'
            '<h1>Torneko 2 town prose preflight</h1><p>' + escape(report['scope']) + '</p><p>ROM: ' +
            report['rom_sha256'] + ' · <a href="report.json">Native evidence</a></p>' + ''.join(cards))
    (OUT / 'index.html').write_text(page + '\n')
    (OUT / 'preview.json').write_text(json.dumps({'rom_sha256': report['rom_sha256'], 'cases': len(cards), 'images': images}, indent=2) + '\n')
    print(OUT / 'index.html')


if __name__ == '__main__':
    run()
