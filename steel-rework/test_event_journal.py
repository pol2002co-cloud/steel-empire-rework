from test_patch import *
from event_catalog import EVENTS,RELATED
from event_decode import decode_script
from unicorn import UC_HOOK_MEM_WRITE
import re
j=manifest['event_journal'];addr=lambda k:int(j[k],16)
STOP=0x13df000;FMT=0x13de000;PARENT=0x1000000
def cstr(u,a):
 b=bytearray()
 for i in range(4096):
  x=u.mem_read(a+i,1)[0]
  if not x:return b.decode('cp949')
  b.append(x)
 raise AssertionError('Unterminated string')

def run_main(choices,flags=None,metrics=False,expected=None):
 u=setup();w(u,0x46019c,FMT);dialogs=[];menus=[];sequence=list(choices)
 for key,val in (flags or {}).items():w(u,0x48d398+key*4,val&0xffffffff)
 initial=bytes(u.mem_read(0x48d398,400));writes=[]
 def hook(u,a,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if a==STOP:u.emu_stop()
  elif a==FMT:
   fmt=cstr(u,r(u,sp+8));args=[]
   for i,t in enumerate(re.findall('%[sd]',fmt)):
    x=r(u,sp+12+4*i);args.append(cstr(u,x) if t=='%s' else x if x<2**31 else x-2**32)
   b=(fmt%tuple(args)).encode('cp949')+b'\0';assert len(b)<=256
   u.mem_write(r(u,sp+4),b);ret(u)
  elif a==addr('select'):
   assert r(u,sp+4)==PARENT;array=r(u,sp+8);count=r(u,sp+12);assert 1<=count<=5
   labels=[cstr(u,r(u,array+4*i)) for i in range(count)];menus.append(labels)
   assert all(len(t.encode('cp949'))<=75 for t in labels),labels
   assert sequence,('Unexpected menu',labels)
   u.reg_write(UC_X86_REG_EAX,sequence.pop(0)&0xffffffff);ret(u,12)
  elif a==addr('speech'):
   assert r(u,sp+4)==PARENT;title=cstr(u,r(u,sp+8));t=cstr(u,r(u,sp+12));assert t.endswith('@w')
   dialogs.append((title,t));ret(u,12)
  elif a==0x44b5b0:
   u.reg_write(UC_X86_REG_EAX,{0:31,1:6,3:8000000}[r(u,sp+4)]);ret(u,4)
  elif a==0x44b660:
   assert cstr(u,r(u,sp+4))=='비트만' and r(u,sp+8)==1
   u.reg_write(UC_X86_REG_EAX,35);ret(u,8)
  elif a==0x44b8c0:u.reg_write(UC_X86_REG_EAX,{1:11,2:10,3:2026}[r(u,sp+4)]);ret(u,4)
 def guard(u,access,a,size,val,data):
  if 0x48d398<=a<0x48d528:writes.append((a,size,val))
 u.hook_add(UC_HOOK_MEM_WRITE,guard);u.hook_add(UC_HOOK_CODE,hook)
 sp=0x13f0000;w(u,sp,STOP);w(u,sp+4,PARENT)
 regs=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
 for i,reg in enumerate(regs):u.reg_write(reg,0xabc000+i)
 u.emu_start(addr('main'),0,count=1000000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP and u.reg_read(UC_X86_REG_ESP)==sp+8
 assert not sequence
 if expected is None:assert not writes and bytes(u.mem_read(0x48d398,400))==initial
 else:
  assert all(a in [0x48d398+98*4,0x48d398+99*4] for a,size,val in writes)
  final=bytearray(initial)
  for k,v in expected.items():struct.pack_into('<I',final,k*4,v)
  assert bytes(u.mem_read(0x48d398,400))==bytes(final)
 for i,reg in enumerate(regs):assert u.reg_read(reg)==0xabc000+i
 return dialogs,menus

cases=0
for n,e in enumerate(EVENTS):
 for state in list(e['states'])+[-1,99]:
  d,m=run_main([3]*(n//3)+[n%3,0,4,4],{e['flag']:state})
  assert str(state) in d[0][1]
  if state in e['states']:assert e['states'][state] in d[0][1]
  else:assert '기록에 없는 단계' in d[0][1]
  cases+=1
 for mode in [1,2,3]:
  d,m=run_main([3]*(n//3)+[n%3,mode]+([0,3] if mode==1 else [])+[4,4])
  assert d;cases+=1
d,m=run_main([3,3,3,0,1,2,3,4],{19:1,27:7,16:2026,17:10,18:20})
assert len(d)>len(RELATED)
assert any('35 / 동료 명단 31명' in t and '군단 6 / 부채 8000000' in t for _,t in d)
assert any('2026년 10월 11일' in t for _,t in d)
assert any('진행 중: 1' in t for _,t in d)
assert m[-1][0].startswith('시작과 상속')
run_main([-1])

# UI wrapper calling conventions/lifetimes, with only rendering primitives stubbed.
for name,nargs,size,ctor,opener,closer in [('select',3,0x3c,0x412f40,0x413080,0x412fe0),('speech',3,0x150,0x412580,0x412810,0x412760)]:
 u=setup();seen=[];obj=[];sp=0x13f0000;w(u,sp,STOP);w(u,sp+4,PARENT)
 string=0x1010000;u.mem_write(string,'테스트@w\0'.encode('cp949'))
 w(u,sp+8,string);w(u,sp+12,string)
 if name=='select':
  w(u,sp+8,0x1011000);w(u,sp+12,5)
  for i in range(5):w(u,0x1011000+i*4,string)
 def hook(u,a,n,data):
  stack=u.reg_read(UC_X86_REG_ESP);this=u.reg_read(UC_X86_REG_ECX)
  if a==STOP:u.emu_stop();return
  if a==ctor:obj.append(this);u.mem_write(this,b'\0'*size);seen.append('construct');ret(u)
  elif a==opener:assert this==obj[0] and r(u,stack+4)==PARENT;seen.append('open');ret(u,12)
  elif a==0x4130b0:assert this==obj[0];seen.append('append');ret(u,4)
  elif a==0x413240:seen.append('choose');u.reg_write(UC_X86_REG_EAX,2);ret(u)
  elif a==0x412910:assert r(u,stack+8)==0;seen.append('speaker');ret(u,8)
  elif a==0x412960:assert cstr(u,r(u,stack+4))=='테스트@w';seen.append('text');ret(u,4)
  elif a==closer:assert this==obj[0];seen.append('destroy');ret(u)
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(addr(name),0,count=20000)
 assert u.reg_read(UC_X86_REG_ESP)==sp+16 and seen[0]=='construct' and seen[-1]=='destroy'
 if name=='select':assert seen.count('append')==5 and u.reg_read(UC_X86_REG_EAX)==2

# F8 supported parents only, consumed once; original ECX is restored for F1.
for vt,busy,world,key in [(0x461954,0,1,1),(0x462738,0,1,1),(0x461954,1,1,1),(0x461954,0,0,1),(0x461954,0,1,0),(0x4632d8,0,1,1)]:
 u=setup();toolbar=0x1001000;keyboard=0x1002000;calls=[]
 w(u,toolbar+0x18,PARENT);w(u,PARENT,vt);w(u,0x4880e0,busy);w(u,0x48c3d8,world);w(u,0x487f3c,keyboard)
 u.reg_write(UC_X86_REG_ESI,toolbar)
 def hook(u,a,n,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if a==0x406390:
   assert r(u,sp+4)==0x77 and r(u,sp+8)==1;u.reg_write(UC_X86_REG_EAX,key);ret(u,8)
  elif a==addr('main'):assert r(u,sp+4)==PARENT;calls.append(1);ret(u,4)
  elif a==0x40a43e:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x40a438,0,count=20000)
 assert len(calls)==int(vt in [0x461954,0x462738] and not busy and world and key)
 assert u.reg_read(UC_X86_REG_ESI)==toolbar and u.reg_read(UC_X86_REG_ECX)==keyboard and u.reg_read(UC_X86_REG_ESP)==0x13f0000

# Preserve every pre-v0.8 instruction/data byte, except the exact toolbar hook,
# PE size/checksum/section metadata, and newly used extension-section padding.
old=(ROOT/'SteelEmpire-v074.exe').read_bytes();op=pefile.PE(data=old)
allowed=set(range(pe.get_offset_from_rva(0xa438),pe.get_offset_from_rva(0xa438)+6))
allowed.update(range(pe.get_offset_from_rva(0x4a494),pe.get_offset_from_rva(0x4a494)+6))
allowed.update(range(pe.get_offset_from_rva(0x48677),pe.get_offset_from_rva(0x48677)+6))
allowed.update(range(pe.get_offset_from_rva(0x4868d),pe.get_offset_from_rva(0x4868d)+2))
for field in ['SizeOfCode','SizeOfImage','CheckSum']:
 a=pe.OPTIONAL_HEADER.get_field_absolute_offset(field);allowed.update(range(a,a+4))
a=pe.sections[-1].get_file_offset();allowed.update(range(a,a+40))
start=op.sections[-1].PointerToRawData+op.sections[-1].Misc_VirtualSize
allowed.update(range(start,len(old)))
diff={i for i in range(len(old)) if old[i]!=binary[i]};assert diff<=allowed,(diff-allowed)
for f in (ROOT/'extracted/patch102.pak').glob('*.cmp'):
 rows=decode_script(f);targets={r['addr'] for r in rows}
 for r0 in rows:
  if 'GOTO ' in r0['text']:assert int(r0['text'].split('GOTO ')[1]) in targets,(f,r0)
assert pe.verify_checksum()
print(f'PASS: {cases} event-state/condition/route cases; all 16 related fields; metrics/navigation; native UI wrapper lifetimes; F8 gating; flags read-only; v0.7.4 byte isolation; 78 decoded scripts')
