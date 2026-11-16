"""Compiled automatic tour against real city/XP helpers and movement boundaries."""
from test_world_events_native import *

ENABLED=1<<29;PERFORMED=1<<30;REST_MASK=65535<<13
CONFIG=G+82*4;THREAD=0x13c0000
TOUR=int(E['tour_actions']['perform'],16)
checks=0

def buildings(u,ident,entries=()):
 t=tp(ident);head=t+0x50b00;w(u,t+0x50a88,head);w(u,t+0x50a8c,len(entries))
 w(u,head,head+0x20 if entries else head);w(u,head+4,head+0x20+16*(len(entries)-1) if entries else head)
 for i,(kind,state) in enumerate(entries):
  node=head+0x20+i*16;p=head+0x100+i*0x100
  w(u,node,head+0x20+(i+1)*16 if i+1<len(entries) else head)
  w(u,node+4,head+0x20+(i-1)*16 if i else head);w(u,node+8,p)
  w(u,p+8,state);w(u,p+0xc,kind)

def tour_fixture(origin=2):
 u=fixture(origin);u.data['native_facilities']=True
 for ident in range(1,74):buildings(u,ident)
 buildings(u,2,[(2,1)]);buildings(u,3,[(3,1)])
 a=army(4)
 for i in range(1,4):station(u,army(i),1)
 p=r(u,a+0x60+5*4)
 for off,value in ((0x48,10),(0x4c,0),(0x50,100),(0x58,100)):
  w(u,p+off,value)
 w(u,THREAD+0x14,0xcafed00d);w(u,WORLD+0x80,0x13a5000)
 u.tour=dict(perform=0,departures=0,targets=[],facilities=[])
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if pc==0x45290b:
   u.reg_write(UC_X86_REG_EAX,THREAD);ret(u)
  elif pc==TOUR:u.tour['perform']+=1
  elif pc==0x4382e0:u.tour['departures']+=1
  elif pc==0x4200a0:u.tour['targets'].append(r(u,u.reg_read(UC_X86_REG_ECX)+0x50))
  elif pc==0x437880:u.tour['facilities'].append((u.reg_read(UC_X86_REG_ECX),r(u,sp+4),r(u,sp+8)))
 u.hook_add(UC_HOOK_CODE,boundary)
 return u

def config(u,enabled=True,rest=0,performed=False,battle=0,home=1,legion=4):
 value=(ENABLED if enabled else 0)|(PERFORMED if performed else 0)|(rest<<13)|(home<<2)|(legion<<9)|battle
 w(u,CONFIG,value);return value

def rest(u):return (r(u,CONFIG)>>13)&65535

def tick(u):
 story=bytes(u.mem_read(G,31*4));rng=r(u,THREAD+0x14)
 result=invoke(u,'we_test_tour',PARENT)
 assert bytes(u.mem_read(G,31*4))==story
 assert r(u,THREAD+0x14)==rng
 return result

def reload_tour(u):
 v=tour_fixture();v.mem_write(G+31*4,bytes(u.mem_read(G+31*4,57*4)))
 for address in (*CASH,HOURS):w(v,address,r(u,address))
 v.mem_write(army(4),bytes(u.mem_read(army(4),0x55b0)))
 p=r(u,army(4)+0x60+5*4);v.mem_write(p,bytes(u.mem_read(p,0xa8)))
 return v

# Ordinary towns have no player building list; performances need no City Hall.
for ident,kind,state,pays in ((2,0,0,True),(2,2,1,True),(2,3,1,True),
                              (2,2,3,True),(2,2,2,True),(2,1,1,True)):
 u=tour_fixture();buildings(u,ident,[(kind,state)] if kind else [])
 config(u);money=r(u,CASH[0]);result=tick(u)
 assert (result==1)==pays
 assert r(u,CASH[0])==money+(2800 if pays else 0)
 assert u.tour['perform']==int(pays)
 assert not u.tour['facilities'],'Tour must not inspect player-only city buildings'
 checks+=1;gc.collect()

# One performance, persistent three-day rest, and no same-city repeat on reload.
u=tour_fixture();config(u);money=r(u,CASH[0]);p=r(u,army(4)+0x60+5*4)
assert tick(u)==1 and r(u,CASH[0])==money+2800
assert rest(u)==3 and r(u,CONFIG)&PERFORMED and r(u,p+0x4c)>0
assert tick(u)==0 and r(u,CASH[0])==money+2800
v=reload_tour(u);assert tick(v)==0 and r(v,CASH[0])==money+2800 and rest(v)==3
w(v,HOURS,101*24);assert tick(v)==0 and rest(v)==2
assert r(v,CASH[0])==money+2800;checks+=1

