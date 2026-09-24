"""Require complete record and password text evidence on the cumulative ROM."""
import json
from tools.rom import ROOT,digest,require


def validate(build,receipt,counts):
    require(len(build['records']['entries'])==64 and len(build['password']['entries'])==2,'Records/password resource coverage differs')
    expected_records={'rank-'+str(i) for i in range(11)}|{'maximum','minimum','locked','grey'}
    for family,expected in (('records',expected_records),('password',{'password-'+str(i) for i in range(4)})):
        folder=ROOT/'build/english'/(family+'-validation')
        report=json.loads((folder/'report.json').read_text());rows=report['cases']
        require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale '+family+' evidence')
        require(len(rows)==len(expected) and {r['case'] for r in rows}==expected,'Missing '+family+' case')
        require(all(r['visible_pixels_checked']>0 and r['reads'] and r['return'] and all(f['guard_tail_abi_match'] for f in r['formats']) for r in rows),'Incomplete '+family+' native evidence')
        if family=='records':
            for row in rows:
                if row['mode'] in ('maximum','minimum'):
                    require({f'records.row.{i}' for i in range(48)}<={r['id'] for r in row['reads']},'Incomplete48-row record evidence')
                if row['mode']!='rank':require(row['page_indices']==list(range(8))+[6],'Record page navigation differs')
        else:
            pages=len(next(r for r in build['password']['entries'] if r['id']=='password.notice')['layout']['pages'])
            require(all(len(row['images'])==pages and len(row['formats'])==1 and row['formats'][0]['bytes']==20 and
                        {r['id'] for r in row['reads']}=={'password.heading','password.notice','password.generated-kana'} for row in rows),'Incomplete password pages/protocol evidence')
        images={r['case']+'/'+p:sha for r in rows for p,sha in r['images'].items()}
        preview=json.loads((folder/'preview.json').read_text())
        require(preview=={'rom_sha256':build['output_sha256'],'cases':len(rows),'images':images},'Stale '+family+' gallery')
        for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Changed '+family+' capture')
        for pattern in ('*.json','index.html','*/*.png','native/*.json'):
            for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
        counts[family]=len(rows);receipt[family+'_scope']=report['scope']
    receipt.update(records_resources=64,password_resources=2)
