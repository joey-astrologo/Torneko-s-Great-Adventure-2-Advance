#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
.venv/bin/python -m tools.audit_terminology
.venv/bin/python -m tools.build_english
.venv/bin/python -m tools.verify_name_entry
.venv/bin/python -m tools.verify_opening_dialogue
.venv/bin/python -m tools.verify_first_dungeon
.venv/bin/python -m tools.verify_castle_arrival
.venv/bin/python -m tools.verify_castle_conversations
.venv/bin/python -m tools.verify_destination_menu
# Recreate the Japanese bank-one context from verify_name_entry's native save;
# native acceptance must also work without historical research checkpoints.
.venv/bin/python -m tools.trace_first_dungeon --castle --output build/english/home-validation/japanese-castle
.venv/bin/python -m tools.trace_destination_menu --fixture build/english/home-validation/japanese-castle/castle --output build/english/home-validation/japanese-destination
.venv/bin/python -m tools.trace_home_return --fixture build/english/home-validation/japanese-destination/home-menu --output build/english/home-validation/japanese-home
.venv/bin/python -m tools.verify_home_return --japanese-fixture build/english/home-validation/japanese-home/village
.venv/bin/python -m tools.trace_home_books --fixture build/english/home-validation/japanese-home/village --output build/english/books-validation/japanese
.venv/bin/python -m tools.verify_town_text
.venv/bin/python -m tools.verify_home_books
.venv/bin/python -m tools.trace_mansion
.venv/bin/python -m tools.verify_mansion
.venv/bin/python -m tools.verify_quest_text
.venv/bin/python -m tools.verify_prose_preflight --cumulative
.venv/bin/python -m tools.research_event_relocation --cumulative
.venv/bin/python -m tools.verify_floor_progress_prototype --cumulative
.venv/bin/python -m tools.verify_well_level_prototype --cumulative
.venv/bin/python -m tools.verify_village_prose_prototype --cumulative
.venv/bin/python -m tools.verify_medal_prototype --cumulative
.venv/bin/python -m tools.verify_story_command_prototype --cumulative
.venv/bin/python -m tools.extract_monsters
.venv/bin/python -m tools.verify_monster_resource --cumulative
.venv/bin/python -m tools.verify_actor_levels --cumulative
.venv/bin/python -m tools.verify_combat_prototype --cumulative
.venv/bin/python -m tools.verify_miss_prototype --cumulative
.venv/bin/python -m tools.verify_queue_notices --copied
.venv/bin/python -m tools.verify_player_status_prototype --cumulative
.venv/bin/python -m tools.verify_player_effect_prototype --cumulative
.venv/bin/python -m tools.verify_item_use_prototype --cumulative
.venv/bin/python -m tools.verify_player_condition_prototype --cumulative
.venv/bin/python -m tools.verify_inventory_action_prototype --cumulative
.venv/bin/python -m tools.verify_pickup_prototype --cumulative
.venv/bin/python -m tools.verify_swap_prototype --cumulative
.venv/bin/python -m tools.verify_container_prototype --cumulative
.venv/bin/python -m tools.verify_town_actions --cumulative
.venv/bin/python -m tools.verify_additional_actions --cumulative
.venv/bin/python -m tools.verify_child_actions --cumulative
.venv/bin/python -m tools.verify_player_messages --cumulative
.venv/bin/python -m tools.verify_blacksmith --cumulative
.venv/bin/python -m tools.verify_blacksmith_transactions --cumulative
.venv/bin/python -m tools.verify_gaibara --cumulative
.venv/bin/python -m tools.verify_gaibara_menu --cumulative
.venv/bin/python -m tools.verify_gaibara_transactions --cumulative
.venv/bin/python -m tools.verify_selection_prompt --cumulative
.venv/bin/python -m tools.verify_remi --cumulative
.venv/bin/python -m tools.verify_remi_menus --cumulative
.venv/bin/python -m tools.verify_remi_picker --cumulative
.venv/bin/python -m tools.verify_remi_picker_fallback --cumulative
.venv/bin/python -m tools.verify_remi_vocations --cumulative
.venv/bin/python -m tools.verify_remi_saved_village --cumulative
.venv/bin/python -m tools.verify_remi_safe --cumulative
.venv/bin/python -m tools.verify_remi_charges --cumulative
.venv/bin/python -m tools.verify_remi_levels --cumulative
.venv/bin/python -m tools.verify_remi_warp_menu --cumulative
.venv/bin/python -m tools.verify_remi_warp_payment --cumulative
.venv/bin/python -m tools.verify_mayor --cumulative
.venv/bin/python -m tools.verify_mayor_editor --cumulative
.venv/bin/python -m tools.verify_mayor_persistence --cumulative
.venv/bin/python -m tools.verify_well_picker --cumulative
.venv/bin/python -m tools.verify_hunger --cumulative
.venv/bin/python -m tools.verify_status_traps --cumulative
.venv/bin/python -m tools.verify_warp_trap --cumulative
.venv/bin/python -m tools.verify_unequip_trap --cumulative
.venv/bin/python -m tools.verify_mud_trap --cumulative
.venv/bin/python -m tools.verify_damage_traps --cumulative
.venv/bin/python -m tools.verify_rust --cumulative
.venv/bin/python -m tools.verify_summon_trap --cumulative
.venv/bin/python -m tools.verify_blast_traps --cumulative
.venv/bin/python -m tools.verify_pitfall --cumulative
.venv/bin/python -m tools.verify_bear_trap --cumulative
.venv/bin/python -m tools.verify_stumble_trap --cumulative
.venv/bin/python -m tools.verify_curse --cumulative
.venv/bin/python -m tools.verify_drain --cumulative
.venv/bin/python -m tools.verify_level_drain --cumulative
.venv/bin/python -m tools.verify_steal_gold --cumulative
.venv/bin/python -m tools.verify_monster_conditions --cumulative
.venv/bin/python -m tools.verify_results --source build/english --output build/english/results-validation
.venv/bin/python -m tools.verify_result_ui --source build/english
.venv/bin/python -m tools.verify_result_ui --source build/english --history
.venv/bin/python -m tools.verify_history_menu --source build/english
.venv/bin/python -m tools.verify_records --source build/english
.venv/bin/python -m tools.verify_password --source build/english
.venv/bin/python -m tools.review_mansion
.venv/bin/python -m tools.audit_menu_layouts
.venv/bin/python -m tools.build_compact_font --output build/font-audition/native
.venv/bin/python -m tools.verify_compact_font --output build/font-audition/native
.venv/bin/python -m tools.review_compact_font --output build/font-audition/native
.venv/bin/python -m tools.probe_menu_resize --english
.venv/bin/python -m tools.verify_menu_edges
.venv/bin/python -m tools.verify_menu_actions
.venv/bin/python -m tools.audit_item_variants --english
.venv/bin/python -m tools.verify_service_ui
.venv/bin/python -m tools.verify_bank
.venv/bin/python -m tools.verify_bank_rewards
.venv/bin/python -m tools.verify_bakery_prototype --cumulative
.venv/bin/python -m tools.extract_items
.venv/bin/python -m tools.extract_item_use
.venv/bin/python -m tools.extract_action_labels
.venv/bin/python -m tools.text_inventory
.venv/bin/python -m tools.audit_text_staging
.venv/bin/python -m tools.verify_item_alias_prototype --cumulative
.venv/bin/python -m tools.verify_items
.venv/bin/python -m tools.trace_storage
.venv/bin/python -m tools.verify_storage
.venv/bin/python -m tools.verify_storage_services
.venv/bin/python -m tools.verify_bank_persistence
.venv/bin/python -m tools.verify_numeric_font
.venv/bin/python -m tools.review_typography
.venv/bin/python -m tools.review_services
.venv/bin/python -m tools.review_combat
.venv/bin/python -m tools.review_queue_notices
.venv/bin/python -m tools.review_item_aliases --cumulative
.venv/bin/python -m tools.review_player_effects --cumulative
.venv/bin/python -m tools.review_item_use --cumulative
.venv/bin/python -m tools.review_more_text story-command --cumulative
.venv/bin/python -m tools.review_more_text player-condition --cumulative
.venv/bin/python -m tools.review_more_text inventory-action --cumulative
.venv/bin/python -m tools.review_more_text pickup --cumulative
.venv/bin/python -m tools.review_swap --cumulative
.venv/bin/python -m tools.review_containers --cumulative
.venv/bin/python -m tools.review_action_labels --cumulative
.venv/bin/python -m tools.review_action_labels --child --cumulative
.venv/bin/python -m tools.review_town_actions --cumulative
.venv/bin/python -m tools.review_player_messages --cumulative
.venv/bin/python -m tools.review_blacksmith --cumulative
.venv/bin/python -m tools.review_gaibara --cumulative
.venv/bin/python -m tools.review_remi --cumulative
.venv/bin/python -m tools.review_mayor --cumulative
.venv/bin/python -m tools.review_well_picker --cumulative
.venv/bin/python -m tools.review_hunger --cumulative
.venv/bin/python -m tools.review_status_traps --cumulative
.venv/bin/python -m tools.review_warp_trap --cumulative
.venv/bin/python -m tools.review_unequip_trap --cumulative
.venv/bin/python -m tools.review_mud_trap --cumulative
.venv/bin/python -m tools.review_damage_traps --cumulative
.venv/bin/python -m tools.review_rust --cumulative
.venv/bin/python -m tools.review_summon_trap --cumulative
.venv/bin/python -m tools.review_blast_traps --cumulative
.venv/bin/python -m tools.review_pitfall --cumulative
.venv/bin/python -m tools.review_bear_trap --cumulative
.venv/bin/python -m tools.review_stumble_trap --cumulative
.venv/bin/python -m tools.review_curse --cumulative
.venv/bin/python -m tools.review_drain --cumulative
.venv/bin/python -m tools.review_level_drain --cumulative
.venv/bin/python -m tools.review_steal_gold --cumulative
.venv/bin/python -m tools.review_monster_conditions --cumulative
.venv/bin/python -m tools.review_results --source build/english --output build/english/results-validation
.venv/bin/python -m tools.review_result_ui --source build/english
.venv/bin/python -m tools.review_result_ui --source build/english --history
.venv/bin/python -m tools.review_text_panels --source build/english --folder history-menu-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder records-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder password-validation
.venv/bin/python -m tools.review_menus
.venv/bin/python -m tools.audit_service_budgets
.venv/bin/python -m tools.sync_text_budgets
.venv/bin/python -m tools.audition_fonts
