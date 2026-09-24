import argparse
import json,html
from tools.rom import ROOT,digest,require
parser=argparse.ArgumentParser();parser.add_argument('--cumulative',action='store_true');args=parser.parse_args()
out=ROOT/('build/english/steal-gold-validation' if args.cumulative else 'build/steal-gold-prototype')
build=json.loads(((ROOT/'build/english' if args.cumulative else out)/'build.json').read_text());report=json.loads((out/'report.json').read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale gold theft evidence')
images={};cards=[]
for c in report['cases']:
 pictures=[]
 for p,sha in c['images'].items():
  rel=c['case']+'/'+p;require(digest((out/rel).read_bytes())==sha,'Gold theft capture changed');images[rel]=sha
  pictures.append('<img width="480" height="320" src="'+html.escape(rel)+'">')
 cards.append('<details open><summary>'+html.escape(c['case'])+'</summary>'+''.join(pictures)+'</details>')
source=''.join('<pre>'+html.escape(r['source']['japanese']+'\n'+r['english'])+'</pre>' for r in build['steal_gold']['entries'])
page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 gold theft attack</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{padding:16px;margin:12px 0;background:#242838}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}pre{white-space:pre-wrap}</style><h1>Torneko 2 gold theft attack</h1><p>'+html.escape(report['scope'])+'</p>'
(out/'index.html').write_text(page+source+''.join(cards)+'\n');(out/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n')
print(out/'index.html')
