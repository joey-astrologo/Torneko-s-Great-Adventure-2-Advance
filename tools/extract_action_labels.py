"""Bounded original 45-slot action-name table, including null/empty slots."""
import json,struct
from tools.rom import ROOT,load_base,digest,require
from tools.extract_items import source

START,END=0x141904,0x1419B8
TABLE_SHA256='aabf92a3a3c2560abae5368f545fe8a038d85ca8048e143fa49f2e6fb215546e'

def extract():
    rom=load_base();require(digest(rom[START:END])==TABLE_SHA256,'Action source table changed');rows=[]
    for index in range(45):
        site=START+index*4;pointer=struct.unpack_from('<I',rom,site)[0];src=source(rom,pointer)
        disposition='null' if src is None else 'empty' if src['raw_hex']=='00' else 'label'
        require(disposition==('empty' if index==0 else 'null' if 36<=index<=39 else 'label'),
                'Action slot classification differs')
        rows.append({'index':index,'pointer_offset':site,'source':src,'disposition':disposition})
    return {'source_rom_sha256':digest(rom),'table_start':START,'table_end_exclusive':END,
            'table_sha256':TABLE_SHA256,'entries':rows,
            'scope':'45 original pointers:40 nonempty action IDs, one empty slot and four nulls. Shared pointer aliases retained as references; table enumeration does not establish native availability or ownership of every consumer.'}

def run():
    out=ROOT/'build/action-label-extraction';out.mkdir(parents=True,exist_ok=True);report=extract()
    (out/'catalog.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Action label table:',len(report['entries']),'slots');return report

if __name__=='__main__':run()
