"""On-site stories with three possible payouts, settled by the shared contract journal."""
from world_event_catalog import choice, stage


def encounter(ident, key, title, category, kind, introduction, *results):
    return dict(
        id=ident, key=key, title=title, category=category, kind=kind, repeat_days=90,
        required_class=0, required_facility=0, country=0, min_completed=0,
        requires_event=[], conditions=[], early=True,
        goal=dict(type="encounter", target_role="any", building_id=0, target_fixed=0),
        stages=[stage(title, introduction, *results)],
    )


ENCOUNTERS = [
    encounter(38, "H1", "폭우 속의 마지막 교신", 3, "chain",
              "비상 전파가 잡혔다. 폭우 속에서 화물열차가 들어갈 역을 찾아 달라고 한다. 수신 단서를 맞춰 직접 회신하거나 현지 기사에게 맡길 수 있다.",
              choice("첫 교신 성공 · 금 36,000", "역장이 답신을 받자마자 신호기를 돌렸다. 열차가 무사히 진입해 급행 수당 금 36,000을 받았다.", reward_gold=36000),
              choice("재교신 성공 · 금 24,000", "재송신 끝에 기관사가 회신했다. 승강장에서 기다리던 가족들이 무사 도착 소식과 함께 금 24,000을 보내왔다.", reward_gold=24000),
              choice("현지 중계 · 금 12,000", "현지 기사가 마지막 구간을 중계했다. 군단은 길을 열어 준 중계료 금 12,000을 받았다.", reward_gold=12000)),
    encounter(39, "H2", "물 차오르는 인양 갱도", 3, "collection",
              "폐광에서 구리 상자를 끌어올렸다. 지금 회수하면 금 24,000이다. 안쪽 유물까지 노릴지는 지반을 살핀 뒤 결정할 수 있다.",
              choice("구리 상자 · 금 24,000", "구리 상자를 실은 마지막 수레가 물이 차기 전에 빠져나왔다. 감정가 금 24,000을 받았다.", reward_gold=24000),
              choice("유물 인양 · 금 72,000·철 30", "배수로 너머에서 봉인된 계측기를 건져 냈다. 박물관의 감정료 금 72,000과 폐궤도 철 30을 받았다.", reward_gold=72000, reward_iron=30),
              choice("긴급 철수 · 금 6,000", "진흙이 밀려들자 모두 밧줄을 타고 올라왔다. 입구로 쓸려 온 동전 꾸러미를 팔아 금 6,000을 받았다.", reward_gold=6000)),
    encounter(40, "H3", "강변 악단의 앙코르", 0, "festival",
              "강물이 불어 악단의 귀향선이 늦어졌다. 기다리는 사람들에게 들려줄 두 곡을 골라 달란다. 곡마다 다른 후원회가 사례를 맡는다.",
              choice("여행자의 왈츠와 대장간 행진곡 · 금 18,000·철 35", "여관 손님들이 춤을 추자 대장장이들도 망치를 두드려 박자를 맞췄다. 여관 조합에서 금 18,000, 대장간에서 철 35를 보냈다.", reward_gold=18000, reward_iron=35),
              choice("여행자의 왈츠와 뱃노래 · 금 18,000·석유 25", "여행자와 뱃사람들이 한 소절씩 주고받았다. 여관 조합이 금 18,000을 모았고 나루에서 석유 25를 실어 주었다.", reward_gold=18000, reward_oil=25),
              choice("대장간 행진곡과 뱃노래 · 철 35·석유 25", "망치 소리와 노 젓는 박자가 강변에 울렸다. 대장간에서 철 35, 나루에서 석유 25를 보내왔다.", reward_iron=35, reward_oil=25)),
]
