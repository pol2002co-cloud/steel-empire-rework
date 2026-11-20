"""Execute the seasonal native routes in x86. --integrated tests the built game as shipped."""
import argparse
import json
import struct

from build import ROOT, asm, pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn import x86_const as x86
import campaign_patch
import seasonal_rewards_patch
import xp_share_patch

PE = pefile.PE(str(ROOT / "package/SteelEmpire.exe"))
IMAGE = PE.get_memory_mapped_image()
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf8"))
STACK, STOP, ARENA = 0x13F0000, 0x13DF000, 0x610000
FUNDS, HOURS = 0x46E5D8, 0x48D388
MAX_INT = 0x7FFFFFFF
REG = {name: getattr(x86, "UC_X86_REG_" + name.upper())
       for name in ("eax", "ebx", "ecx", "edx", "ebp", "esi", "edi", "esp", "eflags")}


def write(u, addr, value):
    u.mem_write(addr, struct.pack("<I", value))


def read(u, addr):
    return struct.unpack("<I", u.mem_read(addr, 4))[0]


def run(u, start, end):
    u.emu_start(start, end, count=300000)
    assert u.reg_read(x86.UC_X86_REG_EIP) == end


def build_fixture(integrated):
    edits = {}
    if integrated:
        assert "seasonal_battle_xp" in MANIFEST and "seasonal_rewards" in MANIFEST
        assert MANIFEST["campaign"]["seasonal_tribute"] == 300000
        campaign = MANIFEST["campaign"]
    else:
        before = {int(e["va"], 16): bytes.fromhex(e["before"]) for e in MANIFEST["patches"]}
        cursor = ARENA

        def put(data):
            nonlocal cursor
            here = cursor
            edits[here] = data
            cursor += (len(data) + 15) & ~15
            return here

        def patch(at, old, new):
            assert len(old) == len(new)
            assert before.get(at, IMAGE[at-0x400000:at-0x400000+len(old)]) == old, hex(at)
            edits[at] = new

        args = (put, asm, lambda: cursor, patch)
        xp_share_patch.emit(*args)
        seasonal_rewards_patch.emit(*args)
        campaign = campaign_patch.emit(*args, MANIFEST)["campaign"]

    def fixture():
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(0x400000, 0x200000)
        u.mem_write(0x400000, IMAGE)
        u.mem_map(ARENA, 0x20000)
        u.mem_map(0x1000000, 0x400000)
        u.reg_write(REG["esp"], STACK)
        for at, code in edits.items():
            u.mem_write(at, code)
        return u

    return fixture, campaign


def test_offers_and_claims(fixture):
    u = fixture()
    quest = 0x1010000
    for month in range(1, 13):
        write(u, HOURS, (month-1)*720 + 719)
        for kind in (0, 1, 2):
            scale = 2 if ((kind == 0 and month in (1, 7)) or
                          (kind == 1 and month in (5, 11))) else 1
            write(u, quest+4, kind)
            write(u, quest+0x124, 5040000)
            for site, (base, dest) in seasonal_rewards_patch.REWARD_SITES.items():
                for i, reg in enumerate(("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp")):
                    u.reg_write(REG[reg], i + 77)
                u.reg_write(REG[base], quest)
                u.reg_write(REG["eflags"], 0x247)
                expected = {reg: u.reg_read(code) for reg, code in REG.items()}
                expected[dest] = 5040000*scale
                run(u, site, site+6)
                assert all(u.reg_read(REG[reg]) == value for reg, value in expected.items()), hex(site)
                assert read(u, quest+0x124) == 5040000
    # The same accepted contract changes at midnight, including across years.
    for kind, hours, amounts in [(1, [4*720-1,4*720,5*720], [100,200,100]),
                                 (0, [12*720-1,12*720], [100,200])]:
        write(u, quest+4, kind)
        write(u, quest+0x124, 100)
        for hour, amount in zip(hours, amounts):
            write(u, HOURS, hour)
            u.reg_write(REG["esi"], quest)
            run(u, 0x44B259, 0x44B25F)
            assert u.reg_read(REG["edx"]) == amount
    # Signed treasury room and signed multiplication both saturate.
    write(u, quest+0x124, MAX_INT)
    write(u, FUNDS, MAX_INT-5)
    run(u, 0x44B259, 0x44B25F)
    assert u.reg_read(REG["edx"]) == 5

    # Execute native inventory, actual credit, exact paid-record removal and both reputation writes.
    for kind, month in ((1,5),(0,7),(1,7),(0,5)):
        u = fixture()
        manager, head, node, town, origin, item = 0x1000000,0x1010000,0x1020000,0x1090000,0x1100000,0x1200000
        q = node+8
        for addr, val in ((0x48D394,manager),(manager+4,head),(manager+8,1),(head,node),(head+4,node),
                          (node,head),(node+4,head),(q,3),(q+4,kind),(q+24,73),(q+0x124,300),
                          (item,73),(FUNDS,50),(HOURS,(month-1)*720)):
            write(u, addr, val)
        u.reg_write(REG["esi"], q)
        u.reg_write(REG["edi"], town)
        u.reg_write(REG["ebx"], origin)

        def external(machine, pc, size, userdata):
            if pc not in (0x438D90, 0x4500E6):
                return
            sp = machine.reg_read(REG["esp"])
            if pc == 0x438D90:
                machine.reg_write(REG["eax"], item)
            machine.reg_write(x86.UC_X86_REG_EIP, read(machine, sp))
            machine.reg_write(REG["esp"], sp+(8 if pc == 0x438D90 else 4))

        u.hook_add(UC_HOOK_CODE, external)
        run(u, 0x44B240 if kind == 1 else 0x44B259, 0x44B293)
        assert read(u,FUNDS) == (650 if (kind,month) in ((1,5),(0,7)) else 350)
        assert read(u,item) == (0 if kind == 1 else 73)
        assert read(u,manager+8) == 0 and read(u,head) == head
        assert read(u,town+0x509F4) == read(u,origin+0x509F4) == 1


