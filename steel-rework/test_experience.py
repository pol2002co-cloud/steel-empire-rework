from test_patch import *
old=(ROOT/'SteelEmpire-v061.exe').read_bytes();new=binary
allowed=set(range(pe.get_offset_from_rva(0x39d9f),pe.get_offset_from_rva(0x39d9f)+5))|set(range(pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')+4))
assert len(old)==len(new)
assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(old,new)))
for xp in [-1,0,4,5,199,200,201,500,1000,10000,1000000,2147483647]:
 u=setup();u.reg_write(UC_X86_REG_EAX,xp & 0xffffffff);sp=u.reg_read(UC_X86_REG_ESP)
 u.emu_start(0x439d89,0x439da4,count=50)
 assert u.reg_read(UC_X86_REG_ESI)==max(5,xp)
 assert u.reg_read(UC_X86_REG_ESP)==sp
print('PASS: 12 XP boundary cases; 201 through signed-int maximum retained; only XP clamp and PE checksum bytes changed')
