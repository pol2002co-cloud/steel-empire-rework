"""Execute calendar notices and seasonal contract accounting in the compiled engine."""
from test_world_event_simple import (fresh, simple_card, invoke, r, w, slot, status, money,
    station, army, BASE, PARENT, CASH, HOURS, G, STATE, attach_queue, pump, fulfill, route)

def at(u,month,year=0):
    w(u,HOURS,(year*12+month-1)*720+24)

def run():
    # News is automatic and save-persistent; all three reward families recur.
    u=fresh();at(u,1);attach_queue(u)
    for year in (0,1):
        for month in range(1,13):
            at(u,month,year)
            # This fixture has no expedition due and new offers disabled.
            u.data['texts'].clear()
            shown=pump(u)
            assert shown==(month%2==1),(month,shown)
            if shown:
                assert str(month)+'월' in u.data['texts'][0][0]
                assert not pump(u)
                saved=bytes(u.mem_read(BASE,216))
                v=fresh();at(v,month,year);v.mem_write(BASE,saved);attach_queue(v)
                assert not pump(v),'An acknowledged month repeats on load'
    u=fresh();at(u,6);route(u,[1,3,2,4,4])
    assert any(title=='연간 행사표' for title,_ in u.data['texts'])

    for month in range(1,13):
        for ident,base,kind in [(0,24000,'freight'),(36,35000,'freight'),(24,120000,'occupy'),(2,35000,'other')]:
            u=fresh();at(u,month);event=simple_card(u,ident)
            before=money(u);invoke(u,'we_test_accept',PARENT,0,0)
            if status(u)==2:fulfill(u,event)
            if status(u)==3:invoke(u,'we_test_claim',PARENT,0)
            assert not status(u)
            doubled=(kind=='freight' and month in (5,11)) or (kind=='occupy' and month in (1,7))
            assert r(u,CASH[0])-before[0]==base*(1+int(doubled))-(30000 if ident==2 else 0),(month,ident)
            if ident==0:assert r(u,CASH[1])==before[1]-40
            if ident==36:assert len(u.data['consumed_machine'])==1
            after=money(u);invoke(u,'we_test_claim',PARENT,0);assert after==money(u)
    # Lock the rate when the machine is actually handed over, even at the cap.
    for month,factor in ((4,1),(5,2)):
        u=fresh();at(u,month);simple_card(u,36);w(u,CASH[0],1999999999)
        invoke(u,'we_test_accept',PARENT,0,0)
        assert status(u)==3 and len(u.data['consumed_machine'])==1
        at(u,month+1);w(u,CASH[0],0)
        assert invoke(u,'we_test_claim',PARENT,0)==1
        assert r(u,CASH[0])==35000*factor and len(u.data['consumed_machine'])==1
    # A blocked equipment reward may retry in another month after receiving gold.
    u=fresh();at(u,11);simple_card(u,31);u.data['full'].add('give_machine')
    invoke(u,'we_test_accept',PARENT,0,0);station(u,army(1),slot(u)[2]);invoke(u,'we_test_progress')
    before=r(u,CASH[0]);invoke(u,'we_test_claim',PARENT,0)
    assert status(u)==3 and r(u,CASH[0])==before+100000
    u.data['full'].clear();at(u,12);invoke(u,'we_test_claim',PARENT,0)
    assert not status(u) and r(u,CASH[0])==before+100000 and len(u.data['grants'])==1
    print('PASS: 24 calendar months, persisted notices, 48 month/contract pairs, capped and partial settlements')

if __name__=='__main__':
    run()
