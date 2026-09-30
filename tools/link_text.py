"""Prototype private link-trade messages and original-width actions."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.compact_font import encode,measure
CATALOG=ROOT/'translations/link-text-review.json'
ERRORS=(0x6EBB0,0x6EB94,0x6EB74,0x6EB58,0x6EB38)
SITES={0x6EBD0:0x57C4C,0x6EBF4:0x57DB8,0x6EC10:0x57DC4,0x6EC60:0x57DC8,0x6ECAC:0x57FE4,0x6ECB8:0x58094}
def add_link_text(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and {e['source']['offset'] for e in c['entries']}==set(ERRORS)|set(SITES),'Link source cohort differs');rows=[]
 for e in c['entries']:
  s=e['source'];at=s['offset'];text=e['english'];require(s==source(build.original,at+0x08000000) and e['status']=='reviewed','Link source/review differs');field='error' if at==0x6EBD0 else 'item' if at==0x6EBF4 else None
  require(re.findall(r'\{([^}]+)\}',text)==([field] if field else []) and not any(x in text for x in '%@'),'Link fields differ');require(bytes.fromhex(s['raw_hex']).count(b'%s')==int(field is not None),'Link native format differs')
  lines=text.split('\n');widths=[measure(line.replace('{'+field+'}','')) if field else measure(line) for line in lines]
  if field=='item':widths=[w+162*line.count('{item}') for w,line in zip(widths,lines)]
  elif field=='error':widths=[w+max(measure(r['english']) for r in c['entries'] if r['source']['offset'] in ERRORS)*line.count('{error}') for w,line in zip(widths,lines)]
  budget=34 if at==0x6ECAC else 216;require(len(lines)<=(1 if at in ERRORS else 2) and max(widths)<=budget,'Link native line budget exceeded')
  raw=b'\r'.join((b'\x06\x06' if at==0x6ECAC else b'')+b''.join(b'%s' if part=='{'+str(field)+'}' else encode(part)[:-1] for part in re.split(r'(\{[^}]+\})',line)) for line in lines)+b'\0'
  maximum=len(raw)
  if field=='item':maximum=len(raw)-2+63
  elif field=='error':maximum=len(raw)-2+max(len(encode(r['english']))-1 for r in c['entries'] if r['source']['offset'] in ERRORS)
  require(not field or maximum<=128,'Link native128-byte format buffer exceeded')
  offset=build.allocate(e['id'],raw,'link-text');rows.append(e|{'offset':offset,'encoded_hex':raw.hex(),'maximum_bytes':maximum,'field':field,'layout':{'pages':[lines],'line_widths':[widths],'maximum_width':budget}})
 by_src={r['source']['offset']:r for r in rows};table=b''.join(struct.pack('<I',by_src[x]['offset']+0x08000000) for x in ERRORS);at=build.allocate('link-text-error-pointers',table,'link-text')
 require(build.original[0x1547BC:0x1547D0]==b''.join(struct.pack('<I',x+0x08000000) for x in ERRORS),'Link original error table differs')
 build.patch('link-error-reader',0x57C50,struct.pack('<I',0x081547BC),struct.pack('<I',at+0x08000000),'link-text')
 for src,site in SITES.items():build.patch('link-reader-'+hex(site),site,struct.pack('<I',src+0x08000000),struct.pack('<I',by_src[src]['offset']+0x08000000),'link-text')
 return {'entries':rows,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
