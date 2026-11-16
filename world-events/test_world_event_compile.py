"""Compile actual freestanding C and execute its exported x86 functions."""
from pathlib import Path
import struct
import tempfile
import world_event_compile as C
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *

checks=0
def check(condition,name):
    global checks
    checks+=1
    assert condition,name
def reject(action,name):
    try:action()
    except (ValueError,RuntimeError):check(True,name)
    else:raise AssertionError(name)

with tempfile.TemporaryDirectory(prefix='SteelWorldC-') as temp:
    root=Path(temp);include=root/'include space';include.mkdir()
    (include/'api.h').write_text('#define STD_API 0x400100u\n#define THIS_API 0x400200u\n')
    source=root/'fixture.c'
    source.write_text('''
#include "api.h"
typedef unsigned (__stdcall *StdApi)(unsigned);
typedef unsigned (__thiscall *ThisApi)(void *,unsigned);
static const unsigned table[4]={7,11,17,23};
__declspec(noinline) static unsigned __stdcall one(unsigned value){return value+3;}
__declspec(noinline) static unsigned __stdcall two(unsigned value){return value*7;}
static StdApi const functions[2]={one,two};
__declspec(dllexport) unsigned __stdcall evaluate(unsigned index,unsigned value){
 return ((StdApi)STD_API)(value)+table[index&3];
}
__declspec(dllexport) unsigned __stdcall this_probe(unsigned value){
 return ((ThisApi)THIS_API)((void*)0x1001000u,value)+5;
}
__declspec(dllexport) unsigned __stdcall internal(unsigned index,unsigned value){
 return functions[index&1](value);
}
__declspec(dllexport) unsigned __stdcall _leading(unsigned value){return value+19;}
''')
    output=root/'fixture.dll'
    image,exports=C.compile_image(source,include,0x540000,output,['evaluate','this_probe','internal','_leading'])
    check(len(image)%4096==0,'image page extent')
    pe=pefile.PE(data=image)
    check(pe.OPTIONAL_HEADER.ImageBase==0x540000,'fixed base')
    check(pe.OPTIONAL_HEADER.AddressOfEntryPoint==0,'no DLL startup')
    check(pe.FILE_HEADER.Characteristics&1,'relocations stripped flag')
    check(not pe.OPTIONAL_HEADER.DllCharacteristics&0x60,'ASLR disabled')
    with pefile.PE(str(output)) as raw_pe:check(raw_pe.verify_checksum(),'normalized DLL checksum')
    check(all(not d.Size and not d.VirtualAddress for i,d in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY) if i in (1,5,9,12,13)),'no runtime dependencies')
    check(all(not s.Characteristics&0x80000000 for s in pe.sections),'no writable sections')
    check(set(exports)=={'evaluate','this_probe','internal','_leading'},'exact requested export names')
    check(C._export_name('_example@8')=='example','stdcall name decoration')
    check(C._export_name('__example@8')=='_example','leading underscore decoration')
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x200000);u.mem_map(0x1000000,0x400000)
    u.mem_write(0x540000,image);seen=[]
    def read(where):return struct.unpack('<I',u.mem_read(where,4))[0]
    def write(where,value):u.mem_write(where,struct.pack('<I',value&0xffffffff))
    def boundary(u,address,size,data):
        if address==0x13df000:u.emu_stop()
        elif address in (0x400100,0x400200):
            sp=u.reg_read(UC_X86_REG_ESP);value=read(sp+4);seen.append(address)
            if address==0x400200:check(u.reg_read(UC_X86_REG_ECX)==0x1001000,'thiscall ECX object')
            u.reg_write(UC_X86_REG_EAX,value*2 if address==0x400100 else value+100)
            u.reg_write(UC_X86_REG_ESP,sp+8);u.reg_write(UC_X86_REG_EIP,read(sp))
    u.hook_add(UC_HOOK_CODE,boundary)
    def no_image_write(u,access,address,size,value,data):
        assert not 0x540000<=address<0x540000+len(image),'compiled code tried to modify RX image'
    u.hook_add(UC_HOOK_MEM_WRITE,no_image_write)
    def call(name,*args):
        sp=0x13f0000;write(sp,0x13df000)
        for i,value in enumerate(args):write(sp+4+i*4,value)
        preserved=(UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)
        for i,reg in enumerate(preserved):u.reg_write(reg,0xaabb0000+i)
        u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(exports[name],0,count=10000)
        check(u.reg_read(UC_X86_REG_EIP)==0x13df000,'export returned')
        check(u.reg_read(UC_X86_REG_ESP)==sp+4+len(args)*4,'stdcall argument cleanup')
        check(all(u.reg_read(reg)==0xaabb0000+i for i,reg in enumerate(preserved)),'callee saved registers')
        return u.reg_read(UC_X86_REG_EAX)
    for i in range(8):check(call('evaluate',i,13)==26+(7,11,17,23)[i&3],'const table + stock stdcall function pointer')
    for i in range(4):check(call('this_probe',i)==105+i,'stock thiscall function pointer')
    for i in range(8):check(call('internal',i,13)==(16 if i%2==0 else 91),'internal function pointer relocations resolved')
    check(call('_leading',1)==20,'underscore export')
    check(seen.count(0x400100)==8 and seen.count(0x400200)==4,'actual external boundaries used')

    reject(lambda:C.read_image(output,0x550000,['evaluate']),'wrong linked base')
    reject(lambda:C.read_image(output,0x540001,['evaluate']),'unaligned base')
    reject(lambda:C.read_image(output,0x530000,['evaluate']),'outside rework base')
    reject(lambda:C.read_image(output,0x540000,['missing']),'missing export')
    reject(lambda:C.read_image(output,0x540000,['evaluate','evaluate']),'duplicate requested export')
    original=output.read_bytes()
    def tamper(label,change):
        path=root/(label+'.dll');modified=pefile.PE(data=original);change(modified);modified.write(str(path));modified.close();return path
    for directory,label in ((1,'imports'),(5,'relocations'),(9,'tls'),(12,'iat'),(13,'delay_imports')):
        def change(p,index=directory):p.OPTIONAL_HEADER.DATA_DIRECTORY[index].VirtualAddress=0x2000;p.OPTIONAL_HEADER.DATA_DIRECTORY[index].Size=16
        path=tamper(label,change)
        reject(lambda path=path:C.read_image(path,0x540000,['evaluate']),'reject '+label)
    path=tamper('writable',lambda p:setattr(p.sections[0],'Characteristics',p.sections[0].Characteristics|0x80000000))
    reject(lambda:C.read_image(path,0x540000,['evaluate']),'writable executable rejected')
    path=tamper('oversize',lambda p:setattr(p.OPTIONAL_HEADER,'SizeOfImage',0x80000))
    reject(lambda:C.read_image(path,0x540000,['evaluate']),'capacity rejected')
    path=tamper('entry',lambda p:setattr(p.OPTIONAL_HEADER,'AddressOfEntryPoint',0x1000))
    reject(lambda:C.read_image(path,0x540000,['evaluate']),'DLL startup rejected')
    # The normalized file retains readonly relocation bytes, but never applies them.
    def restore_rebase(p):
        section=next(s for s in p.sections if s.Name.startswith(b'.reloc'))
        d=p.OPTIONAL_HEADER.DATA_DIRECTORY[5];d.VirtualAddress=section.VirtualAddress;d.Size=section.Misc_VirtualSize
        return section
    def corrupt_rebase(p):
        section=restore_rebase(p)
        first=struct.unpack('<H',p.get_data(section.VirtualAddress+8,2))[0]
        page=struct.unpack('<I',p.get_data(section.VirtualAddress,4))[0]
        p.set_dword_at_rva(page+(first&0xfff),0x400100)
    path=tamper('bad_rebase',corrupt_rebase)
    reject(lambda:C._fix_at_linked_base(path,0x540000),'external pointer relocation rejected')
    def truncate_rebase(p):
        restore_rebase(p);p.OPTIONAL_HEADER.DATA_DIRECTORY[5].Size+=2
    path=tamper('truncated_rebase',truncate_rebase)
    reject(lambda:C._fix_at_linked_base(path,0x540000),'incomplete rebase directory rejected')
    def wrong_rebase_type(p):
        section=restore_rebase(p);entry=struct.unpack('<H',p.get_data(section.VirtualAddress+8,2))[0]
        p.set_word_at_rva(section.VirtualAddress+8,(entry&0xfff)|0x1000)
    path=tamper('wrong_rebase_type',wrong_rebase_type)
    reject(lambda:C._fix_at_linked_base(path,0x540000),'non-HIGHLOW relocation rejected')

    writable=root/'writable.c';writable.write_text('__declspec(dllexport) unsigned __stdcall bad(void){static volatile unsigned n=7;return ++n;}')
    reject(lambda:C.compile_image(writable,include,0x540000,root/'writable_source.dll',['bad']),'actual writable static source rejected')
    large=root/'large.c';large.write_text('static const char big[600000]={[599999]=1};__declspec(dllexport) unsigned __stdcall big_read(unsigned n){return big[n%600000];}')
    reject(lambda:C.compile_image(large,include,0x540000,root/'large.dll',['big_read']),'actual oversized source rejected')
print('PASS: %d compiler/native checks; real Zig fixed-base C, const data, internal/external stdcall/thiscall pointers, export decoration, RX sections, import/TLS/relocation/capacity guards' % checks)
