"""Observe the native bakery with an explicitly redirected service invocation.

The supplied quest-earned save does not establish the bakery unlock. Only the
bank service call is redirected in a disposable emulator, preserving its town
resource argument and native caller/return. No source ROM or save is changed.
"""
import json
import mgba.log
from tools.emulator import Session, Snapshot, Debugger, ffi
from tools.rom import ROOT, load_base, digest, require
from tools.audit_menu_layouts import Observer
from tools.verify_service_ui import cstring
from tools.holy_flame_playtest import items

OUT = ROOT / 'build/services/bakery-native'
from tools.bakery_playtest import service_ready

def run():
    mgba.log.silence()
    rom = load_base()
    fixture = service_ready(rom, OUT)
    with Session(rom, OUT) as game:
        game.restore(fixture)
        observer = Observer(game)
        entries, formats, returns = [], [], []
        memory = game.core.memory
        before = items(game)
        def callback(event):
            observer.callback(event)
            registers, address = event['registers'], event['address']
            if address == 0x0801DFAC:
                require(not entries, 'Repeated service entry')
                require(registers[0] == 0x020141AC, 'Town resource differs')
                entries.append({'original_registers': registers, 'frame': event['frame'],
                                'controlled_pc': 0x0801E394, 'controlled_r1': 0})
                game.core.cpu.gprs[1] = 0
                game.core._core.writeRegister(game.core._core, b'pc', ffi.new('uint32_t*', 0x0801E394))
            elif address == 0x08000FB8 and registers[14] == 0x0801E41F:
                game.snapshot().save(OUT / f'format-{len(formats)}')
                formats.append({'registers': registers, 'frame': event['frame'],
                                'template_hex': cstring(memory, registers[1], 256).hex(),
                                'item_hex': cstring(memory, registers[2], 128).hex()})
            elif address == 0x0801E48E:
                returns.append({'frame': event['frame'], 'registers': registers})
        with Debugger(game, callback, max_events=150000) as debug:
            for address in observer.ADDRESSES + (0x0801DFAC, 0x08000FB8, 0x0801E48E):
                debug.breakpoint(address)
            for index, key in enumerate(('A', 'A', 'A', 'A', 'B', 'B', 'A', 'A')):
                game.press(key, wait=120)
                game.capture(f'page-{index}')
                game.snapshot().save(OUT / f'page-{index}')
                print(index, key, [row['text'] for row in observer.reads[-2:]], flush=True)
                if returns:
                    break
        require(entries, 'Native service entry absent')
        require(game.snapshot().battery == fixture.battery, 'Research unexpectedly saved')
        report = {'rom_sha256': digest(rom), 'fixture': str((OUT / 'native/ready').relative_to(ROOT)),
                  'entries': entries, 'formats': formats, 'returns': returns,
                  'reads': observer.reads, 'creates': observer.creates, 'inputs': game.inputs,
                  'items_before': before, 'items_after': items(game),
                  'scope': 'Controlled PC/r1 redirection of an ordinary bank invocation into the native bakery. This does not prove the bakery unlock or ordinary bakery access.'}
        (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print('Bakery formats', len(formats), 'returns', len(returns))

if __name__ == '__main__':
    run()
