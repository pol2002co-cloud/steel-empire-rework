"""Read-only decoder of the game's compiled script format."""
from pathlib import Path
import struct,re,json
ROOT=Path(__file__).resolve().parent
CFG=(ROOT/'extracted/patch102.pak/script.cfg').read_text(encoding='cp949')
GLOBALS=[s.strip() for s in CFG.splitlines() if s.strip() and not s.startswith('//') and '(' not in s]
FUNCS=[(m[1], [s.strip() for s in m[2].split(',') if s.strip()]) for m in re.finditer(r'(\w+)\(\s*(.*?)\s*\)',CFG)]
def decode_script(path):
 b=path.read_bytes();w=list(struct.unpack('<%dI'%(len(b)//4),b));h=w[:8]
 assert b[:4]==b'COMP'
 labels={w[8+9*i+8]:b[32+36*i:64+36*i].split(b'\0')[0].decode('cp949') for i in range(h[5]) if w[8+9*i+8]!=0xffffffff}
 def value(p):
  t=w[p];v=w[p+1];sign='-' if t&128 else '';t&=127
  if t==5:
   e=b.index(0,(p+1)*4);s=b[(p+1)*4:e].decode('cp949');return repr(s), ((e+3)//4)+1
  if t==1:return sign+str(v if v<0x80000000 else v-0x100000000),p+2
  if t==2:return sign+'local'+str(v),p+2
  if t==16:return sign+GLOBALS[v],p+2
  raise ValueError((path.name,p,t))
 p=8+9*h[5];out=[]
 while p<len(w):
  a=p;op=w[p];p+=1
  if op>=0x8000:
   name,args=FUNCS[op-0x8000];vals=[]
   for _ in args:v,p=value(p);vals.append(v)
   s=name+'('+', '.join(vals)+')'
  elif op==17:s='entry '+str(w[p]);p+=1
  elif op==18:s='return'
  elif op==0:s='nop'
  elif op==1:
   dst,p=value(p);src,p=value(p);s=dst+' = '+src
   while w[p]!=65535:
    oper=w[p];v,p=value(p+1);s+=' '+{1:'+',2:'-',3:'*',4:'/'}[oper]+' '+v
   p+=1
  elif op==2:
   parts=[]
   while True:
    lhs,p=value(p);oper=w[p];rhs,p=value(p+1);parts.append(lhs+' '+{3:'!=',4:'==',5:'<',6:'>',7:'<=',8:'>='}[oper]+' '+rhs)
    join=w[p];p+=1
    if join==65535:break
    parts.append({1:'OR',2:'AND'}[join])
   s='IF '+' '.join(parts)+' GOTO '+str(p+w[p]);p+=1
  elif op==3:s='GOTO '+str(p+w[p]+1);p+=1
  else:raise ValueError((path.name,p,op))
  out.append(dict(addr=a,end=p,label=labels.get(a),text=s))
 return out
if __name__=='__main__':
 dest=ROOT/'event-analysis';dest.mkdir(exist_ok=True)
 for f in (ROOT/'extracted/patch102.pak').glob('*.cmp'):
  rows=decode_script(f)
  (dest/(f.stem+'.txt')).write_text('\n'.join((('\n['+r['label']+']\n') if r['label'] else '')+f"{r['addr']:05d}: {r['text']}" for r in rows),encoding='utf-8')
 print('Decoded',len(list(dest.glob('*.txt'))),'scripts')

