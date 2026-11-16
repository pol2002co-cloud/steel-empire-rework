"""Post-ending event state inside stock serialized script globals 31..84.

Cooldowns store remaining days, not truncated dates. A full-width last-tick day
lets a resumed save safely expire timers after arbitrarily long time gaps.
"""
BASE = 0x48d398 + 31*4
WORDS = 54
MAGIC = 0x57455631
RNG = BASE+4
NEXT_OFFER = BASE+8
LAST_DAY = BASE+12
MONTH = BASE+16
BATTLES = BASE+20
DONE = BASE+24
COOLDOWNS = BASE+32
CARDS = BASE+104
CARD_WORDS = 8
CARD_COUNT = 3
EVENT_COUNT = 38
TIMER_COUNT = 36
# IDs 36/37 reuse never-needed timers of one-shot events 20/22; cards stay put.
COOLDOWN_INDEX = tuple(range(36))+(20,22)
EMPTY, OFFER, ACCEPTED, PENDING_REWARD = range(4)
COST_PAID, COMBAT_DONE, DELIVERY_DONE = 1, 2, 4
GOLD_PAID, IRON_PAID, OIL_PAID, ITEM_PAID, BATTLE = 8, 16, 32, 64, 128


def emit(put, asm, address):
    """Return stdcall helper addresses; getslot exposes a bounded 8-DWORD card.

    Card fields: control, originTown, destinationTown, armyHomeTown, legion,
    acceptedDay, deadlineDay, progress. Control bytes: ID(0..37), stage, status,
    flags. Caller applies actual rewards before finish and persists partial
    payment flags before a subsequent component can be offered again. Call tick
    with the current day/month before processing a dated UI action or finish.
    """
    def code(source):
        return put(asm(source, address()))

    init = code(f'''
      cmp dword ptr [{BASE:#x}],{MAGIC:#x}; je existing;
      push edi;
      mov edi,{BASE:#x}; xor eax,eax; mov ecx,{WORDS}; rep stosd;
      mov eax,[esp+8]; mov [{LAST_DAY:#x}],eax;
      xor eax,0x53454544; mov [{RNG:#x}],eax;
      mov eax,[esp+8]; add eax,7; jnc scheduled;
      mov eax,0xffffffff;
    scheduled:
      mov [{NEXT_OFFER:#x}],eax; mov dword ptr [{MONTH:#x}],0xffffffff;
      mov dword ptr [{BASE:#x}],{MAGIC:#x}; pop edi;
    existing:
      mov eax,1; ret 4
    ''')
    tick = code(f'''
      push esi; push edi;
      mov esi,[esp+12]; push esi; call {init:#x};
      mov eax,esi; sub eax,[{LAST_DAY:#x}]; jc backwards;
      mov [{LAST_DAY:#x}],esi;
      test eax,eax; jz month;
      cmp eax,65535; ja clear_timers;
      mov edi,{COOLDOWNS:#x}; mov ecx,{TIMER_COUNT};
    decrement:
      movzx edx,word ptr [edi]; cmp edx,eax; jbe expired;
      sub edx,eax; mov word ptr [edi],dx; jmp next;
    expired:
      mov word ptr [edi],0;
    next:
      add edi,2; dec ecx; jnz decrement; jmp month;
    clear_timers:
      mov edi,{COOLDOWNS:#x}; xor eax,eax; mov ecx,18; rep stosd; jmp month;
    backwards:
      mov [{LAST_DAY:#x}],esi;
    month:
      mov eax,[esp+16]; cmp eax,[{MONTH:#x}]; je done;
      mov [{MONTH:#x}],eax; mov dword ptr [{BATTLES:#x}],0;
    done:
      mov eax,1; pop edi; pop esi; ret 8
    ''')
    getslot = code(f'''
      cmp dword ptr [{BASE:#x}],{MAGIC:#x}; jne invalid;
      mov eax,[esp+4]; cmp eax,{CARD_COUNT}; jae invalid;
      shl eax,5; add eax,{CARDS:#x}; ret 4;
    invalid:
      xor eax,eax; ret 4
    ''')
    getfield = code(f'''
      cmp dword ptr [esp+8],{CARD_WORDS}; jae invalid;
      push dword ptr [esp+4]; call {getslot:#x}; test eax,eax; jz invalid;
      mov edx,[esp+8]; mov eax,[eax+edx*4]; ret 8;
    invalid:
      xor eax,eax; ret 8
    ''')
    clear = code(f'''
      push edi; push dword ptr [esp+8]; call {getslot:#x};
      test eax,eax; jz done;
      mov edi,eax; xor eax,eax; mov ecx,{CARD_WORDS}; rep stosd; mov eax,1;
    done:
      pop edi; ret 4
    ''')
    setfield = code(f'''
      push ebx; push esi; push edi;
      mov ecx,[esp+20]; cmp ecx,{CARD_WORDS}; jae invalid;
      push dword ptr [esp+16]; call {getslot:#x}; test eax,eax; jz invalid;
      mov ebx,eax; mov ecx,[esp+20]; mov esi,[esp+24];
      test ecx,ecx; jz control;
      cmp ecx,3; ja legion;
      cmp esi,100; ja invalid; jmp write;
    legion:
      cmp ecx,4; jne write; cmp esi,15; ja invalid; jmp write;
    control:
      test esi,esi; jnz validate;
      push dword ptr [esp+16]; call {clear:#x}; jmp done;
    validate:
      mov eax,esi; and eax,255; cmp eax,{EVENT_COUNT}; jae invalid;
      mov eax,esi; shr eax,16; and eax,255;
      cmp eax,{OFFER}; jb invalid; cmp eax,{PENDING_REWARD}; ja invalid;
      mov edi,{CARDS:#x}; mov ecx,{CARD_COUNT};
    scan:
      cmp edi,ebx; je next;
      mov eax,[edi]; test eax,0xff0000; jz next;
      mov edx,eax; xor edx,esi; test edx,255; jz invalid;
      test esi,0x80000000; jz next;
      test eax,0x80000000; jnz invalid;
    next:
      add edi,32; dec ecx; jnz scan; xor ecx,ecx;
    write:
      mov [ebx+ecx*4],esi; mov eax,1; jmp done;
    invalid:
      xor eax,eax;
    done:
      pop edi; pop esi; pop ebx; ret 12
    ''')
    completed = code(f'''
      cmp dword ptr [{BASE:#x}],{MAGIC:#x}; jne invalid;
      mov eax,[esp+4]; cmp eax,{EVENT_COUNT}; jae invalid;
      bt dword ptr [{DONE:#x}],eax; setc al; movzx eax,al; ret 4;
    invalid:
      xor eax,eax; ret 4
    ''')
    count_completed = code(f'''
      cmp dword ptr [{BASE:#x}],{MAGIC:#x}; jne invalid;
      xor eax,eax; xor ecx,ecx;
    count:
      bt dword ptr [{DONE:#x}],ecx; adc eax,0;
      inc ecx; cmp ecx,{EVENT_COUNT}; jb count; ret;
    invalid:
      xor eax,eax; ret
    ''')
    can_offer = code(f'''
      push ebx; push esi; push edi;
      cmp dword ptr [{BASE:#x}],{MAGIC:#x}; jne invalid;
      mov ebx,[esp+16]; cmp ebx,{EVENT_COUNT}; jae invalid;
      cmp dword ptr [esp+24],0; je check_done;
      cmp dword ptr [{BATTLES:#x}],1; jae invalid;
    check_done:
      cmp dword ptr [esp+20],0; jne cooldown;
      bt dword ptr [{DONE:#x}],ebx; jc invalid; jmp capacity;
    cooldown:
      mov edx,ebx; cmp edx,36; jb timer; sub edx,16;
      cmp ebx,37; jne timer; inc edx;
    timer:
      cmp word ptr [{COOLDOWNS:#x}+edx*2],0; jne invalid;
    capacity:
      mov edi,{CARDS:#x}; mov ecx,{CARD_COUNT}; xor esi,esi;
    scan:
      mov eax,[edi]; test eax,0xff0000; jnz active;
      inc esi; jmp next;
    active:
      mov edx,eax; and edx,255; cmp edx,ebx; je invalid;
      cmp dword ptr [esp+24],0; je next;
      test eax,0x80000000; jnz invalid;
    next:
      add edi,32; dec ecx; jnz scan;
      xor eax,eax; test esi,esi; setnz al; jmp done;
    invalid:
      xor eax,eax;
    done:
      pop edi; pop esi; pop ebx; ret 12
    ''')
    finish = code(f'''
      push esi; push edi;
      mov esi,[esp+16]; cmp esi,65535; ja invalid;
      push dword ptr [esp+12]; call {getslot:#x}; test eax,eax; jz invalid;
      mov edi,eax; mov ecx,[eax]; mov edx,ecx; shr edx,16; and edx,255;
      cmp edx,{ACCEPTED}; jb invalid; cmp edx,{PENDING_REWARD}; ja invalid;
      and ecx,255; cmp ecx,{EVENT_COUNT}; jae invalid;
      bts dword ptr [{DONE:#x}],ecx;
      test esi,esi; jz clear_card;
      mov edx,ecx; cmp edx,36; jb timer; sub edx,16;
      cmp ecx,37; jne timer; inc edx;
    timer:
      mov word ptr [{COOLDOWNS:#x}+edx*2],si;
    clear_card:
      xor eax,eax; mov ecx,{CARD_WORDS}; rep stosd; mov eax,1; jmp done;
    invalid:
      xor eax,eax;
    done:
      pop edi; pop esi; ret 8
    ''')
    reserve_battle = code(f'''
      test dword ptr [{BATTLES:#x}],1; jnz invalid;
      push dword ptr [esp+4]; call {getslot:#x}; test eax,eax; jz invalid;
      mov eax,[eax]; test eax,0x80000000; jz invalid;
      shr eax,16; and eax,255; cmp eax,{ACCEPTED}; jb invalid;
      cmp eax,{PENDING_REWARD}; ja invalid;
      or dword ptr [{BATTLES:#x}],1; mov eax,1; ret 4;
    invalid:
      xor eax,eax; ret 4
    ''')
    rng = code(f'''
      cmp dword ptr [{BASE:#x}],{MAGIC:#x}; jne invalid;
      mov eax,[{RNG:#x}]; imul eax,eax,1664525; add eax,1013904223;
      mov [{RNG:#x}],eax; ret;
    invalid:
      xor eax,eax; ret
    ''')
    schedule = code(f'''
      cmp dword ptr [{BASE:#x}],{MAGIC:#x}; jne invalid;
      mov eax,[esp+4]; mov [{NEXT_OFFER:#x}],eax; mov eax,1; ret 4;
    invalid:
      xor eax,eax; ret 4
    ''')
    result = {name:hex(value) for name,value in locals().copy().items()
              if name in ('init','tick','getslot','getfield','setfield','clear','completed',
                          'count_completed','can_offer','finish','reserve_battle','rng','schedule')}
    result.update(base=hex(BASE),words=WORDS,magic=MAGIC,rng_address=hex(RNG),
                  next_offer_address=hex(NEXT_OFFER),last_day_address=hex(LAST_DAY),
                  month_address=hex(MONTH),battles_address=hex(BATTLES),
                  done_address=hex(DONE),cooldowns_address=hex(COOLDOWNS),
                  cards_address=hex(CARDS),card_words=CARD_WORDS,event_count=EVENT_COUNT,
                  card_count=CARD_COUNT,battle_flag=BATTLE,cooldown_index=list(COOLDOWN_INDEX),
                  tour_control_global=82,tour_layout="low2 battle slot; bit29 enabled; bits2..8 home; bits9..12 legion; bits13..28 rest days",
                  card_fields=['control','origin','destination','army_home','legion',
                               'accepted_day','deadline_day','progress'],
                  control_bytes=['event_id','stage','status','flags'])
    return {'world_event_state':result}
