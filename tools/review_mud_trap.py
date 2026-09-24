"""Source/English and native status-trap message chains."""
import argparse
import html,json
from tools.rom import ROOT,digest,require
from tools.verify_mud_trap import OUT


def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/mud-trap-validation'
    build=json.loads((ROOT/'build/english/build.json' if cumulative else OUT/'build.json').read_text());report=json.loads((OUT/'report.json').read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale mud trap evidence');cards=[];images={}
    sources=''.join('<pre>'+html.escape(r['source']['japanese'])+'</pre><pre>'+html.escape(r['english'])+'</pre><p>'+str(r['maximum_width'])+' /216px, '+str(r['encoded_bytes'])+' encoded bytes.</p>' for r in build['mud_trap']['entries'])
    for case in report['cases']:
        pictures=[]
        for name,expected in case['images'].items():
            relative=case['case']+'/'+name;require(digest((OUT/relative).read_bytes())==expected,'Mud trap image changed');images[relative]=expected
            pictures.append('<img width="480" height="320" src="'+html.escape(relative)+'">')
        cards.append('<details open><summary>'+html.escape(case['case'])+'</summary>'+''.join(pictures)+'</details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 mud trap warnings</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}</style><h1>Torneko 2 mud trap warnings</h1><p>Separate five-source prototype. All eight bread IDs203 through210, failed activation and no-bread cases pass. Original native logic spoils the six susceptible bread types and preserves Rotten bread and Golden bread. Exact item IDs/flags, native identification, one-line messages, caller/queue ABI and HP/gold/save are checked. Controlled entry and first-slot item IDs are recorded; ordinary trap discovery and other inventory arrangements remain separate.</p>'''
    if cumulative:page=page.replace('Separate ', 'Integrated ').replace('prototype.', 'consumer.')
    (OUT/'index.html').write_text(page+sources+''.join(cards)+'\n');(OUT/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n');print(OUT/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
