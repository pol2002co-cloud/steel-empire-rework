"""Compiled single-objective contracts and old-card reward migration.

Required scenarios:
1. Existing D1/id18 and G1/id36 OFFER records become fresh stage0 simple cards.
2. Accepted/pending legacy cards retain old stage, selected choice and payment
   flags, while gaining the legacy marker; they terminate after that old stage.
3. Completed bits and every remaining cooldown survive migration unchanged;
   the schema bit in global38 does not count as an event completion.
4. Already-paid costs are never charged again. Pending item/machine/currency or
   partially granted recruits resume only their unpaid components after reload.
5. Any healthy player army can satisfy a visit. Stock/resource/build goals need
   no assigned army. A normal friendly conquest satisfies an occupation goal.
6. Goal completion auto-claims from the posted-message handler without another
   confirm menu, exactly once; repeated tick/message/load cannot duplicate it.
7. The original first-slot save contributes only a readonly script-bank fixture;
   its on-disk hash must remain unchanged before/after the test.
"""
from test_world_events_native import *
from world_event_simple_catalog import SIMPLE_EVENT_CATALOG as SIMPLE
import hashlib,datetime

SIMPLE_MARK=1<<28
LEGACY_MARK=1<<29
SCHEMA_MARK=1<<30
SCHEMA=G+38*4
checks=0


def migrate(u):
 """The existing predicate export calls sync, without accepting a contract."""
 return invoke(u,'we_test_prerequisite',0,2)


def legacy_card(u,ident,stage=0,choice=0,status_code=2,flags=1,progress=0):
 """A real old8DWORD record, deliberately without either new schema marker."""
 for i in range(8):w(u,CARD+i*4,0)
 w(u,CARD,ident|(stage<<8)|(status_code<<16)|(flags<<24))
 w(u,CARD+4,2)
 w(u,CARD+12,1);w(u,CARD+16,1)
 w(u,CARD+20,100);w(u,CARD+24,160)
 w(u,CARD+28,progress|(choice<<24))
 w(u,SCHEMA,r(u,SCHEMA)&~SCHEMA_MARK)


def fresh():
 u=fixture();w(u,int(STATE['next_offer_address'],16),0xffffffff)
 w(u,int(STATE['done_address'],16),0);w(u,SCHEMA,SCHEMA_MARK)
 w(u,G+11*4,0);u.data['default_answer']=-1
 return u


def simple_card(u,ident):
 for i in range(24):w(u,CARD+i*4,0)
 w(u,CARD,ident|(1<<16));w(u,CARD+4,2);w(u,CARD+28,SIMPLE_MARK)
 w(u,SCHEMA,r(u,SCHEMA)|SCHEMA_MARK)
 goal=SIMPLE[ident]['goal']
 if goal['type']=='occupy':
  target=goal['target_fixed'] or 5
  w(u,tp(target)+0x10,1);w(u,ap(target)+0x14,1)
 return SIMPLE[ident]


def no_armies(u,keep=()):
 for city in range(1,74):
  for i in range(15):w(u,tp(city)+0x50654+i*4,0)
 for i in range(100):w(u,WORLD+0xac+i*4,0)
 for index in keep:station(u,army(index),2)


def set_building(u,ident,state):
 p=tp(1)+0x53000+(ident-1)*0x300;w(u,p+8,state)


def fulfill(u,event,visitor=4):
 kind=event['goal']['type']
 if kind in ('visit','occupy'):
  target=slot(u)[2];assert target,(event['key'],'target')
  station(u,army(visitor if kind=='visit' else 3),target)
  if kind=='occupy':w(u,tp(target)+0x10,0);w(u,ap(target)+0x14,0)
 elif kind=='build':set_building(u,event['goal']['building_id'],1)
 invoke(u,'we_test_progress')


def money(u):return tuple(r(u,address) for address in CASH)


def expected_money(before,actions,paid=False):
 return tuple(value+(actions.get('reward_'+key,0))-(0 if paid else actions.get('cost_'+key,0))
              for value,key in zip(before,('gold','iron','oil')))


