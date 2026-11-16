"""Hidden roster ownership, stock codecs and native XP; no original saves edited."""
from pathlib import Path
import sys,struct,json,hashlib
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'tools/python-deps-v093'))
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from world_event_compile import compile_image
import expedition_actions as E

BUILD=ROOT/'expedition-actions-build';BUILD.mkdir(exist_ok=True)
source=BUILD/'expedition_actions.c'
source.write_text(E.SOURCE+r'''
EXEXPORT ex_u32 EXSC probe_encode(ex_u32 a,ex_u32 out){return ((ex_u32(*)(ex_u32,ex_u32))0x419b70)(a,out);}
EXEXPORT ex_u32 EXSC probe_decode(ex_u32 saved,ex_u32 a,ex_u32 town){return ((ex_u32(*)(ex_u32,ex_u32,ex_u32))0x419ca0)(saved,a,town);}
''',encoding='utf8')
image,exports=compile_image(source,BUILD,0x590000,BUILD/'expedition_actions.dll',list(E.EXPORTS)+['probe_encode','probe_decode'])
native=(ROOT/'package/SteelEmpire.exe').read_bytes();pe=pefile.PE(data=native)
if '--integrated' in sys.argv:
 manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf8'))
 section=manifest['world_events'];base=int(section['image_base'],16)
 assert base+section['image_size']<=0x590000,'Probe helpers overlap integrated C image'
 for key in E.EXPORTS:exports[key]=int(section['exports'][key],16)
TOWN=0x1000000;MASTER=0x1080000;WAIT=0x1080100;HERO=0x1090000;GENERIC=0x10a0000
CM=0x10d0000;CRECS=0x10e0000;IM=0x10f0000;IRECS=0x1100000;THREAD=0x13c0000
WORLD=0x13a0000;CITY=0x13b0000;HEAD=0x13b1000;STOP=0x5ff000;STACK=0x13e0000
checks=0
def w(u,a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def r(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
def ret(u,n=0):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EIP,r(u,sp));u.reg_write(UC_X86_REG_ESP,sp+4+n)
def invoke(u,name,*args,this=0,cdecl=False):
 pc=exports[name] if isinstance(name,str) else name
 w(u,STACK,STOP)
 for i,value in enumerate(args):w(u,STACK+4+i*4,value)
 u.reg_write(UC_X86_REG_ESP,STACK);u.reg_write(UC_X86_REG_ECX,this)
 keep={reg:u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)}
 u.emu_start(pc,STOP,count=3000000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP,(name,hex(u.reg_read(UC_X86_REG_EIP)))
 assert u.reg_read(UC_X86_REG_ESP)==STACK+4+(0 if cdecl else len(args)*4),(name,hex(u.reg_read(UC_X86_REG_ESP)))
 assert keep=={reg:u.reg_read(reg) for reg in keep},name
 return u.reg_read(UC_X86_REG_EAX)
def ring(u,head,people):
 nodes=[head+0x20+i*0x10 for i in range(len(people))]
 w(u,head,nodes[0] if nodes else head);w(u,head+4,nodes[-1] if nodes else head)
 for i,(node,p) in enumerate(zip(nodes,people)):
  w(u,node,nodes[i+1] if i+1<len(nodes) else head);w(u,node+4,nodes[i-1] if i else head);w(u,node+8,p)
 return nodes
def person(u,p,kind=3,ident=30,job=2,level=20,xp=0):
 for offset,value in ((0,ident),(4,0),(8,kind),(0x38,job),(0x44,1<<job),(0x48,level),(0x4c,xp),
  (0x50,100),(0x54,100),(0x58,100),(0x60,50),(0x64,40),(0x68,30),(0x6c,30),(0x70,20)):
  w(u,p+offset,value)
 u.mem_write(p+0x18,('Hero%d'%ident if kind==3 else 'Soldier%d'%ident).encode()+b'\0')
def fixture(heroes=3,generics=20):
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0,4096);u.mem_map(0x400000,0x200000);u.mem_write(0x400000,pe.get_memory_mapped_image());u.mem_write(0x590000,image)
 u.mem_map(0x1000000,0x400000);u.alloc=[];u.freed=[];u.fail_at=0;u.heap=0x1210000;u.tls=True;u.calls=[]
 for a,v in ((TOWN+4,1),(TOWN+8,1),(TOWN+0x50a4c,MASTER),(TOWN+0x50a50,heroes),(TOWN+0x50a58,WAIT),(TOWN+0x50a5c,generics),
  (0x4880e8,CM),(CM,13),(CM+4,CRECS),(0x4880ec,IM),(IM,1),(IM+4,IRECS),(THREAD+0x14,0xabcdef01)):
  w(u,a,v)
 for job in range(1,14):
  p=CRECS+(job-1)*0x4e4
  for offset,value in ((0,job),(8,1),(0x38,job),(0x44,1<<job),(0x48,1),(0x50,100),(0x54,100),(0x58,100)):
   w(u,p+offset,value)
 for i in range(heroes):person(u,HERO+i*0x500,3,30+i)
 for i in range(generics):person(u,GENERIC+i*0x500,1,2)
 u.hero_nodes=ring(u,MASTER,[HERO+i*0x500 for i in range(heroes)])
 u.generic_nodes=ring(u,WAIT,[GENERIC+i*0x500 for i in range(generics)])
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if pc==0x450452:
   size=r(u,sp+4);p=0 if u.fail_at and len(u.alloc)+1==u.fail_at else u.heap
   if p:u.heap=(p+size+15)&~15;assert u.heap<0x1300000;u.alloc.append((p,size));u.mem_write(p,bytes(size))
   u.reg_write(UC_X86_REG_EAX,p);ret(u)
  elif pc==0x4500e6:u.freed.append(r(u,sp+4));ret(u)
  elif pc==0x438a80:ret(u,4)
  elif pc==0x45290b:u.reg_write(UC_X86_REG_EAX,THREAD if u.tls else 0);ret(u)
  elif pc in (0x414fc0,0x415010,0x45046d):u.calls.append(pc)
 u.hook_add(UC_HOOK_CODE,boundary)
 return u
