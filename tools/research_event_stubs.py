"""Controlled native follow-on handlers for the two referenced event stubs.

The host drives the original opcode dispatch and skips WAIT; this is not native
map progression. All flag, choice, dialogue and actor handlers are original.
"""
import json
from pathlib import Path
import struct

import mgba.log

from tools.bakery_playtest import service_ready
from tools.emulator import Debugger, Session, ffi
from tools.dialogue_checks import TextChecks
from tools.event_text import table_entries
from tools.opening_text import banks
from tools.rom import ROOT, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit, display_text
from tools.text_codec import tokenize

OUT = ROOT/'build/localization-closure/event-stubs'


def run(source=ROOT/'build/english', output=None, acceptance=False):
    mgba.log.silence()
    original = load_base()
    out = output or (source/'event-repairs-validation' if acceptance else OUT)
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Event stub ROM differs')
    selected = {r['id']:r for r in build['dialogue']['entries']}
    repairs = {'event-bank-3.3ec2', 'event-bank-4.0d25'}
    if acceptance:
        require(all(ident in selected and selected[ident].get('editorial_reconstruction')
                    for ident in repairs), 'Approved event repairs are not inserted')
    fixture = service_ready(rom, out)
    table = struct.unpack_from('<I', original, 0x4EF98)[0]-0x08000000
    require(table == 0x14CE30, 'Original event dispatch table differs')
    lengths = original[0x14CEBC:0x14CEE0]
    cases = []
    configurations = ([(4,5,1,0x516,f,'A') for f in (0,1)] +
                      [(3,11,s,root,None,key) for s,root in ((1,0x720),(2,0x739))
                       for key in (('A','B','RIGHT+A') if acceptance else ('A','B'))])
    for bank, node, selector, root, flag, key in configurations:
        label = f'bank-{bank}-map-{node}-npc-{selector}-flag-{flag}-{key}'
        print(label, flush=True)
        with Session(rom, out/label) as g:
            g.restore(fixture)
            m = g.core.memory
            initial, steps, reads, controls, done, choices = [], [], [], [], [], []
            entries = {(r['group'],r['index']):r for r in table_entries(banks()[bank])}
            initial_items = bytes(m[0x0200DF28:0x0200E888])
            state = {'phase':'initial', 'text':None}
            checks = TextChecks(g, {r['rom_offset']+0x08000000:r for r in selected.values()})
            audit = ScreenTextAudit(g)
            repair_draws, pixel_checks = [], []

            def register(index, value):
                controls.append(dict(register=index, before=g.core.cpu.gprs[index], after=value))
                g.core.cpu.gprs[index] = value

            def jump(value):
                controls.append(dict(pc=value))
                require(g.core._core.writeRegister(g.core._core, b'pc', ffi.new('uint32_t*', value)), 'PC redirect failed')

            def write(address, value, size=1):
                before = bytes(m[address:address+size])
                raw = value.to_bytes(size,'little')
                controls.append(dict(address=address, before_hex=before.hex(), after_hex=raw.hex()))
                for i, byte in enumerate(raw):
                    m.u8[address+i] = byte

            def callback(event):
                address, r = event['address'], event['registers']
                if acceptance and state['phase'] == 'dispatch':
                    audit.callback(event)
                    checks.callback(event)
                    if address == 0x08001BC4 and checks.active and checks.active['id'] in repairs:
                        w = r[0]
                        draw_key = (w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                        if not repair_draws or repair_draws[-1]['key'] != draw_key:
                            repair_draws.append(dict(key=draw_key,code=r[1],x=m.u8[w+2],y=m.u8[w+3],
                                origin=[m.u8[w],m.u8[w+1]],foreground=m.u8[0x020000C2],bank=m.u16[m.u32[w+12]]>>12))
                if address == 0x0801DFAC:
                    if state['phase'] == 'initial':
                        initial.append(event | {'guard':bytes(m[r[13]:r[13]+32]).hex()})
                        state['phase'] = 'load'
                        register(0, bank);register(14, 0x0804B33D);jump(0x0804D6F8)
                    elif state['phase'] == 'dispatch':
                        require(r[4:12] == initial[0]['registers'][4:12] and r[13] == initial[0]['registers'][13]
                                and bytes(m[r[13]:r[13]+32]).hex() == initial[0]['guard'], 'Handler ABI/guard differs')
                        pointer = m.u32[0x02010138]
                        opcode = m.u8[pointer]
                        if opcode == 20:
                            steps.append(dict(offset=pointer-0x020129AC, opcode=20, host_skipped_wait=True))
                            write(0x02010138,pointer+1,4);pointer += 1;opcode = m.u8[pointer]
                        if opcode == 21:
                            done.append(dict(offset=pointer-0x020129AC, opcode=21))
                            state['phase'] = 'done'
                            jump(initial[0]['registers'][14] & ~1)
                            return
                        require(opcode in (3,6,8,11,16), 'Unexpected stub follow-on opcode')
                        raw = bytes(m[pointer:pointer+1+lengths[opcode]])
                        step = dict(offset=pointer-0x020129AC, opcode=opcode, hex=raw.hex())
                        if opcode == 8:
                            row = entries[(raw[2],raw[3])]
                            state['text'] = row['id'];step['text_id'] = row['id']
                        steps.append(step)
                        handler = struct.unpack_from('<I', original, table+(opcode-1)*4)[0]
                        write(0x02010138,pointer+1,4)
                        register(14,0x0801DFAD);jump(handler & ~1)
                elif address == 0x0804B33C and state['phase'] == 'load':
                    require(m.u32[0x02010144] == 0x020129AC, 'Native NPC resource load differs')
                    write(0x0200FED8,node);write(0x02010A78+0x25,selector);write(0x02010A78+0x1F,5)
                    if flag is not None:
                        at = 0x020101AC+(0x82 >> 3)
                        write(at, (m.u8[at] & ~4) | (flag << 2))
                    state['flag_before'] = m.u8[0x020101BC]
                    register(0,0);register(14,0x0801DFAD);state['phase'] = 'dispatch'
                elif address == 0x0804B3A6 and state['phase'] == 'dispatch':
                    require(m.u32[0x02010138] == 0x020129AC+root, 'Native NPC selector differs')
                elif address == 0x080021B4 and state['phase'] == 'dispatch':
                    tokens, end = tokenize(bytes(m[r[1]:r[1]+4096]))
                    ident = checks.resources[r[1]]['id'] if r[1] in checks.resources else state['text']
                    if acceptance:
                        require(r[1] in checks.resources, 'Unowned event follow-on text source')
                        require(ident == 'rom.0006309c' or ident == state['text'], 'Native event selected wrong source')
                        if ident != 'rom.0006309c':
                            require(bytes(m[r[0]+4:r[0]+6]) == bytes((28,2)), 'Native event geometry changed')
                    reads.append(dict(id=ident, source=r[1], text=display_text(tokens),
                                      raw_hex=bytes(m[r[1]:r[1]+end]).hex(), frame=event['frame']))
                elif address == 0x08015E28 and state['phase'] == 'dispatch':
                    choices.append(r[0])

            with Debugger(g, callback, max_events=100000) as d:
                addresses = (0x0801DFAC,0x0804B33C,0x0804B3A6,0x080021B4,0x08015E28)
                for address in set(addresses + (checks.ADDRESSES+audit.ADDRESSES if acceptance else ())):
                    d.breakpoint(address)
                g.press('A',hold=1,wait=120)
                for page in range(60):
                    if done:
                        break
                    pic = g.capture(f'page-{page}')
                    if acceptance and repair_draws and not pixel_checks and checks.completed(state['text']):
                        pixels = 0
                        for draw in repair_draws:
                            glyph,_ = checks.glyph_record(draw['code'])
                            colour = m.u16[0x05000000+2*(16*draw['bank']+draw['foreground'])]
                            rgb = tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                            for y,line in enumerate(glyph['rows']):
                                for x,bit in enumerate(line):
                                    require((pic.getpixel((draw['origin'][0]+draw['x']+x,draw['origin'][1]+16*draw['y']+y))==rgb)==(bit=='#'),
                                            'Visible event repair pixels differ')
                                    pixels += 1
                        pixel_checks.append(dict(image=f'page-{page}.png',pixels=pixels))
                    if key == 'RIGHT+A' and not choices:
                        require(any(r['id']=='rom.0006309c' for r in checks.reads), 'No selected before choice menu opened')
                        g.press('RIGHT',hold=1,wait=20)
                        g.capture('no-selected')
                        g.press('A',hold=1,wait=120)
                    else:
                        g.press(key if not choices else 'A',hold=1,wait=120)
                require(done, 'Native stub follow-on did not finish')
            require(bytes(m[0x0200DF28:0x0200E888]) == initial_items and g.snapshot().battery == fixture.battery,
                    'Stub probe changed inventory/save')
            validation = {}
            if acceptance:
                expected = (['event-bank-4.0d25' if flag else 'event-bank-4.0c68'] if bank==4 else
                            ['event-bank-3.3ec2','rom.0006309c','event-bank-3.3ef9' if key=='A' else 'event-bank-3.3ec5'])
                require([r['id'] for r in checks.reads] == expected and checks.active is None,
                        'Event follow-on full English reads differ')
                require([s['text_id'] for s in steps if s['opcode']==8] == [i for i in expected if i.startswith('event-')],
                        'Original event dialogue branches differ')
                require(choices == ([] if bank==4 else [int(key=='A')]), 'Native event choice outcome differs')
                after = m.u8[0x020101BC]
                require(after == (state['flag_before'] | 4 if bank==4 else state['flag_before']), 'Native repeat flag outcome differs')
                result = audit.report()
                require(not result['unclassified_glyphs'] and not result['unreadable_streams'] and not result['layout_violations'],
                        'Event follow-on has unclassified text/layout findings')
                require(bool(pixel_checks) == (bank==3 or bool(flag)), 'Event repair visible capture missing')
                validation = dict(passed=True,checks=checks.reads,glyph_checks=checks.glyph_checks,audit=result,
                    visible_pixels=pixel_checks,flag_byte_before=state['flag_before'],flag_byte_after=after,
                    caller_guards_and_abi_preserved=True,inventory_and_battery_preserved=True)
            cases.append(dict(case=label, bank=bank, map=node, selector=selector, flag=flag, key=key,
                              steps=steps, terminal=done, reads=reads, choices=choices, inputs=g.inputs,
                              controls=controls, images={p.name:digest(p.read_bytes()) for p in g.output.glob('*.png')},**validation))
            (out/'partial.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
    report = dict(rom_sha256=digest(rom), source_rom_sha256=digest(original), cases=cases,
                  tool_sha256=digest(Path(__file__).read_bytes()),
                  complete=True, scope=__doc__, fixture_sha256=digest(fixture.state))
    if acceptance:
        report.update(passed=True,editorial_reconstructions={i:selected[i]['editorial_reconstruction'] for i in sorted(repairs)},
                      checks_sha256=digest(Path(__file__).with_name('dialogue_checks.py').read_bytes()),
                      audit_sha256=digest(Path(__file__).with_name('screen_text_audit.py').read_bytes()))
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Native stub follow-ons:',len(cases),flush=True)
    return report


if __name__ == '__main__':
    run()