def run_simple(ident):
 global checks
 u=fresh();event=simple_card(u,ident);actions=event['stages'][0]['choices'][0]['actions']
 if event['goal']['type'] in ('supply','equipment','build'):no_armies(u)
 if event['goal']['type']=='item':no_armies(u,(4,))
 before=money(u);invoke(u,'we_test_accept',PARENT,0,0)
 if status(u)==2:fulfill(u,event)
 if status(u)==3:
  menus=len(u.data['selections']);assert invoke(u,'we_present',PARENT)==1
  assert len(u.data['selections'])==menus,(event['key'],'extra claim confirmation')
 assert status(u)==0,(event['key'],slot(u),u.data['texts'][-3:])
 assert invoke(u,int(STATE['completed'],16),ident)==1
 assert money(u)==expected_money(before,actions),(event['key'],money(u),expected_money(before,actions))
 assert not u.data['battles'],event['key']
 if actions.get('cost_machine_id'):
  assert [x[1] for x in u.data['consumed_machine']]==[actions['cost_machine_id']]
 if actions.get('reward_machine_id'):
  assert [(kind,args[1]) for kind,args in u.data['grants']]==[('give_machine',actions['reward_machine_id'])]
 complete=money(u),list(u.data['grants']),list(u.data['consumed_machine'])
 assert invoke(u,'we_test_claim',PARENT,0)==0
 invoke(u,'we_test_progress');invoke(u,'we_present',PARENT)
 assert complete==(money(u),u.data['grants'],u.data['consumed_machine'])
 checks+=1


def migrations():
 global checks
 # The old, actually reported OFFER records lose only their old staged contract.
 for ident in (18,36):
  u=fresh();legacy_card(u,ident,stage=1,choice=2,status_code=1,flags=255,progress=123)
  w(u,CARD+8,28);before=money(u)
  migrate(u);c=slot(u)
  assert c==[ident|(1<<16),2,0,0,0,0,0,SIMPLE_MARK],c
  assert money(u)==before and r(u,SCHEMA)&SCHEMA_MARK
  saved=bytes(u.mem_read(CARD,96));migrate(u);assert bytes(u.mem_read(CARD,96))==saved
  checks+=1;gc.collect()
 # Accepted/pending stages retain old selected branches and every payment flag.
 for state_code in (2,3):
  u=fresh();legacy_card(u,31,stage=1,choice=1,status_code=state_code,flags=25,progress=0x400123)
  before=slot(u);migrate(u);after=slot(u)
  assert after[:7]==before[:7] and after[7]==before[7]|LEGACY_MARK
  checks+=1;gc.collect()
 # Completion flags and all38 timers, including unrelated state, survive sync.
 u=fresh();legacy_card(u,18,status_code=1)
 w(u,int(STATE['done_address'],16),(1<<1)|(1<<10));w(u,SCHEMA,1<<3)
 for i in range(38):u.mem_write(int(STATE['cooldowns_address'],16)+i*2,struct.pack('<H',i+5))
 timers=bytes(u.mem_read(int(STATE['cooldowns_address'],16),76))
 preserved={index:r(u,G+index*4) for index in (0,5,11,19,30,81,82,83,84,85,86,87,94,99)}
 migrate(u)
 assert r(u,int(STATE['done_address'],16))==(1<<1)|(1<<10)
 assert r(u,SCHEMA)==(1<<3)|SCHEMA_MARK
 assert invoke(u,int(STATE['count_completed'],16))==3
 assert bytes(u.mem_read(int(STATE['cooldowns_address'],16),76))==timers
 assert preserved=={index:r(u,G+index*4) for index in preserved};checks+=1
 # A rewarded follow-up OFFER cannot become a fresh contract paying again.
 for ident,stage,progress in ((31,1,1<<22),(34,0,(1<<22)|1)):
  u=fresh();legacy_card(u,ident,stage=stage,status_code=1,flags=0,progress=progress)
  before=money(u);migrate(u)
  assert status(u)==0 and money(u)==before and not u.data['grants'],(ident,slot(u))
  assert invoke(u,int(STATE['completed'],16),ident)==1
  assert struct.unpack('<H',u.mem_read(int(STATE['cooldowns_address'],16)+ident*2,2))[0]==SIMPLE[ident]['repeat_days']
  migrate(u);invoke(u,'we_present',PARENT)
  assert status(u)==0 and money(u)==before and not u.data['grants']
  checks+=1;gc.collect()


