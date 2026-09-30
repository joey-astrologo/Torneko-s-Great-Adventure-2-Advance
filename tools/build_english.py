"""Build the cumulative English ROM from the pinned Japanese base and source assets."""

import argparse
import json
from pathlib import Path
import struct
import tempfile

from tools.bps import create_patch
from tools.build_compact_font import add_font
from tools.build_dialogue import add_dialogue
from tools.compact_font import encode, with_font_snapshot
from tools.name_entry import add_name_entry
from tools.menu_text import add_menus
from tools.service_ui import add_ui
from tools.item_text import add_items
from tools.monster_text import add_monsters
from tools.combat_text import add_combat
from tools.review_fonts import LABEL_OFFSET, LABEL_POINTER
from tools.rom import ROOT, default_rom, load_base
from tools.rom_build import RomBuild

OUTPUT = ROOT / 'build/english'


@with_font_snapshot
def build_rom(include_story=True, include_extra_consumers=True, include_arrival_art=True, include_title_art=True):
    from tools.audit_terminology import validate
    validate()
    build = RomBuild(load_base())
    font = add_font(build, compact_numbers=True)
    names = add_name_entry(build)
    label = build.allocate('opening-start-label', encode(' Start adventure'), 'opening-menu')
    build.patch('opening-start-pointer', LABEL_POINTER, struct.pack('<I', 0x08000000 + LABEL_OFFSET),
                struct.pack('<I', 0x08000000 + label), 'opening-menu')
    dialogue = add_dialogue(build, include_story=include_story)
    menus = add_menus(build)
    ui = add_ui(build, extra_catalog=ROOT/'translations/options-help-review.json')
    items = add_items(build, extra_catalog=ROOT/'translations/special-items-review.json', reserve_inscription=include_extra_consumers)
    scroll_item = {'entries': []}
    if include_extra_consumers:
        from tools.scroll_item_text import add_scroll_item
        scroll_item = add_scroll_item(build, items)
    monsters = add_monsters(build)
    combat = add_combat(build)
    from tools.player_status_text import add_player_status
    player_status = add_player_status(build)
    aliases = player_effects = item_use = {'entries': []}
    player_conditions = inventory_actions = pickup = swap = {'entries': []}
    containers = town_actions = {'entries': [], 'labels': []}
    child_actions = {}
    player_messages = blacksmith = {'entries': []}
    gaibara = selection_prompt = {'entries': []}
    remi = {'entries': [], 'warp_names': {'entries': []}}
    mayor = well_picker = hunger = status_traps = {'entries': []}
    warp_trap = unequip_trap = mud_trap = damage_traps = rust = {'entries': []}
    summon_trap = blast_traps = pitfall = {'entries': []}
    bear_trap = stumble_trap = curse = drain = level_drain = steal_gold = {'entries': []}
    monster_conditions = {'entries': []}
    history = history_menu = records = password = {'entries': []}
    priest = projectiles = monster_announcements = companion = {'entries': []}
    recovery = soldiers = spell_info = spell_menu = {'entries': []}
    item_theft = skill_info = skill_menu = {'entries': []}
    dungeon_leaves = floor_buffs = fullness = status_effects = {'entries': []}
    spell_item = spell_messages = discovery_messages = monster_interactions = staff_use = writing = item_loss = player_notices = skill_messages = battle_results = {'entries': []}
    results = {'entries': [], 'formats': [], 'causes': [], 'history_zero_actor': None, 'other_defeat': None}
    dungeon_shop = save_notices = reference_lists = priest_warning = save_preview = town_root = {'entries': []}
    writing_input = cannot_talk = step_stairs = pot_view = {'entries': []}
    fused_loss = {'entries': [], 'abilities': []}
    book_travel = {'entries': []}
    ability_info = dungeon_story = empty_read = {'entries': []}
    travel_gate = ending_text = dungeon_travel = tutorial_help = {'entries': []}
    link_text = ending_notice = pickup_help = {'entries': []}
    carpenter = fire_scene = travel_confirm = town_routes = form_refusal = ground_remove = monster_identity = {'entries': []}
    if include_extra_consumers:
        from tools.item_alias_text import add_aliases
        from tools.player_effect_text import add_effects
        from tools.item_use_text import add_item_use
        from tools.player_condition_text import add_conditions
        from tools.inventory_action_text import add_actions
        from tools.pickup_text import add_pickup
        aliases = add_aliases(build)
        player_effects = add_effects(build)
        item_use = add_item_use(build)
        player_conditions = add_conditions(build)
        inventory_actions = add_actions(build)
        pickup = add_pickup(build)
        from tools.swap_text import add_swap
        from tools.container_text import add_containers
        from tools.child_action_text import add_child_actions
        from tools.town_item_text import add_town_actions
        swap = add_swap(build)
        containers = add_containers(build)
        child_actions = add_child_actions(build)
        town_actions = add_town_actions(build)
        from tools.player_message_text import add_player_messages
        from tools.blacksmith_text import add_blacksmith
        player_messages = add_player_messages(build)
        blacksmith = add_blacksmith(build)
        from tools.gaibara_text import add_gaibara
        from tools.selection_prompt_text import add_selection_prompt
        from tools.remi_text import add_remi
        gaibara = add_gaibara(build)
        selection_prompt = add_selection_prompt(build)
        remi = add_remi(build)
        from tools.mayor_text import add_mayor
        from tools.well_picker_text import add_well_picker
        from tools.hunger_text import add_hunger
        from tools.status_trap_text import add_status_traps
        mayor = add_mayor(build)
        well_picker = add_well_picker(build, remi)
        hunger = add_hunger(build)
        status_traps = add_status_traps(build)
        from tools.warp_trap_text import add_warp_trap
        warp_trap = add_warp_trap(build)
        from tools.unequip_trap_text import add_unequip_trap
        unequip_trap = add_unequip_trap(build)
        from tools.mud_trap_text import add_mud_trap
        mud_trap = add_mud_trap(build)
        from tools.damage_trap_text import add_damage_traps
        damage_traps = add_damage_traps(build)
        from tools.rust_text import add_rust
        rust = add_rust(build)
        from tools.summon_trap_text import add_summon_trap
        from tools.blast_trap_text import add_blast_traps
        from tools.pitfall_text import add_pitfall
        summon_trap = add_summon_trap(build)
        blast_traps = add_blast_traps(build)
        pitfall = add_pitfall(build)
        from tools.bear_trap_text import add_bear_trap
        bear_trap = add_bear_trap(build)
        from tools.stumble_trap_text import add_stumble_trap
        stumble_trap = add_stumble_trap(build)
        from tools.curse_text import add_curse
        curse = add_curse(build)
        from tools.drain_text import add_drain
        drain = add_drain(build)
        from tools.level_drain_text import add_level_drain
        level_drain = add_level_drain(build)
        from tools.steal_gold_text import add_steal_gold
        steal_gold = add_steal_gold(build)
        from tools.monster_condition_text import add_monster_conditions
        monster_conditions = add_monster_conditions(build)
        from tools.result_text import add_results
        results = add_results(build)
        from tools.history_text import add_history
        from tools.history_menu_text import add_history_menu
        history = add_history(build)
        history_menu = add_history_menu(build)
        from tools.records_text import add_records
        from tools.password_text import add_password
        records = add_records(build)
        password = add_password(build)
        from tools.priest_text import add_priest
        from tools.projectile_text import add_projectiles
        from tools.monster_announcement_text import add_monster_announcements
        from tools.companion_text import add_companion
        priest = add_priest(build)
        projectiles = add_projectiles(build)
        monster_announcements = add_monster_announcements(build)
        companion = add_companion(build)
        from tools.recovery_text import add_recovery
        from tools.soldier_text import add_soldiers
        from tools.spell_text import add_spell_info
        from tools.spell_menu_text import add_spell_menu
        recovery = add_recovery(build)
        soldiers = add_soldiers(build)
        spell_info = add_spell_info(build)
        spell_menu = add_spell_menu(build, spell_info)
        from tools.spell_item_text import add_spell_item
        from tools.spell_message_text import add_spell_messages
        spell_item = add_spell_item(build, spell_info)
        spell_messages = add_spell_messages(build, spell_info)
        from tools.writing_text import add_writing
        writing = add_writing(build, items, spell_info)
        from tools.item_theft_text import add_item_theft
        from tools.skill_text import add_skill_info
        from tools.skill_menu_text import add_skill_menu
        item_theft = add_item_theft(build)
        skill_info = add_skill_info(build, items)
        from tools.skill_message_text import add_skill_messages
        skill_messages = add_skill_messages(build, skill_info)
        from tools.battle_result_text import add_battle_results
        battle_results = add_battle_results(build)
        skill_menu = add_skill_menu(build, skill_info)
        from tools.dungeon_leaf_text import add_dungeon_leaves
        from tools.floor_buff_text import add_floor_buffs
        from tools.fullness_text import add_fullness
        from tools.status_effect_text import add_status_effects
        dungeon_leaves = add_dungeon_leaves(build)
        floor_buffs = add_floor_buffs(build, items)
        fullness = add_fullness(build)
        status_effects = add_status_effects(build)
        from tools.item_loss_text import add_item_loss
        from tools.player_notice_text import add_player_notices
        item_loss = add_item_loss(build)
        player_notices = add_player_notices(build)
        from tools.staff_use_text import add_staff_use
        staff_use = add_staff_use(build)
        from tools.monster_interaction_text import add_monster_interactions
        monster_interactions = add_monster_interactions(build)
        from tools.discovery_message_text import add_discovery_messages
        discovery_messages = add_discovery_messages(build)
        from tools.dungeon_shop_text import add_dungeon_shop
        from tools.save_notice_text import add_save_notices
        from tools.reference_list_text import add_reference_lists
        from tools.priest_warning_text import add_priest_warning
        from tools.save_preview_text import add_save_preview
        from tools.town_root_text import add_town_root
        dungeon_shop = add_dungeon_shop(build)
        save_notices = add_save_notices(build)
        reference_lists = add_reference_lists(build)
        priest_warning = add_priest_warning(build)
        save_preview = add_save_preview(build)
        town_root = add_town_root(build)
        from tools.writing_input import add_input
        from tools.fused_loss_text import add_fused_loss
        from tools.cannot_talk_text import add_cannot_talk
        from tools.step_stairs_text import add_step_stairs
        from tools.pot_view_text import add_pot_view
        writing_input=add_input(build)
        fused_loss=add_fused_loss(build)
        cannot_talk=add_cannot_talk(build)
        step_stairs=add_step_stairs(build)
        pot_view=add_pot_view(build)
        from tools.book_travel_text import add_book_travel
        book_travel=add_book_travel(build)
        from tools.ability_info_text import add_ability_info
        from tools.dungeon_story_text import add_dungeon_story
        from tools.empty_read_text import add_empty_read
        ability_info=add_ability_info(build)
        dungeon_story=add_dungeon_story(build)
        empty_read=add_empty_read(build)
        from tools.travel_gate_text import add_travel_gate
        travel_gate=add_travel_gate(build)
        from tools.ending_text import add_ending
        ending_text=add_ending(build)
        from tools.dungeon_travel_text import add_dungeon_travel
        dungeon_travel=add_dungeon_travel(build)
        from tools.tutorial_help_text import add_tutorial_help
        tutorial_help=add_tutorial_help(build)
        from tools.link_text import add_link_text
        link_text=add_link_text(build)
        from tools.ending_notice_text import add_ending_notice
        ending_notice=add_ending_notice(build)
        from tools.pickup_help_text import add_pickup_help
        pickup_help=add_pickup_help(build)
        from tools.carpenter_text import add_carpenter
        carpenter=add_carpenter(build)
        from tools.fire_scene_text import add_fire_scene
        fire_scene=add_fire_scene(build)
        from tools.travel_confirm_text import add_travel_confirm
        travel_confirm=add_travel_confirm(build)
        from tools.town_routes_text import add_town_routes
        town_routes=add_town_routes(build)
        from tools.form_refusal_text import add_form_refusal
        form_refusal=add_form_refusal(build)
        from tools.ground_remove_text import add_ground_remove
        ground_remove=add_ground_remove(build)
        from tools.monster_identity_text import add_monster_identity
        monster_identity=add_monster_identity(build)
    location_banner = None
    if include_extra_consumers:
        from tools.location_banner import add_location_banner
        location_banner = add_location_banner(build, results)
    arrival_cards = None
    if include_arrival_art:
        from tools.arrival_art import add_arrival_art
        arrival_cards = add_arrival_art(build)
    title_art = None
    if include_title_art:
        from tools.title_art import add_title_art
        title_art = add_title_art(build)
    data, report = build.finish()
    resource_counts = {
        'dialogue': len(dialogue['entries']), 'menus': len(menus['entries']),
        'ui': len(ui['entries']), 'items': len(items['entries']),
        'actor_names': len(monsters['entries']), 'combat': len(combat['entries']),
        'queue_notices': len(combat['queue_notices']['entries']),
        'bank': len(dialogue['town_resource']['service_entries']),
        'storage': len(dialogue['town_resource']['storage_entries']),
        'bakery': len(dialogue['town_resource']['bakery_entries']),
        'player_status': len(player_status['entries']),
        'item_appearances': len(aliases['entries']),
        'player_effects': len(player_effects['entries']),
        'item_use': len(item_use['entries']),
        'player_conditions': len(player_conditions['entries']),
        'inventory_actions': len(inventory_actions['entries']),
        'pickup': len(pickup['entries']),
        'swap': len(swap['entries']),
        'containers': len(containers['entries'])+len(containers['labels']),
        'town_actions': len(town_actions['entries'])+len(town_actions['labels']),
        'player_messages': len(player_messages['entries']),
        'blacksmith': len(blacksmith['entries']),
        'gaibara': len(gaibara['entries']),
        'selection_prompt': len(selection_prompt['entries']),
        'remi': len(remi['entries']) + len(remi['warp_names']['entries']),
        'mayor': len(mayor['entries']),
        'well_picker': len(well_picker['entries']),
        'hunger': len(hunger['entries']),
        'status_traps': len(status_traps['entries']),
        'warp_trap': len(warp_trap['entries']),
        'unequip_trap': len(unequip_trap['entries']),
        'mud_trap': len(mud_trap['entries']),
        'damage_traps': len(damage_traps['entries']),
        'rust': len(rust['entries']),
        'summon_trap': len(summon_trap['entries']),
        'blast_traps': len(blast_traps['entries']),
        'pitfall': len(pitfall['entries']),
        'bear_trap': len(bear_trap['entries']),
        'stumble_trap': len(stumble_trap['entries']),
        'curse': len(curse['entries']),
        'drain': len(drain['entries']),
        'level_drain': len(level_drain['entries']),
        'steal_gold': len(steal_gold['entries']),
        'monster_conditions': len(monster_conditions['entries']),
        'results': len(results['entries']) + len(results['formats']) + len(results['causes']) + bool(results['other_defeat']) + bool(results['history_zero_actor']) + len(results.get('ui_entries', [])),
        'history': len(history['entries']),
        'history_menu': len(history_menu['entries']),
        'records': len(records['entries']),
        'password': len(password['entries']),
        'priest': len(priest['entries']),
        'projectiles': len(projectiles['entries']),
        'monster_announcements': len(monster_announcements['entries']),
        'companion': len(companion['entries']),
        'recovery': len(recovery['entries']),
        'soldiers': len(soldiers['entries']),
        'spell_info': len(spell_info['entries']),
        'spell_menu': len(spell_menu['entries']),
        'spell_item': len(spell_item['entries']),
        'spell_messages': len(spell_messages['entries']),
        'discovery_messages': len(discovery_messages['entries']),
        'monster_interactions': len(monster_interactions['entries']),
        'staff_use': len(staff_use['entries']),
        'scroll_item': len(scroll_item['entries']),
        'writing': len(writing['entries']),
        'item_loss': len(item_loss['entries']),
        'player_notices': len(player_notices['entries']),
        'skill_messages': len(skill_messages['entries']),
        'battle_results': len(battle_results['entries']),
        'dungeon_shop': len(dungeon_shop['entries']),
        'save_notices': len(save_notices['entries']),
        'reference_lists': len(reference_lists['entries']),
        'priest_warning': len(priest_warning['entries']),
        'save_preview': len(save_preview['entries']),
        'town_root': len(town_root['entries']),
        'writing_input': len(writing_input['entries']),
        'fused_loss': len(fused_loss['entries'])+len(fused_loss['abilities']),
        'cannot_talk': len(cannot_talk['entries']),
        'step_stairs': len(step_stairs['entries']),
        'pot_view': len(pot_view['entries']),
        'book_travel': len(book_travel['entries']),
        'ability_info': len(ability_info['entries']),
        'dungeon_story': len(dungeon_story['entries']),
        'empty_read': len(empty_read['entries']),
        'travel_gate': len(travel_gate['entries']),
        'ending_text': len(ending_text['entries']),
        'dungeon_travel': len(dungeon_travel['entries']),
        'tutorial_help': len(tutorial_help['entries']),
        'link_text': len(link_text['entries']),
        'ending_notice': len(ending_notice['entries']),
        'pickup_help': len(pickup_help['entries']),
        'carpenter': len(carpenter['entries']),
        'fire_scene': len(fire_scene['entries']),
        'travel_confirm': len(travel_confirm['entries']),
        'town_routes': len(town_routes['entries']),
        'form_refusal': len(form_refusal['entries']),
        'ground_remove': len(ground_remove['entries']),
        'monster_identity': len(monster_identity['entries']),

        'item_theft': len(item_theft['entries']),
        'skill_info': len(skill_info['entries']),
        'skill_menu': len(skill_menu['entries']),
        'dungeon_leaves': len(dungeon_leaves['entries']),
        'floor_buffs': len(floor_buffs['entries']),
        'fullness': len(fullness['entries']),
        'status_effects': len(status_effects['entries']),
        'well_level_labels': len(dialogue['story_consumers'].get('well_level',{}).get('labels',[])),
    }
    report.update(font=font, name_entry=names, dialogue=dialogue, menus=menus, ui=ui, items=items, monsters=monsters, combat=combat, player_status=player_status,
                  aliases=aliases, player_effects=player_effects, item_use=item_use,
                  player_conditions=player_conditions, inventory_actions=inventory_actions, pickup=pickup,
                  swap=swap, containers=containers, child_actions=child_actions, town_actions=town_actions,
                  player_messages=player_messages, blacksmith=blacksmith,
                  gaibara=gaibara, selection_prompt=selection_prompt, remi=remi,
                  mayor=mayor, well_picker=well_picker, hunger=hunger, status_traps=status_traps,
                  warp_trap=warp_trap, unequip_trap=unequip_trap, mud_trap=mud_trap, damage_traps=damage_traps, rust=rust,
                  summon_trap=summon_trap, blast_traps=blast_traps, pitfall=pitfall,
                  bear_trap=bear_trap, stumble_trap=stumble_trap, curse=curse, drain=drain, level_drain=level_drain, steal_gold=steal_gold,
                  monster_conditions=monster_conditions, results=results, history=history, history_menu=history_menu, records=records, password=password,
                  priest=priest, projectiles=projectiles, monster_announcements=monster_announcements, companion=companion,
                  recovery=recovery, soldiers=soldiers, spell_info=spell_info, spell_menu=spell_menu, spell_item=spell_item, spell_messages=spell_messages,
                  item_theft=item_theft, skill_info=skill_info, skill_menu=skill_menu,
                  dungeon_leaves=dungeon_leaves, floor_buffs=floor_buffs, fullness=fullness, status_effects=status_effects, discovery_messages=discovery_messages, monster_interactions=monster_interactions, staff_use=staff_use, scroll_item=scroll_item, writing=writing, item_loss=item_loss, player_notices=player_notices, skill_messages=skill_messages, battle_results=battle_results,
                  reviewed_resource_counts=resource_counts,
                  dungeon_shop=dungeon_shop, save_notices=save_notices, reference_lists=reference_lists,
                  priest_warning=priest_warning, save_preview=save_preview, town_root=town_root,
                  writing_input=writing_input, fused_loss=fused_loss, cannot_talk=cannot_talk, step_stairs=step_stairs, pot_view=pot_view, book_travel=book_travel, ability_info=ability_info, dungeon_story=dungeon_story, empty_read=empty_read,
                  travel_gate=travel_gate, ending_text=ending_text, dungeon_travel=dungeon_travel, tutorial_help=tutorial_help,
                  link_text=link_text, ending_notice=ending_notice, pickup_help=pickup_help,
                  carpenter=carpenter, fire_scene=fire_scene, travel_confirm=travel_confirm, town_routes=town_routes, form_refusal=form_refusal, ground_remove=ground_remove, monster_identity=monster_identity,
                  arrival_cards=arrival_cards, title_art=title_art, location_banner=location_banner,
                  total_reviewed_inserted_graphics=(arrival_cards['english_graphic_count'] if arrival_cards else 0)+(title_art['english_graphic_count'] if title_art else 0),
                  total_reviewed_inserted_resources=sum(resource_counts.values()),
                  scope="Cumulative English text build with original early-menu geometry, matching compact numbers and approved spacing. Includes private unidentified-item appearances, player-only effects and conditional one-line item-use announcements. Resource counts describe insertion, not whole-game coverage. Native acceptance distinguishes ordinary play from controlled rendering and state probes. Remaining combat, story/item/system consumers, custom names, inscriptions, special definitions, later modes and artwork remain open.")
    report.update(dialogue['story_consumers'])
    return data, report


def run(output=OUTPUT):
    data, report = build_rom()
    output.mkdir(parents=True, exist_ok=True)
    rom = output / 'torneko-2-english.gba'
    report['output_rom'] = str(rom.relative_to(ROOT)) if rom.is_relative_to(ROOT) else str(rom)
    # Verify a complete staged build before replacing generated files. Existing
    # playtest saves and research output in this directory are never removed.
    with tempfile.TemporaryDirectory(prefix='.staging-', dir=output) as directory:
        staged = Path(directory)
        staged_rom = staged / rom.name
        staged_rom.write_bytes(data)
        report['bps'] = create_patch(default_rom(), staged_rom, staged / 'torneko-2-english.bps')
        (staged / 'name-helpers.asm').write_text(report['name_entry']['helpers_source'])
        (staged / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
        for name in (rom.name, 'torneko-2-english.bps', 'name-helpers.asm', 'build.json'):
            (staged / name).replace(output / name)
    print(rom)
    if output.resolve() == OUTPUT.resolve():
        from tools.export_release import run as export_release
        export_release()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output.resolve())
