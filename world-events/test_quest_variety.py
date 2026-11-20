"""Compiled offer rotation, illustration routing and manual reward retry."""
from test_quest_usability import (
    fresh, simple_card, inspect, invoke, money, r, w, status, slot, station,
    PARENT, CASH, CARD, STATE, HOURS, G, army, ap, tp,
)
from world_events_patch import EVENT_CATALOG

def propose(u,ident):
    count=len(EVENT_CATALOG)
    seed=next(s for s in range(10000) if ((s*1664525+1013904223)&0xffffffff)%count==ident)
    w(u,int(STATE['rng_address'],16),seed)
    w(u,int(STATE['next_offer_address'],16),0)
    invoke(u,'we_tick',PARENT)

def run():
    u=fresh()
    propose(u,0)
    assert slot(u)[0]&255==0
    propose(u,9)
    assert EVENT_CATALOG[slot(u,1)[0]&255]['goal']['type']!='supply'
    propose(u,0)
    assert len({EVENT_CATALOG[slot(u,i)[0]&255]['goal']['type'] for i in range(3)})==3

    sources=set()
    for ident in (1,2,3,4,5,7,8,9,10):
        u=fresh();w(u,tp(2)+0x10,1);w(u,ap(3)+0x14,1);w(u,tp(4)+0x10,2)
        propose(u,ident);city=slot(u)[1]
        assert city not in (2,3,4) and r(u,tp(city)+8)!=6
        sources.add(city)
    assert len(sources)>2

    for ident,scene in ((38,4),(39,3),(40,5)):
        u=fresh();propose(u,ident)
        assert slot(u)[0]&255==ident
        saved=slot(u)[7]
        if ident!=40:assert 1<=saved&65535<=60000
        before=money(u);u.data['answers']=[1]
        assert invoke(u,'we_present',PARENT)==1
        assert u.data['art_scenes']==[scene] and slot(u)[7]==saved and money(u)==before
        assert not invoke(u,'we_present',PARENT)
        inspect(u,(1,0,1,4))
        assert u.data['art_scenes'][-1]==scene and slot(u)[7]==saved and money(u)==before

    u=fresh();simple_card(u,31);invoke(u,'we_test_accept',PARENT,0,0)
    station(u,army(1),slot(u)[2]);invoke(u,'we_test_progress');assert status(u)==3
    before=money(u);u.data['full'].add('give_machine')
    inspect(u,(1,0,4))
    assert status(u)==3 and slot(u)[6]==r(u,HOURS)//24+1
    assert r(u,CASH[0])==before[0]+50000
    u.data['full'].clear()
    assert not invoke(u,'we_present',PARENT)
    w(u,HOURS,r(u,HOURS)+24);assert invoke(u,'we_present',PARENT)==1
    assert status(u)==0 and r(u,CASH[0])==before[0]+50000
    assert [a[1] for k,a in u.data['grants'] if k=='give_machine']==[24]
    assert u.data['art_scenes'][-1]==1

if __name__=='__main__':
    run()
    print('PASS offer origins, mixed objectives, illustrated notifications, persisted seeds and exact-once F8 payout retry')
