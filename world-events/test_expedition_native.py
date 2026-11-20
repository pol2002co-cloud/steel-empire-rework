"""Compiled expedition/annual ruin progression through real deferred UI."""
from test_world_event_simple import *
from expedition_catalog import MISSIONS,RECIPES
from ruin_visits import RUINS
from world_event_state import MONTH_NOTICE_SHOWN
import hashlib,json,datetime

KEY='SteelEmpireRework.Expeditions.0130'
PEOPLE=0x1400000;MASTERS=PEOPLE;WAITING=PEOPLE+0x100;HEROES=PEOPLE+0x1000;GENERICS=PEOPLE+0x10000
CTX=PEOPLE+0x9000;THREAD=0x13c7000
SAVE_BYTES=340;RUN=24;VISIT=216
checks=0

def ring(u,head,persons,nodes):
 w(u,head,nodes if persons else head);w(u,head+4,nodes+(len(persons)-1)*16 if persons else head)
 for i,p in enumerate(persons):
  node=nodes+i*16;w(u,node,node+16 if i+1<len(persons) else head);w(u,node+4,node-16 if i else head);w(u,node+8,p)

def person(u,p,ident,kind,job=3,level=20,skill=40):
 for offset,value in ((0,ident),(4,0),(8,kind),(0x10,0),(0x14,0),(0x38,job),(0x44,1<<job),(0x48,level),
                      (0x4c,0),(0x50,100),(0x54,100),(0x58,100),(0x60,30),(0x64,30),(0x68,30),(0x6c,30),(0x70,skill)):
  w(u,p+offset,value)
 u.mem_write(p+0x18,('Hero%d'%ident if kind==3 else 'Mercenary%d'%ident).encode()+b'\0')

def ready(heroes=5,generics=25,level=20,skill=40):
 u=fresh();u.mem_map(PEOPLE,0x40000);attach_queue(u)
 u.exp_awards=[];u.exp_fail_alloc=False;u.exp_allocs=[]
 u.simple_queue['next_heap']=0x1420000
 def boundaries(u,pc,size,data):
  if pc==0x450452:
   # Common WinAPI fixture has already returned; widen its arena allocation.
   sp=u.reg_read(UC_X86_REG_ESP);amount=r(u,sp);p=u.reg_read(UC_X86_REG_EAX)
   u.simple_queue['next_heap']=p+max(32,(amount+15)&~15)
   u.exp_allocs.append((p,amount))
   if u.exp_fail_alloc:u.reg_write(UC_X86_REG_EAX,0)
  elif pc==0x45290b:u.reg_write(UC_X86_REG_EAX,THREAD);ret(u)
  elif pc==0x414fc0:
   p=r(u,u.reg_read(UC_X86_REG_ESP)+4);u.exp_awards.append((p,r(u,p+0x4c)))
  elif pc==0x438a80:ret(u,4)
 u.hook_add(UC_HOOK_CODE,boundaries)
 w(u,THREAD+0x14,0xabcde123)
 hp=[HEROES+i*0x500 for i in range(heroes)];gp=[GENERICS+i*0x500 for i in range(generics)]
 for i,p in enumerate(hp):person(u,p,30+i,3,3,level,skill)
 for i,p in enumerate(gp):person(u,p,2,1,(8,10,11,12,3)[i%5],level,skill)
 ring(u,MASTERS,hp,PEOPLE+0x200);ring(u,WAITING,gp,PEOPLE+0x400)
 for offset,value in ((0xa0,0),(0x50a4c,MASTERS),(0x50a50,heroes),(0x50a58,WAITING),(0x50a5c,generics)):
  w(u,tp(1)+offset,value)
 u.exp_heroes=hp;u.exp_generics=gp
 return u

