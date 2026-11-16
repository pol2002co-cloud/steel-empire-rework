"""Atomic native-save clone and a bounded expedition appendix contract."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

SAVE=0x401160
SAVE_BYTES=bytes.fromhex('83ec108b442414')
MAX_PAYLOAD=8192

def emit(put,asm,address,read):
    source=read(SAVE,0xa8)
    assert source[:7]==SAVE_BYTES
    instructions=list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(source,SAVE))
    assert instructions[-1].address==0x401207 and instructions[-1].mnemonic=='ret'
    body=[]
    for ins in instructions:
        text=ins.mnemonic+' '+ins.op_str
        if ins.address==0x40116d:
            # Second cdecl argument replaces the immutable stock filename table.
            text='mov ecx,[esp+0x20]'
        elif ins.address==0x4011f5:
            text='mov eax,[esi+0xc];and eax,0x20;mov [esp+4],eax;push esi'
        elif ins.address==0x4011fe:
            text='test eax,eax;jnz failed;cmp dword ptr [esp+4],0;jnz failed;mov eax,1;jmp cleanup;failed:xor eax,eax;cleanup:'
        body.append(text)
        if ins.address==0x401175:
            body.append('test eax,eax;jnz opened;add esp,8;pop esi;add esp,0x10;ret;opened:')
    native_save=put(asm(';'.join(body),address()))
    return dict(native_save=hex(native_save),max_payload=MAX_PAYLOAD,
                abi='cdecl native_save(slot,temporary_filename); returns0 on open/write/close failure',
                save_entry=hex(SAVE),save_bytes=SAVE_BYTES.hex(),footer_bytes=32,
                version=1,magic=[0x58504553,0x31564153],
                checksum='CRC32 payload, native16-byte header and footer; character-editor body edits remain compatible',
                safety='Same-directory temporary native save, append/flush/atomic replace; existing slot remains intact on failure')
