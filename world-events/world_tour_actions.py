"""Headless civilian dancer performance using stock XP and level-up routines."""

MAX_DANCERS = 8


def emit(put, asm, address):
    # Stack-local performer pointers and CRT seed never enter the save format.
    perform = put(asm(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,64;
      mov ebx,[ebp+8]; test ebx,ebx; jz invalid;
      cmp dword ptr [ebx],1; jne invalid;
      cmp dword ptr [ebx+0x18],3; jne invalid;
      cmp dword ptr [ebx+0x1c],0; jle invalid;
      mov eax,[ebx+0x34]; test eax,eax; jz invalid;
      cmp dword ptr [eax+4],0; jne invalid;
      cmp dword ptr [eax+0x54],0; jle invalid;
      xor esi,esi; xor edi,edi; mov dword ptr [ebp-40],0;
    scan:
      mov edx,[ebx+esi*4+0x60]; test edx,edx; jz next;
      cmp dword ptr [edx+4],0; jne next;
      cmp dword ptr [edx+0x54],0; jle next;
      cmp dword ptr [edx+0x38],13; jne next;
      cmp dword ptr [edx+0x48],1; jl next;
      cmp dword ptr [edx+0x48],99; jg next;
      cmp dword ptr [edx+0x4c],0; jl next;
      cmp dword ptr [edx+0x4c],0x7fffffd7; ja next;
      cmp dword ptr [edx+0x50],0; jle next;
      xor ecx,ecx;
    unique:
      cmp ecx,edi; jae selected;
      cmp [ebp+ecx*4-76],edx; je next;
      inc ecx; jmp unique;
    selected:
      mov [ebp+edi*4-76],edx; inc edi;
      imul eax,[edx+0x48],200; add eax,800; add [ebp-40],eax;
      cmp edi,{MAX_DANCERS}; jae gathered;
    next:
      inc esi; cmp esi,81; jb scan;
    gathered:
      test edi,edi; jz invalid;
      mov [ebp-44],edi;
      mov eax,[ebp+12]; xor edx,edx; mov ecx,20; div ecx;
      lea eax,[edx*2+2]; mov [ebp-36],eax;
      call 0x45290b; test eax,eax; jz invalid;
      mov [ebp-32],eax; mov ecx,[eax+0x14]; mov [ebp-28],ecx;
      mov edx,[ebp+12]; mov [eax+0x14],edx;
      xor esi,esi;
    award:
      mov edi,[ebp+esi*4-76]; mov eax,[ebp-36]; add [edi+0x4c],eax;
      push edi; mov ecx,[0x4880e8]; call 0x414fc0;
      inc esi; cmp esi,[ebp-44]; jb award;
      mov edx,[ebp-32]; mov ecx,[ebp-28]; mov [edx+0x14],ecx;
      mov eax,[ebp-40]; jmp done;
    invalid:
      xor eax,eax;
    done:
      add esp,64; pop edi; pop esi; pop ebx; pop ebp; ret 8
    ''', address()))
    return {'world_tour_actions':dict(
        perform=hex(perform), max_dancers=MAX_DANCERS,
        native_xp='0x414fc0', native_growth='0x415010', native_rng='0x45046d',
        crt_thread='0x45290b', crt_rng_seed_offset=0x14,
        abi='stdcall perform(army,seed) returns net gold income; caller credits money and enforces city/cooldown.',
        experience='Shared 2+2*(seed%20) XP; actual native 414fc0/415010 growth and level99 cap.',
        income='Sum of pre-performance (1000+200*level)-200 fee per selected dancer, maximum8.',
        eligibility='Healthy player civilian formation and commander; first8 unique living class13 persons in81 formation slots, heroes and generic dancers.',
        rng='Temporarily seed stock CRT thread RNG for native growth, then restore the original seed. No story RNG consumption.',
        writes='Only selected dancer records and temporary/restored CRT RNG seed; no army position, cash, UI or serialized event-state writes.')}
