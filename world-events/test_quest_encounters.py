"""Exercise all three on-site quests in the compiled event engine."""
import gc
from itertools import permutations
from test_world_event_simple import (CARD, CASH, PARENT, STATE, fresh, invoke,
                                     money, r, slot, status, w)
from quest_encounters import ENCOUNTERS

SIMPLE_FORM=1<<28


def offer(u,ident,seed=None):
    u.mem_write(CARD,bytes(96))
    w(u,CARD,ident|(1<<16))
    w(u,CARD+4,2)
    w(u,CARD+28,SIMPLE_FORM|(0 if seed is None else 1+seed))
    u.data['answers'].clear()
    u.data['default_answer']=-1


def play(u,*answers):
    u.data['answers']=list(answers)
    invoke(u,'we_test_accept',PARENT,0,0)
    assert not u.data['answers'],u.data['selections'][-2:]


def payout(u,ident,index,*answers):
    before=money(u)
    play(u,*answers)
    assert not status(u),(ident,slot(u),u.data['selections'][-3:])
    assert invoke(u,int(STATE['completed'],16),ident)
    actions=ENCOUNTERS[ident-38]['stages'][0]['choices'][index]['actions']
    expected=tuple(old+actions.get('reward_'+key,0) for old,key in zip(before,('gold','iron','oil')))
    assert money(u)==expected,(ident,index,expected,money(u))
    assert not invoke(u,'we_test_claim',PARENT,0) and money(u)==expected


def run():
    u=fresh()
    for variant in range(6):
        target=variant%3
        offer(u,38,variant)
        payout(u,38,0,target)
        offer(u,38,variant)
        payout(u,38,1,(target+1)%3,target)
        offer(u,38,variant)
        payout(u,38,2,(target+1)%3,(target+2)%3)
    offer(u,38,4)
    payout(u,38,2,3)

    # A deferred re-transmission saved to the eight-DWORD card keeps the clue,
    # the reduced fee, and its exact RNG state when reopened.
    offer(u,38)
    before=money(u)
    play(u,4)
    assert status(u)==1 and money(u)==before and (slot(u)[7]&65535)
    seed=(slot(u)[7]&65535)-1
    target=seed%3
    rng=r(u,int(STATE['rng_address'],16))
    play(u,(target+1)%3,-1)
    assert (slot(u)[7]>>16)&3==1 and money(u)==before
    saved=bytes(u.mem_read(CARD,32))
    restored=fresh()
    restored.mem_write(CARD,saved)
    w(restored,int(STATE['rng_address'],16),rng)
    payout(restored,38,1,target)
    assert r(restored,int(STATE['rng_address'],16))==rng
    del restored
    gc.collect()

    # seed/2 mod 100 is the roll, independently of the ground report in bit 0.
    for stable,threshold in ((True,70),(False,35)):
        for roll in (0,threshold-1,threshold,99):
            offer(u,39,2*roll+int(not stable))
            payout(u,39,1 if roll<threshold else 2,1,0)
            assert any(str(threshold)+'%' in txt for _,txt in u.data['texts'][-8:])
    offer(u,39,18)
    payout(u,39,0,0)
    offer(u,39,19)
    before=money(u)
    play(u,1,2)
    assert status(u)==1 and ((slot(u)[7]>>16)&3)==1 and money(u)==before
    saved=bytes(u.mem_read(CARD,32))
    restored=fresh()
    restored.mem_write(CARD,saved)
    payout(restored,39,0,1)
    del restored
    gc.collect()

    for first,second in permutations(range(3),2):
        offer(u,40)
        rng=r(u,int(STATE['rng_address'],16))
        remaining=[i for i in range(3) if i!=first]
        payout(u,40,first+second-1,first,remaining.index(second))
        assert r(u,int(STATE['rng_address'],16))==rng
    offer(u,40)
    before=money(u)
    play(u,0,-1)
    assert ((slot(u)[7]>>16)&3)==1 and money(u)==before
    saved=bytes(u.mem_read(CARD,32))
    restored=fresh()
    restored.mem_write(CARD,saved)
    payout(restored,40,2,2,1,1)  # redo first song, choose smiths + sailors
    del restored
    gc.collect()

    # Gold paid, iron blocked. The stock reward flags survive save/restore.
    offer(u,39,2)
    before=money(u)
    w(u,CASH[1],2000000000)
    play(u,1,0)
    assert status(u)==3 and money(u)==(before[0]+72000,2000000000,before[2])
    saved=bytes(u.mem_read(CARD,32))
    restored=fresh()
    restored.mem_write(CARD,saved)
    for address,value in zip(CASH,money(u)):w(restored,address,value)
    w(restored,CASH[1],50)
    assert invoke(restored,'we_test_claim',PARENT,0)
    assert money(restored)==(before[0]+72000,80,before[2])
    assert not invoke(restored,'we_test_claim',PARENT,0)
    assert not status(restored)
    print('PASS radio clues, retries, survey odds, two-song sponsors, save resume and exactly-once settlement')


if __name__=='__main__':
    run()
