"""Real stock XP/growth/RNG execution; only CRT thread-local lookup is mocked."""
from pathlib import Path
import json
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/python-deps-v093'))
import pefile
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
import world_tour_actions as T

ROOT=Path(__file__).resolve().parent
ARMY,CAPTAIN,PEOPLE,THREAD=0x1000000,0x1010000,0x1020000,0x1040000
STACK,STOP=0x13f0000,0x13df000
pe=pefile.PE(str(ROOT/'package/SteelEmpire.exe'))
native=bytes(pe.get_memory_mapped_image())
ks=Ks(KS_ARCH_X86,KS_MODE_32);cursor=0x5e0000;helpers=[]
def asm(source,address):return bytes(ks.asm(source,address)[0])
def put(data):
    global cursor
    result=cursor;helpers.append((result,data));cursor=(cursor+len(data)+15)&~15;return result
metadata=T.emit(put,asm,lambda:cursor)['world_tour_actions']
if '--integrated' in sys.argv:
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    metadata=manifest['world_events']['tour_actions'];helpers=[]
PERFORM=int(metadata['perform'],16)
checks=0
def write(u,address,value):u.mem_write(address,struct.pack('<I',value&0xffffffff))
def read(u,address):return struct.unpack('<I',u.mem_read(address,4))[0]
def fixture():
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000);u.mem_write(0x400000,native)
    for address,data in helpers:u.mem_write(address,data)
    u.mem_map(0x1000000,0x400000)
    for address,value in ((ARMY,1),(ARMY+0x18,3),(ARMY+0x1c,1),(ARMY+0x34,CAPTAIN),
                          (CAPTAIN+0x54,100),(CAPTAIN+0x58,100),(0x4880e8,0x1041000),
                          (THREAD+0x14,0xabcdef01),(0x46e5d8,123456)):
        write(u,address,value)
    u.calls=[];u.writes=[]
    def hook(u,address,size,data):
        if address==STOP:u.emu_stop()
        elif address==0x45290b:
            u.calls.append('thread');sp=u.reg_read(UC_X86_REG_ESP)
            u.reg_write(UC_X86_REG_EAX,THREAD);u.reg_write(UC_X86_REG_EIP,read(u,sp));u.reg_write(UC_X86_REG_ESP,sp+4)
        elif address in (0x414fc0,0x415010,0x45046d):u.calls.append(address)
    u.hook_add(UC_HOOK_CODE,hook)
    u.hook_add(UC_HOOK_MEM_WRITE,lambda u,a,address,size,value,data:u.writes.append((address,size)))
    return u
def dancer(u,index,level=20,xp=0,status=0,hp=100,klass=13,slot=None):
    person=PEOPLE+index*0x200
    for offset,value in ((4,status),(8,1),(0x38,klass),(0x48,level),(0x4c,xp),
                         (0x50,100),(0x54,hp),(0x58,100),(0x60,50),(0x64,40),
                         (0x68,30),(0x6c,30),(0x70,20)):
        write(u,person+offset,value)
    write(u,ARMY+0x60+(index if slot is None else slot)*4,person)
    return person
def perform(u,seed=0,army=ARMY):
    global checks
    before=bytes(u.mem_read(ARMY,0x1000));cash=read(u,0x46e5d8);rng=read(u,THREAD+0x14)
    write(u,STACK,STOP);write(u,STACK+4,army);write(u,STACK+8,seed)
    u.reg_write(UC_X86_REG_ESP,STACK)
    preserved=(UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)
    for i,reg in enumerate(preserved):u.reg_write(reg,0xaabb0000+i)
    u.writes.clear();u.emu_start(PERFORM,0,count=300000)
    assert u.reg_read(UC_X86_REG_EIP)==STOP
    assert u.reg_read(UC_X86_REG_ESP)==STACK+12
    assert all(u.reg_read(reg)==0xaabb0000+i for i,reg in enumerate(preserved))
    assert bytes(u.mem_read(ARMY,0x1000))==before
    assert read(u,0x46e5d8)==cash and read(u,THREAD+0x14)==rng
    assert not any(0x48d398<=a<0x48d398+400 for a,n in u.writes)
    checks+=1
    return u.reg_read(UC_X86_REG_EAX)

