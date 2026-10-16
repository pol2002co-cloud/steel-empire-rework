from test_patch import *

FIND=int(manifest['minimap_find'],16)
DRAW=int(manifest['minimap_draw'],16)
MINI=0x1000000; WORLD=0x1010000; CITY=0x1020000; TOWN=0x1030000
PANEL=0x1040000; SURFACE=0x1050000; MOUSE=0x1060000
END=0x500000

def fixture(scroll=(0,0),city=(40,40)):
 u=setup();w(u,MINI,0x460a6c);w(u,MINI+0x28,WORLD);w(u,0x48c3d8,WORLD)
 w(u,MINI+0x3c,scroll[0]&0xffffffff);w(u,MINI+0x40,scroll[1]&0xffffffff)
 w(u,WORLD+0x23c,CITY);w(u,CITY+8,1);w(u,CITY+0x34,city[0]);w(u,CITY+0x38,city[1]);w(u,CITY+0x7c,TOWN)
 u.mem_write(TOWN+0x14,'포룸'.encode('cp949')+b'\0')
 return u

def find(u,x,y):
 sp=0x13f0000;w(u,sp,END);w(u,sp+4,x&0xffffffff);w(u,sp+8,y&0xffffffff)
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,MINI)
 regs=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
 for i,reg in enumerate(regs):u.reg_write(reg,0x123400+i)
 u.emu_start(FIND,END,count=20000)
 assert u.reg_read(UC_X86_REG_ESP)==sp+12
 assert all(u.reg_read(reg)==0x123400+i for i,reg in enumerate(regs))
 return u.reg_read(UC_X86_REG_EAX)

count=0
for scroll in [(0,0),(-24,-58),(-12,-30)]:
 u=fixture(scroll, (100,130));x=50+scroll[0];y=65+scroll[1]
 for dx in range(-6,7):
  for dy in range(-6,7):
   got=find(u,x+dx,y+dy)
   expected=TOWN+0x14 if 0<=x+dx<96 and 0<=y+dy<77 and dx*dx+dy*dy<=16 else 0
   assert got==expected,(scroll,dx,dy,hex(got));count+=1
u=fixture();w(u,WORLD+0x240,CITY+0x200);w(u,CITY+0x200+8,1);w(u,CITY+0x200+0x34,44);w(u,CITY+0x200+0x38,40);w(u,CITY+0x200+0x7c,TOWN+0x100)
u.mem_write(TOWN+0x114,b'Other\0');assert find(u,22,20)==TOWN+0x114
assert find(u,21,20)==TOWN+0x14 # deterministic nearest/tie
for pos in [(-1,20),(96,20),(20,-1),(20,77),(0x7fffffff,0)]:assert find(u,*pos)==0
for edit in [(CITY+8,0),(CITY+0x7c,0),(WORLD+0x23c,0),(MINI+0x28,0)]:
 u=fixture();w(u,*edit);assert find(u,20,20)==0
u=fixture((-24,-58),(40,40));assert find(u,0,0)==0 # off-screen city

def draw_test(x,y,capture=0,enabled=1,world=True,name='미디엄웨이브'):
 u=fixture();u.mem_write(TOWN+0x14,name.encode('cp949')+b'\0')
 w(u,PANEL+0x38,MINI);w(u,PANEL+0x14,SURFACE);w(u,PANEL+8,357);w(u,PANEL+0xc,640);w(u,PANEL+0x10,123)
 w(u,MINI+4,16);w(u,MINI+8,378);w(u,MINI+0xc,96);w(u,MINI+0x10,77);w(u,MINI+0x14,SURFACE+0x200)
 w(u,MINI+0x20,MINI+0x100);w(u,MINI+0x100,MINI+0x100)
 # Real hit-test uses rectangle getter and its surface check.
 w(u,SURFACE+0x80,0x91);w(u,0x487738,MOUSE);w(u,MOUSE+4,enabled)
 w(u,MOUSE+0x18,x);w(u,MOUSE+0x1c,y);w(u,0x4880e0,capture)
 if not world:w(u,0x48c3d8,0)
 events=[]
 def hook(u,a,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if a==0x413c20:events.append('children');ret(u)
  elif a in (0x403a70,0x403a90):events.append('lock' if a==0x403a70 else 'unlock');ret(u)
  elif a==0x403f90:
   vals=[r(u,sp+4+i*4) for i in range(6)];events.append(('box',vals));assert 0<=vals[0]<vals[2]<640 and 0<=vals[1]<vals[3]<123;ret(u,24)
  elif a==0x403bd0:
   vals=[r(u,sp+4+i*4) for i in range(3)];events.append(('text',vals));assert vals[2]==TOWN+0x14;assert r(u,SURFACE+0x80) in (0,0xd2);ret(u,12)
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_X86_REG_ESI,PANEL);u.reg_write(UC_X86_REG_ECX,PANEL)
 regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
 before=[u.reg_read(reg) for reg in regs];sp=u.reg_read(UC_X86_REG_ESP)
 world_before=bytes(u.mem_read(WORLD,0x1000));town_before=bytes(u.mem_read(TOWN,0x1000))
 u.emu_start(0x40a602,0x40a607,count=30000)
 assert u.reg_read(UC_X86_REG_ESP)==sp
 assert [u.reg_read(reg) for reg in regs]==before
 assert r(u,SURFACE+0x80)==0x91
 assert bytes(u.mem_read(WORLD,0x1000))==world_before and bytes(u.mem_read(TOWN,0x1000))==town_before
 return events

events=draw_test(36,398);assert len(events)==5,events
for args in [(200,398),(36,500),(36,398,1),(36,398,0,0),(36,398,0,1,False)]:assert draw_test(*args)==['children']
assert draw_test(36,398)[2][0]=='box' and draw_test(50,398)==['children']
print('PASS:',count,'hover distance/scroll cases; tooltip enter/leave, drag suppression, cursor bounds, registers and unchanged game state')
