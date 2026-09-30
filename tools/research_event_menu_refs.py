"""Original NPC custom-menu selectors and their text-bank references."""


def run():
    import json,struct
    from collections import defaultdict
    from tools.rom import ROOT,load_base,digest
    (ROOT/'build/event-script-audit').mkdir(parents=True,exist_ok=True)
    from tools.event_text import table_entries
    from tools.opening_text import banks
    r=load_base();assert struct.unpack_from('<I',r,0x50E4C)[0]==0x0814D53A
    inputs=[ROOT/'build/event-script-audit/npc-control-flow.json',ROOT/'build/event-script-audit/script-text-refs.json'];reports=[json.loads(p.read_text()) for p in inputs]
    assert all(report['source_rom_sha256']==digest(r) for report in reports), 'Script reference audit source ROM differs'
    refs=[ref for report in reports for ref in report['references']];uses=defaultdict(list)
    for e in refs:
     if e['mode']==2:uses[(e['bank'],e['extra'])].append(e)
    cat=json.loads((ROOT/'translations/tutorial-help-review.json').read_text());stubs={e['id'] for e in json.loads((ROOT/'build/text-inventory/catalog.json').read_text())['entries'] if e['family']=='event' and e['language_status']=='untranslated'};out=[]
    for (bn,gi),es in sorted(uses.items()):
     g=cat['groups'][gi];rows={(e['group'],e['index']):e for e in table_entries(banks()[bn])};texts=[];bad=[]
     if g['mode']==1:
      # Native50E4C points to14D53A,14 bytes into descriptor14D52C.
      count=g['descriptor'][7];skip=2 if g['menu'] in (8,19,21,22) else 1
      for pos in range(count-1):
       raw=bytes.fromhex(g['intro_table_hex']);word=4*(pos+skip)
       if word+4>len(raw):bad.append(dict(topic=pos,error='Selector beyond catalog table bounds'));continue
       p=int.from_bytes(raw[word:word+4],'little')-0x8000000;pair=tuple(r[p:p+2]);e=rows.get(pair);ref=dict(topic=pos,selector_rom_offset=p,pair=pair,id=e['id'] if e else None,unresolved_stub=bool(e and e['id'] in stubs));texts.append(ref)
       if not e or e['id'] in stubs:bad.append(ref)
     out.append(dict(bank=bn,configuration=gi,mode=g['mode'],menu=g['menu'],script_uses=es,text_references=texts,unresolved=bad));print(bn,gi,'mode',g['mode'],'menu',g['menu'],'uses',len(es),'unresolved',bad)
    report=dict(source_rom_sha256=digest(r),configurations=out,scope='Static mode2 script consumers cross-referenced to original tutorial selector tables; native50E24 count and50E2A..50E3A skip rules. No natural map/NPC reachability claim. Out-of-group source pairs and truncated tables are preserved as explicit failures, not treated as unused text or valid English bindings.');(ROOT/'build/event-script-audit/event-menu-references.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == "__main__":
    run()
