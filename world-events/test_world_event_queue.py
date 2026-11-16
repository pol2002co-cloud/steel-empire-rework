"""Deferred notice dispatch, real frame readiness and load-epoch cancellation."""
from test_world_events_native import *
import datetime,hashlib

HWND=0x123456;CONTROLLER=0x13a8000
QUEUE_KEY='SteelEmpireRework.NoticeQueue.0113'
LOADING_KEY='SteelEmpireRework.NoticeLoading.0113'
MESSAGE=0x86e0
GETMODULE,GETPROC=0x5fc000,0x5fc020
API={name:0x5fc100+i*0x20 for i,name in enumerate(('GetPropA','SetPropA','RemovePropA','PostMessageA','GetTickCount'))}
checks=0

def prepared():
 u=fixture();offer(u,0);u.data['default_answer']=1
 w(u,0x476fe8,HWND);w(u,0x48cc1c,CONTROLLER)
 w(u,CONTROLLER+4,3);w(u,CONTROLLER+0x10,PARENT)
 w(u,0x460060,GETMODULE);w(u,0x460100,GETPROC)
 u.queue=dict(properties={},posted=[],ticks=10000,allocations=[],frees=[],next_heap=0x13d0000,
              missing=set(),set_ok=True,post_ok=True,allocate_ok=True,requests=[])
 def result(u,value,cleanup=0):u.reg_write(UC_X86_REG_EAX,value&0xffffffff);ret(u,cleanup)
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP);q=u.queue
  if pc==GETMODULE:
   module=name(u,r(u,sp+4)).lower();assert module in ('user32.dll','kernel32.dll')
   result(u,0x600000 if module=='user32.dll' else 0x600100,4)
  elif pc==GETPROC:
   proc=name(u,r(u,sp+8));q['requests'].append(proc);assert proc in API,proc
   result(u,0 if proc in q['missing'] else API[proc],8)
  elif pc==API['GetPropA']:
   key=(r(u,sp+4),name(u,r(u,sp+8)));result(u,q['properties'].get(key,0),8)
  elif pc==API['SetPropA']:
   key=(r(u,sp+4),name(u,r(u,sp+8)))
   if q['set_ok']:q['properties'][key]=r(u,sp+12)
   result(u,int(q['set_ok']),12)
  elif pc==API['RemovePropA']:
   key=(r(u,sp+4),name(u,r(u,sp+8)));result(u,q['properties'].pop(key,0),8)
  elif pc==API['PostMessageA']:
   message=tuple(r(u,sp+4+i*4) for i in range(4))
   assert message[0]==HWND and message[1]==MESSAGE,message
   if q['post_ok']:q['posted'].append(message)
   result(u,int(q['post_ok']),16)
  elif pc==API['GetTickCount']:result(u,q['ticks'])
  elif pc==0x450452:
   assert r(u,sp+4)==20,'Only transient5DWORD queue allocations are expected'
   if q['allocate_ok']:
    pointer=q['next_heap'];q['next_heap']+=0x100;q['allocations'].append(pointer)
    u.mem_write(pointer,b'\xcc'*20)
   else:pointer=0
   result(u,pointer)
  elif pc==0x4500e6:
   pointer=r(u,sp+4);assert pointer in q['allocations'] and pointer not in q['frees']
   q['frees'].append(pointer);result(u,0)
 u.hook_add(UC_HOOK_CODE,boundary)
 return u

def bank(u):return bytes(u.mem_read(G,400))
def state(u):return u.queue['properties'].get((HWND,QUEUE_KEY),0)
def fields(u):return [r(u,state(u)+4*i) for i in range(5)] if state(u) else None
def idle(u,parent=PARENT):return invoke(u,'we_idle',parent)
def deliver(u,message=None):return invoke(u,'we_message',*(message or u.queue['posted'][-1]))
def no_ui(u):assert not u.data['selections'] and not u.data['texts']
def arm(u):
 before=bank(u);assert idle(u)==0;no_ui(u);assert bank(u)==before
 assert state(u) and fields(u)[0]==PARENT
 u.queue['ticks']+=1000;assert idle(u)==0
 assert len(u.queue['posted'])==1;no_ui(u)
 return u.queue['posted'][-1]

