"""v0.6 hooks. Addresses are for the hash-verified Korean original."""
import struct

def emit(put, asm, address, patch, original_data):
    def hook(a, old, code):
        target=put(asm(code,address()))
        before=asm(old,a)
        assert len(before)>=5
        patch(a,before,asm(f'jmp {target}',a)+b'\x90'*(len(before)-5))
        return target
    # Extend the two five-row retraining tables, rather than indexing into the
    # adjacent cost/eligibility data when selecting class 7.
    growth=put(original_data(0x460e08,120)+struct.pack('<6i',0,20,0,0,0,0))
    costs=put(original_data(0x460e80,80)+struct.pack('<4i',25,15,5000,20))
    for a,old,new in [
        (0x415211,'mov ecx,[eax*8+0x460e08]',f'mov ecx,[eax*8+{growth}]'),
        (0x415218,'lea eax,[eax*8+0x460e08]',f'lea eax,[eax*8+{growth}]'),
        (0x4152dc,'mov edx,[ecx*8+0x460e08]',f'mov edx,[ecx*8+{growth}]'),
        (0x4152e3,'lea ecx,[ecx*8+0x460e08]',f'lea ecx,[ecx*8+{growth}]'),
        (0x4152ed,'add eax,0x460e80',f'add eax,{costs}')]:
        patch(a,asm(old,a),asm(new,a))
    patch(0x460fac,b'\0'*4,struct.pack('<I',1))
    patch(0x460fec,b'\0'*4,struct.pack('<I',1))
    for a in [0x437566,0x437792]:patch(a,asm('push 0x1b28',a),asm('push 0x2020',a))
    patch(0x431d7b,asm('mov ecx,0x631',0x431d7b),asm('mov ecx,0x76f',0x431d7b))
    patch(0x4320eb,asm('cmp dword ptr [ebx+0x38],5',0x4320eb),asm('cmp dword ptr [ebx+0x38],6',0x4320eb))
    # Adding or researching armored infantry also registers heavy armor.
    add=hook(0x432163,'pop edi;pop esi;pop ebx;add esp,0x4e4', '''
       cmp dword ptr [esp+0x4f4],6; jne done;
       push 7; mov ecx,ebx; call 0x4320e0;
    done: pop edi; pop esi; pop ebx; add esp,0x4e4; jmp 0x43216c
    ''')
    # Original saves contain five serialized slots regardless of active count.
    # New saves use six only when their already-serialized active count is six.
    save=hook(0x431eff,'mov ebp,5','''
       mov ebp,[esi-0x220]; cmp ebp,5; jae ready; mov ebp,5;
    ready: jmp 0x431f04
    ''')
    load=hook(0x431fc5,'add esi,0x260;mov dword ptr [esp+0x10],5','''
       push edi; push ecx; push eax;
       lea edi,[esi+0x1b28]; xor eax,eax; mov ecx,0x13e; rep stosd;
       pop eax; pop ecx; pop edi;
       mov eax,[esi+0x38]; cmp eax,5; jae ready; mov eax,5;
    ready: mov [esp+0x10],eax; add esi,0x260; jmp 0x431fd3
    ''')
    # Recreate menu templates as retraining deltas after loading, just as a new
    # facility does. Pending trainees themselves are deserialized separately.
    patch(0x43202d,asm('call 0x415370',0x43202d),asm('call 0x4152a0',0x43202d))
    finish=hook(0x43209c,'pop edi;pop esi;pop ebp;mov eax,1','''
       mov ecx,[esp+0x14]; mov edx,[ecx+0x38]; lea eax,[ecx+0x260];
    scan: test edx,edx; jz done; cmp dword ptr [eax],6; je add;
       add eax,0x4f8; dec edx; jmp scan;
    add: push 7; call 0x4320e0;
    done:
       pop edi; pop esi; pop ebp; mov eax,1; jmp 0x4320a4
    ''')
    # The city screen alone consumes A. Dialogs have their own update loop;
    # opening the stock airport preserves garrison and pilot checks.
    airport=hook(0x42ed13,'mov ecx,[0x487f3c]', '''
       pushfd; pushad;
       cmp dword ptr [0x4880e0],0; jne done;
       mov ecx,[0x487f3c]; test ecx,ecx; jz done;
       push 1; push 0x41; call 0x406390; test eax,eax; jz done;
       mov edi,[ebx+0x50]; test edi,edi; jz done;
       mov ecx,9; lea edx,[edi+0x50654];
    scan: mov eax,[edx]; test eax,eax; jz next;
       cmp dword ptr [eax+0x18],2; je open;
    next: add edx,4; loop scan; jmp done;
    open: push 0x68; call 0x450452; add esp,4; test eax,eax; jz done;
       push edi; mov ecx,eax; call 0x423820;
       push eax; mov ecx,[0x48cc1c]; call 0x4438f0;
    done: popad; popfd; mov ecx,[0x487f3c]; jmp 0x42ed19
    ''')
    return dict(retraining_growth=hex(growth),retraining_costs=hex(costs),retraining_add=hex(add),retraining_save=hex(save),retraining_load=hex(load),retraining_load_finish=hex(finish),airport_shortcut=hex(airport))
