"""Check the disassembled direct item-definition consumers, including fields.

The bounded Thumb literal scan is an inventory, not whole-program reachability.
Numeric consumers keep the original table; named consumers must use a checked
English copy with all non-name record bytes preserved. The skill footer and
confirmation use their existing bounded48-record equipment subset.
"""
import argparse
import json
import struct
from pathlib import Path

from tools.rom import ROOT, digest, load_base, require


def run(source, output):
    catalog=json.loads((ROOT/'config/item-definition-consumers.json').read_text())
    original=load_base();rom=(source/'torneko-2-english.gba').read_bytes()
    build=json.loads((source/'build.json').read_text())
    require(digest(original)==catalog['base_rom_sha256'] and digest(rom)==build['output_sha256'],'Definition audit identity differs')
    base=catalog['definition_start'];size=catalog['definition_records']*catalog['definition_stride']
    loads=[]
    for at in range(0,catalog['scan_end'],2):
        op=struct.unpack_from('<H',original,at)[0]
        if op&0xF800!=0x4800:continue
        literal=((at+4)&~3)+(op&255)*4
        pointer=struct.unpack_from('<I',original,literal)[0]
        if 0x08000000+base<=pointer<0x08000000+base+size:loads.append((at,literal,pointer))
    require(loads==[(r['load_offset'],r['literal_offset'],r['source_pointer']) for r in catalog['entries']],
            'Direct definition consumer inventory differs')
    results=[]
    for row in catalog['entries']:
        at=row['load_offset'];literal=row['literal_offset']
        require(original[at:row['context_end']].hex()==row['context_hex'],'Definition consumer code differs')
        pointer=struct.unpack_from('<I',rom,literal)[0];offset=pointer-0x08000000
        if row['disposition']=='numeric-record-fields':
            require(pointer==row['source_pointer'] and all(f in (4,8,10,12,16,20,21) for f in row['record_fields']),
                    'Numeric-only definition consumer differs')
        else:
            count=row['copied_records']
            owners=[a for a in build['allocations'] if a['start']==offset and a['end_exclusive']-offset==count*24]
            require(len(owners)==1,'Named definition consumer lacks its owned table')
            for record in range(count):
                start=record*catalog['definition_stride']
                require(rom[offset+start+4:offset+start+24]==original[base+start+4:base+start+24],
                        'Definition copy changed non-name fields')
        results.append(row|dict(compiled_pointer=pointer))
    report=dict(passed=True,rom_sha256=digest(rom),source_sha256=digest(original),consumers=results,
                literal_words=len({r['literal_offset'] for r in results}),scope=__doc__)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print('Item-definition callers:',len(results),'checked')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'build/english')
    p.add_argument('--output',type=Path,default=ROOT/'build/caller-continuation/item-definition-callers.json')
    a=p.parse_args();run(a.source,a.output)
