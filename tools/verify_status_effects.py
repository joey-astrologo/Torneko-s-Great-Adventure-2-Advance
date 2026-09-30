"""Owned actor status effects through actual condition helpers and native text."""
import argparse,struct
from pathlib import Path
from tools.rom import ROOT,require
from tools.verify_dungeon_leaves import run as check
OWNERS={
 'sleep-a':(0x39054,0x3907C,0x390A7,0x390AC,0,0x1DC),
 'sleep-a-resist':(0x39054,0x3909E,0x390A7,0x390AC,0,0x11C),
 'sleep-b':(0x39860,0x39888,0x398B3,0x398B8,0,0x1DC),
 'sleep-b-resist':(0x39860,0x398AA,0x398B3,0x398B8,0,0x11C),
 'sleep-skill':(0x3C6FC,0x3C72C,0x3C757,0x3C764,0,0x1DC),
 'sleep-skill-resist':(0x3C6FC,0x3C74E,0x3C757,0x3C764,0,0x11C),
 'confusion-a':(0x390EC,0x39110,0x39119,0x3911E,0,0x1E8),
 'confusion-b':(0x398C0,0x398E4,0x398ED,0x398F2,0,0x1E8),
 'fake-priest':(0x39700,0x3974A,0x3977D,0x39782,0,0x22C),
 'maximum-hp':(0x3947C,0x394D4,0x394DD,0x394EA,0,0x7F4),
 'actor-level-down':(0x3953C,0x3956A,0x39573,0x395A8,0,0xEC),
 'actor-level-minimum':(0x3953C,0x3959A,0x395A3,0x395A8,0,0xA20),
 'actor-strength':(0x39158,0x391BC,0x391C5,0x391FE,0,0x62C),
 'actor-slow':(0x39158,0x391F0,0x391F9,0x391FE,0,0x200),
}


class StatusEffects:
    breakpoints=()
    scope='Fourteen controlled native status branches across nine routines. Actual sleep/resistance, confusion, disguise, maximum HP, level and strength/speed helpers run; all exact source selectors,256-byte outputs, field bounds, conditional breaks, colours, final pixels and caller/battery preservation pass. Inputs set existing actor status/species fields and are fully recorded. Other source consumers, natural acquisition and combat encounters remain separate.'
    def setup(self,owner,g,hero,actor,write,overrides):
        m=g.core.memory
        write(actor+8,struct.pack('<I',(m.u32[actor+8]&~0x02000001)|0x80000000));write(actor+0x91,b'\1');write(actor+0x84,struct.pack('<HH',30,30));write(actor+0x88,struct.pack('<H',1 if owner=='actor-level-minimum' else 2));write(actor+0x76,struct.pack('<HH',1 if owner=='actor-slow' else 10,10))
        write(actor+0x95,b'\0');write(actor+0x97,b'\0');write(actor+0xA4,bytes([int(owner.endswith('-resist'))]))
        write(actor+0x92,bytes([int(owner=='actor-slow'),0,0]));write(actor+0x9C,b'\0')
        return (hero,actor,0,0) if owner.startswith('sleep-skill') else (actor,0,0,0)
    def event(self,owner,e,g,hero,actor,write,overrides):pass
    def return_register(self,owner):return int(owner.startswith('sleep-skill'))
    def returned(self,owner,g,hero,actor):
        m=g.core.memory
        if owner.startswith('sleep'):
            require(m.u8[actor+0x97]==0 if owner.endswith('-resist') else 6<=m.u8[actor+0x97]<=10,'Native actor sleep state differs')
        if owner.startswith('confusion'):require(10<=m.u8[actor+0x95]<=12,'Native confusion state differs')
        if owner=='fake-priest':require(m.u8[actor+0xA9]==20 and m.u8[actor+0xBE]==0,'Native disguise state differs')
        if owner=='maximum-hp':require(m.u16[actor+0x86]==35 and m.u16[actor+0x84]==30,'Native maximum HP result differs')
        if owner.startswith('actor-level'):require(m.u16[actor+0x88]==1,'Native actor level differs')
        if owner=='actor-strength':require(m.u16[actor+0x76]==7 and m.u8[actor+0x93]==0,'Native strength-only result differs')
        if owner=='actor-slow':require(m.u16[actor+0x76]==1 and m.u8[actor+0x92]==0 and m.u32[actor+8]&0x20,'Native slowdown result differs')


def run(source,only=None):check(source,only,owners=OWNERS,resource_key='status_effects',folder='status-effect-validation',hooks=StatusEffects())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/status-effects-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
