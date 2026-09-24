"""A matching-ROM gallery for the results/history actor-name cases."""
import argparse
import html
import json
from pathlib import Path
from tools.rom import ROOT, digest, require


def run(source, output):
    build=json.loads((source/'build.json').read_text()); report=json.loads((output/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'], 'Stale result gallery')
    cards=[]; images={}
    for row in report['cases']:
        pictures=[]
        for name,sha in row['images'].items():
            relative=row['case']+'/'+name
            require(digest((output/relative).read_bytes())==sha, 'Result capture changed')
            images[relative]=sha
            pictures.append('<img loading="lazy" width="480" height="320" src="'+html.escape(relative)+'">')
        cards.append('<details><summary>'+html.escape(row['case']+': '+row['english_actor'])+'</summary>'+''.join(pictures)+'</details>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 results/history names</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{padding:16px;margin:12px 0;background:#242838}img{image-rendering:pixelated;max-width:100%;height:auto}</style><h1>Torneko 2 results/history names</h1><p>'+html.escape(report['scope'])+'</p>'
    (output/'index.html').write_text(page+''.join(cards)+'\n')
    (output/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n')
    print(output/'index.html')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'build/results-prototype')
    p.add_argument('--output',type=Path)
    a=p.parse_args();run(a.source,a.output or a.source/'validation')
