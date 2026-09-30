"""Independent, unfiltered text observations for bounded dungeon scenarios."""
import argparse
import html
import json
from pathlib import Path

import mgba.log

from tools.emulator import BIOS, Debugger, Session, Snapshot, version
from tools.holy_flame_playtest import items, use
from tools.mansion_playtest import walk_to_stairs
from tools.name_entry_playtest import ACTORS, MAP, position
from tools.rom import ROOT, default_rom, digest, require
from tools.screen_text_audit import ScreenTextAudit, glyph_text

OUT = ROOT / 'build/coverage-audit/dungeon'


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class AuditedSession(Session):
    """Capture after each input that draws text, without changing its timing."""
    audit = None
    last_capture_glyph = 0

    def _advance(self, count):
        if self.audit is None:
            return super()._advance(count)
        for _ in range(count):
            super()._advance(1)
            glyphs = self.audit.glyphs
            if (glyphs and len(glyphs) != self.last_capture_glyph and
                    self.core.frame_counter >= glyphs[-1]['frame']+3):
                label = f'text-{self.core.frame_counter:06d}'
                self.capture(label)
                self.images.append({'path': label+'.png', 'frame': self.core.frame_counter,
                    'glyph_range': [self.last_capture_glyph, len(glyphs)],
                    'png_sha256': digest((self.output/(label+'.png')).read_bytes())})
                self.last_capture_glyph = len(glyphs)

    def press(self, key, wait=120, hold=3):
        if self.audit is None:
            return super().press(key, wait=wait, hold=hold)
        label = f'input-{len(self.inputs):04d}'
        self.audit.phase = label
        before = len(self.audit.glyphs), len(self.audit.observer.reads), len(self.audit.queues)
        super().press(key, wait=wait, hold=hold)
        after = len(self.audit.glyphs), len(self.audit.observer.reads), len(self.audit.queues)
        if after != before:
            self.capture(label)
            self.images.append({'path': label+'.png', 'frame': self.core.frame_counter,
                'glyph_range': [before[0], after[0]], 'reader_range': [before[1], after[1]],
                'queue_range': [before[2], after[2]],
                'png_sha256': digest((self.output/(label+'.png')).read_bytes())})


def inspect_items(game):
    game.press('B', hold=8, wait=120)
    game.press('A', wait=120)
    game.capture('inventory')
    game.press('B', wait=120)
    game.press('B', wait=120)


def natural_loot(game, details, maximum=False):
    """The earned mansion save has real arrows near spawn and gold farther away."""
    m = game.core.memory
    actor = m.u32[ACTORS]
    before_arrows = next(n for _, ident, n in items(game) if ident == 79)
    before_gold = m.u32[actor+0x60]
    details['walks'] = []
    for target, ident in [((9, 25), 79), ((8, 6), 212)]:
        pointer = m.u32[MAP+(target[0]*32+target[1])*28+16]
        require(m.u8[0x020013D0+m.u8[pointer+8]] == ident, 'Natural floor item differs')
        if maximum and ident == 212:
            details['controlled_overrides'].append({'address': pointer+4,
                'before': bytes(m[pointer+4:pointer+6]).hex(), 'after': 'ff7f',
                'reason': 'Maximum positive signed-halfword gold amount; existing floor item'})
            m.u16[pointer+4] = 32767
        value = m.u16[pointer+4] if ident == 212 else m.u8[pointer+4]
        details['walks'].append({'target': target, 'item_id': ident, 'value': value,
                                'steps': walk_to_stairs(game, target)})
        game.capture('gold' if ident == 212 else 'arrows')
        if ident == 79:
            require(next(n for _, i, n in items(game) if i == 79) == before_arrows+value,
                    'Native arrow merge was not reached')
        else:
            require(m.u32[actor+0x60] == before_gold+value, 'Native gold pickup was not reached')
            messages = [''.join(glyph_text(c) for c in q['drawn_codes'])
                        for q in game.audit.final_queues]
            require(f'Picked up {value} Gold.' in messages, 'Gold pickup lacks the English word space')
    details['inventory_after'] = items(game)
    details['gold_before'], details['gold_after'] = before_gold, m.u32[actor+0x60]
    inspect_items(game)


