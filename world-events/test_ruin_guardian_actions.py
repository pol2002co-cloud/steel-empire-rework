"""Actual native guardian construction, visible deployment and world settlement."""
from test_world_event_actions import *
from ruin_guardians import GUARDIANS
from collections import Counter
import hashlib,json

CHAR_DATA=(ROOT/'extracted/Data.pak/char.dat').read_bytes()
ITEM_DATA=(ROOT/'extracted/Data.pak/item.dat').read_bytes()
checks=0

def guardian_fixture():
 u=fixture();u.guard_equips=[]
 # Use real qualifications and item restrictions rather than the broad house mocks.
 for ident in range(1,83):
  raw=4+(ident-1)*288;p=IRECS+(ident-1)*0x10c
  w(u,p+0x24,struct.unpack_from('<I',ITEM_DATA,raw+32)[0])
  w(u,p+0x2c,struct.unpack_from('<I',ITEM_DATA,raw+40)[0])
 def qualifications(u,pc,size,data):
  if pc==0x414ed0:
   p=u.reg_read(UC_X86_REG_EAX)
   if p:
    job=r(u,p+0x38);mask=struct.unpack_from('<I',CHAR_DATA,4+(job-1)*348+104)[0]*2|(1<<job)
    w(u,p+0x44,mask)
  elif pc==0x415aa0:
   sp=u.reg_read(UC_X86_REG_ESP);p=r(u,sp+4);item=r(u,sp+12)
   u.guard_equips.append((p,r(u,item)))
 u.hook_add(UC_HOOK_CODE,qualifications)
 return u

def people(u,a):return [r(u,a+0x60+i*4) for i in range(81) if r(u,a+0x60+i*4)]
def machines(u,a):return [r(u,a+0x3c+i*4) for i in range(9) if r(u,a+0x3c+i*4)]

def board(u,b):
 created=[]
 def models(u,pc,size,data):
  if pc in (0x43d730,0x43f2a0,0x4408e0):
   sp=u.reg_read(UC_X86_REG_ESP);p=u.reg_read(UC_X86_REG_ECX)
   created.append((pc,r(u,sp+8),r(u,sp+16),p))
   w(u,p+0x138,1);w(u,p+0x50,50);u.reg_write(UC_X86_REG_EAX,p);ret(u,16)
 u.hook_add(UC_HOOK_CODE,models);call(u,0x43a5a0,this=b)
 return created

# Every authored formation is fixed-level, boss-free, fully staffed and truly rendered.
for g in GUARDIANS:
 u=guardian_fixture();w(u,HERO+0x48,1 if g['ruin']%2 else 99)
 snapshot=bytes(u.mem_read(TOWN,0x51000))
 assert call(u,'battle',ARMY,g['profile'])==1,g['name']
 b=u.frames[0];a=r(u,b+0x50);ps=people(u,a);ms=machines(u,a)
 assert r(u,a+0x18)==g['army_type'] and r(u,a+0x1c)==len(ps)==(80,9,25)[g['stage']-1]
 assert len(ms)==r(u,a+0x20)==len(g['machines']) and len(set(ps))==len(ps) and len(set(ms))==len(ms)
 assert r(u,a+0x34) in ps and r(u,a+0x55ac)==A.TEMP_MAGIC and r(u,a+8)==0
 assert all(r(u,p+0x48)==g['level'] and r(u,p+8)==0 and r(u,p+0x10)==15 for p in ps)
 expected=Counter(job for job,weapon in g['foot'])
 if ms:expected[9 if g['stage']==2 else 10]+=len(ms)
 assert Counter(r(u,p+0x38) for p in ps)==expected
 assert Counter(r(u,m+4) for m in ms)==Counter(g['machines'])
 assert all(r(u,m+0x50) in (0,1) and not 17<=r(u,m+4)<=21 and r(u,m+0x8c) in ps for m in ms)
 assert all(r(u,m+0x50)==(1 if g['stage']==2 else 0) for m in ms)
 assert Counter((r(u,p+0x38),ident) for p,ident in u.guard_equips)==Counter(g['foot'])
 assert bytes(u.mem_read(TOWN,0x51000))==snapshot
 owned={p for p,size in u.allocs if p!=b};call(u,'destroy',a)
 assert set(u.freed)==owned and len(u.freed)==len(set(u.freed))
 assert bytes(u.mem_read(TOWN,0x51000))==snapshot;checks+=1

 u=guardian_fixture();assert call(u,'battle',ARMY,g['profile'])==1
 b=u.frames[0];a=r(u,b+0x50);ps=people(u,a);ms=machines(u,a);models=board(u,b)
 enemy=[m for m in models if m[1]==a]
 assert len(enemy)==len(g['foot'])+len(g['machines']),g['name']
 assert len({p for pc,a,rec,p in enemy})==len(enemy)
 assert {rec for pc,a,rec,p in enemy if pc!=0x43d730}==set(ms)
 assert {rec for pc,a,rec,p in enemy if pc==0x43d730}==set(ps)-{r(u,m+0x8c) for m in ms}
 assert r(u,b+0x200) and r(u,b+0x204) and r(u,b+0x4b0)==0
 assert sum(r(u,b+0x36c+i*4)!=0 for i in range(81))==len(enemy)
 checks+=1

