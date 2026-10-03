"""Accept the two approved editorial repairs through their original NPC branches."""
import argparse
from pathlib import Path

from tools.research_event_stubs import run
from tools.rom import ROOT


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    run(args.source, args.output, acceptance=True)
