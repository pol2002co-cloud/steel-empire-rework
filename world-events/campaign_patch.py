"""Post-story campaign and event-gated boss construction.

Reserved script globals 94..97 remain inside the stock serialized 100 DWORDs.
No personal save is edited. Machine type and giant-unit constructors are stock.
"""
import struct

BASE=0x48d398
MAGIC_ADDR=BASE+94*4
DEBT_ADDR=BASE+95*4
OCCUPIED_ADDR=BASE+96*4
MONTH_ADDR=BASE+97*4
MAGIC=0x43504e31
FACTIONS=(12,14,15,16,18,20)
HEADQUARTERS=(63,65,66,67,69,71)
BOSSES=(
    (17,'INF MK1',400,150,1500000,'깽디쉬박사: INF-MK1 격파 이후'),
    (18,'INF MK2',600,200,2000000,'깽디쉬박사 사건 완료'),
    (19,'블랙드래곤',500,400,2500000,'라이벌: 잽, 스톤해머와 최종 상대 격파'),
    (20,'랜드배틀쉽',1000,300,3000000,'고대인의유적: 신의 눈 전달 완료'),
    (21,'포트레스',1500,600,5000000,'최후의결전: 최종 승리'),
)
PATCH_SITES={0x41b2b9:5,0x41ae08:5,0x41b47a:5,0x41b386:5,0x430053:5,
             0x421800:5,0x43016b:5,0x430305:10,0x43031e:5,0x40a45b:6}


def allow_campaign_edits(pe,allowed):
    from quest_convenience_patch import PATCH_SITES as quest_sites
    from seasonal_rewards_patch import REWARD_SITES
    seasonal_sites={site:6 for site in REWARD_SITES}
    seasonal_sites[0x43a506]=8
    for va,size in {**quest_sites,**seasonal_sites}.items():
        offset=pe.get_offset_from_rva(va-0x400000)
        allowed.update(range(offset,offset+size))
    for va,size in PATCH_SITES.items():
        offset=pe.get_offset_from_rva(va-0x400000)
        allowed.update(range(offset,offset+size))
    from boss_layout_patch import allow_boss_layout_edits
    allow_boss_layout_edits(pe,allowed)


def patch_scripts(root):
    """Same-width opcode edits preserve every pre-existing trigger PC."""
    from event_decode import decode_script
    changes={}
    for name,pc in [('청산',199),('아시레마',10348)]:
        path=root/'extracted/patch102.pak'/(name+'.cmp')
        rows=decode_script(path)
        row=next(r for r in rows if r['addr']==pc)
        assert row['text']=='ExitFrame()' and row['end']==pc+1
        data=bytearray(path.read_bytes())
        assert struct.unpack_from('<I',data,pc*4)[0]==0x8022
        struct.pack_into('<I',data,pc*4,0x801e)  # WorldFrame(), also zero arguments
        changes[name+'.cmp']=bytes(data)
    return changes