def prepare(u,slot=0):return invoke(u,'ex_prepare',TOWN,slot)
def add(u,a,p):return invoke(u,'ex_add',a,p)
def party(u):
 a=prepare(u)
 for p in (HERO,HERO+0x500,HERO+0xa00,GENERIC,GENERIC+0x500):assert add(u,a,p)==1
 return a
def waiting(u):
 result=[];node=r(u,WAIT)
 for _ in range(10001):
  if node==WAIT:return result
  assert r(u,r(u,node)+4)==node and r(u,r(u,node+4))==node
  result.append(r(u,node+8));node=r(u,node)
 raise AssertionError('unbounded list')

for slot in range(4):
 u=fixture();normal=bytes(u.mem_read(TOWN+0x104,9*0x55b0));a=prepare(u,slot)
 assert a==TOWN+0x104+(slot+9)*0x55b0 and r(u,a+0x14)==slot+10
 assert invoke(u,'ex_resolve',TOWN,slot)==a and not prepare(u,slot)
 assert not any(r(u,a+offset) for offset in (8,12,16)) and not any(r(u,TOWN+0x50654+i*4) for i in range(15))
 assert bytes(u.mem_read(TOWN+0x104,9*0x55b0))==normal;checks+=1
for slot in (4,0xffffffff):
 u=fixture();before=bytes(u.mem_read(TOWN,0x51000));assert not prepare(u,slot) and bytes(u.mem_read(TOWN,0x51000))==before;checks+=1
u=fixture();a=party(u);assert r(u,a+0x1c)==5 and r(u,a+0x34)==HERO and r(u,a+0xfc)==HERO
assert len(waiting(u))==18 and all(r(u,p+4)==2 and r(u,p+0x10)==10 for p in (HERO,GENERIC))
assert all(p not in u.freed for p in (HERO,GENERIC)) and u.generic_nodes[:2]==u.freed[:2]
assert not add(u,a,HERO) and not add(u,a,GENERIC);checks+=1
for mode in ('lord','main','dead','assigned','office','training','foreign_pointer','malformed_list'):
 u=fixture();a=prepare(u);p=HERO
 if mode=='lord':w(u,TOWN+0xa0,p)
 elif mode=='main':w(u,p,14)
 elif mode=='dead':w(u,p+4,1)
 elif mode=='assigned':w(u,p+0x10,1)
 elif mode=='office':w(u,p+0x14,4)
 elif mode=='training':w(u,p+4,2)
 elif mode=='foreign_pointer':p=HERO+0x2000;person(u,p)
 else:w(u,MASTER+4,0)
 before=bytes(u.mem_read(a,0x55b0));assert not add(u,a,p) and bytes(u.mem_read(a,0x55b0))==before,mode;checks+=1
u=fixture(4,21);a=prepare(u)
for i in range(3):assert add(u,a,HERO+i*0x500)
for i in range(20):assert add(u,a,GENERIC+i*0x500)
assert not add(u,a,HERO+3*0x500) and not add(u,a,GENERIC+20*0x500)
assert r(u,a+0x1c)==23 and len(waiting(u))==1;checks+=1

