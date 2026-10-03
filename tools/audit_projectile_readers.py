"""Run all four projectile/staff announcement owners through their full effects.

Controlled existing actors and open trajectories; ordinary A triggers the turn,
then the full original projectile handler executes. No text/source replacements.
This establishes handler behavior, not ordinary monster encounter provenance.
"""
import argparse
import json
from pathlib import Path
import mgba.log
from tools import audit_caller_followup as followup
from tools import verify_player_status_prototype as status
from tools.rom import ROOT, digest, require


def run(source, output):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Projectile reader ROM differs')
    previous = status.OUT
    try:
        status.OUT = output
        status.ready(rom, build)
    finally:
        status.OUT = previous
    original = followup.definitions
    base = next(s for s in original() if s['name'] == 'monster-arrow-landing')
    specs = [base | dict(name=f'projectile-announcement-{i}', expected_call=0x2ABDE,
                        fields=[(0x91,1,i),(0x42,1,2)]) for i in (84,85,121,122)]
    try:
        followup.definitions = lambda: specs
        report = followup.run(source, output/'native/ready', output)
    finally:
        followup.definitions = original
    report.update(driver_sha256=digest(Path(__file__).read_bytes()), scope=__doc__)
    report['passed'] = all(c['english_output'] for c in report['cases'])
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    require(report['passed'], 'Projectile announcement caller has native findings')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/english/projectile-reader-validation')
    args = parser.parse_args()
    run(args.source, args.output)
