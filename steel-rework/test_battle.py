from test_patch import *

def fixture():
 u=setup();b=0x1000000;ally=0x1010000;enemy=0x1020000
 w(u,b+0x200,ally);w(u,b+0x204,enemy);w(u,ally+0x138,1)
 w(u,b+0x1e0,1);w(u,b+0x1e4,3);w(u,b+0xe4c,0xfeedabcd)
 u.reg_write(UC_X86_REG_ESI,b);u.reg_write(UC_X86_REG_EBP,0)
 units=[]
 for i in range(81):
  p=0x1100000+i*0x400;units.append(p);w(u,b+0x36c+i*4,p);w(u,p+0x138,1);w(u,p+0x54,100);w(u,p+0x13c,1)
 # Commander is also present on its side's board, as in the actual game.
 w(u,b+0x36c,enemy)
 return u,b,ally,enemy,units

def frame(u):
 sp=u.reg_read(UC_X86_REG_ESP)
 u.emu_start(0x43c62c,0x43c65f,count=20000)
 assert u.reg_read(UC_X86_REG_ESP)==sp
 assert u.reg_read(UC_X86_REG_EBX)==5

for death_turn in [1,2,3,10]:
 for cap in [0,3,20]:
  u,b,a,e,units=fixture();w(u,b+0x1e0,death_turn);w(u,b+0x1e4,cap)
  # Repeat frames within each turn; deadline must not move or count frames.
  for turn in range(death_turn,death_turn+4):
   w(u,b+0x1e0,turn)
   for _ in range(4):frame(u)
   assert r(u,b+0xe48)==death_turn+3
   assert r(u,b+0x1d8)==(6 if turn==death_turn+3 else 0)
   for p in units[1:]:
    assert r(u,p+0x138)==(0 if turn==death_turn+3 else 1)
    assert r(u,p+0x54)==(0 if turn==death_turn+3 else 100)
   assert r(u,a+0x138)==1 and r(u,b+0xe4c)==0xfeedabcd
  assert r(u,b+0x1e4)==(max(cap,death_turn+3) if cap else 0)

u,b,a,e,units=fixture();w(u,e+0x138,1);frame(u)
assert r(u,b+0xe48)==0 and r(u,b+0x1d8)==0
u,b,a,e,units=fixture();frame(u)
for p in units:w(u,p+0x138,0)
frame(u);assert r(u,b+0x1d8)==6  # Finish early if player killed survivors.
u,b,a,e,units=fixture();w(u,a+0x138,0);frame(u)
assert r(u,b+0x1d8)==6 and r(u,units[1]+0x138)==1 # Original defeat.
u,b,a,e,units=fixture();w(u,b+0x1d8,5);frame(u)
assert r(u,b+0xe48)==0 and r(u,units[1]+0x138)==1 # Manual settlement unchanged.
u,b,a,e,units=fixture();w(u,b+0xe48,99)
u.emu_start(0x43941d,0x439423,count=100)
assert r(u,b+0xe48)==0 and r(u,b+0xe4c)==0xfeedabcd

# Check collapsed generic infantry follows the actual original death branch,
# not the survivor branch, when battle settlement sends event 0x7e6.
u=setup();unit=0x1000000;char=0x1010000;army=0x1020000;town=0x1030000
w(u,unit+0x15c,char);w(u,unit+8,army);w(u,char+8,1);w(u,army+4,town)
u.reg_write(UC_X86_REG_ESI,unit);sp=u.reg_read(UC_X86_REG_ESP);w(u,sp+0x34,0)
u.emu_start(0x43e9b7,0x43ea50,count=100)
assert u.reg_read(UC_X86_REG_ECX)==town
assert r(u,u.reg_read(UC_X86_REG_ESP))==char
print('PASS: 192 battle frames, 12 deadline/cap cases, early victory, original defeat/retreat, constructor reset, actual generic casualty dispatch')
