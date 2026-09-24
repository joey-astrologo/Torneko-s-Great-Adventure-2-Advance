"""Controlled native result/history panels: all raw names, pixels, format guards and ABI."""
import argparse
import json
import struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks
from tools.emulator import Session, Debugger, ffi
from tools.rom import ROOT, digest, require
from tools.service_fixtures import dungeon
from tools.verify_service_ui import materialize


def run(source=ROOT / 'build/results-prototype', output=None):
    source = Path(source)
    output = Path(output) if output else source / 'validation'
    mgba.log.silence()
    rom = (source / 'torneko-2-english.gba').read_bytes()
    build = json.loads((source / 'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Stale results ROM')
    # Prototype checkpoints have separate paths and provenance.
    from tools import verify_player_status_prototype as status
    previous = status.OUT
    try:
        status.OUT = output
        fixture = status.ready(rom, build)
    finally:
        status.OUT = previous
    resource = build['results']; fmt, = resource['formats']; cases = []
    for family in ('results', 'history'):
        entry, fmtcall, fmtend, drawend, ready, end, capacity, inset = (
            (0x0801CA84, 0x0801CB92, 0x0801CB96, 0x0801CBF4, 0x0801CEEE, 0x0801CF5A, 256, 12)
            if family == 'results' else
            (0x08056E04, 0x08056FFC, 0x08057000, 0x08057030, 0x08057164, 0x0805734A, 128, 0))
        configs = [(r, False) for r in resource['entries']] + [(r, True) for r in resource.get('causes', [])]
        for row, cause in configs:
            ident = row['reason'] if cause else row['id']; case = family + ('-cause-' if cause else '-') + str(ident)
            reason = ident if cause else 21
            fmt = resource['other_defeat'] if cause else resource['formats'][0]
            fmtcall, fmtend = ((0x0801CBDC, 0x0801CBE0) if family == 'results' else (0x08057022, 0x08057026)) if cause else ((0x0801CB92, 0x0801CB96) if family == 'results' else (0x08056FFC, 0x08057000))
            actor = resource['history_zero_actor'] if family == 'history' and ident == 0 and not cause else row
            payload = bytes.fromhex(fmt['encoded_hex']).replace(b'%s', bytes.fromhex(actor['encoded_hex'])[:-1])
            with Session(rom, output / case) as game:
                game.restore(fixture); m = game.core.memory
                initial, returns, panels, formats, overrides, draws = [], [], [], [], [], []
                check = TextChecks(game, {})
                pending = []
                def write(a, data):
                    overrides.append({'address': a, 'before': bytes(m[a:a+len(data)]).hex(), 'after': data.hex()})
                    for i, v in enumerate(data): m.u8[a+i] = v
                def callback(e):
                    a, r = e['address'], e['registers']
                    if a == 0x08008F4C and not initial:
                        initial.append(e | {'guard': bytes(m[r[13]:r[13]+32]).hex()})
                        if family == 'results':
                            write(0x020056B3, b'\0'); write(0x020037CC, struct.pack('<hh', reason, 1 if cause else ident))
                        else:
                            write(0x02011BDC, struct.pack('<I', 0))
                            write(0x02004EFC, struct.pack('<IIIIhhhBBBBBB', 10120, 8, 120, 3600, 3, 15, 6, 3, reason, 8, 0, 1 if cause else ident, 0))
                            game.core.cpu.gprs[0] = 0x02002C44
                        overrides.append({'event': e, 'pc_after': entry,
                                          'r0_after': 0x02002C44 if family == 'history' else r[0]})
                        require(game.core._core.writeRegister(game.core._core, b'pc', ffi.new('uint32_t*', entry)), 'Results redirect failed')
                    if not initial or returns: return
                    if a == fmtcall:
                        require(r[1:3] == [fmt['offset']+0x08000000, actor['offset']+0x08000000], 'Raw actor/format pointer differs')
                        require(r[0] == r[13] + (8 if family == 'results' else 4), 'Result output ownership differs')
                        require(len(payload) <= fmt['maximum_bytes'] <= capacity, 'Result output too large')
                        pending.append((r, bytes(m[r[0]+len(payload):r[0]+capacity+16])))
                    if a == fmtend:
                        before, guard = pending.pop()
                        require(r[4:12] == before[4:12] and r[13] == before[13], 'Result format ABI differs')
                        require(bytes(m[before[0]:before[0]+len(payload)]) == payload and
                                bytes(m[before[0]+len(payload):before[0]+capacity+16]) == guard, 'Result format bytes/tail/guard differ')
                        check.resources[before[0]] = {'id': case, 'encoded_hex': payload.hex(), 'layout': {'pages': [[case]]}}
                        formats.append({'source': before[1], 'actor': before[2], 'output': before[0], 'capacity': capacity,
                                        'encoded_hex': payload.hex(), 'tail_guard_abi_match': True})
                    if a == 0x08001BC4 and check.active:
                        window = r[0]; key = (r[0], r[1], r[13], r[14], m.u8[window+2], m.u8[window+3])
                        if not draws or draws[-1]['key'] != key:
                            draws.append({'key': key, 'code': r[1], 'x': m.u8[window+2], 'y': m.u8[window+3],
                                          'origin': [m.u8[window], m.u8[window+1]], 'width': m.u8[window+4]*8})
                    check.callback(e)
                    if a == drawend:
                        require(len(check.reads) == 1 and check.active is None, 'Result reader incomplete')
                        check.resources.clear()
                    if a == ready: panels.append(e)
                    if a == end:
                        before = initial[0]['registers']
                        require(r[4:12] == before[4:12] and r[13] == before[13] and r[0] == before[14] and
                                bytes(m[r[13]:r[13]+32]).hex() == initial[0]['guard'], 'Result caller guard/ABI differs')
                        returns.append(e)
                with Debugger(game, callback, max_events=30000) as debug:
                    for a in set(TextChecks.ADDRESSES + (0x08008F4C, fmtcall, fmtend, drawend, ready, end)):
                        debug.breakpoint(a)
                    game.press('A', hold=1, wait=0)
                    for _ in range(500):
                        game.frames(1)
                        if panels: break
                    require(panels and len(formats) == 1 and len(check.reads) == 1 and not pending and draws, 'Results panel incomplete: ' + case)
                    game.frames(3); picture = game.capture('panel')
                    require(draws[0]['x'] == inset and all(d['width'] == 224 and d['y'] == draws[0]['y'] for d in draws),
                            'Result actor line geometry changed')
                    pixels = 0
                    for draw in draws:
                        glyph, _ = check.glyph_record(draw['code'])
                        for y, bits in enumerate(glyph['rows']):
                            for x, bit in enumerate(bits):
                                px, py = draw['origin'][0] + draw['x'] + x, draw['origin'][1] + draw['y'] * 16 + y
                                require(0 <= px < 240 and 0 <= py < 160 and
                                        (picture.getpixel((px, py)) == (255, 255, 255)) == (bit == '#'),
                                        'Result panel pixels differ: ' + repr((case, px, py, bit, picture.getpixel((px,py)))))
                                pixels += 1
                    game.press('B', hold=1, wait=0)
                    for _ in range(120):
                        if returns: break
                        game.frames(1)
                    require(len(returns) == 1 and game.snapshot().battery == fixture.battery, 'Result close/save failed')
                cases.append({'case': case, 'family': family, 'actor_id': None if cause else ident, 'cause_id': ident if cause else None, 'english_actor': actor['english'],
                              'formats': formats, 'draws': draws, 'reads': check.reads, 'overrides': overrides,
                              'return': returns[0], 'inputs': game.inputs, 'visible_pixels_checked': pixels,
                              'images': {'panel.png': digest((game.output/'panel.png').read_bytes())}})
            print('Result actor:', case, flush=True)
    (output/'report.json').write_text(json.dumps({'passed': True, 'rom_sha256': digest(rom), 'cases': cases,
        'scope': 'Controlled native result/history entry and reason/record selection. All141 raw IDs in results, '
        '140 nonzero history IDs and its distinct fixed Torneko ID0 pass native formatting, original256/128-byte '
        'output guards, ABI,224px window geometry and complete final-screen glyph pixels. Battery unchanged. '
        'An optional27-cause extension also checks every cause in both panels with the same complete pixel, format and guard evidence. Other result/history text, natural defeat, record persistence and ordinary history access remain separate.'}, indent=2)+'\n')
    print('Results:', len(cases), 'cases passed', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'build/results-prototype')
    p.add_argument('--output', type=Path)
    a = p.parse_args(); run(a.source, a.output)
