"""Build the cumulative English ROM from the pinned Japanese base and source assets."""

import argparse
import json
from pathlib import Path
import struct
import tempfile

from tools.bps import create_patch
from tools.build_compact_font import add_font
from tools.build_dialogue import add_dialogue
from tools.compact_font import encode
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


def build_rom(include_story=True, include_extra_consumers=True):
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
    ui = add_ui(build)
    items = add_items(build)
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
    results = {'entries': [], 'formats': [], 'causes': [], 'history_zero_actor': None, 'other_defeat': None}
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
                  reviewed_resource_counts=resource_counts,
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
