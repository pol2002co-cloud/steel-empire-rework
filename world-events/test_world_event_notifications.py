"""Native offer notifications and automatic settlement for single-goal events.

The separate simple-contract suite owns goal/resource/occupation coverage. Here
we check dialogue policy, safe frames, persistence and once-only dispatch.
"""
from test_world_events_native import *
import datetime, hashlib

SHOWN=1<<30
READY=1<<31
BUSY=1<<31
SIMPLE=1<<28
SCHEMA=1<<30
CONFIG=G+82*4
checks=0

def check(ok, message):
 global checks
 assert ok,message
 checks+=1

def prepared(ident=0, origin=2):
 u=fixture(origin);offer(u,ident,origin=origin)
 w(u,G+38*4,r(u,G+38*4)|SCHEMA)
 w(u,CARD+28,SIMPLE)
 u.data['default_answer']=1
 return u

def idle(u,*answers):
 u.data['answers']=list(answers)
 return invoke(u,'we_present',PARENT)

# Existing offers are acknowledged once and survive a reload without nagging.
u=prepared();before=tuple(r(u,p) for p in CASH)
check(idle(u,1)==1 and slot(u)[5]&SHOWN and status(u)==1,'defer records offer acknowledgement')
check(len(u.data['selections'])==1 and tuple(r(u,p) for p in CASH)==before,'defer neither accepts nor spends')
check(not r(u,CONFIG)&BUSY,'native dialogue releases recursion lock')
seen=len(u.data['selections'])
check(idle(u)==0 and len(u.data['selections'])==seen,'acknowledged offer does not reopen')
saved=bytes(u.mem_read(BASE,54*4));v=prepared();v.mem_write(BASE,saved)
check(idle(v)==0 and not v.data['selections'],'acknowledgement survives serialized bank reload')

# Accepting a ready resource goal settles directly, with no claim/army UI.
u=prepared();before=tuple(r(u,p) for p in CASH)
check(idle(u,0,0)==1 and status(u)==0,'one goal acceptance completes ready supply contract')
check(r(u,CASH[0])==before[0]+24000 and r(u,CASH[1])==before[1]-40,'supply cost and reward paid once')
check(len(u.data['selections'])==2,'only introduction and accept/defer/refuse menus appear')
check(invoke(u,int(STATE['completed'],16),0)==1,'automatic settlement records completion')
money=tuple(r(u,p) for p in CASH)
check(idle(u)==0 and tuple(r(u,p) for p in CASH)==money,'subsequent frame cannot duplicate settlement')

# F8 reads acknowledge a card. Accepting without the resource waits quietly.
u=prepared();route(u,[1,0,1,4])
check(bool(slot(u)[5]&SHOWN) and idle(u)==0,'manual F8 defer acknowledges the same offer')
u=prepared();w(u,CASH[1],39);before=r(u,CASH[0])
check(idle(u,0,0)==1 and status(u)==2 and r(u,CASH[1])==39,'insufficient resource accepts waiting goal without spending')
seen=len(u.data['selections'])
check(idle(u)==0 and len(u.data['selections'])==seen,'waiting resource does not create repeated prompts')
w(u,CASH[1],40)
check(idle(u)==1 and status(u)==0 and r(u,CASH[0])==before+24000 and r(u,CASH[1])==0,'resource arrival triggers automatic settlement')
check(len(u.data['selections'])==seen,'automatic completion has no manual claim selection')

# A visit has no assigned formation, departure menu, deadline or extra stop.
u=prepared(6);before=r(u,CASH[0])
check(idle(u,0,0)==1 and status(u)==2,'visit accepts single displayed destination')
check(slot(u)[2]>0 and slot(u)[3:5]==[0,0] and slot(u)[6]==0,'visit keeps no army binding or deadline')
seen=len(u.data['selections'])
check(idle(u)==0,'accepted visit waits without action dialog')
travel(u)
check(status(u)==3,'explicit world arrival marks goal ready')
saved=bytes(u.mem_read(BASE,54*4));destination=slot(u)[2]
v=prepared(6);v.mem_write(BASE,saved);station(v,army(1),destination)
check(idle(v)==1 and status(v)==0,'arrived goal settles automatically after bank reload')
check(r(v,CASH[0])==before+60000 and not v.data['selections'],'reload settlement pays without claim menu')
check(idle(v)==0 and not v.data['battles'],'no repeated reward or obsolete arena launch')
check(idle(u)==1 and status(u)==0 and len(u.data['selections'])==seen,'normal arrival completion needs no additional selection')

# Story/modality/frame/world guards and nested native dialogue are inert.
for block in ['story','modal','wrong_frame','no_world','own_dialogue']:
 u=prepared();before=slot(u);money=tuple(r(u,p) for p in CASH)
 if block=='story':w(u,G+19*4,1)
 if block=='modal':w(u,0x4880e0,1)
 if block=='wrong_frame':w(u,PARENT,0x4632d8)
 if block=='no_world':w(u,0x48c3d8,0)
 if block=='own_dialogue':w(u,CONFIG,BUSY|0x60000200)
 check(idle(u)==(1 if block=='own_dialogue' else 0),block+' blocks dispatch')
 check(slot(u)==before and not u.data['selections'] and tuple(r(u,p) for p in CASH)==money,block+' preserves cards and resources')