u=fixture();a=party(u);snapshots={p:bytes(u.mem_read(p,0x4e4)) for p in (HERO,HERO+0x500,HERO+0xa00,GENERIC,GENERIC+0x500)}
assert invoke(u,'ex_return',a)==1 and not invoke(u,'ex_resolve',TOWN,0)
assert len(waiting(u))==20 and len(set(waiting(u)))==20
for p,old in snapshots.items():
 expected=bytearray(old)
 for offset in (4,0x10,0x14):struct.pack_into('<I',expected,offset,0)
 assert bytes(u.mem_read(p,0x4e4))==expected
assert not invoke(u,'ex_return',a);checks+=1

for failed in (1,2):
 u=fixture();a=party(u);u.fail_at=len(u.alloc)+failed
 before=bytes(u.mem_read(a,0x55b0));people=bytes(u.mem_read(GENERIC,0xa00));members=list(waiting(u))
 assert not invoke(u,'ex_return',a)
 assert bytes(u.mem_read(a,0x55b0))==before and bytes(u.mem_read(GENERIC,0xa00))==people and waiting(u)==members
 assert GENERIC not in u.freed and GENERIC+0x500 not in u.freed;checks+=1

# A failed preflight has no partial return and unknown armies are untouched.
for mode in ('full','invalid_tag','unknown_slot','duplicate_pointer'):
 u=fixture();a=party(u)
 if mode=='full':w(u,TOWN+0x50a5c,10000)
 elif mode=='invalid_tag':w(u,a+0x55ac,123)
 elif mode=='unknown_slot':w(u,a+0x14,15)
 else:w(u,a+0x60+20*4,GENERIC);w(u,a+0x1c,6)
 before=bytes(u.mem_read(a,0x55b0));assert not invoke(u,'ex_return',a) and bytes(u.mem_read(a,0x55b0))==before;checks+=1

# Named IDs resolve to the existing master; generics are reconstructed once.
u=fixture();a=party(u);saved=0x1190000;loaded=0x1150000
w(u,IRECS,1);w(u,IRECS+0x2c,16382);w(u,IRECS+0x50,55)
u.mem_write(GENERIC+0xb4,bytes(u.mem_read(IRECS,0x10c)))
assert invoke(u,'probe_encode',a,saved)==saved
assert r(u,saved+0x74)==E.MAGIC,'Native travel tail must persist expedition tag'
assert invoke(u,'probe_decode',saved,loaded,TOWN)==loaded
assert r(u,loaded+0x34)==HERO and r(u,loaded+0xfc)==HERO
assert r(u,loaded+0x14)==10 and r(u,loaded+0x55ac)==E.MAGIC
assert r(u,loaded+8)==r(u,loaded+0xc)==r(u,loaded+0x10)==0
for i in range(2):
 p=r(u,loaded+0x60+i*4)
 assert p and p!=GENERIC+i*0x500
 assert bytes(u.mem_read(p,0xa8))==bytes(u.mem_read(GENERIC+i*0x500,0xa8))
assert r(u,r(u,loaded+0x60)+0xb4)==1 and r(u,r(u,loaded+0x60)+0xb4+0x50)==55
checks+=1

# Level99 shares are divided equally among eligible living members.
for maximum in (0,1,2,3):
 u=fixture();a=prepare(u)
 for i in range(3):assert add(u,a,HERO+i*0x500)
 for i in range(maximum):w(u,HERO+i*0x500+0x48,99)
 before=r(u,THREAD+0x14);assert invoke(u,'ex_award',a,10,42)==1
 expected=0 if maximum==3 else 30//(3-maximum)
 for i in range(3):assert r(u,HERO+i*0x500+0x4c)==(0 if i<maximum else expected)
 assert r(u,THREAD+0x14)==before and all(r(u,HERO+i*0x500+4)==2 for i in range(3));checks+=1
u=fixture();a=prepare(u);assert add(u,a,HERO);w(u,HERO+0x4c,98)
assert invoke(u,'ex_award',a,10,123)==1 and r(u,HERO+0x48)==21 and r(u,HERO+0x4c)==8
assert r(u,THREAD+0x14)==0xabcdef01 and u.calls.count(0x415010)==1;checks+=1
for failure in ('tls','overflow','zero_threshold','invalid_xp'):
 u=fixture();a=prepare(u);assert add(u,a,HERO)
 if failure=='tls':u.tls=False
 elif failure=='overflow':w(u,HERO+0x4c,0x7ffffffe)
 elif failure=='zero_threshold':w(u,HERO+0x50,0)
 else:pass
 before=bytes(u.mem_read(HERO,0x4e4))
 assert not invoke(u,'ex_award',a,100001 if failure=='invalid_xp' else 10,1)
 assert bytes(u.mem_read(HERO,0x4e4))==before and r(u,THREAD+0x14)==0xabcdef01;checks+=1

