"""Source/English and native status-trap message chains."""
import argparse
import html,json
from tools.rom import ROOT,digest,require
from tools.verify_status_traps import OUT


def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/status-traps-validation'
    build=json.loads((ROOT/'build/english/build.json' if cumulative else OUT/'build.json').read_text());report=json.loads((OUT/'report.json').read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale status trap evidence');cards=[];images={}
    sources=''.join('<pre>'+html.escape(r['source']['japanese'])+'</pre><pre>'+html.escape(r['english'])+'</pre><p>'+str(r['maximum_width'])+' /216px, '+str(r['encoded_bytes'])+' encoded bytes.</p>' for r in build['status_traps']['entries'])
    for case in report['cases']:
        pictures=[]
        for name,expected in case['images'].items():
            relative=case['case']+'/'+name;require(digest((OUT/relative).read_bytes())==expected,'Status trap image changed');images[relative]=expected
            pictures.append('<img width="480" height="320" src="'+html.escape(relative)+'">')
        cards.append('<details open><summary>'+html.escape(case['case'])+'</summary>'+''.join(pictures)+'</details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 status trap warnings</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}</style><h1>Torneko 2 status trap warnings</h1><p>Separate five-source prototype. Controlled entry into the sleep, hallucination and confusion trap handlers, activation/refusal arguments and cleared resistance/status fields. All18 name/branch cases preserve complete one-line message chains, native status timers, caller/queue ABI and HP/items/gold/save. Ordinary trap placement/discovery and additional resistance branches remain separate.</p>'''
    page=page.replace('Separate six-source prototype.', 'Six owned sources.').replace('Separate two-source prototype.', 'Two owned sources.').replace('Separate five-source prototype.', 'Five owned sources.') if cumulative else page
    (OUT/'index.html').write_text(page+sources+''.join(cards)+'\n');(OUT/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n');print(OUT/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

