from build import *
b=(ROOT/'package/SteelEmpire.exe').read_bytes();p=pefile.PE(data=b)
for addr in [0x46ad50,0x470404,0x470a74,0x473840]:
 needle=struct.pack('<I',addr);start=0
 while (pos:=b.find(needle,start))>=0:
  print(hex(addr),'ref',hex(0x400000+p.get_rva_from_offset(pos)),b[max(0,pos-20):pos+24].hex());start=pos+4
