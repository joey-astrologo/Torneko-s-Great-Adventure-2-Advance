"""New private dungeon readers preserve shared sources, code and selector data."""
import struct
import unittest
from tools.extract_shared_text import START,END
from tools.rom import load_base
from tools.rom_build import RomBuild


class DungeonTextOwnership(unittest.TestCase):
    def test_empty_fused_info_shares_category_copy_without_changing_source(self):
        from tools.compact_font import font_snapshot
        from tools.item_text import add_items
        from tools.extract_items import CATEGORY_DESCRIPTIONS
        original = load_base(); build = RomBuild(original)
        with font_snapshot():
            report = add_items(build)
        rom, _ = build.finish()
        first, second = (struct.unpack_from('<I', rom, p)[0] for p in (0x17BF8,0x17E68))
        self.assertEqual(first, second)
        self.assertNotEqual(first, CATEGORY_DESCRIPTIONS+0x08000000)
        self.assertEqual(rom[CATEGORY_DESCRIPTIONS:CATEGORY_DESCRIPTIONS+56],
                         original[CATEGORY_DESCRIPTIONS:CATEGORY_DESCRIPTIONS+56])
        for category in (3,6):
            row = next(r for r in report['entries'] if r['id']==f'item.category.{category}')
            self.assertEqual(struct.unpack_from('<I',rom,first-0x08000000+category*4)[0],
                             row['offset']+0x08000000)

    def test_shop_and_save_notices_preserve_unowned_shared_slots(self):
        from tools.dungeon_shop_text import add_dungeon_shop,LITERALS as shop
        from tools.save_notice_text import add_save_notices,LITERALS as save
        from tools.priest_warning_text import add_priest_warning
        for add,sites in ((add_dungeon_shop,{s:0 for s in shop}),
                          (add_save_notices,{s:0 for s in save}),
                          (add_priest_warning,{0x14144:0x4E0})):
            self.check_private(add,sites)

    def test_save_preview_preserves_editor_overrides_and_original_save_code(self):
        from tools.compact_font import font_snapshot
        from tools.name_entry import add_name_entry
        from tools.save_preview_text import add_save_preview
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            add_name_entry(build);before=bytes(build.data);count=len(build.patches)
            report=add_save_preview(build)
        rom,_=build.finish();patches=build.patches[count:]
        self.assertEqual({p['start'] for p in patches},{0x14978,0x149B8,0x14A18,0x14B28,0x52B2C,0x52B38})
        restored=bytearray(rom[:len(before)])
        for p in patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        table=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for slot in (0x18C,0x964):self.assertEqual(table[slot:slot+4],before[START+slot:START+slot+4])
        for row in report['entries']:
            if 'table_offset' in row:
                slot=row['table_offset'];table[slot:slot+4]=before[START+slot:START+slot+4]
        self.assertEqual(table,before[START:END])

    def test_reference_lists_reuse_names_without_mutating_definition_mechanics(self):
        from tools.compact_font import font_snapshot
        from tools.item_text import add_items
        from tools.skill_text import add_skill_info
        from tools.spell_text import add_spell_info
        from tools.reference_list_text import add_reference_lists,SITES
        from tools.rom import ROOT
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            items=add_items(build,extra_catalog=ROOT/'translations/special-items-review.json')
            add_skill_info(build,items);add_spell_info(build)
            before=bytes(build.data);count=len(build.patches);report=add_reference_lists(build)
        rom,_=build.finish();patches=build.patches[count:]
        self.assertEqual({p['start'] for p in patches},{0x207F0,0x20A80,0x20D18,0x20F54}|{r[0] for r in SITES})
        restored=bytearray(rom[:len(before)])
        for p in patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        for copy in report['copies']:
            owned=next(r for r in build.allocations if r['id']==copy['allocation'])
            self.assertEqual(rom[owned['start']:owned['end_exclusive']],before[owned['start']:owned['end_exclusive']])

    def test_town_root_changes_one_width_and_one_private_reader_only(self):
        from tools.town_root_text import add_town_root
        original=load_base();build=RomBuild(original);add_town_root(build);rom,_=build.finish()
        self.assertEqual({p['start'] for p in build.patches},{0x2069A,0x206B8})
        self.assertEqual(rom[0x2069A:0x2069C],bytes.fromhex('0522'))
        restored=bytearray(rom[:len(original)])
        for p in build.patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,original)

    def test_item_loss_owns_only_eight_existing_private_table_literals(self):
        from tools.item_loss_text import add_item_loss,LITERALS
        _,report=self.check_private(add_item_loss,{site:0 for site in LITERALS})
        self.assertEqual({r['table_offset'] for r in report['entries']},{0x1E0,0x1D8,0x34C})
        for row in report['entries']:
            self.assertNotIn('{fit}',row['english'])
            self.assertLessEqual(max(row['maximum_segment_widths']),216)

    def test_direct_player_notices_keep_native_player_controls(self):
        from tools.player_notice_text import add_player_notices,LITERALS
        _,report=self.check_private(add_player_notices,{site:0 for site in LITERALS})
        self.assertEqual({r['table_offset'] for r in report['entries']},{0x47C,0x9C0})
        for row in report['entries']:
            self.assertEqual(bytes.fromhex(row['encoded_hex']).count(b'\x7e'),1)
            self.assertEqual(row['capacity'],'direct-ROM')

    def test_writing_readers_reuse_owned_names_and_preserve_history_mechanics(self):
        from tools.compact_font import font_snapshot
        from tools.item_text import add_items
        from tools.spell_text import add_spell_info
        from tools.writing_text import add_writing,LITERALS
        from tools.rom import ROOT
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            items=add_items(build,extra_catalog=ROOT/'translations/special-items-review.json')
            spells=add_spell_info(build);before=bytes(build.data);count=len(build.patches)
            report=add_writing(build,items,spells)
        rom,_=build.finish();patches=build.patches[count:]
        self.assertEqual({p['start'] for p in patches},set(LITERALS)|{0x26AC4,0x26B58})
        restored=bytearray(rom[:len(before)])
        for p in patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        table=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset'];table[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],256)
            self.assertLessEqual(max(row['maximum_segment_widths']),216)
        self.assertEqual(table,original[START:END])

    def test_scroll_inscription_keeps_ordinary_names_and_item_mechanics(self):
        from tools.compact_font import font_snapshot
        from tools.item_text import add_items
        from tools.scroll_item_text import add_scroll_item
        from tools.extract_items import DEFINITIONS,COUNT
        from tools.rom import ROOT
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            items=add_items(build,extra_catalog=ROOT/'translations/special-items-review.json',reserve_inscription=True)
            before=bytes(build.data);count=len(build.patches);report=add_scroll_item(build,items)
        rom,_=build.finish();patches=build.patches[count:]
        self.assertEqual({p['start'] for p in patches},{0xF328,0xF32C,0xF330,0xF310})
        restored=bytearray(rom[:len(before)])
        for p in patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        self.assertEqual(rom[0xF310:0xF312],bytes.fromhex('0046'))
        self.assertEqual(len(report['entries']),39)
        self.assertEqual(report['maximum_complete_row_bytes'],63)
        for ident in range(COUNT):
            src=DEFINITIONS+24*ident;dst=report['definition_copy_offset']+24*ident
            self.assertEqual(rom[dst+4:dst+24],original[src+4:src+24])
        self.assertEqual(rom[DEFINITIONS:DEFINITIONS+COUNT*24],original[DEFINITIONS:DEFINITIONS+COUNT*24])

    def test_staff_use_only_redirects_two_owned_formats(self):
        from tools.staff_use_text import add_staff_use,LITERALS
        _,report=self.check_private(add_staff_use,{site:0 for site in LITERALS})
        self.assertEqual({r['table_offset'] for r in report['entries']},{0x228,0x3D8})

    def test_monster_interactions_grow_only_the_pull_output_and_private_readers(self):
        from tools.monster_interaction_text import add_monster_interactions,LITERALS
        original=load_base();build=RomBuild(original);report=add_monster_interactions(build);rom,_=build.finish()
        self.assertEqual({p['start'] for p in build.patches},set(LITERALS)|{0x31824,0x3190E})
        restored=bytearray(rom[:len(original)])
        for p in build.patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,original)
        self.assertEqual(rom[0x31824:0x31826],bytes.fromhex('c0b0'))
        self.assertEqual(rom[0x3190E:0x31910],bytes.fromhex('40b0'))
        private=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset'];private[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],256)
            self.assertLessEqual(max(row['maximum_segment_widths']),216)
        self.assertEqual(private,original[START:END])

    def check_private(self,add,owners):
        original=load_base();build=RomBuild(original);report=add(build);rom,_=build.finish()
        self.assertEqual({p['start'] for p in build.patches},set(owners))
        restored=bytearray(rom[:len(original)])
        for site,relative in owners.items():
            self.assertEqual(struct.unpack_from('<I',rom,site)[0],report['table_offset']+relative+0x08000000)
            restored[site:site+4]=original[site:site+4]
        self.assertEqual(restored,original)
        private=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset']
            self.assertEqual(struct.unpack_from('<I',private,slot)[0],row['offset']+0x08000000)
            private[slot:slot+4]=original[START+slot:START+slot+4]
        self.assertEqual(private,original[START:END])
        return rom,report

    def test_battle_result_tables_preserve_all_unowned_sources(self):
        from tools.battle_result_text import add_battle_results,LITERALS
        _,report=self.check_private(add_battle_results,{site:0 for site in LITERALS})
        self.assertEqual({r['table_offset'] for r in report['entries']},{0x7D0,0x898,0x954,0x958,0x82C,0x830})
        for row in report['entries']:
            self.assertLessEqual(max(row['maximum_segment_widths']),216)
            self.assertLessEqual(row['maximum_bytes'],256)

    def test_skill_messages_reuse_definitions_without_changing_mechanics(self):
        from tools.compact_font import font_snapshot
        from tools.skill_text import add_skill_info
        from tools.item_text import add_items
        from tools.skill_message_text import add_skill_messages,TABLE_SITES,NAME_SITES
        from tools.rom import ROOT
        from tools.extract_skills import DEFINITIONS,COUNT,STRIDE
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            skills=add_skill_info(build,add_items(build,extra_catalog=ROOT/'translations/special-items-review.json'));before=bytes(build.data);count=len(build.patches)
            report=add_skill_messages(build,skills)
        rom,_=build.finish();patches=build.patches[count:]
        self.assertEqual({p['start'] for p in patches},set(TABLE_SITES)|set(NAME_SITES))
        restored=bytearray(rom[:len(before)])
        for p in patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        for ident in range(COUNT):
            src=DEFINITIONS+STRIDE*ident;dst=report['definition_copy_offset']+STRIDE*ident
            self.assertEqual(rom[dst+4:dst+STRIDE],original[src+4:src+STRIDE])
        table=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset'];table[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],256)
            self.assertLessEqual(max(row['maximum_segment_widths']),216)
            if slot==0x754:self.assertTrue(bytes.fromhex(row['encoded_hex']).endswith(b'\x09\0'))
        self.assertEqual(table,original[START:END])

    def test_spell_message_tables_preserve_all_mechanics_and_unowned_sources(self):
        from tools.compact_font import font_snapshot
        from tools.spell_text import add_spell_info
        from tools.spell_message_text import add_spell_messages,LITERALS,DEFINITION_LITERALS
        from tools.extract_spells import DEFINITIONS,COUNT
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            spells=add_spell_info(build);before=bytes(build.data);count=len(build.patches)
            report=add_spell_messages(build,spells)
        rom,_=build.finish();patches=build.patches[count:]
        self.assertEqual({p['start'] for p in patches},set(LITERALS)|set(DEFINITION_LITERALS))
        restored=bytearray(rom[:len(before)])
        for p in patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        for ident in range(COUNT):
            src=DEFINITIONS+12*ident;dst=report['definition_copy_offset']+12*ident
            self.assertEqual(rom[dst+4:dst+12],original[src+4:src+12])
        table=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset'];table[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],256)
            self.assertLessEqual(max(row['maximum_segment_widths']),216)
        self.assertEqual(table,original[START:END])

    def test_spell_inscription_redirects_only_its_kind_format_and_owned_names(self):
        from tools.compact_font import font_snapshot
        from tools.spell_text import add_spell_info
        from tools.spell_item_text import add_spell_item
        from tools.extract_spells import DEFINITIONS,DESCRIPTIONS
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            spells=add_spell_info(build);before=bytes(build.data);count=len(build.patches)
            report=add_spell_item(build,spells)
        rom,_=build.finish();patches=build.patches[count:]
        self.assertEqual({p['start'] for p in patches},{0xF2E8,0xF2EC,0xF2F4})
        restored=bytearray(rom[:len(before)])
        for p in patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        self.assertEqual(rom[DEFINITIONS:DESCRIPTIONS],original[DEFINITIONS:DESCRIPTIONS])
        self.assertEqual(rom[0xF310:0xF312],original[0xF310:0xF312])
        self.assertEqual(report['maximum_complete_row_bytes'],63)
        table=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        table[0x84C:0x850]=original[START+0x84C:START+0x850]
        self.assertEqual(table,original[START:END])

    def test_discovery_readers_preserve_other_shared_consumers_and_frames(self):
        from tools.discovery_message_text import add_discovery_messages,LITERALS
        rom,report=self.check_private(add_discovery_messages,{site:0 for site in LITERALS})
        self.assertEqual(len(report['entries']),7)
        self.assertEqual({r['table_offset'] for r in report['entries']},set.union(*LITERALS.values()))
        for row in report['entries']:
            self.assertLessEqual(row['maximum_bytes'],256)
            self.assertLessEqual(max(row['maximum_segment_widths']),216)

    def test_actor_status_readers_keep_unrelated_shared_slots_original(self):
        from tools.status_effect_text import add_status_effects,LITERALS
        rom,report=self.check_private(add_status_effects,{site:0 for site in LITERALS})
        self.assertEqual(len(report['entries']),9)
        self.assertEqual({r['table_offset'] for r in report['entries']},set.union(*LITERALS.values()))

    def test_fullness_only_redirects_its_three_native_decimal_readers(self):
        from tools.fullness_text import add_fullness,LITERALS
        rom,report=self.check_private(add_fullness,{site:0 for site in LITERALS})
        self.assertEqual(len(report['entries']),1)
        self.assertEqual(report['entries'][0]['table_offset'],0xD0)

    def test_bonus_effect_item_copy_preserves_every_gameplay_byte(self):
        from tools.compact_font import font_snapshot
        from tools.item_text import add_items
        from tools.floor_buff_text import add_floor_buffs
        from tools.extract_items import DEFINITIONS,COUNT
        from tools.rom import ROOT
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            items=add_items(build,extra_catalog=ROOT/'translations/special-items-review.json')
            before=bytes(build.data);patches=len(build.patches)
            report=add_floor_buffs(build,items)
        rom,_=build.finish();new=build.patches[patches:]
        self.assertEqual({p['start'] for p in new},{0x33548,0x33550})
        restored=bytearray(rom[:len(before)])
        for p in new:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,before)
        names={int(r['id'].rsplit('.',1)[1]):r for r in items['entries'] if r['id'].startswith('item.name.')}
        self.assertEqual(set(names),set(range(COUNT)))
        for ident in range(COUNT):
            src=DEFINITIONS+ident*24;dst=report['definition_copy_offset']+ident*24
            self.assertEqual(rom[dst+4:dst+24],original[src+4:src+24])
            self.assertEqual(struct.unpack_from('<I',rom,dst)[0],names[ident]['offset']+0x08000000)
        self.assertEqual(rom[DEFINITIONS:DEFINITIONS+COUNT*24],original[DEFINITIONS:DEFINITIONS+COUNT*24])

    def test_priest_companion_costs_and_original_code_remain_owned_by_original(self):
        from tools.priest_text import add_priest,LITERALS
        rom,report=self.check_private(add_priest,{site:0 for site in LITERALS})
        original=load_base()
        self.assertEqual(rom[0x1AB3C:0x1AB40],original[0x1AB3C:0x1AB40])
        self.assertEqual(rom[0x144B24:0x144B2E],original[0x144B24:0x144B2E])
        self.assertEqual(len(report['entries']),25)

    def test_projectile_interior_pointer_and_unrelated_actions_are_preserved(self):
        from tools.projectile_text import add_projectiles,OWNERS
        rom,report=self.check_private(add_projectiles,OWNERS)
        original=load_base()
        self.assertEqual(rom[0x25AC0:0x25AC4],original[0x25AC0:0x25AC4])
        self.assertEqual(rom[0x26400:0x26760],original[0x26400:0x26760])
        self.assertEqual(len(report['entries']),5)

    def test_companion_floor_table_leaves_priest_and_other_slots_unchanged(self):
        from tools.companion_text import add_companion
        rom,report=self.check_private(add_companion,{0x1AB3C:0})
        original=load_base()
        self.assertEqual(rom[0x1AB40:0x1AB48],original[0x1AB40:0x1AB48])
        self.assertEqual(rom[0x1AB8C:0x1AB90],original[0x1AB8C:0x1AB90])
        self.assertEqual([r['floor'] for r in report['entries']],list(range(1,7)))

    def test_recovery_only_redirects_owned_formatted_branches(self):
        from tools.recovery_text import add_recovery,LITERALS
        rom,report=self.check_private(add_recovery,{site:0 for site in LITERALS})
        original=load_base()
        for site in (0x13DEC,0x13E6C,0x40DFC):
            self.assertEqual(rom[site:site+4],original[site:site+4])
        self.assertEqual({r['table_offset'] for r in report['entries']},{0x120,0x124,0x210})

    def test_every_nonzero_monster_selector_has_one_private_announcement(self):
        from tools.monster_announcement_text import add_monster_announcements,selectors
        from tools.extract_monsters import RESOURCE
        rom,report=self.check_private(add_monster_announcements,{0x2AA54:0,0x2AC2C:0})
        original=load_base();selected=selectors(original)
        self.assertEqual({i:row['table_offset'] for row in report['entries'] for i in row['actor_ids']},selected)
        self.assertEqual((len(selected),len(report['entries'])),(45,24))
        self.assertEqual(rom[RESOURCE:0x47CE7D],original[RESOURCE:0x47CE7D])

    def test_spell_copies_preserve_mechanics_lookup_tail_and_original_consumers(self):
        from tools.compact_font import font_snapshot
        from tools.spell_text import add_spell_info
        from tools.spell_menu_text import add_spell_menu
        from tools.extract_spells import DEFINITIONS,DESCRIPTIONS,COUNT
        original=load_base();build=RomBuild(original)
        with font_snapshot():
            info=add_spell_info(build);menu=add_spell_menu(build,info)
        rom,_=build.finish();restored=bytearray(rom[:len(original)])
        expected={0x228CC,0x228D0,0x228D8,0x225C8,0x22600,0x225D8,0x2261C,0x226DC,0x22760,0x225E0,0x22604,0x22620}
        self.assertEqual({p['start'] for p in build.patches},expected)
        for site in expected:restored[site:site+4]=original[site:site+4]
        self.assertEqual(restored,original)
        copies=[next(r['offset'] for r in info['copies'] if r['id']=='definitions'),menu['definition_copy_offset']]
        for offset in copies:
            for ident in range(COUNT):
                src=DEFINITIONS+12*ident;dst=offset+12*ident
                self.assertEqual(rom[dst+4:dst+12],original[src+4:src+12])
                row=next(r for r in info['entries'] if r['id']==f'spell.name.{ident}')
                self.assertEqual(struct.unpack_from('<I',rom,dst)[0],row['offset']+0x08000000)
        tail=menu['definition_copy_offset']+12*COUNT
        self.assertEqual(rom[tail:menu['definition_copy_offset']+128*12],original[DESCRIPTIONS:DEFINITIONS+128*12])
        self.assertEqual(rom[0xF2F4:0xF2F8],original[0xF2F4:0xF2F8])

    def test_soldier_selector_copy_changes_only_its_a_action_owner(self):
        from tools.soldier_text import add_soldiers
        _,report=self.check_private(add_soldiers,{0x24378:0})
        self.assertEqual({r['table_offset'] for r in report['entries']},set(range(0x800,0x81C,4)))

    def test_item_theft_and_wait_leave_gold_theft_and_native_transfer_code_original(self):
        from tools.item_theft_text import add_item_theft,LITERALS
        rom,report=self.check_private(add_item_theft,{site:0 for site in LITERALS})
        original=load_base()
        for site in (0x2BD38,0x2BD84,0x2BE58,0x2C0E0,0x2C0E4,0x2C0E8):
            self.assertEqual(rom[site:site+4],original[site:site+4])
        self.assertEqual({r['table_offset'] for r in report['entries']},{0x2AC,0x2B0,0x2B8,0x710,0x718})

    def test_skill_info_preserves_mechanics_and_redirects_only_owned_readers(self):
        from tools.compact_font import font_snapshot,encode
        from tools.skill_text import add_skill_info
        from tools.skill_menu_text import add_skill_menu,DEFINITION_SITES,TABLE_SITES
        from tools.extract_skills import DEFINITIONS,COUNT,STRIDE
        original=load_base();build=RomBuild(original)
        names=[]
        for ident in range(48):
            offset=build.allocate(f'test-item-{ident}',encode('Equipment'),'test-equipment')
            names.append({'id':f'item.name.{ident}','offset':offset})
        with font_snapshot():
            info=add_skill_info(build,{'entries':names});add_skill_menu(build,info)
        rom,_=build.finish();restored=bytearray(rom[:len(original)])
        expected={0x2184C,0x21854,0x21850,0x21888,0x2185C,0x21864,0x218E4,0x2182E}
        expected.update(DEFINITION_SITES);expected.update(TABLE_SITES)
        expected.update((0x213BC,0x21DF8,0x21E1C,0x21E38,0x21E58,0x215F4))
        self.assertEqual({p['start'] for p in build.patches},expected)
        for site in expected:
            size=8 if site==0x2182E else 4
            restored[site:site+size]=original[site:site+size]
        self.assertEqual(restored,original)
        definitions=next(r['offset'] for r in info['copies'] if r['id']=='definitions')
        for ident in range(COUNT):
            src=DEFINITIONS+STRIDE*ident;dst=definitions+STRIDE*ident
            self.assertEqual(rom[dst+4:dst+STRIDE],original[src+4:src+STRIDE])
        # Decode the replacement Thumb BL independently: it must call native
        # strcpy, then execute two NOPs in the old fixed9-byte copy region.
        hi,lo=struct.unpack_from('<HH',rom,0x2182E)
        displacement=((hi&0x7FF)<<12)|((lo&0x7FF)<<1)
        if displacement&(1<<22):displacement-=1<<23
        self.assertEqual(0x21832+displacement,0x5CF54)
        self.assertEqual(rom[0x21832:0x21836],bytes.fromhex('c046c046'))

    def test_staff_effect_frame_growth_preserves_dispatch_and_shared_sources(self):
        from tools.dungeon_leaf_text import add_dungeon_leaves,LITERALS
        from tools.compact_font import font_snapshot
        original=load_base();build=RomBuild(original)
        with font_snapshot():info=add_dungeon_leaves(build)
        rom,_=build.finish();restored=bytearray(rom[:len(original)])
        expected=set(LITERALS)|{0x37D86,0x38428}
        self.assertEqual({p['start'] for p in build.patches},expected)
        for site in expected:
            size=2 if site in (0x37D86,0x38428) else 4
            restored[site:site+size]=original[site:site+size]
        self.assertEqual(restored,original)
        push,pop=(struct.unpack_from('<H',rom,site)[0] for site in (0x37D86,0x38428))
        self.assertEqual((push&0xFF80,pop&0xFF80),(0xB080,0xB000))
        self.assertEqual((push&0x7F)*4,(pop&0x7F)*4)
        self.assertEqual((push&0x7F)*4-4,256)
        private=bytearray(rom[info['table_offset']:info['table_offset']+END-START])
        for row in info['entries']:
            slot=row['table_offset'];private[slot:slot+4]=original[START+slot:START+slot+4]
        self.assertEqual(private,original[START:END])
