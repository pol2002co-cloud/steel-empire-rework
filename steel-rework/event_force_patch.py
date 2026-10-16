"""Opt-in, one-shot initial event condition override; never reset story flags."""
from pathlib import Path
import struct
from event_decode import decode_script, GLOBALS

ROOT=Path(__file__).resolve().parent
MAGIC_ADDR=0x48d398+98*4
MASK_ADDR=0x48d398+99*4
MAGIC=0x45564631
TRIGGERS=[('동방제국',19,3),('아시레마',715,4),('베브',180,5),
          ('포룸',3826,6),('사키로',177,7),('카란토',1969,8),
          ('포룸',1552,9),('샤르데나',555,10),('포룸',250,11)]

def emit(put,asm,address,patch):
    # All original scripts declare precisely 31 globals. Slots 98/99 are in
    # the existing 100-dword save block, outside every declared script field.
    assert len(GLOBALS)==31
    scripts=[]
    for p in (ROOT/'extracted/patch102.pak').glob('*.cmp'):
        blob=p.read_bytes();assert struct.unpack_from('<I',blob,8)[0]==31
        scripts.append((p.stem,blob,decode_script(p)))
    records=[];meta=[]
    for name,start,flag in TRIGGERS:
        blob=next(b for n,b,r in scripts if n==name)
        row=next(r for n,b,rows in scripts if n==name for r in rows if r['addr']==start)
        assert row['text'].startswith('IF ') and GLOBALS[flag]+' == 0' in row['text']
        end=row['end']-1  # EAX points at relative-jump word at the hook.
        signature=blob[start*4:(end+1)*4]
        matches=[(n,r['addr']) for n,b,rows in scripts for r in rows
                 if r['end']-1==end and b[start*4:(end+1)*4]==signature]
        assert matches==[(name,start)],matches
        sig=put(signature);records.append((start*4,end*4,len(signature),sig,flag))
        meta.append(dict(script=name,start=start,end=end,flag=flag))
    table=put(b''.join(struct.pack('<5I',*r) for r in records))
    resolver=put(asm(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      cmp dword ptr [{MAGIC_ADDR}],{MAGIC}; jne original;
      mov ebx,[{MASK_ADDR}]; and ebx,511; jz original;
      mov edx,[ebp+8]; mov edx,[edx+0x1cc]; test edx,edx; jz original;
      mov eax,[ebp+12]; sub eax,edx;
      mov esi,{table}; mov ecx,9;
    search: cmp eax,[esi+4]; je compare;
    next: add esi,20; dec ecx; jnz search; jmp original;
    compare: push ecx; push esi; push edx; push eax;
      mov edi,[esi+12]; mov ecx,[esi+8]; mov esi,[esi]; add esi,edx;
      cld; repe cmpsb;
      pop eax; pop edx; pop esi; pop ecx; jne next;
      mov ecx,[esi+16]; sub ecx,3; mov eax,1; shl eax,cl;
      test ebx,eax; jz original;
      cmp dword ptr [ecx*4+0x48d3a4],0; jne consume_old;
      cmp dword ptr [0x48d3e4],0; jne original;
      not eax; and dword ptr [{MASK_ADDR}],eax;
      mov eax,1; jmp done;
    consume_old: not eax; and dword ptr [{MASK_ADDR}],eax;
    original: mov eax,[ebp+16];
    done: pop edi; pop esi; pop ebx; pop ebp; ret 12
    ''',address()))
    hook=put(asm(f'''
      mov ecx,[eax]; mov edx,[esp+0x10];
      pushfd; pushad; push edx; push eax; push esi; call {resolver};
      mov [esp+20],eax; popad; popfd; jmp 0x44a49a
    ''',address()))
    patch(0x44a494,asm('mov ecx,[eax];mov edx,[esp+0x10]',0x44a494),asm(f'jmp {hook}',0x44a494)+b'\x90')
    return dict(resolver=hex(resolver),hook=hex(hook),magic_address=hex(MAGIC_ADDR),mask_address=hex(MASK_ADDR),magic=hex(MAGIC),triggers=meta)
