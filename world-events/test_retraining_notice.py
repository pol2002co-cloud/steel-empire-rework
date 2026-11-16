"""Actual retraining timer -> deferred native completion dialogue."""
from test_world_event_simple import fresh,attach_queue,pump,invoke,army,tp,PARENT,HOURS,G,w,r,ret,ROOT,manifest,binary
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
import json,hashlib
FAC=0x13b0000
PERSON=0x13c0000
KEY='SteelEmpireRework.TrainingCompleted.0121'
checks=0

def fixture(count=1,due=True,active=True):
 u=fresh();attach_queue(u);u.training=[];w(u,FAC+4,tp(2));w(u,FAC+0x38,count)
 for i in range(count):
  slot=FAC+0x250+i*0x4f8;p=PERSON+i*0x100
  for offset,value in ((0,int(active)),(4,0),(0xc,24 if due else 2401),(0x4f4,p)):w(u,slot+offset,value)
  for offset,value in ((0,6),(4,2),(8,1),(0x38,6),(0x48,30),(0x54,100),(0x58,100)):w(u,p+offset,value)
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if pc==0x4151e0:
   p=r(u,sp+4);w(u,p+0x38,7);ret(u,8)
  elif pc==0x438760:
   assert u.reg_read(UC_X86_REG_ECX)==tp(2)
   assert r(u,sp+4)==3 and r(u,sp+8)==FAC
   u.training.append(r(u,sp+16));ret(u,16)
 u.hook_add(UC_HOOK_CODE,boundary)
 return u

def progress(u):
 sp=0x13e0000;stop=0x5ff000;w(u,sp,stop);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,FAC)
 preserved={reg:u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)}
 u.emu_start(0x4323d0,stop,count=1000000)
 assert u.reg_read(UC_X86_REG_EIP)==stop and u.reg_read(UC_X86_REG_ESP)==sp+4
 assert preserved=={reg:u.reg_read(reg) for reg in preserved}

def pending(u):return u.simple_queue['properties'].get((0x123456,KEY),0)

for count in (1,5,6):
 u=fixture(count);progress(u)
 assert len(u.training)==count and pending(u)==count,'Completed retraining has no deferred notification'
 assert all(r(u,FAC+0x250+i*0x4f8)==0 for i in range(count))
 assert not u.data['texts'] and not u.data['selections'],'UI opened in timer update'
 progress(u);assert pending(u)==count and len(u.training)==count
 assert pump(u) and pending(u)==0
 assert any('재훈련' in text and str(count) in text for title,text in u.data['texts'])
 shown=len(u.data['texts']);assert not pump(u) and len(u.data['texts'])==shown
 checks+=1

for due,active in ((False,True),(True,False),(False,False)):
 u=fixture(due=due,active=active);progress(u)
 assert not u.training and pending(u)==0 and not pump(u);checks+=1

for guard in ('modal','story','loading','wrong_frame'):
 u=fixture();progress(u);before=len(u.data['texts'])
 if guard=='modal':w(u,0x4880e0,1)
 elif guard=='story':w(u,G+19*4,1)
 elif guard=='loading':invoke(u,'we_load_begin')
 else:w(u,0x13a8000+0x10,PARENT+0x100)
 assert not pump(u) and len(u.data['texts'])==before
 if guard=='modal':w(u,0x4880e0,0)
 elif guard=='story':w(u,G+19*4,0)
 elif guard=='loading':invoke(u,'we_load_end')
 else:w(u,0x13a8000+0x10,PARENT)
 assert bool(pump(u))==(guard!='loading');checks+=1

u=fixture();progress(u);invoke(u,'we_window_close',0x123456)
assert not pending(u);checks+=1
report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),version=manifest['version'],
 coverage=['Actual4323d0 timer/slot completion and repeat safety','1/5/6 trainees aggregated without modal UI in timer',
 'Actual posted-message notification with modal/story/load/frame safeguards'],
 scoped_mocks=['4151e0 promotion and438760 waiting-roster registration; separately tested by expansion suite','Windows APIs and UI rendering'],
 not_checked=['Hardware visual playtest'])
(ROOT/'test-retraining-notice-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS retraining completion:',checks,'native timer/queued notification cases')