# Init/transition/controller mismatches cannot touch saved state, queue or UI.
for mode in ('state1','state2','state4','state5','no_controller','wrong_top','wrong_vtable',
             'no_world','modal','story','no_hwnd','null_parent'):
 u=prepared();parent=PARENT
 if mode.startswith('state'):w(u,CONTROLLER+4,int(mode[-1]))
 elif mode=='no_controller':w(u,0x48cc1c,0)
 elif mode=='wrong_top':w(u,CONTROLLER+0x10,PARENT+0x100)
 elif mode=='wrong_vtable':w(u,PARENT,0x4632d8)
 elif mode=='no_world':w(u,0x48c3d8,0)
 elif mode=='modal':w(u,0x4880e0,1)
 elif mode=='story':w(u,G+19*4,1)
 elif mode=='no_hwnd':w(u,0x476fe8,0)
 elif mode=='null_parent':parent=0
 before=bank(u);assert idle(u,parent)==0
 assert bank(u)==before and not u.queue['posted'] and not u.queue['allocations'],mode
 no_ui(u);checks+=1;gc.collect()

# Toolbar updates only queue. Native dialogs open from the later message handler.
for vtable in (0x462738,0x461954):
 u=prepared();w(u,PARENT,vtable);before=bank(u)
 assert idle(u)==0 and bank(u)==before
 u.queue['ticks']+=999;assert idle(u)==0 and not u.queue['posted'];no_ui(u)
 u.queue['ticks']+=1;assert idle(u)==0 and len(u.queue['posted'])==1;no_ui(u)
 message=u.queue['posted'][0];assert message[3]==PARENT and message[2]==fields(u)[1]
 assert fields(u)[2]==1;assert idle(u)==0 and len(u.queue['posted'])==1;no_ui(u)
 assert deliver(u,message)==0
 assert len(u.data['selections'])==1 and slot(u)[5]&(1<<30)
 assert fields(u)[2:4]==[0,0]
 count=len(u.data['selections']);assert deliver(u,message)==0 and len(u.data['selections'])==count
 checks+=1;gc.collect()

# Wrong Windows message/owner/generation/parent never acknowledge a real offer.
for mode in ('message','hwnd','generation','parent'):
 u=prepared();correct=arm(u);bad=list(correct)
 bad[{'hwnd':0,'message':1,'generation':2,'parent':3}[mode]]+=1
 before=bank(u);assert deliver(u,bad)==0 and bank(u)==before;no_ui(u)
 assert deliver(u,correct)==0 and len(u.data['selections'])==1
 checks+=1;gc.collect()

# A queued message is harmless if a dialog/load/frame transition starts meanwhile.
for mode in ('state1','state2','state4','state5','top','modal','story','loading','warmup'):
 u=prepared();message=arm(u)
 if mode.startswith('state'):w(u,CONTROLLER+4,int(mode[-1]))
 elif mode=='top':w(u,CONTROLLER+0x10,PARENT+0x100)
 elif mode=='modal':w(u,0x4880e0,1)
 elif mode=='story':w(u,G+19*4,1)
 elif mode=='loading':u.queue['properties'][(HWND,LOADING_KEY)]=1
 elif mode=='warmup':u.queue['ticks']=fields(u)[4]+999
 before=bank(u);assert deliver(u,message)==0 and bank(u)==before;no_ui(u)
 assert fields(u)[2]==0
 checks+=1;gc.collect()

# A dialog already being handled cannot recursively open another event window.
u=prepared();message=arm(u);w(u,state(u)+12,1);before=bank(u)
assert idle(u)==1 and bank(u)==before;no_ui(u)
assert deliver(u,message)==0 and bank(u)==before and fields(u)[3]==1;no_ui(u)
w(u,state(u)+12,0);assert idle(u)==0 and len(u.queue['posted'])==2
assert deliver(u)==0 and len(u.data['selections'])==1;checks+=1

# Loading before any queue allocation sets a transient guard, with no save writes.
u=prepared();before=bank(u)
invoke(u,'we_load_begin');assert u.queue['properties'][(HWND,LOADING_KEY)]==1
assert not state(u) and not u.queue['allocations'] and bank(u)==before
u.queue['ticks']+=5000;assert idle(u)==0 and not u.queue['posted'];no_ui(u)
invoke(u,'we_load_end');assert (HWND,LOADING_KEY) not in u.queue['properties']
assert idle(u)==0 and not u.queue['posted'] and bank(u)==before
u.queue['ticks']+=999;assert idle(u)==0 and not u.queue['posted']
u.queue['ticks']+=1;assert idle(u)==0 and len(u.queue['posted'])==1;no_ui(u)
assert deliver(u)==0 and len(u.data['selections'])==1;checks+=1