def test_battle(fixture):
    # One L99 donor, one living infantryman, one two-seat allied giant and a dead infantryman.
    # Kill credits are 1/2/3/1. An odd pre-season pool tests rounding and donor scaling.
    for month in range(1,13):
        u = fixture()
        battle = 0x1000000
        write(u,HOURS,(month-1)*720)
        units, people = [], []
        for i, levels in enumerate(((99,),(3,),(4,5),(2,))):
            unit = 0x1100000+i*0x1000
            person = unit+0x400
            units.append(unit)
            write(u,battle+0x228+i*4,unit)
            write(u,unit+4,battle)
            write(u,unit+0x138,int(i!=3))
            if i == 2:
                write(u,unit,0x463298)
                write(u,unit+0x150,4)
                write(u,unit+0x15C,unit+0x800)
            for j,level in enumerate(levels):
                member = person+j*0x100
                write(u,unit+0x800+0x8c+j*4 if i==2 else unit+0x15c,member)
                write(u,member+0x48,level)
                write(u,member+0x4c,17)
                people.append((i,j,member,level))
            enemy = 0x1200000+i*0x400
            write(u,battle+0x36c+i*4,enemy)
            write(u,enemy+0xf4,unit)
            write(u,enemy+0x150,i%3)
        base = 6
        write(u,STACK+0x24,base)
        u.reg_write(REG["ebp"],battle)
        run(u,0x43A472,0x43A478)
        mul = 2 if month in (3,9) else 1
        share,remainder = divmod((base+1)*mul,3)
        assert (read(u,battle+0xe4c),read(u,battle+0xe50)) == (share,remainder)
        amounts = []
        for i,j,member,level in people:
            if i == 3:
                assert read(u,member+0x4c)==17
                continue
            u.reg_write(REG["ecx"],units[i])
            u.reg_write(REG["edx"],i%3+1)
            run(u,0x43A506,0x43A50E)
            award = u.reg_read(REG["edx"])
            assert award==(base+i%3+1)*mul and u.reg_read(REG["eax"])==read(u,units[i])
            u.reg_write(REG["eax"],member)
            u.reg_write(REG["esi"],units[i])
            if i == 2:
                u.reg_write(REG["ebx"],award)
                site = 0x43FD68 if j else 0x43FD96
                run(u,site,site+8)
            else:
                write(u,STACK+0x34,award)
                run(u,0x43E8DE,0x43E8EC)
                u.reg_write(REG["esp"],STACK)
            gained = read(u,member+0x4c)-17
            if level==99:
                assert gained==0
            else:
                amounts.append(gained-award)
        assert amounts==[share+(i<remainder) for i in range(3)]
        assert read(u,battle+0xe50)==0
        # A positive overflowing raw or already-nearly-full recipient cannot wrap.
        write(u,STACK+0x24,MAX_INT)
        u.reg_write(REG["ecx"],units[1])
        u.reg_write(REG["edx"],3)
        run(u,0x43A506,0x43A50E)
        assert u.reg_read(REG["edx"])==MAX_INT
        member=people[1][2]
        write(u,member+0x4c,MAX_INT-4)
        write(u,STACK+0x34,MAX_INT)
        u.reg_write(REG["eax"],member)
        u.reg_write(REG["esi"],units[1])
        run(u,0x43E8DE,0x43E8EC)
        assert read(u,member+0x4c)==MAX_INT


