from test_patch import *
import random

cases=0
for faction in [12,14,15,16,18,20]:
 for typ in range(3):
  if faction==15 and typ==1: continue
  for stage in range(2):
   for seed in range(5):
    u=setup();sp=u.reg_read(UC_X86_REG_ESP);army=0x1000000
    for j,v in enumerate([0x5f0000,faction,army,typ,stage]):w(u,sp+j*4,v)
    w(u,army+0x14,1);rng=random.Random(seed);allocated=[0x1010000]
    def hook(u,a,size,data):
     s=u.reg_read(UC_X86_REG_ESP)
     if a==0x45046d:u.reg_write(UC_X86_REG_EAX,rng.randrange(32768));ret(u)
     elif a in [0x414ed0,0x416660]:
      p=allocated[0];allocated[0]+=0x800;w(u,p,r(u,s+4));w(u,p+4,r(u,s+4))
      if a==0x414ed0:w(u,p+0x38,r(u,s+4));w(u,p+0x48,r(u,s+8))
      u.reg_write(UC_X86_REG_EAX,p);ret(u,8 if a==0x414ed0 else 4)
     elif a==0x4162b0:ret(u,8)
     elif a in [0x415aa0,0x4168b0]:u.reg_write(UC_X86_REG_EAX,0);ret(u)
    u.hook_add(UC_HOOK_CODE,hook)
    u.emu_start(0x418fa0,0x5f0000,count=500000)
    assert u.reg_read(UC_X86_REG_EIP)==0x5f0000,(faction,typ,stage,seed,hex(u.reg_read(UC_X86_REG_EIP)))
    assert u.reg_read(UC_X86_REG_ESP)==sp+4
    assert r(u,army+0x1c)==[80,25,9][typ],(faction,typ,r(u,army+0x1c))
    assert r(u,army+0x20)==[0,7,9][typ]
    persons=[r(u,army+0x60+i*4) for i in range(81) if r(u,army+0x60+i*4)]
    assert len(persons)==len(set(persons))
    cases+=1
print('PASS:',cases,'complete army-generation simulations with stubbed allocation/equipment; finite placement and maximum counts')
old=(ROOT/'SteelEmpire-v062.exe').read_bytes()
oldpe=pefile.PE(data=old)
for faction in range(1,22):
 for typ in range(3):
  for stage in range(2):
   states=[]
   for original in [True,False]:
    u=setup()
    if original:u.mem_write(0x400000,oldpe.get_memory_mapped_image())
    sp=u.reg_read(UC_X86_REG_ESP)
    for j,v in enumerate([0x5f0000,faction,0x1000000,typ,stage]):w(u,sp+j*4,v)
    u.emu_start(0x418fa0,0x419088,count=10000)
    s=u.reg_read(UC_X86_REG_ESP)
    states.append((bytes(u.mem_read(s,0x168)),[u.reg_read(x) for x in [UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS]]))
   a,b=states
   assert a[1]==b[1],(faction,typ,'registers')
   allowed=set(range(0x18,0x1c))|set(range(0x44,0x68)) if faction in [12,14,15,16,18,20] else set()
   assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(a[0],b[0])))
allowed=set(range(pe.get_offset_from_rva(0x19083),pe.get_offset_from_rva(0x19083)+5))
allowed.update(range(pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')+4))
start=pe.get_offset_from_rva(int(manifest['enemy_strength_hook'],16)-0x400000)
allowed.update(range(start,pe.sections[-1].PointerToRawData+pe.sections[-1].SizeOfRawData))
vs=pe.sections[-1].get_field_absolute_offset('Misc_VirtualSize')
allowed.update(range(vs,vs+4))
assert pe.sections[-1].Misc_VirtualSize<=pe.sections[-1].SizeOfRawData
assert len(old)==len(binary)
assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(old,binary)))
assert (ROOT/'patch104-v062.pak').read_bytes()==(ROOT/'package/patch104.pak').read_bytes()
print('PASS: 126 profile comparisons; original levels, equipment pools and registers preserved; other factions unchanged; previous patches and archive byte-preserved')

