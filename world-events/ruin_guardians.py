"""Authored annual guardian formations; only ordinary native equipment records."""
import struct
from collections import Counter

RUIN_NAMES=('카푸아유적','펠라유적','케브유적','고대유적')
CLASS_NAMES={3:'중보병',4:'장갑척탄병',5:'해병',6:'장갑보병',7:'중장갑보병'}
MACHINE_NAMES={2:'그리폰MK5',4:'와이번MK2',5:'와이번MK4',12:'유니콘',13:'레드울프',14:'드레드노트',16:'키클롭스',22:'그런트',23:'나이트호크',24:'A.S.6'}
# Native4199fd/461384 reserves eighteen foot cells for the seven-tank formation.
ARMOR_SLOTS=(39,10,13,16,64,67,70)
AIR_SLOTS=(39,10,13,16,37,43,64,67,70)
MIXED_FOOT_SLOTS=(27,28,29,33,34,35,36,37,38,42,43,44,45,46,47,51,52,53)
INFANTRY_SLOTS=(39,)+tuple(i for i in range(81) if i not in (39,41))

_PATTERNS=(((6,38),(6,38),(3,46),(4,42)),
           ((5,44),(5,44),(6,38),(4,42)),
           ((4,42),(4,42),(6,38),(3,46)),
           ((6,38),(5,44),(4,42)))
_AIR=((5,5,5,5,5,2,2,22,22),
      (23,23,23,23,4,4,4,2,2),
      (5,2,2,2,2,5,5,24,24),
      (24,24,24,23,23,22,22,2,2))
_ARMOR=((13,13,13,13,14,14,16),
        (13,13,13,12,12,14,16),
        (13,13,13,16,16,14,14),
        (13,13,13,12,14,14,16))
_MIXED=(((7,40),)*12+((4,43),)*6,
        ((5,45),)*8+((7,40),)*6+((4,43),)*4,
        ((4,43),)*10+((7,40),)*8,
        ((5,45),)*6+((7,40),)*6+((6,46),)*6)

def _summary(g):
 pieces=[]
 for ident,count in Counter(g['machines']).items():pieces.append(MACHINE_NAMES[ident]+' '+str(count)+'대')
 for job,count in Counter(job for job,weapon in g['foot']).items():pieces.append(CLASS_NAMES[job]+' '+str(count)+'명')
 return 'Lv'+str(g['level'])+' / '+' · '.join(pieces)+' / 보스형 제외'

GUARDIANS=[]
for ruin in range(4):
 for stage in range(1,4):
  foot=((7,38),)+tuple(_PATTERNS[ruin][i%len(_PATTERNS[ruin])] for i in range(79)) if stage==1 else _MIXED[ruin] if stage==3 else ()
  machines=_AIR[ruin] if stage==2 else _ARMOR[ruin] if stage==3 else ()
  g=dict(profile=6+ruin*3+stage-1,ruin=ruin,stage=stage,level=20+stage*10,
         army_type=(0,2,1)[stage-1],name=RUIN_NAMES[ruin]+' '+str(stage)+'단계 수호대',foot=foot,machines=machines)
  g['summary']=_summary(g);GUARDIANS.append(g)
GUARDIANS=tuple(GUARDIANS)

def _validate():
 assert len(GUARDIANS)==12 and len(INFANTRY_SLOTS)==80
 assert len(set(INFANTRY_SLOTS))==80 and len(set(MIXED_FOOT_SLOTS))==18
 assert set(ARMOR_SLOTS).isdisjoint(MIXED_FOOT_SLOTS)
 for g in GUARDIANS:
  assert g['profile']==6+g['ruin']*3+g['stage']-1
  assert g['level']=={1:30,2:40,3:50}[g['stage']]
  assert len(g['foot'])=={1:80,2:0,3:18}[g['stage']]
  assert len(g['machines'])=={1:0,2:9,3:7}[g['stage']]
  assert all(ident in MACHINE_NAMES and not 17<=ident<=21 for ident in g['machines'])
  allowed={38:{6,7},40:{6,7},42:{4},43:{4},44:{5},45:{5},46:{1,2,3,4,5,6,7}}
  assert all(job in allowed.get(weapon,set()) for job,weapon in g['foot'])
_validate()

