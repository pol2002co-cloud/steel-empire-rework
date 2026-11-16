"""Compiled feature save/load paired with actual hidden-army codecs.

The original whole-world stream is a bounded fixture. Its expedition roster
images execute stock419b70/419ca0, while all appendix and lifecycle C is real.
"""
from test_expedition_native import *
import copy,struct,json,hashlib

GETPROC=0x5fb020;APPFUNC=0x5fb900;BOX=0x5fb100
FILE=0x13b9000;CODEC=0x1480000;CM=0x1450000;CRECS=0x1460000
CODEC_SIZE=0x3c80
FILE_APIS={n:0x5fa000+i*32 for i,n in enumerate(('CreateFileA','ReadFile','WriteFile','SetFilePointer','GetFileSize','FlushFileBuffers','CloseHandle','DeleteFileA','MoveFileExA','GetTempFileNameA'))}
NOTICE_APIS={n:0x5fc100+i*32 for i,n in enumerate(('GetPropA','SetPropA','RemovePropA','PostMessageA','GetTickCount'))}
checks=0

def wide(u,p):
 b=bytearray()
 for i in range(1000):
  x=bytes(u.mem_read(p+i*2,2))
  if x==b'\0\0':return b.decode('utf-16le')
  b.extend(x)
 raise AssertionError('Unbounded wide message')

def native_call(u,pc,*args):
 sp=0x13e0000;w(u,sp,STOP)
 for i,a in enumerate(args):w(u,sp+4+i*4,a)
 u.reg_write(UC_X86_REG_ESP,sp)
 before={reg:u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)}
 try:u.emu_start(pc,STOP,count=3000000)
 except Exception:
  print('native codec failure',hex(u.reg_read(UC_X86_REG_EIP)),hex(u.reg_read(UC_X86_REG_ECX)),hex(u.reg_read(UC_X86_REG_EDX)))
  raise
 assert u.reg_read(UC_X86_REG_EIP)==STOP and u.reg_read(UC_X86_REG_ESP)==sp+4
 assert before=={reg:u.reg_read(reg) for reg in before}
 return u.reg_read(UC_X86_REG_EAX)

