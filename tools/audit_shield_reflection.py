"""Full shield-reflection attack plus bounded fields, guards, and visible pixels.

Controlled incoming attack with a warrior reflection flag or equipped Blade Shield.
Native source selection, formatter, damage effects and full attack return execute.
Boundary profiles change only formatter fields, not the damage applied by combat.
"""
import argparse
import json
from pathlib import Path

import mgba.log
from PIL import Image
from tools import audit_caller_followup as followup
from tools import verify_player_status_prototype as status
from tools.caller_binding_checks import CallerBindingChecks
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck


class ShieldChecks(CallerBindingChecks):
    def __init__(self, game, build, profile):
        row = build['shield_reflection']['entries'][0]
        binding = dict(call=0x0800CED4,consumer=0x08000FB8,source_offset=row['source']['offset'])
        super().__init__(game,{'caller_repairs':dict(entries=[row],bindings=[binding])},profile)
        self.source = row['offset']+0x08000000
        self.panel = None
        self.colours = []
        self.complete_frame = None
        self.origin = None
        self.combat = None
        self.addresses |= {0x0801588C,0x080158CE,0x0800CEFA,0x08001BC4,0x08001C14,0x08001C68,
                           0x08008F4C,0x0800CC94}

    def callback(self,event):
        a,r = event['address'],event['registers']
        if a == 0x08008F4C and self.combat is None:
            m = self.game.core.memory
            target = m.u32[0x02001624]
            attacker = next(m.u32[0x02001624+4*i] for i in range(1,56)
                            if m.u32[m.u32[0x02001624+4*i]+8] & 0x80000000 and
                            m.u16[m.u32[0x02001624+4*i]+0x84] > 0)
            self.combat = dict(attacker=attacker,target=target,return_address=r[14],
                               hp_before=[m.u16[p+0x84] for p in (attacker,target)])
        if a == 0x0800CC94 and self.combat and r[1] == self.combat['return_address']:
            m = self.game.core.memory
            self.combat['hp_after'] = [m.u16[self.combat[k]+0x84] for k in ('attacker','target')]
        if a == 0x08000FB8 and r[14] == 0x0800CED9 and r[1] != self.source:
            return
        super().callback(event)
        if a == 0x08000FB8 and r[1] == self.source:
            require(self.panel is None,'Shield format repeated unexpectedly')
            dest,expected,guard,*_ = self.pending[0x0800CED8]
            self.panel = ActionCheck(self.game,expected[:-1],0x0800CEFB,256,guard)
        if self.panel:
            if a == 0x08001C14 and self.panel.pending_glyph:
                m = self.game.core.memory
                bank = m.u16[m.u32[r[5]+12]] >> 12
                colour = m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])]
                self.colours.append(tuple(((colour>>s)&31)*255//31 for s in (0,5,10)))
            self.panel.callback(event)
            if self.panel.queued and self.origin is None:
                m = self.game.core.memory
                self.origin = (m.u8[0x02000000],m.u8[0x02000001])
            if self.panel.complete and self.complete_frame is None:
                self.complete_frame = event['frame']

    def report(self):
        report = super().report()
        require(self.combat and 'hp_after' in self.combat and
                all(before > after for before,after in zip(self.combat['hp_before'],self.combat['hp_after'])),
                'Native attack and shield reflection must both apply damage: '+repr(self.combat))
        report['combat_health'] = self.combat
        p = self.panel
        require(p and p.complete and p.returned and len(p.draws)==len(self.colours),
                'Shield message/queue/glyph checks incomplete')
        # The complete attack later closes its message window. Use the first
        # ordinary frame capture after this message's final glyph, before that
        # close; do not keep the window alive by changing the handler.
        capture = next((v for v in self.game.images if v['frame'] >= self.complete_frame+3),None)
        require(capture is not None,'No complete shield message frame was captured')
        picture = Image.open(self.game.output/capture['path']).convert('RGB')
        visible = []
        for draw,colour in zip(p.draws,self.colours):
            if draw['native_scroll']:
                shift = draw['key'][-1]-draw['y']
                require(shift > 0,'Shield message scroll direction differs')
                for old in visible: old['final_y'] -= shift
            visible.append(draw | dict(final_y=draw['y'],colour=colour))
        pixels = 0
        for draw in visible:
            require(draw['final_y'] >= 0,'Shield message left the visible panel')
            glyph,_ = p.glyph_record(draw['code'])
            for y,line in enumerate(glyph['rows']):
                for x,bit in enumerate(line):
                    at = self.origin[0]+draw['x']+x,self.origin[1]+16*draw['final_y']+y
                    require((picture.getpixel(at)==draw['colour']) == (bit=='#'),'Shield visible pixels differ')
                    pixels += 1
        return report | dict(shield_queue=p.queued,visible_pixels_checked=pixels,
                             image=capture['path'],image_sha256=digest((self.game.output/capture['path']).read_bytes()))


def run(source, output):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Shield audit ROM differs')
    previous = status.OUT
    try:
        status.OUT = output
        status.ready(rom,build)
    finally:
        status.OUT = previous
    spec = dict(name='shield-reflection',entry=0xBCBC,expected_call=0xCED4,target='monster',
        fields=[(0x84,2,999),(0x86,2,999)],entry_fields=[(0x41,1,3)],
        args=['monster','player',1,0],stack_args=[0,0],
        entry_memory_fields=[(0x020081D4,4,0x400,'Existing warrior reflection flag read at0800CB6E')])
    old_defs,old_checks = followup.definitions,followup.CallerBindingChecks
    results = []
    try:
        followup.CallerBindingChecks = ShieldChecks
        blade = spec | dict(name='blade-shield-reflection',item=(37,1),equipped=True,
            entry_memory_fields=[(0x020081D4,4,0,'Clear warrior reflection; exercise native equipped-shield getter'),
                (0x0200DF28,4,0xC8800010,'Existing equipped Blade shield record with native reflection ability bit0x10')])
        for selected,profile in [(spec,p) for p in (None,'maximum-width','maximum-bytes','coloured')]+[(blade,None)]:
            followup.definitions = lambda:[selected]
            folder = 'blade-shield' if selected is blade else (profile or 'native-fields')
            result = followup.run(source,output/'native/ready',output/folder,field_profile=profile)
            results.extend(result['cases'])
        damage = lambda c: [a-b for a,b in zip(c['combat_health']['hp_before'],c['combat_health']['hp_after'])]
        require(all(damage(c) == damage(results[0]) for c in results[1:4]),
                'Display boundary overrides changed native combat damage')
    finally:
        followup.definitions,followup.CallerBindingChecks = old_defs,old_checks
    report = dict(rom_sha256=digest(rom),tool_sha256=digest(Path(__file__).read_bytes()),
                  cases=results,passed=all(c['english_output'] and len(c['format_checks'])==1 for c in results),scope=__doc__)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    require(report['passed'],'Shield reflection audit failed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/english/shield-reflection-validation')
    args = parser.parse_args()
    run(args.source,args.output)
