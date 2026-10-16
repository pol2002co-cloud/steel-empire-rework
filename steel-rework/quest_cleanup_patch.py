"""Delete the actual quest object, not a different quest with the same destination."""
def emit(put,asm,address,patch):
    hook=put(asm('''
      lea ebx,[eax+8]; cmp ebx,edx; je 0x448696; jmp 0x448689
    ''',address()))
    patch(0x448677,asm('mov esi,[edx+4];cmp [eax+0xc],esi',0x448677),asm(f'jmp {hook}',0x448677)+b'\x90')
    patch(0x44868d,asm('jne 0x44867a',0x44868d),asm('jne 0x448677',0x44868d))
    return dict(quest_cleanup=dict(hook=hex(hook),rule='Remove exact live quest record identity; preserve other quests sharing type and destination.'))
