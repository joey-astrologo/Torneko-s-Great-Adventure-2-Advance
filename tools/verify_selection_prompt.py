"""Native Which? selector: selection, cancellation and repeated Info restoration."""
import argparse
from tools.service_validation import load_candidate
import json
import struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Snapshot, Debugger
from tools.audit_menu_layouts import Observer
from tools.dialogue_checks import TextChecks
from tools.verify_items import ItemChecks
from tools.verify_gaibara import OUT


def window_snapshot(game, address):
    m = game.core.memory; descriptor = bytes(m[address:address + 24]); base = m.u32[address + 12]
    control = m.u16[0x0400000E]; map_base = 0x06000000 + ((control >> 8) & 31) * 0x800
    char_base = 0x06000000 + ((control >> 2) & 3) * 0x4000
    require(not control & 0x80 and map_base <= base < map_base + 0x800, 'Selector background format differs')
    words = [m.u16[base + y * 64 + x * 2] for y in range(descriptor[5] * 2) for x in range(descriptor[4])]
    tiles = sorted({w & 0x3FF for w in words})
    pixels = b''.join(bytes(m[char_base + i * 32:char_base + (i + 1) * 32]) for i in tiles)
    return {'descriptor_hex': descriptor.hex(), 'control': control, 'map_base': base, 'tiles': tiles,
            'tilemap_sha256': digest(b''.join(struct.pack('<H', w) for w in words)), 'pixels_sha256': digest(pixels)}


def context(rom):
    path = OUT / 'native/selection-entry'
    if path.with_suffix('.json').exists() and Snapshot.load(path).rom_sha256 == digest(rom): return Snapshot.load(path)
    with Session(rom, OUT / 'selection-context') as game:
        game.restore(Snapshot.load(OUT / 'native/entry')); events = []
        def callback(event):
            if event['registers'][14] == 0x0801D613 and not events:
                require(event['registers'][:3] == [1,1,1], 'Synthesis selector arguments differ')
                events.append(event); game.snapshot().save(path)
        with Debugger(game, callback, max_events=3000) as debug:
            debug.breakpoint(0x0801DD5C)
            for _ in range(30):
                if events: break
                game.press('A', wait=90)
        require(events, 'Native item selector not reached')
        (game.output / 'provenance.json').write_text(json.dumps({'rom_sha256': digest(rom), 'events': events, 'inputs': game.inputs,
            'inherited_fixture': 'native/entry; controlled inventory/entry provenance in context-no/provenance.json'}, indent=2) + '\n')
    return Snapshot.load(path)


def run(cumulative=False):
    global OUT
    mgba.log.silence(); OUT, rom, build = load_candidate('gaibara', cumulative)
    require(digest(rom) == build['output_sha256'], 'Selector ROM differs')
    fixture = context(rom); heading = build['selection_prompt']['entries'][0]; results = []
    for case in ('cancel', 'select-second', 'info-reopen'):
        print('Item selector:', case, flush=True)
        with Session(rom, OUT / ('selector-' + case)) as game:
            game.restore(fixture); m = game.core.memory
            initial = [int(v) & 0xFFFFFFFF for v in game.core.cpu.gprs]
            guard = bytes(m[initial[13]:initial[13] + 32]); inventory = bytes(m[0x0200DF28:0x0200DF28 + 20 * 120])
            check = TextChecks(game, {heading['offset'] + 0x08000000: heading})
            items = ItemChecks(game, build); observer = Observer(game); returned, images, restorations = [], [], []
            def callback(event):
                a, r = event['address'], event['registers']
                if a == 0x0801D612 and not returned:
                    require(r[4:12] == initial[4:12] and r[13] == initial[13]
                            and bytes(m[r[13]:r[13] + 32]) == guard, 'Selector return ABI/guard differs')
                    returned.append(event)
                check.callback(event); items.callback(event); observer.callback(event)
            def capture(name): game.capture(name); images.append(name + '.png')
            with Debugger(game, callback, max_events=180000) as debug:
                for address in set(check.ADDRESSES + items.ADDRESSES + observer.ADDRESSES + (0x0801D612,)):
                    debug.breakpoint(address)
                game.frames(120); capture('opened')
                native_heading = [r for r in observer.reads if r['raw_hex'] == heading['encoded_hex']]
                lists = [r for r in observer.reads if r['window_width'] == 168 and r['screen_x'] == 64]
                require(native_heading and lists, 'Native selector heading/list absent')
                windows = [native_heading[-1]['window'], lists[-1]['window']]
                before = [window_snapshot(game, p) for p in windows]
                if case == 'info-reopen':
                    for cycle in range(3):
                        game.press('SELECT', wait=120); capture(f'info-{cycle}')
                        game.press('B', wait=120); capture(f'reopened-{cycle}')
                        after = [window_snapshot(game, p) for p in windows]
                        require(after == before, 'Selector Info did not restore heading/list pixels')
                        restorations.append({'before': before, 'after': after})
                    game.press('B', wait=120)
                elif case == 'select-second':
                    game.press('DOWN', wait=30); capture('second-selected'); game.press('A', wait=120)
                else: game.press('B', wait=120)
                capture('finished')
            require(returned and returned[0]['registers'][0] == (1 if case == 'select-second' else 0), 'Selector result differs')
            require(check.completed(heading['id']) and check.active is None, 'Selector heading incomplete')
            require(bytes(m[0x0200DF28:0x0200DF28 + 20 * 120]) == inventory and game.snapshot().battery == fixture.battery,
                    'Selector changed inventory/battery')
            reads = [r for r in observer.reads if r['raw_hex'] == heading['encoded_hex']]
            require(all(r['screen_x'] == 8 and r['window_width'] == 40 and r['rows'] == 1 and r['initial_x'] == 0 for r in reads), 'Selector geometry differs')
            if case == 'info-reopen': require(len(reads) >= 4 and len(restorations) == 3 and items.description_indices, 'Selector Info/reopening evidence missing')
            results.append({'case': case, 'result': returned[0]['registers'][0], 'heading_reads': reads,
                            'item_formats': items.formats, 'item_reads': items.reads, 'restorations': restorations,
                            'glyph_checks': check.glyph_checks + items.glyph_checks, 'inputs': game.inputs,
                            'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    (OUT / 'selector.json').write_text(json.dumps({'passed': True, 'rom_sha256': digest(rom), 'cases': results,
        'scope': 'Ordinary selector calls from the controlled synthesis fixture. Which? fits the original40px heading. Selection and cancellation preserve inventory; three SELECT/Info cycles restore both heading and168px inventory tilemap/tile pixels exactly. The8px border gap is unchanged. Other caller modes and ordinary progression remain separate.'}, indent=2) + '\n')
    print('Item selector:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
