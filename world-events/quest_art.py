"""Display original artwork inside the stock ShowPicture frame above OpenSpeechBox."""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT, SCENES = 218, 172, 10
RAW = WIDTH * HEIGHT
FRAME_BYTES = 53383  # Event.pak / 시작1.Spr, decompressed including the _RLE file header
HEADER = struct.pack("<4I", int.from_bytes(b"SQA2", "little"), WIDTH, HEIGHT, SCENES)
FOCUS_X = (.35, .51, .40, .75, .51, .47)


def import_atlas():
    from PIL import Image, ImageOps
    palette = Image.new("P", (1, 1))
    palette.putpalette((ROOT / "extracted/Data.pak/steel.pal").read_bytes()[:768])
    payload = bytearray(HEADER)
    for filename,rows,focus in (("quest_art_atlas.png",3,FOCUS_X),("legend_machine_atlas.png",2,(.5,)*4)):
        with Image.open(ROOT/filename) as source:
            atlas=source.convert("RGB")
        for scene,center in enumerate(focus):
            x, y = scene % 2, scene // 2
            box = (x * atlas.width // 2 + 3, y * atlas.height // rows + 3,
                   (x + 1) * atlas.width // 2 - 3, (y + 1) * atlas.height // rows - 3)
            panel = ImageOps.fit(atlas.crop(box), (WIDTH, HEIGHT), Image.Resampling.LANCZOS,
                                 centering=(center,.5))
            payload.extend(panel.quantize(palette=palette, dither=Image.Dither.NONE).tobytes())
    assert len(payload) == 16 + SCENES * RAW
    (ROOT / "QuestScenes.sqa").write_bytes(payload)


def emit(put, asm, address, stock_speech):
    def code(source):
        return put(asm(source, address()))

    filename = put(("QuestScenes.sqa" + "\0").encode("utf-16le"))
    kernel = put(b"kernel32.dll\0")
    path_api = put(b"GetModuleFileNameW\0")
    open_api = put(b"CreateFileW\0")
    picture_name = put("시작1.Spr".encode("cp949") + b"\0")
    # Stock ShowPicture loads a private copy of the framed sprite. The four
    # opaque runs on each row contain 63/63/63/61 pixels. Validate the complete
    # layout before writing only the inside rectangle, keeping the original trim.
    inset = code("""
        push ebp; push ebx; push esi; push edi;
        mov eax,[esp+20]; mov esi,[esp+24]; test esi,esi; jz invalid;
        test eax,eax; jz invalid; mov edx,[eax+0x30]; test edx,edx; jz invalid;
        mov ebp,[edx]; test ebp,ebp; jz invalid; cmp ebp,[edx+4]; jne invalid;
        cmp dword ptr [ebp],0x454c525f; jne invalid; cmp dword ptr [ebp+4],1; jne invalid;
        cmp dword ptr [ebp+8],4; jne invalid; add ebp,12; cmp [eax+0x2c],ebp; jne invalid;
        cmp dword ptr [ebp],250; jne invalid; cmp dword ptr [ebp+4],206; jne invalid;
        cmp dword ptr [ebp+8],250; jne invalid; cmp dword ptr [ebp+12],206; jne invalid;
        lea ebx,[ebp+16]; lea edx,[ebp+840]; mov eax,824; mov ecx,206;
      check_row:
        cmp [ebx],eax; jne invalid; cmp byte ptr [edx],0xbf; jne invalid;
        cmp byte ptr [edx+64],0xbf; jne invalid; cmp byte ptr [edx+128],0xbf; jne invalid;
        cmp byte ptr [edx+192],0xbd; jne invalid; dec ecx; jz last_row;
        cmp byte ptr [edx+254],0; jne invalid;
        add ebx,4; add edx,255; add eax,251; jmp check_row;
      last_row:
        cmp byte ptr [edx+254],1; jne invalid;
      copy_rows:
        lea edx,[ebp+840+17*255]; mov ebx,172; cld;
      copy_row:
        lea edi,[edx+17]; mov ecx,47; rep movsb; inc edi;
        mov ecx,63; rep movsb; inc edi; mov ecx,63; rep movsb; inc edi;
        mov ecx,45; rep movsb; add edx,255; dec ebx; jnz copy_row;
        mov eax,1; jmp finish;
      invalid:
        xor eax,eax;
      finish:
        pop edi; pop esi; pop ebx; pop ebp; ret 8;
    """)
    # Load relative to the executable, including Unicode game directories.
    # Locals: 1024 WCHAR path, header, count, handle, allocation, CreateFileW.
    load = code(f"""
        push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,2080;
        mov esi,esp; mov dword ptr [esi+2072],0;
        cmp dword ptr [ebp+8],{SCENES}; jae fail;
        push {kernel}; call dword ptr [0x460060]; test eax,eax; jz fail; mov ebx,eax;
        push {open_api}; push ebx; call dword ptr [0x460100]; test eax,eax; jz fail;
        mov [esi+2076],eax; push {path_api}; push ebx; call dword ptr [0x460100];
        test eax,eax; jz fail; push 1024; push esi; push 0; call eax;
        test eax,eax; jz fail; cmp eax,1024; jae fail;
      slash:
        dec eax; js fail; cmp word ptr [esi+eax*2],92; jne slash;
        inc eax; cmp eax,{1024-len("QuestScenes.sqa")-1}; ja fail;
        lea edi,[esi+eax*2]; push esi; mov esi,{filename}; mov ecx,{len("QuestScenes.sqa")+1}; cld; rep movsw; pop esi;
        push 0; push 0x80; push 3; push 0; push 1; push 0x80000000; push esi;
        call dword ptr [esi+2076]; cmp eax,-1; je fail; mov [esi+2068],eax;
        lea edx,[esi+2064]; lea ecx,[esi+2048]; push 0; push edx; push 16; push ecx; push eax;
        call dword ptr [0x460090]; test eax,eax; jz close_file;
        cmp dword ptr [esi+2064],16; jne close_file;
        cmp dword ptr [esi+2048],{int.from_bytes(b"SQA2","little")}; jne close_file;
        cmp dword ptr [esi+2052],{WIDTH}; jne close_file; cmp dword ptr [esi+2056],{HEIGHT}; jne close_file;
        cmp dword ptr [esi+2060],{SCENES}; jne close_file;
        mov ebx,[ebp+8]; imul ebx,{RAW}; add ebx,16;
        push 0; push 0; push ebx; push dword ptr [esi+2068]; call dword ptr [0x460114]; cmp eax,ebx; jne close_file;
        push {RAW}; call 0x450452; add esp,4; test eax,eax; jz close_file;
        mov [esi+2072],eax; lea ecx,[esi+2064];
        push 0; push ecx; push {RAW}; push eax; push dword ptr [esi+2068]; call dword ptr [0x460090];
        test eax,eax; jz bad_read; cmp dword ptr [esi+2064],{RAW}; jne bad_read;
        jmp close_file;
      bad_read:
        push dword ptr [esi+2072]; call 0x4500e6; add esp,4; mov dword ptr [esi+2072],0;
      close_file:
        push dword ptr [esi+2068]; call dword ptr [0x460040];
      fail:
        mov eax,[esi+2072]; add esp,2080; pop edi; pop esi; pop ebx; pop ebp; ret 4;
    """)
    # Missing resources are unsafe for the stock picture loader. Check the
    # original private decompressed length through the same archive resolver.
    speech = code(f"""
        push ebp; mov ebp,esp; push ebx; push esi; push edi;
        push dword ptr [ebp+20]; call {load}; test eax,eax; jz plain; mov edi,eax;
        push 0; push {picture_name}; call 0x447c50; add esp,8; test eax,eax; jz free_plain;
        mov ebx,[eax+4]; push eax; call 0x447da0; add esp,4; cmp ebx,{FRAME_BYTES}; jne free_plain;
        sub esp,0x34; mov esi,esp; mov ecx,esi; call 0x412380;
        push 0; push {picture_name}; push dword ptr [ebp+8]; mov ecx,esi; call 0x412410;
        test eax,eax; jz abandon; push edi; push esi; call {inset}; test eax,eax; jz abandon;
        push edi; call 0x4500e6; add esp,4;
        push dword ptr [ebp+16]; push dword ptr [ebp+12]; push dword ptr [ebp+8]; call {stock_speech};
        mov ecx,esi; call 0x4123c0; add esp,0x34; jmp done;
      abandon:
        mov ecx,esi; call 0x4123c0; add esp,0x34;
      free_plain:
        push edi; call 0x4500e6; add esp,4;
      plain:
        push dword ptr [ebp+16]; push dword ptr [ebp+12]; push dword ptr [ebp+8]; call {stock_speech};
      done:
        pop edi; pop esi; pop ebx; pop ebp; ret 16;
    """)
    return dict(quest_art_speech=hex(speech), quest_art_load=hex(load),
                quest_art_inset=hex(inset), quest_art_draw=hex(0x412550))


if __name__ == "__main__":
    import_atlas()

