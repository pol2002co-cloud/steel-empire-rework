"""Annual three-stage guardians: real compiled C progression, mock battle boundary."""
from test_expedition_native import *
checks=0

def guardian(u,index=0):return r(u,visit(u,index)+12)>>16

def world_contact(u,a=None):
 a=a or army(1)
 for city in range(1,74):
  for i in range(15):
   if r(u,tp(city)+0x50654+i*4)==a:w(u,tp(city)+0x50654+i*4,0)
 actor=0x1381000
 w(u,a+8,0);w(u,a+0x10,actor);w(u,actor+0x808,a)
 w(u,actor+0x34,123);w(u,actor+0x38,456);w(u,WORLD+0xac,actor)
 return actor

def arrive(u,index=0):
 if index==3:world_contact(u)
 return visit_ruin(u,index)

def victory(u,index=0,result=3):
 w(u,G+81*4,result);invoke(u,'we_tick',PARENT)

# Four independent chains, true battle adapter calls, fixed profiles and reward gate.
for index in range(4):
 u=ready();v=arrive(u,index);before=tuple(r(u,p) for p in CASH);rng=r(u,state(u)+8)
 assert guardian(u,index)==0 and not invoke(u,'we_test_ex_bless',index,0)
 assert not u.data['battles'],'Native visit callback must never open battle/UI'
 for stage in range(3):
  n=len(u.data['battles'])
  assert invoke(u,'we_test_ex_guardian',index,army(1))==2
  assert guardian(u,index)==stage+5
  assert u.data['battles'][-1]==(army(1),6+index*3+stage)
  assert not invoke(u,'we_test_ex_guardian',index,army(1)) and len(u.data['battles'])==n+1
  assert not invoke(u,'we_test_ex_bless',index,0)
  assert tuple(r(u,p) for p in CASH)==before and r(u,state(u)+8)==rng
  victory(u,index)
  assert guardian(u,index)==stage+1 and not r(u,G+81*4)
  assert not r(u,G+82*4)&3
  checks+=1
 assert invoke(u,'we_test_ex_bless',index,0) and r(u,v+4)==1
 paid=tuple(r(u,p) for p in CASH)
 assert not invoke(u,'we_test_ex_guardian',index,army(1))
 assert not invoke(u,'we_test_ex_bless',index,0) and tuple(r(u,p) for p in CASH)==paid
 visit_ruin(u,index);assert guardian(u,index)==3
 w(u,HOURS,360*24);assert not invoke(u,'we_test_ex_guardian',index,army(1))
 arrive(u,index);assert guardian(u,index)==0 and r(u,v)==2 and r(u,v+4)==1
 assert not invoke(u,'we_test_ex_bless',index,0)
 assert invoke(u,'we_test_ex_guardian',index,army(1))==2;checks+=1

# Defeat/retreat consumes only this ruin's annual attempt, never gives treasures.
for result in (1,2):
 for stage in range(3):
  u=ready();v=arrive(u);before=tuple(r(u,p) for p in CASH)
  for _ in range(stage):
   assert invoke(u,'we_test_ex_guardian',0,army(1))==2;victory(u)
  assert invoke(u,'we_test_ex_guardian',0,army(1))==2;victory(u,result=result)
  assert guardian(u)==4 and not invoke(u,'we_test_ex_guardian',0,army(1))
  assert not invoke(u,'we_test_ex_bless',0,0) and tuple(r(u,p) for p in CASH)==before
  visit_ruin(u);assert guardian(u)==4
  arrive(u,1);assert invoke(u,'we_test_ex_guardian',1,army(1))==2
  checks+=1

# Deferred offer starts only after confirmation; cancellation preserves chance/state.
u=ready();v=arrive(u);snapshot=bytes(u.mem_read(tp(1),0x51000));rng=r(u,state(u)+8)
u.data['answers']=[1];assert pump_ex(u)
assert guardian(u)==0 and not u.data['battles'] and bytes(u.mem_read(tp(1),0x51000))==snapshot
assert r(u,state(u)+8)==rng and len(u.data['selections'])==1;checks+=1
# Failed preparation closes the offer without showing the annual reward choice.
u=ready();arrive(u);u.data['battle_fail']=True;u.data['answers']=[0]
assert pump_ex(u) and guardian(u)==0 and len(u.data['selections'])==1;checks+=1
# F8 ledger returns immediately when a battle starts, with no stale-parent selection.
u=ready();arrive(u);u.data['answers']=[3,2,0,0,0]
assert invoke(u,'we_router',PARENT)==1 and guardian(u)==5
assert len(u.data['selections'])==5 and u.data['battles']==[(army(1),6)];checks+=1
u=ready();arrive(u);station(u,army(2),RUINS[0][1]);u.data['answers']=[1,0]
assert pump_ex(u) and u.data['battles']==[(army(2),6)]
assert not r(u,army(2)+0x10) and r(u,visit(u)+16)==2;checks+=1
# Final victory selects the reward recipient, even after revisiting with another army.
u=ready();v=arrive(u);station(u,army(2),RUINS[0][1])
for _ in range(3):
 assert invoke(u,'we_test_ex_guardian',0,army(2))==2;victory(u)