def setup_io(u):
 u.mem_map(0x1440000,0x80000);w(u,0x460100,GETPROC)
 for address,value in ((0x476fd8,0x13b8000),(0x13b8000,0x13b8100),(0x13b8100+0x14,APPFUNC),(0x4880e8,CM),(CM,13),(CM+4,CRECS),
                       (0x4880ec,0x1470000),(0x1470000,1),(0x1470004,0x1471000),(0x1471000,1),(0x147102c,16382)):
  w(u,address,value)
 for job in range(1,14):
  p=CRECS+(job-1)*0x4e4
  for offset,value in ((0,job),(8,1),(0x38,job),(0x44,1<<job),(0x48,1),(0x50,100),(0x54,100),(0x58,100)):
   w(u,p+offset,value)
 u.files=dict(data={'Steel0.Sav':bytearray(b'previous native slot'),'Steel1.Sav':bytearray(b'another native slot')},handles={},next_handle=100,temps=0,
              fail=set(),missing=set(),writer=None,events=[],boxes=[],snapshots={},pending_snapshot=None,world_positions={},freed=[])
 def answer(u,value,argc=0):u.reg_write(UC_X86_REG_EAX,value&0xffffffff);ret(u,argc*4)
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP);q=u.files
  if pc==GETPROC:
   proc=name(u,r(u,sp+8));target=NOTICE_APIS.get(proc,FILE_APIS.get(proc,BOX if proc=='MessageBoxW' else 0))
   assert target or proc in q['missing'],proc;answer(u,0 if proc in q['missing'] else target,2)
  elif pc==BOX:
   q['boxes'].append((r(u,sp+4),wide(u,r(u,sp+8)),wide(u,r(u,sp+12)),r(u,sp+16)));answer(u,1,4)
  elif pc==FILE_APIS['GetTempFileNameA']:
   if 'temp' in q['fail']:answer(u,0,4);return
   q['temps']+=1;p='SEP%03d.tmp'%q['temps'];q['data'][p]=bytearray();u.mem_write(r(u,sp+16),p.encode()+b'\0');q['events'].append(('temp',p));answer(u,1,4)
  elif pc==0x4502b6:
   path=name(u,r(u,sp+4));q['events'].append(('native_open',path))
   if 'native_open' in q['fail']:answer(u,0);return
   q['writer']=path;q['data'][path]=bytearray();w(u,FILE+12,0);answer(u,FILE)
  elif pc==0x405720:answer(u,123)
  elif pc==APPFUNC:answer(u,456)
  elif pc==0x4502c9:
   p,n,count,file=(r(u,sp+i) for i in (4,8,12,16));assert file==FILE
   q['data'][q['writer']].extend(u.mem_read(p,n*count));answer(u,count)
  elif pc in (0x446760,0x435240,0x449600,0x447e90,0x4226c0):
   assert r(u,sp+4)==FILE
   if pc==0x4226c0:
    q['world_positions'][q['writer']]=len(q['data'][q['writer']]);q['data'][q['writer']].extend(q['pending_snapshot']['codecs'])
   elif pc==0x435240:q['data'][q['writer']].extend(bytes(u.mem_read(G,400)))
   else:q['data'][q['writer']].extend(bytes([pc&255])*256)
   if 'native_write' in q['fail']:w(u,FILE+12,r(u,FILE+12)|0x20)
   answer(u,1,1 if pc in (0x446760,0x447e90,0x4226c0) else 0)
  elif pc==0x4500f1:answer(u,0xffffffff if 'native_close' in q['fail'] else 0)
  elif pc==FILE_APIS['CreateFileA']:
   p=name(u,r(u,sp+4));q['events'].append(('open',p))
   if p not in q['data'] or 'open' in q['fail']:answer(u,0xffffffff,7);return
   h=q['next_handle'];q['next_handle']+=1;q['handles'][h]=[p,0];answer(u,h,7)
  elif pc==FILE_APIS['GetFileSize']:answer(u,len(q['data'][q['handles'][r(u,sp+4)][0]]),2)
  elif pc==FILE_APIS['SetFilePointer']:
   h,pos=r(u,sp+4),r(u,sp+8);q['handles'][h][1]=pos;answer(u,pos,4)
  elif pc==FILE_APIS['ReadFile']:
   h,p,n,out=(r(u,sp+i) for i in (4,8,12,16));path,pos=q['handles'][h];raw=bytes(q['data'][path][pos:pos+n]);u.mem_write(p,raw);q['handles'][h][1]+=len(raw);w(u,out,len(raw));answer(u,1,5)
  elif pc==FILE_APIS['WriteFile']:
   h,p,n,out=(r(u,sp+i) for i in (4,8,12,16));path,pos=q['handles'][h];raw=bytes(u.mem_read(p,n));q['data'][path][pos:pos+n]=raw;q['handles'][h][1]+=n;w(u,out,n);answer(u,0 if 'write' in q['fail'] else 1,5)
  elif pc==FILE_APIS['FlushFileBuffers']:answer(u,int('flush' not in q['fail']),1)
  elif pc==FILE_APIS['CloseHandle']:q['handles'].pop(r(u,sp+4),None);answer(u,1,1)
  elif pc==FILE_APIS['DeleteFileA']:q['data'].pop(name(u,r(u,sp+4)),None);answer(u,1,1)
  elif pc==FILE_APIS['MoveFileExA']:
   old,new=name(u,r(u,sp+4)),name(u,r(u,sp+8));assert r(u,sp+12)==9
   if 'replace' in q['fail']:answer(u,0,3);return
   q['data'][new]=q['data'].pop(old);q['world_positions'][new]=q['world_positions'].pop(old)
   q['snapshots'][new]=q['pending_snapshot'];answer(u,1,3)
  elif pc==0x4500e6:
   # The existing fixture has already returned this cdecl function.
   q['freed'].append(r(u,u.reg_read(UC_X86_REG_ESP)))
 u.hook_add(UC_HOOK_CODE,boundary)
 return u

def snapshot(u):
 codecs=bytearray()
 for slot in range(4):
  a=tp(1)+0x104+(slot+9)*0x55b0;assert native_call(u,0x419b70,a,CODEC)==CODEC
  codecs.extend(u.mem_read(CODEC,CODEC_SIZE))
 return dict(codecs=bytes(codecs),town=bytes(u.mem_read(tp(1),0x51000)),people=bytes(u.mem_read(PEOPLE,0x20000)),
             bank=bytes(u.mem_read(G,400)),cash=tuple(r(u,p) for p in CASH),hours=r(u,HOURS))

