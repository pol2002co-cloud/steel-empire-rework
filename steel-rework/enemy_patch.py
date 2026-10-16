"""Increase six mercenary factions using their original generator profiles."""
def emit(put,asm,address,patch):
    target=put(asm('''
      pushfd; pushad; lea ebp,[esp+36];
      mov eax,[ebp+0x17c];
      cmp eax,12; je selected; cmp eax,14; je selected;
      cmp eax,15; je selected; cmp eax,16; je selected;
      cmp eax,18; je selected; cmp eax,20; jne done;
    selected:
      mov eax,[ebp+0x184]; test eax,eax; jz infantry;
      cmp eax,1; je armored; cmp eax,2; je aircraft; jmp done;
    infantry:
      cmp dword ptr [ebp+0x18],0; jle done;
      mov dword ptr [ebp+0x18],79; jmp done;
    armored:
      mov edi,7; jmp vehicles;
    aircraft:
      mov edi,9;
    vehicles:
      xor ecx,ecx;
    count:
      cmp ecx,9; jae counted;
      cmp dword ptr [ebp+ecx*4+0x44],0; je counted;
      inc ecx; jmp count;
    counted:
      cmp ecx,2; jb done;
      mov ebx,ecx; mov edx,1;
    fill:
      cmp ecx,edi; jae filled;
      mov eax,[ebp+edx*4+0x44]; mov [ebp+ecx*4+0x44],eax;
      inc ecx; inc edx; cmp edx,ebx; jb fill;
      mov edx,1; jmp fill;
    filled:
      cmp edi,7; jne done;
      cmp dword ptr [ebp+0x18],0; jle done;
      mov dword ptr [ebp+0x18],18;
    done:
      popad; popfd;
      sub edx,[esp+0x10]; inc edx; jmp 0x419088
    ''',address()))
    before=asm('sub edx,[esp+0x10];inc edx',0x419083)
    patch(0x419083,before,asm('jmp '+str(target),0x419083))
    return target