def state(u):return invoke(u,'we_test_ex_state')
def run(u,index=0):return state(u)+RUN+index*48
def visit(u,index=0):return state(u)+VISIT+index*28
def values(u,p,count):return [r(u,p+i*4) for i in range(count)]
def shift(u,days):w(u,HOURS,r(u,HOURS)+days*24)
def xorshift(n):
 n^=(n<<13)&0xffffffff;n^=n>>17;n^=(n<<5)&0xffffffff
 return n&0xffffffff
def seed_for(mod):
 return next(n for n in range(1,10000) if xorshift(n)%100==mod and (xorshift(n)>>8)%100>=30)
def start(u,mission=0,ruin=0,roll=30,chief=None):
 s=state(u);w(u,s+8,seed_for(roll))
 return invoke(u,'we_test_ex_start',mission,ruin,chief or HEROES)
def pump_ex(u):
 # The season suite checks the separate monthly notice sharing this message queue.
 mark=G+38*4;w(u,mark,r(u,mark)|MONTH_NOTICE_SHOWN)
 q=u.simple_queue;before=len(q['posts'])
 invoke(u,'we_idle',PARENT);q['ticks']+=1000;invoke(u,'we_idle',PARENT)
 if len(q['posts'])==before:return False
 invoke(u,'we_message',*q['posts'][-1]);return True
def advance(u,days):shift(u,days);invoke(u,'we_tick',PARENT)
def visit_ruin(u,index=0):
 w(u,CTX,PARENT)
 if index<3:
  ident=RUINS[index][1];station(u,army(1),ident);w(u,PARENT+0x50,tp(ident))
 else:w(u,CTX+0x1e0,army(1))
 invoke(u,'we_ruin_visit',CTX,index)
 return visit(u,index)
def visit_cleared_ruin(u,index=0):
 # Reward component fixtures start after guardian victory; the dedicated suite fights all3 stages.
 v=visit_ruin(u,index);w(u,v+12,(r(u,v+12)&65535)|(3<<16));return v
def discover(u,index=0):w(u,visit(u,index),1)
def clone_runtime(u):
 v=ready();s=state(u);other=state(v)
 for address,size in ((tp(1),0x51000),(PEOPLE,0x40000)):
  v.mem_write(address,bytes(u.mem_read(address,size)))
 for address in (*CASH,HOURS):w(v,address,r(u,address))
 v.simple_queue['properties'][(0x123456,KEY)]=s
 v.simple_queue['next_heap']=u.simple_queue['next_heap']
 assert s==other and bytes(v.mem_read(s,SAVE_BYTES))==bytes(u.mem_read(s,SAVE_BYTES))
 return v

