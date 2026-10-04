"""Controlled ending-owner entry, retaining native staging, saves and credits.

The bank's function call is redirected once in a disposable native session.
This does not establish ordinary ending access. Later calls, state selection,
movement, fades, text and saves run without instruction or RAM overrides.
"""
import argparse
import html
import json
from pathlib import Path

import mgba.log

from tools.bakery_playtest import service_ready
from tools.emulator import Debugger, Session, ffi
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit

STAGES = {0x08054DA4: 'ending', 0x080557C8: 'scene-0',
          0x08055934: 'scene-1', 0x080559CC: 'scene-2',
          0x08055A50: 'scene-3', 0x08055AEC: 'scene-4',
          0x080554FC: 'credits', 0x0805532C: 'finale',
          0x08054EEC: 'return'}


def run(source, output, frames):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Ending audit ROM differs')
    original_hash = digest(load_base())
    save = default_rom().with_suffix('.sav')
    save_hash = digest(save.read_bytes())
    fixture = service_ready(rom, output)
    stages, overrides, images, returns = [], [], [], []
    with Session(rom, output, initial_save=fixture.battery) as game:
        game.restore(fixture)
        audit = ScreenTextAudit(game)
        def callback(event):
            address = event['address']
            if address == 0x0801DFAC and not overrides:
                overrides.append(dict(event=event, pc_after=0x08054DA4,
                    stack_guard=bytes(game.core.memory[event['registers'][13]:event['registers'][13]+32]).hex(),
                    reason='Controlled bank-call entry into the complete ending owner'))
                require(game.core._core.writeRegister(game.core._core, b'pc',
                    ffi.new('uint32_t*', 0x08054DA4)), 'Ending entry failed')
                stages.append(dict(stage='ending', **event))
                audit.phase = 'ending'
                return
            if not overrides:
                return
            if address in STAGES:
                stages.append(dict(stage=STAGES[address], **event))
                audit.phase = STAGES[address]
                print(STAGES[address], event['frame'], flush=True)
                if address == 0x08054EEC:
                    old = overrides[0]['event']['registers']
                    current = event['registers']
                    require(current[4:12] == old[4:12] and current[13] == old[13]
                            and current[1] == old[14]
                            and bytes(game.core.memory[current[13]:current[13]+32]).hex()
                            == overrides[0]['stack_guard'], 'Ending owner ABI or stack guard differs')
                    returns.append(event)
            if address in audit.ADDRESSES:
                audit.callback(event)
        with Debugger(game, callback, max_events=500000) as debug:
            for address in set(audit.ADDRESSES) | set(STAGES) | {0x0801DFAC}:
                debug.breakpoint(address)
            game.press('A', hold=1, wait=0)
            for tick in range(frames):
                if returns:
                    break
                # Save prompts and any-button ending waits use normal inputs.
                if tick % 120 == 119:
                    game.press('A', hold=1, wait=0)
                else:
                    game.frames(1)
                if tick % 180 == 0:
                    name = f'frame-{tick:05d}'
                    picture = game.capture(name)
                    images.append(dict(file=name+'.png', frame=game.core.frame_counter,
                        phase=audit.phase, rgb_sha256=digest(picture.tobytes())))
        screen = audit.report()
        (output/'screen-text.json').write_text(json.dumps(screen, indent=2)+'\n')
        snapshot = game.snapshot()
        snapshot.save(output/'final')
        report = dict(rom_sha256=digest(rom), source_rom_sha256=original_hash,
            source_save_sha256=save_hash, fixture_state_sha256=digest(fixture.state),
            fixture_battery_sha256=digest(fixture.battery),
            final_battery_sha256=digest(snapshot.battery), inputs=game.inputs,
            overrides=overrides, stages=stages, images=images,
            ending_returned=bool(returns), scope=__doc__,
            text_counts={key: len(screen[key]) for key in ('reads', 'glyphs',
                'unclassified_glyphs', 'unreadable_streams', 'layout_violations')},
            generator_sha256=digest(Path(__file__).read_bytes()))
    require(original_hash == digest(load_base()) and save_hash == digest(save.read_bytes()),
            'Supplied ROM/save changed')
    report['source_files_unchanged'] = True
    report['complete_stage_order'] = [row['stage'] for row in stages] == list(STAGES.values())
    report['caller_abi_and_guard_preserved'] = bool(returns)
    report['passed'] = report['complete_stage_order'] and bool(returns) and not any(report['text_counts'][key] for key in
        ('unclassified_glyphs', 'unreadable_streams', 'layout_violations'))
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Controlled ending</title>'
        '<style>body{background:#18222b;color:white;font:16px system-ui}figure{display:inline-block}'
        'img{image-rendering:pixelated;width:480px}</style><h1>Controlled ending sequence</h1>'
        '<p>One entry override; native staging, save, fades and credits. See report.json for outcome.</p>'+
        ''.join(f'<figure><figcaption>{html.escape(i["phase"])} / {i["frame"]}</figcaption>'
                f'<img src="{i["file"]}"></figure>' for i in images))
    print(json.dumps({key: report[key] for key in ('passed','ending_returned','text_counts')}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/ending-sequence')
    parser.add_argument('--frames', type=int, default=30000)
    args = parser.parse_args()
    run(args.source, args.output, args.frames)
