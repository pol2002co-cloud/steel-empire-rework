from test_patch import *
import ctypes
STOP=0x13df000;WIDE=0x1001000;PTR=0x1000000;API=0x13de000
win=ctypes.WinDLL('kernel32',use_last_error=True)
convert=win.WideCharToMultiByte
convert.argtypes=[ctypes.c_uint,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p]
convert.restype=ctypes.c_int
oldpe=pefile.PE(str(ROOT/'SteelEmpire-v082.exe'))

def ui_strings():
 out=[]
 for typ in pe.DIRECTORY_ENTRY_RESOURCE.entries:
  if typ.struct.Id!=5:continue
  for entry in typ.directory.entries:
   for lang in entry.directory.entries:
    d=lang.data.struct;b=pe.get_data(d.OffsetToData,d.Size)
    def word(p):return struct.unpack_from('<H',b,p)[0]
    def field(p):
     if word(p)==0:return p+2
     if word(p)==65535:return p+4
     start=p
     while word(p):p+=2
     out.append(b[start:p].decode('utf-16le'));return p+2
    ext=word(2)==65535
    if ext:style=struct.unpack_from('<I',b,12)[0];count=word(16);p=26
    else:style=struct.unpack_from('<I',b)[0];count=word(8);p=18
    for _ in range(3):p=field(p)
    if style&64:p=field(p+(6 if ext else 2))
    for _ in range(count):
     p=(p+3)&~3;p+=24 if ext else 18
     p=field(p);p=field(p);extra=word(p);p+=2+extra
    assert p<=len(b),(entry.struct.Id,p,len(b))
 return sorted(set(out))

def run(text,acp,old=False):
 u=setup()
 if old:u.mem_write(0x400000,oldpe.get_memory_mapped_image())
 raw=(text+'\0').encode('utf-16le');u.mem_write(WIDE,raw);w(u,PTR,WIDE);w(u,0x460034,API)
 u.mem_write(0x487fdc,b'\xcc'*512);calls=[]
 def hook(u,a,n,data):
  if a==STOP:u.emu_stop()
  elif a==API:
   sp=u.reg_read(UC_X86_REG_ESP);args=[r(u,sp+4+i*4) for i in range(8)]
   cp,flags,src,length,dest,cap,default,used=args
   assert length==0xffffffff and flags==0 and default==used==0
   calls.append(cp);buf=ctypes.create_string_buffer(cap)
   source=ctypes.create_string_buffer(raw)
   got=convert(cp or acp,flags,ctypes.addressof(source),-1,ctypes.addressof(buf),cap,None,None)
   if got:u.mem_write(dest,buf.raw[:got])
   u.reg_write(UC_X86_REG_EAX,got);ret(u,32)
 u.hook_add(UC_HOOK_CODE,hook);sp=0x13f0000;w(u,sp,STOP);w(u,sp+4,PTR)
 regs=[UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_EBX]
 for reg in regs:u.reg_write(reg,0x12345678)
 u.emu_start(0x411200,0,count=30000)
 assert u.reg_read(UC_X86_REG_ESP)==sp+8 and u.reg_read(UC_X86_REG_EIP)==STOP
 for reg in regs:assert u.reg_read(reg)==0x12345678
 if len(text)>255:assert not calls and u.reg_read(UC_X86_REG_EAX)==0;return None
 assert r(u,PTR)==WIDE+len(raw) and u.reg_read(UC_X86_REG_EAX)==0x487fdc
 data=bytes(u.mem_read(0x487fdc,512));return data,calls

strings=ui_strings()+['','ASCII 0123','한글 대화 선택창 테스트','마리에 #s포룸#n @w', '가'*255]
reproduced=0
for text in strings:
 expected=text.encode('cp949',errors='replace')+b'\0'
 for cp in [949,1252,65001]:
  output,calls=run(text,cp)
  assert calls==[949] and output[:len(expected)]==expected
  assert output[len(expected):]==b'\xcc'*(512-len(expected))
  before,_=run(text,cp,True)
  if cp==949:assert before==output
  elif before!=output:reproduced+=1
run('가'*256,65001)
# Only one 10-byte conversion call site plus the appended trampoline changes.
old=(ROOT/'SteelEmpire-v082.exe').read_bytes();op=oldpe
allowed=set(range(pe.get_offset_from_rva(0x11231),pe.get_offset_from_rva(0x11231)+10))
a=pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');allowed.update(range(a,a+4))
a=pe.sections[-1].get_file_offset();allowed.update(range(a,a+40))
allowed.update(range(op.sections[-1].PointerToRawData+op.sections[-1].Misc_VirtualSize,len(old)))
assert {i for i in range(len(old)) if old[i]!=binary[i]}<=allowed
assert reproduced>0 and pe.verify_checksum()
print(f'PASS {len(strings)} actual UI/resource/boundary strings under ACP 949/1252/65001; {reproduced} original mismatches reproduced; byte-exact CP949 output, original Korean behavior, buffer guards, pointer advancement, ABI and v082 isolation')