# A long elapsed interval expires the16-bit rest without repaying the old city.
w(v,HOURS,(100+65537)*24);selection=r(v,WORLD+0x80)
assert tick(v)==2 and rest(v)==0
assert r(v,CASH[0])==money+2800 and not r(v,CONFIG)&PERFORMED
assert r(v,army(4)+8)==0 and v.tour['departures']==1
actor=r(v,army(4)+0x10)
assert actor and r(v,actor+0x50)==ap(3) and v.tour['targets']==[ap(3)]
assert r(v,WORLD+0x80)==selection and r(v,army(4)+0x55ac)==20
assert tick(v)==0 and r(v,CASH[0])==money+2800
station(v,army(4),3);w(v,PARENT+0x50,tp(3))
assert tick(v)==1 and r(v,CASH[0])==money+5600 and rest(v)==3
assert v.tour['perform']==1;checks+=1

# Single-goal contracts never reserve an army or pause its civilian tour.
for task_status,home,legion,paused in ((2,1,4,False),(3,1,4,False),(1,1,4,False),
                                      (2,2,4,False),(2,1,3,False)):
 u=tour_fixture();config(u)
 for offset,value in ((0,0|(task_status<<16)),(12,home),(16,legion)):w(u,CARD+offset,value)
 money=r(u,CASH[0]);assert tick(u)==(0 if paused else 1)
 assert r(u,CASH[0])==money+(0 if paused else 2800)
 assert u.tour['perform']==int(not paused);checks+=1;gc.collect()

# Closed tours, native story scenes, combat, invalid formations and dead dancers.
for mode in ('disabled','story','battle','no_world','moving','no_dancer','dead_dancer',
             'dead_commander','captured_commander','noncivil','foreign','empty','bad_home','bad_legion'):
 u=tour_fixture();a=army(4);p=r(u,a+0x60+5*4);config(u)
 if mode=='disabled':config(u,enabled=False)
 elif mode=='story':w(u,G+19*4,1)
 elif mode=='battle':w(u,CONFIG,r(u,CONFIG)|1)
 elif mode=='no_world':w(u,0x48c3d8,0)
 elif mode=='moving':
  actor=0x1384000;w(u,a+8,0);w(u,a+0x10,actor);w(u,actor+0x808,a);w(u,WORLD+0xac,actor);w(u,tp(2)+0x50654+3*4,0)
 elif mode=='no_dancer':w(u,p+0x38,12)
 elif mode=='dead_dancer':w(u,p+0x54,0)
 elif mode=='dead_commander':w(u,hero(4)+0x54,0)
 elif mode=='captured_commander':w(u,hero(4)+4,1)
 elif mode=='noncivil':w(u,a+0x18,1)
 elif mode=='foreign':w(u,a,2)
 elif mode=='empty':w(u,a+0x1c,0)
 elif mode=='bad_home':config(u,home=74)
 elif mode=='bad_legion':config(u,legion=9)
 money=r(u,CASH[0]);assert tick(u)==0,mode
 assert r(u,CASH[0])==money and not u.tour['perform'] and not u.tour['departures'],mode
 checks+=1;gc.collect()

# Unsafe/locked/minor cities yield neither XP nor cash even with the civilian present.
for mode in ('actor_hostile','town_hostile','pre_end_country6','mercenary_hq'):
 u=tour_fixture();config(u)
 if mode=='actor_hostile':w(u,ap(2)+0x14,1)
 elif mode=='town_hostile':w(u,tp(2)+0x10,1)
 elif mode=='pre_end_country6':w(u,G+11*4,0);w(u,tp(2)+8,6)
 elif mode=='mercenary_hq':station(u,army(4),63);buildings(u,63,[(2,1)])
 money=r(u,CASH[0]);assert tick(u)!=1,mode
 assert r(u,CASH[0])==money and not u.tour['perform'],mode
 checks+=1;gc.collect()

# Near-cap rejection is atomic, and eight level99 dancers can reach the exact cap.
u=tour_fixture();config(u);w(u,CASH[0],2000000000)
assert tick(u)==0 and r(u,CASH[0])==2000000000 and not u.tour['perform'];checks+=1
u=tour_fixture();config(u);a=army(4);p=r(u,a+0x60+5*4);w(u,p+0x48,99)
for i in range(7):
 p=0x1260000+i*0x100
 for off,value in ((4,0),(8,1),(0x38,13),(0x48,99),(0x50,100),(0x54,100),(0x58,100)):w(u,p+off,value)
 w(u,a+0x60+(6+i)*4,p)
w(u,a+0x1c,14);w(u,CASH[0],2000000000-164800)
assert tick(u)==1 and r(u,CASH[0])==2000000000;checks+=1

# Explicit UI confirmation, stop/re-enable preserves both rest and paid-city phase.
u=tour_fixture();money=r(u,CASH[0]);assert route(u,[2,0,1])==1
assert not r(u,CONFIG)&ENABLED and r(u,CASH[0])==money and not u.tour['perform'];checks+=1
assert route(u,[2,0,0])==1
assert r(u,CONFIG)&ENABLED and r(u,CONFIG)&PERFORMED and rest(u)==3
assert r(u,CASH[0])==money+2800
paid=r(u,CONFIG);assert route(u,[2,1])==1
assert r(u,CONFIG)==paid&~ENABLED
assert route(u,[2,0,0])==1 and r(u,CONFIG)==paid
assert r(u,CASH[0])==money+2800 and u.tour['perform']==1;checks+=1
u=tour_fixture();money=r(u,CASH[0])
for ident in range(1,63):
 if ident!=2:w(u,tp(ident)+0x10,1)
