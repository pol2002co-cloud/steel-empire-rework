"""Own mission/recipe text for the separate expedition and ruin ledger."""
from ruin_visits import RUINS

MISSIONS=(
    dict(name='엑제로스 군사 교류',text='30일간 군사 교류에 참가합니다. 레벨과 기량이 높을수록 성공률과 추가 지급금이 오릅니다.',days=30,cost=10000,gold=45000,xp=400,job=0),
    dict(name='엑제로스 기술 협력',text='30일간 현지 장비 운용을 돕습니다. 기술자가 있으면 성공률이 오르며 없어도 출발할 수 있습니다.',days=30,cost=20000,gold=80000,xp=200,job=11),
    dict(name='동방대륙 무역 호위',text='30일간 동방 상단을 호위합니다. 드라이버가 있으면 성공률이 오르며 없어도 출발할 수 있습니다.',days=30,cost=30000,gold=120000,xp=180,job=10),
    dict(name='동방대륙 현지 조사',text='30일간 현지 자료를 조사합니다. 과학자가 있으면 성공률이 오르며 없어도 출발할 수 있습니다.',days=30,cost=15000,gold=60000,xp=400,job=8),
    dict(name='유적 입구 조사',text='7일간 유적 입구를 조사합니다. 건축가가 있으면 성공률이 오르며 없어도 출발할 수 있습니다.',days=7,cost=5000,gold=15000,xp=150,job=12),
    dict(name='폐갱도 탐사',text='15일간 유적의 폐갱도를 탐사합니다. 기술자가 있으면 성공률이 오르며 없어도 출발할 수 있습니다.',days=15,cost=10000,gold=30000,xp=250,job=11),
    dict(name='심층 유적 탐험',text='30일간 유적 심층을 탐험합니다. 과학자가 있으면 성공률이 오릅니다. 성공을 쌓으면 미발견 설계도를 확정 획득합니다.',days=30,cost=20000,gold=60000,xp=450,job=8),
)

RECIPES=(
    dict(name='고블린MK2 제작 설계도',machine=6,gold=20000,iron=20,oil=10,days=7,factory=7),
    dict(name='드래곤MK2 제작 설계도',machine=1,gold=240000,iron=30,oil=40,days=10,factory=10),
    dict(name='A.S.6 제작 설계도',machine=24,gold=400000,iron=80,oil=60,days=15,factory=10),
)

# Recipe IDs and production order numbers 1..3 stay compatible with old saves.
LEGEND_RECIPES=(
    dict(name='철왕',condition='서로 다른 유적 방문',unit='곳',required=2,gold=700000,iron=200,oil=80,days=18,factory=9),
    dict(name='뇌격전차',condition='유적 연간 혜택 수령',unit='곳',required=1,gold=900000,iron=240,oil=120,days=24,factory=9),
    dict(name='천둥매',condition='파견 귀환 정산',unit='회',required=3,gold=650000,iron=120,oil=160,days=18,factory=12),
    dict(name='밤까마귀',condition='서로 다른 유적의 심층 봉인실 보존 또는 회수',unit='곳',required=2,gold=1000000,iron=180,oil=220,days=24,factory=12),
)

INITIAL_SLOTS=4
MAX_HEROES=3
MAX_GENERICS=20
SUCCESS_CAP=95
BONUS_GOLD_CAP=50
DEEP_GUARANTEE=3
BLESS_GOLD=20000
BLESS_IRON=20
BLESS_OIL=10
BLESS_XP=120
PRESERVE_BONUS=50
COMPASS_SUCCESS=5
SEAL_BONUS_GOLD=10
ARTIFACTS=(
    ('고대 나침반','유물장부에 보관하면 모든 유적 탐험 성공률이 5%포인트 오릅니다. 장착은 필요 없습니다.'),
    ('상단 인장','유물장부에 보관하면 대장 추가 지급률이 10%포인트 오릅니다. 대장·유물 보정은 최대 50%이며 대성공 지급금은 별도입니다.'),
)


def generate_catalog_header(c_string):
    """ASCII C initializers for the parent's EXMission/EXRecipe/EXRuin types."""
    lines=['#ifndef EXPEDITION_CATALOG_H','#define EXPEDITION_CATALOG_H']
    constants=dict(EX_MISSION_COUNT=len(MISSIONS),EX_RECIPE_COUNT=len(RECIPES)+len(LEGEND_RECIPES),EX_STANDARD_RECIPES=len(RECIPES),EX_RUIN_COUNT=len(RUINS),
                   EX_INITIAL_SLOTS=INITIAL_SLOTS,EX_MAX_HEROES=MAX_HEROES,EX_MAX_GENERICS=MAX_GENERICS,
                   EX_SUCCESS_CAP=SUCCESS_CAP,EX_BONUS_GOLD_CAP=BONUS_GOLD_CAP,EX_DEEP_GUARANTEE=DEEP_GUARANTEE,
                   EX_BLESS_GOLD=BLESS_GOLD,EX_BLESS_IRON=BLESS_IRON,EX_BLESS_OIL=BLESS_OIL,EX_BLESS_XP=BLESS_XP,
                   EX_PRESERVE_BONUS=PRESERVE_BONUS,EX_COMPASS_SUCCESS=COMPASS_SUCCESS,EX_SEAL_BONUS_GOLD=SEAL_BONUS_GOLD)
    lines.extend('#define %s %du'%(name,value) for name,value in constants.items())
    lines.append('static const EXMission EX_MISSIONS[EX_MISSION_COUNT]={')
    for mission in MISSIONS:
        fields=[c_string(mission['name']),c_string(mission['text'])]+[str(mission[k])+'u' for k in ('days','cost','gold','xp','job')]
        lines.append('{'+','.join(fields)+'},')
    lines.append('};\nstatic const EXRecipe EX_RECIPES[EX_RECIPE_COUNT]={')
    for recipe in RECIPES:
        lines.append('{'+','.join([c_string(recipe['name'])]+[str(recipe[k])+'u' for k in ('machine','gold','iron','oil','days','factory')])+'},')
    from legend_machines import MODELS
    assert [r['name'] for r in LEGEND_RECIPES]==[m['name'] for m in MODELS]
    for r in LEGEND_RECIPES:
        fields=[c_string(r['name']), '0u']+[str(r[k])+'u' for k in ('gold','iron','oil','days','factory')]
        lines.append('{'+','.join(fields)+'},')
    lines.append('};\nstatic const EXLegend EX_LEGENDS[]={')
    for r,m in zip(LEGEND_RECIPES,MODELS):
        stats='HP %d · 방어 %d · 사거리 %d · 공격 대인 %d / 대공 %d / 대기갑 %d / 대벽 %d'%(
            m['hp'],m['defense'],m['reach'],*m['attack'])
        lines.append('{'+','.join((c_string(r['condition']),c_string(r['unit']),c_string(stats),str(r['required'])+'u'))+'},')
    lines.append('};\nstatic const EXRuin EX_RUINS[EX_RUIN_COUNT]={')
    lines.extend('{%s,%du},'%(c_string(name),town) for name,town in RUINS)
    lines.append('};')
    for index,(name,text) in enumerate(ARTIFACTS):
        lines.append('#define EX_ARTIFACT_%d_NAME %s'%(index,c_string(name)))
        lines.append('#define EX_ARTIFACT_%d_TEXT %s'%(index,c_string(text)))
    lines.append('#endif\n')
    return '\n'.join(lines)
