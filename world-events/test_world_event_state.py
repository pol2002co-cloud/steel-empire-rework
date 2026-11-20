"""Execute the emitted x86 state helpers without loading or changing a save."""
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/python-deps-v093'))
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
import world_event_state as S

image=bytearray()
ks=Ks(KS_ARCH_X86,KS_MODE_32)
def address():return 0x53b000+len(image)
def put(data):
    where=address();image.extend(data)
    image.extend(b'\x90'*((-len(image))%4))
    return where
def asm(source,where):return bytes(ks.asm(source,where)[0])
meta=S.emit(put,asm,address)['world_event_state']
calls=0
def word(u,where,value):u.mem_write(where,struct.pack('<I',value&0xffffffff))
def read(u,where):return struct.unpack('<I',u.mem_read(where,4))[0]
def fixture():
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000)
    u.mem_map(0x1000000,0x400000);u.mem_write(0x53b000,bytes(image))
    for i in range(100):word(u,0x48d398+i*4,0xabcd0000+i)
    u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:u.emu_stop() if a==0x13df000 else None)
    return u
def call(u,name,*args):
    global calls
    sp=0x13f0000;word(u,sp,0x13df000)
    for i,value in enumerate(args):word(u,sp+4+i*4,value)
    u.reg_write(UC_X86_REG_ESP,sp)
    registers=(UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)
    for i,reg in enumerate(registers):u.reg_write(reg,0xaabb0000+i)
    u.emu_start(int(meta[name],16),0,count=50000)
    assert u.reg_read(UC_X86_REG_EIP)==0x13df000,(name,'return')
    assert u.reg_read(UC_X86_REG_ESP)==sp+4+4*len(args),(name,'stdcall stack')
    for i,reg in enumerate(registers):assert u.reg_read(reg)==0xaabb0000+i,(name,'saved register',reg)
    calls+=1
    return u.reg_read(UC_X86_REG_EAX)
def control(ident,status=S.OFFER,stage=0,flags=0):
    return ident|(stage<<8)|(status<<16)|(flags<<24)
def bank(u):return bytes(u.mem_read(S.BASE,S.WORDS*4))
def guards(u):
    for i in list(range(31))+list(range(85,100)):
        assert read(u,0x48d398+i*4)==0xabcd0000+i,('outside bank',i)

u=fixture();before=bank(u)
for name,args in [('getslot',(0,)),('completed',(0,)),('count_completed',()),
                  ('can_offer',(0,1,0)),('setfield',(0,0,control(0))),
                  ('clear',(0,)),('finish',(0,90)),('reserve_battle',(0,)),
                  ('rng',()),('schedule',(100,))]:
    assert call(u,name,*args)==0
assert bank(u)==before;guards(u)
assert call(u,'init',65530)==1
assert read(u,S.BASE)==S.MAGIC and read(u,S.LAST_DAY)==65530
assert read(u,S.NEXT_OFFER)==65537
before=bank(u);call(u,'init',4);assert bank(u)==before
for slot in (3,4,0xffffffff):
    assert call(u,'getslot',slot)==0
    for field in range(8):assert call(u,'setfield',slot,field,17)==0
for slot in range(3):
    assert call(u,'getslot',slot)==S.CARDS+32*slot
    for field in (8,9,0xffffffff):
        assert call(u,'getfield',slot,field)==0
        assert call(u,'setfield',slot,field,17)==0
for value in (control(S.EVENT_COUNT),control(255),control(1,0),control(0,4),control(0,255)):
    assert call(u,'setfield',0,0,value)==0
for field in (1,2,3):assert call(u,'setfield',0,field,101)==0
assert call(u,'setfield',0,4,16)==0
for field,value in enumerate((control(0),40,73,40,9,65530,65550,0xffffffff)):
    assert call(u,'setfield',0,field,value)==1
    assert call(u,'getfield',0,field)==value
assert call(u,'can_offer',0,1,0)==0
assert call(u,'finish',0,60)==0  # An unaccepted offer cannot be completed.
assert call(u,'setfield',1,0,control(0))==0
assert call(u,'setfield',1,0,control(35))==1
assert call(u,'setfield',2,0,control(34))==1
assert call(u,'can_offer',1,1,0)==0 # Capacity, even for a different ID.
assert call(u,'clear',2)==1
assert call(u,'can_offer',1,1,0)==1
assert call(u,'setfield',0,0,control(0,S.ACCEPTED))==1
assert call(u,'finish',0,65536)==0
assert call(u,'finish',0,60)==1
assert bytes(u.mem_read(S.CARDS,32))==bytes(32)
assert call(u,'finish',0,60)==0
assert call(u,'completed',0)==1 and call(u,'count_completed')==1
assert call(u,'can_offer',0,0,0)==0 and call(u,'can_offer',0,1,0)==0
call(u,'tick',65589,2186)
assert call(u,'can_offer',0,1,0)==0
call(u,'tick',65590,2186)
assert call(u,'can_offer',0,1,0)==1 # Crosses the 16-bit day boundary.
assert call(u,'can_offer',0,0,0)==0
assert call(u,'setfield',1,0,control(35,S.PENDING_REWARD,4,S.GOLD_PAID|S.IRON_PAID))==1
assert call(u,'finish',1,90)==1
assert call(u,'completed',35)==1 and call(u,'count_completed')==2
call(u,'tick',200000,6666)
assert call(u,'can_offer',35,1,0)==1
for ident in (S.EVENT_COUNT,255,0xffffffff):
    assert call(u,'completed',ident)==0
    assert call(u,'can_offer',ident,1,0)==0

