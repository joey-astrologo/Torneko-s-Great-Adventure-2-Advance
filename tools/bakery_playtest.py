"""Reach the ordinary bank invocation used for controlled bakery probes."""
import json
from tools.emulator import Session, Snapshot
from tools.rom import digest, require
from tools.verify_storage import SAVE
from tools.town_playtest import position

def service_ready(rom, output):
    path = output / 'native/ready'
    if path.with_suffix('.json').exists():
        snapshot = Snapshot.load(path)
        if snapshot.rom_sha256 == digest(rom):
            return snapshot
    with Session(rom, output / 'native', initial_save=SAVE.read_bytes()) as game:
        game.frames(600); game.press('START', wait=180); game.press('A', wait=300)
        require(position(game) == (288, 224), 'Storage save did not resume at native book')
        for key, hold in [('RIGHT',16),('DOWN',32),('LEFT',32),('DOWN',32),('LEFT',32),('DOWN',3),('DOWN',16),('RIGHT',64),('DOWN',16),('RIGHT',16),('UP',3)]:
            game.press(key, hold=hold, wait=120)
        snapshot = game.snapshot(); snapshot.save(path)
        (output / 'native/provenance.json').write_text(json.dumps({'rom_sha256': digest(rom), 'save_sha256': digest(SAVE.read_bytes()),
                                                               'inputs': game.inputs, 'controlled_overrides': []}, indent=2)+'\n')
        return snapshot
