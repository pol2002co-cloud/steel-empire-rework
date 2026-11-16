"""Annual random rewards keep the old340-byte save and pay exactly once."""
import functools
from test_expedition_native import *

YEAR_MASK=0xfffff
EXTRAS=((0,0,0),(30000,30,20),(100000,70,40),(0,0,0),(1000000,200,100))
checks=0

@functools.lru_cache(None)
def annual_seed(roll):
 return next(seed for seed in range(1,500001) if xorshift(seed)%10000==roll)

def annual(u,roll,index=0):
 s=state(u);w(u,s+8,annual_seed(roll));v=visit_cleared_ruin(u,index)
 return s,v

def cash(u):return tuple(r(u,p) for p in CASH)

def ordinary_people(u):
 for i in range(81):
  p=r(u,army(1)+0x60+i*4)
  if p:person(u,p,r(u,p),r(u,p+8),r(u,p+0x38))

def run_all():
 global checks
 checks=0
 # Exact odds boundaries:70/20/8.5/1.4/0.1 percent, additive base benefits.
 for roll,tier in ((0,0),(6999,0),(7000,1),(8999,1),(9000,2),(9849,2),(9850,3),(9989,3),(9990,4),(9999,4)):
  u=ready();s,v=annual(u,roll);before=cash(u);rng=r(u,s+8)
  assert r(u,v+8)>>20==tier+1 and not r(u,v+8)&YEAR_MASK
  assert invoke(u,'we_test_ex_bless',0,0)
  expected=tuple(a+b+c for a,b,c in zip(before,(20000,20,10),EXTRAS[tier]))
  assert cash(u)==expected,(roll,tier,cash(u),expected)
  assert r(u,v+4)==1 and r(u,s+8)==rng
  assert bool(r(u,s+16)&4)==(tier==3)
  paid=cash(u);assert not invoke(u,'we_test_ex_bless',0,0) and cash(u)==paid
  assert any('왕실의 보물고' in title for title,_ in u.data['texts'])==(tier==4)
  checks+=1

 # Cancelling, switching the chosen basic benefit and snapshot reload do not reroll.
 for roll in (6999,8999,9849,9989,9999):
  u=ready();s,v=annual(u,roll);encoded=r(u,v+8);rng=r(u,s+8);before=cash(u)
  assert not invoke(u,'we_test_ex_bless',0,3) and r(u,s+8)==rng
  u.data['answers']=[3];assert pump_ex(u)
  assert cash(u)==before and not r(u,v+4)
  assert r(u,v+8)==encoded|1 and r(u,s+8)==rng
  visit_cleared_ruin(u);assert r(u,v+8)==encoded|1 and r(u,s+8)==rng
  loaded=clone_runtime(u);s2=state(loaded);v2=visit(loaded)
  assert invoke(loaded,'we_test_ex_bless',0,2)
  assert cash(loaded)==tuple(a+b for a,b in zip(before,EXTRAS[(encoded>>20)-1]))
  assert r(loaded,v2+4)==1 and r(loaded,s2+8)==rng
  checks+=1

 # An overflow must not heal, grantXP, grant a relic or consume the annual use.
 for choice in (0,1,2):
  u=ready();s,v=annual(u,9999);ordinary_people(u)
  for i in range(81):
   p=r(u,army(1)+0x60+i*4)
   if p:w(u,p+0x54,1)
  w(u,CASH[0],2000000000);encoded=r(u,v+8);before=cash(u)
  assert not invoke(u,'we_test_ex_bless',0,choice)
  assert cash(u)==before and not r(u,v+4) and not u.exp_awards and not r(u,s+16)
  assert all(r(u,p+0x54)==1 for i in range(81) if (p:=r(u,army(1)+0x60+i*4)))
  assert r(u,v+8)==encoded
  w(u,CASH[0],1000);assert invoke(u,'we_test_ex_bless',0,choice)
  assert r(u,v+4)==1 and r(u,v+8)==encoded
  checks+=1
 for address in CASH[1:]:
  u=ready();s,v=annual(u,9999);w(u,address,2000000000);before=cash(u)
  assert not invoke(u,'we_test_ex_bless',0,2) and cash(u)==before and not r(u,v+4)
  checks+=1

 # Missing CRT/TLS support cannot grant the random bonus beforeXP succeeds.
 u=ready();s,v=annual(u,9999);ordinary_people(u);before=cash(u);encoded=r(u,v+8)
 def no_tls(u,pc,size,data):
  if pc==0x45290b:u.reg_write(UC_X86_REG_EAX,0)
 hook=u.hook_add(UC_HOOK_CODE,no_tls)
 assert not invoke(u,'we_test_ex_bless',0,1)
 assert cash(u)==before and not r(u,v+4) and not u.exp_awards and r(u,v+8)==encoded
 u.hook_del(hook);assert invoke(u,'we_test_ex_bless',0,1)
 assert cash(u)==tuple(a+b for a,b in zip(before,EXTRAS[4])) and r(u,v+4)==1
 checks+=1

 # Mystic events award the first missing permanent effect, then substitute cash.
 for held,expected,bonus in ((0,4,0),(4,12,0),(12,28,0),(28,28,150000),(31,31,150000)):
  u=ready();s=state(u);w(u,s+16,held);s,v=annual(u,9850);before=cash(u)
  assert invoke(u,'we_test_ex_bless',0,0)
  assert r(u,s+16)==expected and cash(u)==tuple(a+b+c for a,b,c in zip(before,(20000,20,10),(bonus,0,0)))
  assert not invoke(u,'we_test_ex_bless',0,2) and r(u,s+16)==expected
  checks+=1

 # Each ruin has its own yearly result; day360 requires a new physical visit.
 u=ready();s,a=annual(u,9999,0);_,b=annual(u,9850,1)
 assert invoke(u,'we_test_ex_bless',0,0) and invoke(u,'we_test_ex_bless',1,0)
 first=r(u,a+8);rng=r(u,s+8);w(u,HOURS,359*24);visit_cleared_ruin(u)
 assert r(u,a+8)==first and r(u,s+8)==rng and not invoke(u,'we_test_ex_bless',0,0)
 w(u,HOURS,360*24);assert not invoke(u,'we_test_ex_bless',0,0)
 w(u,s+8,annual_seed(7000));visit_cleared_ruin(u)
 assert r(u,a)==2 and r(u,a+8)==2<<20 and r(u,b+4)==1
 before=cash(u);assert invoke(u,'we_test_ex_bless',0,0)
 assert cash(u)==tuple(a+b for a,b in zip(before,(50000,50,30))) and r(u,a+4)==2
 checks+=1

 # Preservation scales the basic benefit, never multiplies a jackpot by accident.
 u=ready();s,v=annual(u,9999);w(u,v+20,1);before=cash(u)
 assert invoke(u,'we_test_ex_bless',0,0)
 assert cash(u)==tuple(a+b for a,b in zip(before,(1030000,230,115)));checks+=1

 # Current and old340-byte footers roundtrip; malformed packed fields fail closed.
 import test_expedition_save as physical
 for seen,artifacts in ((1,3),((5<<20)|1,31)):
  u=physical.ready_save();s=state(u);v=visit(u);w(u,v,1);w(u,v+4,1);w(u,v+8,seen);w(u,s+16,artifacts)
  assert physical.save(u)==1
  raw=u.files['data']['Steel0.Sav'];assert struct.unpack_from('<I',raw,len(raw)-20)[0]==340
  physical.load(u)
  assert r(u,visit(u)+8)==seen and r(u,state(u)+16)==artifacts and not r(u,state(u)+344)
  checks+=1
 for seen,artifacts in (((6<<20)|1,3),((1<<23)|1,3),(497104,3),(1,32)):
  u=physical.ready_save();s=state(u);v=visit(u);w(u,v,1);w(u,v+8,seen);w(u,s+16,artifacts)
  assert physical.save(u)==1;physical.load(u)
  assert not r(u,visit(u)) and not r(u,state(u)+16) and r(u,state(u)+344)==1
  checks+=1
 u=ready();s=state(u);v=visit(u);w(u,v,1);w(u,v+8,1);w(u,v+12,3<<16);w(u,s+8,annual_seed(9999))
 assert invoke(u,'we_test_ex_bless',0,0) and r(u,v+8)>>20==5
 assert r(u,v+8)&YEAR_MASK==1;checks+=1

 report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),version=manifest['version'],
  coverage=['Exact10000-way annual tier boundaries and additive basic rewards','Visit-time persisted roll, no reroll bydefer/reselection/runtime reload',
  'Money/iron/oil overflow andXP/TLS failure preserve result and annual use; no healing/relic beforepayment',
  'First-missing permanent effects, duplicate substitution, independent ruins and360-day rollover',
  'Old340-byte footer andpacked current records roundtrip; invalidseen/artifactmasks failclosed'],
  scoped_mocks=['Sharedcompiled game fixture Windows APIs/UI rendering and saved-world stream; actualstoredfooter C runs'],
  not_checked=['Hardware visual playtest','Statistical MonteCarlo randomness quality; exactbucket boundaries tested'])
 (ROOT/'test-ruin-random-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('PASS annual ruin random:',checks,'native tier/ledger/persistence cases')
 return checks

if __name__=='__main__':run_all()
