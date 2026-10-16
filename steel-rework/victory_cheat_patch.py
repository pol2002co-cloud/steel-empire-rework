def emit(put,asm,address,patch):
    target=put(asm('''
      pushfd; pushad;
      lea edi,[esi+0x36c]; mov ecx,81;
    scan:
      mov eax,[edi]; test eax,eax; jz next;
      mov dword ptr [eax+0x138],0;
      mov dword ptr [eax+0x54],0;
      mov dword ptr [eax+0x13c],0;
    next:
      add edi,4; loop scan;
      mov eax,[esi+0x204]; test eax,eax; jz commander_done;
      mov dword ptr [eax+0x138],0;
      mov dword ptr [eax+0x54],0;
      mov dword ptr [eax+0x13c],0;
    commander_done:
      mov eax,[esi+0x200]; test eax,eax; jz finish;
      cmp dword ptr [eax+0x138],0; jne finish;
      mov dword ptr [eax+0x138],1;
      mov dword ptr [eax+0x54],1;
    finish:
      mov dword ptr [esi+0xe48],0;
      mov dword ptr [esi+0x1d8],6;
      popad; popfd; jmp 0x43c86c
    ''',address()))
    old=asm('mov ecx,[esi+0x204];mov [ecx+0x138],ebp',0x43c860)
    patch(0x43c860,old,asm(f'jmp {target}',0x43c860)+b'\x90'*(len(old)-5))
    return target
