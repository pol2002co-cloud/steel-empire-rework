"""Execute the compiled event C engine against bounded native-world fixtures.

UI, routing and reward-grant boundaries are mocked here. The separate
test_world_event_actions.py executes native grants, battle and save codecs.
"""
from test_patch import *
from world_event_catalog import EVENT_CATALOG
import re,gc

assert 'world_events' in manifest,'Build the integrated world_events module first'
E=manifest['world_events'];EX=E['exports'];STATE=E['state'];ACTION=E['actions']
STOP=0x5ff000;PRINTF=0x5ff100;WORLD=0x1000000;PARENT=0x1001000
CARD=int(STATE['cards_address'],16);BASE=int(STATE['base'],16)
G=0x48d398;HOURS=0x48d388;CASH=(0x46e5d8,0x46e5dc,0x46e5e0)
def tp(i):return 0x2000000+(i-1)*0x60000
def ap(i):return 0x10a0000+i*0x200
def army(i):return 0x1100000+(i-1)*0x6000
def hero(i):return 0x1200000+i*0x1000
def slot(u,i=0):return [r(u,CARD+i*32+j*4) for j in range(8)]
def status(u,i=0):return (r(u,CARD+i*32)>>16)&255
def name(u,p):
 if not p:return ''
 b=bytearray()
 for i in range(10000):
  v=bytes(u.mem_read(p+i,1))[0]
  if not v:return b.decode('cp949')
  b.append(v)
 raise AssertionError('unterminated native string')

def invoke(u,name_or_pc,*args):
 pc=int(EX[name_or_pc],16) if isinstance(name_or_pc,str) else name_or_pc
 sp=0x13e0000;w(u,sp,STOP)
 for i,v in enumerate(args):w(u,sp+4+i*4,v)
 u.reg_write(UC_X86_REG_ESP,sp)
 before={reg:u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)}
 try:u.emu_start(pc,STOP,count=3000000)
 except Exception:
  print('native failure',hex(u.reg_read(UC_X86_REG_EIP)),name_or_pc,args);raise
 assert u.reg_read(UC_X86_REG_EIP)==STOP,hex(u.reg_read(UC_X86_REG_EIP))
 assert u.reg_read(UC_X86_REG_ESP)==sp+4+len(args)*4,(name_or_pc,hex(u.reg_read(UC_X86_REG_ESP)))
 assert before=={reg:u.reg_read(reg) for reg in before},name_or_pc
 return u.reg_read(UC_X86_REG_EAX)

def station(u,a,ident):
 for city in range(1,74):
  for i in range(15):
   if r(u,tp(city)+0x50654+i*4)==a:w(u,tp(city)+0x50654+i*4,0)
 for i in range(100):
  p=r(u,WORLD+0xac+i*4)
  if p and r(u,p+0x808)==a:w(u,WORLD+0xac+i*4,0)
 w(u,a+8,tp(ident));w(u,a+0x10,0)
 w(u,tp(ident)+0x50654+(r(u,a+0x14)-1)*4,a)

