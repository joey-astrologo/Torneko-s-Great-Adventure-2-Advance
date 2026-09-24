"""Source, English and native screenshots for the closed static queue mapping."""
import argparse
import html
import json
from pathlib import Path

from tools.rom import ROOT, digest, require
from tools.verify_queue_notices import OUT


def run(source=ROOT / 'build/english', output=OUT):
    global OUT
    OUT = Path(output)
    build = json.loads((source / 'build.json').read_text())
    report = json.loads((OUT / 'report.json').read_text())
    require(report['passed'] and report['rom_sha256'] == build['output_sha256'],
            'Stale queue-notice gallery evidence')
    rows = {r['id']: r for r in build['combat']['queue_notices']['entries']}
    images, cards = {}, []
    for case in report['cases']:
        for name, capture_sha in case['images'].items():
            capture_path = case['case'] + '/' + name
            require(digest((OUT / capture_path).read_bytes()) == capture_sha, 'Queue-notice image changed')
            images[capture_path] = capture_sha
        row = rows.get(case['id'].removesuffix('-copied'))
        text = (row['source']['japanese'] + '\n' + row['english']) if row else case['id']
        relative = case['case'] + '/rendered.png'
        sha = case['images']['rendered.png']
        require(digest((OUT / relative).read_bytes()) == sha, 'Queue-notice image changed')
        images[relative] = sha
        cards.append('<details><summary>' + html.escape(case['case']) + '</summary><pre>' +
                     html.escape(text) + '</pre><p>' + str(case['queue']['line_widths']) +
                     'px / 216px; ' + str(case['queue']['bytes']) + ' bytes.</p><img width="480" '
                     'height="320" loading="lazy" src="' + html.escape(relative) + '"></details>')
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 static notices</title>'
            '<style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}'
            'details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}'
            'img{image-rendering:pixelated;max-width:100%;height:auto}</style>'
            '<h1>Torneko 2 static notices</h1><p>' + html.escape(report['scope']) + '</p>')
    (OUT / 'index.html').write_text(page + ''.join(cards) + '\n')
    (OUT / 'preview.json').write_text(json.dumps({'rom_sha256': report['rom_sha256'],
        'cases': len(report['cases']), 'images': images}, indent=2) + '\n')
    print(OUT / 'index.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/english')
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    run(args.source, args.output)