u=prepared();w(u,BASE,0);u.data['answers']=[0]
check(invoke(u,'we_router',PARENT)==0 and r(u,BASE)==int(STATE['magic']),'first F8 initializes before returning to original journal')
check(not r(u,CONFIG)&BUSY,'fresh initialization releases dialogue lock')

# One native frame presents only one offer; ready settlements take priority.
u=prepared(6);w(u,CARD+32,2|(1<<16));w(u,CARD+36,2);w(u,CARD+60,SIMPLE)
check(idle(u,1)==1 and slot(u)[5]&SHOWN and not slot(u,1)[5]&SHOWN,'one offer per frame')
check(idle(u,1)==1 and slot(u,1)[5]&SHOWN,'next offer waits for following frame')
u=prepared(6);w(u,CARD+32,0|(3<<16));w(u,CARD+36,2);w(u,CARD+60,SIMPLE)
before=r(u,CASH[0])
check(idle(u)==1 and status(u,1)==0 and not slot(u)[5]&SHOWN,'ready settlement precedes unread offer')
check(r(u,CASH[0])==before+24000 and not u.data['selections'],'priority settlement has no choice UI')
check(idle(u,1)==1 and slot(u)[5]&SHOWN,'offer remains available after prioritized settlement')

# Every new contract is available for notification before the final event.
u=prepared(31);w(u,G+11*4,0)
check(idle(u,1)==1 and slot(u)[5]&SHOWN and len(u.data['selections'])==1,'new airport goal is not hidden by former ending gate')
u=fixture();u.data['default_answer']=1;w(u,int(STATE['next_offer_address'],16),0)
check(invoke(u,'we_present',PARENT)==1 and any(status(u,i)==1 for i in range(3)),'new automatic offer does not require F8')
check(len(u.data['selections'])==1,'new notice enters the single introduction menu')

# Resource-cap failure retries once per game day, without manual claim or spam.
u=prepared();w(u,CARD,0|(3<<16));w(u,CASH[0],2000000000)
iron=r(u,CASH[1])
check(idle(u)==1 and status(u)==3 and r(u,CASH[0])==2000000000,'capacity failure keeps pending reward')
check(slot(u)[5]&READY and slot(u)[6]==r(u,HOURS)//24+1,'failed automatic claim schedules next-day retry')
texts=len(u.data['texts'])
check(idle(u)==0 and len(u.data['texts'])==texts,'capacity warning does not repeat each frame')
saved=bytes(u.mem_read(BASE,54*4));v=prepared();v.mem_write(BASE,saved)
w(v,CASH[0],100);w(v,CASH[1],r(u,CASH[1]));w(v,HOURS,r(u,HOURS)+24)
check(idle(v)==1 and status(v)==0 and r(v,CASH[0])==24100,'freed capacity settles on next-day automatic retry after reload')
check(r(v,CASH[1])==iron-40 and not v.data['selections'],'retry cannot charge the already-paid cost twice or require a menu')

# Replay the actual save bank read-only; original storyline words stay intact.
source=Path('C:/Games/DGGL/Games/EoSteel_Win/Steel0.Sav')
real_bank_replayed=False
if source.exists():
 raw=source.read_bytes()
 if len(raw)>=0x34+400:
  values=struct.unpack_from('<100I',raw,0x34)
  if values[31]==int(STATE['magic']) and any((values[i]>>16)&255 for i in (57,65,73)):
   u=fixture();u.data['default_answer']=1;u.mem_write(G,raw[0x34:0x34+400]);w(u,HOURS,values[34]*24)
   original=bytes(u.mem_read(G,31*4));idle(u,1)
   check(bytes(u.mem_read(G,31*4))==original,'actual serialized bank replay preserves original story globals')
   check(source.read_bytes()==raw,'actual player save was never changed')
   real_bank_replayed=True

digest=hashlib.sha256(binary).hexdigest()
report=dict(status='passed',cases=checks,engine_sha256=digest,version=manifest['version'],real_bank_replayed=real_bank_replayed,
 tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 coverage=['Once-only offer acknowledgement, defer and serialized reload',
 'Single-objective resource waiting and visit arrival with automatic settlement, no claim/army/arena UI',
 'Priority and one notice per frame, story/modal/frame/world/reentrancy guards',
 'Pending capacity, next-game-day automatic retry and persisted partial cost protection'],
 scoped_mocks=['Existing native harness UI select/speech, formatting, routing and action boundaries'],
 not_checked=['Hardware visual playtest'])
(ROOT/'test-world-notifications-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS single-goal automatic event dialogue:',checks,'native C checks; notification policy, persistence, guards and automatic settlement')
