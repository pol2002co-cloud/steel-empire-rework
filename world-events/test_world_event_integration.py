"""F8 extension routing and safe world/city idle dispatch in the built game."""
from test_patch import *

J=manifest['event_journal'];W=manifest['world_events'];C=manifest['campaign']
extension=int(J['extension_pointer'],16);router=int(W['router'],16);tick=int(W.get('idle',W['tick']),16)
assert r(setup(),extension)==router
PARENT,TOOLBAR,KEYBOARD,STUB=0x1000000,0x1001000,0x1002000,0x1201000
checks=0

for vtable in (0x461954,0x462738,0x4632d8):
 for busy,world,keyboard,key in ((0,1,1,1),(1,1,1,1),(0,0,1,1),(0,1,0,1),(0,1,1,0)):
  for mode in (None,0,1):
   u=setup();seen=[]
   for address,value in ((TOOLBAR+0x18,PARENT),(PARENT,vtable),(0x4880e0,busy),
                         (0x48c3d8,world),(0x487f3c,KEYBOARD if keyboard else 0),
                         (extension,0 if mode is None else STUB)):
    w(u,address,value)
   u.reg_write(UC_X86_REG_ESI,TOOLBAR)
   def hook(u,address,size,data):
    sp=u.reg_read(UC_X86_REG_ESP)
    if address==0x406390:
     assert r(u,sp+4)==0x77 and r(u,sp+8)==1
     seen.append('key');u.reg_write(UC_X86_REG_EAX,key);ret(u,8)
    elif address==STUB:
     assert r(u,sp+4)==PARENT;seen.append('router');u.reg_write(UC_X86_REG_EAX,mode);ret(u,4)
    elif address==int(J['main'],16):
     assert r(u,sp+4)==PARENT;seen.append('legacy');ret(u,4)
    elif address==0x40a43e:u.emu_stop()
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x40a438,0,count=20000)
   supported=vtable in (0x461954,0x462738) and not busy and world and keyboard
   expected=(['key'] if supported else [])
   if supported and key:
    if mode is not None:expected+=['router']
    if mode!=1:expected+=['legacy']
   assert seen==expected,(vtable,busy,world,keyboard,key,mode,seen)
   assert u.reg_read(UC_X86_REG_ESP)==0x13f0000
   assert u.reg_read(UC_X86_REG_ESI)==TOOLBAR
   assert u.reg_read(UC_X86_REG_ECX)==(KEYBOARD if keyboard else 0)
   checks+=1

seed=int(manifest['imperial_campaign']['seed'],16)
restore=int(manifest['black_power_return']['restore'],16)
delivery=int(manifest['quest_convenience']['process'],16)
for vtable in (0x461954,0x462738,0x4632d8):
 for busy,world,keyboard in ((0,1,1),(1,1,1),(0,0,1),(0,1,0)):
  u=setup();seen=[]
  for address,value in ((TOOLBAR+0x18,PARENT),(PARENT,vtable),(0x4880e0,busy),
                        (0x48c3d8,world),(0x487f3c,KEYBOARD if keyboard else 0)):
   w(u,address,value)
  u.reg_write(UC_X86_REG_ESI,TOOLBAR)
  def hook(u,address,size,data):
   sp=u.reg_read(UC_X86_REG_ESP)
   if address in (tick,delivery):
    assert r(u,sp+4)==PARENT;seen.append('tick' if address==tick else 'delivery')
    u.reg_write(UC_X86_REG_EAX,0);ret(u,4)
   elif address in (seed,restore):
    seen.append('seed' if address==seed else 'restore');ret(u)
   elif address==0x406390:
    assert r(u,sp+4)==0x78 and r(u,sp+8)==1
    seen.append('key');u.reg_write(UC_X86_REG_EAX,0);ret(u,8)
   elif address==0x40a461:u.emu_stop()
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x40a45b,0,count=20000)
  supported=vtable in (0x461954,0x462738) and not busy and world
  expected=['tick','seed','restore','delivery'] if supported else []
  if supported and vtable==0x462738 and keyboard:expected+=['key']
  assert seen==expected,(vtable,busy,world,keyboard,seen)
  assert u.reg_read(UC_X86_REG_ESP)==0x13f0000
  assert u.reg_read(UC_X86_REG_ESI)==TOOLBAR
  assert u.reg_read(UC_X86_REG_ECX)==(KEYBOARD if keyboard else 0)
  checks+=1
# Opening a native automatic event consumes the callback before F9/other work.
for vtable in (0x461954,0x462738):
 u=setup();seen=[]
 for address,value in ((TOOLBAR+0x18,PARENT),(PARENT,vtable),(0x48c3d8,1),(0x487f3c,KEYBOARD)):
  w(u,address,value)
 u.reg_write(UC_X86_REG_ESI,TOOLBAR)
 def consumed(u,address,size,data):
  if address==tick:seen.append('automatic');u.reg_write(UC_X86_REG_EAX,1);ret(u,4)
  elif address in (seed,restore,delivery,0x406390):raise AssertionError('Old frame continued after automatic event')
  elif address==0x40a461:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,consumed);u.emu_start(0x40a45b,0,count=20000)
 assert seen==['automatic'] and u.reg_read(UC_X86_REG_ESP)==0x13f0000
 assert u.reg_read(UC_X86_REG_ESI)==TOOLBAR;checks+=1
print('PASS: %d F8 extension/fallback and idle tick safety cases; original main preserved; native toolbar stack/registers' % checks)
