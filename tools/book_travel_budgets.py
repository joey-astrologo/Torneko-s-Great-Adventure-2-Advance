"""Original legacy record and travel windows, with saved-name reserve."""
import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
    path=source/'book-travel-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==16,'Book/travel budget evidence stale')
    config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('book-travel-current-')]
    def add(ident,title,window,start,end,labels,note):
        config['contexts'].append({'id':'book-travel-current-'+ident,'name':title,'stage':'current','window':window,'start':start,'end':end,'rows':len(labels),'labels':labels,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':note})
    add('labels','Record-menu labels',72,6,72,['Records','Scores','Trade items'],'Original72px window,6px cursor reserve, native2/3 rows. Final selection and repeated cancellation pass.')
    add('yes','Travel Yes column',80,6,32,['Yes'],'Original32px cursor stride; first label starts6px.')
    add('no','Travel No column',80,38,80,['No'],'Original32px cursor stride; second label starts38px.')
    add('travel','Travel question',80,0,80,['Travel?'],'Centered in the original80px one-row window.')
    add('prompts','Travel and trade prompts',224,0,216,['Go through Mysterious Meadow?','Put items in the storehouse','to trade them.','has save data. Overwrite it?'],'Separate lines in their original two-row modals; no geometry or font change.')
    add('saved-name','Saved village warning',224,112,216,[' Village already'],'112px reserved for eight maximum14px saved-name glyphs. Original1F getter/14 centering controls and complete189px native row verified.')
