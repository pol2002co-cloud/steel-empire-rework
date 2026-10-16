from build import *
b=(ROOT/'package/SteelEmpire.exe').read_bytes();p=pefile.PE(data=b)
for s in ['브라보','니케','bravo','nike','Bravo','Nike']:
 for enc in ['cp949','utf-16le']:
  pos=b.find(s.encode(enc))
  if pos>=0: print(s,enc,hex(0x400000+p.get_rva_from_offset(pos)),repr(b[pos-25:pos+70]))