def test_full_dispatch(fixture):
    # Execute the complete 81-cell stock settlement and its virtual infantry/vehicle/giant paths.
    for month, mul in ((3,2),(4,1),(9,2)):
        for ident in range(17,22):
            u = fixture()
            battle, vt, notify = 0x1000000, 0x1010000, 0x1010100
            write(u,battle,vt)
            write(u,vt+0x10,notify)
            write(u,HOURS,(month-1)*720)
            members = []
            for idx, (kind, unit_vt, levels) in enumerate(((4,0x463298,(99,20)),(1,0x463268,(10,)))):
                unit, machine, person = (0x1020000+idx*0x40000,0x1030000+idx*0x40000,
                                         0x1040000+idx*0x40000)
                for addr,val in ((battle+0x228+idx*40*4,unit),(unit,unit_vt),(unit+4,battle),
                                 (unit+0x150,kind),(unit+0x138,1),(unit+0x15c,machine),
                                 (machine+4,ident if idx==0 else 6)):
                    write(u,addr,val)
                for seat,level in enumerate(levels):
                    member=person+seat*0x1000
                    members.append(member)
                    for addr,val in ((machine+0x8c+4*seat,member),(member+0x38,10),
                                     (member+0x48,level),(member+0x4c,100000 if level==99 else 7),(member+0x50,100000)):
                        write(u,addr,val)
            def boundary(machine, pc, size, data):
                if pc == notify:
                    sp = machine.reg_read(REG["esp"])
                    machine.reg_write(x86.UC_X86_REG_EIP,read(machine,sp))
                    machine.reg_write(REG["esp"],sp+16)
            u.hook_add(UC_HOOK_CODE,boundary)
            u.reg_write(REG["ebp"],battle)
            write(u,STACK+0x10,battle)
            write(u,STACK+0x24,201)
            run(u,0x43A472,0x43A547)
            share,rem = divmod(201*mul,2)
            gains = [read(u,member+0x4c)-initial for member, initial in zip(members,(100000,7,7))]
            assert gains[0]==0 and sorted(gains[1:])==[201*mul+share,201*mul+share+rem], (month,ident,gains,share,rem)


def test_tribute(fixture,campaign):
    u = fixture()
    world = 0x1000000
    write(u,0x48c3d8,world)
    for i,ident in enumerate((63,65)):
        city,town,army = 0x1010000+i*256,0x1040000+i*0x60000,0x1150000+i*256
        for addr,val in ((world+0x23c+4*i,city),(city+0x7c,town),(town+4,ident),
                         (town+0x50654,army),(army,1),(army+0x14,1),(army+0x1c,1)):
            write(u,addr,val)
    total=0
    for m in range(1,15):
        write(u,HOURS,(m-1)*720+29*24)
        if m==7:
            write(u,0x1150000+0x14,0) # First HQ was evacuated before July settlement.
        if m==13:
            write(u,FUNDS,1999800000)
            total=1999800000
        total=min(2000000000,total+(300000 if m%12 in (1,7) else 150000)*(2 if m<7 else 1))
        for again in range(2):
            u.reg_write(REG["esp"],STACK)
            write(u,STACK,STOP)
            run(u,int(campaign["revenue"],16),STOP)
            assert read(u,FUNDS)==total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--integrated", action="store_true")
    fixture,campaign = build_fixture(parser.parse_args().integrated)
    test_offers_and_claims(fixture)
    test_battle(fixture)
    test_full_dispatch(fixture)
    test_tribute(fixture,campaign)
    print("PASS seasonal native rewards: 12 months, 9 commission sites, exact settlement, mixed infantry and giant crew, L99 remainder, 2 HQs, withdrawal, year rollover, saturation")
