"""Legendary forge, depot UI, driver/pilot, stock serialization and combat."""
import sys
import struct
import subprocess
import tempfile
from pathlib import Path

from test_world_event_actions import (
    ARMY, HERO, MRECS, TOWN, MACHINE_DATA, STOP, UC_HOOK_CODE, UC_X86_REG_EAX,
    UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EIP, UC_X86_REG_ESP,
    asm, call, cdecl, machine_stock, manifest, r, ret, w,
)
from legend_machines import MODELS, emit


def fixture():
    u, head, _ = machine_stock([])
    if '--integrated' in sys.argv:
        give = int(manifest['world_events']['legend_machines']['give_legend'], 16)
    else:
        cursor = 0x5f1000
        def put(data):
            nonlocal cursor
            dest = cursor
            u.mem_write(dest, data)
            cursor = (dest + len(data) + 15) & ~15
            return dest
        give = int(emit(put, asm, lambda: cursor)['give_legend'], 16)
    for model in MODELS:
        index = model['base_id'] - 1
        raw = MACHINE_DATA[4 + 240*index:4 + 240*(index+1)]
        record = MRECS + index * 0x1a8
        u.mem_write(record+12, raw[:32])
        u.mem_write(record+0xe8, raw[112:240])
    return u, head, give


def name(u, machine):
    return bytes(u.mem_read(machine + 12, 32)).split(b'\0')[0].decode('cp949')


def equip_through_depot(u, head, machine, model):
    # The actual equipment menu's selected row, its native formation slot,
    # and the owning town inventory. Execute selection, binding and unlink.
    ui, picker, slots = 0x13a1000, 0x13a2000, 0x13a3000
    crew_mask = 0x400 if model['base_id'] in (13,16) else 0x200
    w(u,ui+0x48,picker); w(u,ui+0x4c,slots); w(u,ui+0x54,TOWN+0x50a60)
    w(u,picker+0x2c,head); w(u,picker+0x4c,0)
    w(u,slots+0x28,ARMY); w(u,slots+0x30,0); w(u,slots+0x38,crew_mask)
    w(u,HERO+0x44,crew_mask); w(u,ARMY+0x60+r(u,0x461750)*4,HERO)
    w(u,HERO+0x60,80); w(u,HERO+0x64,50); w(u,HERO+0x70,70)
    def audio(u, pc, size, data):
        if pc==0x4056d0: ret(u,16)
    hook=u.hook_add(UC_HOOK_CODE,audio)
    u.reg_write(UC_X86_REG_EDI,ui); u.reg_write(UC_X86_REG_ESP,0x13e0000)
    u.emu_start(0x42b11d,0x42b19b,count=100000)
    u.hook_del(hook)
    assert u.reg_read(UC_X86_REG_EIP)==0x42b19b
    assert r(u,machine+0x8c)==HERO and r(u,ARMY+0x3c)==machine
    assert r(u,HERO+0x60)==80+model['hit'] and r(u,HERO+0x64)==50+model['evade']
    assert r(u,HERO+0x70)==70+model['skill']