# All military army types can fight the air stage; no movement or city ownership changes.
for kind in (0,1,2):
 u=guardian_fixture();w(u,ARMY+0x18,kind)
 snapshot=bytes(u.mem_read(TOWN,0x51000));assert call(u,'battle',ARMY,7)==1
 assert r(u,ARMY+8)==TOWN and bytes(u.mem_read(TOWN,0x51000))==snapshot;checks+=1

# Allocation and late equipment failures dispose only the private partially built enemy.
for g in GUARDIANS:
 for size in (0x55b0,0x4e4,0xe54)+((0x1a8,) if g['machines'] else ()):
  u=guardian_fixture();snapshot=bytes(u.mem_read(TOWN,0x51000));u.fail[0]=size
  assert not call(u,'battle',ARMY,g['profile']) and not u.frames
  assert {p for p,size in u.allocs}==set(u.freed) and len(u.freed)==len(set(u.freed))
  assert bytes(u.mem_read(TOWN,0x51000))==snapshot;checks+=1
 u=guardian_fixture();snapshot=bytes(u.mem_read(TOWN,0x51000));seen=[0]
 def late_person(u,pc,size,data):
  if pc==0x414ed0:
   seen[0]+=1
   if seen[0]==3:u.fail[0]=0x4e4
 u.hook_add(UC_HOOK_CODE,late_person)
 assert not call(u,'battle',ARMY,g['profile']) and not u.frames
 assert {p for p,size in u.allocs}==set(u.freed) and len(u.freed)==len(set(u.freed))
 assert bytes(u.mem_read(TOWN,0x51000))==snapshot;checks+=1
 if g['foot']:
  u=guardian_fixture();snapshot=bytes(u.mem_read(TOWN,0x51000));seen=[0]
  def late_item(u,pc,size,data):
   if pc==0x4162b0:
    seen[0]+=1
    if seen[0]==3:u.reg_write(UC_X86_REG_EAX,0);ret(u,8)
  u.hook_add(UC_HOOK_CODE,late_item)
  assert not call(u,'battle',ARMY,g['profile']) and not u.frames
  assert {p for p,size in u.allocs}==set(u.freed) and len(u.freed)==len(set(u.freed))
  assert bytes(u.mem_read(TOWN,0x51000))==snapshot;checks+=1

