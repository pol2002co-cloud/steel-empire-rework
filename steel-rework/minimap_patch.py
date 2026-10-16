"""World minimap hover label. Uses existing game cursor, town list and font renderer."""
def emit(put, asm, address):
    # this=mini; args=local x,y; return=town name or NULL. No game-state writes.
    find = put(asm('''
      push ebx; push esi; push edi; push ebp; sub esp,8;
      mov ebp,ecx; xor eax,eax; mov [esp],eax; mov dword ptr [esp+4],17;
      mov eax,[esp+28]; cmp eax,96; jae search_done;
      mov eax,[esp+32]; cmp eax,77; jae search_done;
      mov esi,[ebp+0x28]; test esi,esi; jz search_done;
      add esi,0x23c; mov edi,100;
    city_loop:
      mov edx,[esi]; test edx,edx; jz city_next;
      cmp dword ptr [edx+8],1; jne city_next;
      mov eax,[edx+0x7c]; test eax,eax; jz city_next;
      cmp byte ptr [eax+0x14],0; je city_next;
      mov eax,[edx+0x34]; sar eax,1; add eax,[ebp+0x3c];
      cmp eax,96; jae city_next;
      sub eax,[esp+28]; imul eax,eax; mov ebx,eax;
      mov eax,[edx+0x38]; sar eax,1; add eax,[ebp+0x40];
      cmp eax,77; jae city_next;
      sub eax,[esp+32]; imul eax,eax; add eax,ebx;
      cmp eax,[esp+4]; jae city_next;
      mov [esp+4],eax; mov eax,[edx+0x7c]; add eax,0x14; mov [esp],eax;
    city_next:
      add esi,4; dec edi; jnz city_loop;
    search_done:
      mov eax,[esp]; add esp,8; pop ebp; pop edi; pop esi; pop ebx; ret 8
    ''', address()))
    # Hover tooltip on parent surface, preserving the original v0.5 behavior.
    draw = put(asm(f'''
      call 0x413c20; pushfd; pushad; sub esp,40;
      mov ebx,esi; mov edi,[ebx+0x38]; test edi,edi; jz hover_done;
      cmp dword ptr [edi],0x460a6c; jne hover_done;
      mov eax,[edi+0x28]; test eax,eax; jz hover_done;
      cmp eax,[0x48c3d8]; jne hover_done;
      cmp dword ptr [0x4880e0],0; jne hover_done;
      mov ecx,[0x487738]; test ecx,ecx; jz hover_done;
      lea eax,[esp]; push eax; call 0x405b40; test eax,eax; jz hover_done;
      lea eax,[esp]; push eax; mov ecx,edi; call 0x413b70;
      cmp eax,edi; jne hover_done;
      mov eax,[esp]; sub eax,[edi+4]; mov edx,[esp+4]; sub edx,[edi+8];
      push edx; push eax; mov ecx,edi; call {find}; test eax,eax; jz hover_done;
      mov ebp,eax; xor ecx,ecx;
    name_length:
      cmp byte ptr [ebp+ecx],0; je name_ready;
      inc ecx; cmp ecx,32; jb name_length; jmp hover_done;
    name_ready:
      lea ecx,[ecx+ecx*2]; lea ecx,[ecx*2+8]; mov [esp+24],ecx;
      mov eax,[esp]; sub eax,[ebx+4]; add eax,12;
      mov edx,[ebx+0xc]; sub edx,ecx; dec edx; cmp eax,edx; jle x_ready; mov eax,edx;
    x_ready:
      test eax,eax; jns x_nonnegative; xor eax,eax;
    x_nonnegative:
      mov [esp+28],eax;
      mov eax,[esp+4]; sub eax,[ebx+8]; add eax,12;
      mov edx,[ebx+0x10]; sub edx,19; cmp eax,edx; jle y_ready; mov eax,edx;
    y_ready:
      test eax,eax; jns y_nonnegative; xor eax,eax;
    y_nonnegative:
      mov [esp+32],eax;
      mov esi,[ebx+0x14]; test esi,esi; jz hover_done;
      mov ecx,esi; call 0x403a70;
      mov eax,[esi+0x80]; mov [esp+36],eax;
      mov eax,[esp+28]; mov edx,[esp+32]; mov ecx,[esp+24]; add ecx,eax; dec ecx;
      push 0; push 0; add edx,17; push edx; push ecx; sub edx,17; push edx; push eax;
      mov ecx,esi; call 0x403f90;
      mov dword ptr [esi+0x80],0xd2;
      mov eax,[esp+28]; mov edx,[esp+32]; add eax,4; add edx,3;
      push ebp; push edx; push eax; mov ecx,esi; call 0x403bd0;
      mov eax,[esp+36]; mov [esi+0x80],eax;
      mov ecx,esi; call 0x403a90;
    hover_done:
      add esp,40; popad; popfd; jmp 0x40a607
    ''', address()))
    return find, draw