def legacy_rewards():
 global checks
 # The selected oil branch remains26000, not the first/new branch24000.
 u=fresh();legacy_card(u,0,choice=1,flags=1)
 before=money(u);migrate(u);invoke(u,'we_test_progress')
 assert status(u)==3 and invoke(u,'we_test_claim',PARENT,0)==1
 assert money(u)==expected_money(before,EVENT_CATALOG[0]['stages'][0]['choices'][1]['actions'],paid=True)
 assert status(u)==0;checks+=1
 # A final old aircraft reward retains its partially paid ledger across reload.
 u=fresh();legacy_card(u,31,stage=2,status_code=3,flags=1|8)
 u.data['full'].add('give_machine');before=money(u)
 assert invoke(u,'we_test_claim',PARENT,0)==0 and status(u)==3
 expected=(before[0],before[1],before[2]+100)
 assert money(u)==expected and not u.data['grants']
 saved=bytes(u.mem_read(G+31*4,57*4));v=fresh();v.mem_write(G+31*4,saved)
 for address,value in zip(CASH,expected):w(v,address,value)
 assert invoke(v,'we_test_claim',PARENT,0)==1 and status(v)==0
 assert money(v)==expected and [(kind,args[1]) for kind,args in v.data['grants']]==[('give_machine',24)]
 assert invoke(v,'we_test_claim',PARENT,0)==0 and len(v.data['grants'])==1;checks+=1
 # A machine already surrendered by the old contract must not be removed twice.
 u=fresh();legacy_card(u,36,flags=1,progress=1<<23)
 u.data['machines'].clear();before=money(u);migrate(u);invoke(u,'we_test_progress')
 assert status(u)==3 and invoke(u,'we_test_claim',PARENT,0)==1
 old=EVENT_CATALOG[36]['stages'][0]['choices'][0]['actions']
 assert money(u)==expected_money(before,old,paid=True) and not u.data['consumed_machine']
 assert status(u)==0;checks+=1
 # Older accepted routes could have no target between stages. They must recover.
 u=fresh();legacy_card(u,31,stage=1,status_code=2,flags=1)
 migrate(u);invoke(u,'we_test_progress')
 assert slot(u)[2],('legacy accepted target was not repaired',slot(u))
 fulfill(u,SIMPLE[31]);assert status(u)==3
 assert invoke(u,'we_test_claim',PARENT,0)==1 and status(u)==0;checks+=1
 # This old stage originally led to more battles; it now ends this contract.
 u=fresh();legacy_card(u,31,stage=1,choice=0,status_code=3,flags=1|2)
 before=money(u);assert invoke(u,'we_test_claim',PARENT,0)==1
 assert status(u)==0 and not u.data['battles']
 assert money(u)==expected_money(before,EVENT_CATALOG[31]['stages'][1]['choices'][0]['actions'],paid=True)
 assert invoke(u,int(STATE['completed'],16),31)==1;checks+=1
 # Choice1 was an optional skip. Marker bits must not reinterpret it as choice0.
 u=fresh();legacy_card(u,31,stage=1,choice=1,status_code=3,flags=1)
 before=money(u);assert invoke(u,'we_test_claim',PARENT,0)==1
 assert status(u)==0 and money(u)==before and not u.data['grants'];checks+=1
 # Gold already paid while the item bag was full cannot be awarded again.
 u=fresh();legacy_card(u,19,choice=2,status_code=3,flags=1|8)
 u.data['full'].add('give_item');before=money(u)
 for _ in range(3):assert invoke(u,'we_test_claim',PARENT,0)==0
 assert money(u)==before and status(u)==3 and not u.data['grants']
 saved=bytes(u.mem_read(G+31*4,57*4));v=fresh();v.mem_write(G+31*4,saved)
 for address,value in zip(CASH,before):w(v,address,value)
 assert invoke(v,'we_test_claim',PARENT,0)==1 and status(v)==0
 assert money(v)==before and len(v.data['grants'])==1
 assert invoke(v,'we_test_claim',PARENT,0)==0 and len(v.data['grants'])==1;checks+=1
 # One recruit already exists. Only the two remaining paid-for recruits resume.
 u=fresh();legacy_card(u,13,status_code=3,flags=1,progress=(1<<20)|(1<<22))
 before=money(u);assert invoke(u,'we_test_claim',PARENT,0)==1
 assert money(u)==before and len(u.data['grants'])==2
 assert all(kind=='hire' and args[1]==1 for kind,args in u.data['grants'])
 assert status(u)==0;checks+=1


