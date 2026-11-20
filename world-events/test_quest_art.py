"""Exercise the x86 scene reader, dialogue wrapper and original indexed game blitter."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from build import ROOT, asm, pefile
from archive import SRC, entries, decode
from quest_art import HEADER, WIDTH, HEIGHT, SCENES, RAW, FRAME_BYTES, emit
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP)

STOP = 0x13df000
STACK = 0x13f0000
SURFACE, BITS, BUF = 0x1001000, 0x1050000, 0x1100000
TITLE, PAGE, PARENT = 0x1201000, 0x1202000, 0x1203000
REGS = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
FILENAME = "D:\\게임 모음\\강철제국\\"
ASSET = (ROOT / "QuestScenes.sqa").read_bytes()


def run_all(integrated, preview=None):
    engine = (ROOT / "package/SteelEmpire.exe").read_bytes()
    pe = pefile.PE(data=engine)
    image = pe.get_memory_mapped_image()
    original = (SRC/"Event.pak").read_bytes()
    _,compressed,offset,size,raw_size = next(e for e in entries(original) if e[0].lower()=="시작1.spr")
    frame = original[offset:offset+size]
    frame = bytes(decode(frame)) if compressed else frame
    assert len(frame)==raw_size==FRAME_BYTES
    # Independent reference for the stock illustration: four opaque runs on each line.
    assert struct.unpack_from('<7I',frame)==(0x454c525f,1,4,250,206,250,206)
    rows=[]
    for y in range(206):
        base=28+y*4
        pos=base+struct.unpack_from('<I',frame,base)[0]
        line=bytearray()
        for length in (63,63,63,61):
            assert frame[pos]==128+length
            line.extend(frame[pos+1:pos+1+length])
            pos+=1+length
        rows.append(line)
    def executable_resource(group, number):
        group=next(x for x in pe.DIRECTORY_ENTRY_RESOURCE.entries if str(x.name)==group)
        record=next(x for x in group.directory.entries if x.id==number).directory.entries[0].data.struct
        return pe.get_data(record.OffsetToData,record.Size)
    extra = bytearray()
    def addr(): return 0x600000 + len(extra)
    def put(data):
        base = addr()
        extra.extend(data + b"\0" * (-len(data) % 16))
        return base
    stock=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))["event_journal"]
    if integrated:
        meta = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        assert hashlib.sha256(engine).hexdigest() == meta["output_sha256"]
        funcs = meta["event_journal"]
        plain = int(funcs["speech"], 16)
    else:
        plain = 0x604000
        funcs = emit(put,asm,addr,plain)
    entry = int(funcs["quest_art_speech"],16)
    assert ASSET[:16] == HEADER and len(ASSET) == 16 + SCENES * RAW
    assert len({hashlib.sha256(ASSET[16+s*RAW:16+(s+1)*RAW]).digest() for s in range(SCENES)}) == SCENES
    def run(scene, mode="", clip=False):
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        u.mem_map(0x400000,0x210000);u.mem_write(0x400000,image)
        if extra: u.mem_write(0x600000,bytes(extra))
        u.mem_map(0x1000000,0x400000)
        u.mem_map(0,0x1000)  # Stock x86 exception registration in Picture open/destroy.
        pos=0;events=[];picture=[0];dialog=[0]
        heap=0x1220000;live=set();pitch=672
        frame_at,archive,text_surface=0x1160000,0x11a0000,SURFACE+0x400
        source=bytearray(frame)
        if mode=="bad_sprite":source[12]^=1
        if mode=="bad_row":source[12+840+205*255+254]^=1
        u.mem_write(frame_at,bytes(source))
        def read(p): return struct.unpack("<I",u.mem_read(p,4))[0]
        def write(p,v):u.mem_write(p,struct.pack("<I",v & 0xffffffff))
        def reg(x):return u.reg_read(x)
        def result(n):u.reg_write(UC_X86_REG_EAX,n & 0xffffffff)
        def ret(n=0):
            sp=reg(UC_X86_REG_ESP)
            u.reg_write(UC_X86_REG_EIP,read(sp));u.reg_write(UC_X86_REG_ESP,sp+4+n)
        def args(n):return [read(reg(UC_X86_REG_ESP)+4+i*4) for i in range(n)]
        def stub(a,fn):
            u.hook_add(UC_HOOK_CODE,lambda u,pc,size,data:fn(),begin=a,end=a)
        def api(iat,fn):
            a=0x1300000+(iat & 0xfff)*16
            write(iat,a);stub(a,fn)
        def path():
            assert args(3)[2]==1024
            p=(FILENAME+"SteelEmpire.exe").encode("utf-16le")+b"\0\0"
            u.mem_write(args(3)[1],p);result(1024 if mode=="path" else len(p)//2-1);ret(12)
        def proc():
            name=bytes(u.mem_read(args(2)[1],32)).partition(b"\0")[0]
            result(0 if mode=="api" else {b"GetModuleFileNameW":0x13b0000,b"CreateFileW":0x13b0004}[name]);ret(8)
        def open_file():
            p,access,share,sa,creation,flags,template=args(7)
            assert bytes(u.mem_read(p,len((FILENAME+"QuestScenes.sqa").encode("utf-16le"))+2)).decode("utf-16le")==FILENAME+"QuestScenes.sqa\0"
            assert (access,share,sa,creation,flags,template)==(0x80000000,1,0,3,128,0)
            events.append("open");result(-1 if mode=="absent" else 9);ret(28)
        def read_file():
            nonlocal pos
            fd,buf,n,count,ov=args(5);assert fd==9 and ov==0
            assert n in (16,RAW)
            data=ASSET[pos:pos+n]
            if mode=="bad_header" and not pos:data=b"junk"+data[4:]
            if mode=="short" and pos:data=data[:-1]
            if mode=="truncated_header" and not pos:data=data[:-1]
            u.mem_write(buf,data);write(count,len(data));pos+=len(data)
            result(0 if mode=="read_error" and n==RAW else 1);ret(20)
        def seek():
            nonlocal pos
            fd,pos,hi,origin=args(4);assert (fd,hi,origin)==(9,0,0)
            assert pos==16+scene*RAW
            result(-1 if mode=="seek" else pos);ret(16)
        def alloc():
            nonlocal heap
            size=args(1)[0]
            if size==RAW and mode=="oom":
                result(0)
            else:
                assert size in (RAW,8,12),size
                pointer=BUF if size==RAW else heap
                if size!=RAW:heap+=32
                live.add(pointer);result(pointer)
            ret()
        def free():
            pointer=args(1)[0]
            assert pointer in live,("unknown/double free",hex(pointer))
            live.remove(pointer);ret()
        resource_name="시작1.Spr".encode("cp949")+b"\0"
        def open_archive():
            ptr,flags=args(2);assert bytes(u.mem_read(ptr,len(resource_name)))==resource_name and flags==0
            events.append("preflight")
            write(archive+4,FRAME_BYTES-1 if mode=="bad_size" else FRAME_BYTES)
            result(0 if mode=="no_frame" else archive);ret()
        def resource_ctor():
            ptr,owner=args(2)
            assert bytes(u.mem_read(ptr,len(resource_name)))==resource_name and owner==0
            wrapper=reg(UC_X86_REG_ECX)
            write(wrapper,frame_at);write(wrapper+4,frame_at)
            result(wrapper);ret(8)
        def window_ctor():
            window=reg(UC_X86_REG_ECX);u.mem_write(window,bytes(0x28));ret()
        def surface(sf,x,y,w,h):
            for offset,value in ((0x48,x),(0x4c,y),(0x50,BITS),(0x54,x),(0x58,y),
                    (0x5c,x+w-1),(0x60,y+h-1),(0x6c,pitch)):
                write(sf+offset,value)
        def attach():
            ptr=reg(UC_X86_REG_ECX)
            parent,x,y,w,h=args(5);assert parent==PARENT
            if read(ptr)==0x460c20:
                assert (x,y,w,h)==(190,37,252,210)
                picture[0]=ptr;sf=SURFACE
                assert read(read(ptr)+4)==0x412550
                events.append("picture_open")
            else:
                assert read(ptr)==0x460c34 and (x,y,w,h)==(88,235,463,121)
                dialog[0]=ptr;sf=text_surface
                events.append("speech_open")
            surface(sf,x,y,w,h)
            if clip and sf==SURFACE:
                for offset,value in ((0x54,218),(0x58,54),(0x5c,370),(0x60,188)):write(sf+offset,value)
            write(ptr+0x14,sf);result(1);ret(20)
        def detach():
            ptr=reg(UC_X86_REG_ECX)
            assert ptr==picture[0]
            events.append("picture_close");picture[0]=0;write(ptr+0x14,0);ret()
        def speech_ctor():
            ptr=reg(UC_X86_REG_ECX)
            u.mem_write(ptr,bytes(0x150));write(ptr,0x460c34);ret()
        def speaker():
            assert args(2)==[TITLE,0] and reg(UC_X86_REG_ECX)==dialog[0];ret(8)
        def playback():
            assert args(1)==[PAGE] and reg(UC_X86_REG_ECX)==dialog[0]
            assert read(dialog[0]+0x28)==1
            events.append("text")
            ret(4)
            if picture[0]:
                # Stock modal dispatch redraws the picture sibling before text.
                sp=reg(UC_X86_REG_ESP)-4;write(sp,reg(UC_X86_REG_EIP));u.reg_write(UC_X86_REG_ESP,sp)
                u.reg_write(UC_X86_REG_ECX,picture[0]);u.reg_write(UC_X86_REG_EIP,read(read(picture[0])+4))
        def speech_entry():
            assert args(3)==[PARENT,TITLE,PAGE]
            events.append("speech")
            if not integrated:u.reg_write(UC_X86_REG_EIP,int(stock['speech'],16))
        def do_lock():
            sf=reg(UC_X86_REG_ECX)
            write(sf+0x50,0 if mode=="unavailable_surface" else BITS);ret()
        api(0x460060,lambda:(result(1),ret(4)));api(0x460100,proc)
        api(0x460090,read_file);api(0x460114,seek);api(0x460040,lambda:(events.append("close"),ret(4)))
        stub(0x13b0000,path);stub(0x13b0004,open_file)
        stub(0x450452,alloc);stub(0x4500e6,free)
        stub(0x447c50,open_archive);stub(0x447da0,lambda:(events.append("archive_close"),ret()))
        stub(0x4133a0,window_ctor);stub(0x413510,attach);stub(0x413560,detach)
        stub(0x413480,lambda:ret());stub(0x413c60,resource_ctor);stub(0x413cb0,lambda:ret())
        stub(0x412580,speech_ctor);stub(0x412910,speaker);stub(0x412960,playback)
        stub(0x412760,lambda:(events.append("speech_close"),ret()))
        stub(plain,speech_entry)
        stub(0x403a70,do_lock);stub(0x403a90,lambda:ret())
        # ShowPicture open/draw/close, OpenSpeechBox geometry and the blitter run as shipped.
        initial=bytes([0x55])*(pitch*480);u.mem_write(BITS,initial)
        for i,x in enumerate(REGS):u.reg_write(x,0x76000+i)
        u.reg_write(UC_X86_REG_ESP,STACK)
        for i,x in enumerate((STOP,PARENT,TITLE,PAGE,scene)):write(STACK+4*i,x)
        u.emu_start(entry,STOP,count=3000000)
        assert reg(UC_X86_REG_EIP)==STOP and reg(UC_X86_REG_ESP)==STACK+20
        assert all(reg(r)==0x76000+i for i,r in enumerate(REGS))
        assert not live and not picture[0],(mode,live)
        assert events.count("text")==events.count("speech")==1
        assert events.index("speech")<events.index("text")<events.index("speech_close")
        if "open" in events and mode!="absent":assert events.count("close")==1
        if "preflight" in events and mode!="no_frame":assert events.count("archive_close")==1
        success=(not mode or mode=="unavailable_surface") and 0<=scene<SCENES
        if success:
            assert events.index("picture_open")<events.index("speech")<events.index("speech_close")<events.index("picture_close")
        elif mode in ("bad_row","bad_sprite"):
            assert events.index("picture_close")<events.index("speech")
            assert bytes(u.mem_read(frame_at,len(source)))==bytes(source)
        else:assert "picture_open" not in events
        expected=bytearray(initial)
        if success and mode!="unavailable_surface":
            pixels=ASSET[16+RAW*scene:16+(scene+1)*RAW]
            for y,row in enumerate(rows):
                line=row.copy()
                if 17<=y<189:line[16:234]=pixels[(y-17)*218:(y-16)*218]
                off=(37+y)*pitch+190
                if not clip:expected[off:off+250]=line
                elif 54<=37+y<=188:expected[off+28:off+181]=line[28:181]
        actual=bytes(u.mem_read(BITS,len(expected)))
        assert actual==expected,(scene,mode,clip)
        if preview and scene==0 and success and not mode and not clip:
            render_preview(u,write,surface,text_surface,pitch,executable_resource,preview)
    cases=0
    for scene in range(SCENES):
        for clip in (False,True):run(scene,clip=clip);cases+=1
    for mode in ("absent","path","api","bad_header","truncated_header","seek","short","oom",
                 "read_error","unavailable_surface","no_frame","bad_size","bad_sprite","bad_row"):
        run(2,mode);cases+=1
    for invalid in (SCENES,0xffffffff):run(invalid);cases+=1
    print("PASS stock quest frame:",cases,"cases; all framed images, stock layering, fallback and ABI")
    return cases

def render_preview(u,write,surface,sf,pitch,resource,output):
    """Native drawing paths with a neutral backdrop and a fixed dialogue page."""
    from PIL import Image
    from world_event_simple_catalog import SIMPLE_EVENT_CATALOG
    controls=0x1280000;hangul=0x12e0000;latin=0x12f6000
    for base,name,number in ((controls,'SPRITE',132),(hangul,'FONTS',128),(latin,'FONTS',127)):
        u.mem_write(base,resource(name,number))
    write(0x4880dc,controls+8)
    dialog=0x11b0000;head=dialog+0x200;node=head+0x40
    event=SIMPLE_EVENT_CATALOG[0]
    raw=event['stages'][0]['text']
    words=raw.split();lines=['']
    for word in words:
        current=(lines[-1]+' '+word).strip()
        if len(current.encode('cp949'))>52:lines.append(word)
        else:lines[-1]=current
    lines=lines[:3]
    surface(sf,88,235,463,121)
    for off,value in ((0,1),(8,2),(12,1),(16,hangul+8),(20,latin+8),
                      (24,12),(28,12),(32,6),(36,12),(0x30,pitch),
                      (0x34,88),(0x38,235),(0x3c,551),(0x40,356)):
        write(sf+4+off,value)
    write(dialog+0x14,sf);u.mem_write(dialog+0x3c,event['title'].encode('cp949')+b'\0')
    write(dialog+0x148,head);write(head,node)
    for i,string in enumerate(lines):
        entry=node+i*16;data=head+0x100+i*128
        write(entry,entry+16 if i+1<len(lines) else head);write(entry+8,data)
        u.mem_write(data,string.encode('cp949')+b'\0')
    u.reg_write(UC_X86_REG_ECX,dialog);u.reg_write(UC_X86_REG_ESP,STACK);write(STACK,STOP)
    u.emu_start(0x412e40,STOP,count=5000000)
    assert u.reg_read(UC_X86_REG_EIP)==STOP
    data=bytes(u.mem_read(BITS,pitch*480))
    frame=Image.frombytes('P',(pitch,480),data).crop((0,0,640,480))
    frame.putpalette((ROOT/'extracted/Data.pak/steel.pal').read_bytes()[:768])
    frame.save(output)

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--integrated",action="store_true")
    cli.add_argument("--preview",type=Path,help="write one native-rendered sample dialogue")
    args=cli.parse_args()
    run_all(args.integrated,args.preview)