def save(u,slot=0):
 u.files['pending_snapshot']=snapshot(u)
 return invoke(u,'we_save',slot)

def restore_native_world(u,slot=0):
 """Fixture-native header/master/waiting restore, then real army decoder."""
 filename='Steel%d.Sav'%slot;s=u.files['snapshots'][filename];raw=u.files['data'][filename]
 u.mem_write(tp(1),s['town']);u.mem_write(PEOPLE,s['people']);u.mem_write(G,s['bank']);w(u,HOURS,s['hours'])
 for p,value in zip(CASH,s['cash']):w(u,p,value)
 offset=u.files['world_positions'][filename]
 for index in range(4):
  a=tp(1)+0x104+(index+9)*0x55b0;u.mem_write(a,b'\0'*0x55b0)
  u.mem_write(CODEC,bytes(raw[offset+index*CODEC_SIZE:offset+(index+1)*CODEC_SIZE]))
  assert native_call(u,0x419ca0,CODEC,a,tp(1))==a

def load(u,slot=0):restore_native_world(u,slot);invoke(u,'we_load_game',slot,1)
def waiting(u):
 found=[];node=r(u,WAITING)
 for _ in range(10001):
  if node==WAITING:return found
  assert r(u,r(u,node)+4)==node and r(u,r(u,node+4))==node
  found.append(r(u,node+8));node=r(u,node)
 raise AssertionError('Waiting ring did not terminate')
def ready_save(**kwargs):return setup_io(ready(**kwargs))

# Real native party images and real C appendix agree after a saved/loaded mission.
u=ready_save();assert start(u);s=state(u)
for offset,value in ((12,7),(16,3),(20,9),(VISIT,1),(VISIT+4,1),(VISIT+8,1),(VISIT+20,1)):w(u,s+offset,value)
expected=bytes(u.mem_read(s,SAVE_BYTES));reserved=invoke(u,'ex_resolve',tp(1),0)
assert save(u)==1;raw=bytes(u.files['data']['Steel0.Sav']);footer=struct.unpack('<8I',raw[-32:])
assert raw[footer[4]:-32]==expected and footer[3]==SAVE_BYTES
advance(u,30);assert pump_ex(u) and not r(u,run(u));assert len(waiting(u))==25
load(u);assert bytes(u.mem_read(state(u),SAVE_BYTES))==expected
a=invoke(u,'ex_resolve',tp(1),0);assert a==reserved and r(u,a+0x1c)==23 and r(u,a+0x34)==HEROES
assert len(waiting(u))==5 and all(r(u,p+0x10)==10 for p in u.exp_heroes[:3])
before=r(u,CASH[0]);awards=len(u.exp_awards);advance(u,30);assert pump_ex(u) and r(u,CASH[0])>before and not r(u,run(u))
assert len(waiting(u))==25 and len(set(waiting(u)))==25 and len(u.exp_awards)>awards
paid=r(u,CASH[0]);awards=len(u.exp_awards);assert not pump_ex(u) and r(u,CASH[0])==paid and len(u.exp_awards)==awards;checks+=1

# Already-paid cash/XP survive a real footer+roster roundtrip while return waits.
u=ready_save();assert start(u);advance(u,30);invoke(u,'we_idle',PARENT);u.exp_fail_alloc=True
assert pump_ex(u) and r(u,run(u))==3 and r(u,run(u)+36)&3==3
u.exp_fail_alloc=False;paid=r(u,CASH[0]);awards=len(u.exp_awards)
assert save(u)==1;load(u)
assert r(u,run(u))==3 and r(u,run(u)+36)&3==3 and r(u,CASH[0])==paid
advance(u,1);assert pump_ex(u) and not r(u,run(u))
assert r(u,CASH[0])==paid and len(u.exp_awards)==awards and len(waiting(u))==25;checks+=1

