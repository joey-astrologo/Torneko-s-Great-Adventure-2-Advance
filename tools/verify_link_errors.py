"""Follow link failures from protocol producers through cleanup and town return.

Entry uses native saves from verify_link_entry and ordinary green-book inputs.
Faults, where requested, are recorded at their producer; no error index, text
pointer, branch PC, cleanup, or save result is substituted.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path

import mgba.log

from tools.emulator import Session, Debugger, ffi
from tools.link_emulator import LinkPair, compile_bridge
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit
from tools.town_playtest import position
from tools.verify_link_entry import carried_records
from tools.verify_link_exchange import audit_ok, stored_items

PHASE = 0x02012848
ERROR_TEXT = ['No response from the other player.', 'Hardware error.',
              'Connect only two systems.', 'No other player found.',
              'Data was not received correctly.']
POINTS = {0x08057C54, 0x08057DAC, 0x08057C1C, 0x08057C3C, 0x08057C40,
          0x08057D46, 0x08058110, 0x080581A4, 0x0805821E, 0x08058598,
          0x08058098, 0x080585C2, 0x08015348, 0x080587C8, 0x080588A4}
EXPECTED_ERRORS = {
    'no-cable': [[3]], 'hardware': [[1]], 'third-system': [[2]],
    'count-mismatch': [[4], [0]], 'asymmetric': [[3], [3]],
    'partner-declines': [[3], []],
    **{f'disconnect-{n}': [[0], [0]] for n in range(1,5)},
    **{f'cancel-{s}': [[]] for s in ('picker','item-confirm','connect-confirm')},
    'hardware-after-save': [[1], [1]], 'third-system-after-save': [[2], [2]],
}


def inventory(game):
    m = game.core.memory
    return dict(stored=stored_items(game), carried=carried_records(game),
                capacity=m.u16[0x02002C2A], gold=m.u32[m.u32[0x02001624]+0x60])


def run_case(rom, output, name, library, fixture_root, original_baseline=False, expect_recovery=False):
    linked = name != 'no-cable' and not name.startswith('cancel-') and name not in ('hardware', 'third-system')
    records, games, saved = [], [], []
    with ExitStack() as stack:
        for peer in range(2 if linked else 1):
            battery = (fixture_root/f'peer-{peer}/traded.sav').read_bytes()
            g = stack.enter_context(Session(rom, output/f'peer-{peer}', initial_save=battery))
            games.append(g)
            audit = ScreenTextAudit(g)
            rec = dict(peer=peer, events=[], entries=[], returns=[], errors=[], phases=[],
                       controls=[], battery_before=digest(battery), images=[])
            records.append(rec)

            def write_register(e, register, value, reason, g=g, rec=rec):
                rec['controls'].append(dict(event=e, register=register, value=value, reason=reason))
                require(g.core._core.writeRegister(g.core._core, register.encode(),
                        ffi.new('uint32_t*', value)), 'Fault setup failed')

            def callback(e, g=g, rec=rec, audit=audit, peer=peer, write_register=write_register):
                a, r, m = e['address'], e['registers'], g.core.memory
                if a == 0x08057C54:
                    require(r[14] == 0x0804A18F, 'Unexpected green-book caller')
                    rec['entries'].append(e | dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
                elif a == 0x08057DAC:
                    old = rec['entries'][-1]
                    q = old['registers']
                    require(r[4:12] == q[4:12] and r[13] == q[13] and r[0] == q[14]
                            and bytes(m[r[13]:r[13]+32]).hex() == old['guard'], 'Owner ABI/guard differs')
                    rec['returns'].append(e)
                elif a == 0x08057C1C:
                    rec['errors'].append(e)
                elif a == 0x0805821E:
                    state = dict(phase=m.u32[PHASE], saved=m.u32[r[13]+0xD4],
                                 frame=e['frame'], remaining=r[8], received=r[9])
                    if not rec['phases'] or (state['phase'],state['saved']) != (
                            rec['phases'][-1]['phase'],rec['phases'][-1]['saved']):
                        rec['phases'].append(state)
                elif a in POINTS and a not in (0x080587C8, 0x080588A4, 0x080581A4):
                    rec['events'].append(e)
                if name in ('hardware', 'hardware-after-save') and a == 0x080587C8 and not rec['controls'] and (
                        name == 'hardware' or m.u32[PHASE] == 4):
                    at = 0x02012859
                    rec['controls'].append(dict(event=e, address=at, before=m.u8[at], after=1,
                        reason='Set native serial-driver fault latch before status construction.'))
                    m.u8[at] = 1
                if name in ('third-system','third-system-after-save') and a == 0x080588A4 and not rec['controls'] and (
                        name == 'third-system' or m.u32[PHASE] == 4):
                    write_register(e, 'r5', (r[5] & ~0x30) | 0x20,
                        'Supply SIOCNT participant ID 2 to its native status decoder; two-core harness cannot attach a third system.')
                if name == 'count-mismatch' and peer == 0 and a == 0x08058598 and not rec['controls']:
                    write_register(e, 'r9', r[9]+1, 'Corrupt received-record count before native count comparison.')
                audit.callback(e)

            d = stack.enter_context(Debugger(g, callback, max_events=250000))
            for at in set(audit.ADDRESSES) | POINTS:
                d.breakpoint(at)
            rec['audit_object'] = audit
            g.frames(600); g.press('START', wait=180); g.press('A', wait=300)
            require(position(g) == (320,224) and len(stored_items(g)) == 1, 'Link save fixture differs')
            rec['before'] = inventory(g)
            g.press('UP', hold=3, wait=60); g.press('A', wait=120)
            g.press('DOWN', wait=30); g.press('DOWN', wait=30); g.press('A', wait=180)
            require(len(rec['entries']) == 1, 'Ordinary green-book entry absent')

        pair = stack.enter_context(LinkPair(games, library)) if linked else None

        def press(key, wait=120, peers=None):
            if pair and pair.native:
                if peers is None:
                    pair.press(key, wait=wait)
                else:
                    before = [g.core.frame_counter for g in games]
                    for p in peers: games[p].core.set_keys(getattr(games[p].core, 'KEY_'+key))
                    try: pair.frames(2)
                    finally:
                        for p in peers: games[p].core.clear_keys(getattr(games[p].core, 'KEY_'+key))
                    pair.frames(wait)
                    pair.inputs.append(dict(key=key, peers=peers, hold=2, released=wait, before=before,
                                            after=[g.core.frame_counter for g in games]))
            else:
                for p in (range(len(games)) if peers is None else peers): games[p].press(key, wait=wait)

        def frames(count):
            if pair and pair.native: pair.frames(count)
            else:
                for g in games: g.frames(count)

        def capture(label):
            for g, rec in zip(games, records):
                g.capture(label)
                rec['images'].append(dict(file=label+'.png',sha256=digest((g.output/(label+'.png')).read_bytes())))

        # Instruction -> picker -> actions -> item confirmation -> cable confirmation.
        for label in ('picker','actions','item-confirm','connect-confirm'):
            press('A')
            if name == 'cancel-'+label:
                press('B'); break
        else:
            if name == 'asymmetric':
                press('A', peers=[0]); frames(120); press('A', peers=[1], wait=1)
            elif name == 'partner-declines':
                press('B', peers=[1]); press('A', peers=[0], wait=1)
            else: press('A', wait=1)
        if name.startswith('disconnect-'):
            desired = int(name.rsplit('-',1)[1])
            for _ in range(700):
                if any(g.core.memory.u32[PHASE] == desired and rec['phases'] for g,rec in zip(games,records)):
                    break
                frames(1)
            else: raise ValueError('Disconnect phase not reached')
            wire = pair.report()
            for g, rec in zip(games,records):
                rec['disconnect'] = dict(frame=g.core.frame_counter, phase=g.core.memory.u32[PHASE])
            pair.close()
        else: wire = None
        frames(650)
        capture('outcome')
        # Dismiss an error/success and cancel any remaining picker/repeat panels.
        for _ in range(5):
            if all(rec['returns'] for rec in records): break
            press('B', wait=180)
        capture('returned')
        if pair and pair.native: wire = pair.report()
        require([[e['registers'][0] for e in rec['errors']] for rec in records] == EXPECTED_ERRORS[name],
                'Expected protocol failure/cancellation was not exercised')
        for g, rec in zip(games,records):
            rec['after'] = inventory(g)
            rec['inputs'] = g.inputs
            observer = rec.pop('audit_object')
            rec['audit'] = observer.report() if original_baseline else audit_ok(observer)
            require(len(rec['returns']) == 1 and g.core.memory.u8[0x0200FED8] == 21,
                    'Link owner did not return to town exactly once')
            require(all(e['registers'][0] == 0xFFFFFFFF for e in rec['events']
                        if e['address'] == 0x08057D46), 'Failed protocol returned success')
            for at in (0x08057C3C,0x08057C40):
                require(sum(e['address'] == at for e in rec['events']) == len(rec['errors']),
                        'Full post-error cleanup was not executed')
            rec['inventory_preserved'] = rec['before'] == rec['after']
            known_loss = name.endswith('-after-save') and not expect_recovery
            require(rec['inventory_preserved'] != known_loss, 'Unexpected inventory recovery result')
            if known_loss:
                require(rec['after'] == rec['before'] | {'stored': []},
                        'Fault changed more than the known lost offered item')
            if name == 'disconnect-4' or (name == 'count-mismatch' and rec['peer'] == 1):
                require([e['registers'][14] for e in rec['events'] if e['address'] == 0x08015348]
                        == [0x080580E3,0x080585ED], 'Intermediate save/rollback save absent')
            for e in ([] if original_baseline else rec['errors']):
                text = '\n'.join(r.get('text','') for r in rec['audit']['reads'])
                require(ERROR_TEXT[e['registers'][0]] in text and 'Check the link cable.' in text,
                        'Selected error not observed in full text stream')
            saved.append(g.snapshot().battery)
            rec['battery_after'] = digest(saved[-1])
            (g.output/'after.sav').write_bytes(saved[-1])
            (g.output/'case.json').write_text(json.dumps(rec,indent=2)+'\n')
    cold=[]
    for peer, battery in enumerate(saved):
        with Session(rom,output/f'cold-{peer}',initial_save=battery) as g:
            g.frames(600); g.press('START',wait=180); g.press('A',wait=300)
            require(inventory(g) == records[peer]['after'], 'Cold load differs from returned inventory')
            cold.append(dict(peer=peer, inventory=inventory(g), inputs=g.inputs))
    preserved = all(r['inventory_preserved'] for r in records)
    print(name, ': expected routes verified; inventory preserved =', preserved, flush=True)
    return dict(name=name, peers=records, wire=wire, cold_loads=cold,
                inventory_preserved=preserved, text_checked=not original_baseline)


def run(source, output, names, fixture_root, original_baseline=False, expect_recovery=False):
    mgba.log.silence()
    rom=load_base() if original_baseline else (source/'torneko-2-english.gba').read_bytes()
    if not original_baseline:
        require(digest(rom)==json.loads((source/'build.json').read_text())['output_sha256'], 'Stale ROM')
    base, save = digest(load_base()), digest(default_rom().with_suffix('.sav').read_bytes())
    library, bridge=compile_bridge(output/'native-bridge')
    cases=[]
    for name in names:
        case=run_case(rom,output/name,name,library,fixture_root,original_baseline,expect_recovery)
        cases.append(case)
        (output/'partial.json').write_text(json.dumps(cases,indent=2)+'\n')
    require(base==digest(load_base()) and save==digest(default_rom().with_suffix('.sav').read_bytes()),
            'Source files changed')
    report=dict(rom_sha256=digest(rom), source_rom_sha256=base, source_save_sha256=save,
                tool_sha256=digest(Path(__file__).read_bytes()),bridge=bridge,cases=cases,
                fixture_saves={str(p):digest(p.read_bytes()) for p in
                               sorted(fixture_root.glob('peer-*/traded.sav'))},
                original_baseline=original_baseline, expected_routes_verified=True,
                text_checks_passed=not original_baseline,
                inventory_preserved=all(c['inventory_preserved'] for c in cases),
                findings=[c['name'] for c in cases if not c['inventory_preserved']],
                scope=__doc__ + ' Two native saved item records (bread/staff). Hardware latch, '
                'third participant SIOCNT sample and received count are explicit injected faults; '
                'disconnects detach the native link driver. No physical cable or third core tested.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'build/english')
    p.add_argument('--output',type=Path,default=ROOT/'build/link-errors/native')
    p.add_argument('--fixture-root',type=Path,default=ROOT/'build/link-entry')
    p.add_argument('--original-baseline',action='store_true')
    p.add_argument('--expect-recovery',action='store_true')
    p.add_argument('--cases',nargs='+',default=['no-cable','hardware','third-system','count-mismatch',
                    'asymmetric','partner-declines','disconnect-1','disconnect-2','disconnect-3','disconnect-4',
                    'cancel-picker','cancel-item-confirm','cancel-connect-confirm',
                    'hardware-after-save','third-system-after-save'])
    args=p.parse_args()
    run(args.source,args.output,args.cases,args.fixture_root,args.original_baseline,args.expect_recovery)
