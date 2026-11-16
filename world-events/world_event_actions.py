"""Native inventory/recruitment and real optional battle adapters.

No script interpreter, story flag, city ownership or original army is reset.
The event engine owns costs and the persisted pending-reward/completion state.
"""
import struct

TEMP_MAGIC=0x57454231
PATCH_SITES={0x4398f6:5,0x439a01:5}
PROFILES={'infantry':1,'armor':2,'air':3,'artillery':4,'elite_armor':5}


def emit(put,asm,address,patch,result_address=0x48d398+81*4):
    def code(s):return put(asm(s,address()))
    centers=put(struct.pack('<9I',10,13,16,37,39,43,64,67,70))
    # stdcall find_item(army,id): spare inventory only, never equipped items.
    find_item=code('''
      mov edx,[esp+4]; test edx,edx; jz no;
      cmp dword ptr [edx],1; jne no;
      mov eax,[esp+8]; cmp eax,1; jl no; cmp eax,82; jg no;
      add edx,0x1a4; mov ecx,80;
    scan: cmp [edx],eax; je yes; add edx,0x10c; loop scan;
    no: xor eax,eax; ret 8;
    yes: mov eax,edx; ret 8;
    ''')
    take_item=code(f'''
      push dword ptr [esp+8]; push dword ptr [esp+8]; call {find_item};
      test eax,eax; jz done; mov dword ptr [eax],0; mov eax,1;
    done: ret 8;
    ''')
    give_item=code('''
      push esi; push edi;
      mov edi,[esp+12]; test edi,edi; jz invalid;
      cmp dword ptr [edi],1; jne invalid;
      mov esi,[esp+16]; cmp esi,1; jl invalid; cmp esi,60; jg invalid;
      cmp esi,46; je invalid;
      lea edx,[edi+0x1a4]; mov ecx,80;
    scan: cmp dword ptr [edx],0; je found; add edx,0x10c; loop scan;
      mov eax,2; jmp done;
    found: mov ecx,[0x4880ec]; test ecx,ecx; jz invalid;
      push edx; push esi; call 0x4162b0; jmp done;
    invalid: xor eax,eax;
    done: pop edi; pop esi; ret 8;
    ''')
    # stdcall known(head,id), native integer technology-list nodes.
    known=code('''
      push esi; push edi; mov edi,[esp+12]; test edi,edi; jz no;
      mov edx,[esp+16]; mov esi,[edi]; mov ecx,10000;
    scan: cmp esi,edi; je no; test esi,esi; jz no;
      cmp [esi+8],edx; je yes; mov esi,[esi]; loop scan;
    no: xor eax,eax; jmp done;
    yes: mov eax,1;
    done: pop edi; pop esi; ret 8;
    ''')
    hire=code(f'''
      push ebp; mov ebp,esp; push esi; push edi;
      mov esi,[ebp+8]; test esi,esi; jz invalid;
      mov edi,[ebp+12]; cmp edi,1; jl invalid; cmp edi,13; jg invalid;
      cmp dword ptr [ebp+16],1; jl invalid;
      cmp dword ptr [ebp+16],30; jg invalid;
      cmp dword ptr [esi+0x50a5c],10000; jae full;
      cmp dword ptr [esi+0x50a58],0; je invalid;
      push edi; push dword ptr [esi+0x50a04]; call {known};
      test eax,eax; jz invalid;
      mov ecx,[0x4880e8]; test ecx,ecx; jz invalid;
      push dword ptr [ebp+16]; push edi; call 0x414ed0;
      test eax,eax; jz invalid;
      mov dword ptr [eax+8],1; mov dword ptr [eax+0x10],0;
      push eax; push 0; push 0; push 2; mov ecx,esi; call 0x438760;
      mov eax,1; jmp done;
    full: mov eax,2; jmp done;
    invalid: xor eax,eax;
    done: pop edi; pop esi; pop ebp; ret 12;
    ''')
    give_machine=code(f'''
      push esi; push edi;
      mov esi,[esp+12]; test esi,esi; jz invalid;
      mov edi,[esp+16]; cmp edi,1; jl invalid; cmp edi,24; jg invalid;
      cmp edi,17; jl ordinary; cmp edi,21; jle invalid;
    ordinary:
      cmp dword ptr [esi+0x50a68],10000; jae full;
      cmp dword ptr [esi+0x50a64],0; je invalid;
      mov ecx,[0x4880f0]; test ecx,ecx; jz invalid;
      push edi; call 0x416660; test eax,eax; jz invalid;
      mov dword ptr [eax],0;
      push eax; push 0; push 0; push 7; mov ecx,esi; call 0x438760;
      mov eax,1; jmp done;
    full: mov eax,2; jmp done;
    invalid: xor eax,eax;
    done: pop edi; pop esi; ret 8;
    ''')
    # Native loader4163e0 maps raw+20 category to runtime+50. Runtime+8 is
    # movement flags, not category (legitimate Goblin MK2 uses2, tanks10/11).
    # A spare can still be referenced by an unfinished workshop row. Inspect
    # the stock five-row repair queue rather than relying only on its HP.
    machine_ready=code('''
      push ebx; push esi; push edi;
      mov edx,[esp+20]; test edx,edx; jz no;
      cmp dword ptr [edx],0; jne no;
      cmp dword ptr [edx+0x8c],0; jne no;
      cmp dword ptr [edx+0x90],0; jne no;
      mov eax,[edx+0x54]; test eax,eax; jle no;
      cmp eax,[edx+0x58]; jne no;
      mov eax,[edx+4]; cmp eax,5; jbe air;
      cmp eax,22; jae air;
      cmp dword ptr [edx+0x50],0; jne no; jmp workshop;
    air: cmp dword ptr [edx+0x50],1; jne no;
    workshop:
      mov eax,[esp+16]; mov edi,[eax+0x50a88]; test edi,edi; jz yes;
      mov esi,[edi]; mov ebx,1000;
    building:
      cmp esi,edi; je yes; test esi,esi; jz no;
      dec ebx; js no; mov eax,[esi+8]; test eax,eax; jz no;
      cmp dword ptr [eax+0xc],19; jne nextbuilding;
      mov ecx,[eax+0x38]; cmp ecx,5; ja no;
      add eax,0x250;
    repair:
      test ecx,ecx; jz nextbuilding;
      cmp dword ptr [eax],0; je nextrepair;
      cmp [eax+0x1c],edx; je no;
    nextrepair: add eax,0x20; dec ecx; jmp repair;
    nextbuilding: mov esi,[esi]; jmp building;
    yes: mov eax,1; jmp done;
    no: xor eax,eax;
    done: pop edi; pop esi; pop ebx; ret 8;
    ''')
    # Return a proved native list node; a repeated pointer or malformed count
    # invalidates the operation rather than leaving a dangling saved reference.
    machine_node=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,8;
      mov ebx,[ebp+8]; test ebx,ebx; jz no;
      cmp dword ptr [ebx+4],1; jne no;
      cmp dword ptr [ebx+8],1; jne no;
      mov eax,[ebp+12]; cmp eax,1; jl no; cmp eax,24; jg no;
      cmp eax,17; jl ordinary; cmp eax,21; jle no;
    ordinary:
      cmp dword ptr [ebx+0x50a68],0; jle no;
      cmp dword ptr [ebx+0x50a68],10000; ja no;
      mov esi,[ebx+0x50a64]; test esi,esi; jz no;
      mov edi,[esi]; mov dword ptr [ebp-16],0; mov dword ptr [ebp-20],0;
    scan:
      cmp edi,esi; je counted; test edi,edi; jz no;
      inc dword ptr [ebp-16]; cmp dword ptr [ebp-16],10000; ja no;
      mov eax,[edi]; mov ecx,[edi+4]; test eax,eax; jz no;
      test ecx,ecx; jz no; cmp [eax+4],edi; jne no; cmp [ecx],edi; jne no;
      mov edx,[edi+8]; test edx,edx; jz no;
      mov ecx,[ebp-20]; test ecx,ecx; jz candidate;
      cmp [ecx+8],edx; je no;
    candidate:
      mov eax,[ebp+12]; cmp [edx+4],eax; jne next;
      push edx; push ebx; call {machine_ready}; test eax,eax; jz next;
      cmp dword ptr [ebp-20],0; jne next; mov [ebp-20],edi;
    next: mov edi,[edi]; jmp scan;
    counted:
      mov eax,[ebp-16]; cmp eax,[ebx+0x50a68]; jne no;
      mov eax,[ebp-20]; jmp done;
    no: xor eax,eax;
    done: add esp,8; pop edi; pop esi; pop ebx; pop ebp; ret 8;
    ''')
    find_machine=code(f'''
      push dword ptr [esp+8]; push dword ptr [esp+8]; call {machine_node};
      test eax,eax; jz done; mov eax,[eax+8];
    done: ret 8;
    ''')
    take_machine=code(f'''
      push esi; push edi;
      push dword ptr [esp+16]; push dword ptr [esp+16]; call {machine_node};
      test eax,eax; jz done;
      mov esi,eax; mov edi,[eax+8]; mov edx,[eax]; mov ecx,[eax+4];
      mov [ecx],edx; mov [edx+4],ecx;
      mov eax,[esp+12]; dec dword ptr [eax+0x50a68];
      push edi; call 0x4500e6; add esp,4;
      push esi; call 0x4500e6; add esp,4; mov eax,1;
    done: pop edi; pop esi; ret 8;
    ''')
    # Marked enemy armies are heap-owned and never inserted in world/town lists.
    # Cancel the stock home-town defeat statistic before stock troop disposal.
    dispose=code(f'''
      mov eax,[esp+4]; test eax,eax; jz original;
      cmp dword ptr [eax+0x55ac],{TEMP_MAGIC}; jne original;
      cmp dword ptr [eax+0x14],0; je original;
      dec dword ptr [ecx+0x509f8];
    original: jmp 0x437fc0;
    ''')
    patch(0x4398f6,asm('call 0x437fc0',0x4398f6),asm(f'call {dispose}',0x4398f6))
    # stdcall destroy(enemy): handles partial construction, loss and retreat.
    destroy=code(f'''
      push esi; mov esi,[esp+8]; test esi,esi; jz done;
      cmp dword ptr [esi+0x55ac],{TEMP_MAGIC}; jne done;
      mov ecx,[esi+4]; push esi; call {dispose};
      mov dword ptr [esi+0x55ac],0;
      push esi; call 0x4500e6; add esp,4;
    done: pop esi; ret 4;
    ''')
    tail=code(f'''
      pushfd; pushad;
      mov eax,[ebp+0x50]; test eax,eax; jz done;
      cmp dword ptr [eax+0x55ac],{TEMP_MAGIC}; jne done;
      mov edx,[0x48d39c]; inc edx; mov [{result_address}],edx;
      push eax; call {destroy};
    done: popad; popfd;
      mov ecx,[ebp+0x34]; pop edi; pop esi; jmp 0x439a06;
    ''')
    patch(0x439a01,asm('mov ecx,[ebp+0x34];pop edi;pop esi',0x439a01),asm(f'jmp {tail}',0x439a01))
    # stdcall person(enemy,slot,class,level,weapon). Record ownership precedes
    # equipment lookup so partial failures can use the normal disposal path.
    person=code('''
      push ebp; mov ebp,esp; push esi; push edi;
      mov esi,[ebp+8]; mov edi,[ebp+12];
      push dword ptr [ebp+20]; push dword ptr [ebp+16];
      mov ecx,[0x4880e8]; call 0x414ed0;
      test eax,eax; jz done;
      mov [esi+edi*4+0x60],eax; inc dword ptr [esi+0x1c];
      mov dword ptr [eax+8],0; mov dword ptr [eax+0x10],15;
      mov dword ptr [eax+0x14],0;
      cmp edi,39; jne weapon;
      mov [esi+0x34],eax;
    weapon:
      cmp dword ptr [ebp+24],0; je done;
      mov edi,eax; sub esp,0x10c; mov edx,esp;
      push edx; push dword ptr [ebp+24]; mov ecx,[0x4880ec]; call 0x4162b0;
      test eax,eax; jz equip_failed;
      mov eax,esp; push eax; push 0; push edi; call 0x415aa0; add esp,12;
      test eax,eax; jnz equip_failed;
      add esp,0x10c; mov eax,edi; jmp done;
    equip_failed: add esp,0x10c; xor eax,eax;
    done: pop edi; pop esi; pop ebp; ret 20;
    ''')
    from ruin_guardians import emit as guardian_emit, GUARDIANS
    guardian_enemy=guardian_emit(put,code,person,destroy,TEMP_MAGIC)
    # stdcall enemy(homeTown,profile,level), returns a private native army.
    enemy=code(f'''
      cmp dword ptr [esp+8],6; jae {guardian_enemy};
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,12;
      push 0x55b0; call 0x450452; add esp,4;
      test eax,eax; jz done;
      mov esi,eax; mov edi,eax; xor eax,eax; mov ecx,0x156c; cld; rep stosd;
      mov dword ptr [esi],12; mov eax,[ebp+8]; mov [esi+4],eax;
      mov dword ptr [esi+0x14],15;
      mov dword ptr [esi+0x55ac],{TEMP_MAGIC};
      mov eax,[ebp+12]; cmp eax,2; je armor;
      cmp eax,3; je air; cmp eax,5; je elite;
      mov dword ptr [esi+0x18],0; xor ebx,ebx;
    foot:
      mov eax,ebx; test ebx,ebx; jnz footslot; mov eax,39;
    footslot:
      test ebx,ebx; jz commander;
      dec eax;
      mov ecx,2; mov edx,18;
      cmp dword ptr [ebp+12],4; jne footclass;
      mov ecx,4; mov edx,43;
    footclass:
      jmp makefoot;
    commander: mov ecx,3; mov edx,21;
    makefoot:
      push edx; push dword ptr [ebp+16]; push ecx; push eax; push esi; call {person};
      test eax,eax; jz failed;
      inc ebx; cmp ebx,24; jb foot; jmp ready;
    armor:
      mov dword ptr [esi+0x18],1; mov dword ptr [esp],6; jmp vehicles;
    air:
      mov dword ptr [esi+0x18],2; mov dword ptr [esp],6; jmp vehicles;
    elite:
      mov dword ptr [esi+0x18],1; mov dword ptr [esp],9;
    vehicles:
      xor ebx,ebx;
    vehicle:
      mov eax,[ebx*4+{centers}]; mov [esp+4],eax;
      mov ecx,10; cmp dword ptr [esi+0x18],2; jne crew; mov ecx,9;
    crew:
      push 0; push dword ptr [ebp+16]; push ecx; push eax; push esi; call {person};
      test eax,eax; jz failed; mov [esp+8],eax;
      mov edi,9; cmp dword ptr [ebp+12],5; jne normal_vehicle; mov edi,13;
    normal_vehicle:
      mov eax,ebx; xor edx,edx; mov ecx,3; div ecx; add edi,edx;
      cmp dword ptr [esi+0x18],2; jne make_vehicle;
      mov edi,4; test ebx,1; jz make_vehicle; mov edi,23;
    make_vehicle:
      push edi; mov ecx,[0x4880f0]; call 0x416660;
      test eax,eax; jz failed;
      mov [esi+ebx*4+0x3c],eax; mov dword ptr [eax],15;
      inc dword ptr [esi+0x20]; cmp dword ptr [eax+8],0; jne bind;
      inc dword ptr [esi+0x24];
    bind:
      push 0; push dword ptr [esp+12]; push eax; call 0x4168b0; add esp,12;
      inc ebx; cmp ebx,[esp]; jb vehicle;
    ready:
      mov eax,esi; jmp done;
    failed:
      push esi; call {destroy}; xor eax,eax;
    done:
      add esp,12; pop edi; pop esi; pop ebx; pop ebp; ret 12;
    ''')
    battle=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      mov esi,[ebp+8]; test esi,esi; jz no;
      cmp dword ptr [esi],1; jne no;
      cmp dword ptr [esi+0x14],1; jl no; cmp dword ptr [esi+0x14],9; jg no;
      cmp dword ptr [esi+0x18],3; jae no;
      mov ecx,[ebp+12]; cmp ecx,1; jl no; cmp ecx,17; jg no;
      mov edi,[esi+8]; test edi,edi; jnz context_ready;
      cmp ecx,6; jb no; mov edi,[esi+4]; test edi,edi; jz no;
    context_ready:
      mov eax,[esi+0x34]; test eax,eax; jz no;
      cmp dword ptr [eax+4],0; jne no;
      cmp dword ptr [eax+0x54],0; jle no;
      mov ecx,[ebp+12];
      cmp ecx,3; jne type_ok;
      cmp dword ptr [esi+0x18],2; jne no;
      cmp dword ptr [esi+0x20],0; jle no;
    type_ok:
      cmp dword ptr [0x48cc1c],0; je no;
      cmp dword ptr [0x4880e8],0; je no;
      cmp dword ptr [0x4880ec],0; je no;
      cmp dword ptr [0x4880f0],0; je no;
      mov eax,[eax+0x48]; cmp eax,15; jge enough; mov eax,15;
    enough:
      cmp eax,99; jle bounded; mov eax,99;
    bounded:
      push eax; push ecx; push edi; call {enemy}; test eax,eax; jz no;
      mov ebx,eax; push 0xe54; call 0x450452; add esp,4;
      test eax,eax; jz release;
      push 0; push 0; push edi; push ebx; push esi;
      mov ecx,eax; call 0x4393a0;
      mov dword ptr [{result_address}],0;
      push eax; mov ecx,[0x48cc1c]; call 0x4438f0;
      mov eax,1; jmp done;
    release:
      push ebx; call {destroy};
    no: xor eax,eax;
    done: pop edi; pop esi; pop ebx; pop ebp; ret 8;
    ''')
    return {'world_event_actions':dict(
        find_item=hex(find_item), take_item=hex(take_item), give_item=hex(give_item),
        hire=hex(hire),give_machine=hex(give_machine),known=hex(known),
        find_machine=hex(find_machine),take_machine=hex(take_machine),
        battle=hex(battle),enemy=hex(enemy),person=hex(person),destroy=hex(destroy),
        dispose=hex(dispose),tail=hex(tail),result_address=hex(result_address),
        profiles=PROFILES,guardian_enemy=hex(guardian_enemy),guardian_profiles=GUARDIANS,results={'loss':1,'retreat':2,'win':3},
        abi='stdcall; give_item(army,id),take_item(army,id),find_item(army,id); hire(town,class,level1..30); give_machine(town,id); find_machine(homeTown,id),take_machine(homeTown,id); battle(army,profile1..17);6..17 annual guardians at fixed30/40/50, own-home world context allowed, ordinary equipment only. Grants return1success,2capacity,0invalid/locked. Finds return actual spare record pointer or0. take_machine returns1consumed/0missing; only full-HP crewless undeployed ordinary stock, no active repair reference, no duplicate/malformed links. Battle returns1async started,0invalid; stock result encoded at result_address after cleanup.',
        safety='No story VM reset or ownership change. Spare inventory only. Ordinary vehicle gift does not unlock production; caller gates reward eligibility. Recruits require learned class. Private enemy heap, ordinary units, stock casualties/XP; no event reward duplication managed here.')}
