def emit(put,asm,address,patch):
    prepare=put(asm('''
      pushfd; pushad; mov ebx,ebp; mov eax,[esp+0x48]; sub esp,24;
      mov [esp+20],eax; xor eax,eax;
      mov [esp],eax; mov [esp+4],eax; mov [esp+8],eax;
      lea eax,[ebx+0x228]; mov [esp+12],eax; mov dword ptr [esp+16],81;
    unit_loop:
      mov eax,[esp+12]; mov ebp,[eax]; test ebp,ebp; jz next_unit;
      cmp dword ptr [ebp+0x138],0; je next_unit;
      mov edi,[esp+20]; lea edx,[ebx+0x36c]; mov ecx,81;
    kills:
      mov eax,[edx]; test eax,eax; jz next_kill;
      cmp [eax+0xf4],ebp; jne next_kill;
      mov eax,[eax+0x150]; cmp eax,2; ja next_kill;
      inc eax; add edi,eax; jno next_kill; mov edi,0x7fffffff;
    next_kill:
      add edx,4; loop kills;
      mov eax,[ebp+0x150]; test eax,eax; jz infantry;
      cmp eax,2; ja next_unit;
      mov edx,[ebp+0x15c]; test edx,edx; jz next_unit;
      add edx,0x8c; mov ecx,2; jmp member;
    infantry:
      lea edx,[ebp+0x15c]; mov ecx,1;
    member:
      mov eax,[edx]; test eax,eax; jz next_member;
      cmp dword ptr [eax+0x48],99; jl eligible;
      add [esp],edi; adc dword ptr [esp+4],0; jmp next_member;
    eligible:
      inc dword ptr [esp+8];
    next_member:
      add edx,4; loop member;
    next_unit:
      add dword ptr [esp+12],4; dec dword ptr [esp+16]; jnz unit_loop;
      xor eax,eax; xor edx,edx; mov ecx,[esp+8]; test ecx,ecx; jz store;
      mov eax,[esp]; mov edx,[esp+4]; cmp edx,ecx; jae saturate;
      div ecx; cmp eax,0x7fffffff; jbe store;
    saturate:
      mov eax,0x7fffffff; xor edx,edx;
    store:
      mov [ebx+0xe4c],eax; mov [ebx+0xe50],edx;
      add esp,24; popad; popfd;
      lea ebx,[ebp+0x228]; jmp 0x43a478
    ''',address()))
    adjust=put(asm('''
      push ecx; push ebx;
      cmp dword ptr [eax+0x48],99; jl eligible;
      xor edx,edx; jmp done;
    eligible:
      mov ebx,[esi+4]; mov ecx,[ebx+0xe4c];
      cmp dword ptr [ebx+0xe50],0; je add_share;
      dec dword ptr [ebx+0xe50]; inc ecx;
    add_share:
      add edx,ecx; jno done; mov edx,0x7fffffff;
    done:
      pop ebx; pop ecx; ret
    ''',address()))
    def hook(a,old,code):
        target=put(asm(code,address()));before=old if isinstance(old,bytes) else asm(old,a)
        patch(a,before,asm(f'jmp {target}',a)+b'\x90'*(len(before)-5))
        return target
    patch(0x43a472,asm('lea ebx,[ebp+0x228]',0x43a472),asm(f'jmp {prepare}',0x43a472)+b'\x90')
    inf=hook(0x43e8de,'mov ecx,[esp+0x34];push 0',f'mov edx,[esp+0x34];call {adjust};mov ecx,edx;push 0;jmp 0x43e8e4')
    crew1=hook(0x43fd68,bytes.fromhex('8b504c03d3'),f'mov edx,ebx;call {adjust};add edx,[eax+0x4c];jmp 0x43fd6d')
    crew2=hook(0x43fd96,bytes.fromhex('8b484c03cb'),f'mov edx,ebx;call {adjust};mov ecx,[eax+0x4c];add ecx,edx;jmp 0x43fd9b')
    return dict(xp_share_prepare=hex(prepare),xp_share_adjust=hex(adjust),xp_share_infantry=hex(inf),xp_share_crew=[hex(crew1),hex(crew2)])
