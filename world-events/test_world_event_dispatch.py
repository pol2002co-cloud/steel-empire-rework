"""Execute both dispatcher hooks with the native instruction continuations."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/python-deps-v093'))
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
import world_event_dispatch as D

STOP=0x5ff000
STACK=0x13f0000
EXPORTS=dict(zip(('we_message','we_load_begin','we_load_end','we_window_close','we_load_game','we_save','we_world_reset'),
                 (0x5d0000,0x5d0010,0x5d0020,0x5d0030,0x5d0040,0x5d0050,0x5d0060)))
REGS=(UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)

def w(u,a,v): u.mem_write(a,struct.pack('<I',v))
def r(u,a): return struct.unpack('<I',u.mem_read(a,4))[0]
def ret(u,n=0):
    sp=u.reg_read(UC_X86_REG_ESP)
    u.reg_write(UC_X86_REG_EIP,r(u,sp))
    u.reg_write(UC_X86_REG_ESP,sp+4+n)

def fixture(result=123):
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    u.mem_map(0x400000,0x200000);u.mem_map(0x1000000,0x400000)
    ks=Ks(KS_ARCH_X86,KS_MODE_32)
    def asm(s,a=0):return bytes(ks.asm(s,a)[0])
    cursor=0x5e0000
    def put(b):
        nonlocal cursor
        p=cursor;u.mem_write(p,b);cursor=(p+len(b)+15)&~15;return p
    u.mem_write(D.WNDPROC,D.WND_BYTES)
    u.mem_write(D.LOAD,D.LOAD_BYTES)
    u.mem_write(D.SAVE,D.SAVE_BYTES)
    u.mem_write(D.WORLD_RESET,D.RESET_BYTES)
    def patch(p,b,new):
        assert bytes(u.mem_read(p,len(b)))==b
        assert len(new)==len(b)
        u.mem_write(p,new)
    m=D.emit(put,asm,lambda:cursor,patch,EXPORTS)
    calls=[]
    def boundary(u,pc,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if pc==EXPORTS['we_message']:
            calls.append(('message',*[r(u,sp+i) for i in (4,8,12,16)]))
            u.reg_write(UC_X86_REG_EAX,0x12345678);ret(u,16)
        elif pc==EXPORTS['we_window_close']:
            calls.append(('close',r(u,sp+4)))
            # Deliberately clobber even nonvolatile registers and flags. The
            # teardown hook promises complete preservation for native replay.
            for reg in REGS+(UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX):
                u.reg_write(reg,0xdeadbeef)
            u.reg_write(UC_X86_REG_EFLAGS,0x202);ret(u,4)
        elif pc==EXPORTS['we_load_begin']:
            calls.append(('begin',));ret(u)
        elif pc==0x401217:
            # Native entry displaced bytes already ran, reserving 16 bytes.
            calls.append(('original',r(u,sp+20),u.reg_read(UC_X86_REG_EAX)))
            u.reg_write(UC_X86_REG_EAX,result)
            u.reg_write(UC_X86_REG_ESP,sp+16);ret(u)
        elif pc==EXPORTS['we_load_end']:
            calls.append(('end',u.reg_read(UC_X86_REG_EAX)))
            u.reg_write(UC_X86_REG_EAX,0xbad);ret(u)
        elif pc==EXPORTS['we_load_game']:
            calls.append(('game',r(u,sp+4),r(u,sp+8)))
            u.reg_write(UC_X86_REG_EAX,0xbad2);ret(u,8)
        elif pc==EXPORTS['we_save']:
            calls.append(('save',r(u,sp+4)))
            u.reg_write(UC_X86_REG_EAX,result);ret(u,4)
        elif pc==0x401e07:
            calls.append(('forward',u.reg_read(UC_X86_REG_ECX),
                          u.reg_read(UC_X86_REG_EFLAGS)&0x8d5))
            u.reg_write(UC_X86_REG_EAX,77);ret(u,16)
    u.hook_add(UC_HOOK_CODE,boundary)
    for i,reg in enumerate(REGS):u.reg_write(reg,0x123400+i)
    return u,m,calls

def invoke(u,entry,args):
    w(u,STACK,STOP)
    for i,v in enumerate(args):w(u,STACK+4+4*i,v)
    before=[u.reg_read(reg) for reg in REGS]
    u.reg_write(UC_X86_REG_ESP,STACK)
    u.emu_start(entry,STOP,count=10000)
    assert u.reg_read(UC_X86_REG_EIP)==STOP
    assert before==[u.reg_read(reg) for reg in REGS]

class DispatchTests(unittest.TestCase):
    def test_custom_message_stdcall_and_return(self):
        u,m,c=fixture();invoke(u,D.WNDPROC,[99,D.MESSAGE,123,456])
        self.assertEqual(c,[('message',99,D.MESSAGE,123,456)])
        self.assertEqual(u.reg_read(UC_X86_REG_EAX),0x12345678)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP),STACK+20)

    def test_all_standard_messages_replay_native_comparison(self):
        for msg in (0,2,0x10,0x20,0x21,0x100,0x101,0xffff):
            with self.subTest(msg=msg):
                u,m,c=fixture();invoke(u,D.WNDPROC,[99,msg,123,456])
                self.assertEqual(c[0][:2],('forward',msg))
                # cmp ECX,20h: ZF iff equal, CF iff unsigned below.
                self.assertEqual(bool(c[0][2]&0x40),msg==0x20)
                self.assertEqual(bool(c[0][2]&1),msg<0x20)
                self.assertEqual(u.reg_read(UC_X86_REG_EAX),77)
                self.assertEqual(u.reg_read(UC_X86_REG_ESP),STACK+20)

    def test_destroy_cleanup_and_native_forward(self):
        u,m,c=fixture();invoke(u,D.WNDPROC,[0x12345,0x82,123,456])
        self.assertEqual(c[0],('close',0x12345))
        self.assertEqual(c[1][:2],('forward',0x82))
        self.assertEqual(u.reg_read(UC_X86_REG_ESP),STACK+20)

    def test_load_success_failure_and_argument_cdecl(self):
        for result in (0,1,0xffffffff,0x12345678):
            for slot in (0,1,9):
                with self.subTest(result=result,slot=slot):
                    u,m,c=fixture(result);invoke(u,D.LOAD,[slot])
                    self.assertEqual(c,[('begin',),('original',slot,slot),('game',slot,result),('end',result)])
                    self.assertEqual(u.reg_read(UC_X86_REG_EAX),result)
                    self.assertEqual(u.reg_read(UC_X86_REG_ESP),STACK+4)

    def test_save_cdecl_wrapper_keeps_slot_and_actual_result(self):
        for result in (0,1):
            for slot in (0,1,5):
                u,m,c=fixture(result);invoke(u,D.SAVE,[slot])
                self.assertEqual(c,[('save',slot)])
                self.assertEqual(u.reg_read(UC_X86_REG_EAX),result)
                self.assertEqual(u.reg_read(UC_X86_REG_ESP),STACK+4)

if __name__=='__main__':unittest.main()