visit_ruin(u);assert guardian(u)==3 and r(u,v+16)==2
for index in (1,2):
 p=r(u,army(index)+0x34);person(u,p,30+index,3);w(u,p+0x54,1)
assert invoke(u,'we_test_ex_bless',0,2)
assert r(u,r(u,army(2)+0x34)+0x54)==100 and r(u,r(u,army(1)+0x34)+0x54)==1;checks+=1
# Stage2 permits a ground army and warns about anti-air before committing.
u=ready();arrive(u);assert invoke(u,'we_test_ex_guardian',0,army(1))==2;victory(u)
assert invoke(u,'we_test_ex_guardian',0,army(1))==2
assert any('대공' in text for _,text in u.data['texts']);checks+=1

# Failure to create an enemy does not consume a yearly attempt.
u=ready();arrive(u);u.data['battle_fail']=True;before=tuple(r(u,p) for p in CASH)
assert not invoke(u,'we_test_ex_guardian',0,army(1)) and guardian(u)==0
assert tuple(r(u,p) for p in CASH)==before;checks+=1
# Other battles/story/drawing and unvisited/away/civilian/dead armies cannot start.
for mode in ('unvisited','away','civilian','dead','quest','story','window'):
 u=ready();v=arrive(u)
 if mode=='unvisited':w(u,v,0)
 if mode=='away':station(u,army(1),2)
 if mode=='civilian':w(u,army(1)+0x18,3)
 if mode=='dead':w(u,r(u,army(1)+0x34)+4,1)
 if mode=='quest':w(u,G+82*4,r(u,G+82*4)|1)
 if mode=='story':w(u,G+19*4,1)
 if mode=='window':w(u,0x4880e0,123)
 assert not invoke(u,'we_test_ex_guardian',0,army(1)) and guardian(u)==0 and not u.data['battles'],mode
 checks+=1
u=ready();arrive(u,3);actor=r(u,army(1)+0x10);w(u,actor+0x34,124)
assert not invoke(u,'we_test_ex_guardian',3,army(1)) and guardian(u,3)==0
# A fresh real contact authorizes the new location; the old saved contact is not a teleport.
visit_ruin(u,3);assert invoke(u,'we_test_ex_guardian',3,army(1))==2;checks+=1

# Save format stays340B; all completed steps and locked losses persist.
import test_expedition_save as physical
for stage in range(5):
 u=physical.ready_save();v=arrive(u);w(u,v+12,(r(u,v+12)&65535)|(stage<<16))
 assert physical.save(u)==1
 raw=u.files['data']['Steel0.Sav'];assert struct.unpack_from('<I',raw,len(raw)-20)[0]==340
 physical.load(u);assert guardian(u)==stage and not r(u,state(u)+344)
 checks+=1
# An interrupted unsaved combat reloads at the preceding cleared step, never as a win.
for stage in (5,6,7):
 u=physical.ready_save();v=arrive(u);w(u,v+12,(r(u,v+12)&65535)|(stage<<16))
 assert physical.save(u)==1;physical.load(u)
 assert guardian(u)==stage-5 and not r(u,visit(u)+4);checks+=1
# A completed native battle result is routed once after load, before legacy quest slots.
u=physical.ready_save();v=arrive(u);w(u,v+12,(r(u,v+12)&65535)|(7<<16));w(u,G+81*4,3)
assert physical.save(u)==1;physical.load(u);invoke(u,'we_tick',PARENT)
assert guardian(u)==3 and not r(u,G+81*4);invoke(u,'we_tick',PARENT);assert guardian(u)==3;checks+=1
# A legacy quest result owns its low-bit slot; it cannot strand or advance a guardian.
u=physical.ready_save();v=arrive(u);w(u,v+12,(r(u,v+12)&65535)|(5<<16));w(u,G+81*4,3);w(u,G+82*4,r(u,G+82*4)|1)
assert physical.save(u)==1;physical.load(u);assert guardian(u)==0
invoke(u,'we_tick',PARENT);assert guardian(u)==0 and not r(u,G+81*4);checks+=1
for malformed in (1<<19,101):
 u=physical.ready_save();v=arrive(u);w(u,v+12,malformed)
 assert physical.save(u)==1;physical.load(u)
 assert not r(u,visit(u)) and r(u,state(u)+344)==1;checks+=1
u=physical.ready_save();arrive(u,0);arrive(u,1)
for i in (0,1):w(u,visit(u,i)+12,(r(u,visit(u,i)+12)&65535)|(5<<16))
assert physical.save(u)==1;physical.load(u);assert not r(u,visit(u)) and r(u,state(u)+344)==1;checks+=1

report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),
 coverage=['Four annual3-stage chains, profile routing, deferred/native-menu lifecycle, AA warning and exact-once rewards',
 'Loss/retreat, independent ruins, 360-day reset, eligibility, contact-position guard, failure rollback',
 'Old340B persistence, stage resume/interrupted combat, pendingresult ownership, malformed records failclosed'],
 scoped_mocks=['Shared native UI/Windows APIs and A_BATTLE asynchronous start; separate guardian action suite executes real native battle constructor/board/settlement'],
 not_checked=['Real hardware rendered fights and play balance'])
(ROOT/'test-ruin-guardians-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS annual guardian progression:',checks,'compiled C cases')
