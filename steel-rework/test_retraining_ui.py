from test_patch import *

# Execute the entire retraining UI initializer, including its cloned base
# initializer and real refresh loop. Only external widgets/resources are stubbed.
for count in [0,1,5,6]:
 for occupied in [False,True]:
  u=setup();u.mem_map(0,0x1000)
  ui=0x1000000;town=0x1010000;fac=0x1080000;head=0x1090000
  w(u,ui+0x90,town);w(u,ui+0x94,fac);w(u,fac+0x38,count)
  w(u,town+0x50a4c,head);w(u,town+0x50a58,head);w(u,head,head)
  for i in range(6):
   slot=fac+0x250+i*0x4f8
   u.mem_write(slot+0x28,('Class%d'%i).encode()+b'\0')
   if occupied:
    w(u,slot,1);w(u,slot+0x4f4,0x10b0000+i*0x100)
  trace=[];nextptr=[0x1100000];widgets=set();labels=[];positions=[]
  def hook(u,a,size,data):
   assert 0x400000<=a<0x600000,('escaped code',hex(a),[hex(x) for x in trace[-15:]])
   trace.append(a)
   sp=u.reg_read(UC_X86_REG_ESP);this=u.reg_read(UC_X86_REG_ECX)
   if a==0x450452:
    p=nextptr[0];nextptr[0]+=0x400;u.reg_write(UC_X86_REG_EAX,p);ret(u)
   elif a==0x4500e6:ret(u)
   elif a in [0x426700,0x426610]:u.reg_write(UC_X86_REG_EAX,1);ret(u,4 if a==0x426610 else 0)
   elif a in [0x40e4b0,0x402400,0x410380]:ret(u)
   elif a==0x413d50:u.reg_write(UC_X86_REG_EAX,0);ret(u,4)
   elif a in [0x40ee50,0x40e800]:
    p=r(u,sp+4);positions.append((r(u,p+0x10),r(u,p+0x18)))
    widgets.add(this);u.reg_write(UC_X86_REG_EAX,this);ret(u,4)
   elif a==0x40fd70:widgets.add(this);u.reg_write(UC_X86_REG_EAX,this);ret(u,32)
   elif a==0x40f770:widgets.add(this);u.reg_write(UC_X86_REG_EAX,this);ret(u,4)
   elif a in [0x40e950,0x40e760,0x40f790]:
    assert this in widgets,(hex(a),hex(this));ret(u,12 if a==0x40f790 else 4)
   elif a==0x4100f0:assert this in widgets;ret(u,4)
   elif a==0x410140:u.reg_write(UC_X86_REG_EAX,0);ret(u)
   elif a==0x40e790:
    assert this in widgets,('invalid label',hex(this))
    labels.append(this) # Run the actual string copy/free routine.
  u.hook_add(UC_HOOK_CODE,hook)
  sp=u.reg_read(UC_X86_REG_ESP);w(u,sp,0x5f0000);u.reg_write(UC_X86_REG_ECX,ui)
  u.emu_start(0x4230e0,0x5f0000,count=100000)
  assert u.reg_read(UC_X86_REG_EIP)==0x5f0000,hex(u.reg_read(UC_X86_REG_EIP))
  assert u.reg_read(UC_X86_REG_ESP)==sp+4
  assert r(u,ui+0x90)==town and r(u,ui+0x94)==fac
  for offset in [0x48,0x60,0x78,0x98]:
   assert all(r(u,ui+offset+i*4) in widgets for i in range(6)),hex(offset)
  assert len(labels)==2+count,(count,len(labels))
  assert len({r(u,ui+offset+i*4) for offset in [0x48,0x60,0x78,0x98] for i in range(6)})==24
print('PASS: 8 complete retraining UI initialization/refresh cases; six distinct columns; empty and occupied slots; actual label string copy; owner pointers and stack preserved')