def natural_goals():
 global checks
 # Visiting is physical presence, independent of the stored army identity.
 for visitor in (1,2,3,4):
  u=fresh();event=simple_card(u,6);invoke(u,'we_test_accept',PARENT,0,0)
  target=slot(u)[2];assert target and status(u)==2
  w(u,CARD+12,73);w(u,CARD+16,9)
  station(u,army(visitor),target);invoke(u,'we_test_progress')
  assert status(u)==3 and invoke(u,'we_present',PARENT)==1 and status(u)==0
  checks+=1;gc.collect()
 # Construction in Porum needs neither personnel nor a visiting army.
 for ident in (3,4,5,34):
  u=fresh();event=simple_card(u,ident);no_armies(u);building=event['goal']['building_id']
  set_building(u,building,2);before=money(u)
  assert invoke(u,'we_test_accept',PARENT,0,0)==1 and status(u)==2 and money(u)==before
  set_building(u,building,1);invoke(u,'we_test_progress')
  assert status(u)==3 and invoke(u,'we_present',PARENT)==1 and status(u)==0
  checks+=1;gc.collect()
 # Ordinary capture must exclude civilian presence and physically present enemies.
 u=fresh();event=simple_card(u,24);invoke(u,'we_test_accept',PARENT,0,0);target=slot(u)[2]
 w(u,tp(target)+0x10,0);w(u,ap(target)+0x14,0);station(u,army(4),target)
 invoke(u,'we_test_progress');assert status(u)==2
 station(u,army(3),target)
 enemy=0x1270000
 for off,value in ((0,12),(8,tp(target)),(0x14,1),(0x18,0),(0x1c,1)):w(u,enemy+off,value)
 w(u,tp(target)+0x50654+10*4,enemy);invoke(u,'we_test_progress');assert status(u)==2
 w(u,tp(target)+0x50654+10*4,0);invoke(u,'we_test_progress')
 assert status(u)==3 and not u.data['battles'];assert invoke(u,'we_present',PARENT)==1 and status(u)==0
 checks+=1


def user_reference():
 global checks
 source=Path('C:/Games/DGGL/Games/EoSteel_Win/Steel0.Sav')
 if not source.exists():return
 raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
 if len(raw)<0x34+400:return
 values=struct.unpack_from('<100I',raw,0x34)
 if values[31]!=int(STATE['magic']):return
 u=fresh();u.mem_write(G,raw[0x34:0x34+400]);w(u,HOURS,values[34]*24)
 previous=[slot(u,i) for i in range(3)];old_money=money(u);done=(values[37],values[38]&~SCHEMA_MARK)
 migrate(u)
 for i,c in enumerate(previous):
  if ((c[0]>>16)&255)==1 and (c[0]&255)<38:
   assert slot(u,i)==[c[0]&255|(1<<16),c[1],0,0,0,0,0,SIMPLE_MARK]
 assert (r(u,G+37*4),r(u,SCHEMA)&~SCHEMA_MARK)==done
 assert money(u)==old_money and hashlib.sha256(source.read_bytes()).hexdigest()==digest
 checks+=1


