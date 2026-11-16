"""Defer event UI to the native message loop and invalidate it during loading.

Both hooks replace whole instructions. The load hook retains the native cdecl
slot argument and return value; no persistent state contains frame pointers.
"""
WNDPROC = 0x401E00
LOAD = 0x401210
MESSAGE = 0x86E0
WND_BYTES = bytes.fromhex('8b4c240883f920')
LOAD_BYTES = bytes.fromhex('8b44240483ec10')
SAVE=0x401160
SAVE_BYTES=bytes.fromhex('83ec108b442414')
WORLD_RESET=0x4206d0
RESET_BYTES=bytes.fromhex('6aff6889d14500')
PATCH_SITES = {WNDPROC: WND_BYTES, LOAD: LOAD_BYTES,SAVE:SAVE_BYTES,WORLD_RESET:RESET_BYTES}


def emit(put, asm, address, patch, exports):
    def symbol(name):
        value = exports[name]
        return int(value, 0) if isinstance(value, str) else value

    def code(source):
        return put(asm(source, address()))

    trampoline = put(LOAD_BYTES + asm('jmp 0x401217', address() + 7))
    load_hook = code(f'''
      push ebp; mov ebp,esp;
      call {symbol('we_load_begin')};
      push dword ptr [ebp+8]; call {trampoline}; add esp,4;
      push eax; push eax; push dword ptr [ebp+8]; call {symbol('we_load_game')};
      mov eax,[esp]; call {symbol('we_load_end')}; pop eax;
      pop ebp; ret;
    ''')
    save_hook=code(f'push dword ptr [esp+4];call {symbol("we_save")};ret')
    world_reset_hook=code(f'pushfd;pushad;call {symbol("we_world_reset")};popad;popfd;push -1;push 0x45d189;jmp 0x4206d7')
    wndproc_hook = code(f'''
      cmp dword ptr [esp+8],{MESSAGE}; jne ordinary;
      mov eax,esp;
      push dword ptr [eax+16]; push dword ptr [eax+12];
      push dword ptr [eax+8]; push dword ptr [eax+4];
      call {symbol('we_message')}; ret 16;
    ordinary:
      cmp dword ptr [esp+8],0x82; jne replay;
      pushfd; pushad;
      push dword ptr [esp+40]; call {symbol('we_window_close')};
      popad; popfd;
    replay:
      mov ecx,[esp+8]; cmp ecx,0x20; jmp 0x401e07;
    ''')
    assert asm('mov ecx,[esp+8];cmp ecx,0x20', WNDPROC) == WND_BYTES
    assert asm('mov eax,[esp+4];sub esp,0x10', LOAD) == LOAD_BYTES
    patch(WNDPROC, WND_BYTES, asm(f'jmp {wndproc_hook}', WNDPROC) + b'\x90\x90')
    patch(LOAD, LOAD_BYTES, asm(f'jmp {load_hook}', LOAD) + b'\x90\x90')
    patch(SAVE,SAVE_BYTES,asm(f'jmp {save_hook}',SAVE)+b'\x90\x90')
    patch(WORLD_RESET,RESET_BYTES,asm(f'jmp {world_reset_hook}',WORLD_RESET)+b'\x90\x90')
    return {
        'save_hook':hex(save_hook),'world_reset_hook':hex(world_reset_hook),'wndproc_hook': hex(wndproc_hook), 'load_hook': hex(load_hook),
        'trampoline': hex(trampoline), 'message': MESSAGE,
        'native_wndproc': hex(WNDPROC), 'native_load': hex(LOAD),
        'hwnd_global': '0x476fe8', 'frame_manager_global': '0x48cc1c',
        'frame_current_offset': 16, 'frame_state_offset': 4,
        'frame_active_state': 3, 'modal_global': '0x4880e0',
        'patch_sites': {hex(k): v.hex() for k, v in PATCH_SITES.items()},
    }
