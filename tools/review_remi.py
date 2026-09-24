"""Review the remi's source text, native pages and transaction evidence."""
import argparse
import html
import json
from tools.rom import ROOT, digest, require
from tools.verify_remi import OUT


def run(cumulative=False):
    global OUT
    if cumulative:
        OUT = ROOT / 'build/english/remi-validation'
    build = json.loads((ROOT / 'build/english/build.json' if cumulative else OUT / 'build.json').read_text())
    rows = {r['id']: r for r in build['remi']['entries']}
    cards, images, counts = [], {}, {}
    for filename, prefix in [(name, '') for name in ('report.json','menus.json','pickers.json','picker-fallbacks.json','vocations.json','saved-village.json')] + [('safe.json','safe-'),('charges.json','charges-'),('levels.json','levels-'),('warp-menus.json','warp-'),('warp-payments.json','warp-payment-')]:
        report = json.loads((OUT / filename).read_text())
        require(report['passed'] and report['rom_sha256'] == build['output_sha256'], 'Stale remi native evidence')
        counts[filename] = len(report['cases'])
        for case in report['cases']:
            pictures = []
            for name, expected in case['images'].items():
                relative = prefix + case['case'] + '/' + name
                require(digest((OUT / relative).read_bytes()) == expected, 'Remi screenshot changed')
                images[relative] = expected
                pictures.append('<img loading="lazy" width="480" height="320" src="' + html.escape(relative) + '">')
            text = ''
            if case.get('id') in rows:
                row = rows[case['id']]
                text = '<pre>' + html.escape(row['japanese']) + '</pre><pre>' + html.escape(row['english']) + '</pre><p>' + html.escape(str(row['layout'])) + '</p>'
            cards.append('<details><summary>' + html.escape(prefix + case['case']) + '</summary>' + text + ''.join(pictures) + '</details>')
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 remi text</title>'
            '<style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}'
            'details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}'
            'img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}a{color:#bce}</style>'
            '<h1>Torneko 2 remi text</h1><p>' + ('Cumulative candidate. ' if cumulative else 'Separate prototype. ') + 'Controlled service invocation and inventories; '
            'native text, original menu geometry, number selectors, all vocation choices and saved-village overwrite warning. Iron safe purchases, staff charging, level changes, warp labels and native warp payment/output records are checked. The later dispatcher transition, actual village overwrite/cold reload and ordinary unlocking remain separate.</p>'
            '<p><a href="report.json">Rendering/formatter cases</a> · <a href="vocations.json">Vocation changes</a> · <a href="menus.json">Menu cases</a></p>' + ''.join(cards))
    (OUT / 'index.html').write_text(page + '\n')
    (OUT / 'preview.json').write_text(json.dumps({'rom_sha256': build['output_sha256'], 'case_counts': counts, 'images': images}, indent=2) + '\n')
    print(OUT / 'index.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
