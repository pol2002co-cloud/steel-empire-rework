from pathlib import Path
import sys,struct,hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'tools/python-deps'))
import pefile
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from archive import SRC,entries,decode
ks=Ks(KS_ARCH_X86,KS_MODE_32)
def asm(s,a):return bytes(ks.asm(s,a)[0])
def sha(b):return hashlib.sha256(b).hexdigest()
def makepak(files):
 out=bytearray(); index=bytearray()
 for name,data in files.items():
  nb=name.encode('cp949'); index+=bytes([len(nb),0])+struct.pack('<III',len(out),len(data),len(data))+nb+b'\0';out+=data
 off=len(out);out+=index+struct.pack('<II',off,len(files))+b'\x12'
 return out
def build():
 expected='65bf8699804849f36cef9108eebe88f8c9f1661ac77ea5c2e6688ae347795fde'
 candidates=[SRC/'SteelEmpire.exe',*sorted((SRC/'ReworkBackups').glob('*/SteelEmpire.exe'))]
 original=next((p.read_bytes() for p in candidates if p.is_file() and sha(p.read_bytes())==expected),None)
 assert original is not None,'Unsupported original executable; no verified backup found'
 b=bytearray(original); pe=pefile.PE(data=b)
 def offset(a):return pe.get_offset_from_rva(a-0x400000)
 # Add a dedicated executable/read-only section; existing sections are untouched.
 raw=(len(b)+0xfff)&~0xfff; va=0x400000+((pe.OPTIONAL_HEADER.SizeOfImage+0xfff)&~0xfff)
 capacity=0x20000
 section=bytearray(capacity); cursor=0; edits=[]
 def put(data):
  nonlocal cursor
  at=cursor;section[at:at+len(data)]=data;cursor=(at+len(data)+15)&~15;assert cursor<capacity;return va+at
 machines=(ROOT/'extracted/Data.pak/machine.dat').read_bytes()
 groups={0:[],1:[]}; names={}
 for i in range(24):
  rec=machines[4+i*240:4+(i+1)*240];typ=struct.unpack_from('<I',rec,32)[0]
  if typ in groups:
   name=rec[:32].split(b'\0')[0];groups[typ].append((i+1,put(name+b'\0')));names[i+1]=name.decode('cp949')
 items=bytearray((ROOT/'extracted/Data.pak/item.dat').read_bytes())
 medals={54:5000,55:5000,56:3000,57:10000,58:7000,59:4000,60:12000}
 medal_names={i:put(items[4+(i-1)*288:4+(i-1)*288+32].split(b'\0')[0]+b'\0') for i in medals}
 for i,price in medals.items():struct.pack_into('<I',items,4+(i-1)*288+0x9c,price)
 code=['pushfd','pushad','mov ebx, [esi+4]','test ebx, ebx','jz done','mov eax, [ebx]','cmp eax, 0x462354','je ground','cmp eax, 0x462380','je air','cmp eax,0x4622c8','je medals','jmp done']
 for typ,label in [(0,'ground'),(1,'air')]:
  code+=[label+':']
  for ident,ptr in groups[typ]:
   # A machine list node is next/prev followed by the 0x1a8-byte record, id at +4.
   code += ['mov edx, [ebx+0x5c]','mov edi, [edx]',f'scan{ident}:','cmp edi, edx',f'je add{ident}',f'cmp dword ptr [edi+0xc], {ident}',f'je next{ident}','mov edi, [edi]',f'jmp scan{ident}',f'add{ident}:',f'push {ptr}','mov ecx, ebx','call 0x42a820',f'next{ident}:']
  code+=['jmp done']
 code+=['medals:']
 for ident,ptr in medal_names.items():
  code+=['mov edx,[ebx+0x5c]','mov edi,[edx]',f'medal_scan{ident}:','cmp edi,edx',f'je medal_add{ident}',f'cmp dword ptr [edi+8],{ident}',f'je medal_next{ident}','mov edi,[edi]',f'jmp medal_scan{ident}',f'medal_add{ident}:',f'push {ptr}','mov ecx,ebx','call 0x429480',f'medal_next{ident}:']
 code+=['done:','popad','popfd','push 0x50','call 0x450452','jmp 0x44bc1f']
 market=put(asm(';'.join(code),va+cursor))
 # Replace only the training UI enumeration, using valid character templates 1..13.
 # Costs remain handled by the game's original queue/resource logic.
 code='''mov ebx, 1; train_loop:; mov ecx, [0x4880e8]; lea edx, [esp+0xc]; push edx; push ebx; call 0x415370; test eax,eax; jz train_next; mov ecx,[esp+0xb8]; mov edx,[esp+0xc]; push 1; push 0; push ecx; mov ecx,[esi+0x44]; push edx; call 0x4101a0; train_next:; inc ebx; cmp ebx,13; jle train_loop; jmp 0x424a8e'''
 training=put(asm(code,va+cursor))
 # Training completion: retain original base/specialty/facility bonuses, then
 # add floor((captain_level-1)/3). The real game level-up routine handles stats.
 code='''push eax; push edx; mov eax,[esi+4]; mov eax,[eax+0xf4]; test eax,eax; jz level_done; mov eax,[eax+0x48]; cmp eax,1; jle level_done; cmp eax,82; jle level_valid; mov eax,82; level_valid:; dec eax; xor edx,edx; mov ecx,3; div ecx; add edi,eax; level_done:; cmp edi,30; jle level_cap_done; mov edi,30; level_cap_done:; pop edx; pop eax; mov ecx,[0x4880e8]; jmp 0x431c88'''
 instructor=put(asm(code,va+cursor))
 # At the one-time winner selection, choose the local human object (+0xa4).
 # Mark a folded human active so the existing payout loop still awards the pot.
 # No bankroll is fabricated; normal deductions and award routine remain intact.
 code='''mov ecx,[esi+0xa4]; test ecx,ecx; jz poker_fallback; mov dword ptr [ecx+8],1; jmp 0x44e0f7; poker_fallback:; mov ecx,[esi+eax*4+0x94]; jmp 0x44e0f7'''
 poker=put(asm(code,va+cursor))
 # Retain recruited player companions in their roster after battle cleanup.
 code='''cmp dword ptr [edx+8],3; jne casualty_original; cmp dword ptr [ebp+4],1; jne casualty_original; mov dword ptr [edx+4],1; mov dword ptr [edx+0x10],0; test edi,edi; jz casualty_done; dec dword ptr [edi+0x1c]; casualty_done:; jmp 0x438191; casualty_original:; cmp dword ptr [edx+8],3; jne 0x438181; jmp 0x43813b'''
 casualty=put(asm(code,va+cursor))
 # Tick original clock, recover on calendar-day transition using existing status.
 code='''pushfd; pushad; mov esi,[0x48d388]; call 0x446740; mov eax,[0x48d388]; xor edx,edx; mov ecx,24; div ecx; mov edi,eax; mov eax,esi; xor edx,edx; div ecx; cmp eax,edi; je return_done; mov eax,[ebx+0xa8]; test eax,eax; jz return_done; mov eax,[eax+0x7c]; test eax,eax; jz return_done; cmp dword ptr [eax+4],1; jne return_done; mov edi,[eax+0x50a4c]; test edi,edi; jz return_done; mov esi,[edi]; return_loop:; cmp esi,edi; je return_done; mov eax,[esi+8]; test eax,eax; jz return_next; cmp dword ptr [eax+8],3; jne return_next; cmp dword ptr [eax+4],1; jne return_next; mov dword ptr [eax+4],0; mov dword ptr [eax+0x10],0; mov edx,[eax+0x58]; mov [eax+0x54],edx; return_next:; mov esi,[esi]; jmp return_loop; return_done:; popad; popfd; jmp 0x421ea6'''
 recovery=put(asm(code,va+cursor))
 # Prevent month-end recovery from returning companions before midnight.
 code='''cmp dword ptr [eax+4],1; jne 0x430586; cmp dword ptr [eax+8],3; je 0x430586; jmp 0x430547'''
 monthly=put(asm(code,va+cursor))
 # One per-battle deadline, allocated with the battle object and initialized
 # in its constructor. The enemy commander object remains valid until cleanup.
 battle_init=put(asm('mov [esi+0x1ec],ebp; mov [esi+0xe48],ebp; jmp 0x439423',va+cursor))
 code='''pushfd; pushad; mov eax,[esi+0x200]; cmp dword ptr [eax+0x138],0; je collapse_finish; cmp dword ptr [esi+0x1d8],5; je collapse_done; mov eax,[esi+0x204]; cmp dword ptr [eax+0x138],0; jne collapse_done; mov edx,[esi+0xe48]; test edx,edx; jnz deadline_set; mov edx,[esi+0x1e0]; add edx,3; mov [esi+0xe48],edx; deadline_set:; mov eax,[esi+0x1e4]; test eax,eax; jle limit_done; cmp eax,edx; jge limit_done; mov [esi+0x1e4],edx; limit_done:; mov edi,0; lea ebx,[esi+0x36c]; mov ecx,81; collapse_scan:; mov eax,[ebx]; test eax,eax; jz collapse_next; cmp dword ptr [eax+0x138],0; je collapse_next; cmp [esi+0x1e0],edx; jl collapse_alive; mov dword ptr [eax+0x138],0; mov dword ptr [eax+0x54],0; mov dword ptr [eax+0x13c],0; jmp collapse_next; collapse_alive:; inc edi; collapse_next:; add ebx,4; loop collapse_scan; test edi,edi; jnz collapse_done; collapse_finish:; cmp dword ptr [esi+0x1d8],5; je collapse_done; mov dword ptr [esi+0x1d8],6; collapse_done:; popad; popfd; mov eax,[esi+0x200]; mov ebx,5; jmp 0x43c65f'''
 collapse=put(asm(code,va+cursor))
 from minimap_patch import emit
 minimap_find,minimap_draw=emit(put,asm,lambda:va+cursor)
 def patch(a,old,new):
  o=offset(a);assert b[o:o+len(old)]==old,(hex(a),b[o:o+len(old)].hex(),old.hex())
  assert len(new)==len(old);b[o:o+len(new)]=new;edits.append({'va':hex(a),'before':old.hex(),'after':new.hex()})
 patch(0x44bc18,asm('push 0x50;call 0x450452',0x44bc18),asm(f'jmp {market}',0x44bc18)+b'\x90\x90')
 patch(0x424a3c,asm('mov ecx,[esi+0x88]',0x424a3c),asm(f'jmp {training}',0x424a3c)+b'\x90')
 patch(0x431c82,asm('mov ecx,[0x4880e8]',0x431c82),asm(f'jmp {instructor}',0x431c82)+b'\x90')
 patch(0x44e0f0,asm('mov ecx,[esi+eax*4+0x94]',0x44e0f0),asm(f'jmp {poker}',0x44e0f0)+b'\x90\x90')
 patch(0x438135,asm('cmp dword ptr [edx+8],3; jne 0x438181',0x438135),asm(f'jmp {casualty}',0x438135)+b'\x90')
 patch(0x421ea1,asm('call 0x446740',0x421ea1),asm(f'jmp {recovery}',0x421ea1))
 patch(0x430541,asm('cmp dword ptr [eax+4],1; jne 0x430586',0x430541),asm(f'jmp {monthly}',0x430541)+b'\x90')
 patch(0x4381aa,asm('je 0x4381bf',0x4381aa),asm('je 0x4381c5',0x4381aa))
 for a in [0x41b0fc,0x41b484,0x44acab]:
  patch(a,asm('push 0xe48',a),asm('push 0xe54',a))
 patch(0x43941d,asm('mov [esi+0x1ec],ebp',0x43941d),asm(f'jmp {battle_init}',0x43941d)+b'\x90')
 patch(0x43c62c,asm('mov eax,[esi+0x200]',0x43c62c),asm(f'jmp {collapse}',0x43c62c)+b'\x90')
 patch(0x40a602,asm('call 0x413c20',0x40a602),asm(f'jmp {minimap_draw}',0x40a602))
 # Preserve the computed per-unit battle experience instead of clamping to 200.
 patch(0x439d9f,asm('mov esi,200',0x439d9f),b'\x90'*5)
 from expansion_patch import emit as expand
 expansion=expand(put,asm,lambda:va+cursor,patch,lambda a,n:original[offset(a):offset(a)+n])
 from enemy_patch import emit as enemy_emit
 enemy_hook=enemy_emit(put,asm,lambda:va+cursor,patch)
 from retraining_ui_patch import emit as retrain_ui_emit
 retrain_ui=retrain_ui_emit(put,asm,lambda:va+cursor,patch,lambda a,n:original[offset(a):offset(a)+n])
 from victory_cheat_patch import emit as victory_emit
 victory_cheat=victory_emit(put,asm,lambda:va+cursor,patch)
 from xp_share_patch import emit as xp_share_emit
 xp_share=xp_share_emit(put,asm,lambda:va+cursor,patch)
 # Only temporary tavern mercenary records: zero their poker bankroll on entry.
 patch(0x42bc4c,asm('mov ecx,[ebx+0x14]',0x42bc4c),asm('xor ecx,ecx;nop',0x42bc4c))
 # The hiring dialog still requires the player's affirmative choices. Its
 # compatibility score takes the stock unconditional, zero-fee acceptance path.
 tavern_accept=put(asm('mov eax,71;ret 4',va+cursor))
 patch(0x42cb41,asm('call 0x42ca10',0x42cb41),asm(f'call {tavern_accept}',0x42cb41))
 from event_journal_patch import emit as journal_emit
 journal=journal_emit(put,asm,lambda:va+cursor,patch)
 from event_force_patch import emit as force_emit
 event_force=force_emit(put,asm,lambda:va+cursor,patch)
 from quest_cleanup_patch import emit as quest_emit
 quest_cleanup=quest_emit(put,asm,lambda:va+cursor,patch)
 from text_encoding_patch import emit as text_emit
 text_encoding=text_emit(put,asm,lambda:va+cursor,patch)
 hdr=pe.sections[-1].get_file_offset()+40
 assert not any(b[hdr:hdr+40]);struct.pack_into('<8sIIIIIIHHI',b,hdr,b'.rework\0',cursor,va-0x400000,capacity,raw,0,0,0,0,0x60000020)
 struct.pack_into('<H',b,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),pe.FILE_HEADER.NumberOfSections+1)
 struct.pack_into('<I',b,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),va-0x400000+capacity)
 struct.pack_into('<I',b,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+capacity)
 b+=b'\0'*(raw-len(b))+section
 p=pefile.PE(data=b);struct.pack_into('<I',b,p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),p.generate_checksum())
 char=bytearray((ROOT/'extracted/Data.pak/char.dat').read_bytes())
 costs={7:(45,30,10000,25),8:(5,10,12000,30),11:(15,10,6000,20),12:(20,5,6000,20),13:(0,5,4000,15)}
 for ident,cost in costs.items():struct.pack_into('<4I',char,4+(ident-1)*348+204,*cost)
 out=ROOT/'package';out.mkdir(exist_ok=True)
 (out/'SteelEmpire.exe').write_bytes(b)
 (out/'patch104.pak').write_bytes(makepak({'char.dat':char,'item.dat':items}))
 shutil.copy2(ROOT.parent/'vendor/cnc-ddraw-v7.1.0.0/ddraw.dll',out/'ddraw.dll')
 (out/'ddraw.ini').write_text('[ddraw]\nwidth=1280\nheight=960\nwindowed=true\nfullscreen=false\nmaintas=true\nboxing=false\nmaxfps=60\nvsync=false\nadjmouse=true\nrenderer=auto\nborder=true\nresizable=true\nsavesettings=1\nd3d9_filter=0\nshader=Nearest neighbor\nmaxgameticks=0\n',encoding='ascii')
 manifest={'version':'0.2.0-experimental','source_sha256':sha(original),'output_sha256':sha(b),'patches':edits,'market_hook':hex(market),'training_hook':hex(training),'instructor_hook':hex(instructor),'poker_hook':hex(poker),'training_level_rule':'min(30, original_base_and_facilities + max(0, floor((captain_level - 1) / 3)))','poker_rule':'Human wins every settled hand, including folded hands; original payout logic. Leaving before settlement does not pay out.','machines':names,'training_ids':list(range(1,14)),'new_costs_iron_oil_gold_days':costs,'excluded_boss_ids':list(range(17,22))}
 manifest.update(version='0.3.0-experimental',casualty_hook=hex(casualty),recovery_hook=hex(recovery),monthly_hook=hex(monthly),companion_return='Player recruited companions remain on roster and return at next calendar midnight with full HP; generic mercenary death unchanged.',aircraft_landing='Type 2 air armies pass airport capability check in every town; other garrison restrictions remain.')
 manifest.update(version='0.4.0-experimental',collapse_hook=hex(collapse),battle_init_hook=hex(battle_init),enemy_collapse='Enemy commander death starts a 3-turn deadline. Combat continues until enemy elimination or deadline; remaining enemies are then marked dead and normal battle settlement runs. Player defeat and manual retreat retain original behavior.')
 manifest.update(version='0.5.0-experimental',minimap_find=hex(minimap_find),minimap_draw=hex(minimap_draw),minimap_hover='World minimap: nearest visible town within 4 original-resolution pixels shows a name tooltip; leaves no persistent state; existing click and drag actions unchanged.')
 manifest.update(version='0.6.2-experimental',battle_experience='Removed the 200-per-unit battle XP clamp; original calculation and minimum 5 unchanged',minimap_labels='Hover only, restored v0.5 tooltip behavior',medal_prices=medals,retraining='Level 15+ armored infantry -> heavy armored infantry: armor +20, iron 25, oil 15, gold 5000, 20 days. Six slots; old five-slot saves still load.',airport='A in the city screen opens the stock airport when an aircraft army is stationed there, including airportless towns.',**expansion)
 manifest.update(version='0.7.0-experimental',enemy_strength_hook=hex(enemy_hook),enemy_factions=[12,14,15,16,18,20],enemy_strength='New generated mercenary armies: infantry 79 plus commander; mixed armor 7 vehicles plus 18 infantry; air 9 aircraft. Original class, level, equipment and commander profiles retained. Existing serialized armies are not refilled.')
 manifest.update(version='0.7.1-experimental',**retrain_ui)
 manifest.update(version='0.7.2-experimental',victory_cheat=hex(victory_cheat),victory_cheat_rule='Original Bravo Nike recognition: eliminate all enemy battle units and enter normal victory settlement immediately, bypassing the three-turn commander-collapse delay.')
 manifest.update(version='0.7.3-experimental',**xp_share)
 manifest.update(version='0.7.4-experimental',tavern_hiring='Tavern mercenaries enter with zero poker bankroll; hiring accepts regardless of compatibility, using original confirmation and recruitment flow. Player money and other patrons unchanged.')
 manifest.update(version='0.8.0-experimental',**journal)
 manifest.update(version='0.8.1-experimental',event_force=event_force)
 manifest.update(version='0.8.2-experimental',**quest_cleanup)
 manifest.update(version='0.8.3-experimental',**text_encoding)
 (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8');build()