# Run the real settlement and world actor removal for each outcome and each enemy type.
for profile in (6,7,8):
 for outcome in ('loss','retreat','win'):
  u=guardian_fixture();wrld=0x13c0000;actor=0x13c1000;head=0x13c2000;vt=0x13b1000;music=0x13b1100
  for off in (0xac,0x84,0x80):w(u,wrld+off,actor)
  w(u,0x48c3d8,wrld);w(u,wrld+0x3d4,head);w(u,head,head);w(u,head+4,head)
  w(u,ARMY+8,0);w(u,ARMY+0x10,actor);w(u,actor,vt);w(u,actor+0x808,ARMY)
  assert call(u,'battle',ARMY,profile)==1
  b=u.frames[0];a=r(u,b+0x50)
  assert r(u,b+0x48)==TOWN and r(u,b+0x1e4)==0 and r(u,b+0x1e8)==0
  assert r(u,ARMY+8)==0 and r(u,ARMY+0x10)==actor
  au=0x12c0000;eu=0x12c1000
  for p in (au,eu):w(u,p,vt);w(u,p+0x138,1);w(u,p+0x50,50)
  w(u,au+0x138,0 if outcome=='loss' else 1);w(u,eu+0x138,0 if outcome=='win' else 1)
  w(u,b+0x200,au);w(u,b+0x204,eu);w(u,b+0x228,au);w(u,b+0x36c,eu)
  w(u,0x476fd8,music);w(u,music,vt);w(u,vt+0xc,0x5fc100);w(u,vt+0x14,0x5fc120);w(u,vt,0x5fc140);w(u,HERO+8,3)
  w(u,TOWN+0x509f8,17);calls=[]
  def virtual(u,pc,size,data):
   if pc==0x5fc100:ret(u)
   elif pc==0x5fc120:
    sp=u.reg_read(UC_X86_REG_ESP);calls.append((r(u,sp+4),r(u,sp+8),r(u,sp+12)));ret(u,12)
   elif pc==0x5fc140:ret(u,4)
   elif pc==0x45046d:u.reg_write(UC_X86_REG_EAX,0);ret(u)
  u.hook_add(UC_HOOK_CODE,virtual);call(u,0x439680,this=b)
  assert r(u,int(u.actions['result_address'],16))=={'loss':1,'retreat':2,'win':3}[outcome]
  assert r(u,wrld+0xac)==(0 if outcome=='loss' else actor)
  assert r(u,TOWN+0x509f8)==17+(outcome=='loss')
  assert calls and all(message==0x7e6 and stationed==0 for message,lucky,stationed in calls)
  assert a in u.freed and len(u.freed)==len(set(u.freed));checks+=1

for address,value in ((ARMY,12),(ARMY+4,0),(ARMY+0x18,3),(ARMY+0x34,0),(HERO+4,1),(HERO+0x54,0),(ARMY+0x14,0),(0x48cc1c,0)):
 u=guardian_fixture();w(u,address,value)
 if address==ARMY+4:w(u,ARMY+8,0)
 assert not call(u,'battle',ARMY,8) and not u.frames and not u.allocs;checks+=1
for profile in (0,18,0xffffffff):
 u=guardian_fixture();assert not call(u,'battle',ARMY,profile) and not u.allocs;checks+=1

report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest() if '--integrated' in sys.argv else None,
 integrated='--integrated' in sys.argv,coverage=['Twelve full ordinary fixed30/40/50 formations with real class/item eligibility',
 'Real43a5a0 deployment:80foot,9air,7armor+18foot, complete visible models and both commanders',
 'Ground/armor/air players against air guards; native world439680/420b70/437fc0 loss,retreat,win',
 'Partial enemy/frame/equipment failures, unique cleanup and unchanged player/city ownership'],
 scoped_mocks=['House character allocation preserves real qualification masks; original equipment and crew routines execute',
 'Windows/UI/graphics model constructors and virtual model casualty/draw destructors are mocked'],
 not_checked=['Rendered hardware combat and interactive attack/AI behavior','Actual per-unit damage/death virtual callbacks and campaign balance win rates'])
(ROOT/'test-ruin-guardian-actions-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS ruin guardian actions:',checks,'native formation, deployment, failure and world settlement cases')
