"""In-game F8 event journal and explicit one-shot force settings.

Story records are read-only; only opt-in reserved settings are written.
"""
import struct
from event_catalog import EVENTS,RELATED
from event_force_patch import MAGIC_ADDR,MASK_ADDR,MAGIC

def emit(put,asm,address,patch):
    strings={}
    def s(t):
        if t not in strings:strings[t]=put(t.encode('cp949')+b'\0')
        return strings[t]
    def code(t):return put(asm(t,address()))
    def arr(values):return put(struct.pack('<%dI'%len(values),*values))
    def pages(texts):
        # Stock speech window has three scrolling lines. Break prose at word
        # boundaries to give each acknowledgement a small, readable page.
        out=[]
        for text in texts:
            words=text.split();part=''
            for word in words:
                candidate=(part+' '+word).strip()
                if len(candidate.encode('cp949'))>140 and part:
                    out.append(s(part+'@w'));part=word
                else:part=candidate
            if part:out.append(s(part+'@w'))
        return arr(out+[0])
    unknown=s('기록에 없는 단계입니다. 숫자를 확인하세요.')
    records=[]
    for e in EVENTS:
        states=arr([s(e['states'].get(i,'기록에 없는 단계입니다. 숫자를 확인하세요.')) for i in range(12)])
        records.extend([s(e['name']),0x48d398+4*e['flag'],states,pages(e['conditions']),pages(e['route']),arr(e['related']+[0])])
    table=arr(records)
    # __stdcall select(parent, pointer-array, count), 0-based result.
    select=code('''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,0x3c;
      mov esi,esp; mov ecx,esi; call 0x412f40;
      push 235; push 88; push dword ptr [ebp+8]; mov ecx,esi; call 0x413080;
      mov edi,[ebp+12]; mov ebx,[ebp+16];
    append: test ebx,ebx; jz choose; push dword ptr [edi]; mov ecx,esi; call 0x4130b0;
      add edi,4; dec ebx; jmp append;
    choose: mov ecx,esi; call 0x413240; push eax;
      mov ecx,esi; call 0x412fe0; pop eax;
      add esp,0x3c; pop edi; pop esi; pop ebx; pop ebp; ret 12
    ''')
    # __stdcall speech(parent, title, text). Text is owned by caller throughout.
    speech=code('''
      push ebp; mov ebp,esp; push esi; sub esp,0x150;
      mov esi,esp; mov ecx,esi; call 0x412580;
      push 235; push 88; push dword ptr [ebp+8]; mov ecx,esi; call 0x412810;
      push 0; push dword ptr [ebp+12]; mov ecx,esi; call 0x412910;
      push dword ptr [ebp+16]; mov ecx,esi; call 0x412960;
      mov ecx,esi; call 0x412760;
      add esp,0x150; pop esi; pop ebp; ret 12
    ''')
    showpages=code(f'''
      push ebp; mov ebp,esp; push esi; mov esi,[ebp+16];
    again: mov eax,[esi]; test eax,eax; jz done;
      push eax; push dword ptr [ebp+12]; push dword ptr [ebp+8]; call {speech};
      add esi,4; jmp again;
    done: pop esi; pop ebp; ret 12
    ''')
    # __stdcall related(parent, indices): format saved values without changing them.
    reltable=arr([arr([s(RELATED[i][0]),arr([s(RELATED[i][1].get(v,'저장된 수치')) for v in range(12)])]) if i in RELATED else 0 for i in range(31)])
    relfmt=s('%s : %d@N%s@w');reltitle=s('관련 진행 기록')
    related=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,256;
      mov edi,esp; mov esi,[ebp+12];
    again: mov eax,[esi]; test eax,eax; jz done;
      mov ebx,[eax*4+{reltable}]; mov edx,[eax*4+0x48d398];
      mov ecx,{s('저장된 수치')}; cmp edx,12; jae format;
      mov ecx,[ebx+4]; mov ecx,[ecx+edx*4];
    format: push ecx; push edx; push dword ptr [ebx]; push {relfmt}; push edi;
      call dword ptr [0x46019c]; add esp,20;
      push edi; push {reltitle}; push dword ptr [ebp+8]; call {speech};
      add esi,4; jmp again;
    done: add esp,256; pop edi; pop esi; pop ebx; pop ebp; ret 8
    ''')
    allrelated=arr(list(RELATED)+[0])
    guide=pages(['주요 사건 9개와 관련 세부 기록을 모두 공개합니다. 목록은 다음 페이지를 누르면 처음으로 돌아옵니다.',
                 '종료는 성공만 뜻하지 않습니다. 원본이 같은 값으로 저장하는 거절과 실패는 구분하지 못하므로 사건 설명을 함께 확인하세요.',
                 '시작 조건은 모두 함께 만족해야 합니다. 미시작은 값 0이며, 이미 종료한 사건은 미시작이 아닙니다.',
                 '조건을 맞춘 뒤 해당 도시나 건물에 들어가거나 월드맵으로 나가야 원래 이벤트 처리가 실행됩니다.',
                 '발동 조건과 강제 설정에서 미시작 사건을 예약할 수 있습니다. 원래 장소에 들어가면 조건과 선행 분기를 무시하고 시작합니다.',
                 '다른 주요 사건이 진행 중이면 예약은 대기합니다. 이미 시작, 거절, 완료한 사건은 예약할 수 없습니다. 예약은 게임 저장에 포함됩니다.',
                 '날짜, 돈, 부대 수는 현재 값입니다. 도시 의뢰 조건은 해당 도시 관청의 수락 및 보고 대기 의뢰도 확인하세요.'])
    # Current metrics use pure getters; RequestCount is intentionally NOT called
    # because that function modifies the quest-list iterator while searching.
    snapshotfmt=s('비트만 레벨 %d / 동료 명단 %d명@N편성 군단 %d / 부채 %d 겔더@w')
    snapshot=code(f'''
      push ebp; mov ebp,esp; push edi; sub esp,256; mov edi,esp;
      push 3; call 0x44b5b0; push eax;
      push 1; call 0x44b5b0; push eax;
      push 0; call 0x44b5b0; push eax;
      push 1; push {s('비트만')}; call 0x44b660; push eax;
      push {snapshotfmt}; push edi; call dword ptr [0x46019c]; add esp,24;
      push edi; push {s('시작 조건 현재 값')}; push dword ptr [ebp+8]; call {speech};
      mov eax,[0x48d3e4]; push eax; push {s('다른 주요 사건 진행 중: %d (0=아니오)@w')}; push edi;
      call dword ptr [0x46019c]; add esp,12;
      push edi; push {s('시작 조건 현재 값')}; push dword ptr [ebp+8]; call {speech};
      push 1; call 0x44b8c0; push eax; push 2; call 0x44b8c0; push eax;
      push 3; call 0x44b8c0; push eax; push {s('현재 날짜: %d년 %d월 %d일@w')}; push edi;
      call dword ptr [0x46019c]; add esp,20;
      push edi; push {s('시작 조건 현재 값')}; push dword ptr [ebp+8]; call {speech};
      add esp,256; pop edi; pop ebp; ret 4
    ''')
    forcemenu=arr([s(t) for t in ['원래 발동 조건 보기','조건 무시 예약 켜기','조건 무시 예약 끄기','사건 상세로']])
    forceui=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi;
      mov esi,[ebp+12]; mov eax,[esi+4]; sub eax,0x48d3a4; shr eax,2;
      mov ecx,eax; mov ebx,1; shl ebx,cl;
    status: mov eax,[esi+4]; cmp dword ptr [eax],0; jne locked;
      mov edi,{s('조건 무시 예약: 꺼짐@w')};
      cmp dword ptr [{MAGIC_ADDR}],{MAGIC}; jne show;
      test dword ptr [{MASK_ADDR}],ebx; jz show;
      mov edi,{s('조건 무시 예약: 켜짐@N원래 발동 장소에 들어가세요. 다른 주요 사건 진행 중에는 대기합니다.@w')}; jmp show;
    locked: mov edi,{s('이미 시작하거나 종료한 사건입니다. 다시 실행하거나 예약할 수 없습니다.@w')};
    show: push edi; push dword ptr [esi]; push dword ptr [ebp+8]; call {speech};
    menu: push 4; push {forcemenu}; push dword ptr [ebp+8]; call {select};
      cmp eax,3; jae done; test eax,eax; jz conditions; cmp eax,2; je disable;
      mov eax,[esi+4]; cmp dword ptr [eax],0; jne status;
      cmp dword ptr [{MAGIC_ADDR}],{MAGIC}; je initialized;
      mov dword ptr [{MASK_ADDR}],0; mov dword ptr [{MAGIC_ADDR}],{MAGIC};
    initialized: or dword ptr [{MASK_ADDR}],ebx; jmp status;
    disable: cmp dword ptr [{MAGIC_ADDR}],{MAGIC}; jne status;
      mov eax,ebx; not eax; and dword ptr [{MASK_ADDR}],eax; jmp status;
    conditions: push dword ptr [esi+12]; push dword ptr [esi]; push dword ptr [ebp+8]; call {showpages}; jmp menu;
    done: pop edi; pop esi; pop ebx; pop ebp; ret 8
    ''')
    submenu=arr([s(t) for t in ['현재 단계와 다음 진행','발동 조건과 강제 설정','전체 진행 순서와 선택 분기','관련 진행 기록','사건 목록으로']])
    extramenu=arr([s(t) for t in ['전체 세부 진행 기록','시작 조건의 현재 값','이벤트 진행창 안내']])
    menuformat=s('%s : %s');stageformat=s('현재 단계 %d@N%s@w')
    # Stack slots: main-page index, selected event; choices[5], buffers[3*256].
    main=code(f'''
      push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,0x420;
      mov edi,esp; mov dword ptr [edi],0;
    list: mov eax,[edi]; cmp eax,3; je extras;
      lea eax,[eax+eax*2]; imul eax,eax,24; add eax,{table}; mov esi,eax;
      xor ebx,ebx;
    row: mov eax,[esi+4]; mov edx,[eax]; mov ecx,{s('진행 중')};
      test edx,edx; jnz notzero; mov ecx,{s('미시작')}; jmp labelready;
    notzero: cmp edx,10; jl labelready; mov ecx,{s('종료/분기')};
    labelready: mov eax,ebx; shl eax,8; lea eax,[edi+eax+0x20]; mov [edi+ebx*4+8],eax;
      push ecx; push dword ptr [esi]; push {menuformat}; push eax;
      call dword ptr [0x46019c]; add esp,16;
      add esi,24; inc ebx; cmp ebx,3; jl row; jmp choose;
    extras: xor ebx,ebx;
    extrarow: mov eax,[ebx*4+{extramenu}]; mov [edi+ebx*4+8],eax;
      inc ebx; cmp ebx,3; jl extrarow;
    choose: mov dword ptr [edi+20],{s('다음 페이지 (순환)')};
      mov dword ptr [edi+24],{s('닫기 - 게임으로')};
      push 5; lea eax,[edi+8]; push eax; push dword ptr [ebp+8]; call {select};
      cmp eax,3; je nextpage; cmp eax,3; ja done;
      mov ebx,[edi]; cmp ebx,3; je utility;
      lea ebx,[ebx+ebx*2]; add eax,ebx; imul eax,eax,24; add eax,{table}; mov [edi+4],eax;
    detailmenu: push 5; push {submenu}; push dword ptr [ebp+8]; call {select};
      cmp eax,4; jae list; mov esi,[edi+4];
      cmp eax,1; je conditions; cmp eax,2; je route; cmp eax,3; je records;
      mov eax,[esi+4]; mov edx,[eax]; mov ecx,{unknown};
      cmp edx,12; jae statefmt; mov ecx,[esi+8]; mov ecx,[ecx+edx*4];
    statefmt: lea ebx,[edi+0x320]; push ecx; push edx; push {stageformat}; push ebx;
      call dword ptr [0x46019c]; add esp,16;
      push ebx; push dword ptr [esi]; push dword ptr [ebp+8]; call {speech}; jmp detailmenu;
    conditions: push esi; push dword ptr [ebp+8]; call {forceui}; jmp detailmenu;
    route: push dword ptr [esi+16];
    textpages: push dword ptr [esi]; push dword ptr [ebp+8]; call {showpages}; jmp detailmenu;
    records: mov eax,[esi+20]; cmp dword ptr [eax],0; je noextra;
      push eax; push dword ptr [ebp+8]; call {related}; jmp detailmenu;
    noextra: push {s('이 사건은 별도 세부 기록이 없습니다. 현재 단계와 실제 동료 명단을 함께 확인하세요.@w')};
      push dword ptr [esi]; push dword ptr [ebp+8]; call {speech}; jmp detailmenu;
    utility: test eax,eax; jz allrecords; cmp eax,1; je metrics;
      push {guide}; push {s('이벤트 진행창 안내')}; push dword ptr [ebp+8]; call {showpages}; jmp list;
    metrics: push dword ptr [ebp+8]; call {snapshot}; jmp list;
    allrecords: push {allrelated}; push dword ptr [ebp+8]; call {related}; jmp list;
    nextpage: inc dword ptr [edi]; and dword ptr [edi],3; jmp list;
    done: add esp,0x420; pop edi; pop esi; pop ebx; pop ebp; ret 4
    ''')
    # Shared map/city toolbar update: native dialogs run their own input loop.
    # Restrict the parent type so this never runs on battle or title screens.
    hotkey=code(f'''
      pushfd; pushad;
      cmp dword ptr [0x4880e0],0; jne done;
      mov edi,[esi+0x18]; test edi,edi; jz done;
      mov eax,[edi]; cmp eax,0x461954; je supported;
      cmp eax,0x462738; jne done;
    supported: cmp dword ptr [0x48c3d8],0; je done;
      mov ecx,[0x487f3c]; test ecx,ecx; jz done;
      push 1; push 0x77; call 0x406390; test eax,eax; jz done;
      push edi; call {main};
    done: popad; popfd; mov ecx,[0x487f3c]; jmp 0x40a43e
    ''')
    patch(0x40a438,asm('mov ecx,[0x487f3c]',0x40a438),asm(f'jmp {hotkey}',0x40a438)+b'\x90')
    return dict(event_journal=dict(hotkey='F8',hook=hex(hotkey),main=hex(main),select=hex(select),speech=hex(speech),pages=hex(showpages),related=hex(related),snapshot=hex(snapshot),forceui=hex(forceui),table=hex(table),events=len(EVENTS),related_records=len(RELATED),persistent_writes='Explicit force setting only; reserved globals 98/99'))