def fixture(origin=2):
 u=setup();u.mem_map(0x2000000,0x3000000)
 u.data=dict(answers=[],texts=[],selections=[],battles=[],grants=[],visits=[],machines={1:2,6:2},consumed_machine=[],full=set(),budget={},default_answer=0,deny_jobs=set(),deny_facilities=set(),native_facilities=True,battle_fail=False)
 w(u,0x48c3d8,WORLD);w(u,PARENT,0x462738);w(u,PARENT+0x50,tp(origin))
 w(u,HOURS,2400);w(u,G+11*4,10)
 for addr in CASH:w(u,addr,10000000 if addr==CASH[0] else 100000)
 for city in range(1,74):
  t=tp(city);a=ap(city);country=1 if city==1 else 2+(city-2)%10
  if city==28:country=6
  if city==40:country=8
  if city==63:country=12
  w(u,WORLD+0x23c+(city-1)*4,a);w(u,a+0x7c,t);w(u,a+0x34,city*2);w(u,a+0x38,city%11)
  w(u,t+4,city);w(u,t+8,country);u.mem_write(t+0x14,('도시%d'%city).encode('cp949')+b'\0')
  # Actual native 437880(minID,maxID) walks these real circular building lists.
  bh=t+0x52000;w(u,t+0x50a88,bh);w(u,t+0x50a8c,32)
  w(u,bh,t+0x52100);w(u,bh+4,t+0x52100+31*16)
  for ident in range(1,33):
   node=t+0x52100+(ident-1)*16;p=t+0x53000+(ident-1)*0x300
   w(u,node,bh if ident==32 else node+16);w(u,node+4,bh if ident==1 else node-16);w(u,node+8,p)
   w(u,p+8,1);w(u,p+0xc,ident)
  # Native technology lists are shared immutable fixtures; all 13 basic jobs.
  w(u,t+0x50a04,0x13a0000);w(u,t+0x50a1c,0x13a0000)
  base=0x1300000+city*0x1000;head=base;w(u,t+0x50a58,head)
  w(u,head,base+0x100)
  for job in range(1,14):
   node=base+0x100+(job-1)*16;p=base+0x300+(job-1)*0xb0
   w(u,node,head if job==13 else node+16);w(u,node+8,p)
   for off,val in ((0,job),(8,1),(0x38,job),(0x54,100)):w(u,p+off,val)
 for job in range(1,14):
  node=0x13a0100+(job-1)*16;w(u,node,0x13a0000 if job==13 else node+16);w(u,node+8,job)
 w(u,0x13a0000,0x13a0100)
 head=0x13a1000;node=head+32;p=0x13a2000
 w(u,tp(1)+0x50a4c,head);w(u,head,node);w(u,node,head);w(u,node+8,p)
 for off,val in ((0,14),(8,3),(0x38,3),(0x54,100)):w(u,p+off,val)
 u.mem_write(p+0x18,'비트만'.encode('cp949')+b'\0')
 for i,typ in enumerate((0,1,2,3),1):
  a=army(i);p=hero(i)
  for off,val in ((0,1),(4,tp(1)),(0x14,i),(0x18,typ),(0x1c,1),(0x20,1 if typ in (1,2) else 0),(0x34,p),(0xfc,p)):w(u,a+off,val)
  for off,val in ((0,14+i),(8,3),(0x38,9 if typ==2 else 10 if typ==1 else 3),(0x48,60),(0x54,100)):w(u,p+off,val)
  for j,job in enumerate((8,9,10,11,12,13)):
   support=0x1250000+i*0x1000+j*0xb0
   for off,val in ((0,job),(8,1),(0x10,i),(0x38,job),(0x54,100)):w(u,support+off,val)
   w(u,a+0x60+j*4,support)
  w(u,a+0x1c,7)
  for j,ident in enumerate((1,53,1,53)):w(u,a+0x1a4+j*0x10c,ident)
  station(u,a,origin)
 w(u,0x46019c,PRINTF)
 select_pc=int(manifest['event_journal']['select'],16);speech_pc=int(manifest['event_journal']['speech'],16)
 action_pc={int(ACTION[k],16):k for k in ('battle','give_item','hire','give_machine','find_machine','take_machine')}
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP);d=u.data
  if pc==PRINTF:
   dest=r(u,sp+4);fmt=name(u,r(u,sp+8));idx=[0]
   def sub(m):
    v=r(u,sp+12+idx[0]*4);idx[0]+=1
    return name(u,v) if m.group(0).endswith('s') else str(v if v<0x80000000 else v-0x100000000)
   text=re.sub(r'%[-0-9.]*[dusxX]',sub,fmt);b=text.encode('cp949');u.mem_write(dest,b+b'\0')
   u.reg_write(UC_X86_REG_EAX,len(b));ret(u)
  elif pc==speech_pc:
   d['texts'].append((name(u,r(u,sp+8)),name(u,r(u,sp+12))))
   u.reg_write(UC_X86_REG_EAX,1);ret(u,12)
  elif pc==select_pc:
   labels=r(u,sp+8);n=r(u,sp+12);options=[name(u,r(u,labels+i*4)) for i in range(n)]
   d['selections'].append(options);answer=d['answers'].pop(0) if d['answers'] else d['default_answer']
   u.reg_write(UC_X86_REG_EAX,answer&0xffffffff);ret(u,12)
  elif pc==0x437880 and not d['native_facilities']:
   ident=r(u,sp+4);p=0x13b0000+ident*0x100
   if ident in d['deny_facilities']:p=0
   else:w(u,p+8,1)
   u.reg_write(UC_X86_REG_EAX,p);ret(u,8)
  elif pc==0x4382e0:
   t=u.reg_read(UC_X86_REG_ECX);legion=r(u,sp+4);a=r(u,t+0x50654+(legion-1)*4)
   assert a
   actor=0x1380000+legion*0x1000;w(u,actor+0x808,a);w(u,a+0x10,actor);w(u,a+8,0);w(u,t+0x50654+(legion-1)*4,0)
   for i in range(100):
    if not r(u,WORLD+0xac+i*4):w(u,WORLD+0xac+i*4,actor);break
   u.reg_write(UC_X86_REG_EAX,actor);ret(u,4)
  elif pc==0x4200a0:w(u,u.reg_read(UC_X86_REG_ECX)+0x50,r(u,sp+4));ret(u,4)
  elif pc in action_pc:
   kind=action_pc[pc];argc=3 if kind=='hire' else 2;args=tuple(r(u,sp+4+i*4) for i in range(argc))
   if kind=='find_machine':result=0x13bf000 if d['machines'].get(args[1],0)>0 else 0
   elif kind=='take_machine':
    result=int(d['machines'].get(args[1],0)>0)
    if result:d['machines'][args[1]]-=1;d['consumed_machine'].append(args)
   elif kind=='battle':
    d['battles'].append(args);result=0 if d['battle_fail'] else 1
   else:
    result=2 if kind in d['full'] or d['budget'].get(kind,1)==0 else 1
    if result==1:
     d['grants'].append((kind,args))
     if kind in d['budget']:d['budget'][kind]-=1
   u.reg_write(UC_X86_REG_EAX,result);ret(u,argc*4)
 u.hook_add(UC_HOOK_CODE,boundary)
 invoke(u,int(STATE['init'],16),100)
 return u