# Same parent address and same game clock cannot revive a pre-load queued message.
u=prepared();stale=arm(u);hours=r(u,HOURS);original=bank(u)
invoke(u,'we_load_begin');assert bank(u)==original
assert fields(u)[1]!=stale[2] and fields(u)[0]==0 and fields(u)[2]==0
u.queue['ticks']+=5000;assert idle(u)==0;assert deliver(u,stale)==0;no_ui(u)
invoke(u,'we_load_end');assert r(u,HOURS)==hours and bank(u)==original
assert idle(u)==0;u.queue['ticks']+=999;assert idle(u)==0;assert deliver(u,stale)==0;no_ui(u)
u.queue['ticks']+=1;assert idle(u)==0
fresh=u.queue['posted'][-1];assert fresh[2]!=stale[2] and fresh[3]==stale[3]
assert deliver(u,stale)==0;no_ui(u)
assert deliver(u,fresh)==0 and len(u.data['selections'])==1;checks+=1

# Parent changes arm a fresh warmup and invalidate the old parent's message.
u=prepared();stale=arm(u);other=PARENT+0x200
w(u,other,0x461954);w(u,CONTROLLER+0x10,other)
assert idle(u,other)==0 and fields(u)[0]==other
assert deliver(u,stale)==0;no_ui(u)
u.queue['ticks']+=1000;assert idle(u,other)==0
assert u.queue['posted'][-1][3]==other
# Use a postponed offer; base fixture UI validates strings, not a fixed owner.
assert deliver(u)==0 and len(u.data['selections'])==1;checks+=1

# API and allocator failures leave no unowned heap or accidental UI invocation.
for mode in ('missing_api','allocation_failure','set_failure','post_failure'):
 u=prepared();before=bank(u)
 if mode=='missing_api':u.queue['missing'].add('PostMessageA')
 elif mode=='allocation_failure':u.queue['allocate_ok']=False
 elif mode=='set_failure':u.queue['set_ok']=False
 elif mode=='post_failure':u.queue['post_ok']=False
 assert idle(u)==0
 u.queue['ticks']+=1000;assert idle(u)==0
 no_ui(u);assert not u.queue['posted']
 if mode=='post_failure':
  assert fields(u)[2]==0;u.queue['post_ok']=True;assert idle(u)==0 and len(u.queue['posted'])==1
 else:
  assert bank(u)==before
  assert len(u.queue['allocations'])==len(u.queue['frees'])
 checks+=1;gc.collect()

# Unsigned GetTickCount rollover preserves the one-second warmup.
u=prepared();u.queue['ticks']=0xffffff00;assert idle(u)==0
u.queue['ticks']=(0xffffff00+999)&0xffffffff;assert idle(u)==0 and not u.queue['posted']
u.queue['ticks']=(0xffffff00+1000)&0xffffffff;assert idle(u)==0 and len(u.queue['posted'])==1
assert deliver(u)==0 and len(u.data['selections'])==1;checks+=1

# WM_NCDESTROY adapter cleanup is idempotent and cancels every pending callback.
u=prepared();stale=arm(u);invoke(u,'we_load_begin')
invoke(u,'we_window_close',HWND)
assert not u.queue['properties'] and len(u.queue['frees'])==len(u.queue['allocations'])==1
invoke(u,'we_window_close',HWND)
assert len(u.queue['frees'])==1 and deliver(u,stale)==0;no_ui(u);checks+=1

# Transient modal guards from an interrupted old session never survive a load.
u=prepared();tour=0x60000200;w(u,G+82*4,tour|0x80000000)
invoke(u,'we_load_begin');invoke(u,'we_load_end')
assert r(u,G+82*4)==tour;no_ui(u);checks+=1

digest=hashlib.sha256(binary).hexdigest()
report=dict(status='passed',cases=checks,engine_sha256=digest,version=manifest['version'],
 tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),test='test_world_event_queue.py',
 coverage=['Controller running3/currentparent and world/city readiness; no UI or save writes during init/load/transition',
  'Runtime Windows properties and heap; only PostMessage from toolbar; native UI deferred to message dispatch',
  'Generation, owner, parent, modal/story/loading guards and full same-parent/same-clock reload cancellation',
  'One-second warmup, GetTickCount rollover, failures and idempotent window-destruction cleanup'],
 scoped_mocks=['Windows module/proc/property/PostMessage/tick APIs and native allocator/free boundaries',
  'Common native fixture UI renderer/selection; event present and queue C execute'],
 not_checked=['Hardware save-load/render visual playtest'])
(ROOT/'test-world-queue-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS deferred notice queue:',checks,'native C cases; load/frame readiness, pure deferred UI, generations, warmup, API failures, same-save reload and window cleanup')
