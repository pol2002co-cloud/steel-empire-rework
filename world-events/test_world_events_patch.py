"""Generator checks, including actual C compilation of the generated tables."""
from pathlib import Path
import copy
import re
import tempfile
import unittest

import world_events_patch as P


def api_fixture():
    state = {name: hex(0x53b000+i*16) for i, name in enumerate((
        "getslot", "completed", "count_completed", "tick", "rng", "can_offer",
        "schedule", "finish", "clear", "reserve_battle"))}
    state.update(base="0x48d414", magic=0x57455631, done_address="0x48d42c",
                 last_day_address="0x48d420", next_offer_address="0x48d41c")
    actions = {name: hex(0x53c000+i*16) for i, name in enumerate((
        "find_item", "take_item", "give_item", "hire", "give_machine", "battle", "known", "find_machine", "take_machine", "perform"))}
    return state, actions, dict(event_journal=dict(select="0x53d000", speech="0x53d100"))


class GenerationTests(unittest.TestCase):
    def test_cp949_strings_and_native_source_literals(self):
        for text in ('장터의 교환 제안', 'ABCDEF09"\\\n', '금 1,000 · 철 20'):
            literal = P.c_string(text)
            decoded = bytes(int(x, 8) for x in re.findall(r'\\([0-7]{3})', literal))
            self.assertEqual(decoded, text.encode('cp949'))
            literal.encode('ascii')
        with self.assertRaises(ValueError):
            P.c_string('잘못된\0문자')
        source = '/* "주석" */\n// "두 번째 주석"\nconst char *s="본문\\n\\\"인용\\\""; int q=\'"\';'
        result = P.cp949_source(source)
        self.assertIn('/* "주석" */', result)
        self.assertIn('// "두 번째 주석"', result)
        self.assertIn('\\n\\\"', result)
        self.assertNotIn('본문', result)
        self.assertIn("int q='\"'", result)

    def test_roles_keep_sequence_not_just_a_union(self):
        mask, sequence = P.encode_roles(['near', 'far', 'airport'])
        self.assertEqual(sequence, 0x321)
        self.assertEqual(mask, P.ROLE_MASKS['near']|P.ROLE_MASKS['far']|P.ROLE_MASKS['airport'])
        self.assertEqual(P.encode_roles(['near', 'near'])[1], 0x11)
        with self.assertRaises(ValueError):
            P.encode_roles(['near']*7)
        with self.assertRaises(ValueError):
            P.encode_roles(['unreachable'])

    def test_full_deterministic_header_and_native_adapter_macros(self):
        state, actions, journal = api_fixture()
        header = P.generate_header(state, actions, journal)
        self.assertEqual(header, P.generate_header(state, actions, journal['event_journal']))
        header.encode('ascii')
        for symbol in ('S_BASE', 'S_MAGIC', 'S_DONE', 'S_GETSLOT', 'S_FINISH', 'S_CLEAR',
                       'S_RESERVE_BATTLE', 'UI_SELECT', 'UI_SPEECH', 'A_FIND_ITEM',
                       'A_TAKE_ITEM', 'A_GIVE_ITEM', 'A_HIRE', 'A_GIVE_MACHINE',
                       'A_BATTLE', 'A_KNOWN', 'A_FIND_MACHINE', 'A_TAKE_MACHINE', 'A_PERFORM', 'P_REGIONAL_TWO_TYPES', 'R_BLACK_POWER_HQ'):
            self.assertIn('#define '+symbol+' ', header)
        self.assertEqual(header.count('static const Choice CH_'), sum(len(e['stages']) for e in P.EVENT_CATALOG))
        self.assertEqual(header.count('static const Stage ST_'), len(P.EVENT_CATALOG))
        self.assertEqual(header.count('static const Choice LEGACY_CH_'), sum(len(e['stages']) for e in P.LEGACY_EVENT_CATALOG))
        self.assertEqual(header.count('static const Stage LEGACY_ST_'), len(P.LEGACY_EVENT_CATALOG))
        self.assertIn('#define WORLD_EVENT_COUNT 41', header)
        self.assertIn('static const Event EVENTS[]={', header)
        self.assertIn('static const Event LEGACY_EVENTS[]={', header)
        self.assertEqual(P.predicates(P.EVENT_CATALOG[23]), 0)
        self.assertEqual(P.predicates(P.LEGACY_EVENT_CATALOG[23]), P.PREDICATE_MASKS['regional_once']|P.PREDICATE_MASKS['regional_two_types'])
        self.assertIn('두 종류 이상', P.condition_text(P.LEGACY_EVENT_CATALOG[23], P.LEGACY_EVENT_CATALOG))
        self.assertIn('자동 완료', P.condition_text(P.EVENT_CATALOG[23]))

    def test_unknown_fields_bad_legs_and_unsigned_addresses_rejected(self):
        state, actions, journal = api_fixture()
        for key, value in (('invented_action', 1), ('target_roles', ['near']), ('battle_profile', 'boss')):
            catalog = copy.deepcopy(P.EVENT_CATALOG)
            catalog[0]['stages'][0]['choices'][0]['actions'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                P.generate_header(state, actions, journal, catalog)
        with self.assertRaises(ValueError):
            P.generate_header(dict(state, base=-1), actions, journal)
        with self.assertRaises(ValueError):
            P.generate_header(dict(state, base=True), actions, journal)
        with self.assertRaises(ValueError):
            P.generate_header(state, actions, journal, P.EVENT_CATALOG[:-1])
        catalog = copy.deepcopy(P.EVENT_CATALOG)
        catalog[0]['stages'][0]['choices'][0]['actions']['cost_gold'] = 0xffffffff
        with self.assertRaises(ValueError):
            P.generate_header(state, actions, journal, catalog)

    def test_emitter_embeds_real_native_image_at_its_linked_base(self):
        from world_event_compile import REWORK_END
        from keystone import Ks, KS_ARCH_X86, KS_MODE_32
        image = bytearray()
        ks = Ks(KS_ARCH_X86, KS_MODE_32)
        patches = []
        def address():
            return 0x53b000+len(image)
        def put(data):
            where = address()
            image.extend(data)
            image.extend(bytes((-len(image)) % 16))
            return where
        def asm(source, where):
            return bytes(ks.asm(source, where)[0])
        def patch(where, old, new):
            self.assertEqual(len(old), len(new))
            patches.append(where)
        with tempfile.TemporaryDirectory(prefix='SteelEmitter-') as temp:
            from build import sha
            from archive import SRC
            import pefile
            original=next(p.read_bytes() for p in [SRC/'SteelEmpire.exe',*sorted((SRC/'ReworkBackups').glob('*/SteelEmpire.exe'))] if p.is_file() and sha(p.read_bytes())=='65bf8699804849f36cef9108eebe88f8c9f1661ac77ea5c2e6688ae347795fde')
            original_pe=pefile.PE(data=original)
            def read(a,n):
                off=original_pe.get_offset_from_rva(a-0x400000)
                return original[off:off+n]
            meta = P.emit(put, asm, address, patch,
                          dict(select='0x500000', speech='0x500100'), temp,read=read)['world_events']
            base = int(meta['image_base'], 16)
            self.assertEqual(base % 0x10000, 0)
            self.assertLess(base+meta['image_size'], REWORK_END)
            self.assertEqual(set(meta['exports']), set(P.EXPORTS))
            self.assertEqual(meta['tick'], meta['exports']['we_tick'])
            self.assertEqual(meta['router'], meta['exports']['we_router'])
            self.assertEqual(bytes(image[base-0x53b000:base-0x53b000+2]), b'MZ')
            self.assertEqual(sorted(patches), sorted([0x4398f6, 0x439a01, 0x401e00, 0x401210, 0x432439,0x401160,0x4206d0,0x4498f5]))
            self.assertEqual(meta['events'], len(P.EVENT_CATALOG))
            self.assertEqual(meta['stages'], 41)
            self.assertEqual(meta['choices'], 47)
            self.assertEqual(meta['legacy_stages'], 51)
            self.assertEqual(meta['legacy_choices'], 95)
            self.assertIn('perform', meta['tour_actions'])
            self.assertEqual(meta['state']['card_count'], 3)
            self.assertEqual(meta['resources']['gold'], '0x46e5d8')
            self.assertTrue((Path(temp)/'world_event_generated.h').is_file())
            self.assertTrue((Path(temp)/'world_event_native_cp949.c').is_file())

    def test_actual_compiled_structure_fields_and_cp949_bytes(self):
        from world_event_compile import compile_image
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP
        import struct
        state, actions, journal = api_fixture()
        with tempfile.TemporaryDirectory(prefix='SteelCatalog-') as temp:
            folder = Path(temp)
            (folder/'world_event_generated.h').write_text(P.generate_header(state, actions, journal), encoding='ascii')
            source = '''
typedef unsigned int u32;
typedef struct {const char *label,*result;int next,cost[3],reward[3];int cost_item,cost_count,item,item_count,machine,hire_class,hire_count,job,army_type,profile,legs,roles,project_part;u32 role_sequence;int cost_machine;} Choice;
typedef struct {const char *title,*text;const Choice *choices;int count,min_completed;} Stage;
typedef struct {const char *key,*title,*conditions;int category,kind,repeat_days,job,facility,country,min_completed;u32 dep_low,dep_high,predicates;int count;const Stage *stages;int early,goal,building,target_fixed,goal_roles;} Event;
#include "world_event_generated.h"
__declspec(dllexport) unsigned __stdcall probe(unsigned id,unsigned field){
 const Event *e=&EVENTS[id];
 if(field==0)return sizeof(EVENTS)/sizeof(EVENTS[0]);
 if(field==1)return e->count;
 if(field==2)return e->predicates;
 if(field==3)return e->stages[0].choices[0].cost[1];
 if(field==4)return e->stages[0].choices[0].army_type;
 if(field==5)return e->stages[0].choices[0].role_sequence;
 if(field==6)return e->stages[e->count-1].choices[0].machine;
 if(field==7)return e->stages[0].choices[0].next;
 if(field==8)return e->early;
 if(field==9)return e->stages[0].choices[0].cost_machine;
 if(field==10)return e->goal;
 if(field==11)return e->building;
 if(field==12)return e->target_fixed;
 if(field==13)return e->goal_roles;
 return ((const unsigned char *)e->title)[field-100];
}
__declspec(dllexport) unsigned __stdcall legacy_probe(unsigned id,unsigned field){
 const Event *e=&LEGACY_EVENTS[id];
 if(field==0)return sizeof(LEGACY_EVENTS)/sizeof(LEGACY_EVENTS[0]);
 if(field==1)return e->count;
 if(field==2)return e->predicates;
 if(field==3)return e->stages[0].choices[0].role_sequence;
 if(field==4)return e->stages[e->count-1].choices[0].machine;
 return e->goal|e->building|e->target_fixed|e->goal_roles;
}
__declspec(dllexport) unsigned __stdcall literal(unsigned i){const unsigned char *s=(const unsigned char *)"기본 본문";return s[i];}
'''
            path = folder/'probe.c'
            path.write_text(P.cp949_source(source), encoding='utf-8')
            image, exports = compile_image(path, folder, 0x550000, folder/'probe.dll', ['probe', 'literal', 'legacy_probe'])
            u = Uc(UC_ARCH_X86, UC_MODE_32)
            u.mem_map(0x400000, 0x200000)
            u.mem_map(0x1000000, 0x400000)
            u.mem_write(0x550000, image)
            u.hook_add(UC_HOOK_CODE, lambda u,a,n,d: u.emu_stop() if a == 0x13df000 else None)
            def call(name, *args):
                sp = 0x13f0000
                u.mem_write(sp, struct.pack('<I', 0x13df000))
                for index, value in enumerate(args):
                    u.mem_write(sp+4+index*4, struct.pack('<I', value))
                u.reg_write(UC_X86_REG_ESP, sp)
                u.emu_start(exports[name], 0, count=100000)
                self.assertEqual(u.reg_read(UC_X86_REG_EIP), 0x13df000)
                self.assertEqual(u.reg_read(UC_X86_REG_ESP), sp+4+4*len(args))
                return u.reg_read(UC_X86_REG_EAX)
            self.assertEqual(call('probe', 0, 0), len(P.EVENT_CATALOG))
            self.assertEqual(call('probe', 34, 1), 1)
            self.assertEqual(call('probe', 23, 2), P.predicates(P.EVENT_CATALOG[23]))
            self.assertEqual(call('probe', 0, 3), 40)
            self.assertEqual(call('probe', 0, 4), 0xffffffff)
            self.assertEqual(call('probe', 20, 5), 0)
            self.assertEqual(call('probe', 31, 6), 24)
            self.assertEqual(call('probe', 34, 7), 0xffffffff)
            self.assertEqual(call('probe', 0, 8), 1)
            self.assertEqual(call('probe', 31, 8), 1)
            self.assertEqual(call('probe', 36, 9), 6)
            self.assertEqual(call('probe', 37, 9), 1)
            self.assertEqual(call('probe', 36, 10), P.GOAL_TYPES['equipment'])
            self.assertEqual(call('probe', 3, 10), P.GOAL_TYPES['build'])
            self.assertEqual(call('probe', 3, 11), 6)
            self.assertEqual(call('probe', 3, 12), 1)
            self.assertEqual(call('probe', 32, 12), 40)
            self.assertEqual(call('probe', 31, 13), P.ROLE_MASKS['airport'])
            self.assertEqual(call('legacy_probe', 0, 0), 38)
            self.assertEqual(call('legacy_probe', 34, 1), 2)
            self.assertEqual(call('legacy_probe', 23, 2), P.predicates(P.LEGACY_EVENT_CATALOG[23]))
            self.assertEqual(call('legacy_probe', 20, 3), 0xaaa)
            self.assertEqual(call('legacy_probe', 31, 4), 24)
            self.assertEqual(call('legacy_probe', 3, 5), 0)
            for index, byte in enumerate(P.EVENT_CATALOG[0]['title'].encode('cp949')):
                self.assertEqual(call('probe', 0, index+100), byte)
            for index, byte in enumerate('기본 본문'.encode('cp949')):
                self.assertEqual(call('literal', index), byte)


if __name__ == '__main__':
    unittest.main()
