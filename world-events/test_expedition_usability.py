"""Real F8 expedition flow, repeat convenience, preview and rare passives."""
from test_expedition_native import *
checks=0

def route(u,answers):
 u.data['answers']=answers;return invoke(u,'we_router',PARENT)

# Recommended captain is mission-aware and chosen before costs/people change.
u=ready();w(u,HEROES+2*0x500+0x48,80);w(u,HEROES+2*0x500+0x70,150)
assert route(u,[3,0,0,0,0,3])==1
a=invoke(u,'ex_resolve',tp(1),0)
assert a and r(u,a+0x34)==HEROES+2*0x500,'Recommended captain was not ranked first'
assert any('자동 추천' in text for title,text in u.data['texts'])
assert any('순수익' in text and '차질' in text for title,text in u.data['texts']);checks+=1

# Repeat an active mission with fresh people; its original party is untouched.
u=ready();assert start(u,3);a=invoke(u,'ex_resolve',tp(1),0)
before=bytes(u.mem_read(a,0x55b0));cash=r(u,CASH[0])
assert route(u,[3,1,0,0,0,3])==1
assert r(u,run(u,1))==1 and r(u,run(u,1)+4)==3
assert bytes(u.mem_read(a,0x55b0))==before
assert r(u,CASH[0])==cash-MISSIONS[3]['cost'];checks+=1

# Cancelling a repeated dispatch never reserves or charges a second party.
u=ready();assert start(u);cash=r(u,CASH[0]);people=bytes(u.mem_read(PEOPLE,0x18000))
route(u,[3,1,0,0,1,3])
assert not r(u,run(u,1)) and r(u,CASH[0])==cash
assert bytes(u.mem_read(PEOPLE,0x18000))==people;checks+=1

for delay,label in ((0,'진행'),(30,'지연'),(37,'정산')):
 u=ready();assert start(u,roll=99)
 if delay:advance(u,delay)
 route(u,[3,1,-1,3])
 assert any(label in item for options in u.data['selections'] for item in options),label
 checks+=1

# Crystal affects new departures only, including short exploration trips.
for mission,m in enumerate(MISSIONS):
 u=ready();discover(u);w(u,state(u)+16,8)
 assert start(u,mission)
 assert r(u,run(u)+16)-r(u,run(u)+12)==max(1,(m['days']*4+4)//5)
 checks+=1
u=ready();assert start(u);due=r(u,run(u)+16);w(u,state(u)+16,8)
invoke(u,'we_tick',PARENT);assert r(u,run(u)+16)==due;checks+=1

# Star compass is additive/capped; sage XP is native and paid only once.
u=ready();assert start(u);chance=r(u,run(u)+20)
u=ready();w(u,state(u)+16,4);assert start(u)
assert r(u,run(u)+20)==min(95,chance+5);checks+=1
u=ready(heroes=3,generics=0);w(u,state(u)+16,16);assert start(u)
advance(u,30);assert pump_ex(u) and not r(u,run(u))
assert sum(xp for p,xp in u.exp_awards)==3*500
paid=list(u.exp_awards);assert not pump_ex(u) and u.exp_awards==paid;checks+=1

report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),
 coverage=['F8 recommendation, net/penalty preview and repeated mission fresh-party/cancel',
 'Readable travel/delay/settlement statuses','Three rare passives, short trips, no retroactive deadline or duplicate XP'],
 scoped_mocks=['Native expedition fixture UI drawing/selection and Windows property APIs'],not_checked=['Hardware visual playtest'])
(ROOT/'test-expedition-usability-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS expedition usability:',checks,'compiled UI/passive cases')