def info(game, details):
    use(game, 204, 40)
    game.capture('description')
    game.press('B', wait=120)
    game.capture('description-closed')
    details['item_id'] = 204


def eat(game, details):
    before = len(items(game))
    use(game, 204, 11)
    game.capture('eaten')
    require(len(items(game)) == before-1, 'Native Eat did not consume the bread')
    details['item_id'] = 204


def drop_and_pick_up(game, details, full=False):
    m = game.core.memory
    initial = items(game)
    use(game, 204, 7)
    game.capture('dropped')
    game.press('B', hold=8, wait=30)
    game.press('B', hold=8, wait=30)
    origin = position(game)
    pointer = m.u32[MAP+(origin[0]*32+origin[1])*28+16]
    require(pointer and len(items(game)) == len(initial)-1, 'Native Drop did not complete')
    if full:
        # Explicit controlled capacity case. No floor-item, actor, PC or register
        # changes; the native Drop above owns and establishes the floor item.
        source = bytes(m[pointer:pointer+120])
        for slot in range(20):
            address = 0x0200DF28+slot*120
            if not m.u32[address] & 0x80000000:
                old = bytes(m[address:address+120])
                details['controlled_overrides'].append({'address': address,
                    'before': old.hex(), 'after': source.hex(),
                    'reason': 'Fill a vacant slot to exercise inventory-full refusal'})
                for i, value in enumerate(source):
                    m.u8[address+i] = value
        require(len(items(game)) == 20, 'Controlled inventory is not full')
    before = bytes(m[0x0200DF28:0x0200DF28+2400])
    for key, back, dx, dy in [('LEFT','RIGHT',-1,0),('RIGHT','LEFT',1,0),
                               ('UP','DOWN',0,-1),('DOWN','UP',0,1)]:
        if not m.u32[MAP+((origin[0]+dx)*32+origin[1]+dy)*28+20] & 0x4000:
            continue
        game.press(key, wait=90)
        if position(game) != origin:
            game.press(back, wait=180)
            break
    require(position(game) == origin, 'Ordinary step back missed the dropped item')
    game.capture('pickup-result')
    if full:
        require(bytes(m[0x0200DF28:0x0200DF28+2400]) == before and
                m.u32[MAP+(origin[0]*32+origin[1])*28+16] == pointer,
                'Full inventory refusal changed carried items or removed the floor item')
    else:
        require(len(items(game)) == len(initial), 'Ordinary walking pickup failed')
    details['inventory_before'] = initial
    details['inventory_after'] = items(game)


CASES = {'natural-gold-arrows-combat': natural_loot, 'item-info': info,
         'eat-bread': eat, 'drop-walk-pickup': drop_and_pick_up,
         'full-inventory': lambda g, d: drop_and_pick_up(g, d, full=True),
         'maximum-gold': lambda g, d: natural_loot(g, d, maximum=True)}


def tutorial(game, details):
    route_path = ROOT/'config/routes/dungeon-coverage.json'
    route = json.loads(route_path.read_text())
    require(game.core.frame_counter == route['fixture_frame'], 'Tutorial starting frame differs')
    for i, step in enumerate(route['inputs']):
        if 'key' in step or 'keys' in step:
            game.press(step.get('key', step.get('keys')), hold=step['hold'], wait=step['released'])
        elif 'frames' in step:
            game.frames(step['frames'])
        else:
            raise ValueError('Unrecognized replay input')
        if i % 100 == 0:
            print('Tutorial input', i, 'pickups', len(game.audit.pickups), flush=True)
    observed = [{k: x[k] for k in ('floor','position','item_id')} for x in game.audit.pickups]
    require(observed == route['expected_pickups'], 'Tutorial did not reach all 14 expected pickups')
    details['route_sha256'] = digest(route_path.read_bytes())
    details['route'] = str(route_path.relative_to(ROOT))
    details['all_14_pickups_matched'] = True


