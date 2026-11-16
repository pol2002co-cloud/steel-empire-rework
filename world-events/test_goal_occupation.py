"""Native city arrival evidence for visit versus military occupation goals.

No save is opened or changed. Execute original4381e0/4382e0 using synthetic
world storage; mock only world actor removal/creation at their boundaries.
"""
from test_patch import *

STOP=0x5ff000;WORLD=0x1000000;TOWN=0x1010000;CITY=0x1070000
ARMY=0x1080000;PERSON=0x1090000;ACTOR=0x10a0000;OTHER=0x10b0000

def physical_player_armies(u,town):
 for i in range(15):
  p=r(u,town+0x50654+4*i)
  if p and r(u,p)==1 and r(u,p+8)==town and r(u,p+0x14)>0 and r(u,p+0x1c)>0:
   yield p

def occupied(u,town):
 if r(u,town+0x10)&1:return False
 if not any(r(u,p+0x18)!=3 for p in physical_player_armies(u,town)):return False
 # Fail closed on a mixed/stale resident array, even though native entry
 # normally evicts every resident belonging to a different faction.
 for i in range(15):
  p=r(u,town+0x50654+4*i)
  if p and r(u,p)!=1 and r(u,p+0x14)>0 and r(u,p+0x1c)>0 and r(u,p+0x18)!=3:
   return False
 return True

def fixture(kind=0,faction=1,flags=1):
 u=setup();u.mem_map(0,4096)
 for p,v in ((TOWN,WORLD),(TOWN+4,63),(TOWN+8,12),(TOWN+0x10,flags),
             (WORLD+0x23c,CITY),(CITY+0x7c,TOWN),
             (ARMY,faction),(ARMY+4,TOWN),(ARMY+0x10,ACTOR),
             (ARMY+0x14,1),(ARMY+0x18,kind),(ARMY+0x1c,1),
             (ARMY+0x60,PERSON),(PERSON+0x54,1),(PERSON+0x58,100)):
  w(u,p,v)
 def boundary(u,pc,size,data):
  if pc==0x420b70:ret(u,4)
  elif pc==0x420c50:
   sp=u.reg_read(UC_X86_REG_ESP);p=r(u,sp+4)
   w(u,p+0x10,ACTOR);ret(u,8)
 u.hook_add(UC_HOOK_CODE,boundary)
 return u

def invoke(u,pc,*args):
 sp=0x13f0000;w(u,sp,STOP)
 for i,v in enumerate(args):w(u,sp+4+i*4,v)
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,TOWN)
 u.emu_start(pc,STOP,count=100000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP
 assert u.reg_read(UC_X86_REG_ESP)==sp+4+4*len(args)

checks=0
for kind in (0,1,2):
 u=fixture(kind);invoke(u,0x4381e0,ARMY)
 assert r(u,ARMY+8)==TOWN and r(u,ARMY+0x10)==0
 assert r(u,TOWN+0x50654)==ARMY and not(r(u,TOWN+0x10)&1)
 assert r(u,PERSON+0x54)==100 and occupied(u,TOWN)
 assert list(physical_player_armies(u,TOWN))==[ARMY]
 # Leaving removes physical ownership but the hostility bit stays clear.
 invoke(u,0x4382e0,1)
 assert r(u,TOWN+0x50654)==0 and r(u,ARMY+8)==0
 assert not occupied(u,TOWN) and not(r(u,TOWN+0x10)&1)
 checks+=2

for flags in (0,1):
 u=fixture(3,flags=flags);invoke(u,0x4381e0,ARMY)
 assert r(u,TOWN+0x10)==flags
 assert list(physical_player_armies(u,TOWN))==[ARMY]
 assert not occupied(u,TOWN);checks+=1

u=fixture(0,12,0);invoke(u,0x4381e0,ARMY)
assert r(u,TOWN+0x10)&1 and not occupied(u,TOWN);checks+=1

for field,value in ((ARMY+8,OTHER),(ARMY+0x14,0),(ARMY+0x1c,0)):
 u=fixture();invoke(u,0x4381e0,ARMY);w(u,field,value)
 assert not occupied(u,TOWN);checks+=1

u=fixture();invoke(u,0x4381e0,ARMY)
for p,v in ((TOWN+0x50658,OTHER),(OTHER,12),(OTHER+8,TOWN),
            (OTHER+0x14,2),(OTHER+0x1c,5),(OTHER+0x18,0)):w(u,p,v)
assert not occupied(u,TOWN);checks+=1
print('PASS occupation goals:',checks,'native arrival/leave and fail-closed predicate cases')
