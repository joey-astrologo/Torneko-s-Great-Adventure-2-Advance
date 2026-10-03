#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
.venv/bin/python -m tools.audit_terminology
.venv/bin/python -m tools.build_english
.venv/bin/python -m tools.audit_reader_routes
.venv/bin/python -m tools.verify_title_art
.venv/bin/python -m tools.accept_title_art
.venv/bin/python -m tools.verify_location_banner
.venv/bin/python -m tools.accept_location_banner
.venv/bin/python -m tools.verify_floor_menu
.venv/bin/python -m tools.verify_wind
.venv/bin/python -m tools.verify_town_overview
.venv/bin/python -m tools.audit_status_expiry
.venv/bin/python -m tools.verify_caller_repairs
.venv/bin/python -m tools.audit_remaining_callers --extended
.venv/bin/python -m tools.audit_item_definition_callers
.venv/bin/python -m tools.verify_name_entry
.venv/bin/python -m tools.verify_opening_dialogue
.venv/bin/python -m tools.verify_arrival_art
.venv/bin/python -m tools.accept_arrival_art
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
.venv/bin/python -m tools.verify_event_repairs --source build/english
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
.venv/bin/python -m tools.verify_walking_pickup
.venv/bin/python -m tools.audit_dungeon_screens
.venv/bin/python -m tools.audit_town_screens
.venv/bin/python -m tools.accept_screen_audit
.venv/bin/python -m tools.verify_projectiles --source build/english
.venv/bin/python -m tools.verify_monster_announcements --source build/english
.venv/bin/python -m tools.verify_priest --source build/english
.venv/bin/python -m tools.verify_priest_services --source build/english
.venv/bin/python -m tools.verify_companion --source build/english
.venv/bin/python -m tools.verify_recovery --source build/english
.venv/bin/python -m tools.verify_options_help --source build/english
.venv/bin/python -m tools.verify_soldiers --source build/english
.venv/bin/python -m tools.verify_spell_info --source build/english
.venv/bin/python -m tools.verify_spell_menu --source build/english
.venv/bin/python -m tools.verify_spell_item --source build/english
.venv/bin/python -m tools.verify_scroll_item --source build/english
.venv/bin/python -m tools.verify_spell_messages --source build/english
.venv/bin/python -m tools.verify_item_theft --source build/english
.venv/bin/python -m tools.verify_skill_info --source build/english
.venv/bin/python -m tools.verify_skill_menu --source build/english
.venv/bin/python -m tools.verify_skill_equipment --source build/english
.venv/bin/python -m tools.verify_skill_set --source build/english
.venv/bin/python -m tools.verify_skill_actions --source build/english
.venv/bin/python -m tools.verify_dungeon_leaves --source build/english
.venv/bin/python -m tools.verify_floor_buffs --source build/english
.venv/bin/python -m tools.verify_fullness --source build/english
.venv/bin/python -m tools.verify_status_effects --source build/english
.venv/bin/python -m tools.verify_discovery_messages --source build/english
.venv/bin/python -m tools.verify_monster_interactions --source build/english
.venv/bin/python -m tools.verify_staff_use --source build/english
.venv/bin/python -m tools.verify_writing --source build/english
.venv/bin/python -m tools.verify_item_loss --source build/english
.venv/bin/python -m tools.verify_player_notices --source build/english
.venv/bin/python -m tools.verify_swap_prototype --cumulative
.venv/bin/python -m tools.verify_container_prototype --cumulative
.venv/bin/python -m tools.verify_town_actions --cumulative
.venv/bin/python -m tools.verify_additional_actions --cumulative
.venv/bin/python -m tools.verify_child_actions --cumulative
.venv/bin/python -m tools.verify_player_messages --cumulative
.venv/bin/python -m tools.verify_strengthening
.venv/bin/python -m tools.verify_skill_shouts
.venv/bin/python -m tools.verify_skill_learning
.venv/bin/python -m tools.verify_battle_results
.venv/bin/python -m tools.verify_dungeon_shop --source build/english
.venv/bin/python -m tools.verify_save_notices --source build/english
.venv/bin/python -m tools.verify_reference_lists --source build/english
.venv/bin/python -m tools.verify_priest_warning --source build/english
.venv/bin/python -m tools.verify_save_preview --source build/english
.venv/bin/python -m tools.verify_town_root --source build/english
.venv/bin/python -m tools.verify_writing_lookup --source build/english
.venv/bin/python -m tools.verify_writing_editor --source build/english
.venv/bin/python -m tools.verify_custom_items --source build/english
.venv/bin/python -m tools.verify_fused_loss --source build/english
.venv/bin/python -m tools.verify_cannot_talk --source build/english
.venv/bin/python -m tools.verify_step_stairs --source build/english
.venv/bin/python -m tools.verify_pot_view --source build/english
.venv/bin/python -m tools.verify_book_travel --source build/english
.venv/bin/python -m tools.verify_ability_info --source build/english
.venv/bin/python -m tools.verify_dungeon_story --source build/english
.venv/bin/python -m tools.verify_empty_read --source build/english
.venv/bin/python -m tools.verify_travel_gate --source build/english
.venv/bin/python -m tools.verify_ending --source build/english
.venv/bin/python -m tools.verify_dungeon_travel --source build/english
.venv/bin/python -m tools.verify_tutorial_help --source build/english
.venv/bin/python -m tools.verify_tutorial_menus --source build/english
.venv/bin/python -m tools.verify_tutorial_banks --source build/english
.venv/bin/python -m tools.verify_tutorial_alternates --source build/english
.venv/bin/python -m tools.verify_link_messages --source build/english
.venv/bin/python -m tools.verify_link_picker --source build/english
.venv/bin/python -m tools.verify_ending_notice --source build/english
.venv/bin/python -m tools.verify_pickup_help --source build/english
.venv/bin/python -m tools.verify_carpenter --source build/english
.venv/bin/python -m tools.verify_fire_scene --source build/english
.venv/bin/python -m tools.verify_travel_confirm --source build/english
.venv/bin/python -m tools.verify_town_routes --source build/english
.venv/bin/python -m tools.verify_form_refusal --source build/english
.venv/bin/python -m tools.verify_ground_remove --source build/english
.venv/bin/python -m tools.verify_monster_identity --source build/english
.venv/bin/python -m tools.verify_native_tutorial --source build/english
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
.venv/bin/python -m tools.verify_compound_numbers
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
.venv/bin/python -m tools.review_text_panels --source build/english --folder strengthening-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder skill-shouts-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder skill-learning-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder battle-results-validation
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
.venv/bin/python -m tools.review_text_panels --source build/english --folder walking-pickup-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder projectile-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder monster-announcement-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder priest-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder priest-service-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder companion-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder recovery-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder options-help-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder soldier-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder spell-info-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder spell-menu-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder spell-item-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder scroll-item-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder spell-messages-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder item-theft-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder skill-info-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder skill-menu-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder skill-equipment-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder skill-set-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder skill-action-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder dungeon-leaves-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder floor-buff-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder fullness-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder status-effect-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder discovery-messages-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder monster-interactions-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder staff-use-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder writing-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder item-loss-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder player-notices-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder dungeon-shop-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder save-notices-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder reference-lists-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder priest-warning-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder save-preview-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder town-root-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder writing-editor-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder fused-loss-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder cannot-talk-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder step-stairs-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder pot-view-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder book-travel-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder ability-info-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder dungeon-story-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder empty-read-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder travel-gate-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder ending-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder dungeon-travel-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder tutorial-help-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder tutorial-all-menu-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder tutorial-bank-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder tutorial-alternate-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder link-message-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder link-picker-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder ending-notice-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder pickup-help-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder carpenter-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder fire-scene-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder travel-confirm-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder town-routes-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder form-refusal-validation
.venv/bin/python -m tools.review_text_panels --source build/english --folder ground-remove-validation
.venv/bin/python -m tools.review_menus
.venv/bin/python -m tools.audit_service_budgets
.venv/bin/python -m tools.sync_text_budgets
.venv/bin/python -m tools.audition_fonts
