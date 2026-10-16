from test_patch import *
MAN=0x1000000;HEAD=0x1001000;BASE=0x1002000;STOP=0x13df000
def fixture(n):
 u=setup();nodes=[BASE+i*0x200 for i in range(n)];w(u,MAN+4,HEAD);w(u,MAN+8,n)
 w(u,HEAD,nodes[0] if n else HEAD);w(u,HEAD+4,nodes[-1] if n else HEAD)
 for i,a in enumerate(nodes):
  w(u,a,nodes[i+1] if i+1<n else HEAD);w(u,a+4,nodes[i-1] if i else HEAD)
  w(u,a+8,3);w(u,a+12,1);w(u,a+24,47);w(u,a+8+0x124,5040000)
 return u,nodes
def remaining(u):
 out=[];p=r(u,HEAD)
 while p!=HEAD:
  assert p not in out;out.append(p);p=r(u,p)
 assert len(out)==r(u,MAN+8)
 for i,a in enumerate(out):assert r(u,a+4)==(out[i-1] if i else HEAD)
 assert r(u,HEAD+4)==(out[-1] if out else HEAD)
 return out
count=0
for n in range(7):
 for index in range(-2,n):
  u,nodes=fixture(n);freed=[];target=nodes[index]+8 if index>=0 else 0 if index==-1 else 0x1010000
  w(u,target+4,1) if target else None
  w(u,target+16,47) if target else None
  def hook(u,a,size,data):
   if a==STOP:u.emu_stop()
   elif a==0x4500e6:freed.append(r(u,u.reg_read(UC_X86_REG_ESP)+4));ret(u)
  u.hook_add(UC_HOOK_CODE,hook);sp=0x13f0000;w(u,sp,STOP);w(u,sp+4,target);u.reg_write(UC_X86_REG_ECX,MAN)
  for reg in [UC_X86_REG_EBX,UC_X86_REG_EBP,UC_X86_REG_ESI,UC_X86_REG_EDI]:u.reg_write(reg,0x12345678)
  u.emu_start(0x448660,0,count=20000)
  assert remaining(u)==[a for i,a in enumerate(nodes) if i!=index]
  assert freed==([nodes[index]] if index>=0 else [])
  assert u.reg_read(UC_X86_REG_ESP)==sp+8
  for reg in [UC_X86_REG_EBX,UC_X86_REG_EBP,UC_X86_REG_ESI,UC_X86_REG_EDI]:assert u.reg_read(reg)==0x12345678
  count+=1

# Reproduce stock bug, then execute the identical reward/cleanup path patched.
for old in [True,False]:
 u,nodes=fixture(2)
 if old:
  oldpe=pefile.PE(str(ROOT/'SteelEmpire-v081.exe'));u.mem_write(0x400000,oldpe.get_memory_mapped_image())
 town=0x1100000;origin=0x1180000;item=0x1200000;w(u,item,73);w(u,nodes[1]+8+24,73)
 w(u,0x46e5d8,1000);w(u,0x48d394,MAN)
 u.reg_write(UC_X86_REG_ESI,nodes[1]+8);u.reg_write(UC_X86_REG_EDI,town);u.reg_write(UC_X86_REG_EBX,origin)
 def settle(u,a,size,data):
  if a==0x44b293:u.emu_stop()
  elif a==0x438d90:u.reg_write(UC_X86_REG_EAX,item);ret(u,4)
  elif a==0x4500e6:ret(u)
 u.hook_add(UC_HOOK_CODE,settle);u.emu_start(0x44b240,0,count=20000)
 assert r(u,0x46e5d8)==5041000 and r(u,item)==0
 assert remaining(u)==([nodes[1]] if old else [nodes[0]])
 assert r(u,town+0x509f4)==1 and r(u,origin+0x509f4)==1

old=(ROOT/'SteelEmpire-v081.exe').read_bytes();op=pefile.PE(data=old)
allowed=set(range(pe.get_offset_from_rva(0x48677),pe.get_offset_from_rva(0x48677)+6))
allowed.update(range(pe.get_offset_from_rva(0x4868d),pe.get_offset_from_rva(0x4868d)+2))
for field in ['CheckSum']:
 a=pe.OPTIONAL_HEADER.get_field_absolute_offset(field);allowed.update(range(a,a+4))
a=pe.sections[-1].get_file_offset();allowed.update(range(a,a+40))
allowed.update(range(op.sections[-1].PointerToRawData+op.sections[-1].Misc_VirtualSize,len(old)))
diff={i for i in range(len(old)) if old[i]!=binary[i]};assert diff<=allowed
assert pe.verify_checksum()
print(f'PASS: {count} exact removal/null/nonmember/list cases; stock wrong-quest deletion reproduced; patched payout removes only paid quest, money/item/reputation unchanged; v081 byte isolation')
