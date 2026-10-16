from test_event_journal import *
from event_force_patch import MAGIC_ADDR,MASK_ADDR,MAGIC,TRIGGERS

for n,e in enumerate(EVENTS):
 prefix=[3]*(n//3)+[n%3,1]
 # Enable persists, disable only clears this event; views never initialize data.
 run_main(prefix+[1,3,4,4],expected={98:MAGIC,99:1<<n})
 run_main(prefix+[1,2,3,4,4],expected={98:MAGIC,99:0})
 run_main(prefix+[1,3,4,4],{98:MAGIC,99:511},expected={98:MAGIC,99:511})
 for state in [1,2,10,11,99,-1]:
  run_main(prefix+[1,3,4,4],{e['flag']:state})

STOP=0x13df000;MANAGER=0x1000000;BLOB=0x1020000;LOCALS=0x1010000
original=pefile.PE(str(ROOT/'SteelEmpire-v080.exe')).get_memory_mapped_image()
def evaluate(blob,row,values,old=False):
 u=setup()
 if old:u.mem_write(0x400000,original)
 u.mem_write(BLOB,blob);w(u,MANAGER+0x1cc,BLOB);w(u,MANAGER+0x1d0,BLOB);w(u,MANAGER+0x1d8,BLOB+(row['addr']+1)*4);w(u,MANAGER+0x1dc,LOCALS)
 for k,v in values.items():w(u,0x48d398+k*4,v)
 before=bytes(u.mem_read(0x48d398,400))
 u.reg_write(UC_X86_REG_ECX,MANAGER);sp=0x13f0000;w(u,sp,STOP)
 u.hook_add(UC_HOOK_CODE,lambda uc,a,n,d:uc.emu_stop() if a==STOP else None)
 u.emu_start(0x44a360,0,count=20000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP and u.reg_read(UC_X86_REG_ESP)==sp+4
 after=bytes(u.mem_read(0x48d398,400));assert before[:396]==after[:396]
 return r(u,MANAGER+0x1d8),r(u,MASK_ADDR),u

count=0
triggers={(name,start):flag for name,start,flag in TRIGGERS}
for path in (ROOT/'extracted/patch102.pak').glob('*.cmp'):
 blob=path.read_bytes()
 for row in decode_script(path):
  if not row['text'].startswith('IF '):continue
  a,_,_=evaluate(blob,row,{})
  b,_,_=evaluate(blob,row,{},True);assert a==b,(path,row)
  values={98:MAGIC,99:511}
  a,mask,_=evaluate(blob,row,values)
  b,_,_=evaluate(blob,row,values,True)
  flag=triggers.get((path.stem,row['addr']))
  if flag:
   assert a==BLOB+int(row['text'].split('GOTO ')[1])*4
   assert mask==511^(1<<(flag-3))
  else:assert a==b and mask==511,(path,row)
  count+=1

for name,start,flag in TRIGGERS:
 path=ROOT/'extracted/patch102.pak'/f'{name}.cmp';blob=path.read_bytes()
 row=next(r0 for r0 in decode_script(path) if r0['addr']==start)
 for state in [0,1,2,10,11,99]:
  for busy in [0,1,2]:
   for magic,mask in [(0,511),(MAGIC,0),(MAGIC,511)]:
    values={flag:state,19:busy,98:magic,99:mask}
    a,result,u=evaluate(blob,row,values);b,_,_=evaluate(blob,row,values,True)
    forced=state==0 and busy==0 and magic==MAGIC and mask==511
    assert a==(BLOB+int(row['text'].split('GOTO ')[1])*4 if forced else b)
    assert result==(mask & ~(1<<(flag-3)) if magic==MAGIC and mask and (state or forced) else mask)
    # Resume the first original assignment, proving the real story flag starts.
    if forced:
     w(u,MANAGER+0x1d8,a+4);u.reg_write(UC_X86_REG_ECX,MANAGER);w(u,0x13f0000,STOP);u.reg_write(UC_X86_REG_ESP,0x13f0000)
     u.emu_start(0x44a2a0,0,count=20000)
     assert r(u,0x48d398+flag*4)==1

# A reserved marker prevents an old save's arbitrary spare mask from enabling.
# New game clears all 100 dwords, save/load keep the original 400-byte block.
u=setup();u.mem_write(0x48d398,b'\xff'*400);w(u,0x13f0000,STOP)
u.hook_add(UC_HOOK_CODE,lambda uc,a,n,d:uc.emu_stop() if a==STOP else None)
u.emu_start(0x4495e0,0,count=20000);assert bytes(u.mem_read(0x48d398,400))==b'\0'*400
print(f'PASS: force menu enable/disable and 54 replay locks; {count} original VM predicates differential-tested; 486 trigger state/lock/setting cases; original first assignments; new-game reset')

saved=[]
for entry,io in [(0x449600,0x4502c9),(0x449620,0x45016e)]:
 u=setup();w(u,0x13f0000,STOP);w(u,0x13f0004,0x1234)
 if entry==0x449600:
  w(u,MAGIC_ADDR,MAGIC);w(u,MASK_ADDR,511);w(u,0x48d398+5*4,10)
 def io_hook(u,a,n,data):
  if a==STOP:u.emu_stop()
  elif a==io:
   sp=u.reg_read(UC_X86_REG_ESP)
   assert [r(u,sp+i) for i in [4,8,12,16]]==[0x48d398,400,1,0x1234]
   if entry==0x449600:saved.append(bytes(u.mem_read(0x48d398,400)))
   else:u.mem_write(0x48d398,saved[0])
   u.reg_write(UC_X86_REG_EAX,1);ret(u)
 u.hook_add(UC_HOOK_CODE,io_hook);u.emu_start(entry,0,count=20000)
 assert r(u,MAGIC_ADDR)==MAGIC and r(u,MASK_ADDR)==511 and r(u,0x48d398+20)==10
print('PASS: original save/load routines round-trip force settings and completed-event records without a format change')