def attach_queue(u):
 """Real compiled deferred handler; only Windows APIs/heap are boundaries."""
 hwnd=0x123456;controller=0x13a8000
 names=('GetPropA','SetPropA','RemovePropA','PostMessageA','GetTickCount')
 api={key:0x5fc100+i*32 for i,key in enumerate(names)}
 w(u,0x476fe8,hwnd);w(u,0x48cc1c,controller);w(u,controller+4,3);w(u,controller+0x10,PARENT)
 w(u,0x460060,0x5fc000);w(u,0x460100,0x5fc020)
 u.simple_queue=dict(properties={},posts=[],ticks=10000,next_heap=0x13d2000)
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP);q=u.simple_queue;value=0;argc=0
  if pc==0x5fc000:value=0x600000;argc=1
  elif pc==0x5fc020:value=api[name(u,r(u,sp+8))];argc=2
  elif pc==api['GetPropA']:value=q['properties'].get((r(u,sp+4),name(u,r(u,sp+8))),0);argc=2
  elif pc==api['SetPropA']:q['properties'][(r(u,sp+4),name(u,r(u,sp+8)))]=r(u,sp+12);value=1;argc=3
  elif pc==api['RemovePropA']:value=q['properties'].pop((r(u,sp+4),name(u,r(u,sp+8))),0);argc=2
  elif pc==api['PostMessageA']:q['posts'].append(tuple(r(u,sp+4+i*4) for i in range(4)));value=1;argc=4
  elif pc==api['GetTickCount']:value=q['ticks']
  elif pc==0x450452:value=q['next_heap'];q['next_heap']+=256
  elif pc==0x4500e6:pass
  else:return
  u.reg_write(UC_X86_REG_EAX,value);ret(u,argc*4 if pc not in (0x450452,0x4500e6) else 0)
 u.hook_add(UC_HOOK_CODE,boundary)


def pump(u):
 previous=len(u.simple_queue['posts']);menus=len(u.data['selections'])
 invoke(u,'we_idle',PARENT);u.simple_queue['ticks']+=1000;invoke(u,'we_idle',PARENT)
 assert len(u.data['selections'])==menus,'UI ran from frame update'
 if len(u.simple_queue['posts'])==previous:return False
 invoke(u,'we_message',*u.simple_queue['posts'][-1])
 assert len(u.data['selections'])==menus,'Automatic claim asked for confirmation'
 return True


def automatic_claims():
 global checks
 u=fresh();event=simple_card(u,6);invoke(u,'we_test_accept',PARENT,0,0)
 before=money(u);station(u,army(4),slot(u)[2]);attach_queue(u)
 assert pump(u) and status(u)==0
 assert money(u)==expected_money(before,event['stages'][0]['choices'][0]['actions'])
 paid=money(u);assert not pump(u) and money(u)==paid;checks+=1
 # Failed capacity retries automatically on the next game day, not every frame.
 u=fresh();legacy_card(u,19,status_code=3,flags=1|8);migrate(u)
 before=money(u);u.data['full'].add('give_item');attach_queue(u)
 assert pump(u) and status(u)==3 and money(u)==before
 assert not pump(u) and money(u)==before
 u.data['full'].clear();w(u,HOURS,r(u,HOURS)+24)
 assert pump(u) and status(u)==0 and money(u)==before and len(u.data['grants'])==1
 assert not pump(u) and len(u.data['grants'])==1;checks+=1


