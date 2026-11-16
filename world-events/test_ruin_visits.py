"""Real named-label resolver and observer wrapper against owned CMP files."""
from test_patch import *
import ruin_visits as R
import hashlib

CTX=0x1000000;DATA=0x1100000;NAME=0x1200000
CALLBACK=0x5ff100;END=0x5ff000
SOURCE=ROOT/'package/SteelEmpire.exe'
checks=0

def fixture(script,label,mode=4,busy=0):
    u=setup();cursor=[0x5e0000]
    # This unit emitter starts from stock bytes even on an integrated candidate.
    u.mem_write(R.ENTRY,R.PATCH_SITES[R.ENTRY])
    def put(data):
        at=cursor[0];u.mem_write(at,data);cursor[0]=(at+len(data)+15)&~15;return at
    def patch(at,old,new):
        assert bytes(u.mem_read(at,len(old)))==old
        assert len(old)==len(new);u.mem_write(at,new)
    meta=R.emit(put,asm,lambda:cursor[0],patch,dict(we_ruin_visit=CALLBACK))
    raw=(ROOT/'extracted/patch102.pak'/(script+'.cmp')).read_bytes()
    u.mem_write(DATA,raw);u.mem_write(NAME,label.encode('cp949')+b'\0')
    for offset,value in ((0,0x1002000),(0x1cc,DATA),(0x1d0,DATA),(0x1d4,DATA+32),(0x1d8,busy),(0x1e0,0x1003000)):w(u,CTX+offset,value)
    seen=[];native=[];flags=[]
    def boundary(u,pc,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if pc==CALLBACK:
            seen.append((r(u,sp+4),r(u,sp+8)))
            # Aggressively clobber volatile registers and flags at callback.
            for reg in (UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX):u.reg_write(reg,0xdeadbeef)
            u.reg_write(UC_X86_REG_EFLAGS,0x246);ret(u,8)
        elif pc==0x4498f5:flags.append(u.reg_read(UC_X86_REG_EFLAGS))
        elif pc==0x4498fa:assert u.reg_read(UC_X86_REG_EFLAGS)==flags[-1]
        elif pc==0x449910:
            native.append((u.reg_read(UC_X86_REG_ECX),r(u,sp+4),r(u,sp+8)))
            ret(u,8)
    u.hook_add(UC_HOOK_CODE,boundary)
    sp=0x13e0000;w(u,sp,END);w(u,sp+4,NAME);w(u,sp+8,mode)
    u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,CTX)
    before={reg:u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)}
    story=bytes(u.mem_read(0x48d398,400));script_before=bytes(u.mem_read(DATA,len(raw)))
    u.emu_start(0x4498d0,END,count=100000)
    assert u.reg_read(UC_X86_REG_EIP)==END and u.reg_read(UC_X86_REG_ESP)==sp+12
    assert before=={reg:u.reg_read(reg) for reg in before}
    assert story==bytes(u.mem_read(0x48d398,400)) and script_before==bytes(u.mem_read(DATA,len(raw)))
    return seen,native,raw

for index,(label,town) in enumerate(R.RUINS):
    script=('카푸아','펠라','케브','아시레마')[index]
    seen,native,raw=fixture(script,label)
    assert seen==[(CTX,index)] and len(native)==1
    assert native[0][0]==CTX and native[0][2]==4
    for mode in (0,1,2,3,5):
        seen,native,_=fixture(script,label,mode=mode)
        assert not seen and len(native)==1 and native[0][2]==mode;checks+=1
    seen,native,_=fixture(script,label,busy=DATA+100)
    assert not seen and len(native)==1;checks+=1
    seen,native,_=fixture(script,'mainFrame')
    assert not seen and len(native)==1;checks+=1
    seen,native,_=fixture(script,'없는 유적')
    assert not seen and not native;checks+=1
    checks+=1

# Same label in the wrong script cannot bypass the original name resolver.
for script,label in [('카푸아','펠라유적'),('펠라','케브유적'),('케브','고대유적'),('아시레마','카푸아유적')]:
    seen,native,_=fixture(script,label);assert not seen and not native;checks+=1

# Verify the real constructor/contact layouts used by the C visit validator.
PARENT=0x1000000;TOWN=0x1010000;CTX=0x1020000;OBJECT=0x1030000
ARMY=0x1040000;TARGET=0x1050000;ACTOR=0x1060000
u=setup();sp=0x13e0000;w(u,sp,END);w(u,sp+4,TOWN)
u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,PARENT)
def base_frame(u,pc,size,data):
    if pc==0x444e10:ret(u)
h=u.hook_add(UC_HOOK_CODE,base_frame)
u.emu_start(0x42e740,END,count=10000)
assert u.reg_read(UC_X86_REG_EIP)==END and u.reg_read(UC_X86_REG_ESP)==sp+8
assert r(u,PARENT)==0x462738 and r(u,PARENT+0x50)==TOWN
u.hook_del(h);checks+=1

w(u,sp,END);w(u,sp+4,PARENT);w(u,sp+8,OBJECT)
u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,CTX)
u.emu_start(0x449750,0x44977e,count=10000)
assert u.reg_read(UC_X86_REG_EIP)==0x44977e and r(u,CTX)==PARENT;checks+=1

u=setup();w(u,PARENT,0x461954);w(u,PARENT+0x54,CTX)
w(u,ACTOR+0x808,ARMY);w(u,TARGET+0x7c,OBJECT)
u.mem_write(OBJECT+0x14,'고대유적'.encode('cp949')+b'\0')
for register,value in ((UC_X86_REG_ESI,PARENT),(UC_X86_REG_EDI,ACTOR),
                       (UC_X86_REG_EBX,TARGET),(UC_X86_REG_ESP,sp)):
    u.reg_write(register,value)
u.emu_start(0x41b25e,0x4498d0,count=10000)
at=u.reg_read(UC_X86_REG_ESP)
assert r(u,CTX+0x1e0)==ARMY and u.reg_read(UC_X86_REG_ECX)==CTX
assert r(u,at+4)==OBJECT+0x14 and r(u,at+8)==4;checks+=1

print('PASS ruin visits:',checks,'native named-entry/ABI/puzzle-isolation cases; four real ruin labels')
(ROOT/'test-ruin-visits-report.json').write_text(json.dumps(dict(status='passed',cases=checks,
    engine_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),ruins=4,
    scoped_mocks=['Downstream449910 execution and new C notification callback; original449860/4498d0 name resolution and wrapper execute',
                  'City base444e10 only; real City constructor runs, ScriptContext prefix runs until resource formatting, World contact runs until named dispatch'],
    not_checked=['Hardware visual playtest','Annual ledger and reward UI are integrated by parent']),indent=2),encoding='utf8')
