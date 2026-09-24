"""Pin complete source/case/capture evidence for additional trap and monster effects."""
import json
from tools.dialogue_checks import player_layout_cases
from tools.rom import ROOT, digest, require


def validate(build, receipt, counts):
    names = {name for name, _ in player_layout_cases()}
    fields = {'maximum-width', 'maximum-bytes', 'coloured'}
    expected = {
        'bear-trap': {'activated', 'refused', 'grab-six', 'grab-seven'} | fields,
        'stumble-trap': {'empty', 'refused', 'protected', 'staff', 'drop', 'placement-full'} | fields,
        'curse': {'shield', 'weapon', 'ring', 'priority', 'carried', 'empty', 'already-cursed',
                  'curseproof-ring', 'protected', 'ability'} | fields,
        'drain': {'strength', 'strength-clamp', 'strength-minimum', 'strength-current-low',
                  'hp', 'hp-clamp', 'hp-minimum', 'hp-current-low', 'resistant', 'strength-protected'} |
                 {kind + '-' + name for kind in ('strength', 'hp') for name in fields} |
                 {'player-' + name for name in names},
        'level-drain': {kind + '-' + name for kind in ('one', 'two', 'clamp', 'minimum', 'transformed', 'resistant')
                        for name in names},
        'steal-gold': {'ordinary', 'empty', 'all-gold', 'maximum-gold', 'protected', 'ability', 'transformed',
                       'combined-maximum-width', 'combined-maximum-bytes'} | fields |
                      {'player-' + name for name in names},
    }
    expected['monster-conditions'] = ({'fullness-'+str(v) for v in (0,5120,5121,5376,25600,51200,0x7FFFFFFF)} |
        {'fullness-'+kind+'-'+name for kind in ('protected','resistant') for name in names} |
        {'seal-'+kind+'-'+name for kind in ('fresh','existing','resistant') for name in names} |
        {'kaclang-'+name for name in fields | {'native','existing'}})
    resources = {'monster-conditions': 3, 'bear-trap': 3, 'stumble-trap': 4, 'curse': 2, 'drain': 3, 'level-drain': 3, 'steal-gold': 4}
    for family, required in expected.items():
        folder = ROOT / f'build/english/{family}-validation'
        report = json.loads((folder / 'report.json').read_text())
        rows = report['cases']
        require(report['passed'] and report['rom_sha256'] == build['output_sha256'],
                'Stale monster-effect report: ' + family)
        require(len(rows) == len(required) and {r['case'] for r in rows} == required,
                'Monster-effect cases missing/duplicated: ' + family)
        entries = build[family.replace('-', '_')]['entries']
        require(len(entries) == resources[family], 'Monster-effect resources differ: ' + family)
        if family == 'steal-gold':
            require({r['id'] for r in entries} == {f['id'] for r in rows for f in r['formats']},
                    'Gold format/fragment source coverage differs')
        else:
            require({r['table_offset'] for r in entries} <= {s for r in rows for s in r['queue_slots']},
                    'Monster-effect source coverage differs: ' + family)
        require(all(max(q['line_widths']) <= 216 for r in rows for q in r['queues']),
                'Monster-effect native line exceeds budget: ' + family)
        preview = json.loads((folder / 'preview.json').read_text())
        images = {r['case'] + '/' + path: sha for r in rows for path, sha in r['images'].items()}
        require(preview['rom_sha256'] == build['output_sha256'] and preview['cases'] == len(rows)
                and preview['images'] == images, 'Stale monster-effect gallery: ' + family)
        for relative, sha in images.items():
            require(digest((folder / relative).read_bytes()) == sha, 'Monster-effect image changed')
        counts[family] = len(rows)
        for pattern in ('*.json', 'index.html', '*/*.png', '*/*.json', 'native/*.json'):
            for path in folder.glob(pattern):
                if path.is_file():
                    receipt['artifacts'][str(path.relative_to(ROOT))] = digest(path.read_bytes())
    receipt.update(monster_effect_resources=sum(resources.values()),
                   monster_effect_native_cases=sum(counts[k] for k in expected),
                   monster_effect_scope='Additional bear/stumbling trap, curse, stat/level drain and gold theft '
                   'consumers plus fullness loss, spell sealing and Kaclang. Controlled handler/state/field inputs verify complete messages and native '
                   'effects, original formatter/field capacities, ABI and unaffected items/gold/HP/save. '
                   'Ordinary AI, trap discovery, resistance acquisition and later recovery/progression remain '
                   'separate. Each family report records the exact controlled overrides and native effects.')