route(u,[2,0])
assert not r(u,CONFIG)&ENABLED and r(u,CASH[0])==money;checks+=1

# Unconfigured is a readable status, never a nonexistent legion0.
u=tour_fixture();w(u,CONFIG,0);route(u,[2,2])
assert any('군단 미지정' in text for _,text in u.data['texts'])
assert not any('제0군단' in text for _,text in u.data['texts']);checks+=1

# Reproduce real ordinary-town metadata with no player construction lists.
source=Path('C:/Games/DGGL/Games/EoSteel_Win/Steel0.Sav')
definitions=ROOT/'extracted/Data.pak/town.dat'
if source.exists() and definitions.exists():
 import hashlib
 raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest();towns=definitions.read_bytes();records=[]
 for ident in (1,2):
  title=towns[4+(ident-1)*516:4+(ident-1)*516+32].split(b'\0')[0]
  matches=[p for p in range(0,len(raw)-232,4) if struct.unpack_from('<I',raw,p)[0]==ident and raw[p+52:p+52+len(title)+1]==title+b'\0']
  assert len(matches)==1;records.append(struct.unpack_from('<4I',raw,matches[0]))
 if all(not record[3]&1 for record in records):
  u=tour_fixture(origin=1)
  for ident in range(1,74):buildings(u,ident);w(u,tp(ident)+0x10,1)
  for ident,country,weather,flags in records:
   for offset,value in ((4,ident),(8,country),(12,weather),(16,flags)):w(u,tp(ident)+offset,value)
  station(u,army(4),1);w(u,PARENT+0x50,tp(1));w(u,CONFIG,0)
  money=r(u,CASH[0]);route(u,[2,0,0])
  assert r(u,CONFIG)&ENABLED and rest(u)==3 and r(u,CASH[0])==money+2800
  assert not u.tour['facilities']
  w(u,HOURS,r(u,HOURS)+72);assert tick(u)==2
  assert u.tour['targets']==[ap(2)]
  assert hashlib.sha256(source.read_bytes()).hexdigest()==digest;checks+=1

# Battle result clears just low2 bits, leaving tour identity/rest/phase untouched.
u=tour_fixture();high=config(u,rest=3,performed=True);w(u,CONFIG,high|1)
w(u,CARD,12|(2<<16)|(129<<24));w(u,CARD+28,0);w(u,G+81*4,3)
invoke(u,'we_test_progress')
assert r(u,CONFIG)==high and r(u,G+81*4)==0 and (r(u,CARD)>>24)&2;checks+=1

# Accepting a simple contract preserves the enabled tour and opens no arena.
u=tour_fixture();high=config(u,rest=3,performed=True);offer(u,12)
result=invoke(u,'we_test_accept',PARENT,0,0)
assert result==1 and r(u,CONFIG)==high and not u.data['battles'];checks+=1

# Enabling/disabling the UI while another battle is reserved retains its slot.
u=tour_fixture();w(u,CONFIG,1);route(u,[2,0,0])
assert r(u,CONFIG)&ENABLED and r(u,CONFIG)&3==1 and not u.tour['perform']
packed=r(u,CONFIG);route(u,[2,1]);assert r(u,CONFIG)==packed&~ENABLED;checks+=1
print('PASS compiled tour:',checks,'cases; real major-city/XP helpers, actual move boundaries, cooldown/reload/phase, hostile/protected/story guards, cash cap, explicit UI, shared battle-slot packing')
if __name__=='__main__':
 import hashlib,datetime
 digest=hashlib.sha256((ROOT/'package/SteelEmpire.exe').read_bytes()).hexdigest()
 assert digest==manifest['output_sha256']
 report=dict(status='passed',cases=checks,engine_sha256=digest,version=manifest['version'],
  mapped_sha256=E['mapped_sha256'],test='test_world_tour.py',
  tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  coverage=['Building-free friendly ordinary-city eligibility, class13 performance and XP/growth',
   'Once per arrival, three-day rest, stock script-bank reload and elapsed gap greater than65536 days',
   'Native world departure/target calls, selected actor preservation and actual destination arrival',
   'World contracts do not reserve touring armies; living civilian/dancer and story/country/hostility guards',
   'Actual first-slot ordinary-town headers with empty construction lists: start, perform and depart; unconfigured status',
   'Exact2b gold cap, explicit enable confirmation, stop/re-enable retain cooldown and phase',
   'Battle-result slot and tour configuration retain each other in packed global82'],
  scoped_mocks=['UI select/speech and formatting from common native harness',
   'World detach/target boundaries; arrival explicitly simulated',
   'CRT thread-local lookup only; stock XP, growth, RNG and facility search execute'],
  not_checked=['Hardware visual playtest','Full save-file roundtrip; exact script bank and army/person fixture state restored'])
 (ROOT/'test-world-tour-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