def run_all():
 global checks
 checks=0
 # A real hidden roster reserves23 people and never changes nine normal armies.
 u=ready();before=bytes(u.mem_read(tp(1)+0x104,9*0x55b0));cash=r(u,CASH[0]);s=state(u)
 assert start(u) and r(u,run(u))==1 and r(u,CASH[0])==cash-MISSIONS[0]['cost']
 a=invoke(u,'ex_resolve',tp(1),0)
 assert a and r(u,a+0x1c)==23 and r(u,a+0x34)==HEROES
 assert sum(r(u,p+4)==2 for p in u.exp_heroes)==3 and sum(r(u,p+4)==2 for p in u.exp_generics)==20
 assert bytes(u.mem_read(tp(1)+0x104,9*0x55b0))==before
 assert not r(u,a+8) and not r(u,a+0x10);checks+=1

 # Every mission is attainable without a mandatory specialist or main-story flag.
 for mission,data in enumerate(MISSIONS):
  u=ready(generics=0);discover(u);story=bytes(u.mem_read(G,31*4));cash=r(u,CASH[0])
  assert start(u,mission,roll=2 if mission==2 else 30)
  assert r(u,run(u)+16)-r(u,run(u)+12)==data['days']
  if mission==6:u.data['answers']=[0]
  advance(u,data['days']);assert pump_ex(u) and not r(u,run(u))
  assert r(u,CASH[0])>cash-data['cost'] and bytes(u.mem_read(G,31*4))==story
  if mission==2:assert r(u,state(u)+16)&2
  if mission==5:assert r(u,state(u)+16)&1
  checks+=1

 # All four separate slots work simultaneously; the fifth attempt is inert.
 u=ready(heroes=12,generics=0);normal=bytes(u.mem_read(WORLD+0x84,36))
 for index in range(4):assert start(u,chief=HEROES+index*3*0x500)
 before=r(u,CASH[0]);assert not start(u) and r(u,CASH[0])==before
 assert bytes(u.mem_read(WORLD+0x84,36))==normal and all(r(u,run(u,i))==1 for i in range(4))
 advance(u,30)
 for _ in range(4):assert pump_ex(u)
 assert all(not r(u,run(u,i)) for i in range(4)) and all(r(u,p+0x10)==0 for p in u.exp_heroes)
 checks+=1

 # No money, no captain, failed confirmation and invalid missions are inert.
 for mode in ('no_money','no_hero','invalid_mission','cancel'):
  u=ready(heroes=0 if mode=='no_hero' else 5);state(u)
  if mode=='no_money':w(u,CASH[0],0)
  before=bytes(u.mem_read(tp(1),0x51000));cash=r(u,CASH[0]);roster=bytes(u.mem_read(PEOPLE,0x20000))
  if mode=='cancel':
   u.data['answers']=[3,0,0,0,1,3];invoke(u,'we_router',PARENT)
  else:assert not start(u,mission=7 if mode=='invalid_mission' else 0)
  assert r(u,CASH[0])==cash and bytes(u.mem_read(tp(1),0x51000))==before and bytes(u.mem_read(PEOPLE,0x20000))==roster,mode
  assert all(not r(u,run(u,i)) for i in range(4)),mode;checks+=1

 # Real deferred claims: normal, great and delayed outcomes; XP and cash once.
 for roll,outcome in ((30,1),(2,2),(99,3)):
  u=ready();cash=r(u,CASH[0]);assert start(u,roll=roll)
  rptr=run(u);assert r(u,rptr+28)==outcome
  due=r(u,rptr+16);advance(u,29);assert r(u,rptr)==1 and not pump_ex(u)
  advance(u,1)
  if outcome==3:
   assert r(u,rptr)==2 and r(u,rptr+16)==due+7
   assert pump_ex(u) and r(u,CASH[0])==cash-MISSIONS[0]['cost']
   assert not pump_ex(u);advance(u,6);assert r(u,rptr)==2;advance(u,1)
  assert r(u,rptr)==3
  bonus=r(u,rptr+24);gold=MISSIONS[0]['gold']//2 if outcome==3 else MISSIONS[0]['gold']*(100+bonus+(25 if outcome==2 else 0))//100
  v=clone_runtime(u);assert pump_ex(v) and r(v,run(v))==0
  assert r(v,CASH[0])==cash-MISSIONS[0]['cost']+gold
  paid=r(v,CASH[0]);assert not pump_ex(v) and r(v,CASH[0])==paid
  assert r(v,tp(1)+0x50a5c)==25 and all(r(v,p+4)==0 and r(v,p+0x10)==0 for p in v.exp_heroes)
  checks+=1

 # Return delays are measured from the original due date, including story gaps.
 for roll,days,expected_status,expected_due in ((99,36,2,137),(99,100,3,137),(30,100,3,130)):
  u=ready();cash=r(u,CASH[0]);assert start(u,roll=roll)
  assert r(u,run(u)+16)==130
  w(u,G+19*4,1);advance(u,days)
  assert r(u,run(u))==1 and r(u,CASH[0])==cash-MISSIONS[0]['cost'] and not u.exp_awards
  w(u,G+19*4,0);invoke(u,'we_tick',PARENT)
  assert r(u,run(u))==expected_status and r(u,run(u)+16)==expected_due,(roll,days,values(u,run(u),12))
  if expected_status==2:
   assert pump_ex(u) and not pump_ex(u)
   assert r(u,CASH[0])==cash-MISSIONS[0]['cost'] and not u.exp_awards
   advance(u,1);assert r(u,run(u))==3 and r(u,run(u)+16)==137
  assert pump_ex(u) and not r(u,run(u))
  assert r(u,CASH[0])>cash-MISSIONS[0]['cost'] and u.exp_awards
  checks+=1

 # 99-level shares move to the other22 members through actual stock XP.
 u=ready(level=80);w(u,HEROES+0x48,99);w(u,HEROES+0x70,200)
 assert start(u,roll=30);advance(u,30);assert pump_ex(u)
 assert len(u.exp_awards)==22 and sum(xp for p,xp in u.exp_awards)==23*MISSIONS[0]['xp']
 assert max(xp for p,xp in u.exp_awards)-min(xp for p,xp in u.exp_awards)<=1
 assert r(u,HEROES+0x48)==99 and r(u,THREAD+0x14)==0xabcde123;checks+=1

 # Main-story reassignment wins, including the last remaining member.
 for heroes,generics,remaining in ((5,25,22),(1,0,0)):
  u=ready(heroes=heroes,generics=generics);assert start(u)
  normal=tp(1)+0x104
  for offset,value in ((0,1),(4,tp(1)),(0x14,1),(0x1c,1),(0x34,HEROES),(0x60,HEROES)):
   w(u,normal+offset,value)
  w(u,HEROES+0x10,1);w(u,HEROES+4,0);w(u,G+4*4,10)
  story=bytes(u.mem_read(G,31*4));advance(u,30)
  assert pump_ex(u) and not r(u,run(u))
  assert r(u,normal+0x60)==HEROES and r(u,HEROES+0x10)==1 and r(u,HEROES+4)==0
  assert not any(p==HEROES for p,xp in u.exp_awards)
  assert len(u.exp_awards)==remaining and sum(xp for p,xp in u.exp_awards)==remaining*MISSIONS[0]['xp']
  assert bytes(u.mem_read(G,31*4))==story and not invoke(u,'ex_resolve',tp(1),0)
  checks+=1

 # Level and aptitude improve chances/bonus, subject to caps; passive artifacts.
 scores=[]
 for level,skill,artifacts in ((1,0,0),(50,80,0),(99,200,0),(20,40,1),(20,40,0),(20,40,2)):
  u=ready(level=level,skill=skill);discover(u);w(u,state(u)+16,artifacts)
  assert start(u,mission=4);scores.append((r(u,run(u)+20),r(u,run(u)+24)))
  assert scores[-1][0]<=95 and scores[-1][1]<=50;checks+=1
 assert scores[0][0]<scores[1][0]<=scores[2][0] and scores[0][1]<scores[1][1]<=scores[2][1]
 assert scores[3][0]==min(95,scores[4][0]+5) and scores[5][1]==min(50,scores[4][1]+10)

 # Annual benefits require an actual visit and reset on the360-day game year.
 u=ready();s=state(u);cash=tuple(r(u,p) for p in CASH)
 assert not invoke(u,'we_test_ex_bless',0,0)
 v=visit_cleared_ruin(u);assert r(u,v)==1
 assert invoke(u,'we_test_ex_bless',0,0) and r(u,v+4)==1
 assert tuple(r(u,p) for p in CASH)==tuple(a+b for a,b in zip(cash,(20000,20,10)))
 assert not invoke(u,'we_test_ex_bless',0,0)
 visit_cleared_ruin(u,1);assert invoke(u,'we_test_ex_bless',1,0)
 w(u,HOURS,359*24);visit_cleared_ruin(u);assert not invoke(u,'we_test_ex_bless',0,0)
 w(u,HOURS,360*24);assert not invoke(u,'we_test_ex_bless',0,0)
 visit_cleared_ruin(u);assert r(u,v)==2 and invoke(u,'we_test_ex_bless',0,0);checks+=1

 u=ready();v=visit_cleared_ruin(u);w(u,v+20,1);cash=r(u,CASH[0])
 assert invoke(u,'we_test_ex_bless',0,0) and r(u,CASH[0])==cash+30000
 u=ready();v=visit_cleared_ruin(u)
 for i in range(81):
  p=r(u,army(1)+0x60+i*4)
  if p:person(u,p,r(u,p),r(u,p+8),r(u,p+0x38));w(u,p+0x54,1)
 assert invoke(u,'we_test_ex_bless',0,2)
 assert all(r(u,p+0x54)==r(u,p+0x58) for i in range(81) if (p:=r(u,army(1)+0x60+i*4)))
 assert not invoke(u,'we_test_ex_bless',0,2);checks+=2

 u=ready();v=visit_cleared_ruin(u)
 for i in range(81):
  p=r(u,army(1)+0x60+i*4)
  if p:person(u,p,r(u,p),r(u,p+8),r(u,p+0x38))
 w(u,hero(1)+0x48,99)
 assert invoke(u,'we_test_ex_bless',0,1) and len(u.exp_awards)==6
 assert sum(xp for p,xp in u.exp_awards)==7*120 and all(xp==140 for p,xp in u.exp_awards)
 assert r(u,v+4)==1 and not invoke(u,'we_test_ex_bless',0,1);checks+=1
 u=ready();v=visit_cleared_ruin(u);w(u,CASH[0],2000000000);before=tuple(r(u,p) for p in CASH)
 assert not invoke(u,'we_test_ex_bless',0,0) and r(u,v+4)==0 and tuple(r(u,p) for p in CASH)==before
 w(u,CASH[0],1000);assert invoke(u,'we_test_ex_bless',0,0);checks+=1
 for mode in ('wrong_city','wrong_frame','foreign_army'):
  u=ready();w(u,CTX,PARENT);ident=RUINS[0][1];station(u,army(1),ident);w(u,PARENT+0x50,tp(ident))
  if mode=='wrong_city':w(u,PARENT+0x50,tp(ident+1))
  elif mode=='wrong_frame':w(u,PARENT,0x4632d8)
  else:w(u,army(1),2)
  invoke(u,'we_ruin_visit',CTX,0);assert not r(u,visit(u));checks+=1

 # Deep-story choice is persisted before a capacity retry; rewards never repeat.
 for choice,story,blueprint in ((0,1,0),(1,2,1)):
  u=ready();discover(u);assert start(u,mission=6,roll=30);advance(u,30)
  u.data['answers']=[choice];w(u,CASH[0],2000000000)
  assert pump_ex(u) and r(u,visit(u)+20)==story and r(u,state(u)+12)==blueprint
  assert r(u,run(u)+36)&4 and r(u,run(u))==3
  v=clone_runtime(u);w(v,CASH[0],1000);advance(v,1);before=len(v.data['selections'])
  assert pump_ex(v) and r(v,run(v))==0 and len(v.data['selections'])==before
  assert r(v,visit(v)+20)==story and r(v,state(v)+12)==blueprint;checks+=1

 # Three successful explorations guarantee a previously unknown blueprint.
 u=ready();discover(u)
 for i in range(3):
  assert start(u,mission=4,roll=30);advance(u,7);assert pump_ex(u)
  assert r(u,state(u)+12)&7==(1 if i==2 else 0)
  assert bool(r(u,state(u)+12)&32)==(i==2)
 assert r(u,visit(u)+24)==0;checks+=1

 u=ready();discover(u);assert start(u,mission=6,roll=30);advance(u,30);u.data['answers']=[-1]
 cash=r(u,CASH[0]);assert pump_ex(u) and r(u,run(u))==3 and not r(u,visit(u)+20)
 assert r(u,CASH[0])==cash;advance(u,1);u.data['answers']=[1]
 assert pump_ex(u) and not r(u,run(u)) and r(u,visit(u)+20)==2;checks+=1

 # Pending currency and return-memory failures use durable paid bits.
 u=ready();assert start(u);advance(u,30);w(u,CASH[0],2000000000)
 assert pump_ex(u) and r(u,run(u))==3 and not r(u,run(u)+36)&1
 assert not pump_ex(u);w(u,CASH[0],1000);advance(u,1);u.exp_fail_alloc=True
 assert pump_ex(u) and r(u,run(u)+36)&3==3 and r(u,run(u))==3
 paid=r(u,CASH[0]);u.exp_fail_alloc=False;v=clone_runtime(u);advance(v,1)
 assert pump_ex(v) and r(v,run(v))==0 and r(v,CASH[0])==paid;checks+=1

 # Production has one cost, required completed facilities and delayed delivery.
 for ident,recipe in enumerate(RECIPES):
  u=ready();w(u,state(u)+12,7);before=tuple(r(u,p) for p in CASH)
  assert invoke(u,'we_test_ex_recipe',ident)
  assert tuple(r(u,p) for p in CASH)==tuple(a-b for a,b in zip(before,(recipe['gold'],recipe['iron'],recipe['oil'])))
  paid=tuple(r(u,p) for p in CASH);assert not invoke(u,'we_test_ex_recipe',ident)
  advance(u,recipe['days']-1);assert not pump_ex(u)
  advance(u,1);u.data['full'].add('give_machine');assert pump_ex(u) and r(u,state(u)+328)==ident+1
  assert not pump_ex(u);u.data['full'].clear();advance(u,1)
  assert pump_ex(u) and not r(u,state(u)+328)
  assert ('give_machine',(tp(1),recipe['machine'])) in u.data['grants']
  assert tuple(r(u,p) for p in CASH)==paid and not pump_ex(u);checks+=1
 u=ready();assert not invoke(u,'we_test_ex_recipe',0);w(u,state(u)+12,1)
 for ident in (17,18):w(u,tp(1)+0x53000+(ident-1)*0x300+8,2)
 before=tuple(r(u,p) for p in CASH);assert not invoke(u,'we_test_ex_recipe',0)
 assert tuple(r(u,p) for p in CASH)==before;checks+=1
 for ident in (0,1,2):
  u=ready();w(u,state(u)+12,7)
  for facility_id in ((7,8,9) if ident==0 else (10,11,12)):
   w(u,tp(1)+0x53000+(facility_id-1)*0x300+8,2)
  before=tuple(r(u,p) for p in CASH);assert not invoke(u,'we_test_ex_recipe',ident)
  assert tuple(r(u,p) for p in CASH)==before;checks+=1

 # Interrupted reserve keeps three heroes protected, charges no cost, then rolls back.
 u=ready();state(u);tail=r(u,WAITING+4);w(u,WAITING+4,0);cash=r(u,CASH[0])
 assert not start(u) and r(u,run(u))==4 and r(u,CASH[0])==cash
 assert all(r(u,p+0x10)==10 for p in u.exp_heroes[:3])
 w(u,WAITING+4,tail);assert pump_ex(u) and not r(u,run(u)) and r(u,CASH[0])==cash
 assert all(r(u,p+0x10)==0 for p in u.exp_heroes);checks+=1

 report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),version=manifest['version'],
  coverage=['Actual compiled mission/party/annual/recipe progression and deferred native dialogue',
  'Normal/great/setback+7days from original due date, long story/time gaps, level and skill caps, level99 redistribution, passive artifacts',
  'Pointer-free metadata plus reserved native roster snapshot reload; exact-once currency/XP/return retries',
  '360-day annual visit/use gating, independent ruins, preserved/recovered story choice, third-success blueprint guarantee',
  'All3 recipes 7/10/15days, resource/facility gates, capacity retry and single delivery'],
  scoped_mocks=['WinAPI properties/time and allocation arena','Existing fixture native UI renderer and atomic machine grant',
  'Runtime-snapshot reload; separate storage suite tests physical save footer'],not_checked=['Hardware visual playtest'])
 (ROOT/'test-expedition-native-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('PASS expedition progression:',checks,'native C mission/annual/production and deferred notification cases')

if __name__=="__main__":run_all()
