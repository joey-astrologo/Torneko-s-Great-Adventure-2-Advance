"""Require same-ROM case, source and capture evidence for owned trap consumers."""
import json

from tools.dialogue_checks import player_layout_cases
from tools.rom import ROOT, digest, require


def validate(build, receipt, counts):
    names = [name for name, _ in player_layout_cases()]
    cases = {
        'warp-trap': {f'{failed}-{name}' for failed in (0, 1) for name in names},
        'unequip-trap': {'activated', 'refused', 'nothing-equipped', 'protected'},
        'mud-trap': {f'bread-{i}' for i in range(203, 211)} | {'refused', 'no-bread'},
        'damage-traps': {f'{kind}-{failed}-{name}' for kind in ('poison-arrow', 'falling-rock')
                         for failed in (0, 1) for name in names},
        'rust': {'acid-leather', 'acid-rust', 'acid-refused', 'shield-none', 'weapon-none',
                 'both-none', 'shield-leather', 'shield-silver', 'shield-rust', 'weapon-rust',
                 'shield-minimum', 'weapon-minimum', 'shield-ring', 'weapon-ring',
                 'shield-protected', 'weapon-protected', 'named-maximum-width',
                 'named-maximum-bytes', 'named-coloured'},
        'summon-trap': {'activated', 'refused', 'other-spawn-mode', 'zero-spawn-count'},
        'blast-traps': {f'{kind}-{failed}-{name}' for kind in ('mine', 'iron-ball')
                        for failed in (0, 1) for name in names},
        'pitfall': {'activated', 'refused', 'protected', 'special-floor'},
    }
    resource_counts = {'warp-trap': 2, 'unequip-trap': 4, 'mud-trap': 5, 'damage-traps': 4, 'rust': 11}
    resource_counts.update({'summon-trap': 4, 'blast-traps': 4, 'pitfall': 3})
    for family, expected in cases.items():
        folder = ROOT / f'build/english/{family}-validation'
        report = json.loads((folder / 'report.json').read_text())
        rows = report['cases']
        require(report['passed'] and report['rom_sha256'] == build['output_sha256'],
                'Stale trap evidence: ' + family)
        require(len(rows) == len(expected) and {r['case'] for r in rows} == expected,
                'Missing or duplicate trap cases: ' + family)
        entries = build[family.replace('-', '_')]['entries']
        require(len(entries) == resource_counts[family] and
                {r['table_offset'] for r in entries} <= {s for r in rows for s in r['queue_slots']},
                'Missing trap source coverage: ' + family)
        preview = json.loads((folder / 'preview.json').read_text())
        require(preview['rom_sha256'] == build['output_sha256'] and preview['cases'] == len(rows),
                'Stale trap gallery: ' + family)
        captures = {r['case'] + '/' + path: sha for r in rows for path, sha in r['images'].items()}
        require(captures == preview['images'], 'Trap gallery coverage differs: ' + family)
        for relative, sha in captures.items():
            path = folder / relative
            require(digest(path.read_bytes()) == sha, 'Trap capture changed: ' + str(path))
        counts[family] = len(rows)
        for pattern in ('*.json', 'index.html', '*/*.png', '*/*.json', 'native/*.json'):
            for path in folder.glob(pattern):
                if path.is_file():
                    receipt['artifacts'][str(path.relative_to(ROOT))] = digest(path.read_bytes())
    receipt.update(trap_native_cases=sum(counts[k] for k in cases),
        trap_text_resources=sum(resource_counts.values()),
        trap_text_scope='Owned warp, equipment-removal, mud, poison-arrow, falling-rock and acid/rust consumers. '
        'Controlled handler entry, names and activation/state branches check complete native message chains, '
        'teleport movement, equipment removal, bread conversion, strength/HP loss and rust enhancement changes. '
        'Native source item properties are retained. Rust fields cover colours, the full 64-byte capacity, '
        'maximum-width conditional wrapping and the -99 enhancement limit. Protection/ring return overrides '
        'are recorded. Ordinary trap discovery, protection acquisition, other inventory arrangements and '
        'death/revival remain separate. Summoning covers four native spawned monsters in both modes '
        'and controlled zero-count refusal. Mine/iron-ball cases check native HP damage and the complete '
        'damage-message chain. Pitfalls include the separately owned delayed five-HP damage consumer, '
        'refusal, protection and special-floor branches; final next-floor arrival remains separate.')
