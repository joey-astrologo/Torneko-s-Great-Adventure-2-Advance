"""Check all seven native event loads/getters with controlled offset relocation.

Uses the prose preflight ROM; English candidate strings are only supplied to
selected table words in disposable RAM. No event scripts or ROM tables change.
"""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger,ffi
from tools.opening_text import BANK_RAM,banks
from tools.event_text import table_entries
from tools.lz77 import decompress

OUT=ROOT/'build/event-relocation-probe'

def invoke(game,address,args,max_steps=100000):
    cpu=game.core.cpu
    for i,value in enumerate(args):cpu.gprs[i]=value
    preserved=[int(cpu.gprs[i])&0xFFFFFFFF for i in range(4,12)],int(cpu.gprs[13])&0xFFFFFFFF
    cpu.gprs[14]=0x08000355
    for reg,value in ((b'cpsr',int(cpu.cpsr.packed)|0x20),(b'pc',address)):
        require(game.core._core.writeRegister(game.core._core,reg,ffi.new('uint32_t*',value)),'Controlled function entry failed')
    with Debugger(game) as debug:
        debug.breakpoint(0x08000354);debug.run_until(lambda events:bool(events),max_steps=max_steps)
    result=debug.events[-1]['registers']
    require((result[4:12],result[13])==preserved,'Native event function changed preserved registers/SP')
    return result[0]

def run(inserted=False,cumulative=False,source=None):
    global OUT
    mgba.log.silence()
    root=ROOT/('build/english' if cumulative else 'build/event-prose-insertion' if inserted else 'build/prose-preflight')
    if source is not None:
        require(cumulative, 'An alternate build directory requires cumulative bindings')
        root=source
    if cumulative:
        OUT=root/'event-bindings-validation';inserted=True
    elif inserted:OUT=root/'relocation'
    rom=(root/('torneko-2-english.gba' if cumulative else 'game.gba')).read_bytes()
    build=json.loads((root/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Prose preflight ROM differs')
    fixture=Snapshot.load(root/('event-prose-validation/native/reader-entry' if cumulative else 'native/reader-entry'))
    selected={r['id']:r for r in (build['dialogue']['entries'] if cumulative else build['preflight']['entries'])};results=[]
    with Session(rom,OUT) as game:
        for bank in banks():
            game.restore(fixture);m=game.core.memory
            invoke(game,0x0804D6F8,[bank['index']],max_steps=10000000)
            require(m.u32[0x0200FF38]==BANK_RAM,'Event loader selected another RAM bank')
            packed=struct.unpack_from('<I',rom,bank['pointer_offset'])[0]-0x08000000
            decoded,_=decompress(rom,packed);expected=bytearray(decoded)
            for word in range(4):struct.pack_into('<I',expected,word*4,(struct.unpack_from('<I',decoded,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
            require(bytes(m[BANK_RAM:BANK_RAM+len(decoded)])==expected,'Native event loader output/fixups differ')
            entries=table_entries(bank);changed=[]
            for entry in entries:
                if entry['id'] not in selected:continue
                target=selected[entry['id']]['rom_offset']+0x08000000
                replacement=(target-(BANK_RAM+entry['strings_offset']+entry['group_offset']))&0xFFFFFFFF
                address=BANK_RAM+entry['slot'];before=m.u32[address]
                if inserted:require(before==replacement,'ROM event table is not already bound to English')
                else:m.u32[address]=replacement
                changed.append({'id':entry['id'],'slot':entry['slot'],'before':before,'after':replacement,'target':target})
                struct.pack_into('<I',expected,entry['slot'],replacement)
            checked=[]
            for entry in entries:
                actual=invoke(game,0x08050270,[entry['group'],entry['index']])
                target=(BANK_RAM+entry['strings_offset']+entry['group_offset']+struct.unpack_from('<I',expected,entry['slot'])[0])&0xFFFFFFFF
                require(actual==target,'Native getter did not resolve exact table target')
                if entry['id'] in selected:
                    payload=bytes.fromhex(selected[entry['id']]['encoded_hex'])
                    require(bytes(m[actual:actual+len(payload)])==payload,'Native getter target does not contain compiled English')
                checked.append({'id':entry['id'],'group':entry['group'],'index':entry['index'],'target':actual})
            require(bytes(m[BANK_RAM:BANK_RAM+len(decoded)])==expected,'Read-only getter changed event bank')
            require(game.snapshot().battery==fixture.battery,'Controlled loader/getter wrote battery')
            results.append({'bank':bank['id'],'decoded_bytes':len(decoded),'native_load_and_fixups_match':True,
                            'controlled_table_words':changed,'getter_cases':checked,'abi_and_save_preserved':True})
            print('Event relocation',bank['id'],len(checked),'native getters;',len(changed),'controlled English offsets',flush=True)
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':('Actual ROM event bindings; no RAM offset replacement. ' if inserted else 'Controlled RAM offset replacement. ')+'Controlled native whole-bank loads and exact getter resolution for all seven known banks. Selected getter targets are verified against appended English. Event scripts remain unchanged; ROM versus controlled RAM binding is specified above. This proves address arithmetic/decoded allocation/ABI, not ordinary scene reachability, custom-consumer byte budgets or branch outcomes.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--inserted',action='store_true');mode.add_argument('--cumulative',action='store_true')
    parser.add_argument('--source',type=Path)
    args=parser.parse_args();run(args.inserted,args.cumulative,args.source)
