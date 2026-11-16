"""Observe real ruin script entry without replacing the original story."""
import struct

ENTRY=0x4498f5
PATCH_SITES={ENTRY:bytes.fromhex('8b4c240c51')}
RUINS=(('카푸아유적',20),('펠라유적',41),('케브유적',52),('고대유적',0))

def emit(put,asm,address,patch,exports):
    def code(source):return put(asm(source,address()))
    names=[put(name.encode('cp949')+b'\0') for name,_ in RUINS]
    table=put(struct.pack('<4I',*names))
    callback=exports['we_ruin_visit']
    if isinstance(callback,str):callback=int(callback,0)
    resolver=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      mov ebx,[ebp+8]; test ebx,ebx; jz done;
      cmp dword ptr [ebx+0x1d8],0; jne done;
      cmp dword ptr [ebx+0x1cc],0; je done;
      mov eax,[ebx+0x1d0]; test eax,eax; jz done;
      mov edx,[ebp+12]; cmp edx,[eax+0x14]; jae done;
      mov eax,[ebx+0x1d4]; test eax,eax; jz done;
      imul edx,edx,36; add eax,edx; mov [ebp+12],eax;
      xor edi,edi;
    next_name:
      mov esi,[ebp+12]; mov edx,[edi*4+{table}]; mov ecx,32;
    compare:
      mov al,[esi]; cmp al,[edx]; jne different;
      test al,al; je found;
      inc esi; inc edx; dec ecx; jnz compare;
    different:
      inc edi; cmp edi,4; jb next_name; jmp done;
    found:
      push edi; push ebx; call {callback};
    done:
      pop edi; pop esi; pop ebx; pop ebp; ret 8;
    ''')
    hook=code(f'''
      pushfd; pushad;
      cmp dword ptr [esp+48],4; jne skip;
      push eax; push esi; call {resolver};
    skip:
      popad; popfd;
      mov ecx,[esp+0xc]; push ecx; jmp 0x4498fa;
    ''')
    assert asm('mov ecx,[esp+0xc];push ecx',ENTRY)==PATCH_SITES[ENTRY]
    patch(ENTRY,PATCH_SITES[ENTRY],asm(f'jmp {hook}',ENTRY))
    return dict(hook=hex(hook),resolver=hex(resolver),callback=hex(callback),
                native_named_entry='0x4498d0',native_entry_dispatch='0x449910',
                ruins=[dict(index=i,name=name,town=town) for i,(name,town) in enumerate(RUINS)],
                visit_context='Script parent is DWORD0; world contact army is DWORD+0x1e0. City parent+0x50 is town.',
                safety='Observe successful mode4 named-entry resolution only when no script is already running; original execution and story variables remain unchanged.')