def emit(put,asm,address,patch,journal,convenience=None,imperial=None,black_power=None,world_events=None):
    def code(t):return put(asm(t,address()))
    def s(t):return put(t.encode('cp949')+b'\0')
    def arr(v):return put(struct.pack('<%dI'%len(v),*v))
    select=int(journal['event_journal']['select'],16)
    speech=int(journal['event_journal']['speech'],16)
    liberation=int(convenience['quest_convenience']['liberation'],16) if convenience else 0x448410
    process=int(convenience['quest_convenience']['process'],16) if convenience else 0
    imperial_eligible=int(imperial['imperial_campaign']['eligible'],16) if imperial else 0
    imperial_seed=int(imperial['imperial_campaign']['seed'],16) if imperial else 0
    black_power_restore=int(black_power['black_power_return']['restore'],16) if black_power else 0
    world_tick=int(world_events['world_events'].get('idle',world_events['world_events']['tick']),16) if world_events else 0
    init=code(f'''
      cmp dword ptr [{MAGIC_ADDR}],{MAGIC}; je done;
      mov dword ptr [{DEBT_ADDR}],0; mov dword ptr [{OCCUPIED_ADDR}],0;
      mov dword ptr [{MONTH_ADDR}],0; mov dword ptr [{MAGIC_ADDR}],{MAGIC};
    done: ret
    ''')
    # EAX=HQ town record -> bit index, -1 for every other town.
    index_code=['mov edx,[eax+4]']
    for i,ident in enumerate(HEADQUARTERS):
        index_code += [f'cmp edx,{ident}',f'je found{i}']
    index_code+=['mov eax,-1','ret']
    for i in range(6):index_code += [f'found{i}: mov eax,{i}','ret']
    index=code(';'.join(index_code))
    factions=arr(FACTIONS)
    # stdcall eligible(town record). Towns 1..62 are actual cities; the six
    # mercenary headquarters do not themselves count as occupied cities.
    eligible=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      mov eax,[ebp+8]; test eax,eax; jz no; call {index};
      cmp eax,6; jae no; mov ebx,[eax*4+{factions}];
      mov esi,[0x48c3d8]; test esi,esi; jz no; add esi,0x23c;
      mov edi,100;
    town: mov eax,[esi]; test eax,eax; jz nexttown;
      mov edx,[eax+0x7c]; test edx,edx; jz nexttown;
      cmp dword ptr [edx+4],62; ja nexttown;
      push esi; push edi; lea esi,[edx+0x50654]; mov edi,15;
    troop: mov eax,[esi]; test eax,eax; jz nexttroop;
      cmp [eax],ebx; jne nexttroop;
      cmp dword ptr [eax+0x14],0; je nexttroop;
      cmp dword ptr [eax+0x1c],0; jg blocked;
    nexttroop: add esi,4; dec edi; jnz troop;
      pop edi; pop esi;
    nexttown: add esi,4; dec edi; jnz town;
      mov eax,1; jmp done;
    blocked: pop edi; pop esi;
    no: xor eax,eax;
    done: pop edi; pop esi; pop ebx; pop ebp; ret 4
    ''')
    # stdcall garrison(town record), living player formations only.
    garrison=code('''
      push esi; push edi; mov edx,[esp+12]; lea esi,[edx+0x50654];
      mov edi,15;
    scan: mov eax,[esi]; test eax,eax; jz next;
      cmp dword ptr [eax],1; jne next;
      cmp dword ptr [eax+0x14],0; je next;
      cmp dword ptr [eax+0x1c],0; jle next;
      mov eax,1; jmp done;
    next: add esi,4; dec edi; jnz scan; xor eax,eax;
    done: pop edi; pop esi; ret 4
    ''')
    # At the hostile-town quest gate, replace the test for the six HQs only.
    # The EDI actor and EBX target are the original native ingress operands.
    ingress=code(f'''
      push ebx; push esi; mov esi,[ebx+0x7c]; mov eax,esi;
      {f'push esi; call {imperial_eligible}; test eax,eax; jz ordinary; mov eax,[edi+0x808]; cmp dword ptr [eax],1; jne ordinary; mov eax,1; pop esi; pop ebx; ret 4; ordinary: mov eax,esi;' if imperial_eligible else ''}
      call {index}; cmp eax,6; jae stock;
      mov eax,[edi+0x808]; cmp dword ptr [eax],1; jne stock;
      push esi; call {eligible}; pop esi; pop ebx; ret 4;
    stock: pop esi; pop ebx; jmp {liberation}
    ''')
    patch(0x41b2b9,asm('call 0x448410',0x41b2b9),asm(f'call {ingress}',0x41b2b9))
    # A second gate in the actual attachment routine prevents bypass by an
    # empty HQ or by entering through another UI path. Ordinary towns untouched.
    attach=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      mov edi,ecx; mov esi,[ebp+8]; mov ebx,[ebp+12];
      mov eax,[esi+0x808]; cmp dword ptr [eax],1; jne stock;
      mov eax,[ebx+0x7c]; call {index}; cmp eax,6; jae stock;
      push eax; push dword ptr [ebx+0x7c]; call {garrison};
      test eax,eax; jnz accepted;
      push dword ptr [ebx+0x7c]; call {eligible}; test eax,eax; jz refused;
    accepted: pop eax;
      push eax; push ebx; push esi; mov ecx,edi; call 0x421050;
      mov edx,eax; pop ecx; test edx,edx; jz returnresult;
      call {init}; bts dword ptr [{OCCUPIED_ADDR}],ecx;
    returnresult: mov eax,edx; jmp done;
    refused: pop eax;
    denied: xor eax,eax; jmp done;
    stock: push ebx; push esi; mov ecx,edi; call 0x421050;
    done: pop edi; pop esi; pop ebx; pop ebp; ret 8
    ''')
    for a in (0x41ae08,0x41b47a,0x41b386,0x430053):
        patch(a,asm('call 0x421050',a),asm(f'call {attach}',a))
    # Existing Black Crow field armies may counterattack even while their HQ
    # is occupied. Never generate armies inside a player-held headquarters.
    counterattack=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,24;
      mov ebx,ecx; mov eax,[ebp+8]; test eax,eax; jz done;
      mov esi,[eax+0x7c]; test esi,esi; jz done;
      cmp dword ptr [esi+4],66; jne done;
      cmp dword ptr [esi+8],15; jne done;
      mov [esp],eax; mov [esp+4],esi;
      mov edx,[0x48d388]; sub edx,[eax+0x24]; cmp edx,144; jb done;
      push esi; call {garrison}; test eax,eax; jz scan;
      mov eax,[esp]; mov edx,[0x48d388]; mov [eax+0x24],edx;
    scan: mov dword ptr [esp+8],0;
    army: mov edx,[esp+8]; mov edi,[ebx+edx*4+0xac]; test edi,edi; jz nextarmy;
      mov eax,[edi+0x808]; test eax,eax; jz nextarmy;
      cmp dword ptr [eax],15; jne nextarmy;
      mov edx,[esp+4]; cmp [eax+4],edx; jne nextarmy;
      cmp dword ptr [eax+0x14],0; je nextarmy;
      cmp dword ptr [eax+0x1c],0; jle nextarmy;
      cmp dword ptr [eax+8],0; jne nextarmy;
      cmp dword ptr [edi+0x14],0; je nextarmy;
      cmp dword ptr [edi+0x50],0; jne nextarmy;
      mov esi,[esp+4]; test byte ptr [esi+0x10],1; jnz cities;
      push esi; call {garrison}; test eax,eax; jnz cities;
      mov eax,[esp]; jmp order;
    cities: mov dword ptr [esp+12],0; mov dword ptr [esp+16],0x7fffffff;
      mov dword ptr [esp+20],0;
    city: mov edx,[esp+20]; mov esi,[ebx+edx*4+0x23c]; test esi,esi; jz nextcity;
      mov eax,[esi+0x7c]; test eax,eax; jz nextcity;
      cmp dword ptr [eax+4],62; ja nextcity;
      cmp dword ptr [eax+8],1; je nextcity;
      test byte ptr [eax+0x10],2; jnz nextcity;
      push eax; call {garrison}; test eax,eax; jz nextcity;
      mov eax,[esi+0x34]; sub eax,[edi+0x34]; cdq; xor eax,edx; sub eax,edx;
      mov ecx,eax; mov eax,[esi+0x38]; sub eax,[edi+0x38]; cdq; xor eax,edx; sub eax,edx;
      add eax,ecx; cmp eax,[esp+16]; jae nextcity;
      mov [esp+16],eax; mov [esp+12],esi;
    nextcity: inc dword ptr [esp+20]; cmp dword ptr [esp+20],100; jb city;
      mov eax,[esp+12]; test eax,eax; jz nextarmy;
    order: push eax; mov ecx,edi; mov edx,[edi]; call dword ptr [edx+8];
    nextarmy: inc dword ptr [esp+8]; cmp dword ptr [esp+8],100; jb army;
    done: add esp,24; pop edi; pop esi; pop ebx; pop ebp; ret 4
    ''')
    ai=code(f'''
      pushfd; pushad; mov ebx,[esp+40];
      push ebx; call {counterattack};
      test ebx,ebx; jz stock;
      mov esi,[ebx+0x7c]; test esi,esi; jz stock; mov eax,esi;
      call {index}; cmp eax,6; jae stock;
      push esi; call {garrison}; test eax,eax; jz stock;
      popad; popfd; ret 4;
    stock: popad; popfd; sub esp,0x40; push ebx; push ebp; jmp 0x421805
    ''')
    patch(0x421800,asm('sub esp,0x40;push ebx;push ebp',0x421800),asm(f'jmp {ai}',0x421800))
    # stdcall revenue(): one award per calendar month, inside the native month
    # accounting function before its cash snapshot. Never pays without garrison.
    revenue=code(f'''
      pushad; call {init};
      mov eax,[0x48d388]; xor edx,edx; mov ecx,720; div ecx; inc eax;
      cmp [{MONTH_ADDR}],eax; je done; mov [{MONTH_ADDR}],eax;
      mov esi,[0x48c3d8]; test esi,esi; jz done; add esi,0x23c;
      mov edi,100; xor ebx,ebx;
    town: mov eax,[esi]; test eax,eax; jz next;
      mov ebp,[eax+0x7c]; test ebp,ebp; jz next;
      mov eax,ebp; call {index}; cmp eax,6; jae next;
      push eax; push ebp; call {garrison}; pop ecx; test eax,eax; jz lost;
      bts dword ptr [{OCCUPIED_ADDR}],ecx;
      add ebx,150000; jmp next;
    lost: btr dword ptr [{OCCUPIED_ADDR}],ecx;
    next: add esi,4; dec edi; jnz town;
      mov ecx,0x48d380; call 0x4466e0;
      cmp eax,1; je double_tribute; cmp eax,7; jne pay;
    double_tribute: add ebx,ebx;
    pay:
      mov eax,[0x46e5d8]; cmp eax,2000000000; jge done;
      add eax,ebx; cmp eax,2000000000; jle store; mov eax,2000000000;
    store: mov [0x46e5d8],eax;
    done: popad; ret
    ''')
    month_hook=code(f'call {revenue};mov eax,[0x46e5dc];jmp 0x430170')
    patch(0x43016b,asm('mov eax,[0x46e5dc]',0x43016b),asm(f'jmp {month_hook}',0x43016b))
    # Debt-free ending is shown once. Continue ordinary month-end processing
    # thereafter, including wages and insolvency rules; no fabricated new debt.
    debt=code(f'''
      pushfd; push eax; call {init};
      cmp dword ptr [{DEBT_ADDR}],1; je continued;
      mov dword ptr [{DEBT_ADDR}],1;
      pop eax; popfd; mov dword ptr [0x48d398],0; jmp 0x43030f;
    continued: pop eax; popfd; jmp 0x430348
    ''')
    patch(0x430305,asm('mov dword ptr [0x48d398],0',0x430305),asm(f'jmp {debt}',0x430305)+b'\x90'*5)
    patch(0x43031e,asm('jmp 0x430661',0x43031e),asm('jmp 0x430348',0x43031e)+b'\x90'*3)
    # EAX=machine ID, return boolean. Historic saves gain unlocks from actual
    # success evidence; initial refusals with the same ending value stay locked.
    unlock=code(f'''
      cmp eax,17; je mk1; cmp eax,18; je mk2; cmp eax,19; je dragon;
      cmp eax,20; je land; cmp eax,21; je fortress; jmp no;
    mk1: cmp dword ptr [{BASE+10*4}],6; jl no;
      cmp dword ptr [{BASE+10*4}],10; jg no; jmp yes;
    mk2: cmp dword ptr [{BASE+10*4}],10; je yes; jmp no;
    dragon: cmp dword ptr [{BASE+5*4}],10; jne no;
      cmp dword ptr [{BASE+20*4}],1; jne no;
      cmp dword ptr [{BASE+21*4}],1; je yes; jmp no;
    land: cmp dword ptr [{BASE+9*4}],10; je yes; jmp no;
    fortress: cmp dword ptr [{BASE+11*4}],10; je yes;
    no: xor eax,eax; ret;
    yes: mov eax,1; ret
    ''')
    table=arr([x for ident,name,iron,oil,gold,condition in BOSSES
               for x in (ident,s(name),iron,oil,gold,s(condition))])
    # stdcall manufacture(formation, table row). One giant in an otherwise
    # empty armored formation; its existing commander is the stock driver.
    manufacture=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      mov ebx,[ebp+8]; mov esi,[ebp+12];
      cmp esi,{table}; jb invalid; cmp esi,{table+4*24}; ja invalid;
      mov eax,esi; sub eax,{table}; xor edx,edx; mov ecx,24; div ecx;
      test edx,edx; jnz invalid;
      mov eax,[esi]; call {unlock}; test eax,eax; jz locked;
      test ebx,ebx; jz invalid; cmp dword ptr [ebx],1; jne invalid;
      mov ecx,1; cmp dword ptr [esi],19; jne category;
      mov ecx,2;
    category: cmp [ebx+0x18],ecx; jne invalid;
      cmp dword ptr [ebx+0x14],1; jl invalid;
      cmp dword ptr [ebx+0x14],9; jg invalid;
      mov eax,[ebx+4]; test eax,eax; jz invalid;
      cmp dword ptr [eax+4],1; jne invalid;
      cmp [ebx+8],eax; jne invalid;
      cmp dword ptr [ebx+0x1c],1; jne invalid;
      mov edi,[ebx+0x34]; test edi,edi; jz invalid;
      cmp [ebx+0xfc],edi; jne invalid;
      mov ecx,10; cmp dword ptr [esi],19; jne crewclass; mov ecx,9;
    crewclass: cmp [edi+0x38],ecx; jne invalid;
      cmp dword ptr [edi+4],0; jne invalid;
      cmp dword ptr [edi+0x54],0; jle invalid;
      lea edx,[ebx+0x3c]; mov ecx,9;
    slots: cmp dword ptr [edx],0; jne invalid; add edx,4; loop slots;
      mov eax,[esi+8]; cmp [0x46e5dc],eax; jl poor;
      mov eax,[esi+12]; cmp [0x46e5e0],eax; jl poor;
      mov eax,[esi+16]; cmp [0x46e5d8],eax; jl poor;
      mov ecx,[0x4880f0]; test ecx,ecx; jz invalid;
      push dword ptr [esi]; call 0x416660; test eax,eax; jz invalid;
      push eax; push 0; push edi; push eax; call 0x4168b0; add esp,12; pop edx;
      cmp dword ptr [edx+4],21; jne mobile; mov dword ptr [edx+0x88],12;
    mobile:
      mov dword ptr [edx],1; mov [ebx+0x4c],edx;
      inc dword ptr [ebx+0x20]; cmp dword ptr [edx+8],0; jne counts;
      inc dword ptr [ebx+0x24];
    counts: push ebx; call 0x421160;
      mov eax,[esi+8]; sub [0x46e5dc],eax;
      mov eax,[esi+12]; sub [0x46e5e0],eax;
      mov eax,[esi+16]; sub [0x46e5d8],eax;
      mov eax,1; jmp done;
    poor: mov eax,2; jmp done;
    locked: mov eax,3; jmp done;
    invalid: xor eax,eax;
    done: pop edi; pop esi; pop ebx; pop ebp; ret 8
    ''')
    # Reuse the exact stored instance rather than manufacturing a replacement.
    # Inventory ownership is proved by traversing the native pointer list.
    stored=code('''
      push esi; push edi; mov edx,[esp+12]; mov ecx,[esp+16];
      test edx,edx; jz no; cmp dword ptr [edx+4],1; jne no;
      cmp ecx,17; jb no; cmp ecx,21; ja no;
      mov edi,[edx+0x50a64]; test edi,edi; jz no;
      mov esi,[edi]; mov edx,10000;
    scan: cmp esi,edi; je no; test esi,esi; jz no;
      mov eax,[esi+8]; test eax,eax; jz next;
      cmp [eax+4],ecx; je found;
    next: mov esi,[esi]; dec edx; jnz scan;
    no: xor eax,eax; jmp done;
    found: mov eax,esi;
    done: pop edi; pop esi; ret 8
    ''')
    reassign=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,8;
      mov ebx,[ebp+8]; test ebx,ebx; jz invalid;
      cmp dword ptr [ebx],1; jne invalid;
      mov eax,[ebx+4]; test eax,eax; jz invalid;
      cmp dword ptr [eax+4],1; jne invalid;
      cmp [ebx+8],eax; jne invalid; mov [esp],eax;
      cmp dword ptr [ebx+0x14],1; jl invalid;
      cmp dword ptr [ebx+0x14],9; jg invalid;
      push dword ptr [ebp+12]; push eax; call {stored}; test eax,eax; jz invalid;
      mov [esp+4],eax; mov esi,[eax+8];
      cmp dword ptr [esi+0x54],0; jle invalid;
      cmp dword ptr [esi+0x8c],0; jne invalid;
      cmp dword ptr [esi+0x90],0; jne invalid;
      mov ecx,1; cmp dword ptr [esi+4],19; jne type; mov ecx,2;
    type: cmp [ebx+0x18],ecx; jne invalid;
      cmp dword ptr [ebx+0x1c],1; jne invalid;
      cmp dword ptr [ebx+0x20],0; jne invalid;
      mov edi,[ebx+0x34]; test edi,edi; jz invalid;
      cmp [ebx+0xfc],edi; jne invalid;
      cmp dword ptr [edi+4],0; jne invalid;
      cmp dword ptr [edi+0x54],0; jle invalid;
      mov ecx,10; cmp dword ptr [esi+4],19; jne crew; mov ecx,9;
    crew: cmp [edi+0x38],ecx; jne invalid;
      lea edx,[ebx+0x3c]; mov ecx,9;
    slots: cmp dword ptr [edx],0; jne invalid; add edx,4; loop slots;
      mov eax,[esp]; cmp dword ptr [eax+0x50a68],0; jle invalid;
      push 0; push edi; push esi; call 0x4168b0; add esp,12;
      mov edx,[esp+4]; mov eax,[edx]; mov ecx,[edx+4];
      mov [ecx],eax; mov [eax+4],ecx;
      mov eax,[esp]; dec dword ptr [eax+0x50a68];
      mov [ebx+0x4c],esi; mov dword ptr [esi],1;
      inc dword ptr [ebx+0x20]; cmp dword ptr [esi+8],0; jne speed;
      inc dword ptr [ebx+0x24];
    speed: cmp dword ptr [esi+4],21; jne mobile; mov dword ptr [esi+0x88],12;
    mobile: push ebx; call 0x421160;
      push dword ptr [esp+4]; call 0x4500e6; add esp,4;
      mov eax,1; jmp done;
    invalid: xor eax,eax;
    done: add esp,8; pop edi; pop esi; pop ebx; pop ebp; ret 8
    ''')
    title=s('포룸 특수병기 제작')
    names=arr([s(x[1]) for x in BOSSES[:4]]+[s('다음: 포트레스 / 닫기')])
    finalnames=arr([s('포트레스'),s('이전 목록'),s('닫기')])
    confirm=arr([s('자원 사용 후 제작·배치'),s('취소')])
    reassign_confirm=arr([s('보관 중인 병기 재배치 (무료)'),s('취소')])
    rowfmt=s('%s@N철 %d / 석유 %d / 금 %d@N%s@w')
    result=arr([s('포룸에 군단장 1명만 남긴 군단이 필요합니다. 블랙드래곤은 파일럿의 항공 군단, 나머지는 드라이버의 장갑 군단입니다. 병사와 차량을 빼 주세요. 보관 병기는 정비와 조종사 상태도 확인하세요.@w'),
                s('선택한 군단에 병기를 배치했습니다. 일반 출격과 저장이 가능합니다.@w'),
                s('철, 석유 또는 금이 부족합니다.@w'),s('이벤트 성공 조건을 아직 만족하지 않았습니다.@w')])
    main=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,600;
      mov edi,esp;
      push {s('포룸 F9에서 제작·재배치합니다. 같은 보관 병기가 있으면 무료로 다시 배치합니다. 군단장 1명만 남긴 빈 군단을 주둔시키세요. 블랙드래곤은 파일럿의 항공 군단, 나머지는 드라이버의 장갑 군단에 1기를 배치합니다.@w')};
      push {title}; push dword ptr [ebp+8]; call {speech};
      push {s('적 용병단은 점령 도시가 없어야 본거지를 공격할 수 있습니다. 점령한 본거지에 아군 군단을 남기면 월말 15만 겔더를 받습니다. 철수하면 적 부대가 다시 돌아올 수 있습니다.@w')};
      push {title}; push dword ptr [ebp+8]; call {speech};
    list: push 5; push {names}; push dword ptr [ebp+8]; call {select};
      cmp eax,4; jb row; cmp eax,4; jne done;
      push 3; push {finalnames}; push dword ptr [ebp+8]; call {select};
      cmp eax,1; je list; test eax,eax; jnz done; mov eax,4;
    row: imul eax,eax,24; add eax,{table}; mov esi,eax;
      push dword ptr [esi+20]; push dword ptr [esi+16]; push dword ptr [esi+12];
      push dword ptr [esi+8]; push dword ptr [esi+4]; push {rowfmt}; push edi;
      call dword ptr [0x46019c]; add esp,28;
      push edi; push {title}; push dword ptr [ebp+8]; call {speech};
      mov dword ptr [edi+516],0;
      mov eax,[ebp+8]; cmp dword ptr [eax],0x462738; jne lockedcheck;
      mov eax,[eax+0x50]; push dword ptr [esi]; push eax; call {stored};
      test eax,eax; jz lockedcheck; mov [edi+516],eax; jmp choosearmy;
    lockedcheck: mov eax,[esi]; call {unlock}; test eax,eax; jnz choosearmy;
      mov eax,3; jmp message;
    choosearmy: mov eax,[ebp+8]; cmp dword ptr [eax],0x462738; jne invalid;
      mov eax,[eax+0x50]; test eax,eax; jz invalid;
      cmp dword ptr [eax+4],1; jne invalid;
      mov ebx,eax; xor ecx,ecx;
    find: mov eax,[ebx+ecx*4+0x50654]; test eax,eax; jz next;
      cmp dword ptr [eax],1; jne next;
      mov edx,1; cmp dword ptr [esi],19; jne findtype; mov edx,2;
    findtype: cmp [eax+0x18],edx; jne next;
      cmp dword ptr [eax+0x1c],1; jne next; cmp dword ptr [eax+0x20],0; jne next;
      mov edx,[eax+0x34]; test edx,edx; jz next;
      push ecx; mov ecx,10; cmp dword ptr [esi],19; jne findcrew; mov ecx,9;
    findcrew: cmp [edx+0x38],ecx; pop ecx; jne next;
      mov [edi+512],eax; jmp ask;
    next: inc ecx; cmp ecx,9; jl find;
    invalid: xor eax,eax; jmp message;
    ask: mov eax,[edi+512]; push dword ptr [eax+0x14];
      push {s('포룸의 제%d군단에 병기를 배치합니다.@w')}; push edi;
      call dword ptr [0x46019c]; add esp,12;
      push edi; push {title}; push dword ptr [ebp+8]; call {speech};
      mov eax,{confirm}; cmp dword ptr [edi+516],0; je confirmation;
      mov eax,{reassign_confirm};
    confirmation: push 2; push eax; push dword ptr [ebp+8]; call {select};
      test eax,eax; jnz list;
      cmp dword ptr [edi+516],0; je create;
      push dword ptr [esi]; push dword ptr [edi+512]; call {reassign}; jmp message;
    create: push esi; push dword ptr [edi+512]; call {manufacture};
    message: push dword ptr [eax*4+{result}]; push {title};
      push dword ptr [ebp+8]; call {speech}; jmp list;
    done: add esp,600; pop edi; pop esi; pop ebx; pop ebp; ret 4
    ''')
    hotkey=code(f'''
      pushfd; pushad;
      cmp dword ptr [0x4880e0],0; jne done;
      mov edi,[esi+0x18]; test edi,edi; jz done;
      cmp dword ptr [edi],0x462738; je dispatch;
      cmp dword ptr [edi],0x461954; jne done;
    dispatch:
      cmp dword ptr [0x48c3d8],0; je done;
      {f'push edi; call {world_tick}; test eax,eax; jnz done;' if world_tick else ''}
      {f'call {imperial_seed};' if imperial_seed else ''}
      {f'call {black_power_restore};' if black_power_restore else ''}
      {f'push edi; call {process}; test eax,eax; jnz done;' if process else ''}
      cmp dword ptr [edi],0x462738; jne done;
      mov ecx,[0x487f3c]; test ecx,ecx; jz done;
      push 1; push 0x78; call 0x406390; test eax,eax; jz done;
      push edi; call {main};
    done: popad; popfd; mov ecx,[0x487f3c]; jmp 0x40a461
    ''')
    patch(0x40a45b,asm('mov ecx,[0x487f3c]',0x40a45b),asm(f'jmp {hotkey}',0x40a45b)+b'\x90')
    return dict(campaign=dict(init=hex(init),eligible=hex(eligible),index=hex(index),garrison=hex(garrison),
        ingress=hex(ingress),attach=hex(attach),ai=hex(ai),counterattack=hex(counterattack),revenue=hex(revenue),debt=hex(debt),
        unlock=hex(unlock),stored=hex(stored),reassign=hex(reassign),manufacture=hex(manufacture),table=hex(table),main=hex(main),hotkey=hex(hotkey),
        monthly_tribute=150000,seasonal_tribute_months=[1,7],seasonal_tribute=300000,bosses=BOSSES,reserved_globals=[94,95,96,97],
        endings='Victory and debt-free movies retained; return to world instead of title. Failure endings unchanged.'))

