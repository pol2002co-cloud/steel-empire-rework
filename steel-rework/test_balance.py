"""Execute patched x86 code and original creation/payout routines in Unicorn."""
from test_patch import *
import itertools
count=0
def instructor_test(level,specialty,facilities,unit):
 global count
 u=setup();building=0x1000000;town=0x1010000;captain=0x1020000;manager=0x1030000;records=0x1040000;output=0x1100000
 w(u,building+4,town);w(u,town+0xf4,captain if level is not None else 0)
 w(u,captain+0x38,unit if specialty else 0);w(u,captain+0x48,(level or 0)&0xffffffff)
 w(u,0x4880e8,manager);w(u,manager,13);w(u,manager+4,records)
 for ident in range(1,14):
  row=records+(ident-1)*0x4e4;w(u,row,ident);w(u,row+0x38,ident);w(u,row+0x48,1);w(u,row+0x50,100)
  for off in [0x54,0x58,0x60,0x64,0x68,0x6c,0x70]:w(u,row+off,40)
 sp=u.reg_read(UC_X86_REG_ESP);w(u,sp,0x5f0000);w(u,sp+4,unit);u.reg_write(UC_X86_REG_ECX,building)
 def hook(u,a,size,data):
  if a==0x437880:
   stack=u.reg_read(UC_X86_REG_ESP);kind=r(u,stack+4);u.reg_write(UC_X86_REG_EAX,0x1200000 if kind in facilities else 0);ret(u,8)
  elif a==0x450452:u.reg_write(UC_X86_REG_EAX,output);ret(u)
  elif a==0x45046d:u.reg_write(UC_X86_REG_EAX,17);ret(u)
  elif a==0x5f0000:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x431c20,0,count=100000)
 base=(1 if level is None else 6 if specialty else 3)+sum({16:3,24:1,3:1}[i] for i in facilities)
 expected=min(30,base+(max(0,min(level,82)-1)//3 if level is not None else 0))
 assert u.reg_read(UC_X86_REG_EAX)==output
 assert r(u,output+0x48)==expected,(level,specialty,facilities,unit,r(u,output+0x48),expected)
 assert r(u,output+0x58)==40+(expected-1)*(17%r(u,0x460c80+unit*24)+1)
 assert r(u,output+0x54)==r(u,output+0x58)
 assert u.reg_read(UC_X86_REG_ESP)==sp+8
 count+=1
for level,specialty,facilities,unit in itertools.product([None,-1,0,1,3,4,10,30,60,82,99,2147483647],[False,True],[[],[16,24,3]],range(1,14)):
 instructor_test(level,specialty,facilities,unit)

def poker_test(human_index,folded,missing):
 u=setup();table=0x1000000;players=[0x1010000+i*0x1000 for i in range(4)];human=players[human_index];pot=1300
 for i,p in enumerate(players):
  w(u,table+0x94+i*4,p if i not in missing else 0);w(u,p+8,0 if i==human_index and folded else 1);w(u,p+0x2c,2000)
 w(u,table+0xa4,human);w(u,table+0x44,pot);w(u,table+0x60,0)
 # Run the real settlement loop, with rank/presentation calls stubbed only.
 # Rank stub guarantees every NPC hand outranks the human.
 awarded=[]
 def hook(u,a,size,data):
  if a==0x44c4d0:u.reg_write(UC_X86_REG_EAX,1 if u.reg_read(UC_X86_REG_ECX)==human else 900000);ret(u)
  elif a==0x44c180:
   stack=u.reg_read(UC_X86_REG_ESP)
   if r(u,stack+4)==3:awarded.append(u.reg_read(UC_X86_REG_ECX))
   ret(u,8)
  elif a==0x44d0d0:ret(u,4)
  elif a in [0x44e158,0x44e185,0x44e18b]:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook)
 for i in range(4):
  u.reg_write(UC_X86_REG_ESI,table);u.reg_write(UC_X86_REG_EBP,0x13);u.reg_write(UC_X86_REG_ESP,0x13f0000)
  u.emu_start(0x44e0a8,0,count=10000)
 assert r(u,table+0xa8)==human
 assert awarded==[human],(human_index,folded,missing,awarded)
 assert r(u,human+0x2c)==2000+pot
 assert all(r(u,p+0x2c)==2000 for p in players if p!=human)
 assert r(u,table+0x44)==0
for human_index,folded in itertools.product(range(4),[False,True]):
 poker_test(human_index,folded,[])
 poker_test(human_index,folded,[(human_index+1)%4,(human_index+2)%4])
print(f'PASS: {count} instructor scenarios with original stat growth; 16 poker settlement scenarios with original payout; no duplicate pot payout')
