"""Record successful native retraining; dialogue runs later in WndProc."""
PATCH_SITES={0x432439:bytes.fromhex('c746f800000000')}

def emit(put,asm,address,patch,exports):
    entry=exports['we_training_done']
    hook=put(asm(f'''mov dword ptr [esi-8],0; pushfd; pushad;
      push dword ptr [edi+4];
      call {entry}; popad; popfd; jmp 0x432440''',address()))
    patch(0x432439,PATCH_SITES[0x432439],asm(f'jmp {hook}',0x432439)+b'\x90\x90')
    return dict(hook=hex(hook),native_completion='0x432439',
                notification='Deferred native dialogue; aggregate completed trainees; no save fields')
