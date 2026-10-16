from test_patch import *

END=0x5f0000; FAC=0x1000000; MAN=0x1010000; RECORDS=0x1020000; CHAR=0x1100000; TARGET=0x1110000
def call(u,pc,this,*args):
 sp=0x13e0000;w(u,sp,END)
 for i,v in enumerate(args):w(u,sp+4+i*4,v)
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,this)
 u.emu_start(pc,END,count=1000000)
 assert u.reg_read(UC_X86_REG_EIP)==END,hex(u.reg_read(UC_X86_REG_EIP))
 assert u.reg_read(UC_X86_REG_ESP)==sp+4+len(args)*4
 return u.reg_read(UC_X86_REG_EAX)
def fixture():
 u=setup();w(u,0x4880e8,MAN);w(u,MAN,13);w(u,MAN+4,RECORDS)
 for i in range(1,14):
  p=RECORDS+(i-1)*0x4e4
  for o,v in [(0,i),(8,1),(0x38,i),(0x48,1),(0x58,50),(0x5c,30),(0x50,100),(0x94,45),(0x98,30),(0x9c,10000),(0xa0,25)]:w(u,p+o,v)
 return u

for level in [1,14,15,30,99]:
 u=fixture();call(u,0x4152a0,MAN,7,TARGET)
 assert [r(u,TARGET+o) for o in [0x58,0x5c,0x60,0x64,0x68,0x70]]==[0,20,0,0,0,0]
 assert [r(u,TARGET+o) for o in [0x94,0x98,0x9c,0xa0]]==[25,15,5000,20]
 for o,v in [(0,6),(8,1),(0x38,6),(0x48,level),(0x58,250),(0x5c,75),(0x60,40),(0x64,20),(0x70,30)]:w(u,CHAR+o,v)
 assert bool(call(u,0x4151a0,MAN,CHAR,TARGET))==(level>=15)
 call(u,0x4151e0,MAN,CHAR,TARGET)
 assert r(u,CHAR+0x38)==(7 if level>=15 else 6)
 assert r(u,CHAR+0x5c)==(95 if level>=15 else 75)
 assert r(u,CHAR+0x58)==250
u=fixture()
for i in range(2,7):call(u,0x4320e0,FAC,i)
assert r(u,FAC+0x38)==6
assert [r(u,FAC+0x260+i*0x4f8) for i in range(6)]==list(range(2,8))
before=bytes(u.mem_read(FAC,0x2020));call(u,0x4320e0,FAC,6);assert bytes(u.mem_read(FAC,0x2020))==before