def battle(u, machine, model):
    # Exercise the real tank/air combat constructor, layer selector and
    # battle-parameter copy. Only audio/render-resource and animation output
    # are stubbed in this headless run.
    actor, context, coord = 0x13a4000, 0x13a5000, 0x13a6000
    sprite = 0x13a7000
    assets = []
    def render(u, pc, size, data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if pc==0x446490:
            u.reg_write(UC_X86_REG_EAX,sprite); ret(u,8)
        elif pc==0x413e90: ret(u,4)
        elif pc==0x43eb20:
            assets.extend(bytes(u.mem_read(r(u,sp+n),32)).split(b'\0')[0] for n in (16,20))
            u.reg_write(UC_X86_REG_EAX,sprite); ret(u,20)
        elif pc==0x43f830: ret(u,4)
        elif pc==0x43fa40: ret(u,12)
        elif pc==0x45046d: u.reg_write(UC_X86_REG_EAX,0); ret(u)
    hook=u.hook_add(UC_HOOK_CODE,render)
    call(u,0x43f2a0,context,ARMY,coord,machine,this=actor)
    u.hook_del(hook)
    assert assets==[bytes(u.mem_read(machine+off,32)).split(b'\0')[0] for off in (0x108,0x148)]
    assert all(asset.endswith(b'.nr2') for asset in assets)
    assert r(u,actor+0xa8)==machine and name(u,r(u,actor+0xa8))==model['name']
    assert r(u,actor+0x150)==(1 if model['base_id'] in (13,16) else 2)
    assert [r(u,actor+off) for off in (0x54,0x58,0x70)]==[model['hp']-17,model['hp'],model['defense']]
    assert tuple(r(u,actor+off) for off in (0x7c,0x84,0x88,0x80))==model['attack']
    assert [r(u,actor+off) for off in (0x98,0x9c,0xa0)]==[model['rate'],model['reach'],model['splash']]


editor_records=[]
for index, model in enumerate(MODELS):
    u, head, give = fixture()
    ident=model['base_id']; template=MRECS+(ident-1)*0x1a8
    standard=bytes(u.mem_read(template,0x1a8))
    assert call(u,'give_machine',TOWN,ident)==1
    ordinary=r(u,r(u,head)+8)
    assert call(u,give,TOWN,index)==1
    machine=r(u,r(u,head)+8)
    assert machine!=ordinary and r(u,machine+4)==ident and name(u,machine)==model['name']
    assert bytes(u.mem_read(template,0x1a8))==standard and bytes(u.mem_read(ordinary,0x1a8))==standard
    assert call(u,'find_machine',TOWN,ident)==ordinary
    assert call(u,'take_machine',TOWN,ident)==1
    assert call(u,'take_machine',TOWN,ident)==0 and r(u,r(u,head)+8)==machine

    # Real native disk record in both directions, including damage and the
    # whole numeric profile plus nonserialized stock art reconstruction.
    w(u,machine+0x54,model['hp']-17)
    cdecl(u,0x416da0,machine,0x13a8000)
    editor_records.append(bytes(u.mem_read(0x13a8000,160)))
    loaded=0x13a9000; cdecl(u,0x416e90,0x13a8000,loaded)
    assert bytes(u.mem_read(machine,0x1a8))==bytes(u.mem_read(loaded,0x1a8))
    w(u,r(u,head)+8,loaded)
    equip_through_depot(u,head,loaded,model)
    cdecl(u,0x416da0,loaded,0x13a8000)
    editor_records.append(bytes(u.mem_read(0x13a8000,160)))
    assert r(u,TOWN+0x50a68)==0 and r(u,head)==r(u,head+4)==head
    battle(u,loaded,model)
    w(u,TOWN+0x50654,ARMY); w(u,ARMY+0x34,0)
    call(u,0x437df0,1,this=TOWN)
    assert r(u,r(u,head)+8)==loaded and r(u,loaded+0x8c)==0 and name(u,loaded)==model['name']
    assert [r(u,HERO+off) for off in (0x60,0x64,0x70)]==[80,50,70]

for fault in ('machine_alloc','node_alloc','model_lookup','full','bad_index','broken_list'):
    u,head,give=fixture();index=0;expected=0
    if fault=='machine_alloc':u.fail[0]=0x1a8
    elif fault=='node_alloc':u.fail[0]=12
    elif fault=='model_lookup':w(u,0x10e0000,1)
    elif fault=='full':w(u,TOWN+0x50a68,10000);expected=2
    elif fault=='bad_index':index=4
    else:w(u,head+4,0)
    before=bytes(u.mem_read(TOWN+0x50a60,12)),bytes(u.mem_read(head,12))
    assert call(u,give,TOWN,index)==expected
    assert before==(bytes(u.mem_read(TOWN+0x50a60,12)),bytes(u.mem_read(head,12)))
    assert {p for p,_ in u.allocs}==set(u.freed)

print('PASS four forge-only machines: actual depot equip/unassign, crew modifiers, native save/load, combat stats, chassis resources, stock delivery and six failure paths')

if '--editor' in sys.argv:
    from archive import SRC
    root=Path(__file__).resolve().parent
    fixture_path=root/'editor/size-compat-tests/fixtures/122KB-binary-1named-h0.Sav'
    with tempfile.TemporaryDirectory() as directory:
        temp=Path(directory)
        save=temp/'test.Sav'
        data=fixture_path.read_bytes()
        invalid=bytearray(editor_records[0])
        struct.pack_into('<I',invalid,0,1)  # Wrong model ID with a real legendary name.
        save.write_bytes(data+b'\0'*(-len(data)%4)+b''.join(editor_records)+invalid)
        runner=temp/'LegendEditorTest.cs'
        runner.write_text('''using System;
using System.Collections.Generic;
using System.Linq;
using SteelEditor;
class LegendEditorTest {
 static void Main(string[] args) {
  var model = new EquipmentModel(args[0]);
  model.OpenSave(args[1]);
  foreach (string name in args.Skip(2)) {
   var rows=model.Rows.Where(r=>r.Name.Contains(name+" · ")).ToArray();
   if(rows.Length!=2 || !rows.Any(r=>r.Name.StartsWith("[배치 해제] ")))throw new Exception(name);
   foreach(var row in rows)model.Apply(row,new Dictionary<int,int>{{0x5c,777}});
  }
  model.Save(false);
  var reload=new EquipmentModel(args[0]);
  reload.OpenSave(args[1]);
  foreach(string name in args.Skip(2)){
   var edited=reload.Rows.Where(r=>r.Name.Contains(name+" · ")&&reload.Get(r,0x5c)==777);
   if(edited.Count()!=2)throw new Exception(name);
  }
 }
}''',encoding='utf-8-sig')
        editor=temp/'test.exe'
        subprocess.run([r'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe',
                        '/nologo','/platform:x86','/out:'+str(editor),'/r:System.Core.dll',
                        '/resource:'+str(root/'extracted/Data.pak/char.dat')+',char.dat',
                        str(root/'editor/SaveModel.cs'),str(root/'editor/EquipmentModel.cs'),
                        str(runner)],check=True)
        subprocess.run([str(editor),str(SRC),str(save),*[model['name'] for model in MODELS]],check=True)
    print('PASS compiled C# equipment editor recognizes all 8 crafted/spare/crewed records, rejects mismatched chassis, edits and reloads')
