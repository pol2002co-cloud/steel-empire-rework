from test_patch import *
import random

def scenario(levels,base,dead=(),vehicles=()):
 u=setup();battle=0x1000000;sp=u.reg_read(UC_X86_REG_ESP);people=[];units=[]
 for i,level in enumerate(levels):
  p=0x1100000+i*0x1000;c=p+0x400;m=p+0x800
  units.append(p);w(u,battle+0x228+i*4,p);w(u,p+4,battle);w(u,p+0x138,int(i not in dead))
  if i in vehicles:
   w(u,p+0x150,1);w(u,p+0x15c,m);w(u,m+0x8c,c)
   lv=level if isinstance(level,tuple) else (level,)
   if len(lv)>1:w(u,m+0x90,c+0x100)
   for j,l in enumerate(lv):w(u,c+j*0x100+0x48,l);people.append((i,c+j*0x100,l))
  else:w(u,p+0x15c,c);w(u,c+0x48,level);people.append((i,c,level))
  # One enemy credited per friendly; kill bonus 1, 2 or 3.
  e=0x1200000+i*0x400;w(u,battle+0x36c+i*4,e);w(u,e+0xf4,p);w(u,e+0x150,i%3)
 w(u,sp+0x24,base);u.reg_write(UC_X86_REG_EBP,battle)
 u.emu_start(0x43a472,0x43a478,count=100000)
 assert u.reg_read(UC_X86_REG_ESP)==sp
 donors=[x for x in people if x[0] not in dead and x[2]>=99]
 eligible=[x for x in people if x[0] not in dead and x[2]<99]
 pool=sum(base+i%3+1 for i,c,l in donors)
 q,rem=divmod(pool,len(eligible)) if eligible else (0,0)
 assert (r(u,battle+0xe4c),r(u,battle+0xe50))==(q,rem),(levels,base,pool,q,rem,r(u,battle+0xe4c))
 extras=[];paid=0
 for i,c,l in people:
  if i in dead:continue
  raw=base+i%3+1;w(u,c+0x4c,7)
  u.reg_write(UC_X86_REG_ESI,units[i]);u.reg_write(UC_X86_REG_EAX,c);u.reg_write(UC_X86_REG_EBX,raw)
  if i not in vehicles:
   w(u,sp+0x34,raw);u.emu_start(0x43e8de,0x43e8ec,count=1000);u.reg_write(UC_X86_REG_ESP,sp)
  elif c==units[i]+0x400:u.emu_start(0x43fd96,0x43fd9e,count=1000)
  else:u.emu_start(0x43fd68,0x43fd70,count=1000)
  gained=r(u,c+0x4c)-7;paid+=gained
  assert gained==0 if l>=99 else gained>=raw
  if l<99:extras.append(gained-raw)
 if eligible:
  assert sum(extras)==pool and max(extras)-min(extras)<=1
  assert paid==sum(base+i%3+1 for i,c,l in people if i not in dead)
 else:assert paid==0
 assert r(u,battle+0xe50)==0

for base in [5,200,201,10000]:
 for levels in [[99,98,1],[99,99,99],[1,50,98],[99],[98],[99,99,1,2,3,4]]:
  scenario(levels,base);scenario(levels,base,dead=(0,))
 scenario([(99,50),(98,99),99,1],base,vehicles=(0,1))
 scenario([(99,99),(99,),99],base,vehicles=(0,1))
 scenario([99]*80+[1],base)
print('PASS: 60 XP pooling cases; infantry and mixed-level vehicle crew; dead exclusion; all/no capped units; maximum army; kill bonus included; integer remainder conserved through actual award hooks')