CASES['tutorial-three-floors'] = tutorial


def run(selected, source=ROOT/'build/english', output=OUT):
    mgba.log.silence()
    rom_path = source / 'torneko-2-english.gba'
    rom = rom_path.read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Build differs from insertion ledger')
    protected = {str(p): digest(p.read_bytes()) for p in
                 (default_rom(), default_rom().with_suffix('.sav'), rom_path)}
    from tools.service_fixtures import dungeon
    service_fixture = dungeon(rom, build)
    service_fixture.save(output/'service-fixture/ready')
    provenance = output/'service-fixture/inputs.json'
    provenance.write_bytes((ROOT/'build/services/current-dungeon/inputs.json').read_bytes())
    fresh = None
    results = []
    for name in selected:
        print('Screen audit:', name, flush=True)
        folder = output/name
        fixture = service_fixture
        if name == 'tutorial-three-floors':
            from tools.verify_location_banner import fresh_fixture
            fresh = fresh_fixture(rom, output/'fresh-fixture')
            fixture = fresh
        case_provenance = output/'fresh-fixture/inputs.json' if fresh is fixture else provenance
        with AuditedSession(rom, folder) as game:
            game.restore(fixture)
            game.audit = audit = ScreenTextAudit(game)
            game.images = []
            details = {'controlled_overrides': []}
            error = None
            with Debugger(game, audit.callback, max_events=500000) as debug:
                for address in audit.ADDRESSES:
                    debug.breakpoint(address)
                try:
                    CASES[name](game, details)
                except Exception as exc:
                    error = str(exc) + (': '+str(exc.__cause__) if exc.__cause__ else '')
            game.capture('end')
            result = {'case': name, 'rom_sha256': digest(rom),
                'source_sha256': protected[str(default_rom())], 'emulator': version(), 'bios': BIOS,
                'fixture_state_sha256': digest(fixture.state),
                'fixture_battery_sha256': digest(fixture.battery),
                'fixture_provenance': str(case_provenance.relative_to(ROOT)),
                'fixture_provenance_sha256': digest(case_provenance.read_bytes()),
                'inputs': game.inputs, 'images': game.images, 'route_error': error,
                **details, **audit.report()}
            result['passed'] = not error and not audit.unclassified and not audit.unreadable and not audit.layout_violations
            result['tools_sha256'] = {name: digest((ROOT/'tools'/name).read_bytes()) for name in
                ('audit_dungeon_screens.py', 'screen_text_audit.py', 'audit_menu_layouts.py', 'emulator.py')}
            save_json(folder/'report.json', result)
            results.append(result)
            print(name, 'route error:', error, 'unclassified glyphs:',
                  sorted({hex(x['code']) for x in audit.unclassified}),
                  'queues:', len(audit.queues), 'reads:', len(audit.observer.reads),
                  'layout violations:', len(audit.layout_violations), flush=True)
    require(all(digest(Path(p).read_bytes()) == sha for p, sha in protected.items()),
            'Protected input changed')
    save_json(output/'report.json', {'rom_sha256': digest(rom), 'cases': results,
        'original_files_unchanged': True, 'scope': 'Unfiltered shared-reader/glyph observations '
        'on bounded dungeon scenarios. All ordinary buttons except explicitly recorded vacant-slot '
        'overrides in the full-inventory case. Screenshots also require visual review; these hooks '
        'cannot establish coverage of graphics, other renderers or unvisited scenarios.'})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', action='append', choices=list(CASES))
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--allow-findings', action='store_true', help='Retain a failing historical control without a nonzero exit')
    args = parser.parse_args()
    results = run(args.case or list(CASES), args.source.resolve(), args.output.resolve())
    require(args.allow_findings or all(r['passed'] for r in results), 'Screen audit has unresolved findings')
