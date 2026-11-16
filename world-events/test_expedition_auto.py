"""Automatic party selection against an exhaustive small-roster oracle."""
from test_expedition_native import *
from itertools import combinations
import random
checks=0

def metric(u, mission, party, artifacts):
 m=MISSIONS[mission];chief=party[0]
 skill=min(200,r(u,chief+0x70));level=r(u,chief+0x48)
 generic=sum(r(u,p+8)==1 for p in party)
 specialists=min(5,sum(bool(m['job']) and r(u,p+0x38)==m['job'] for p in party))
 total=sum(r(u,p+0x48) for p in party)
 chance=min(95,45+level//5+skill//10+total//len(party)//10+generic//4+specialists*2+
  (5 if mission>=4 and artifacts&1 else 0)+(5 if artifacts&4 else 0))
 bonus=min(50,level//5+skill//4+(10 if artifacts&2 else 0))
 return chance,bonus,len(party),total

def oracle(u,mission,heroes,generics,artifacts):
 best=None
 for chief in heroes:
  rest=[p for p in heroes if p!=chief]
  for hn in range(min(2,len(rest))+1):
   for h in combinations(rest,hn):
    for gn in range(min(20,len(generics))+1):
     for g in combinations(generics,gn):
      value=metric(u,mission,[chief,*h,*g],artifacts)
      if best is None or value>best:best=value
 return best

def auto(u,mission=0,index=0):
 discover(u)
 assert invoke(u,'we_test_ex_start',mission,0,0)==1,'Selected mission must automatically choose its captain and party'
 a=invoke(u,'ex_resolve',tp(1),index)
 party=[r(u,a+0x60+i*4) for i in range(81)]
 chief=r(u,a+0x34)
 return [chief]+[p for p in party if p and p!=chief]

rng=random.Random(141)
# Exhaustive oracle includes smaller parties, capped specialist effects and integer rounding.
for i in range(18):
 u=ready(heroes=3+i%2,generics=4+i%3)
 mission=i%7;artifacts=(0,1,2,4,7,31)[i%6];w(u,state(u)+16,artifacts)
 for p in u.exp_heroes+u.exp_generics:
  w(u,p+0x48,rng.choice([1,10,19,20,49,80,99]))
  w(u,p+0x70,rng.choice([0,9,40,100,199,250]))
  w(u,p+0x38,rng.choice([3,8,10,11,12]))
 expected=oracle(u,mission,u.exp_heroes,u.exp_generics,artifacts)
 party=auto(u,mission)
 assert metric(u,mission,party,artifacts)==expected,(i,metric(u,mission,party,artifacts),expected)
 assert len(party)==len(set(party)) and len(party)<=23
 assert r(u,run(u)+20)==expected[0] and r(u,run(u)+24)==expected[1]
 checks+=1

# Extra specialists above five cannot displace stronger people just for their class.
u=ready(heroes=3,generics=25,level=80,skill=0)
for p in u.exp_generics:w(u,p+0x38,11);w(u,p+0x48,1)
for p in u.exp_generics[-20:]:w(u,p+0x38,3);w(u,p+0x48,99)
party=auto(u,1)
assert sum(r(u,p+0x38)==11 for p in party)<=5
assert len(party)==23;checks+=1

# Low-level extras can lower the actual chance: do not fill slots blindly.
u=ready(heroes=3,generics=3,level=99,skill=40)
for p in u.exp_generics:w(u,p+0x48,1)
party=auto(u)
assert not any(p in u.exp_generics for p in party);checks+=1

# Busy, dead, training, assigned and excluded story characters stay untouched.
u=ready(heroes=8,generics=6)
for p,offset,value in [(u.exp_heroes[0],4,1),(u.exp_heroes[1],0x10,1),
 (u.exp_heroes[2],0x14,1),(u.exp_heroes[3],4,2),(u.exp_heroes[4],0,14)]:w(u,p+offset,value)
w(u,tp(1)+0xa0,u.exp_heroes[5]);w(u,u.exp_generics[0]+4,2)
party=auto(u,3)
assert set(party)<=set(u.exp_heroes[6:]+u.exp_generics[1:]);checks+=1

# No captain, insufficient money and full rosters must not charge or reserve anyone.
u=ready(heroes=0);cash=r(u,CASH[0]);assert not invoke(u,'we_test_ex_start',0,0,0)
assert r(u,CASH[0])==cash and not r(u,run(u));checks+=1
u=ready();w(u,CASH[0],0);before=bytes(u.mem_read(PEOPLE,0x18000))
assert not invoke(u,'we_test_ex_start',0,0,0)
assert bytes(u.mem_read(PEOPLE,0x18000))==before;checks+=1
u=ready(heroes=12,generics=0);used=set()
for i in range(4):
 party=auto(u,index=i);assert not used.intersection(party);used.update(party)
cash=r(u,CASH[0]);assert not invoke(u,'we_test_ex_start',0,0,0) and r(u,CASH[0])==cash;checks+=1

# Full 124-hero catalogue and forty candidates exercise the bounded native search.
u=ready(heroes=0,generics=40,level=80,skill=40)
u.mem_map(0x1800000,0xa0000)
hp=[0x1800000+i*0x500 for i in range(124)]
for i,p in enumerate(hp):person(u,p,30+i,3,3,20,40)
w(u,hp[-1]+0x48,99);w(u,hp[-1]+0x70,200)
ring(u,MASTERS,hp,PEOPLE+0x3000);w(u,tp(1)+0x50a50,len(hp))
for i,p in enumerate(u.exp_generics):w(u,p+0x38,11 if i<20 else 3)
pc=int(EX['we_test_ex_start'],16);sp=0x13e0000;w(u,sp,STOP)
for i,v in enumerate((1,0,0)):w(u,sp+4+i*4,v)
u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(pc,STOP,count=30000000)
assert u.reg_read(UC_X86_REG_EIP)==STOP and u.reg_read(UC_X86_REG_ESP)==sp+16
assert u.reg_read(UC_X86_REG_EAX)==1
a=invoke(u,'ex_resolve',tp(1),0)
assert r(u,a+0x34)==hp[-1] and r(u,a+0x1c)==23 and r(u,run(u)+20)==95;checks+=1

report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),
 coverage=['Exhaustive optimum: chance, payout bonus, party size, total levels',
 'Automatic captain, specialist cap, average dilution, 7 missions, artifacts, eligibility, repeated parties, no-charge failures'],
 scoped_mocks=['Existing native expedition fixture Windows APIs and dialogue drawing'],not_checked=['Hardware playtest'])
(ROOT/'test-expedition-auto-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS automatic expedition:',checks,'native cases including 18 exhaustive oracles')
