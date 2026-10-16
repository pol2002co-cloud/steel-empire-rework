from test_battle import *
for recognized in [False,True]:
 for living in [0,1,40,81]:
  for commander_alive in [False,True]:
   u,b,a,e,units=fixture();w(u,e+0x138,int(commander_alive));w(u,b+0xe48,99)
   for i in range(81):
    if i>=living:w(u,b+0x36c+i*4,0)
   board=bytes(u.mem_read(b+0x36c,81*4));ally=bytes(u.mem_read(a,0x180));seen=[]
   def hook(u,pc,size,data):
    sp=u.reg_read(UC_X86_REG_ESP)
    if pc==0x406420:
     ptr=r(u,sp+4)
     assert bytes(u.mem_read(0x46f068,11)).split(b'\0')[0]==b'qmfkqhslzp'
     u.reg_write(UC_X86_REG_EAX,int(recognized and ptr==0x46f068));ret(u,4)
    elif pc==0x406280:seen.append('clear');ret(u)
    elif pc==0x446210:seen.append('message');ret(u,4)
   u.hook_add(UC_HOOK_CODE,hook);sp=u.reg_read(UC_X86_REG_ESP)
   u.emu_start(0x43c826,0x43c8ea,count=10000)
   assert u.reg_read(UC_X86_REG_EIP)==0x43c8ea
   assert u.reg_read(UC_X86_REG_ESP)==sp
   assert bytes(u.mem_read(a,0x180))==ally
   assert bytes(u.mem_read(b+0x36c,81*4))==board
   if recognized:
    assert seen==['clear','message']
    assert r(u,b+0x1d8)==6 and r(u,b+0xe48)==0
    assert r(u,e+0x138)==0
    for i in range(living):
     p=r(u,b+0x36c+i*4)
     assert [r(u,p+x) for x in [0x138,0x54,0x13c]]==[0,0,0]
   else:assert seen==[] and r(u,b+0x1d8)==0 and r(u,b+0xe48)==99
old=(ROOT/'SteelEmpire-v071.exe').read_bytes();oldpe=pefile.PE(data=old)
allowed=set(range(pe.get_offset_from_rva(0x3c860),pe.get_offset_from_rva(0x3c860)+12))
for off,n in [(pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),4),(pe.sections[-1].get_field_absolute_offset('Misc_VirtualSize'),4)]:allowed.update(range(off,off+n))
start=pe.get_offset_from_rva(int(manifest['victory_cheat'],16)-0x400000)
allowed.update(range(start,pe.sections[-1].PointerToRawData+pe.sections[-1].SizeOfRawData))
assert len(old)==len(binary) and all(a==b or i in allowed for i,(a,b) in enumerate(zip(old,binary)))
print('PASS: 32 cheat/non-cheat recognition cases; immediate settlement; all enemies eliminated; player units retained; previous executable changes isolated')
