"""Native save clone plus isolated, fault-injected Win32 file transactions."""
from pathlib import Path
import sys,struct,tempfile,json,hashlib,zlib,subprocess,os,re
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'tools/python-deps-v093'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
import pefile
from world_event_compile import compile_image,ZIG
from world_events_patch import cp949_source
import expedition_storage as S

native=(ROOT/'SteelEmpire-v0120.exe').read_bytes();pe=pefile.PE(data=native)
ks=Ks(KS_ARCH_X86,KS_MODE_32)
compiled={};checks=0
STOP=0x5ff000;STACK=0x13e0000;DATA=0x10b0000;OUTPUT=0x10b2000;FILE=0x10a0000
GETMODULE=0x5fc000;GETPROC=0x5fc020;APPFUNC=0x5fc900
APIS={n:0x5fd000+i*32 for i,n in enumerate(('CreateFileA','ReadFile','WriteFile','SetFilePointer','GetFileSize','FlushFileBuffers','CloseHandle','DeleteFileA','MoveFileExA','GetTempFileNameA'))}

def w(u,a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def r(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
def string(u,a):
 b=bytearray()
 for i in range(260):
  x=bytes(u.mem_read(a+i,1))[0]
  if not x:return b.decode('ascii')
  b.append(x)
 raise AssertionError('Unbounded native path')
def ret(u,n=0):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EIP,r(u,sp));u.reg_write(UC_X86_REG_ESP,sp+4+n)
def result(u,value,argc=0):u.reg_write(UC_X86_REG_EAX,value&0xffffffff);ret(u,argc*4)

def build():
 with tempfile.TemporaryDirectory(prefix='SteelExpeditionStore-') as t:
  folder=Path(t);image=bytearray();base=0x5e0000
  def address():return base+len(image)
  def put(data):
   at=address();image.extend(data);image.extend(bytes((-len(image))%16));return at
  def read(a,n):return native[pe.get_offset_from_rva(a-0x400000):pe.get_offset_from_rva(a-0x400000)+n]
  meta=S.emit(put,lambda s,a:bytes(ks.asm(s,a)[0]),address,read)
  (folder/'expedition_storage.h').write_text((ROOT/'expedition_storage.h').read_text(encoding='utf8'),encoding='utf8')
  source='''typedef unsigned int u32;
#define SC __attribute__((stdcall))
#define V(a) (*(volatile u32 *)(u32)(a))
#define PTR(a) ((u32)(a))
typedef u32 (SC *F1)(u32);typedef u32 (SC *F2)(u32,u32);typedef u32 (SC *F3)(u32,u32,u32);typedef u32 (SC *F4)(u32,u32,u32,u32);
typedef u32 (*Allocate)(u32);typedef void (*Release)(u32);
#define E_NATIVE_SAVE '''+meta['native_save']+'''
#include "expedition_storage.h"
__declspec(dllexport) int SC save(u32 slot,u32 p,u32 n){return es_save(slot,(void *)p,n);}
__declspec(dllexport) int SC load(u32 slot,u32 p,u32 n){return es_load(slot,(void *)p,n);}
__declspec(dllexport) u32 SC crc(u32 p,u32 n){return es_crc((void *)p,n);}
'''
  (folder/'probe.c').write_text(cp949_source(source),encoding='utf8')
  mapped,exports=compile_image(folder/'probe.c',folder,0x550000,folder/'probe.dll',['save','load','crc'])
  return mapped,exports,bytes(image),meta

mapped,exports,clone,meta=build()

def fixture():
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000);u.mem_write(0x400000,pe.get_memory_mapped_image());u.mem_write(0x550000,mapped);u.mem_write(0x5e0000,clone);u.mem_map(0x1000000,0x400000)
 w(u,0x460060,GETMODULE);w(u,0x460100,GETPROC);w(u,0x476fd8,0x10a1000);w(u,0x10a1000,0x10a1100);w(u,0x10a1100+0x14,APPFUNC)
 u.q=dict(files={'Steel0.Sav':bytearray(b'original-slot'), 'Steel1.Sav':bytearray(b'other-slot')},handles={},next_handle=100,missing=set(),next_heap=0x10c0000,allocations={},temps=0,writer=None,events=[],fail=set(),short_reads=False,short_writes=False)
 def boundary(u,pc,size,data):
  sp=u.reg_read(UC_X86_REG_ESP);q=u.q
  if pc==GETMODULE:result(u,0x600000,1)
  elif pc==GETPROC:
   key=string(u,r(u,sp+8));result(u,0 if key in q['missing'] else APIS[key],2)
  elif pc==APIS['GetTempFileNameA']:
   if 'temp' in q['fail']:result(u,0,4);return
   q['temps']+=1;p='SEP%03d.tmp'%q['temps'];q['files'][p]=bytearray();u.mem_write(r(u,sp+16),p.encode()+b'\0');q['events'].append(('temp',p));result(u,1,4)
  elif pc==0x4502b6:
   path=string(u,r(u,sp+4));q['events'].append(('native-open',path))
   assert path.startswith('SEP') and path.endswith('.tmp')
   if 'native_open' in q['fail']:result(u,0);return
   q['writer']=path;q['files'][path]=bytearray();w(u,FILE+12,0);result(u,FILE)
  elif pc==0x405720:result(u,123)
  elif pc==APPFUNC:result(u,456)
  elif pc==0x4502c9:
   p,n,count,file=r(u,sp+4),r(u,sp+8),r(u,sp+12),r(u,sp+16);assert file==FILE
   q['files'][q['writer']].extend(u.mem_read(p,n*count));result(u,count)
  elif pc in (0x446760,0x435240,0x449600,0x447e90,0x4226c0):
   assert r(u,sp+4)==FILE
   q['files'][q['writer']].extend(bytes([pc&255])*256)
   if 'native_write' in q['fail']:w(u,FILE+12,r(u,FILE+12)|0x20)
   result(u,1,1 if pc in (0x446760,0x447e90,0x4226c0) else 0)
  elif pc==0x4500f1:q['events'].append(('native-close',q['writer']));result(u,0xffffffff if 'native_close' in q['fail'] else 0)
  elif pc==APIS['CreateFileA']:
   path=string(u,r(u,sp+4));q['events'].append(('open',path))
   if 'open' in q['fail'] or path not in q['files']:result(u,0xffffffff,7);return
   h=q['next_handle'];q['next_handle']+=1;q['handles'][h]=[path,0];result(u,h,7)
  elif pc==APIS['GetFileSize']:result(u,q.get('fake_size',len(q['files'][q['handles'][r(u,sp+4)][0]])),2)
  elif pc==APIS['SetFilePointer']:
   h,position=r(u,sp+4),r(u,sp+8);q['handles'][h][1]=position;result(u,position,4)
  elif pc==APIS['ReadFile']:
   h,p,n,out=r(u,sp+4),r(u,sp+8),r(u,sp+12),r(u,sp+16);path,position=q['handles'][h];data=q['files'][path][position:position+n]
   if q['short_reads'] and data:data=data[:-1]
   u.mem_write(p,bytes(data));q['handles'][h][1]+=len(data);w(u,out,len(data));result(u,0 if 'read' in q['fail'] else 1,5)
  elif pc==APIS['WriteFile']:
   h,p,n,out=r(u,sp+4),r(u,sp+8),r(u,sp+12),r(u,sp+16);path,position=q['handles'][h];data=bytes(u.mem_read(p,n))
   if q['short_writes']:data=data[:max(0,n-1)]
   q['files'][path][position:position+len(data)]=data;q['handles'][h][1]+=len(data);w(u,out,len(data));q['events'].append(('write',len(data)));result(u,0 if 'write' in q['fail'] else 1,5)
  elif pc==APIS['FlushFileBuffers']:q['events'].append(('flush',));result(u,int('flush' not in q['fail']),1)
  elif pc==APIS['CloseHandle']:
   h=r(u,sp+4);q['events'].append(('close',h));q['handles'].pop(h,None);result(u,1,1)
  elif pc==APIS['DeleteFileA']:
   path=string(u,r(u,sp+4));q['events'].append(('delete',path));q['files'].pop(path,None);result(u,1,1)
  elif pc==APIS['MoveFileExA']:
   old,new,flags=string(u,r(u,sp+4)),string(u,r(u,sp+8)),r(u,sp+12);assert flags==9;q['events'].append(('replace',old,new))
   if 'replace' in q['fail']:result(u,0,3);return
   q['files'][new]=q['files'].pop(old);result(u,1,3)
  elif pc==0x450452:
   if 'allocation' in q['fail']:result(u,0);return
   p=q['next_heap'];n=r(u,sp+4);q['next_heap']+=(n+15)&~15;q['allocations'][p]=n;result(u,p)
  elif pc==0x4500e6:q['allocations'].pop(r(u,sp+4));result(u,0)
 u.hook_add(UC_HOOK_CODE,boundary)
 for i,reg in enumerate((UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)):u.reg_write(reg,0x123400+i)
 return u

