"""Build a hash-pinned native gallery for a reviewed text-panel family."""
import argparse,html,json
from pathlib import Path
from tools.rom import ROOT,digest,require


def run(source,folder):
    out=source/folder;build=json.loads((source/'build.json').read_text())
    report=json.loads((out/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale text-panel report')
    cards=[];images={}
    for row in report['cases']:
        pictures=[]
        for name,sha in row['images'].items():
            relative=row['case']+'/'+name
            require(digest((out/relative).read_bytes())==sha,'Text-panel capture changed')
            images[relative]=sha
            pictures.append('<img loading="lazy" width="480" height="320" src="'+html.escape(relative)+'">')
        cards.append('<details><summary>'+html.escape(row['case'])+'</summary>'+''.join(pictures)+'</details>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 text panels</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{padding:16px;margin:12px 0;background:#242838}img{image-rendering:pixelated;max-width:100%;height:auto}</style><h1>Torneko 2 text panels</h1><p>'+html.escape(report['scope'])+'</p>'
    (out/'index.html').write_text(page+''.join(cards)+'\n')
    (out/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n')
    print(out/'index.html')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--folder',required=True)
    a=p.parse_args();run(a.source,a.folder)
