from build import *
b=(ROOT/'package/SteelEmpire.exe').read_bytes();p=pefile.PE(data=b)
for term in ['돈을','고용','포커']:
 start=0
 while True:
  pos=b.find(term.encode('cp949'),start)
  if pos<0:break
  lo=b.rfind(b'\0',max(0,pos-160),pos)+1;hi=b.find(b'\0',pos)
  print(hex(0x400000+p.get_rva_from_offset(lo)),b[lo:hi].decode('cp949',errors='replace'));start=hi+1
