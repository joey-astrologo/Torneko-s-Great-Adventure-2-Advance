"""Owned dungeon cutscene text; retain original tables and native controls."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.text_codec import tokenize
from tools.dialogue_layout import compile_dialogue,width
from tools.compact_font import encode,load_font
CATALOG=ROOT/'translations/dungeon-story-review.json'

def add_dungeon_story(build):
 catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original) and {r['index'] for r in catalog['entries']}==set(range(23))-{9,19},'Dungeon story source cohort differs')
 table=bytearray(build.original[0x1471D4:0x147234]);rows=[]
 for row in catalog['entries']:
  original=source(build.original,struct.unpack_from('<I',build.original,0x1471D8+4*row['index'])[0]);require(row['status']=='reviewed' and row['source']==original,'Dungeon story source differs');tokens=tokenize(bytes.fromhex(original['raw_hex']))[0];text=row['english']
  if row['index'] in (1,5,6,7,15,16,17):
   controls=[t['raw_hex'] for t in tokens if t['kind']=='command' and t.get('name')!='newline'];require(all(c in ('0306','14') for c in controls),'Dungeon story centered control family differs');require(not any(c in text for c in '{}%@'),'Unexpected centered-story control')
   pages=[p.split('\n') for p in text.split('\n\n')];require(all(1<=len(p)<=2 for p in pages),'Centered story page height exceeds original');widths=[[width(line,load_font()) for line in p] for p in pages];require(max(max(p) for p in widths)<=216,'Centered story exceeds native width')
   # The native page clear resets foreground. These original inscriptions
   # start each page with0306; preserve that per-page colour and command count.
   count=controls.count('0306');require(count in (0,len(pages)),'Inscription colour/page correspondence differs');raw=b''
   for n,page in enumerate(pages):
    if count:raw+=b'\x03\x06'
    raw+=b'\r'.join(b'\x14'+encode(line)[:-1] for line in page)
    if n+1<len(pages):raw+=b'\r'*(3-len(page))
   raw+=b'\0';layout={'pages':pages,'line_widths':widths,'maximum_width':216,'native_width':224,'encoded_bytes':len(raw),'source_colour_commands':controls.count('0306'),'centered_reflow':True}
  else:raw,layout=compile_dialogue(text,tokens)
  at=build.allocate(row['id'],raw,'dungeon-story');struct.pack_into('<I',table,4*(row['index']+1),at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':raw.hex(),'layout':layout})
 at=build.allocate('dungeon-story-private-table',bytes(table),'dungeon-story')
 for site,old,delta in [(0x1BE10,0x081471D4,0),(0x1C198,0x081471EC,24),(0x1C278,0x081471EC,24),(0x1C530,0x08147214,64)]:build.patch('dungeon-story-reader-'+hex(site),site,struct.pack('<I',old),struct.pack('<I',at+0x08000000+delta),'dungeon-story')
 return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
