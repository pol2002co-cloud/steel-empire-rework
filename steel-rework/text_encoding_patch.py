"""Keep UTF-16 UI resource strings in the game's CP949 bitmap-font encoding."""
def emit(put,asm,address,patch):
    # UI template reader 0x411200: the first six WideCharToMultiByte arguments
    # are already on the stack. Only replace flags/codepage and the call.
    hook=put(asm('''
      push 0; push 949; call dword ptr [0x460034]; jmp 0x41123b
    ''',address()))
    patch(0x411231,asm('push 0;push 0;call dword ptr [0x460034]',0x411231),asm(f'jmp {hook}',0x411231)+b'\x90'*5)
    return dict(text_encoding=dict(hook=hex(hook),reader='0x411200',codepage=949,rule='UTF-16 UI resource labels always convert to CP949, independently of Windows ACP/UTF-8 beta setting. No system locale changes.'))
