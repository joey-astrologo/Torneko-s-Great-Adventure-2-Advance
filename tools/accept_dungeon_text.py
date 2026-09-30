"""Pin walking, priest, companion, Throw and monster-announcement evidence."""
import json,struct
from tools.rom import ROOT,digest,require


def validate(build,receipt,counts):
    cohorts={'battle-results':('battle_results',37,6),'skill-shouts':('skill_messages',512,6),'skill-learning':('skill_messages',384,6),'strengthening':('player_messages',12,40),'priest':('priest',35,25),'priest-service':('priest',17,25),
             'projectile':('projectiles',20,5),'monster-announcement':('monster_announcements',117,24),
             'companion':('companion',6,6),'walking-pickup':('pickup',5,6),
             'recovery':('recovery',19,3),'options-help':('ui',4,30),
             'soldier':('soldiers',9,7),'spell-info':('spell_info',64,132),
             'spell-menu':('spell_menu',9,5),'spell-item':('spell_item',125,2),'scroll-item':('scroll_item',77,39),'spell-messages':('spell_messages',384,5),'discovery-messages':('discovery_messages',40,7),'monster-interactions':('monster_interactions',8,2),'staff-use':('staff_use',8,2),'writing':('writing',102,6),'item-loss':('item_loss',32,3),'player-notices':('player_notices',6,2),
             'item-theft':('item_theft',25,5),'skill-info':('skill_info',131,266),
             'skill-menu':('skill_menu',4,19),'skill-equipment':('skill_menu',7,19),
             'skill-set':('skill_menu',1,19),'skill-action':('skill_menu',3,19),
             'dungeon-leaves':('dungeon_leaves',88,15),'floor-buff':('floor_buffs',25,1),
             'fullness':('fullness',12,1),'status-effect':('status_effects',56,9)}
    for family,(key,count,resources) in cohorts.items():
        folder=ROOT/'build/english'/(family+'-validation');path=folder/'report.json'
        report=json.loads(path.read_text());rows=report['cases'];entries=build[key]['entries']
        require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale dungeon evidence: '+family)
        require(len(entries)==resources and len(rows)==count and len({r['case'] for r in rows})==count,'Incomplete dungeon cohort: '+family)
        require(all(r['visible_pixels_checked']>0 and r['inputs'] and r['images'] for r in rows),'Missing visible dungeon evidence: '+family)
        if family in ('priest','projectile','monster-announcement','companion','recovery','soldier','dungeon-leaves','fullness','status-effect','discovery-messages','monster-interactions','staff-use','writing','item-loss','player-notices'):
            required={r['id'] for r in entries if family!='priest' or r['table_offset']!=0x4DC}
            require({r['id'] for r in rows}==required,'Dungeon source set differs: '+family)
        if family in ('projectile','monster-announcement','priest-service','recovery','options-help','spell-info','spell-menu','spell-item','scroll-item','spell-messages','item-theft','skill-info','skill-menu','skill-equipment','skill-set','skill-action','dungeon-leaves','floor-buff','fullness','status-effect','discovery-messages','monster-interactions','staff-use','writing','item-loss','player-notices','strengthening','skill-shouts','skill-learning','battle-results'):
            require(all(r['caller_guard_abi_preserved'] for r in rows),'Dungeon caller preservation missing')
        if family in ('dungeon-leaves','status-effect','discovery-messages','monster-interactions','staff-use','item-loss'):
            if family=='dungeon-leaves':
                from tools.verify_dungeon_leaves import OWNERS
            elif family=='item-loss':
                from tools.verify_item_loss import OWNERS
            elif family=='staff-use':
                from tools.verify_staff_use import OWNERS
            elif family=='monster-interactions':
                from tools.verify_monster_interactions import OWNERS
            elif family=='discovery-messages':
                from tools.verify_discovery_messages import OWNERS
            else:
                from tools.verify_status_effects import OWNERS
            require({(r['owner'],r['field']) for r in rows}=={(owner,field) for owner in OWNERS for field in ('native','maximum-width','maximum-bytes','coloured')},'Effect owner/field coverage differs')
            require(all(all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Effect format/guard evidence missing')
        elif family=='battle-results':
            from tools.verify_battle_results import OWNERS,Results
            require({(r['owner'],r['field']) for r in rows}=={(owner,field) for owner in OWNERS for field in Results().case_fields(owner)},'Battle result reader/field coverage differs')
            require({r['id'] for r in rows}=={r['id'] for r in entries} and all(all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Battle result sources/guards differ')
        elif family=='skill-shouts':
            from tools.verify_skill_shouts import OWNERS
            require({(r['owner'],r['field']) for r in rows}=={(owner,str(i)) for owner in OWNERS for i in range(128)},'Skill shout selector coverage differs')
            require({r['id'] for r in rows}=={'skill-message.764','skill-message.774'} and all(r['queue']['one_line'] and all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Skill shout source/one-line/guard evidence differs')
        elif family=='skill-learning':
            from tools.dialogue_checks import player_layout_cases
            require({(r['skill_id'],r['player_case']) for r in rows}=={(i,name) for i in range(128) for name,_ in player_layout_cases()},'Skill acquisition selector/name coverage differs')
            # Original definitions select sword or shield here. Every bare-hand
            # bit is accompanied by a shield mask, which overrides it. Validate
            # the actual per-definition branch rather than inventing coverage
            # of the retained, currently unselected bare-hand explanation.
            definitions={r['id']:bytes.fromhex(r['record_hex']) for r in build['skill_info']['definitions']}
            for row in rows:
                definition=definitions[row['skill_id']]
                slot=0x7F0 if struct.unpack_from('<I',definition,16)[0] else 0x7E8 if struct.unpack_from('<I',definition,12)[0]&1 else 0x7EC
                require([r['id'] for r in row['reads']]==['skill-message.754',f'skill-message.{slot:x}'],'Skill acquisition native explanation differs')
            require(all(r['native_state_checked'] and all(f['guard_abi_preserved'] for f in r['formats']) for r in rows),'Skill acquisition state/guard evidence differs')
        elif family=='strengthening':
            from tools.verify_strengthening import OWNERS,Strengthening
            require({(r['owner'],r['field']) for r in rows}=={(owner,field) for owner in OWNERS for field in Strengthening().case_fields(owner)},'Strengthening name/state coverage differs')
            require({r['id'] for r in rows}=={'player-message.368','player-message.36c'} and all(all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Strengthening routing/guard evidence differs')
        elif family=='player-notices':
            from tools.verify_player_notices import OWNERS,Notices
            require({(r['owner'],r['field']) for r in rows}=={(owner,field) for owner in OWNERS for field in Notices().case_fields(owner)},'Player notice name coverage differs')
        elif family=='writing':
            from tools.verify_writing import OWNERS,Writing
            expected={(owner,field) for owner in OWNERS for field in Writing().case_fields(owner)}
            require({(r['owner'],r['field']) for r in rows}==expected and all(all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Writing selector/guard coverage differs')
        elif family=='floor-buff':
            require({r['branch'] for r in rows}==set(range(8)) and all(r['native_state_checked'] for r in rows),'Bonus-effect branches missing')
        elif family=='fullness':
            require({(r['owner'],r['field']) for r in rows}=={(owner,field) for owner in ('food','increase','decrease') for field in ('normal','boundary','maximum-decimal','zero-decimal')} and all(r['native_state_checked'] for r in rows),'Fullness cases/states missing')
        elif family=='priest':
            require(all(r['return'] and r['reads'] and all(f['guard_tail_abi_match'] for f in r['formats']) for r in rows),'Priest output/return evidence missing')
        elif family=='priest-service':
            require({r['case'] for r in rows}=={'navigation','curse-none','poison-none','hp-full','hp-cap'}|{f'{i}-{k}' for i in range(4) for k in ('decline','no-funds','success')},'Priest branches missing')
            require(all(r['menu_opens']>=1 for r in rows),'Priest menu was not displayed')
        elif family=='companion':
            require({r['floor'] for r in rows}==set(range(1,7)) and all(len(r['selection'])==1 and r['return'] for r in rows),'Companion native selectors missing')
        elif family=='monster-announcement':
            require({r['actor_id'] for r in rows if r['field']=='native'}==set(map(int,build[key]['selectors'])),'Monster native selector cases missing')
            require(all(r['effect_body_explicitly_skipped'] for r in rows),'Monster controlled scope differs')
        elif family=='walking-pickup':
            require({r['case'] for r in rows}=={'native-item','gold','arrows','full','standing-option'},'Walking cases differ')
            require(not next(r for r in rows if r['case']=='native-item')['overrides'],'Ordinary walking case was modified')
            require(all(len(r['walk_entries'])==1 and all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Walking native dispatch/guards missing')
        elif family=='recovery':
            require({r['owner'] for r in rows}=={'heal','maximum','skill','warp'} and all(all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Recovery native owners/guards missing')
        elif family=='options-help':
            require({r['mode'] for r in rows}==set(range(4)) and all(r['return'] for r in rows),'Option help modes/returns missing')
        elif family=='soldier':
            require({r['selector'] for r in rows}==set(range(7)) and all(r['return'] and r['selection'] and r['object_restore_events'] for r in rows),'Soldier object selections/restoration missing')
        elif family=='scroll-item':
            require({(r['item_id'],r['state']) for r in rows}=={(i,state) for i in range(116,153) for state in ('normal','priced')}|{(149,state) for state in ('priced-maximum','priced-equipped','priced-cursed')},'Inscribed scroll row coverage differs')
            require(all(r['parent_restored'] and r['lookups'] and all(b['name_price_separate'] for b in r['budgets']) for r in rows),'Inscribed scroll lookup/price/restoration evidence missing')
        elif family=='spell-item':
            require({(r['spell_id'],r['state']) for r in rows}=={(i,state) for i in range(61) for state in ('normal','priced')}|{(43,state) for state in ('priced-maximum','priced-equipped','priced-cursed')},'Inscribed spell row coverage differs')
            require(all(r['parent_restored'] and r['lookups'] and all(b['name_price_separate'] for b in r['budgets']) for r in rows),'Inscribed spell lookup/price/restoration evidence missing')
        elif family=='spell-messages':
            for kind in ('cast','unlearned'):require({r['spell_id'] for r in rows if r['kind']==kind}==set(range(1,61)),'Spell cast/name coverage incomplete')
            require({r['spell_id'] for r in rows if r['kind']=='forget'}==set(range(2,61))-{22},'Spell forgetting selector coverage incomplete')
            learned={d['id'] for d in build['spell_info']['definitions'] if bytes.fromhex(d['record_hex'])[7]}
            require({r['spell_id'] for r in rows if r['kind']=='learn'}==learned and sum(r['kind']=='learn' for r in rows)==3*len(learned),'Spell learning/player coverage incomplete')
            require({f['id'] for r in rows for f in r['formats']}=={r['id'] for r in entries} and all(r['native_state_checked'] and all(f['guard_abi_preserved'] for f in r['formats']) for r in rows),'Spell state/format evidence incomplete')
        elif family=='spell-info':
            require({r['spell_id'] for r in rows}==set(range(61)) and all(len(r['selection'])==len(r['return'])==2 and all(f['guard_abi_preserved'] for f in r['formats']) for r in rows),'Spell Info selectors/reopening/guards missing')
        elif family=='spell-menu':
            required={r['id'] for r in build['spell_info']['definitions'] if r['menu_eligible']}
            for available in (False,True):
                require({i for r in rows if r['available']==available for i in r['covered_ids']}==required,'Spell menu names/state coverage differs')
            require(all(all(f['guard_abi_preserved'] for f in r['formats']) for r in rows),'Spell menu formatter guards missing')
        elif family=='skill-info':
            require({r['skill_id'] for r in rows}==set(range(128)) and all(len(r['selection'])==len(r['return'])==2 and all(f['guard_abi_preserved'] for f in r['formats']) for r in rows),'Skill Info selectors/reopening/guards missing')
            require({r['footer_case'] for r in rows}=={'unassigned','single','multiple','hidden'},'Skill assignment footer variants missing')
        elif family=='skill-menu':
            required={r['id'] for r in build['skill_info']['definitions'] if r['menu_eligible']}
            require({i for r in rows for i in r['covered_ids']}==required,'Skill list name coverage differs')
        elif family=='skill-equipment':
            require({r['case'] for r in rows}=={'empty-weapon','three-weapon','zero-cost','incompatible','not-equipped','shield','empty-shield'},'Equipment skill states missing')
        elif family=='skill-set':
            require({read['id'] for row in rows for read in row['reads']} >= {'skill-menu.92c','skill-menu.960'},'Native Set confirmation/result missing')
        elif family=='skill-action':
            require({r['case'] for r in rows}=={'retained-action-1','retained-action-2','retained-action-4'},'Retained action render probes missing')
        elif family=='item-theft':
            require({r['id'] for r in rows}=={r['id'] for r in entries if r['table_offset']!=0x718} and any(r['native_transfer_checked'] for r in rows),'Theft/wait sources or native transfer missing')
        images={r['case']+'/'+p:sha for r in rows for p,sha in r['images'].items()}
        require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':count,'images':images},'Stale dungeon gallery: '+family)
        for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Changed dungeon capture: '+p)
        for pattern in ('*.json','index.html','*/*.png','native/*.json'):
            for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
        counts[family]=count;receipt[family+'_scope']=report['scope']
    receipt['additional_dungeon_resources']=603
