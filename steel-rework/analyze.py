from pathlib import Path
import sys, re, struct
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'tools/python-deps'))
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
SRC=Path(r'D:\Games\DGGL\Games\EoSteel_Win')
b=(SRC/'SteelEmpire.exe').read_bytes(); pe=pefile.PE(data=b)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
lines=[]
for s in pe.sections:
 if s.Characteristics & 0x20000000:
  lines.extend(f'{a:08x} {m:8} {o}' for a,z,m,o in md.disasm_lite(s.get_data(),pe.OPTIONAL_HEADER.ImageBase+s.VirtualAddress))
(ROOT/'disassembly.txt').write_text('\n'.join(lines),encoding='utf-8')
for m in re.finditer(rb'[\x20-\x7e\x80-\xff]{4,}',b):
 t=m.group().decode('cp949',errors='replace')
 if any(x in t.lower() for x in ['.dat','.pak','구입','구매','병종','비행','탱크','ddraw','direct','생산']):
  print(hex(pe.OPTIONAL_HEADER.ImageBase+pe.get_rva_from_offset(m.start())),repr(t))
print('IMPORTS',[(x.dll.decode(),[i.name.decode() if i.name else i.ordinal for i in x.imports]) for x in pe.DIRECTORY_ENTRY_IMPORT])