def individual_bags(u,capacities):
 """Override the shared atomic gift boundary with per-army free-space budgets."""
 u.data['full'].add('give_item');u.data['gift_attempts']=[]
 pc=int(ACTION['give_item'],16)
 def boundary(u,address,size,data):
  if address!=pc:return
  # The common fixture has already returned this2-argument stdcall as full.
  sp=u.reg_read(UC_X86_REG_ESP);a,item=r(u,sp-8),r(u,sp-4)
  u.data['gift_attempts'].append(a)
  if capacities.get(a,0)>0:
   capacities[a]-=1;u.data['grants'].append(('give_item',(a,item)))
   u.reg_write(UC_X86_REG_EAX,1)
 u.hook_add(UC_HOOK_CODE,boundary)


def mobile(u,index,world_slot):
 a=army(index);actor=0x1380000+index*0x1000
 w(u,a+8,0);w(u,a+0x10,actor);w(u,actor+0x808,a);w(u,WORLD+0xac+world_slot*4,actor)


def reward_fallbacks():
 global checks
 for where in ('moving','hq63','preferred_full'):
  u=fresh();legacy_card(u,19,status_code=3,flags=1|8)
  w(u,CARD+12,0);w(u,CARD+16,0);no_armies(u)
  if where=='moving':mobile(u,1,0);mobile(u,4,1)
  elif where=='hq63':station(u,army(1),63);station(u,army(4),63)
  else:
   station(u,army(1),2);mobile(u,4,0);w(u,CARD+12,1);w(u,CARD+16,1)
  individual_bags(u,{army(1):0,army(4):1});before=money(u)
  assert invoke(u,'we_test_claim',PARENT,0)==1 and status(u)==0,where
  assert u.data['gift_attempts'][:2]==[army(1),army(4)],(where,u.data['gift_attempts'])
  assert u.data['grants']==[('give_item',(army(4),1))] and money(u)==before
  assert invoke(u,'we_test_claim',PARENT,0)==0 and len(u.data['grants'])==1
  checks+=1;gc.collect()
 # No army leaves the item pending; a newly available moving army resumes daily.
 u=fresh();legacy_card(u,19,status_code=3,flags=1|8)
 w(u,CARD+12,0);w(u,CARD+16,0);no_armies(u);migrate(u)
 budgets={army(4):1};individual_bags(u,budgets);before=money(u);attach_queue(u)
 assert pump(u) and status(u)==3 and money(u)==before and not u.data['grants']
 assert not pump(u) and not u.data['gift_attempts']
 mobile(u,4,0);w(u,HOURS,r(u,HOURS)+24)
 assert pump(u) and status(u)==0 and money(u)==before
 assert u.data['grants']==[('give_item',(army(4),1))]
 assert not pump(u) and len(u.data['grants'])==1;checks+=1


def run_all():
 global checks
 checks=0;migrations();legacy_rewards();natural_goals();automatic_claims();reward_fallbacks()
 for event in SIMPLE:run_simple(event['id']);gc.collect()
 user_reference()
 return checks


if __name__=='__main__':
 count=run_all()
 report=dict(status='passed',cases=count,event_count=len(SIMPLE),engine_sha256=hashlib.sha256(binary).hexdigest(),
  version=manifest['version'],test='test_world_event_simple.py',tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  scoped_mocks=['Native world fixture UI and atomic grant/battle adapters; separately tested by native action suite','Windows notice APIs and heap boundaries; compiled queue/present/claim execute'],
  coverage=['All38 single-goal paths without extra story/job/formation prerequisites','Old OFFER conversion and accepted/pending stage/choice/cost/reward preservation',
   'Rewarded follow-up offers close without new rewards; no old extra stages, duplicate money/items/recruits, or completion/cooldown reset','Any-army visits, army-free resources/buildings and ordinary conquest',
   'Posted-message automatic claims without extra confirmation, one-day capacity retry','Readonly first-slot save-bank migration fixture'],not_checked=['Hardware visual playtest','Full real save-file rewrite'])
 (ROOT/'test-world-simple-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print('PASS simple world contracts:',count,'native C cases; all38 goals, legacy migration and reward deduplication')