# Annual visits may grant XP to ordinary armies without changing membership.
u=fixture();a=TOWN+0x104;w(u,a,1);w(u,a+0x14,1);w(u,a+0x60,HERO)
before=bytes(u.mem_read(a,0x55b0));assert invoke(u,'ex_award',a,10,12)==1
assert r(u,HERO+0x4c)==10 and bytes(u.mem_read(a,0x55b0))==before;checks+=1
u=fixture();a=prepare(u);assert add(u,a,HERO);w(u,HERO+4,1);w(u,HERO+0x54,0)
assert invoke(u,'ex_return',a)==1 and r(u,HERO+4)==1 and r(u,HERO+0x54)==0 and r(u,HERO+0x10)==0;checks+=1
u=fixture();a=TOWN+0x104;w(u,a,1);w(u,a+0x14,1);w(u,a+0x60,HERO);w(u,HERO+4,2)
before=bytes(u.mem_read(HERO,0x4e4));assert not invoke(u,'ex_award',a,10,1)
assert bytes(u.mem_read(HERO,0x4e4))==before;checks+=1

# Main-story reassignment wins: remove only the hidden duplicate reference.
u=fixture();a=party(u);normal=TOWN+0x104;w(u,normal+0x14,1);w(u,normal+0x60,HERO);w(u,HERO+0x10,1);w(u,HERO+4,0)
assert invoke(u,'ex_reconcile',TOWN)==1 and r(u,normal+0x60)==HERO and r(u,HERO+0x10)==1
assert all(r(u,a+0x60+i*4)!=HERO for i in range(81)) and r(u,a+0x1c)==4
assert invoke(u,'ex_return',a)==1 and r(u,HERO+0x10)==1;checks+=1

# Execute the complete stock world-load postpass with one serialized city and
# no serialized field actors. Hidden inline rosters must stay off-map.
u=fixture();a=party(u);w(u,WORLD+0x3d4,HEAD);w(u,HEAD,HEAD);w(u,HEAD+4,HEAD)
VT=0x13b2000;VIRTUAL=0x5de000
w(u,CITY,VT);w(u,VT+8,VIRTUAL);w(u,CITY+8,1);w(u,CITY+0xc,5001);w(u,CITY+0x7c,TOWN)
u.mem_write(VIRTUAL,b'\xc2\x04\x00');reads=[];world_construct=[]
def world_boundary(u,pc,size,data):
 sp=u.reg_read(UC_X86_REG_ESP)
 if pc==0x45016e:
  assert r(u,sp+8)==56 and r(u,sp+12)==1
  header=[0]*14;header[12]=1;u.mem_write(r(u,sp+4),struct.pack('<14I',*header));reads.append(1)
  u.reg_write(UC_X86_REG_EAX,1);ret(u)
 elif pc==0x420410:
  assert r(u,sp+4)==WORLD;world_construct.append('city');u.reg_write(UC_X86_REG_EAX,CITY);ret(u,8)
 elif pc in (0x41f3b0,0x420c50,0x438330):raise AssertionError('Hidden expedition spawned a map actor or resident army')
u.hook_add(UC_HOOK_CODE,world_boundary)
invoke(u,0x4227c0,0x1234,this=WORLD)
assert reads==[1] and world_construct==['city'] and r(u,WORLD+0x23c)==CITY
assert all(not r(u,WORLD+0xac+i*4) for i in range(100))
assert all(not r(u,WORLD+0x84+i*4) for i in range(9))
assert all(not r(u,TOWN+0x50654+i*4) for i in range(15))
assert invoke(u,'ex_resolve',TOWN,0)==a and r(u,a+0x1c)==5
assert not any(r(u,a+offset) for offset in (8,12,16));checks+=1

print('PASS expedition actions:',checks,'native roster/codec/XP ownership cases; ordinary nine armies unchanged')
(ROOT/'test-expedition-actions-report.json').write_text(json.dumps(dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(native).hexdigest(),
 coverage=['Four hidden native inline rosters outside normal nine','Bounded hero/master and generic ownership transfer; atomic allocation failure',
 'Native419b70/419ca0 save codecs; named ID identity and generic item/skill preservation','Native414fc0/415010 growth, level99 redistribution and restored CRT seed',
 'No world/resident registration and main-story hero reassignment preservation'],
 not_checked=['Hardware visual playtest','Full real save-file roundtrip; stock army codecs and full world-load postpass execute']),indent=2),encoding='utf8')
