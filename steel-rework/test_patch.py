from build import *
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
binary=(ROOT/'package/SteelEmpire.exe').read_bytes();pe=pefile.PE(data=binary)
def setup():
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000);u.mem_write(0x400000,pe.get_memory_mapped_image());u.mem_map(0x1000000,0x400000)
 u.reg_write(UC_X86_REG_ESP,0x13f0000);return u
def w(u,a,v):u.mem_write(a,struct.pack('<I',v))
def r(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
def ret(u,n=0):
 sp=u.reg_read(UC_X86_REG_ESP);pc=r(u,sp);u.reg_write(UC_X86_REG_ESP,sp+4+n);u.reg_write(UC_X86_REG_EIP,pc)
def market_test(vtable,existing,expected):
 u=setup();owner=0x1000000;shop=0x1001000;head=0x1002000;nodes=0x1003000;added=[]
 w(u,owner+4,shop);w(u,shop,vtable);w(u,shop+0x5c,head)
 def setlist(ids):
  w(u,head,nodes if ids else head)
  for j,ident in enumerate(ids):w(u,nodes+j*0x200,nodes+(j+1)*0x200 if j+1<len(ids) else head);w(u,nodes+j*0x200+12,ident)
 setlist(existing);u.reg_write(UC_X86_REG_ESI,owner)
 def hook(u,a,size,data):
  if a==0x42a820:
   ptr=r(u,u.reg_read(UC_X86_REG_ESP)+4);name=bytes(u.mem_read(ptr,32)).split(b'\0')[0].decode('cp949');ident=next(int(k) for k,v in manifest['machines'].items() if v==name)
   assert u.reg_read(UC_X86_REG_ECX)==shop;added.append(ident);setlist(existing+added);ret(u,4)
  elif a==0x450452:u.reg_write(UC_X86_REG_EAX,0x12345678);ret(u)
  elif a==0x44bc1f:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x44bc18,0,count=20000)
 assert added==expected,(added,expected)
 assert u.reg_read(UC_X86_REG_ESP)==0x13efffc
 assert u.reg_read(UC_X86_REG_ESI)==owner
 assert u.reg_read(UC_X86_REG_EAX)==0x12345678
ground=list(range(6,17));air=[1,2,3,4,5,22,23,24]
for vt,ids in [(0x462354,ground),(0x462380,air)]:
 market_test(vt,[],ids);market_test(vt,ids,[]);market_test(vt,ids[::2],[i for i in ids if i not in ids[::2]])
market_test(0x462298,[],[])
u=setup();ui=0x1000000;manager=0x1001000;records=0x1010000;lst=0x1002000
w(u,0x4880e8,manager);w(u,manager,255);w(u,manager+4,records);w(u,ui+0x44,lst)
for ident in range(1,14):w(u,records+(ident-1)*0x4e4,ident);w(u,records+(ident-1)*0x4e4+0xac,ident+100)
u.reg_write(UC_X86_REG_ESI,ui);seen=[]
def training_hook(u,a,size,data):
 if a==0x4101a0:
  sp=u.reg_read(UC_X86_REG_ESP);ident=r(u,sp+4);assert r(u,sp+8)==ident+100;assert u.reg_read(UC_X86_REG_ECX)==lst;seen.append(ident);ret(u,16)
 elif a==0x424a8e:u.emu_stop()
u.hook_add(UC_HOOK_CODE,training_hook);u.emu_start(0x424a3c,0,count=50000)
assert seen==list(range(1,14)),seen
assert u.reg_read(UC_X86_REG_ESP)==0x13f0000
p=(ROOT/'package/patch104.pak').read_bytes();es=list(entries(p));assert len(es)==2
name,flag,off,size,raw=es[0];assert name=='char.dat' and flag==0 and size==raw==88744
orig=(ROOT/'extracted/Data.pak/char.dat').read_bytes();new=p[off:off+size]
changed=set(i for i,(a,b) in enumerate(zip(orig,new)) if a!=b)
allowed=set()
for ident,cost in manifest['new_costs_iron_oil_gold_days'].items():
 start=4+(int(ident)-1)*348+204;allowed.update(range(start,start+16));assert struct.unpack_from('<4I',new,start)==tuple(cost)
assert changed<=allowed
assert pe.verify_checksum()
print('PASS: 7 market scenarios; real character lookup with 13 UI entries; stack/register preservation; archive and cost isolation; PE checksum')
