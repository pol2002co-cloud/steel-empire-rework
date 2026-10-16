from test_patch import *

def casualty(kind,player):
 u=setup();town=0x1000000;army=0x1080000;char=0x1090000;head=0x10a0000;node=head+0x100
 w(u,town+4,player);w(u,town+0x50a4c,head);w(u,town+0x50a50,1)
 w(u,head,node);w(u,head+4,node);w(u,node,head);w(u,node+4,head);w(u,node+8,char)
 w(u,army+4,town);w(u,army+0x1c,2);w(u,army+0x60,char)
 w(u,char,19);w(u,char+8,kind);w(u,char+0x10,3);w(u,char+0x58,250)
 sp=u.reg_read(UC_X86_REG_ESP);w(u,sp,0x5f0000);w(u,sp+4,char);w(u,sp+8,army)
 u.reg_write(UC_X86_REG_ECX,town);freed=[]
 def hook(u,a,size,data):
  if a==0x4500e6:freed.append(r(u,u.reg_read(UC_X86_REG_ESP)+4));ret(u)
  elif a==0x5f0000:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x4380c0,0,count=10000)
 keep=kind==3 and player==1
 assert (char not in freed)==keep,(kind,player,freed)
 assert r(u,army+0x60)==0 and r(u,army+0x1c)==1
 if keep:
  assert r(u,char+4)==1 and r(u,char+0x10)==0 and r(u,town+0x50a50)==1 and r(u,head)==node
 assert u.reg_read(UC_X86_REG_ESP)==sp+12
for kind in [0,1,2,3]:
 for player in [1,2]:casualty(kind,player)

def clock_test(hour,tick):
 u=setup();world=0x1000000;view=0x1010000;town=0x1020000;head=0x1090000
 w(u,world+0xa8,view);w(u,view+0x7c,town);w(u,town+4,1);w(u,town+0x50a4c,head)
 chars=[]
 for i,(kind,status) in enumerate([(3,1),(1,1),(3,0),(3,2)]):
  c=0x1100000+i*0x1000;n=head+0x100+i*0x20;chars.append(c)
  w(u,n,head if i==3 else n+0x20);w(u,n+8,c);w(u,c+8,kind);w(u,c+4,status);w(u,c+0x58,250);w(u,c+0x54,7)
 w(u,head,head+0x100);w(u,0x48d388,hour);w(u,0x48d384,10);w(u,0x48d38c,tick)
 u.reg_write(UC_X86_REG_EBX,world);u.reg_write(UC_X86_REG_ECX,0x48d380)
 sp=u.reg_read(UC_X86_REG_ESP)
 u.emu_start(0x421ea1,0x421ea6,count=10000)
 changed=(tick==9 and hour%24==23)
 assert r(u,chars[0]+4)==(0 if changed else 1)
 assert r(u,chars[0]+0x54)==(250 if changed else 7)
 for c,status in zip(chars[1:],[1,0,2]):assert r(u,c+4)==status and r(u,c+0x54)==7
 assert r(u,0x48d388)==hour+(tick==9) and u.reg_read(UC_X86_REG_ESP)==sp
for hour in [0,22,23,24,719,743,8639]:
 for tick in [0,8,9]:clock_test(hour,tick)

for typ in [0,1,2,3]:
 for flags in range(16):
  u=setup();town=0x1000000;army=0x1010000;w(u,town+0x10,flags);w(u,army+0x18,typ)
  sp=u.reg_read(UC_X86_REG_ESP);w(u,sp,0x5f0000);w(u,sp+4,army);u.reg_write(UC_X86_REG_ECX,town)
  u.emu_start(0x4381a0,0x5f0000,count=100)
  assert u.reg_read(UC_X86_REG_EAX)==int(typ==2 or bool(flags&4))
  assert u.reg_read(UC_X86_REG_ESP)==sp+8
print('PASS: 8 full casualty cleanup cases, 21 real clock transitions, 64 landing checks')