# Footer corruption and old versions protect-return native members without rewards.
for corruption in ('crc','legacy'):
 u=ready_save();assert start(u);assert save(u)==1
 raw=u.files['data']['Steel0.Sav'];base=struct.unpack_from('<I',raw,len(raw)-16)[0]
 if corruption=='crc':raw[-1]^=1
 else:del raw[base:]
 load(u);assert r(u,run(u))==4;cash=r(u,CASH[0]);awards=len(u.exp_awards)
 for _ in range(4):
  if not r(u,run(u)):break
  assert pump_ex(u)
 assert not r(u,run(u)) and not invoke(u,'ex_resolve',tp(1),0)
 assert len(waiting(u))==25 and len(set(waiting(u)))==25
 assert r(u,CASH[0])==cash and len(u.exp_awards)==awards;checks+=1

# Changing another native field keeps valid metadata; an old slot starts empty.
u=ready_save();assert start(u);assert save(u)==1;expected=bytes(u.mem_read(state(u),SAVE_BYTES))
u.files['data']['Steel0.Sav'][200]^=1;load(u)
assert bytes(u.mem_read(state(u),SAVE_BYTES))==expected and r(u,run(u))==1;checks+=1
u=ready_save();state(u);assert save(u,1)==1
raw=u.files['data']['Steel1.Sav'];base=struct.unpack_from('<I',raw,len(raw)-16)[0];del raw[base:]
w(u,state(u)+12,7);w(u,state(u)+16,3);load(u,1)
assert not r(u,state(u)+12) and not r(u,state(u)+16) and not r(u,run(u));checks+=1

# Failed native load and new-game reset never borrow an unrelated save's state.
u=ready_save();assert start(u);expected=bytes(u.mem_read(state(u),SAVE_BYTES));events=len(u.files['events'])
invoke(u,'we_load_game',5,0)
assert bytes(u.mem_read(state(u),SAVE_BYTES))==expected and len(u.files['events'])==events;checks+=1
old=u.simple_queue['properties'][(0x123456,KEY)];invoke(u,'we_world_reset')
assert (0x123456,KEY) not in u.simple_queue['properties'] and u.files['freed'].count(old)==1;checks+=1

# Save errors are immediate Unicode warnings; old slot and live party are intact.
for fault in ('native_write','write','flush','replace'):
 u=ready_save();assert start(u);live=bytes(u.mem_read(state(u),SAVE_BYTES));old=bytes(u.files['data']['Steel0.Sav']);u.files['fail'].add(fault)
 assert save(u)==0 and bytes(u.files['data']['Steel0.Sav'])==old and bytes(u.mem_read(state(u),SAVE_BYTES))==live
 assert len(u.files['boxes'])==1
 owner,text,title,flags=u.files['boxes'][0];assert owner==0x123456 and title=='저장 실패' and '유지' in text and flags&0x10
 assert not u.files['handles'] and not any(p.startswith('SEP') for p in u.files['data']);checks+=1
u=ready_save();state(u);u.exp_fail_alloc=True;invoke(u,'we_world_reset');old=bytes(u.files['data']['Steel0.Sav'])
assert invoke(u,'we_save',0)==0 and bytes(u.files['data']['Steel0.Sav'])==old and len(u.files['boxes'])==1;checks+=1
u=ready_save();state(u);u.files['fail'].add('replace');u.files['missing'].add('MessageBoxW')
assert save(u)==0 and not u.files['boxes'];assert pump_ex(u)
assert any('저장하지 못했습니다' in text for _,text in u.data['texts']);checks+=1

report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),version=manifest['version'],
 coverage=['Actual we_save/es_save/clone/appendix paired with actual419b70/419ca0 roster codecs',
 'Active mission metadata restores with members, completes once, and never duplicates generic waiting entries',
 'Corrupt/legacy footer protected-return has no XP or cash; unrelated native body edit remains compatible',
 'Failed native load preserves live state, constructor reset frees own record, immediate UTF16 save errors preserve slot'],
 scoped_mocks=['Whole native world stream/header/master/waiting restoration bounded fixtures; hidden army codecs execute',
 'Win32 properties/file APIs, UI renderer, ordinary native top-level serialization callees'],
 not_checked=['Hardware save-menu/gameplay roundtrip','Real disk failure; separate storage smoke uses actual Win32 files'])
(ROOT/'test-expedition-save-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS integrated expedition saves:',checks,'native roster/appendix/lifecycle/fault cases')
