"""Compiled quest objective/shortage UI and optional unbound native movement."""
from test_world_event_simple import *
import datetime,hashlib,json

checks=0
def check(ok,why):
 global checks
 assert ok,why
 checks+=1
def texts(u):return '\n'.join(text for _,text in u.data['texts'])
def labels(u):return '\n'.join(text for row in u.data['selections'] for text in row)
def inspect(u,answers=(1,0,1,4)):
 u.data['texts'].clear();u.data['selections'].clear();return route(u,list(answers))

def run_all():
 global checks
 checks=0
 u=fresh();simple_card(u,0);w(u,CASH[1],3);invoke(u,'we_test_accept',PARENT,0,0)
 before=money(u);inspect(u)
 check('철 3/40' in texts(u) and '부족 37' in texts(u),'Resource detail must show exact current/needed/shortage')
 check(any(title=='목표와 보상' for title,_ in u.data['texts']) and '금 24,000' in texts(u),'Objective and reward remain explicit')
 check('진행' in labels(u) and '+금24000' in labels(u),'Quest list exposes status and primary reward')
 check(money(u)==before and status(u)==2,'Reading a shortage never spends or completes')

 u=fresh();simple_card(u,36);u.data['machines'][6]=0;invoke(u,'we_test_accept',PARENT,0,0);no_armies(u);inspect(u)
 check('고블린MK2 0/1' in texts(u),'Equipment detail must show missing spare count')
 check('승무원' in texts(u) and '수리' in texts(u),'Equipment eligibility is explained at the goal')
 check('목표 도시로 이동' not in labels(u),'A stock delivery does not ask for a courier')
 u=fresh();simple_card(u,1)
 for i in range(1,5):
  for j in range(80):w(u,army(i)+0x1a4+j*0x10c,0)
 invoke(u,'we_test_accept',PARENT,0,0);inspect(u)
 check('5mm 권총 0/1' in texts(u),'Spare-item goal shows its exact item and missing quantity')
 w(u,army(4)+0x1a4,1);invoke(u,'we_test_progress');before=money(u)
 check(status(u)==3 and invoke(u,'we_test_claim',PARENT,0)==1,'Any army spare still completes the item goal')
 check(r(u,CASH[0])==before[0]+2600 and invoke(u,'we_test_claim',PARENT,0)==0,'Item reward stays once-only')

 u=fresh();simple_card(u,3);set_building(u,6,2);invoke(u,'we_test_accept',PARENT,0,0);no_armies(u);inspect(u)
 check('포룸 창고' in texts(u) and '미완공' in texts(u),'Construction goal names the actual building state')
 check('목표 도시로 이동' not in labels(u),'Construction needs no assigned army')

 # A sole civilian army is sufficient for a visit, without binding the quest.
 u=fresh();simple_card(u,6);invoke(u,'we_test_accept',PARENT,0,0);target=slot(u)[2];no_armies(u,(4,));before=slot(u)
 inspect(u,(1,0,0,0,4));a=army(4);actor=r(u,a+0x10)
 check(actor and r(u,a+8)==0 and r(u,actor+0x50)==ap(target),'Optional move uses real departure and right-click target')
 check(slot(u)[3:5]==[0,0] and slot(u)[2]==before[2],'Moving never designates the completion army')
 check(not u.data['battles'],'Movement does not create an event arena')
 station(u,army(1),target);invoke(u,'we_test_progress')
 check(status(u)==3,'A different army may finish the moved quest')

 u=fresh();simple_card(u,6);invoke(u,'we_test_accept',PARENT,0,0);no_armies(u,(4,));before=bytes(u.mem_read(army(4),0x55b0));inspect(u,(1,0,0,1,4))
 check(bytes(u.mem_read(army(4),0x55b0))==before,'Cancelling the departure confirmation leaves the army untouched')
 u=fresh();simple_card(u,6);invoke(u,'we_test_accept',PARENT,0,0);no_armies(u);inspect(u,(1,0,0,4))
 check('이동 가능한 아군 군단이 없습니다' in texts(u),'No-army refusal explains the actual reason')

 # Occupation moves only a military formation and leaves normal capture rules.
 u=fresh();simple_card(u,24);invoke(u,'we_test_accept',PARENT,0,0);no_armies(u,(4,));target=slot(u)[2];inspect(u,(1,0,0,4))
 check('전투 군단' in texts(u) and r(u,army(4)+8)==tp(2),'Occupation does not send a civilian formation')
 u=fresh();simple_card(u,24);invoke(u,'we_test_accept',PARENT,0,0);no_armies(u,(1,));target=slot(u)[2];inspect(u,(1,0,0,0,4))
 check(r(u,tp(target)+0x10)&1 and not u.data['battles'] and status(u)==2,'Moving cannot award occupation or bypass the original battle')

 # Only unpaid simple contracts may be abandoned.
 u=fresh();simple_card(u,0);w(u,CASH[1],3);invoke(u,'we_test_accept',PARENT,0,0);before=money(u);inspect(u,(1,0,0,0,4))
 check(status(u)==0 and money(u)==before,'Confirmed abandon clears only the unpaid simple contract')
 check(not invoke(u,int(STATE['completed'],16),0),'Abandon is never a completion')
 u=fresh();simple_card(u,0);w(u,CASH[1],3);invoke(u,'we_test_accept',PARENT,0,0);inspect(u,(1,0,0,1,4))
 check(status(u)==2,'Abandon opt-out retains progress')
 u=fresh();legacy_card(u,6,flags=1);w(u,CARD+8,5);migrate(u);before=slot(u);inspect(u,(1,0,1,4))
 check(status(u)==2 and slot(u)[3:5]==before[3:5] and '포기할 수 없습니다' in texts(u),'Legacy and paid contracts remain protected')
 u=fresh();legacy_card(u,19,status_code=3,flags=1|8);migrate(u);u.data['full'].add('give_item');before=money(u);inspect(u,(1,0,4))
 check(status(u)==3 and money(u)==before,'Partial reward is retained and paid currency never repeats')
 check('+금60000' not in labels(u),'Pending list does not advertise already-paid currency')
 check('목표 도시로 이동' not in labels(u),'Reward pending has no movement/abandon action')

 u=fresh();simple_card(u,0);inspect(u,(1,3,0,4,4))
 check('다른 이벤트 완료' not in texts(u) and '38종' in labels(u),'Catalogue no longer displays obsolete prerequisite counters')
 check('의뢰 1/3' in labels(u),'Quest list shows occupied capacity without another popup')
 for row in u.data['selections']:check(len(row)<=5,'Native menus stay within five entries')

 # A new target varies within the closest/farthest three legal choices.
 chosen_near=set();chosen_far=set()
 for ident,results in ((6,chosen_near),(8,chosen_far)):
  u=fresh()
  for seed in range(1,31):
   simple_card(u,ident);w(u,BASE+4,seed)
   invoke(u,'we_test_accept',PARENT,0,0);results.add(slot(u)[2])
 check(len(chosen_near)==3 and chosen_near=={1,3,4},'Near targets rotate among the nearest three valid cities')
 check(len(chosen_far)==3,'Far targets also rotate instead of repeating one city')
 u=fresh();simple_card(u,6);invoke(u,'we_test_accept',PARENT,0,0)
 target=slot(u)[2];rng=r(u,BASE+4)
 inspect(u,(1,0,2,4));inspect(u,(1,0,2,4))
 check(slot(u)[2]==target and r(u,BASE+4)==rng,'Opening an active quest never rerolls its destination')
 for ident,expected in ((13,1),(32,40)):
  u=fresh();simple_card(u,ident);w(u,BASE+4,12345)
  invoke(u,'we_test_accept',PARENT,0,0)
  check((slot(u)[2] if status(u) else expected)==expected and r(u,BASE+4)==12345,'Fixed home/capital targets use no random draw')
 u=fresh();simple_card(u,31)
 for city in range(1,63):w(u,tp(city)+0x53000+19*0x300+8,2)
 for city in (10,11,12):w(u,tp(city)+0x53000+19*0x300+8,1)
 invoke(u,'we_test_accept',PARENT,0,0)
 check(slot(u)[2] in (10,11,12),'Airport targets retain the actual completed-facility condition')
 return checks

if __name__=='__main__':
 count=run_all()
 report=dict(status='passed',cases=count,engine_sha256=hashlib.sha256(binary).hexdigest(),version=manifest['version'],
  test='test_quest_usability.py',tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  coverage=['Exact objective, resource/item/equipment/build readiness, remaining rewards and concise five-row ledger',
   'Optional global army selection uses native movement without assigning the quest or changing ownership',
   'Opt-out, any-army completion, occupation military selection, protected legacy/paid/pending records'],
  scoped_mocks=['Shared native UI, formatting, departure/right-click target and grant adapters'],not_checked=['Hardware visual playtest'])
 (ROOT/'test-quest-usability-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('PASS quest usability:',count,'compiled objective/movement/protection cases')