# Full-width delta and saturated16-bit remaining timers survive save/reload.
assert call(u,'setfield',0,0,control(7,S.ACCEPTED))==1
assert call(u,'finish',0,65535)==1
saved=bank(u);restored=fixture();restored.mem_write(S.BASE,saved)
call(restored,'init',200000);assert bank(restored)==saved
call(restored,'tick',265534,8851);assert call(restored,'can_offer',7,1,0)==0
call(restored,'tick',265535,8851);assert call(restored,'can_offer',7,1,0)==1
assert call(restored,'setfield',0,0,control(8,S.ACCEPTED))==1
assert call(restored,'finish',0,90)==1
call(restored,'tick',300000,10000);assert call(restored,'can_offer',8,1,0)==1
call(restored,'tick',299999,10000) # A clock rewind cannot underflow a timer.
assert call(restored,'can_offer',8,1,0)==1
assert call(restored,'setfield',0,0,control(8,S.ACCEPTED))==1
assert call(restored,'finish',0,90)==1
call(restored,'tick',299998,10000)
assert struct.unpack('<H',restored.mem_read(S.COOLDOWNS+16,2))[0]==90
call(restored,'tick',299999,10000)
assert struct.unpack('<H',restored.mem_read(S.COOLDOWNS+16,2))[0]==89

# Only one battle card, one accepted battle per month; declining is free.
assert call(u,'setfield',0,0,control(9,S.OFFER,0,S.BATTLE))==1
assert call(u,'can_offer',10,1,1)==0
assert call(u,'setfield',1,0,control(10,S.OFFER,0,S.BATTLE))==0
assert call(u,'reserve_battle',0)==0
assert read(u,S.BATTLES)==0
assert call(u,'setfield',0,0,control(9,S.ACCEPTED,0,S.BATTLE|S.COST_PAID))==1
assert call(u,'reserve_battle',0)==1 and call(u,'reserve_battle',0)==0
assert call(u,'finish',0,90)==1
assert call(u,'can_offer',10,1,1)==0
call(u,'tick',200001,6667);assert call(u,'can_offer',10,1,1)==1
assert call(u,'setfield',0,0,control(10,S.OFFER,0,S.BATTLE))==1
assert call(u,'clear',0)==1 and read(u,S.BATTLES)==0
assert call(u,'can_offer',11,1,1)==1
assert call(u,'schedule',200009)==1 and read(u,S.NEXT_OFFER)==200009

# Packed timers use exact neighboring halfwords, and all36 completion bits work.
for ident in range(36):
    assert call(u,'setfield',0,0,control(ident,S.ACCEPTED))==1
    assert call(u,'finish',0,ident+1)==1
    assert struct.unpack('<H',u.mem_read(S.COOLDOWNS+2*ident,2))[0]==ident+1
assert call(u,'count_completed')==36
assert read(u,S.DONE)==0xffffffff and read(u,S.DONE+4)==15
call(u,'tick',200002,6667)
assert [struct.unpack('<H',u.mem_read(S.COOLDOWNS+2*i,2))[0] for i in range(36)]==list(range(36))

# Reference LCG and deterministic restoration, without changing the global RNG.
seed=read(u,S.RNG)
for _ in range(100):
    seed=(seed*1664525+1013904223)&0xffffffff
    assert call(u,'rng')==seed
restored.mem_write(S.BASE,bank(u))
for _ in range(100):assert call(u,'rng')==call(restored,'rng')
guards(u);guards(restored)
maximum=fixture();call(maximum,'init',0xffffffff)
assert read(maximum,S.NEXT_OFFER)==0xffffffff
guards(maximum)
# New events use spare one-shot timers without moving old serialized cards.
for ident,timer in [(36,20),(37,22),(38,3),(39,4),(40,5)]:
 assert call(u,'setfield',0,0,control(ident,S.ACCEPTED))==1
 assert call(u,'finish',0,90)==1
 assert struct.unpack('<H',u.mem_read(S.COOLDOWNS+timer*2,2))[0]==90
 assert call(u,'can_offer',ident,90,0)==0
 assert call(u,'completed',ident)==1
 # Completing an old one-shot cannot erase the new contract cooldown.
 assert call(u,'setfield',0,0,control(timer,S.ACCEPTED))==1
 assert call(u,'finish',0,0)==1
 assert struct.unpack('<H',u.mem_read(S.COOLDOWNS+timer*2,2))[0]==90
assert call(u,'count_completed')==41
guards(u)
print('PASS: %d native event-state calls; stock-bank bounds, old-save init, capacity, duplicates, all41 bits, cooldown rollover/long gaps, battle limit, payment flags, save restoration, RNG, stdcall registers' % calls)
