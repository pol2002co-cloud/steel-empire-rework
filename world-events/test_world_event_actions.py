"""Real native constructor, equipment, inventory/list and cleanup execution."""
from test_patch import *
import world_event_actions as A

STOP=0x5ff000;TOWN=0x1000000;ARMY=0x1060000;HERO=0x10c0000
CM=0x10d0000;MM=0x10e0000;IM=0x10f0000
MRECS=0x1300000;IRECS=0x1340000;FRAME=0x13b0000
MACHINE_DATA=(ROOT/'extracted/Data.pak/machine.dat').read_bytes()
def machine_field(ident,offset):
 return struct.unpack_from('<I',MACHINE_DATA,4+(ident-1)*240+offset)[0]

def call(u,pc,*args,this=0):
 if isinstance(pc,str):pc=int(u.actions[pc],16)
 sp=0x13e0000;w(u,sp,STOP)
 for i,v in enumerate(args):w(u,sp+4+i*4,v)
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,this)
 u.emu_start(pc,STOP,count=1000000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP,hex(u.reg_read(UC_X86_REG_EIP))
 assert u.reg_read(UC_X86_REG_ESP)==sp+4+len(args)*4
 return u.reg_read(UC_X86_REG_EAX)

def fixture():
 u=setup();u.mem_map(0,4096);cursor=0x5d0000
 def put(b):
  nonlocal cursor
  pc=cursor;u.mem_write(pc,b);cursor=(pc+len(b)+15)&~15;return pc
 def patch(pc,old,new):u.mem_write(pc,old);u.mem_write(pc,new)
 if '--integrated' in sys.argv:u.actions=manifest['world_events']['actions']
 else:u.actions=A.emit(put,asm,lambda:cursor,patch)['world_event_actions']
 for p,v in ((0x4880e8,CM),(0x4880f0,MM),(0x4880ec,IM),(0x48cc1c,FRAME)):w(u,p,v)
 for p,v in ((ARMY,1),(ARMY+4,TOWN),(ARMY+8,TOWN),(ARMY+0x14,1),(ARMY+0x1c,1),(ARMY+0x34,HERO),(HERO+0x54,100),(HERO+0x48,60)):w(u,p,v)
 w(u,ARMY+0xfc,HERO)
 w(u,MM,24);w(u,MM+4,MRECS);w(u,IM,82);w(u,IM+4,IRECS)
 w(u,CM,13);w(u,CM+4,0x1280000)
 for job in range(1,14):
  p=0x1280000+(job-1)*0x4e4
  for o,v in ((0,job),(8,1),(0x38,job),(0x44,1<<job),(0x48,1),(0x54,100),(0x58,100)):w(u,p+o,v)
 for ident in range(1,25):
  p=MRECS+(ident-1)*0x1a8
  for o,v in ((4,ident),(8,machine_field(ident,0x24)),(0x50,machine_field(ident,0x20)),(0x54,1000),(0x58,1000),(0x5c,200),(0x60,200),(0x64,200),(0x68,200),(0x6c,100),(0x70,10),(0x7c,20),(0x84,20),(0x88,30)):w(u,p+o,v)
 for ident in range(1,83):
  p=IRECS+(ident-1)*0x10c
  for o,v in ((0,ident),(0x24,0),(0x2c,16382),(0x4c,10),(0x50,15),(0x58,100),(0x5c,100),(0x60,100),(0x64,100)):w(u,p+o,v)
 heap=[0x1100000];allocs=[];freed=[];frames=[];fail=[0];notices=[]
 def malloc(size):
  if fail[0] and size==fail[0]:return 0
  p=heap[0];heap[0]=(p+size+15)&~15;assert heap[0]<0x12f0000
  allocs.append((p,size));return p
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if pc==0x450452:u.reg_write(UC_X86_REG_EAX,malloc(r(u,sp+4)));ret(u)
  elif pc==0x4500e6:
   if r(u,sp+4):freed.append(r(u,sp+4))
   ret(u)
  elif pc==0x414ed0:
   p=malloc(0x4e4)
   if p:
    job=r(u,sp+4)
    for o,v in ((0,job),(8,1),(0x38,job),(0x44,1<<job),(0x48,r(u,sp+8)),(0x54,100),(0x58,100),(0x68,100),(0x6c,100),(0x60,80),(0x64,50),(0x70,70)):w(u,p+o,v)
   u.reg_write(UC_X86_REG_EAX,p);ret(u,8)
  elif pc in (0x442800,0x446310,0x413d80):u.reg_write(UC_X86_REG_EAX,u.reg_read(UC_X86_REG_ECX));ret(u)
  elif pc==0x4438f0:frames.append(r(u,sp+4));ret(u,4)
  elif pc==0x438a80:notices.append(r(u,sp+4));ret(u,4)
 u.hook_add(UC_HOOK_CODE,boundary)
 u.allocs=allocs;u.freed=freed;u.frames=frames;u.fail=fail
 return u

checks=0
for profile in range(1,6):
 u=fixture();snapshot=bytes(u.mem_read(TOWN,0x51000))
 if profile==3:w(u,ARMY+0x18,2);w(u,ARMY+0x20,1)
 assert call(u,'battle',ARMY,profile)==1
 assert len(u.frames)==1
 b=u.frames[0];enemy=r(u,b+0x50)
 assert r(u,b+0x4c)==ARMY and r(u,b+0x48)==TOWN
 assert r(u,b+0x1e4)==0 and r(u,b+0x1e8)==0
 assert r(u,enemy)==12 and r(u,enemy+4)==TOWN and r(u,enemy+8)==0
 assert r(u,enemy+0x55ac)==A.TEMP_MAGIC and r(u,enemy+0x34)!=0
 assert r(u,enemy+0x1c)==(24 if profile in (1,4) else 9 if profile==5 else 6)
 assert r(u,enemy+0x20)==(0 if profile in (1,4) else 9 if profile==5 else 6)
 assert bytes(u.mem_read(TOWN,0x51000))==snapshot
 for i in range(9):
  machine=r(u,enemy+0x3c+i*4)
  if machine:assert r(u,machine+0x8c)!=0
 # Native disposal frees the exact heap-owned units/machines and no player data.
 call(u,'destroy',enemy)
 owned={p for p,size in u.allocs if p!=b}
 assert set(u.freed)==owned and len(u.freed)==len(set(u.freed)),(profile,u.freed,u.allocs)
 assert bytes(u.mem_read(TOWN,0x51000))==snapshot
 checks+=1

for profile in range(1,6):
 u=fixture()
 if profile==3:w(u,ARMY+0x18,2);w(u,ARMY+0x20,1)
 assert call(u,'battle',ARMY,profile)==1;b=u.frames[0];created=[]
 def model(u,pc,size,data):
  if pc in (0x43d730,0x43f2a0,0x4408e0):
   sp=u.reg_read(UC_X86_REG_ESP);created.append((pc,r(u,sp+8),r(u,sp+16)))
   p=u.reg_read(UC_X86_REG_ECX);w(u,p+0x138,1)
   u.reg_write(UC_X86_REG_EAX,p);ret(u,16)
 u.hook_add(UC_HOOK_CODE,model)
 call(u,0x43a5a0,this=b)
 n=24 if profile in (1,4) else 9 if profile==5 else 6
 assert sum(r(u,b+0x36c+i*4)!=0 for i in range(81))==n
 assert len(created)==n+1 and r(u,b+0x200)!=0 and r(u,b+0x204)!=0
 checks+=1

for addr,value in ((ARMY,12),(ARMY+8,0),(ARMY+0x18,3),(ARMY+0x34,0),(HERO+4,1),(HERO+0x54,0),(ARMY+0x14,0),(0x48cc1c,0)):
 u=fixture();w(u,addr,value);assert call(u,'battle',ARMY,1)==0 and not u.frames and not u.allocs;checks+=1
for profile in (0,18,0xffffffff):
 u=fixture();assert call(u,'battle',ARMY,profile)==0 and not u.allocs;checks+=1
u=fixture();w(u,ARMY+0x18,2);assert call(u,'battle',ARMY,3)==0 and not u.allocs;checks+=1

for result in (0,1,2):
 u=fixture();call(u,'battle',ARMY,1);b=u.frames[0];enemy=r(u,b+0x50)
 if result==2:call(u,'dispose',enemy,this=TOWN)
 w(u,0x48d39c,result);w(u,TOWN+0x509f8,17)
 # Execute the real battle cleanup tail after its unit/model destructors.
 sp=0x13e0000
 for i in range(8):w(u,sp+i*4,0)
 w(u,sp+32,STOP)
 u.reg_write(UC_X86_REG_EBP,b);u.reg_write(UC_X86_REG_ESP,sp)
 u.emu_start(0x439a01,STOP,count=1000000)
 assert r(u,int(u.actions['result_address'],16))==result+1
 assert r(u,TOWN+0x509f8)==17 and enemy in u.freed
 assert len(u.freed)==len(set(u.freed));checks+=1

# Execute the full original settlement function: it decides the result from the
# commander states, applies stock army loss, destroys units, then runs our tail.
for outcome in ('loss','retreat','win'):
 u=fixture();call(u,'battle',ARMY,1);b=u.frames[0];enemy=r(u,b+0x50)
 au=0x12c0000;eu=0x12c1000;vt=0x13b1000;music=0x13b1100
 for p in (au,eu):w(u,p,vt);w(u,p+0x138,1);w(u,p+0x50,50)
 w(u,au+0x138,0 if outcome=='loss' else 1)
 w(u,eu+0x138,0 if outcome=='win' else 1)
 w(u,b+0x200,au);w(u,b+0x204,eu);w(u,b+0x228,au);w(u,b+0x36c,eu)
 w(u,0x476fd8,music);w(u,music,vt);w(u,vt+0xc,0x5fc100)
 w(u,vt+0x14,0x5fc120);w(u,vt,0x5fc140);w(u,HERO+8,3)
 w(u,TOWN+0x509f8,17)
 def virtual(u,pc,size,data):
  if pc==0x5fc100:ret(u)
  elif pc==0x5fc120:ret(u,12)
  elif pc==0x5fc140:ret(u,4)
  elif pc==0x45046d:u.reg_write(UC_X86_REG_EAX,0);ret(u)
 u.hook_add(UC_HOOK_CODE,virtual)
 call(u,0x439680,this=b)
 assert r(u,int(u.actions['result_address'],16))=={'loss':1,'retreat':2,'win':3}[outcome]
 assert enemy in u.freed and len(u.freed)==len(set(u.freed))
 assert r(u,TOWN+0x509f8)==17+(outcome=='loss')
 checks+=1

# Allocation/equipment failures release all partial enemy state and start no UI.
for size in (0x55b0,0x4e4,0xe54):
 u=fixture();u.fail[0]=size
 assert call(u,'battle',ARMY,1)==0 and not u.frames
 assert {p for p,n in u.allocs}==set(u.freed);checks+=1

u=fixture();assert call(u,'give_item',ARMY,54)==1
p=call(u,'find_item',ARMY,54);assert p==ARMY+0x1a4 and r(u,p)==54
assert call(u,'take_item',ARMY,54)==1 and r(u,p)==0
assert call(u,'take_item',ARMY,54)==0
for i in range(80):w(u,ARMY+0x1a4+i*0x10c,5)
assert call(u,'give_item',ARMY,54)==2
for ident in (0,46,61,83):assert call(u,'give_item',ARMY,ident)==0
checks+=8

def lists(u,known_id):
 for offset,head in ((0x50a04,0x13c0000),(0x50a1c,0x13c0100),(0x50a58,0x13c0200),(0x50a64,0x13c0300),(0x50a94,0x13c0400)):
  w(u,TOWN+offset,head);w(u,head,head);w(u,head+4,head)
  if offset in (0x50a04,0x50a1c):
   node=head+32;w(u,head,node);w(u,head+4,node);w(u,node,head);w(u,node+4,head);w(u,node+8,known_id)

for job in (1,8,11,12,13):
 u=fixture();lists(u,job);assert call(u,'hire',TOWN,job,15)==1
 assert r(u,TOWN+0x50a5c)==1
 node=r(u,r(u,TOWN+0x50a58));p=r(u,node+8)
 assert r(u,p+0x38)==job and r(u,p+0x48)==15 and r(u,p+0x10)==0 and r(u,p+8)==1
 assert call(u,'hire',TOWN,2 if job!=2 else 3,15)==0
 w(u,TOWN+0x50a5c,10000);assert call(u,'hire',TOWN,job,15)==2;checks+=3

for ident in (1,13,22,24):
 u=fixture();lists(u,ident);assert call(u,'give_machine',TOWN,ident)==1
 assert r(u,TOWN+0x50a68)==1
 node=r(u,r(u,TOWN+0x50a64));p=r(u,node+8)
 assert r(u,p+4)==ident and r(u,p)==0
 assert call(u,'give_machine',TOWN,2 if ident!=2 else 3)==1
 w(u,TOWN+0x50a68,10000);assert call(u,'give_machine',TOWN,ident)==2;checks+=3
for ident in (0,17,18,19,20,21,25):
 u=fixture();lists(u,ident);assert call(u,'give_machine',TOWN,ident)==0;checks+=1

def cdecl(u,pc,*args):
 sp=0x13e0000;w(u,sp,STOP)
 for i,v in enumerate(args):w(u,sp+4+i*4,v)
 u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(pc,STOP,count=1000000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP and u.reg_read(UC_X86_REG_ESP)==sp+4

# The actual serializer/deserializer preserves rewards through stock save records.
u=fixture();lists(u,11);assert call(u,'hire',TOWN,11,15)==1
p=r(u,r(u,r(u,TOWN+0x50a58))+8);record=0x13c1000;loaded=0x13c2000
cdecl(u,0x415c90,p,record);cdecl(u,0x415db0,record,loaded)
for off in (0,8,0x10,0x38,0x44,0x48):assert r(u,p+off)==r(u,loaded+off)
checks+=1
u=fixture();lists(u,0);assert call(u,'give_machine',TOWN,24)==1
p=r(u,r(u,r(u,TOWN+0x50a64))+8);record=0x13c1000;loaded=0x13c2000
cdecl(u,0x416da0,p,record);cdecl(u,0x416e90,record,loaded)
for off in (0,4,8,0x54,0x58,0x5c,0x7c,0x84):assert r(u,p+off)==r(u,loaded+off)
checks+=1

def machine_stock(ids):
 u=fixture();lists(u,0);w(u,TOWN+4,1);w(u,TOWN+8,1)
 for ident in ids:assert call(u,'give_machine',TOWN,ident)==1
 head=r(u,TOWN+0x50a64);nodes=[];p=r(u,head)
 while p!=head:nodes.append(p);p=r(u,p)
 return u,head,nodes

for ident in (1,4,6,13,16,22,24):
 u,head,nodes=machine_stock([ident]);node=nodes[0];p=r(u,node+8)
 assert call(u,'find_machine',TOWN,ident)==p
 record=0x13c1000;loaded=0x13c2000
 cdecl(u,0x416da0,p,record);cdecl(u,0x416e90,record,loaded)
 assert r(u,loaded+4)==ident and r(u,loaded+0x54)==r(u,loaded+0x58)>0
 # Restore the native loaded instance into the same stock node to prove the
 # delivery lookup is based on saved IDs/state, not a creation-time pointer.
 w(u,node+8,loaded);u.freed.clear()
 assert call(u,'find_machine',TOWN,ident)==loaded
 assert call(u,'take_machine',TOWN,ident)==1
 assert r(u,TOWN+0x50a68)==0 and (r(u,head),r(u,head+4))==(head,head)
 assert u.freed==[loaded,node]
 assert call(u,'find_machine',TOWN,ident)==0 and call(u,'take_machine',TOWN,ident)==0
 assert u.freed==[loaded,node];checks+=1

for offset,value in ((0,1),(0x8c,HERO),(0x90,HERO),(0x54,0),(0x54,999),(0x58,0),(0x50,1),(0x50,10)):
 u,head,nodes=machine_stock([13]);p=r(u,nodes[0]+8);w(u,p+offset,value)
 before=bytes(u.mem_read(TOWN+0x50a60,12)),bytes(u.mem_read(head,8)),bytes(u.mem_read(nodes[0],12))
 assert call(u,'find_machine',TOWN,13)==0 and call(u,'take_machine',TOWN,13)==0
 assert not u.freed and before==(bytes(u.mem_read(TOWN+0x50a60,12)),bytes(u.mem_read(head,8)),bytes(u.mem_read(nodes[0],12)));checks+=1

for ident in (0,17,18,19,20,21,25):
 u,head,nodes=machine_stock([13]);assert call(u,'find_machine',TOWN,ident)==0 and call(u,'take_machine',TOWN,ident)==0
 assert not u.freed and r(u,TOWN+0x50a68)==1;checks+=1

# Repairs are pointer references in five native workshop rows, even if an
# editor has already set the queued machine's HP back to its maximum.
u,head,nodes=machine_stock([13]);p=r(u,nodes[0]+8)
bh=0x13c4000;bn=bh+32;workshop=0x13c5000
w(u,TOWN+0x50a88,bh);w(u,bh,bn);w(u,bn,bh);w(u,bn+8,workshop)
w(u,workshop+0xc,19);w(u,workshop+0x38,5);w(u,workshop+0x250,1);w(u,workshop+0x26c,p)
assert call(u,'find_machine',TOWN,13)==0 and call(u,'take_machine',TOWN,13)==0 and not u.freed
w(u,workshop+0x250,0);assert call(u,'find_machine',TOWN,13)==p
w(u,workshop+0x38,6);assert call(u,'find_machine',TOWN,13)==0
w(u,workshop+0x38,5);assert call(u,'take_machine',TOWN,13)==1;checks+=3

# Mixed stock, duplicate IDs and linked-list integrity are all resolved against
# actual instances; consuming one machine preserves every unrelated record.
u,head,nodes=machine_stock([1,13,13,24]);selected=call(u,'find_machine',TOWN,13)
others={r(u,n+8) for n in nodes if r(u,n+8)!=selected}
assert call(u,'take_machine',TOWN,13)==1 and r(u,TOWN+0x50a68)==3
assert selected in u.freed and not others.intersection(u.freed)
assert call(u,'take_machine',TOWN,13)==1 and r(u,TOWN+0x50a68)==2
assert call(u,'take_machine',TOWN,13)==0 and len(u.freed)==4;checks+=1
for corruption in ('duplicate','count','next','prev','home'):
 u,head,nodes=machine_stock([13,13])
 if corruption=='duplicate':w(u,nodes[1]+8,r(u,nodes[0]+8))
 elif corruption=='count':w(u,TOWN+0x50a68,1)
 elif corruption=='next':w(u,nodes[0],head)
 elif corruption=='prev':w(u,nodes[0]+4,0)
 else:w(u,TOWN+4,2)
 assert call(u,'find_machine',TOWN,13)==0 and call(u,'take_machine',TOWN,13)==0 and not u.freed;checks+=1
# Calibrated from shipped machine.dat, not synthetic air/ground values: +8 is
# movement flags (0/2/10/11); +50 is machine category (0 ground/1 air).
ordinary=list(range(1,17))+[22,23,24]
for ident in ordinary:
 u,head,nodes=machine_stock([ident]);p=r(u,nodes[0]+8)
 assert r(u,p+8)==machine_field(ident,0x24)
 assert r(u,p+0x50)==machine_field(ident,0x20)
 assert call(u,'find_machine',TOWN,ident)==p
 assert call(u,'take_machine',TOWN,ident)==1
 assert u.freed==[p,nodes[0]];checks+=1

# Private readonly save captures from before/after the user's new save. Decode
# actual 160-byte stock records with the original native loader, then run the
# emitted lookup/consume helper. Never open a live .Sav for writing.
goblin_record=bytes.fromhex('060000000000000002000000b0edbaedb8b04d4b320000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004a0100004a0100004600000052000000140000000400000009000000040000000100000001000000030000000a000000f7ffffff1a00000023000000e02e00001e00000014000000a8610000')
assert len(goblin_record)==160
u,head,nodes=machine_stock([6]);record=0x13c1000;loaded=0x13c2000
u.mem_write(record,goblin_record);cdecl(u,0x416e90,record,loaded)
w(u,nodes[0]+8,loaded);assert call(u,'find_machine',TOWN,6)==loaded
assert (r(u,loaded+8),r(u,loaded+0x50),r(u,loaded+0x54),r(u,loaded+0x58))==(2,0,330,330)
# Native unassign clears assignment/crew and inserts the same machine into
# spare stock; it must become eligible without any helper-side state rewrite.
w(u,head,head);w(u,head+4,head);w(u,TOWN+0x50a68,0)
w(u,TOWN+0x50654,ARMY);w(u,ARMY+0x34,0);w(u,ARMY+0x3c,loaded)
w(u,loaded,1);w(u,loaded+0x8c,HERO);w(u,loaded+0x90,HERO)
assert call(u,'find_machine',TOWN,6)==0
call(u,0x437df0,1,this=TOWN)
assert (r(u,loaded),r(u,loaded+0x8c),r(u,loaded+0x90))==(0,0,0)
assert call(u,'find_machine',TOWN,6)==loaded
assert call(u,'take_machine',TOWN,6)==1;checks+=3
real_stock_cases=0
for filename in ('StockMachineRecords.bin','StockMachineRecords-current.bin','StockMachineRecords-played.bin'):
 source=ROOT/'delivery-report-v0113'/filename
 if not source.exists():continue
 records=source.read_bytes();assert len(records)%160==0
 goblins=0
 for off in range(0,len(records),160):
  raw=records[off:off+160];ident=struct.unpack_from('<I',raw)[0]
  if ident not in ordinary:continue
  u,head,nodes=machine_stock([ident]);node=nodes[0]
  record=0x13c1000;loaded=0x13c2000;u.mem_write(record,raw)
  cdecl(u,0x416e90,record,loaded);w(u,node+8,loaded)
  before=bytes(u.mem_read(loaded,0x1a8));u.freed.clear()
  eligible=(r(u,loaded)==0 and not r(u,loaded+0x8c) and not r(u,loaded+0x90)
            and r(u,loaded+0x54)==r(u,loaded+0x58)>0)
  assert bool(call(u,'find_machine',TOWN,ident))==eligible,(filename,off//160,ident)
  assert bytes(u.mem_read(loaded,0x1a8))==before
  assert call(u,'take_machine',TOWN,ident)==int(eligible)
  assert u.freed==([loaded,node] if eligible else [])
  if ident==6:
   assert eligible and r(u,loaded+8)==2 and r(u,loaded+0x50)==0
   goblins+=1
  real_stock_cases+=1;checks+=1
 assert goblins>0,(filename,'Goblin MK2 missing')
print('PASS world event actions:',checks,'cases; actual save stock records:',real_stock_cases)

if '--integrated' in sys.argv:
 import hashlib,datetime
 report=dict(status='passed',cases=checks,engine_sha256=hashlib.sha256(binary).hexdigest(),version=manifest['version'],test='test_world_event_actions.py --integrated',tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scoped_mocks=['Heap OS allocation/free','Graphics constructors and frame dispatch','Character creation'],not_checked=['Hardware visual playtest'])
 (ROOT/'test-world-actions-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