def call(u,name,*args):
 sp=STACK;w(u,sp,STOP)
 for i,v in enumerate(args):w(u,sp+4+i*4,v)
 u.reg_write(UC_X86_REG_ESP,sp);before=[u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]
 u.emu_start(exports[name],STOP,count=10000000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP and u.reg_read(UC_X86_REG_ESP)==sp+4+4*len(args)
 assert before==[u.reg_read(reg) for reg in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]
 return u.reg_read(UC_X86_REG_EAX)

payload=bytes(range(64))
u=fixture();u.mem_write(DATA,b'123456789');assert call(u,'crc',DATA,9)==zlib.crc32(b'123456789');checks+=1
for n in (4,64,2048,8192):
 u=fixture();data=bytes(i%251 for i in range(n));u.mem_write(DATA,data);other=bytes(u.q['files']['Steel1.Sav'])
 assert call(u,'save',0,DATA,n)==1
 saved=bytes(u.q['files']['Steel0.Sav']);f=struct.unpack('<8I',saved[-32:]);assert f[:4]==(0x58504553,0x31564153,1,n)
 assert f[4]==1296 and f[5]==zlib.crc32(saved[:16]) and f[6]==zlib.crc32(data) and f[7]==zlib.crc32(saved[-32:-4])
 assert saved[1296:-32]==data and bytes(u.q['files']['Steel1.Sav'])==other
 u.mem_write(OUTPUT,b'\xcc'*n);assert call(u,'load',0,OUTPUT,n)==1 and bytes(u.mem_read(OUTPUT,n))==data
 assert not u.q['handles'] and not u.q['allocations']
 assert not any(p.startswith('SEP') for p in u.q['files']);checks+=1
 # Legitimate editor edits to the native body do not invalidate own metadata.
 u.q['files']['Steel0.Sav'][200]^=1;assert call(u,'load',0,OUTPUT,n)==1;checks+=1

for fault in ('temp','native_open','native_write','native_close','open','write','flush','replace'):
 u=fixture();u.mem_write(DATA,payload);before={p:bytes(v) for p,v in u.q['files'].items()};u.q['fail'].add(fault)
 assert call(u,'save',0,DATA,64)==0,fault
 assert {p:bytes(v) for p,v in u.q['files'].items()}==before,fault
 assert not u.q['handles'],fault;checks+=1
u=fixture();u.mem_write(DATA,payload);u.q['short_writes']=True;before=bytes(u.q['files']['Steel0.Sav'])
assert call(u,'save',0,DATA,64)==0 and bytes(u.q['files']['Steel0.Sav'])==before;checks+=1

for slot,n in ((6,64),(0xffffffff,64),(0,0),(0,8196),(0,3)):
 u=fixture();u.mem_write(DATA,payload);assert call(u,'save',slot,DATA,n)==0 and not u.q['events'];checks+=1

# Appendix must fit within the existing editor's64MiB whole-save limit.
for size in (64*1024*1024-64-31,64*1024*1024,0xffffffff):
 u=fixture();u.mem_write(DATA,payload);u.q['fake_size']=size;before=bytes(u.q['files']['Steel0.Sav'])
 assert call(u,'save',0,DATA,64)==0 and bytes(u.q['files']['Steel0.Sav'])==before
 assert not u.q['handles'];checks+=1

for corruption in ('payload','header','footer','version','length','size','short_read','read','allocation'):
 u=fixture();u.mem_write(DATA,payload);assert call(u,'save',0,DATA,64)==1
 b=u.q['files']['Steel0.Sav']
 if corruption=='payload':b[-33]^=1
 elif corruption=='header':b[0]^=1
 elif corruption=='footer':b[-1]^=1
 elif corruption=='version':struct.pack_into('<I',b,len(b)-24,99)
 elif corruption=='length':struct.pack_into('<I',b,len(b)-20,68)
 elif corruption=='size':del b[500:504]
 elif corruption=='short_read':u.q['short_reads']=True
 else:u.q['fail'].add(corruption)
 u.mem_write(OUTPUT,b'\xcc'*64);assert call(u,'load',0,OUTPUT,64)==0xffffffff,corruption
 assert bytes(u.mem_read(OUTPUT,64))==b'\xcc'*64 and not u.q['allocations'] and not u.q['handles'];checks+=1

u=fixture();u.q['files']['Steel0.Sav']=bytearray(b'legacy'*200);u.mem_write(OUTPUT,b'\xcc'*64)
assert call(u,'load',0,OUTPUT,64)==0 and bytes(u.mem_read(OUTPUT,64))==b'\xcc'*64;checks+=1
u=fixture();u.q['missing'].add('MoveFileExA');assert call(u,'save',0,DATA,64)==0 and not u.q['events'];checks+=1

# The game's real fwrite core sets FILE._flag bit20 on short/error OS writes.
for written,expected in ((4096,4096),(2048,2048),(0xffffffff,0)):
 u=fixture();u.mem_write(DATA,b'x'*4096);w(u,FILE+12,0);w(u,FILE+16,1)
 def low_write(u,pc,size,data):
  if pc==0x452215:result(u,written)
 u.hook_add(UC_HOOK_CODE,low_write)
 w(u,STACK,STOP)
 for i,value in enumerate((DATA,1,4096,FILE)):w(u,STACK+4+i*4,value)
 u.reg_write(UC_X86_REG_ESP,STACK);u.emu_start(0x4502f8,STOP,count=100000)
 assert u.reg_read(UC_X86_REG_EIP)==STOP and u.reg_read(UC_X86_REG_ESP)==STACK+4
 assert u.reg_read(UC_X86_REG_EAX)==expected
 assert bool(r(u,FILE+12)&0x20)==(written!=4096);checks+=1

os_checks=0
if os.name=='nt':
 # Run real Win32 atomic replacement in an owned temporary folder, never the game.
 with tempfile.TemporaryDirectory(prefix='SteelExpeditionWin32-') as temp:
  folder=Path(temp)
  header=(ROOT/'expedition_storage.h').read_text(encoding='utf8').replace('(Allocate)0x450452','(Allocate)heap_alloc').replace('(Release)0x4500e6','(Release)heap_free')
  (folder/'expedition_storage.h').write_text(header,encoding='utf8')
  source=r'''
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned int u32;
#define SC __attribute__((stdcall))
#define PTR(a) ((u32)(a))
typedef u32 (SC *F1)(u32);typedef u32 (SC *F2)(u32,u32);typedef u32 (SC *F3)(u32,u32,u32);typedef u32 (SC *F4)(u32,u32,u32,u32);
typedef u32 (*Allocate)(u32);typedef void (*Release)(u32);
static const char *names[]={"Steel0.Sav","Steel1.Sav","Steel2.Sav","Steel3.Sav","Steel4.Sav","Steel5.Sav"};
static u32 mapped(u32 a){if(a==0x460060)return PTR(GetModuleHandleA);if(a==0x460100)return PTR(GetProcAddress);if(a>=0x469060&&a<0x469078)return PTR(names[(a-0x469060)/4]);return 0;}
#define V(a) mapped(a)
static u32 heap_alloc(u32 n){return PTR(malloc(n));}static void heap_free(u32 p){free((void *)p);}
static int fail_native;
static u32 write_native(u32 slot,const char *path){FILE *f=fopen(path,"wb");unsigned char data[1296];if(!f)return 0;memset(data,'A',sizeof(data));size_t n=fwrite(data,1,fail_native?8:sizeof(data),f);int result=fclose(f);return !fail_native&&n==sizeof(data)&&result==0;}
#define E_NATIVE_SAVE ((u32)write_native)
#include "expedition_storage.h"
static int count;
#define CHECK(x) do{count++;if(!(x)){printf("FAIL Win32 line%d error%lu\n",__LINE__,GetLastError());return 1;}}while(0)
static int exact(const char *name,const char *text){char b[100]={0};FILE *f=fopen(name,"rb");if(!f)return 0;size_t n=fread(b,1,sizeof(b),f);fclose(f);return n==strlen(text)&&!memcmp(b,text,n);}
int main(void){
 unsigned int state[16],out[16];FILE *f;HANDLE lock;WIN32_FIND_DATAA found;HANDLE search;int i;
 for(i=0;i<16;i++)state[i]=i+10;
 f=fopen(names[0],"wb");CHECK(f!=0);CHECK(fwrite("ORIGINAL",1,8,f)==8);CHECK(fclose(f)==0);
 lock=CreateFileA(names[0],GENERIC_READ,FILE_SHARE_READ,0,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,0);CHECK(lock!=INVALID_HANDLE_VALUE);
 CHECK(es_save(0,state,sizeof(state))==0);CHECK(CloseHandle(lock));CHECK(exact(names[0],"ORIGINAL"));
 fail_native=1;CHECK(es_save(0,state,sizeof(state))==0);CHECK(exact(names[0],"ORIGINAL"));fail_native=0;
 CHECK(es_save(0,state,sizeof(state))==1);memset(out,0,sizeof(out));CHECK(es_load(0,out,sizeof(out))==1);CHECK(!memcmp(out,state,sizeof(out)));
 f=fopen(names[0],"r+b");CHECK(f!=0);CHECK(fseek(f,200,SEEK_SET)==0);CHECK(fputc('B',f)!=EOF);CHECK(fclose(f)==0);CHECK(es_load(0,out,sizeof(out))==1);
 f=fopen(names[0],"r+b");CHECK(f!=0);CHECK(fseek(f,1296,SEEK_SET)==0);CHECK(fputc('Z',f)!=EOF);CHECK(fclose(f)==0);memset(out,0xcc,sizeof(out));CHECK(es_load(0,out,sizeof(out))==-1);CHECK(out[0]==0xccccccccu);
 CHECK(es_save(0,state,sizeof(state))==1);f=fopen(names[0],"r+b");CHECK(f!=0);CHECK(fseek(f,0,SEEK_END)==0);CHECK(ftell(f)==1296+sizeof(state)+32);CHECK(fclose(f)==0);
 CHECK(write_native(1,names[1])==1);CHECK(es_load(1,out,sizeof(out))==0);
 search=FindFirstFileA("SEP*.tmp",&found);CHECK(search==INVALID_HANDLE_VALUE);
 printf("PASS real Windows storage: %d checks\n",count);return 0;
}
'''
  (folder/'win32.c').write_text(source,encoding='ascii')
  compile_result=subprocess.run([str(ZIG),'cc','-target','x86-windows-gnu','-O1',str(folder/'win32.c'),'-o',str(folder/'win32.exe'),'-lkernel32'],capture_output=True,text=True,encoding='utf8',errors='replace')
  assert compile_result.returncode==0,compile_result.stdout+compile_result.stderr
  executed=subprocess.run([str(folder/'win32.exe')],cwd=folder,capture_output=True,text=True)
  assert executed.returncode==0,executed.stdout+executed.stderr
  print(executed.stdout.strip());os_checks=int(re.search(r'(\d+) checks',executed.stdout).group(1))

report=dict(status='passed',cases=checks,real_windows_checks=os_checks,native_sha256=hashlib.sha256(native).hexdigest(),
 coverage=['Actual native401160 save clone with alternate path/cdecl/nonvolatile registers','Real native4502f8 fwrite core sets sticky error on short/failing OS write',
 'Open, sticky native write error, close, short write, flush and replace rollback',
 'CRC32 and4..8192byte appendix roundtrip, version/size/header/payload corruption, old-save fallback, output unchanged on errors',
 'Ordinary editor body edits preserve appendix compatibility; no real user save was opened for writing'],
 scoped_mocks=['OS file APIs in memory, native world serialization callees with deterministic1296byte native prefix'],
 not_checked=['Hardware disk failure','Full native world serialization/UI flow'])
(ROOT/'test-expedition-storage-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PASS expedition storage:',checks,'native clone/file transaction/appendix fault cases')
