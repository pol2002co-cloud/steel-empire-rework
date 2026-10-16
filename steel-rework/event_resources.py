from build import *
sys.stdout.reconfigure(encoding='utf-8');b=(ROOT/'package/SteelEmpire.exe').read_bytes();p=pefile.PE(data=b)
for a in [0x47158c]:
 o=p.get_offset_from_rva(a-0x400000);print(hex(a),b[o:b.find(b'\0',o)].decode('cp949'))
for pak in SRC.glob('*.pak'):
 if pak.name.lower() in ['music.pak','sound.pak','map.pak']:continue
 es=[e for e in entries(pak.read_bytes()) if not e[0].lower().endswith(('.spr','.pal','.bmp','.wav'))]
 print(pak.name,es[:70])
