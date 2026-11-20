"""Blueprint-only machines backed by stock-compatible, individually saved chassis."""
import struct


MODELS = (
    dict(name='철왕', base_id=16, hp=6200, attack=(330, 240, 530, 620), defense=235,
         rate=8, reach=3, splash=2, hit=65, evade=20, skill=45, speed=30),
    dict(name='뇌격전차', base_id=13, hp=4300, attack=(370, 340, 490, 430), defense=172,
         rate=6, reach=3, splash=2, hit=78, evade=55, skill=60, speed=45),
    dict(name='천둥매', base_id=2, hp=3100, attack=(340, 520, 390, 200), defense=125,
         rate=8, reach=3, splash=1, hit=85, evade=80, skill=65, speed=60),
    dict(name='밤까마귀', base_id=23, hp=3800, attack=(420, 290, 560, 580), defense=145,
         rate=6, reach=3, splash=2, hit=72, evade=65, skill=55, speed=52),
)


def reject_legendary_delivery(machine_register, reject_label):
    """Protect a crafted variant when a delivery asks for its stock chassis."""
    cases = []
    for index, model in enumerate(MODELS):
        name = model['name'].encode('cp949') + b'\0'
        cases.append(f"cmp dword ptr [{machine_register}+4],{model['base_id']}; jne stock_{index};")
        for offset, value in enumerate(name):
            cases.append(f"cmp byte ptr [{machine_register}+{12 + offset}],{value}; jne stock_{index};")
        cases.append(f'jmp {reject_label}; stock_{index}:')
    return '\n'.join(cases)


def emit(put, asm, address):
    # Each row holds a drawable stock model, a CP949 display name, and the
    # contiguous native fields from current HP (+54) through speed (+88).
    rows = bytearray()
    for model in MODELS:
        rows.extend(struct.pack(
            '<I32s14I', model['base_id'], model['name'].encode('cp949'),
            model['hp'], model['hp'], *model['attack'], model['defense'],
            model['rate'], model['reach'], model['splash'], model['hit'],
            model['evade'], model['skill'], model['speed']))
    table = put(bytes(rows))
    # 43899e inserts new machines at the front of the town's native owning
    # list. Preallocate both objects before linking; the forge supplies the
    # confirmation in its own panel and needs no duplicate town-feed entry.
    give = put(asm(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      mov ebx,[ebp+8]; test ebx,ebx; jz invalid;
      mov eax,[ebp+12]; cmp eax,{len(MODELS)}; jae invalid;
      imul eax,eax,{struct.calcsize('<I32s14I')}; lea esi,[eax+{table}];
      mov edx,[ebx+0x50a64]; test edx,edx; jz invalid;
      cmp dword ptr [ebx+0x50a68],10000; jae full;
      mov eax,[edx]; test eax,eax; jz invalid; cmp [eax+4],edx; jne invalid;
      mov ecx,[0x4880f0]; test ecx,ecx; jz invalid;
      push 0x1a8; call 0x450452; add esp,4; test eax,eax; jz invalid;
      mov edi,eax; push edi; push dword ptr [esi]; mov ecx,[0x4880f0];
      call 0x4166b0; test eax,eax; jz free_machine;
      mov dword ptr [edi],0; mov dword ptr [edi+0x8c],0;
      mov dword ptr [edi+0x90],0;
      push edi; add esi,4; add edi,12; mov ecx,8;
      rep movsd dword ptr es:[edi], dword ptr [esi];
      add edi,0x28; mov ecx,14; rep movsd dword ptr es:[edi], dword ptr [esi]; pop edi;
      push 12; call 0x450452; add esp,4; test eax,eax; jz free_machine;
      mov edx,[ebx+0x50a64]; mov ecx,[edx]; mov [eax],ecx;
      mov [eax+4],edx; mov [eax+8],edi; mov [ecx+4],eax; mov [edx],eax;
      inc dword ptr [ebx+0x50a68]; mov eax,1; jmp done;
    free_machine: push edi; call 0x4500e6; add esp,4;
    invalid: xor eax,eax; jmp done;
    full: mov eax,2;
    done: pop edi; pop esi; pop ebx; pop ebp; ret 8;
    ''', address()))
    return dict(give_legend=hex(give), profiles=list(MODELS))