# Execute the game's serializers with file I/O intercepted as an in-memory
# stream. This catches byte alignment/slot-count bugs across old and new saves.
def serialize(u,legacy=False):
 stream=bytearray()
 def io(u,a,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if a==0x4311d0:ret(u,4)
  elif a==0x4502c9:
   stream.extend(u.mem_read(r(u,sp+4),r(u,sp+8)*r(u,sp+12)));u.reg_write(UC_X86_REG_EAX,1);ret(u)
 h=u.hook_add(UC_HOOK_CODE,io)
 if legacy:
  # A genuine original five-slot writer, independent of the patched writer.
  u.mem_write(0x431eff,asm('mov ebp,5',0x431eff))
 call(u,0x431ee0,FAC,0x1234);u.hook_del(h)
 return stream
def deserialize(stream,count):
 u=fixture();w(u,FAC+0x38,count);pos=0
 def io(u,a,size,data):
  nonlocal pos
  sp=u.reg_read(UC_X86_REG_ESP)
  if a==0x431340:ret(u,8)
  elif a==0x436ee0:u.reg_write(UC_X86_REG_EAX,CHAR);ret(u,4)
  elif a==0x45016e:
   n=r(u,sp+8)*r(u,sp+12);assert pos+n<=len(stream)
   u.mem_write(r(u,sp+4),bytes(stream[pos:pos+n]));pos+=n;u.reg_write(UC_X86_REG_EAX,1);ret(u)
 h=u.hook_add(UC_HOOK_CODE,io);call(u,0x431fa0,FAC,0x1234,0);u.hook_del(h)
 assert pos==len(stream)
 return u
new=serialize(u);assert len(new)==6*0x4f4
loaded=deserialize(new,6);assert r(loaded,FAC+0x38)==6
assert r(loaded,FAC+0x260+5*0x4f8)==7 and r(loaded,FAC+0x260+5*0x4f8+0x5c)==20
w(u,FAC+0x38,5);old=serialize(u,True);assert len(old)==5*0x4f4
loaded=deserialize(old,5);assert r(loaded,FAC+0x38)==6 and r(loaded,FAC+0x260+5*0x4f8)==7
# An actual pending named trainee in slot six must survive the variable-length
# character record appended by the original serializer.
u=fixture()
for i in range(2,7):call(u,0x4320e0,FAC,i)
slot=FAC+0x250+5*0x4f8
w(u,slot,1);w(u,slot+8,9);w(u,slot+0x4f4,CHAR)
for o,v in [(0,80),(4,2),(8,3),(0x38,6),(0x48,30),(0x58,200)]:w(u,CHAR+o,v)
stream=serialize(u);assert len(stream)==6*0x4f4+0xa8
loaded=deserialize(stream,6);assert r(loaded,slot)==1 and r(loaded,slot+8)==9 and r(loaded,slot+0x4f4)==CHAR
# No armored-infantry research: loading must not grant the technology.
u=fixture();call(u,0x4320e0,FAC,2);stream=serialize(u)
loaded=deserialize(stream,1);assert r(loaded,FAC+0x38)==1

def airport(key,types,capture=0):
 u=setup();city=0x1000000;town=0x1010000;keyboard=0x1080000;controller=0x1090000;dialog=0x10a0000;opened=[]
 w(u,city+0x50,town);w(u,0x487f3c,keyboard);w(u,keyboard+0x404+0x41*4,key);w(u,0x4880e0,capture);w(u,0x48cc1c,controller)
 for i,typ in enumerate(types):
  army=0x10b0000+i*0x100;w(u,town+0x50654+i*4,army);w(u,army+0x18,typ)
 def hook(u,a,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if a==0x450452:assert r(u,sp+4)==0x68;u.reg_write(UC_X86_REG_EAX,dialog);ret(u)
  elif a==0x423820:assert r(u,sp+4)==town;u.reg_write(UC_X86_REG_EAX,dialog);ret(u,4)
  elif a==0x4438f0:assert r(u,sp+4)==dialog;opened.append(True);ret(u,4)
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_X86_REG_EBX,city)
 sp=u.reg_read(UC_X86_REG_ESP);u.emu_start(0x42ed13,0x42ed19,count=20000)
 assert u.reg_read(UC_X86_REG_ESP)==sp
 return bool(opened)
for key,types,capture,expected in [(1,[2],0,True),(1,[0,1,2],0,True),(0,[2],0,False),(1,[],0,False),(1,[1],0,False),(1,[2],1,False)]:assert airport(key,types,capture)==expected

# Item shop uses item ID at node+8, unlike vehicle IDs at node+12.
for existing in [[],[54,55,56],[54,55,56,57,58,59,60]]:
 u=setup();owner=0x1000000;shop=0x1001000;head=0x1002000;nodes=0x1003000;added=[]
 w(u,owner+4,shop);w(u,shop,0x4622c8);w(u,shop+0x5c,head)
 def setlist(ids):
  w(u,head,nodes if ids else head)
  for j,ident in enumerate(ids):w(u,nodes+j*0x200,nodes+(j+1)*0x200 if j+1<len(ids) else head);w(u,nodes+j*0x200+8,ident)
 setlist(existing)
 items=(ROOT/'extracted/Data.pak/item.dat').read_bytes()
 names={items[4+(i-1)*288:4+(i-1)*288+32].split(b'\0')[0]:i for i in range(54,61)}
 def hook(u,a,size,data):
  if a==0x429480:
   ptr=r(u,u.reg_read(UC_X86_REG_ESP)+4);ident=names[bytes(u.mem_read(ptr,32)).split(b'\0')[0]];added.append(ident);setlist(existing+added);ret(u,4)
  elif a==0x450452:ret(u)
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_X86_REG_ESI,owner);u.emu_start(0x44bc18,0x44bc1f,count=30000)
 assert added==[i for i in range(54,61) if i not in existing]
pak=(ROOT/'package/patch104.pak').read_bytes()
e=next(e for e in entries(pak) if e[0]=='item.dat');patched=pak[e[2]:e[2]+e[3]]
allowed=set()
for i,price in manifest['medal_prices'].items():
 pos=4+(int(i)-1)*288+0x9c;assert struct.unpack_from('<I',patched,pos)[0]==price>0;allowed.update(range(pos,pos+4))
assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(items,patched)))
print('PASS: real retraining eligibility, stat application, six-slot capacity/dedup; original five-slot save migration and six-slot roundtrip; airport key/garrison guards; medal shop dedup and price-only data edits')
