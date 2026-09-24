"""Read matching standalone or cumulative service candidates without rebuilding."""
import json
from tools.rom import ROOT,digest,require


def load_candidate(service,cumulative=False):
    out=ROOT/('build/english/'+service+'-validation' if cumulative else 'build/'+service+'-prototype')
    source=ROOT/'build/english' if cumulative else out
    rom=(source/('torneko-2-english.gba' if cumulative else 'game.gba')).read_bytes()
    build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Service candidate ROM differs')
    return out,rom,build