def offer(u,ident,stage=0,origin=None):
 origin=origin or (1 if ident in (30,35) else 28 if ident==31 else 40 if ident==32 else 2)
 for i in range(8):w(u,CARD+i*4,0)
 w(u,CARD,ident|(stage<<8)|(1<<16));w(u,CARD+4,origin)
 w(u,PARENT+0x50,tp(origin))
 for i in range(1,5):station(u,army(i),origin)
 w(u,int(STATE['done_address'],16),0xffffffff^(1<<ident) if ident<32 else 0xffffffff)
 high=(1<<(len(EVENT_CATALOG)-32))-1
 w(u,int(STATE['done_address'],16)+4,high^(1<<(ident-32)) if ident>=32 else high)
 for index,val in ((5,10),(20,1),(21,1),(85,0x42505231),(84,0x3fffff00),(87,0x3fffffff)):w(u,G+index*4,val)

def travel(u):
 c=slot(u)
 if c[2]:
  u.data['visits'].append(c[2])
  a=army(c[4]) if c[4] else army(1)
  station(u,a,c[2]);w(u,PARENT+0x50,tp(c[2]))
 invoke(u,'we_test_progress')

def advance_month(u):
 hours=r(u,HOURS)+720;w(u,HOURS,hours)
 invoke(u,int(STATE['tick'],16),hours//24,hours//720)

def route(u,answers):
 u.data['answers']=list(answers);u.data['default_answer']=-1
 try:return invoke(u,'we_router',PARENT)
 finally:u.data['default_answer']=0

checks=0
def run_event(ident,preferred=0,overrides=None):
 global checks
 u=fixture();offer(u,ident);steps=0;used={}
 story=bytes(u.mem_read(G,31*4))
 ownership=[(r(u,tp(i)+8),r(u,tp(i)+0x10),r(u,ap(i)+0x14)) for i in range(1,74)]
 while status(u) and steps<35:
  steps+=1;c=slot(u);stage=(c[0]>>8)&255;s=EVENT_CATALOG[ident]['stages'][stage]
  if status(u)==1:
   history=used.setdefault(stage,[])
   choice=preferred if not history and preferred<len(s['choices']) else 0
   if overrides and stage in overrides and not history:choice=overrides[stage]
   if ident==34 and stage==0:choice=next((i for i in range(3) if i not in history),0)
   history.append(choice)
   origin=c[1];w(u,PARENT+0x50,tp(origin))
   for i in range(1,5):station(u,army(i),origin)
   result=invoke(u,'we_test_accept',PARENT,0,choice)
   if not result:
    advance_month(u);result=invoke(u,'we_test_accept',PARENT,0,choice)
   assert result,(ident,stage,choice,slot(u),u.data['texts'][-3:])
  for _ in range(12):
   c=slot(u)
   if status(u)!=2:break
   if c[2]:travel(u);continue
   flags=c[0]>>24
   ch=s['choices'][(c[7]>>24)&255]['actions']
   if ch.get('battle_profile') and not flags&2:
    if r(u,G+82*4)==0:
     route(u,[1,0,0])
     if not r(u,G+82*4):
      advance_month(u);route(u,[1,0,0])
     assert r(u,G+82*4),(ident,'battle retry',slot(u),u.data['texts'][-3:])
    w(u,G+81*4,3)
   invoke(u,'we_test_progress')
  if status(u)==3:
   assert invoke(u,'we_test_claim',PARENT,0),(ident,'claim',slot(u),u.data['texts'][-3:])
 assert status(u)==0,(ident,'unfinished',slot(u),u.data['texts'][-4:])
 assert bytes(u.mem_read(G,31*4))==story,(ident,'original story globals changed')
 assert ownership==[(r(u,tp(i)+8),r(u,tp(i)+0x10),r(u,ap(i)+0x14)) for i in range(1,74)],(ident,'ownership changed')
 assert invoke(u,int(STATE['completed'],16),ident)==1
 before=tuple(r(u,p) for p in CASH),len(u.data['grants'])
 assert invoke(u,'we_test_claim',PARENT,0)==0
 assert before==(tuple(r(u,p) for p in CASH),len(u.data['grants']))
 if ident==20:
  countries=[r(u,tp(i)+8) for i in u.data['visits']]
  assert len(countries)==6 and len(set(countries))==6,countries
 checks+=1
 return u

def reload(u):
 bank=bytes(u.mem_read(G+31*4,57*4));money=[r(u,p) for p in CASH]
 hours=r(u,HOURS);current=[(r(u,army(i)+8)-0x2000000)//0x60000+1 for i in range(1,5)]
 v=fixture();v.mem_write(G+31*4,bank);w(v,HOURS,hours)
 for p,value in zip(CASH,money):w(v,p,value)
 for i,ident in enumerate(current,1):
  if 1<=ident<=73:station(v,army(i),ident)
 v.data['grants']=list(u.data['grants']);v.data['machines']=dict(u.data['machines']);v.data['consumed_machine']=list(u.data['consumed_machine']);return v

def critical():
 global checks
 # Pending item rewards retain the already-paid currency over repeated claims
 # and a simulated load of the exact stock script bank.
 u=fixture();offer(u,19);u.data['full'].add('give_item');gold=r(u,CASH[0])
 assert invoke(u,'we_test_accept',PARENT,0,0)==0 and status(u)==3
 assert r(u,CASH[0])==gold+60000
 for _ in range(3):assert invoke(u,'we_test_claim',PARENT,0)==0
 assert r(u,CASH[0])==gold+60000
 v=reload(u);assert invoke(v,'we_test_claim',PARENT,0)==1
 assert len(v.data['grants'])==1 and r(v,CASH[0])==gold+60000
 assert invoke(v,'we_test_claim',PARENT,0)==0;checks+=1

 # Partial recruitment resumes only the two remaining paid-for soldiers.
 u=fixture();offer(u,13);u.data['budget']['hire']=1;gold=r(u,CASH[0])
 assert invoke(u,'we_test_accept',PARENT,0,0)==0 and status(u)==3
 assert len(u.data['grants'])==1 and r(u,CASH[0])==gold-24000
 v=reload(u);assert invoke(v,'we_test_claim',PARENT,0)==1
 assert len(v.data['grants'])==3 and all(k=='hire' for k,a in v.data['grants'])
 assert r(v,CASH[0])==gold-24000;checks+=1

 # Currency capacity waits; the acceptance cost is never paid a second time.
 u=fixture();offer(u,0);w(u,CASH[0],2000000000-1000);iron=r(u,CASH[1])
 assert invoke(u,'we_test_accept',PARENT,0,0)==0 and status(u)==3
 assert r(u,CASH[1])==iron-40
 assert invoke(u,'we_test_claim',PARENT,0)==0 and r(u,CASH[1])==iron-40
 w(u,CASH[0],1000000);assert invoke(u,'we_test_claim',PARENT,0)==1
 assert r(u,CASH[0])==1024000 and r(u,CASH[1])==iron-40;checks+=1

 # Loss and retreat cannot pay a combat reward; retrying the same contract
 # neither recharges nor consumes a second monthly combat allowance.
 u=fixture();offer(u,24);money=tuple(r(u,p) for p in CASH)
 assert invoke(u,'we_test_accept',PARENT,0,0)==2
 for result in (1,2):
  w(u,G+81*4,result);invoke(u,'we_test_progress')
  assert status(u)==2 and tuple(r(u,p) for p in CASH)==money
  assert invoke(u,'we_test_claim',PARENT,0)==0
  route(u,[1,0,0]);assert r(u,G+82*4)==1
 assert len(u.data['battles'])==3 and r(u,int(STATE['battles_address'],16))==1
 w(u,G+81*4,3);invoke(u,'we_test_progress');assert status(u)==3
 assert invoke(u,'we_test_claim',PARENT,0)==1
 assert r(u,CASH[0])==money[0]+150000;checks+=1

 # An interrupted battle card permits retry after loading; it never silently
 # records a victory just because its transient native battle is gone.
 u=fixture();offer(u,24);assert invoke(u,'we_test_accept',PARENT,0,0)==2
 v=reload(u);invoke(v,'we_tick',PARENT)
 assert status(v)==2 and r(v,G+82*4)==0
 route(v,[1,0,0]);assert r(v,G+82*4)==1 and len(v.data['battles'])==1;checks+=1

 # Final air-defense AS6 gift waits independently after money/oil are paid.
 u=fixture();offer(u,31,stage=2,origin=28);u.data['full'].add('give_machine');gold=r(u,CASH[0]);oil=r(u,CASH[2])
 assert invoke(u,'we_test_accept',PARENT,0,0)==2
 w(u,G+81*4,3);invoke(u,'we_test_progress');assert status(u)==3
 assert invoke(u,'we_test_claim',PARENT,0)==0
 assert (r(u,CASH[0]),r(u,CASH[2]))==(gold+200000,oil+100)
 v=reload(u);assert invoke(v,'we_test_claim',PARENT,0)==1
 assert v.data['grants']==[('give_machine',(tp(1),24))]
 assert (r(v,CASH[0]),r(v,CASH[2]))==(gold+200000,oil+100);checks+=1

 # Native F8 routing preserves the old journal, supports closing, and exposes
 # the new catalog before ending without activating any event state.
 u=fixture();assert route(u,[0])==0 and route(u,[2])==1
 w(u,G+11*4,0);before_story=bytes(u.mem_read(G,31*4))
 assert route(u,[1,-1])==1 and bytes(u.mem_read(G,31*4))==before_story
 before=bytes(u.mem_read(BASE,216));w(u,G+11*4,10);w(u,G+19*4,1);invoke(u,'we_tick',PARENT)
 assert bytes(u.mem_read(BASE,216))==before;checks+=1

 # Scheduler creates records without popup spam and respects the three-card
 # and one-active-combat bounds even after a long date advance.
 u=fixture();u.data['texts'].clear()
 for _ in range(5):
  day=r(u,int(STATE['next_offer_address'],16));w(u,HOURS,day*24)
  invoke(u,'we_tick',PARENT)
  active=[slot(u,i)[0] for i in range(3) if status(u,i)]
  assert len(active)<=3 and sum(bool(x&0x80000000) for x in active)<=1
  assert len({x&255 for x in active})==len(active)
 assert not u.data['texts'] and sum(bool(status(u,i)) for i in range(3))==3;checks+=1

 # Safe route selection must not choose hostile or protected cities for an
 # ordinary noncombat delivery when an accessible alternative exists.
 u=fixture();offer(u,6)
 for ident in (1,3):w(u,ap(ident)+0x14,1);w(u,tp(ident)+0x10,1)
 w(u,tp(4)+0x10,2)
 assert invoke(u,'we_test_accept',PARENT,0,0)==1
 assert slot(u)[2] not in (1,3,4);checks+=1

 # An HQ rebuilding mission uses an ordinary liaison city instead of marching
 # into the hostile headquarters and starting an unrequested conquest fight.
 u=fixture();offer(u,30);w(u,ap(63)+0x14,1);w(u,tp(63)+0x10,1)
 assert invoke(u,'we_test_accept',PARENT,0,0)==1
 assert 1<=slot(u)[2]<=62;checks+=1

 # Refusing a partially paid reward or a later stage after an earlier reward
 # cannot discard the deduplication record and reopen profitable repeats.
 u=fixture();offer(u,19);u.data['full'].add('give_item')
 assert invoke(u,'we_test_accept',PARENT,0,0)==0
 before=slot(u);money=tuple(r(u,p) for p in CASH)
 route(u,[1,0,4,0]);assert slot(u)==before and tuple(r(u,p) for p in CASH)==money;checks+=1
 u=fixture();offer(u,10);assert invoke(u,'we_test_accept',PARENT,0,0)==1
 travel(u);assert status(u)==3 and invoke(u,'we_test_claim',PARENT,0)==1
 assert status(u)==1 and ((slot(u)[0]>>8)&255)==1
 before=slot(u);money=tuple(r(u,p) for p in CASH)
 expected=before[:];expected[5]|=1<<30 # Viewing only acknowledges this new-stage notice.
 route(u,[1,0,2]);assert slot(u)==expected and tuple(r(u,p) for p in CASH)==money;checks+=1

 u=fixture();offer(u,0);w(u,CASH[1],39);before=slot(u);money=tuple(r(u,p) for p in CASH)
 assert invoke(u,'we_test_accept',PARENT,0,0)==0 and slot(u)==before
 assert tuple(r(u,p) for p in CASH)==money;checks+=1

 # F6's later tiers require other event records, not merely advancing dates.
 u=fixture();offer(u,35,origin=1)
 done_address=int(STATE['done_address'],16)
 w(u,done_address,(1<<12)-1);w(u,done_address+4,0)
 assert invoke(u,'we_test_accept',PARENT,0,0)==1
 assert status(u)==1 and ((slot(u)[0]>>8)&255)==1
 before=slot(u);money=tuple(r(u,p) for p in CASH)
 advance_month(u)
 assert invoke(u,'we_test_accept',PARENT,0,0)==0 and slot(u)==before
 assert tuple(r(u,p) for p in CASH)==money
 w(u,done_address,(1<<24)-1)
 assert invoke(u,'we_test_accept',PARENT,0,0)==1
 assert status(u)==1 and ((slot(u)[0]>>8)&255)==2
 assert invoke(u,'we_test_accept',PARENT,0,0)==0
 w(u,done_address,0xffffffff);w(u,done_address+4,7)
 assert invoke(u,'we_test_accept',PARENT,0,0)==0
 w(u,done_address,0xffffffff);w(u,done_address+4,((1<<(len(EVENT_CATALOG)-32))-1)^8)
 assert invoke(u,'we_test_accept',PARENT,0,0)==1 and status(u)==0
 assert invoke(u,int(STATE['count_completed'],16))==len(EVENT_CATALOG);checks+=1

 def aim(u,ident):
  seed=next(s for s in range(10000) if (((s*1664525+1013904223)&0xffffffff)%len(EVENT_CATALOG))==ident)
  w(u,int(STATE['rng_address'],16),seed)
 def proposed(mode):
  u=fixture();day=r(u,int(STATE['next_offer_address'],16));w(u,HOURS,day*24);aim(u,24)
  invoke(u,'we_tick',PARENT)
  assert status(u)==1 and (slot(u)[0]&255)==24 and slot(u)[0]&0x80000000
  assert r(u,int(STATE['battles_address'],16))==2
  origin=slot(u)[1];w(u,PARENT+0x50,tp(origin))
  for i in range(1,5):station(u,army(i),origin)
  if mode=='decline':route(u,[1,0,3]);assert status(u)==0
  elif mode=='peaceful':assert invoke(u,'we_test_accept',PARENT,0,1)==1 and status(u)==0
  else:
   assert invoke(u,'we_test_accept',PARENT,0,0)==2
   assert r(u,int(STATE['battles_address'],16))==3
   w(u,G+81*4,3);invoke(u,'we_test_progress')
   assert invoke(u,'we_test_claim',PARENT,0)==1 and status(u)==0
  # A new week is still in the same month, so a new combat proposal is barred.
  day=r(u,int(STATE['next_offer_address'],16));w(u,HOURS,day*24);aim(u,27)
  invoke(u,'we_tick',PARENT)
  assert not any(slot(u,i)[0]&0x80000000 for i in range(3) if status(u,i))
  # A later month releases the proposal quota without erasing the cooldown.
  for i in range(3):invoke(u,int(STATE['clear'],16),i)
  month=r(u,HOURS)//720+1;w(u,HOURS,month*720);w(u,int(STATE['next_offer_address'],16),month*30)
  aim(u,27);invoke(u,'we_tick',PARENT)
  assert status(u)==1 and slot(u)[0]&0x80000000
  assert r(u,int(STATE['battles_address'],16))==2
  return u
 for mode in ('decline','peaceful','win'):proposed(mode);checks+=1

 # Facility tests execute the actual two-argument native function, including
 # family upgrades and construction state, so a ret4 mock cannot mask ABI bugs.
 def remove_building(u,city,ident):
  node=tp(city)+0x52100+(ident-1)*16;next_node=r(u,node);prev=r(u,node+4)
  w(u,prev,next_node);w(u,next_node+4,prev);w(u,tp(city)+0x50a8c,r(u,tp(city)+0x50a8c)-1)
 u=fixture();u.reg_write(UC_X86_REG_ECX,tp(2))
 p=invoke(u,0x437880,7,9);assert r(u,p+0xc)==7
 remove_building(u,2,7);remove_building(u,2,8)
 u.reg_write(UC_X86_REG_ECX,tp(2));p=invoke(u,0x437880,7,9);assert r(u,p+0xc)==9
 assert invoke(u,'we_test_prerequisite',36,2)==1
 for state,expected in ((2,0),(3,1),(0,0),(1,1)):
  w(u,p+8,state);assert invoke(u,'we_test_prerequisite',36,2)==expected;checks+=1
 remove_building(u,2,9);assert invoke(u,'we_test_prerequisite',36,2)==0;checks+=1
 u=fixture();remove_building(u,2,17)
 assert invoke(u,'we_test_prerequisite',4,2)==1
 remove_building(u,2,18);assert invoke(u,'we_test_prerequisite',4,2)==0;checks+=1

 # Early contracts are available without ending, while postwar chains stay
 # gated. The scheduler itself is checked, not just the catalog's declaration.
 u=fixture();w(u,G+11*4,0)
 assert invoke(u,'we_test_prerequisite',36,2)==1
 assert invoke(u,'we_test_prerequisite',31,28)==0
 day=r(u,int(STATE['next_offer_address'],16));w(u,HOURS,day*24);aim(u,36)
 invoke(u,'we_tick',PARENT)
 assert status(u)==1 and (slot(u)[0]&255)==36;checks+=1

 # Aircraft/tank cargo remains in stock during travel and is consumed exactly
 # once on final settlement, including changed stock and pending cash/reload.
 for ident,machine in ((36,6),(37,1)):
  u=fixture();offer(u,ident);u.data['machines'][machine]=0;money=tuple(r(u,p) for p in CASH)
  assert invoke(u,'we_test_accept',PARENT,0,0)==0 and status(u)==1
  assert tuple(r(u,p) for p in CASH)==money
  u.data['machines'][machine]=1
  if ident==37:u.data['answers']=[3,0]
  assert invoke(u,'we_test_accept',PARENT,0,0)==1
  if ident==37:assert slot(u)[4]==4
  assert u.data['machines'][machine]==1 and not u.data['consumed_machine']
  u.data['machines'][machine]=0;travel(u);assert status(u)==3
  assert invoke(u,'we_test_claim',PARENT,0)==0 and tuple(r(u,p) for p in CASH)==money
  u.data['machines'][machine]=1;w(u,CASH[0],2000000000)
  assert invoke(u,'we_test_claim',PARENT,0)==0 and u.data['machines'][machine]==0
  assert u.data['consumed_machine']==[(tp(1),machine)]
  v=reload(u);w(v,CASH[0],1000000)
  assert invoke(v,'we_test_claim',PARENT,0)==1 and status(v)==0
  assert v.data['consumed_machine']==[(tp(1),machine)]
  assert invoke(v,'we_test_claim',PARENT,0)==0;checks+=1
 u=fixture();offer(u,13);w(u,tp(1)+0x50a5c,9999);money=tuple(r(u,p) for p in CASH)
 assert invoke(u,'we_test_accept',PARENT,0,0)==0 and status(u)==1
 assert tuple(r(u,p) for p in CASH)==money;checks+=1

if __name__=='__main__':
 from test_world_event_simple import run_all
 import hashlib,datetime
 checks=run_all()
 print('PASS compiled world events:',checks,'all38 simple goals, old active-card migration, native ABI and reward deduplication')
 report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),version=manifest['version'],test='test_world_events_native.py',event_count=len(EVENT_CATALOG),tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scoped_mocks=['UI and formatting','Route departure/target and explicit arrival','Atomic grant/battle boundaries, separately tested by native action suite','Windows notice APIs and heap boundaries for deferred automatic claims'],not_checked=['Hardware visual playtest','Full real save-file roundtrip'])
 (ROOT/'test-world-native-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
