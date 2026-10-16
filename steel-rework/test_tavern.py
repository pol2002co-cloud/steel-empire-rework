from test_patch import *

for money in [0,1,5000,1000000]:
 u=setup();npc=0x1000000;entry=0x1010000;sp=u.reg_read(UC_X86_REG_ESP)
 w(u,entry+0x14,money);w(u,npc+0xa4,123)
 u.reg_write(UC_X86_REG_EBX,entry);u.reg_write(UC_X86_REG_EAX,npc)
 u.emu_start(0x42bc4c,0x42bc57,count=20)
 assert r(u,npc+0xa4)==0 and r(u,entry+0x14)==money
 assert u.reg_read(UC_X86_REG_ESP)==sp-4 and r(u,sp-4)==12

for state in [0,1,2]:
 for slot in range(6):
  u=setup();ui=0x1000000;npc=0x1010000;sp=u.reg_read(UC_X86_REG_ESP)
  w(u,ui+0x64+slot*4,state);w(u,npc+0x3c,1)
  u.reg_write(UC_X86_REG_EDI,ui);u.reg_write(UC_X86_REG_ESI,npc);u.reg_write(UC_X86_REG_EBP,slot)
  # Execute argument push, modified call and the actual hiring threshold.
  u.emu_start(0x42cb3e,0x42cb57,count=100)
  assert u.reg_read(UC_X86_REG_EIP)==0x42cb57
  assert u.reg_read(UC_X86_REG_ESP)==sp
  # Original acceptance sets recruited status; actual roster transfer happens
  # through the unchanged tavern-exit code after the player chooses hire.
  w(u,sp+0x1bc,slot)
  u.emu_start(0x42cc32,0x42cc45,count=20)
  assert r(u,ui+slot*4+0x64)==2

old=(ROOT/'SteelEmpire-v073.exe').read_bytes()
allowed=set()
for va,n in [(0x42bc4c,3),(0x42cb41,5)]:
 off=pe.get_offset_from_rva(va-0x400000);allowed.update(range(off,off+n))
for off in [pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),pe.sections[-1].get_field_absolute_offset('Misc_VirtualSize')]:allowed.update(range(off,off+4))
oldpe=pefile.PE(data=old);start=oldpe.sections[-1].PointerToRawData+oldpe.sections[-1].Misc_VirtualSize
allowed.update(range(start,pe.sections[-1].PointerToRawData+pe.sections[-1].SizeOfRawData))
assert len(old)==len(binary) and all(a==b or i in allowed for i,(a,b) in enumerate(zip(old,binary)))
assert (ROOT/'patch104-v062.pak').read_bytes()==(ROOT/'package/patch104.pak').read_bytes()
print('PASS: 4 bankroll cases; 18 hiring cases across all six slots; stack cleanup; recruited status; only tavern patches and PE metadata changed, archive unchanged')
