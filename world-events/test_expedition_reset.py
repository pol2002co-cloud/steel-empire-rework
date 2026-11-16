"""Actual World-constructor hook, distinct from ordinary actor registration."""
from pathlib import Path
import sys,struct,json,hashlib
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'tools/python-deps-v093'))
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *

binary=(ROOT/'package/SteelEmpire.exe').read_bytes();pe=pefile.PE(data=binary)
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf8'))
assert manifest['output_sha256']==hashlib.sha256(binary).hexdigest()
dispatch=manifest['world_events']['dispatch']
reset=int(manifest['world_events']['exports']['we_world_reset'],16)
hook=int(dispatch['world_reset_hook'],16)
CTOR=0x4206d0;CONTINUE=0x4206d7;STACK=0x13e0000
original=(ROOT/'SteelEmpire-v0120.exe').read_bytes();base=pefile.PE(data=original)
original_image=base.get_memory_mapped_image();current_image=pe.get_memory_mapped_image()
assert original_image[CTOR-0x400000:CONTINUE-0x400000]==bytes.fromhex('6aff6889d14500')
assert current_image[0x420ac0-0x400000:0x420ac8-0x400000]==original_image[0x420ac0-0x400000:0x420ac8-0x400000], 'Actor registration must not reset expedition state'
checks=1

md=Cs(CS_ARCH_X86,CS_MODE_32);md.skipdata=True
section=next(s for s in base.sections if s.Name.rstrip(b'\0')==b'.text')
callers=[a for a,size,mnemonic,operands in md.disasm_lite(section.get_data(),0x400000+section.VirtualAddress) if mnemonic=='call' and operands=='0x4206d0']
assert callers==[0x444a73,0x44ffb7],callers
checks+=1

REGS=(UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)
for flags in (0x202,0x246,0xa97):
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000);u.mem_write(0x400000,current_image);u.mem_map(0x1000000,0x400000)
 for i,reg in enumerate(REGS):u.reg_write(reg,0x123400+i)
 u.reg_write(UC_X86_REG_ECX,0x1000000)
 u.reg_write(UC_X86_REG_EFLAGS,flags);u.reg_write(UC_X86_REG_ESP,STACK)
 u.mem_write(STACK,struct.pack('<II',0x5ff000,0x46f49c))
 before={reg:u.reg_read(reg) for reg in REGS};called=[]
 def boundary(u,pc,size,data):
  if pc==reset:
   called.append(pc)
   for reg in REGS:u.reg_write(reg,0xdeadbeef)
   u.reg_write(UC_X86_REG_EFLAGS,0x202)
   sp=u.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',u.mem_read(sp,4))[0]
   u.reg_write(UC_X86_REG_ESP,sp+4);u.reg_write(UC_X86_REG_EIP,ret)
 u.hook_add(UC_HOOK_CODE,boundary)
 u.emu_start(CTOR,CONTINUE,count=10000)
 assert u.reg_read(UC_X86_REG_EIP)==CONTINUE and called==[reset]
 assert before=={reg:u.reg_read(reg) for reg in REGS}
 assert u.reg_read(UC_X86_REG_EFLAGS)&0x8d5==flags&0x8d5
 assert u.reg_read(UC_X86_REG_ESP)==STACK-8
 assert struct.unpack('<4I',u.mem_read(STACK-8,16))==(0x45d189,0xffffffff,0x5ff000,0x46f49c)
 checks+=1

# Failed native load must not allocate/reset or read any file/property state.
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000);u.mem_write(0x400000,current_image);u.mem_map(0x1000000,0x400000)
for address,value in ((0x476fe8,0x123456),(0x48c3d8,0x1000000),(0x460060,0x5fc000),(0x460100,0x5fc020)):
 u.mem_write(address,struct.pack('<I',value))
u.mem_write(0x1010000,b'\xcc'*512)
def forbidden(u,pc,size,data):
 assert pc not in (0x5fc000,0x5fc020,0x450452,0x4500e6),'Failed load touched live state'
u.hook_add(UC_HOOK_CODE,forbidden)
u.mem_write(STACK,struct.pack('<III',0x5ff000,0,0));u.reg_write(UC_X86_REG_ESP,STACK)
u.emu_start(int(manifest['world_events']['exports']['we_load_game'],16),0x5ff000,count=100000)
assert u.reg_read(UC_X86_REG_EIP)==0x5ff000 and u.reg_read(UC_X86_REG_ESP)==STACK+12
assert bytes(u.mem_read(0x1010000,512))==b'\xcc'*512;checks+=1

# Actual reset C export owns only its property and never dereferences freed World.
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000);u.mem_write(0x400000,current_image);u.mem_map(0x1000000,0x400000)
for address,value in ((0x476fe8,0x123456),(0x48c3d8,0xdeadbeef),(0x460060,0x5fc000),(0x460100,0x5fc020)):
 u.mem_write(address,struct.pack('<I',value))
apis={name:0x5fd000+i*32 for i,name in enumerate(('GetPropA','SetPropA','RemovePropA','PostMessageA','GetTickCount'))}
properties={'SteelEmpireRework.Expeditions.0130':0x1010000,'SteelEmpireRework.NoticeQueue.0113':0x1020000}
frees=[]
def number(u,address):return struct.unpack('<I',u.mem_read(address,4))[0]
def text(u,address):
 data=bytes(u.mem_read(address,100));return data.split(b'\0')[0].decode('ascii')
def answer(u,value,cleanup=0):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,number(u,sp));u.reg_write(UC_X86_REG_ESP,sp+4+cleanup)
def api_boundary(u,pc,size,data):
 sp=u.reg_read(UC_X86_REG_ESP)
 if pc==0x5fc000:answer(u,0x600000,4)
 elif pc==0x5fc020:answer(u,apis[text(u,number(u,sp+8))],8)
 elif pc==apis['RemovePropA']:
  assert number(u,sp+4)==0x123456;key=text(u,number(u,sp+8));assert key=='SteelEmpireRework.Expeditions.0130';answer(u,properties.pop(key,0),8)
 elif pc==0x4500e6:frees.append(number(u,sp+4));answer(u,0)
u.hook_add(UC_HOOK_CODE,api_boundary)
for _ in range(2):
 u.mem_write(STACK,struct.pack('<I',0x5ff000));u.reg_write(UC_X86_REG_ESP,STACK);u.emu_start(reset,0x5ff000,count=100000)
 assert u.reg_read(UC_X86_REG_EIP)==0x5ff000 and u.reg_read(UC_X86_REG_ESP)==STACK+4
 assert properties=={'SteelEmpireRework.NoticeQueue.0113':0x1020000} and frees==[0x1010000]
 assert number(u,0x48c3d8)==0xdeadbeef;checks+=1

report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),
 coverage=['Only initial/new-game World constructor direct callers','Actor-registration routine untouched','Actual patched constructor replays native SEH prologue and preserves all registers/flags/stack',
 'Actual failed-load C export performs no state/file/property operations','Actual reset C export removes only own property once and never reads freed World'],
 scoped_mocks=['Reset callback clobbered only for hook ABI cases; actual C reset executed separately','Windows property/module lookup and native heap-free APIs'],
 not_checked=['Hardware new-game UI flow'])
(ROOT/'test-expedition-reset-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PASS expedition World reset:',checks,'native constructor/registration/replay cases')
