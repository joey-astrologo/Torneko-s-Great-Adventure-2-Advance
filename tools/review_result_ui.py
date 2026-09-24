"""Gallery for the owned result-panel labels, fields and numeric bounds."""
import argparse,html,json
from pathlib import Path
from tools.rom import ROOT,digest,require


def run(source,history=False):
    build=json.loads((source/'build.json').read_text());out=source/('history-ui-validation' if history else 'ui-validation')
    report=json.loads((out/'report.json').read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale result UI gallery')
    images={};cards=[]
    for row in report['cases']:
        pictures=[]
        for name,sha in row['images'].items():
            relative=row['case']+'/'+name;require(digest((out/relative).read_bytes())==sha,'Result UI capture changed');images[relative]=sha
            pictures.append('<img loading="lazy" width="480" height="320" src="'+html.escape(relative)+'">')
        cards.append('<details><summary>'+html.escape(row['case'])+'</summary>'+''.join(pictures)+'</details>')
    resources=build['results']['ui_entries']+(build.get('history',{}).get('entries',[]) if history else [])
    if history:
        ids={r['id'] for case in report['cases'] for r in case['reads']+case['formats']}
        pointers={a for case in report['cases'] for f in case['formats'] for a in f['arguments']}
        resources=[r for r in resources if r['id'] in ids or r['offset']+0x08000000 in pointers]
    budget=''.join('<tr><td>'+html.escape(r['english'])+'</td><td>'+str(r['maximum_width'])+' / '+str(r['budget'])+'px</td><td>'+str(r['maximum_bytes'])+' / '+str(r['capacity'])+' bytes</td></tr>' for r in resources)
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 results UI</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}td,details{padding:12px;background:#242838}details{margin:12px 0}img{image-rendering:pixelated;max-width:100%;height:auto}</style><h1>Torneko 2 results UI</h1><p>'+html.escape(report['scope'])+'</p><table>'+budget+'</table>'+''.join(cards)
    (out/'index.html').write_text(page+'\n');(out/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n');print(out/'index.html')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/results-ui-prototype');p.add_argument('--history',action='store_true');a=p.parse_args();run(a.source,a.history)
