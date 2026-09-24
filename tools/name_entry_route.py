"""Normal-button navigation of the verified name editor, with state assertions."""

from tools.name_entry import EDIT, IDS, indexed
from tools.rom import require

PAGE = 0x0200CCE4
SELECTION = 0x0200CCEC
POSITION = 0x0200CCF0


class NameEntryRoute:
    def __init__(self, game, pages):
        self.game = game
        self.pages = [bytes.fromhex(p) if isinstance(p, str) else p for p in pages]

    def press(self, key):
        self.game.press(key, wait=12)

    def home(self):
        for _ in range(10):
            selected = self.game.core.memory.u32[SELECTION]
            if selected == 0:
                return
            self.press('UP' if selected >= 4 else 'LEFT')
        raise ValueError('Could not reach name-editor action row')

    def choose_id(self, ident, page=None):
        if page is None:
            page = next((i for i, p in enumerate(self.pages) if ident in p[4:]), None)
        require(page is not None and ident in self.pages[page][4:], 'Character not selectable')
        target = self.pages[page].index(ident, 4)
        self.home()
        for _ in range(len(self.pages)):
            if self.game.core.memory.u32[PAGE] == page:
                break
            self.press('A')
        require(self.game.core.memory.u32[PAGE] == page, 'Page switch failed')
        row, col = divmod(target - 4, 10)
        self.press('DOWN')
        for _ in range(row):
            self.press('DOWN')
        for _ in range(col):
            self.press('RIGHT')
        require(self.game.core.memory.u32[SELECTION] == target, 'Keyboard cursor differs')
        position = self.game.core.memory.u32[POSITION]
        self.press('A')
        if ident < 0xFE:
            require(self.game.core.memory.u8[EDIT + position] == ident, 'Selected ID was not entered')

    def clear(self):
        for _ in range(8):
            if self.game.core.memory.u8[EDIT] == 1:
                require(self.game.core.memory.u32[POSITION] == 0, 'Empty name cursor differs')
                return
            self.press('B')
        raise ValueError('Could not clear name')

    def enter(self, text):
        for char in text:
            self.choose_id(IDS[char])
        require(bytes(self.game.core.memory[EDIT:EDIT + 16]) == indexed(text),
                'Entered name record differs')

    def confirm(self):
        self.press('START')
        require(self.game.core.memory.u32[SELECTION] == 3, 'Start did not select Done')
        self.game.press('A', wait=180)