def generate_header():
 def quoted(text):return '"'+''.join('\\%03o'%b for b in text.encode('cp949'))+'"'
 rows=[]
 for g in GUARDIANS:
  rows.append('{'+','.join([quoted(g['name']),quoted(g['summary'])]+[str(g[k])+'u' for k in ('profile','level')]+[str(len(g[k]))+'u' for k in ('foot','machines')])+'}')
 return '/* Authored guardian previews; no original game resources. */\nstatic const EXGuardian EX_GUARDIANS[12]={\n'+',\n'.join(rows)+'\n};\n'

def emit(put,code,person,destroy,temp_magic):
 records=[]
 for g in GUARDIANS:
  slots=INFANTRY_SLOTS if g['stage']==1 else MIXED_FOOT_SLOTS
  foot=put(b''.join(struct.pack('<3I',slot,job,weapon) for slot,(job,weapon) in zip(slots,g['foot']))) if g['foot'] else 0
  slots=AIR_SLOTS if g['stage']==2 else ARMOR_SLOTS
  vehicles=put(b''.join(struct.pack('<3I',slot,(slot//27)*3+(slot%9)//3,ident) for slot,ident in zip(slots,g['machines']))) if g['machines'] else 0
  records.extend((g['level'],g['army_type'],len(g['machines']),vehicles,len(g['foot']),foot))
 table=put(struct.pack('<%dI'%len(records),*records))
 helper=code(f'''
   push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,12;
   mov eax,[ebp+12]; sub eax,6; cmp eax,11; ja invalid;
   imul eax,eax,24; add eax,{table}; mov [ebp-16],eax;
   push 0x55b0; call 0x450452; add esp,4;
   test eax,eax; jz invalid;
   mov esi,eax; mov edi,eax; xor eax,eax; mov ecx,0x156c; cld; rep stosd;
   mov dword ptr [esi],12; mov eax,[ebp+8]; mov [esi+4],eax;
   mov dword ptr [esi+0x14],15; mov dword ptr [esi+0x55ac],{temp_magic};
   mov eax,[ebp-16]; mov eax,[eax+4]; mov [esi+0x18],eax;
   xor ebx,ebx;
 vehicles:
   mov eax,[ebp-16]; cmp ebx,[eax+8]; jae foot_begin;
   mov edi,ebx; imul edi,edi,12; add edi,[eax+12];
   mov ecx,10; cmp dword ptr [eax+4],2; jne crew; mov ecx,9;
 crew:
   push 0; push dword ptr [eax]; push ecx; push dword ptr [edi]; push esi; call {person};
   test eax,eax; jz failed; mov [ebp-20],eax;
   push dword ptr [edi+8]; mov ecx,[0x4880f0]; call 0x416660;
   test eax,eax; jz failed;
   mov [ebp-24],eax; mov edx,[edi+4]; mov [esi+edx*4+0x3c],eax;
   mov dword ptr [eax],15; inc dword ptr [esi+0x20];
   cmp dword ptr [eax+8],0; jne bind; inc dword ptr [esi+0x24];
 bind:
   push 0; push dword ptr [ebp-20]; push eax; call 0x4168b0; add esp,12;
   mov eax,[ebp-24]; mov edx,[ebp-20]; cmp [eax+0x8c],edx; jne failed;
   inc ebx; jmp vehicles;
 foot_begin:
   xor ebx,ebx;
 foot:
   mov eax,[ebp-16]; cmp ebx,[eax+16]; jae ready;
   mov edi,ebx; imul edi,edi,12; add edi,[eax+20];
   push dword ptr [edi+8]; push dword ptr [eax]; push dword ptr [edi+4]; push dword ptr [edi]; push esi; call {person};
   test eax,eax; jz failed; inc ebx; jmp foot;
 ready:
   mov eax,esi; jmp done;
 failed:
   push esi; call {destroy};
 invalid:
   xor eax,eax;
 done:
   add esp,12; pop edi; pop esi; pop ebx; pop ebp; ret 12;
 ''')
 return helper

if __name__=='__main__':
 _validate();header=generate_header();header.encode('ascii');assert header.count('u,')>12
 print('PASS guardian catalogue:12 authored profiles, fixed30/40/50, legal weapon classes, ordinary equipment and bounded formations')
