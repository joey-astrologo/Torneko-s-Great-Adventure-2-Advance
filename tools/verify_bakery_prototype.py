"""Native bakery prototype checks with explicit controlled service invocation."""
import argparse, json, struct
from collections import Counter
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Snapshot, Debugger, ffi
from tools.build_bakery_prototype import build_rom, OUT
from tools.bakery_playtest import service_ready
from tools.town_playtest import position
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.verify_service_ui import materialize
from tools.audit_menu_layouts import Observer
from tools.numeric_checks import NumericChecks
from tools.holy_flame_playtest import items
from tools.name_entry import HERO

class BakeryChecks(TextChecks):
    ADDRESSES = TextChecks.ADDRESSES + (0x08000FB8, 0x0801E41E, 0x08015CE8, 0x08015E28)
    def __init__(self, game, build):
        self.rows = {r['offset'] + 0x08000000: r for r in build['bakery']}
        super().__init__(game, {p: r for p, r in self.rows.items() if r['index'] != 103})
        self.pending, self.choice_active = None, False
        self.formats, self.choices = [], []
    def callback(self, event):
        a, r, m = event['address'], event['registers'], self.game.core.memory
        if a == 0x08015CE8:
            self.choice_active = True
        elif a == 0x08015E28 and self.choice_active:
            self.choices.append(r[0]); self.choice_active = False
        if a == 0x08000FB8 and r[1] in self.rows:
            row = self.rows[r[1]]
            require(row['index'] == 103 and r[14] == 0x0801E41F and r[0] == r[13] + 4,
                    'Unexpected bakery format owner/buffer')
            require(r[3] in (100, 300, 400), 'Unbounded bakery price')
            expected = materialize(bytes.fromhex(row['encoded_hex']), r[2:4], m)
            require(len(expected) <= row['layout']['maximum_formatted_bytes'] <= 256, 'Bakery format capacity exceeded')
            self.pending = (r[0], expected, bytes(m[r[0]+256:r[0]+272]), bytes(m[r[13]:r[13]+4]), r[4:12], r[13], row)
        if a == 0x0801E41E:
            require(self.pending is not None, 'Missing bakery format entry')
            dest, expected, guard, prefix, regs, sp, row = self.pending
            require(bytes(m[dest:dest+len(expected)]) == expected, 'Bakery formatted bytes differ')
            require(bytes(m[dest+256:dest+272]) == guard and bytes(m[sp:sp+4]) == prefix,
                    'Bakery formatter crossed buffer bounds')
            require(r[4:12] == regs and r[13] == sp, 'Bakery formatter changed ABI registers')
            self.resources[dest] = row | {'encoded_hex': expected.hex()}
            self.formats.append({'id': row['id'], 'expected_hex': expected.hex(), 'bytes': len(expected),
                                 'capacity': 256, 'guards_preserved': True, 'abi_preserved': True})
            self.pending = None
        if a in TextChecks.ADDRESSES:
            super().callback(event)

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT = ROOT / 'build/english/bakery-validation'
        rom = (ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Cumulative bakery ROM differs')
        build['bakery'] = build['dialogue']['town_resource']['bakery_entries']
    else:
        rom, build = build_rom()
    fixture = service_ready(rom, OUT)
    results = []
    cases = [(f'buy-{i}', i, None, None, False) for i in range(3)]
    cases += [('decline', 2, None, None, False), ('cancel', 0, None, None, False),
              ('leave', 3, None, None, False), ('insufficient', 2, None, 399, False),
              ('exact-gold', 2, None, 400, False), ('full', 0, None, None, True),
              ('buy-again', 0, None, None, False)]
    cases += [(f'max-name-{label}', 0, name, None, True) for label, name in player_layout_cases()]
    for label, selected, player, gold, full in cases:
        print('Bakery', label, flush=True)
        with Session(rom, OUT / label) as game:
            game.restore(fixture); m = game.core.memory
            overrides = []
            if player:
                for i, value in enumerate(player.ljust(16, b'\0')): m.u8[HERO+i] = value
                overrides.append({'player_hex': player.hex()})
            wallet = m.u32[0x02001624]+0x60
            if gold is not None:
                overrides.append({'wallet_before': m.u32[wallet], 'wallet_after': gold}); m.u32[wallet] = gold
            if full:
                sample = bytes(m[0x0200DF28:0x0200DF28+120]); require(sample[3]&0x80, 'No native item for full-inventory probe')
                for slot in range(20):
                    for i, value in enumerate(sample): m.u8[0x0200DF28+slot*120+i] = value
                overrides.append({'full_inventory': '20 copies of the naturally carried first item'})
            before, money = [i for _, i, _ in items(game)], m.u32[wallet]
            check, observer, numbers = BakeryChecks(game, build), Observer(game), NumericChecks(game)
            entries, returned, given = [], [], []
            def callback(event):
                a, r = event['address'], event['registers']
                if a == 0x0801DFAC:
                    require(not entries and r[0] == 0x020141AC, 'Unexpected bank entry for controlled bakery call')
                    entries.append({'frame': event['frame'], 'original_registers': r, 'controlled_pc': 0x0801E394, 'controlled_r1': 0})
                    game.core.cpu.gprs[1] = 0
                    game.core._core.writeRegister(game.core._core, b'pc', ffi.new('uint32_t*', 0x0801E394))
                    return
                if a == 0x0801E48E:
                    require(r[4:12] == entries[0]['original_registers'][4:12]
                            and r[13] == entries[0]['original_registers'][13]
                            and r[0] == entries[0]['original_registers'][14], 'Bakery service return ABI differs')
                    returned.append(event['frame'])
                if a == 0x08041E9C and r[14] == 0x0801E45B: given.append(r[0])
                check.callback(event); observer.callback(event); numbers.callback(event)
            def until(predicate, context):
                for _ in range(16):
                    if predicate(): return
                    game.press('A', wait=120)
                require(predicate(), 'Bakery did not reach '+context)
            def menu():
                until(lambda: not check.active and check.reads and check.reads[-1]['id'] == 'bakery.101', 'menu')
            with Debugger(game, callback, max_events=120000) as debug:
                for a in set(check.ADDRESSES + observer.ADDRESSES + (0x0801DFAC, 0x0801E48E, 0x08041E9C)):
                    debug.breakpoint(a)
                game.press('A', wait=120); menu(); game.capture('menu')
                for _ in range(selected): game.press('DOWN', wait=30)
                game.press('B' if label == 'cancel' else 'A', wait=120)
                if full:
                    require(check.completed('bakery.107') or check.active and check.active['id']=='bakery.107', 'Full inventory warning absent')
                    game.capture('full-first-page'); until(lambda: bool(returned), 'full refusal return')
                elif label in ('cancel', 'leave'):
                    until(lambda: bool(returned), 'leave return')
                else:
                    until(lambda: check.choice_active, 'purchase confirmation'); game.capture('confirmation')
                    game.press('B' if label == 'decline' else 'A', wait=120)
                    if label in ('decline', 'insufficient'):
                        if label == 'insufficient':
                            game.capture('insufficient-first-page')
                        menu()
                        if label == 'insufficient': require(check.completed('bakery.106'), 'Insufficient-gold text absent')
                        game.capture('returned-menu'); game.press('B', wait=120)
                    else:
                        until(lambda: check.choice_active, 'buy another'); game.capture('purchased')
                        if label == 'buy-again':
                            game.press('A', wait=120); menu(); game.press('DOWN', wait=30); game.press('A', wait=120)
                            until(lambda: check.choice_active, 'second purchase confirmation'); game.press('A', wait=120)
                            until(lambda: check.choice_active, 'second buy another'); game.capture('purchased-again')
                        game.press('B', wait=120)
                    until(lambda: bool(returned), 'service return')
                game.capture('closed')
            expected = ([203,206] if label == 'buy-again' else [([203,206,207][selected])] if label.startswith('buy-') or label=='exact-gold' else [])
            after = [i for _, i, _ in items(game)]
            prices = {203:100, 206:300, 207:400}
            require(given == expected and Counter(after) == Counter(before)+Counter(expected), 'Native bakery delivered wrong items')
            require(m.u32[wallet] == money-sum(prices[i] for i in expected), 'Bakery gold deduction differs')
            require(not check.active and not check.pending and returned, 'Bakery text did not finish')
            require(game.snapshot().battery == fixture.battery, 'Bakery test unexpectedly saved')
            results.append({'case': label, 'controlled_overrides': overrides, 'service_entries': entries,
                            'items_before': before, 'items_after': after, 'native_given_ids': given,
                            'gold_before': money, 'gold_after': m.u32[wallet], 'reads': check.reads,
                            'formats': check.formats, 'glyph_checks': check.glyph_checks, 'choices': check.choices,
                            'native': observer.reads, 'numeric_checks': numbers.samples, 'inputs': game.inputs})
    require({r['id'] for case in results for r in case['reads']} == {r['id'] for r in build['bakery']}, 'Bakery source coverage incomplete')
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': ('Cumulative build. ' if cumulative else 'Isolated candidate. ') + '13 controlled bakery service calls using the native purchase code, original window geometry, three prices/items, cancellation, decline, buy-again, insufficient/exact gold, full capacity and three player-name extremes. PC/r1 redirect from a native bank call is explicit. No natural bakery unlock or persisted bakery purchase is claimed.'}
    (OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Bakery prototype:',len(results),'cases passed')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
