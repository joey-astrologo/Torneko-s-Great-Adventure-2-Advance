"""Measure native menu geometry before committing English action labels."""

import json

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.text_codec import readable, tokenize

OUTPUT = ROOT/'build/menu-layout-audit/native'
DUNGEON = ROOT/'build/mansion/native/quest-room-entrance'
TOWN = ROOT/'build/mansion/native/family-1-1/morning'
CASES = [
    ('dungeon-root',DUNGEON,[('B',8)]),
    ('inventory-food',DUNGEON,[('B',8),'A','A']),
    ('inventory-arrows',DUNGEON,[('B',8),'A','DOWN','A']),
    ('inventory-equipped',DUNGEON,[('B',8),'A','DOWN','DOWN','A']),
    ('ground-arrows',DUNGEON,[('B',8),'A','DOWN','A','DOWN','DOWN','A',('B',8),'DOWN','A']),
    ('tactics',DUNGEON,[('B',8),'DOWN','DOWN','A']),
    ('ground-empty',DUNGEON,[('B',8),'DOWN','A']),
    ('bank',TOWN,[('UP',8),'A','A']),
]


def parent_image(game):
    """Read the parent tilemap and every referenced 4bpp tile, without OAM cursor blink."""
    m=game.core.memory
    descriptor=bytes(m[0x02000000:0x02000018])
    base=m.u32[0x0200000C]
    control=m.u16[0x0400000E]  # Native menu BG3, shared map/character base with BG2.
    map_base=0x06000000+((control>>8)&31)*0x800
    char_base=0x06000000+((control>>2)&3)*0x4000
    require(not control&0x80 and map_base<=base<map_base+0x800,'Unexpected parent background format')
    words=[m.u16[base+y*64+x*2] for y in range(descriptor[5]*2) for x in range(descriptor[4])]
    indices=sorted({w&0x3ff for w in words})
    pixels=b''.join(bytes(m[char_base+i*32:char_base+(i+1)*32]) for i in indices)
    return {'descriptor_hex':descriptor.hex(),'bg3_control':control,'tilemap_start':base,
            'tilemap_entries':len(words),'tilemap_sha256':digest(b''.join(w.to_bytes(2,'little') for w in words)),
            'character_base':char_base,'tile_indices':indices,'tile_pixels_sha256':digest(pixels)}


class Observer:
    ADDRESSES = (0x08001798,0x08002298,0x080021B4,0x08002284,0x08001BC4,0x08001C6E)

    def __init__(self,game):
        self.game = game
        self.creates,self.reads,self.callers = [],[],[]
        self.stack = []
        self.draw_pending = None

    def callback(self,event):
        r,a,m = event['registers'],event['address'],self.game.core.memory
        if a == 0x08001798:
            self.creates.append({'frame':event['frame'],'arguments':r[:4],'return':r[14]})
        elif a == 0x08002298:
            self.callers.append({'frame':event['frame'],'window':r[0],'source':r[1],'return':r[14]})
        elif a == 0x080021B4:
            data = bytes(m[r[1]:r[1]+2048])
            tokens,end = tokenize(data)
            context = bytes(m[r[0]:r[0]+24])
            if (self.stack and not self.stack[-1]['glyph_positions']
                    and self.stack[-1].get('entry_registers') == tuple(r)):
                row = self.stack[-1]
                require(row['raw_hex'] == data[:end].hex() and row['context_hex'] == context.hex(),
                        'Repeated native reader entry changed source/window')
                row['repeated_entry_observations'] = row.get('repeated_entry_observations', 0) + 1
                return
            row = {'frame':event['frame'],'source':r[1],'window':r[0],
                'entry_registers':tuple(r),
                'context_hex':context.hex(),'screen_x':context[0],'screen_y':context[1],
                'initial_x':context[2],'initial_row':context[3],'window_width':context[4]*8,
                'rows':context[5],'fixed_advance':context[6],'spacing':context[8],
                'raw_hex':data[:end].hex(),'text':readable(tokens),'tokens':tokens,'glyph_positions':[]}
            self.reads.append(row);self.stack.append(row)
        elif a == 0x08002284:
            if self.stack:self.stack.pop()
        elif a == 0x08001BC4 and self.stack:
            key=(r[0],r[1],r[13],r[14],m.u8[r[0]+2],m.u8[r[0]+3])
            if self.draw_pending is not None:
                require(self.draw_pending==key,'Overlapping native glyph calls')
                row=self.stack[-1];row['repeated_draw_observations']=row.get('repeated_draw_observations',0)+1
                return
            self.draw_pending=key
            self.stack[-1]['glyph_positions'].append({'code':r[1],'x':m.u8[r[0]+2],'row':m.u8[r[0]+3],
                                                    'spacing':m.u8[r[0]+8]})
        elif a == 0x08001C6E:
            self.draw_pending=None


def run():
    mgba.log.silence()
    original = load_base();source_save = default_rom().with_suffix('.sav')
    save_hash = digest(source_save.read_bytes())
    routes = []
    for name,fixture,actions in CASES:
        snapshot = Snapshot.load(fixture)
        with Session(original,OUTPUT/name) as game:
            game.restore(snapshot)
            observer = Observer(game)
            with Debugger(game,observer.callback,max_events=30000) as debug:
                for address in observer.ADDRESSES:debug.breakpoint(address)
                for i,action in enumerate(actions):
                    key,hold = action if isinstance(action,tuple) else (action,3)
                    game.press(key,hold=hold,wait=240)
                    game.capture(f'step-{i:02}')
                game.capture('menu')
                menu_end = len(observer.reads)
                # These item menus return to their parent list. Verify exact
                # parent VRAM bytes after cancel/reopen/cancel; cursor is OAM.
                parent_checks = []
                if name.startswith('inventory-'):
                    game.press('B',wait=120)
                    before=parent_image(game)
                    for _ in range(2):
                        game.press('A',wait=120);game.press('B',wait=120)
                        require(parent_image(game)==before,'Native parent descriptor/tilemap/pixels changed')
                        parent_checks.append(before|{'descriptor_and_pixels_preserved':True})
                    game.capture('parent-after-cancel')
            require(game.snapshot().battery == snapshot.battery,'Menu research wrote its battery')
            routes.append({'id':name,'fixture':str(fixture.relative_to(ROOT)),
                'fixture_state_sha256':digest(snapshot.state),'inputs':game.inputs,
                'creates':observer.creates,'callers':observer.callers,'reads':observer.reads,
                'menu_read_count':menu_end,'parent_checks':parent_checks,
                'capture':str((game.output/'menu.png').relative_to(ROOT)),
                'battery_unchanged':True})
    require(digest(load_base()) == digest(original) and digest(source_save.read_bytes()) == save_hash,
            'Original files changed')
    report = {'passed':True,'source_rom_sha256':digest(original),'source_save_sha256':save_hash,
        'original_files_unchanged':True,'routes':routes,
        'scope':'Original Japanese native geometry and glyph positions from ordinary menu inputs; food, arrows, equipped shield, dropped-arrow ground actions, empty ground, root, tactics and new bank. Parent checks cover only the three observed inventory-action states. No English insertion, forced game state, transactions or whole-game menu coverage.'}
    (OUTPUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Native menu audit:',len(routes),'routes;',sum(len(r['parent_checks']) for r in routes),'parent checks')
    return report


if __name__ == '__main__':
    run()
