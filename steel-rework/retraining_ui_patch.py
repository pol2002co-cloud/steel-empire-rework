"""Six-column retraining UI; shared five-column training UI remains original."""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

def emit(put,asm,address,patch,read):
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    def change(a,old,new):
        x,y=asm(old,a),asm(new,a)
        assert len(x)==len(y),(hex(a),old,new)
        patch(a,x,y)
    def clone(start,end,changes):
        target=address(); data=bytearray(read(start,end-start))
        for ins in md.disasm(bytes(data),start):
            replacement=changes.get(ins.address)
            dest=target+ins.address-start
            if replacement:
                encoded=asm(replacement,dest)
            elif ins.mnemonic=='call' and ins.op_str.startswith('0x'):
                encoded=asm('call '+ins.op_str,dest)
            else:continue
            assert len(encoded)==ins.size,(hex(ins.address),replacement)
            data[ins.address-start:ins.address-start+ins.size]=encoded
        assert set(changes)<=set(i.address for i in md.disasm(read(start,end-start),start))
        return put(bytes(data))
    base=clone(0x42b400,0x42b6ed,{
        0x42b505:'mov edi,0xa3',0x42b50a:'lea ebx,[ebp+0x60]',
        0x42b53e:'mov dword ptr [esp+0x30],0x46',
        0x42b583:'mov [ebx-0x18],eax',
        0x42b62d:'mov dword ptr [esp+0x30],0x46',
        0x42b672:'mov [ebx+0x18],eax',
        0x42b675:'add edi,0x46',0x42b67c:'cmp edi,0x247',
    })
    clear=clone(0x42b6f0,0x42b742,{
        0x42b6fc:'cmp esi,6',0x42b717:'mov ecx,[edi+esi*4+0x60]',
        0x42b733:'mov ecx,[edi+esi*4+0x78]',
    })
    change(0x4230fb,'call 0x42b400',f'call {base}')
    change(0x4236b4,'call 0x42b6f0',f'call {clear}')
    change(0x42f5c3,'push 0xa0','push 0xb0')
    # Shift later arrays and owning pointers by one entry per added column.
    for ins in md.disasm(read(0x4230b0,0x648),0x4230b0):
        text=ins.op_str
        if '[esp' in text:continue
        for old,new in [('0x84','0x90'),('0x88','0x94'),('0x8c','0x98'),('0x5c','0x60')]:
            if old in text:
                change(ins.address,ins.mnemonic+' '+text,ins.mnemonic+' '+text.replace(old,new));break
    for a,old,new in [
        (0x42313c,'mov edi,0xb6','mov edi,0xa6'),
        (0x4231a8,'add edi,0x50','add edi,0x46'),
        (0x4231ae,'cmp edi,0x246','cmp edi,0x24a'),
        (0x4231f6,'cmp ebp,5','cmp ebp,6'),
        (0x4231cb,'mov ecx,[edi-0x14]','mov ecx,[edi-0x18]'),
        (0x4231de,'mov ecx,[edi+0x14]','mov ecx,[edi+0x18]'),
        (0x4231e8,'mov ecx,[edi+0x30]','mov ecx,[edi+0x38]'),
        (0x423690,'mov ecx,[ebx-0x14]','mov ecx,[ebx-0x18]'),
        (0x4236c1,'mov ecx,[ebx+0x14]','mov ecx,[ebx+0x18]'),
        (0x4236c9,'mov ecx,[ebx+0x30]','mov ecx,[ebx+0x38]'),
    ]:change(a,old,new)
    return dict(retraining_ui_base=hex(base),retraining_ui_clear=hex(clear))