# Exact original XP/growth entry, original class table and original rand execute.
for seed in range(20):
    u=fixture();person=dancer(u,0,20,98)
    assert perform(u,seed)==4800
    gain=2+2*seed
    assert read(u,person+0x48)==20+(98+gain)//100
    assert read(u,person+0x4c)==(98+gain)%100
    assert u.calls.count(0x414fc0)==1 and u.calls.count(0x415010)==1
    assert u.calls.count(0x45046d)==5
    assert read(u,person+0x58)>100 and read(u,person+0x54)==read(u,person+0x58)
    before=bytes(u.mem_read(person,0xa8));other=fixture();p=dancer(other,0,20,98)
    assert perform(other,seed)==4800 and bytes(other.mem_read(p,0xa8))==before

for level,xp,expected_level,expected_xp in ((98,90,99,100),(99,0,99,100),(99,99,99,100)):
    u=fixture();person=dancer(u,0,level,xp)
    assert perform(u,19)==800+200*level
    assert read(u,person+0x48)==expected_level and read(u,person+0x4c)==expected_xp
    assert u.calls.count(0x45046d)==(5 if level==98 else 0)

# Pointer duplication including the commander alias never doubles income/XP.
u=fixture();person=dancer(u,0,10,0)
write(u,ARMY+0x34,person)
for slot in (1,2,39,80):write(u,ARMY+0x60+slot*4,person)
assert perform(u,9)==2800 and read(u,person+0x4c)==20
assert u.calls.count(0x414fc0)==1

u=fixture();person=dancer(u,0,1,0,slot=80)
write(u,person+8,3) # Named companions and generic dancers share the real class.
assert perform(u,0xffffffff)==1000
assert read(u,person+0x4c)==2+2*(0xffffffff%20)

# Eight eligible unique dancers are paid; extra, dead and invalid people stay intact.
u=fixture();people=[dancer(u,i,10+i,0) for i in range(10)]
before=[bytes(u.mem_read(p,0xa8)) for p in people]
assert perform(u,0)==sum(800+200*(10+i) for i in range(8))
assert u.calls.count(0x414fc0)==8
for i,p in enumerate(people):
    assert read(u,p+0x4c)==(2 if i<8 else 0)
    if i>=8:assert bytes(u.mem_read(p,0xa8))==before[i]

for offset,value in ((0,2),(0x18,0),(0x18,1),(0x18,2),(0x1c,0),(0x34,0)):
    u=fixture();person=dancer(u,0);write(u,ARMY+offset,value);before=bytes(u.mem_read(person,0xa8))
    assert perform(u)==0 and not u.calls
    assert bytes(u.mem_read(person,0xa8))==before
for offset,value in ((4,1),(0x54,0),(0x54,0xffffffff)):
    u=fixture();dancer(u,0);write(u,CAPTAIN+offset,value)
    assert perform(u)==0 and not u.calls
u=fixture();assert perform(u,army=0)==0 and not u.calls
u=fixture();assert perform(u)==0 and not u.calls
for offset,value in ((4,1),(0x54,0),(0x38,12),(0x48,0),(0x48,100),
                     (0x4c,0xffffffff),(0x4c,0x7ffffff0),(0x50,0),(0x50,0x80000000)):
    u=fixture();person=dancer(u,0);write(u,person+offset,value);before=bytes(u.mem_read(person,0xa8))
    assert perform(u)==0 and not u.calls
    assert bytes(u.mem_read(person,0xa8))==before

# Dead dancers do not consume the cap; all eight living level99 performers count.
u=fixture();dead=dancer(u,0,50,0,hp=0)
live=[dancer(u,i,99,0) for i in range(1,9)]
assert perform(u,19)==8*20600
assert all(read(u,p+0x4c)==100 and read(u,p+0x48)==99 for p in live)
assert not u.calls.count(0x45046d) and read(u,dead+0x4c)==0
print('PASS tour actions:',checks,'native performances; real XP/growth/level99/RNG, 81 slots, unique8 cap, heroes/generics, invalid/dead guards, deterministic seed, cash/position/story RNG preserved, stdcall registers')
