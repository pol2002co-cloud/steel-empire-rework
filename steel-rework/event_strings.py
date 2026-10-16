from build import *
sys.stdout.reconfigure(encoding='utf-8');b=(ROOT/'package/SteelEmpire.exe').read_bytes();p=pefile.PE(data=b)
for term in ['이벤트','event','Event','시빌라이트','밀레니엄']:
 start=0
 for k in range(10):
  pos=b.find(term.encode('cp949'),start)
  if pos<0:break
  lo=b.rfind(b'\0',max(0,pos-160),pos)+1;hi=b.find(b'\0',pos)
  print(hex(0x400000+p.get_rva_from_offset(lo)),b[lo:hi].decode('cp949',errors='replace')[:150]);start=hi+1
