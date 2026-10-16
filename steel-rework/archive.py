from pathlib import Path
import struct,json
SRC=Path(r'D:\Games\DGGL\Games\EoSteel_Win')
ROOT=Path(__file__).resolve().parent
def entries(b):
 pos,n=struct.unpack_from('<II',b,len(b)-9)
 for _ in range(n):
  nl,flag=b[pos:pos+2]; off,size,raw=struct.unpack_from('<III',b,pos+2)
  name=b[pos+14:pos+14+nl].decode('cp949'); pos+=15+nl
  yield name,flag,off,size,raw
def decode(b):
 out=bytearray(); p=0
 while p<len(b):
  flags=b[p]; p+=1
  for bit in range(8):
   if p>=len(b):break
   if flags&(1<<bit):
    x=b[p]|b[p+1]<<8;p+=2
    d=x&4095;n=(x>>12)+2
    if not d or d>len(out):raise ValueError((p,d,len(out)))
    for _ in range(n):out.append(out[-d])
   else:out.append(b[p]);p+=1
 return out
if __name__=='__main__':
 for pak in ['Data.pak','patch102.pak','patch103.pak']:
  b=(SRC/pak).read_bytes(); folder=ROOT/'extracted'/pak;folder.mkdir(parents=True,exist_ok=True)
  for name,flag,off,size,raw in entries(b):
   data=decode(b[off:off+size]) if flag else b[off:off+size]
   assert len(data)==raw,(name,len(data),raw)
   (folder/name).write_bytes(data)
   print(pak,name,len(data))
