from test_patch import *
sys.stdout.reconfigure(encoding='utf-8')
for faction in [12,14,15,16,18,20]:
 for typ in [0,1,2]:
  for stage in [0,1]:
   u=setup();sp=u.reg_read(UC_X86_REG_ESP)
   for j,x in enumerate([0x5f0000,faction,0x1000000,typ,stage]):w(u,sp+j*4,x)
   u.emu_start(0x418fa0,0x419083,count=10000);s=u.reg_read(UC_X86_REG_ESP)
   print(faction,typ,stage,'commander',u.reg_read(UC_X86_REG_EBP),u.reg_read(UC_X86_REG_EBX),u.reg_read(UC_X86_REG_ESI),'level',r(u,s+0x10),u.reg_read(UC_X86_REG_EDX),'inf',r(u,s+0x18),'class',[r(u,s+0x1c+j*4) for j in range(3)],'weap',[r(u,s+0x2c+j*4) for j in range(6)],'veh',[r(u,s+0x44+j*4) for j in range(9)])
