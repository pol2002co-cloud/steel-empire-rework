"""Own postwar stories; numeric effects are interpreted by the common engine.

No addresses or original game bytes live here. Ordinary costs are checked at
acceptance; stock equipment is consumed only after arrival. Rewards wait for
every visit/battle objective. ``require_job`` borrows a living
ordinary specialist, never removes them. The common menu supplies defer/refuse.
"""

CATEGORIES = ("도시 생활·내정", "이동·배송", "용병단·군단 생활", "탐험·발견", "선택형 전투", "연속 후일담", "장비납품")
EARLY_EVENT_IDS = frozenset((*range(7), 8, 9, 10, 13, 14, 15, 17, 18, 19, 20, 21, 23, 34, 36, 37))
BATTLE_PROFILES = ("infantry", "armor", "air", "artillery", "elite_armor")
TARGET_ROLES = ("near", "far", "airport", "home", "capital", "border", "lab", "factory", "hq", "different_country", "black_power_hq")
STORY_CONDITIONS = ("rival_victory", "black_power_restored", "final_victory", "caranto_player_garrison", "living_companion", "regional_once", "regional_rumor", "three_delivery_regions")


def choice(label, result, next_stage=-1, **actions):
    return dict(label=label, result=result, next_stage=next_stage, actions=actions)


def stage(title, text, *choices, min_completed=0):
    return dict(title=title, text=text, choices=list(choices), min_completed=min_completed)


def event(key, title, kind, stages, repeat_days=60, required_class=0,
          required_facility=0, country=0, min_completed=0, requires_event=(), conditions=()):
    category = ord(key[0]) - ord("A")
    return dict(id=category*6+int(key[1])-1, key=key, title=title, category=category,
                kind=kind, repeat_days=repeat_days, required_class=required_class,
                required_facility=required_facility, country=country,
                min_completed=min_completed, requires_event=list(requires_event),
                conditions=list(conditions), stages=stages, early=category*6+int(key[1])-1 in EARLY_EVENT_IDS)


EVENT_CATALOG = [
    event("A1", "장터의 교환 제안", "trade", [
        stage("철인가, 석유인가", "상인은 겨울 재고를 채울 철 40 또는 석유 25를 찾는다. 이번 계약 한 번의 거래이며, 같은 제안은 60일 동안 다시 받지 않는다.",
              choice("철 40을 납품한다 · 금 24,000", "철을 잰 상인은 운송장에 도장을 찍고 금 24,000을 건넸다.", cost_iron=40, reward_gold=24000),
              choice("석유 25를 납품한다 · 금 26,000", "밀봉을 확인한 상인은 석유 25의 대금으로 금 26,000을 지급했다.", cost_oil=25, reward_gold=26000))]),
    event("A2", "대장간의 주문서", "trade", [
        stage("민병대의 예비 권총", "민병대가 5mm 권총 한 정을 주문했다. 가방의 예비 물품만 납품한다. 장착 중인 무기나 다른 물품을 자동으로 해제하지 않는다.",
              choice("예비 5mm 권총 1정 납품 · 금 2,600", "새 권총은 야간 순찰조에 배정되었다. 기준 대금 600과 소액 인계 수당 2,000을 받았다.", cost_item_id=1, cost_item_count=1, reward_gold=2600))], required_facility=13),
    event("A3", "작은 도시 축제", "festival", [
        stage("빈 무대를 채우는 방법", "전쟁이 끝난 뒤 처음 열리는 축제다. 후원은 기부이며 투자 수익은 없다. 댄서 공연은 이번 사건의 짧은 참여로, 술집 공연 정산을 다시 실행하지 않는다.",
              choice("축제에 금 30,000 후원", "시장 한쪽에 따뜻한 음식이 놓였다. 주민들은 군단 이름을 후원자 명부에 적었다.", cost_gold=30000),
              choice("일반 댄서와 축제에 참여", "댄서가 아이들과 손뼉을 맞췄다. 무대가 끝나자 주민들이 여행용 식량 대신 금 20,000을 모아 주었다.", require_job=13, reward_gold=20000),
              choice("관객으로 축제를 즐긴다", "그날만큼은 승전 소식 대신 악기 소리가 광장을 채웠다. 군단은 축제의 방문객으로 기록되었다."))]),
    event("A4", "무너진 창고 지붕", "trade", [
        stage("젖기 전의 마지막 상자", "창고지기는 비가 들기 전에 지붕을 덮어 달라고 한다. 건축가는 차출로 사라지지 않는다. 거절해도 실제 창고가 파괴되거나 재고가 줄지 않는다.",
              choice("건축가와 철 20으로 보수 · 금 50,000", "건축가가 배수 방향을 바꿨다. 비가 그친 뒤 창고지기는 보수 대금 금 50,000을 지급했다.", require_job=12, cost_iron=20, reward_gold=50000),
              choice("현지 인부 고용 · 금 40,000 / 석유 30", "인부들이 천막을 세우는 동안 군단은 창고를 지켰다. 남은 정비용 석유 30을 답례로 받았다.", cost_gold=40000, reward_oil=30))], required_facility=6),
    event("A5", "연구소의 자료 정리", "trade", [
        stage("뒤섞인 상자 표찰", "연구원은 '푸른 표찰은 관측, 붉은 표찰은 동력'이라고 설명한다. 분류를 틀려도 다시 시도할 수 있다. 새 기술이나 사건 설계도를 해금하지 않는다.",
              choice("일반 과학자에게 정리를 맡긴다", "과학자는 중복된 도면을 따로 묶었다. 연구소가 정리 수당 금 35,000과 철 20을 지급했다.", require_job=8, reward_gold=35000, reward_iron=20),
              choice("푸른 표찰을 관측 기록에 넣는다", "관측 기록의 순서가 맞아들었다. 연구원은 확인 수당 금 20,000과 석유 15를 건넸다.", reward_gold=20000, reward_oil=15),
              choice("붉은 표찰을 관측 기록에 넣는다", "동력 계산서였다. 연구원은 처음의 색상 설명을 다시 읽어 주었다. 비용이나 보상 없이 다시 분류한다.", next_stage=0))], required_facility=17),
    event("A6", "공장의 남은 부품", "trade", [
        stage("규격 밖 볼트의 쓰임새", "공장은 호환되지 않는 재고를 분류하려 한다. 생산 중인 장비를 취소하거나 보유 차량을 분해하지 않는다. 기술자는 작업 후 원래 부대로 돌아간다.",
              choice("기술자와 철 10 투입 · 석유 40", "규격별로 나눈 볼트 덕분에 예비 펌프를 조립했다. 공장은 남은 석유 40을 인계했다.", require_job=11, cost_iron=10, reward_oil=40),
              choice("현지 정비 요청 · 금 30,000 / 철 35·석유 20", "정비공이 쓸 수 있는 부품만 골라 포장했다. 철 35와 석유 20을 돌려받았다.", cost_gold=30000, reward_iron=35, reward_oil=20))], required_facility=7),

    event("B1", "끊긴 전령선", "delivery", [
        stage("문서 가방의 봉인", "통신선 수리가 늦어져 봉인 문서를 직접 보내야 한다. 실제 이동 후 목적지에서 확인한다. 민간군단도 맡을 수 있으며 일반 의뢰 보상과 중복 처리하지 않는다.",
              choice("가까운 도시에 문서 전달 · 금 60,000", "봉인이 온전한 것을 확인한 관리가 수령증에 서명했다. 전령선이 다시 이어졌다.", delivery_legs=1, target_roles=["near"], reward_gold=60000),
              choice("먼 연락소까지 전달 · 금 90,000", "먼 연락소는 오래 기다리던 발신 날짜를 확인했다. 긴 여정의 수당 금 90,000을 받았다.", delivery_legs=1, target_roles=["far"], reward_gold=90000))]),
    event("B2", "상단의 경비 계약", "delivery", [
        stage("마지막 길목의 약탈자", "상단은 도착지의 약탈자 분견대를 경계한다. 경비 계약은 도착 후 기존 손실 규칙이 적용되는 전투 1회를 포함한다. 전투를 원치 않으면 문서만 운송할 수 있다.",
              choice("경비 계약 · 도착 후 보병전 / 금 160,000", "길목의 약탈자를 격파하자 상단이 안전 확인서를 보냈다. 계약금이 정산되었다.", delivery_legs=1, target_roles=["near"], battle_profile="infantry", reward_gold=160000),
              choice("안전한 문서 배송 · 금 70,000", "군단은 교전 구역을 피한 연락로로 문서를 전달했다. 상단은 문서 배송분만 정산했다.", delivery_legs=1, target_roles=["near"], reward_gold=70000))], repeat_days=90),
    event("B3", "기상관측 기록 회수", "delivery", [
        stage("바람을 적어 둔 수첩", "서로 다른 관측소에 흩어진 수첩을 모은다. 날씨나 사고 확률을 바꾸는 사건은 아니다. 선택한 전문가가 포함된 군단으로 실제 관측소를 방문한다.",
              choice("과학자와 가까운 관측소 2곳 · 금 85,000", "과학자는 두 수첩의 시간 오차를 맞췄다. 항로 담당자가 관측 정리비를 지급했다.", require_job=8, delivery_legs=2, target_roles=["near", "lab"], reward_gold=85000),
              choice("파일럿과 먼 항로 2곳 · 금 120,000·석유 35", "파일럿은 누락된 풍향 기록을 보완했다. 다음 운항을 위한 석유 35도 지급되었다.", require_job=9, require_army_type=2, delivery_legs=2, target_roles=["airport", "far"], reward_gold=120000, reward_oil=35))]),
    event("B4", "급한 항공 부품", "delivery", [
        stage("다음 비행 전까지", "공항의 정비반이 철 25와 석유 20을 기다린다. 항공군단의 실제 출발·도착이 필요하다. 부품 대신 정비 문서만 운송하는 계약도 가능하다.",
              choice("부품 운송 · 철 25·석유 20 / 금 130,000", "정비반은 도착한 자재로 예비 계통을 교체했다. 다음 편의 출발 기록과 대금을 받았다.", require_army_type=2, cost_iron=25, cost_oil=20, delivery_legs=1, target_roles=["airport"], reward_gold=130000),
              choice("정비 문서 운송 · 금 80,000", "정비 순서를 적은 문서가 먼저 도착했다. 부품 납품과 별도의 문서 운송료만 지급되었다.", require_army_type=2, delivery_legs=1, target_roles=["airport"], reward_gold=80000))], required_class=9, required_facility=20),
    event("B5", "민간 보급선 재개", "delivery", [
        stage("첫 번째 생필품 운송", "전투 없는 생필품 보급선을 두 번 왕복한다. 각 구간은 실제 도시 이동으로 확인하며 첫 구간 보상은 한 번만 지급한다.",
              choice("민간군단으로 첫 운송 · 금 65,000", "상점에 등불과 비누가 다시 놓였다. 상단은 첫 구간의 운송료를 지급하고 다음 인계지를 알려 주었다.", next_stage=1, require_army_type=3, delivery_legs=1, target_roles=["near"], reward_gold=65000),
              choice("다른 군단으로 첫 운송 · 금 55,000", "보급품을 받은 상인이 빈 수레를 돌려보냈다. 두 번째 인계 준비가 끝났다.", next_stage=1, delivery_legs=1, target_roles=["near"], reward_gold=55000)),
        stage("두 번째 인계", "다음 도시까지 운송하면 보급선 복구가 끝난다. 앞서 받은 첫 구간 보상은 재개하거나 불러와도 다시 지급하지 않는다.",
              choice("마지막 운송 · 금 90,000·철 20", "두 번째 도시의 상인도 수령증에 서명했다. 상단은 추가 감사금과 예비 철 20을 건넸다.", delivery_legs=1, target_roles=["far"], reward_gold=90000, reward_iron=20))]),
    event("B6", "도난 화물의 행방", "delivery", [
        stage("팔리기 직전의 짐", "화물은 가까운 도시로 옮겨졌다. 현지에서 금 45,000으로 되사거나, 전투군단으로 약탈자를 격파한다. 사건 화물 기록만 사용하며 실제 상점 재고를 지우지 않는다.",
              choice("화물 매입 · 금 45,000 지불 / 보상 100,000", "주인의 낙인을 확인한 뒤 화물을 돌려주었다. 매입 비용이 포함된 반환 대금을 받았다.", cost_gold=45000, delivery_legs=1, target_roles=["near"], reward_gold=100000),
              choice("약탈자와 보병전 · 금 140,000", "화물을 지키던 약탈자를 제압했다. 상단은 분실 목록을 지우고 전투 경비를 지급했다.", delivery_legs=1, target_roles=["near"], battle_profile="infantry", reward_gold=140000))], repeat_days=90),

    event("C1", "모의전 초청장", "battle", [
        stage("실탄 훈련의 약속", "지역 용병단이 실탄 대결을 제안한다. 안전 모의전이 아니므로 사망·손실·철수는 원래 전투 규칙을 따른다. 참가할 전투군단을 확인한 뒤 선택한다.",
              choice("보병 분견대와 대결 · 금 90,000", "상대 분견대가 패배를 인정했다. 군단은 이번 대결의 승전 기록과 정산금을 받았다.", battle_profile="infantry", reward_gold=90000),
              choice("기갑 분견대와 대결 · 금 140,000", "기갑전의 사격 기록을 교환했다. 계약된 훈련 경비 금 140,000이 지급되었다.", battle_profile="armor", reward_gold=140000))], repeat_days=90),
    event("C2", "입대를 원하는 청년들", "hire", [
        stage("지원서 두 묶음", "청년들은 무상 입대가 아니라 정식 계약을 원한다. 인원 여유와 해당 도시의 병과 해금 여부를 확인하고 고용한다. 지원병 레벨은 포룸 훈련대장 레벨에 비례하며 최대 28이다.",
              choice("동원병 3명 고용 · 금 24,000", "세 청년이 계약서에 서명했다. 기존 대기 인원 목록에서 배치할 수 있다.", cost_gold=24000, hire_class=1, hire_count=3),
              choice("기술자 1명 고용 · 금 35,000", "공구 가방을 든 지원자가 정식 계약을 마쳤다. 기술자는 대기 명단에 합류했다.", cost_gold=35000, hire_class=11, hire_count=1))], required_facility=5),
    event("C3", "주둔지의 작은 연회", "festival", [
        stage("식탁 위의 작은 깃발", "주둔 병사들이 신임 군단장을 위한 식탁을 마련했다. 이번 연회는 기념 기록이며 급여·월드맵 사기·영구 능력치 보너스를 바꾸지 않는다.",
              choice("금 15,000으로 연회 후원", "취사병은 평소보다 두꺼운 빵을 잘랐다. 병사들은 군단장의 첫 건배를 오래 기억했다.", cost_gold=15000),
              choice("일반 댄서가 함께한다", "댄서가 창고 앞을 작은 무대로 삼았다. 병사들의 박수 속에 주둔지의 밤이 지나갔다.", require_job=13),
              choice("간소한 차 모임으로 한다", "군단장은 병사들과 차를 나눴다. 화려한 연회는 아니었지만 모두 한 자리에 앉았다."))]),
    event("C4", "기갑 시범 기동", "visit", [
        stage("수송로의 새 노면", "지방 정부는 실제 차량 운행 기록을 원한다. 드라이버와 정상 차량이 있는 기계화군단으로 지정 도시까지 이동한다. 차량 처분이나 영구 고장은 없다.",
              choice("가까운 시험 구간 · 금 75,000·석유 20", "운행 시험관은 통과 시간을 적고 노면 검사를 마쳤다. 연료 보충분이 지급되었다.", require_army_type=1, require_job=10, delivery_legs=1, target_roles=["near"], reward_gold=75000, reward_oil=20),
              choice("먼 시험 구간 · 금 120,000·석유 45", "장거리 기록으로 보급 간격을 정했다. 시험관은 운행 수당과 석유 45를 지급했다.", require_army_type=1, require_job=10, delivery_legs=1, target_roles=["far"], reward_gold=120000, reward_oil=45))], required_class=10),
    event("C5", "항공 교류 훈련", "delivery", [
        stage("항로인가, 교전인가", "항공군단에 두 종류의 교류 계약이 왔다. 기록 배송은 비전투 임무다. 항공전은 기존 손실 규칙이 적용되는 전투 1회로, 특수 기체도 현재 장비 성능을 그대로 사용한다.",
              choice("비행 기록 배송 · 금 95,000·석유 30", "두 비행장의 경로 기록을 대조했다. 항로 담당자가 운송료와 연료를 지급했다.", require_army_type=2, delivery_legs=1, target_roles=["airport"], reward_gold=95000, reward_oil=30),
              choice("항공 초계대와 전투 · 금 180,000", "초계대와의 교전이 끝났다. 군단은 항공전 기록과 계약 보상을 받았다.", require_army_type=2, battle_profile="air", reward_gold=180000))], repeat_days=90, required_class=9),
    event("C6", "떠돌이 병사의 제보", "visit", [
        stage("폐역에 남은 표찰", "떠돌이 병사는 옛 수송로의 폐역 이야기를 들려준다. 한 번의 정보료는 한 번만 지불한다. 이 제보를 마치면 폐역의 금고 사건 조건을 충족한다.",
              choice("무료 소문을 따라 가까운 도시 방문", "폐역 창고를 기억하는 역무원과 만났다. 상자 표찰을 대조할 단서가 기록되었다.", delivery_legs=1, target_roles=["near"]),
              choice("정보료 금 10,000으로 장소를 확인", "병사는 장부의 날짜와 표찰 색을 자세히 설명했다. 같은 제보에 다시 요금을 받지 않는다.", cost_gold=10000))], repeat_days=60, conditions=["regional_rumor"]),

    event("D1", "오래된 전장의 잔해", "trade", [
        stage("다시 쓸 수 있는 금속", "녹슨 잔해를 현지 수거인들이 모아 두었다. 실제 지도 물체나 전투 장비를 지우지 않고 사건용 회수 물자만 정산한다.",
              choice("기술자가 분류 · 철 55·석유 20", "기술자는 재사용 가능한 금속과 밀봉된 연료통을 골라냈다. 철 55와 석유 20을 확보했다.", require_job=11, reward_iron=55, reward_oil=20),
              choice("수거인 고용 · 금 20,000 / 철 40·석유 15", "수거인들이 위험한 잔해를 치우고 회수품을 인계했다. 고용료를 제외한 물자가 정산되었다.", cost_gold=20000, reward_iron=40, reward_oil=15))], repeat_days=60, conditions=["regional_once"]),
    event("D2", "폐역의 금고", "trade", [
        stage("세 번째 승강장, 아홉 번째 달", "이 지역에서 들은 폐역 소문을 따라 금고를 찾았다. 장부 첫 줄에는 '봄의 세 번째 승강장, 종전의 아홉 번째 달'이라고 적혀 있다. 오답은 다시 시도할 수 있고 영구 실패는 없다.",
              choice("번호 3과 9를 맞춘다", "잠금쇠가 풀렸다. 금고 안의 보관료 금 60,000과 예비 권총 한 정을 인계받았다.", reward_gold=60000, reward_item_id=1, reward_item_count=1),
              choice("번호 9와 3을 맞춘다", "번호의 순서가 맞지 않았다. 장부는 여전히 금고 옆에 놓여 있다. 다시 시도한다.", next_stage=0),
              choice("자물쇠 수리 · 금 20,000 / 보상 60,000", "수리공이 번호 장치를 복구했다. 금고의 보관료 금 60,000과 예비 권총을 받았다.", cost_gold=20000, reward_gold=60000, reward_item_id=1, reward_item_count=1))], repeat_days=60, requires_event=[17], conditions=["regional_once"]),
    event("D3", "전쟁 기록 수집", "collection", [
        stage("여섯 나라의 목소리 · 전반", "서로 다른 나라의 접근 가능한 도시 여섯 곳에서 전쟁 기록을 모은다. 먼저 세 나라를 방문한다. 기록은 가방 물품이 아닌 사건 진행으로 보관하며 이미 방문한 나라는 다시 세지 않는다.",
              choice("서로 다른 세 나라 방문 · 금 60,000", "첫 세 묶음의 기록을 정리했다. 서로 다른 증언의 날짜가 맞아들기 시작했다.", next_stage=1, delivery_legs=3, target_roles=["different_country"]*3, reward_gold=60000)),
        stage("여섯 나라의 목소리 · 후반", "앞서 기록한 세 나라를 제외한 세 나라를 더 방문하고 연구 자료를 완성한다. 중간 보상은 이미 정산되었으므로 다시 지급하지 않는다.",
              choice("새로운 세 나라 방문 · 금 100,000·철 60", "여섯 나라의 기록이 하나의 색인으로 묶였다. 연구원은 군단의 이름을 자료 수집자로 남겼다.", delivery_legs=3, target_roles=["different_country"]*3, reward_gold=100000, reward_iron=60))], repeat_days=0, min_completed=3),
    event("D4", "동료에게 온 편지", "visit", [
        stage("고향에서 온 안부", "현재 살아 있고 실제 동료 명단에 있는 인물에게 안부 편지가 도착했다. 편지는 생존한 동료에게만 전달하며 사망한 인물을 되살리거나 새로 영입하지 않는다.",
              choice("금 10,000을 들여 답장을 보낸다", "'무사히 지내고 있다'는 답장이 전령 가방에 들어갔다. 고향에서 보내 온 감사금 금 30,000을 받았다.", cost_gold=10000, reward_gold=30000),
              choice("근처 도시의 전령소를 방문한다", "동료는 고향 소식을 직접 전해 듣고 짧은 답장을 남겼다. 전령소는 귀환길의 여비 금 45,000을 건넸다.", delivery_legs=1, target_roles=["near"], reward_gold=45000))], repeat_days=60, conditions=["living_companion"]),
    event("D5", "버려진 비행장의 정비 기록", "delivery", [
        stage("마지막 정비 일지", "항공 부품과 항공 교류 계약을 마친 군단에 옛 정비 일지의 위치가 전해졌다. 파일럿과 일반 기술자가 기록을 대조한다. 새로운 비행장이나 기술 해금은 만들지 않는다.",
              choice("기술자와 기록 회수 · 석유 70", "기술자는 중복 정비 항목을 지웠다. 공항 관리반은 비축 석유 70을 지원했다.", require_job=11, require_army_type=2, delivery_legs=1, target_roles=["airport"], reward_oil=70),
              choice("시험 운항 · 철 20·석유 20 / 금 130,000·석유 90", "시험 기록으로 정비 순서가 확인되었다. 운항 대금과 보충 석유가 정산되었다.", require_job=11, require_army_type=2, cost_iron=20, cost_oil=20, delivery_legs=2, target_roles=["airport", "airport"], reward_gold=130000, reward_oil=90))], repeat_days=0, required_class=9, requires_event=[9, 16]),
    event("D6", "국경 마을의 감사장", "festival", [
        stage("소문보다 늦게 도착한 감사", "이 지역의 보수·배송·전투 중 서로 다른 두 종류의 도움을 확인했다. 주민 대표는 그 일을 적은 감사장을 준비했다. 감사장은 지역 소식의 완료 기록으로 남는다.",
              choice("보수 금 70,000을 받는다", "감사장 아래 군단의 이름이 적혔다. 주민 대표는 약속한 보수를 건넸다.", reward_gold=70000),
              choice("보수를 받지 않고 철 20을 후원한다", "주민들은 후원받은 철로 공동 우물을 보수하기로 했다. 군단의 기부가 감사장에 덧붙여졌다.", cost_iron=20))], repeat_days=60, conditions=["regional_once"]),

    event("E1", "보급소 습격 예고", "battle", [
        stage("표시된 매복 지점", "보급소를 노리는 일반 분견대의 위치가 확인되었다. 전투는 수락한 경우에만 발생한다. 무시하거나 거절해도 실제 창고·생산 시설은 파괴되지 않는다.",
              choice("선제 차단 보병전 · 금 150,000·철 30", "매복 지점을 장악했다. 보급소는 전투 수당과 예비 철을 인계했다.", battle_profile="infantry", reward_gold=150000, reward_iron=30),
              choice("우회 운송 후원 · 금 35,000", "상인들이 안전한 도로로 수송 일정을 바꿨다. 군단은 전투 없이 보급소의 협조자로 기록되었다.", cost_gold=35000))], repeat_days=90),
    event("E2", "종전 명령을 못 들은 잔당", "battle", [
        stage("낡은 명령서의 날짜", "에투루리아의 일반 분견대가 오래된 통행 명령서를 내민다. 사망한 본편 지휘관은 등장하지 않는다. 협상 비용을 내거나 기존 규칙의 전투 한 번으로 해결한다.",
              choice("철 30·석유 20을 제공해 협상 · 금 80,000", "분견대는 보급품을 받고 오래된 검문 명령을 거뒀다. 현지 관리가 협상 경비를 정산했다.", cost_iron=30, cost_oil=20, reward_gold=80000),
              choice("잔당 보병대와 전투 · 금 160,000", "일반 분견대의 저항이 끝났다. 현지 관리는 민간 수송의 재개를 확인했다.", battle_profile="infantry", reward_gold=160000))], repeat_days=90, country=8),
    event("E3", "초소의 통행 분쟁", "battle", [
        stage("서로 다른 통행증", "상인과 경비대가 통행료를 두고 다툰다. 사건 해결은 실제 도시 소유권·외교·지도 통행 가능 상태를 바꾸지 않는다. 전투를 선택하면 일반 경비 분견대를 상대한다.",
              choice("중재비 금 30,000 · 보상 65,000", "양측이 임시 통행 장부에 서명했다. 상단이 중재 경비를 정산했다.", cost_gold=30000, reward_gold=65000),
              choice("경비 분견대와 전투 · 금 145,000", "초소의 분견대가 물러났다. 상인들은 이번 계약분의 경비료를 지급했다.", battle_profile="infantry", reward_gold=145000))], repeat_days=90),
    event("E4", "숲속의 포병 관측소", "battle", [
        stage("수풀 뒤의 측정기", "숲과 야지에서 활동하는 포병·호위병 중심의 분견대다. 일반 지휘관을 중심으로 편성하며 대형 보스 장비는 없다. 기존 군단장 제거·손실·경험치 규칙을 유지한다.",
              choice("포병 관측소 공격 · 금 190,000·철 50", "관측소의 사격 지시가 끊겼다. 회수 가능한 사건 물자를 정리하고 계약금을 받았다.", battle_profile="artillery", reward_gold=190000, reward_iron=50))], repeat_days=90),
    event("E5", "구조대의 퇴로 확보", "battle", [
        stage("구조대가 돌아오는 길", "구조대가 지나갈 길을 막는 적 분견대를 제거하거나 구급상자만 지원한다. 별도 민간인 추종 AI나 보호 대상 사망 게임오버는 없다. 두 보상 경로는 중복 지급하지 않는다.",
              choice("퇴로 확보 보병전 · 금 170,000", "적 분견대를 격파하자 구조대가 퇴로 확인서를 보냈다. 군단은 계약 보상을 받았다.", battle_profile="infantry", reward_gold=170000),
              choice("예비 구급상자 1개 지원 · 금 65,000", "의무 담당자가 봉인을 확인했다. 구조대는 의료 지원 대금 금 65,000을 지급했다.", cost_item_id=53, cost_item_count=1, reward_gold=65000))], repeat_days=90),
    event("E6", "현상수배 기갑 분견대", "battle", [
        stage("일반 수배와 정예 수배", "기갑 분견대의 두 수배 중 하나를 고른다. 실제 전투 손실이 발생할 수 있다. 장비 에디터로 바꾼 성능을 몰래 되돌리지 않으며 차량 포획·보스 설계도 지급은 없다.",
              choice("보통 기갑대 · 금 110,000", "일반 기갑 분견대의 격파 확인서가 발급되었다. 수배금 금 110,000을 받았다.", battle_profile="armor", reward_gold=110000),
              choice("정예 기갑대 · 금 240,000", "정예 기갑 분견대를 격파했다. 확인된 전적에 따라 정예 수배금이 지급되었다.", battle_profile="elite_armor", reward_gold=240000))], repeat_days=90),

    event("F1", "블랙파워의 재건", "chain", [
        stage("본거지 인근의 연락도시", "라이벌과의 실제 결착 뒤 재건을 준비하는 블랙파워에서 소식이 왔다. 적 본거지 자체가 아니라 그 인근의 안전한 일반 연락도시를 방문한다. 소유·주둔·상납금 규칙을 바꾸거나 사망한 영웅을 되살리지 않는다.",
              choice("블랙파워 본거지 인근 연락도시 방문", "연락도시의 군수 담당자는 평범한 병사들의 재건 이야기를 들려주었다. 적 본거지를 점령할 필요는 없었다.", next_stage=1, delivery_legs=1, target_roles=["black_power_hq"])),
        stage("새 창고에 필요한 물자", "재건 담당자는 철 40과 석유 25를 요청한다. 지원을 거절해도 재건 후일담은 이어지고 본편 관계나 본거지 소유권은 바뀌지 않는다.",
              choice("군수품 납품 · 철 40·석유 25 / 금 70,000", "재건 담당자는 자재를 창고에 적재하고 납품 대금을 정산했다.", next_stage=2, cost_iron=40, cost_oil=25, reward_gold=70000),
              choice("군수 지원 없이 이야기를 듣는다", "담당자는 지원을 강요하지 않았다. 군단은 재건된 분견대의 소식을 끝까지 들었다.", next_stage=2)),
        stage("재건된 분견대", "일반 분견대와의 선택 전투다. 참가하면 기존 전투 손실이 적용된다. 전투를 하지 않아도 재건 이야기를 마칠 수 있다.",
              choice("분견대와 보병전 · 금 120,000", "대결이 끝난 뒤 양측은 생존자들의 이름으로 전적을 남겼다. 재건 후일담이 완료되었다.", battle_profile="infantry", reward_gold=120000),
              choice("전투 없이 재건을 지켜본다", "군단은 새 창고의 문이 열리는 것을 보고 돌아섰다. 블랙파워 재건 후일담이 완료되었다."))], repeat_days=0, conditions=["rival_victory", "black_power_restored"]),
    event("F2", "엑제로스: 파멸의 달의 잔향", "chain", [
        stage("군수품 속 암호문", "최후의결전 이후 군수품 사이에서 남은 방어망의 암호문이 발견되었다. 공항과 관측소의 기록을 대조한다. 본편 엔딩이나 보스 제작 조건을 다시 실행하지 않는다.",
              choice("관측 기록 2곳 회수 · 금 80,000", "두 기록의 암호가 일치했다. 남은 기갑 방위대와 항공 초계대의 위치를 확인했다.", next_stage=1, delivery_legs=2, target_roles=["airport", "lab"], reward_gold=80000)),
        stage("잔존 기갑 방위대", "첫 번째 방어망은 기갑대다. 승리 뒤에도 자동으로 다음 전투가 시작되지 않는다. 수리·저장·군단 교체 후 다음 단계를 선택할 수 있다.",
              choice("기갑 방위대 전투 · 금 160,000·철 60", "기갑 방위대의 저항이 끝났다. 관제 기록은 항공 초계대가 마지막 방어망임을 가리켰다.", next_stage=2, battle_profile="armor", reward_gold=160000, reward_iron=60),
              choice("전투 없이 관측 기록만 남기고 마친다", "기갑대와의 교전을 보류했다. 기체 보상 없이 남은 방어망의 기록을 관제반에 인계했다.")),
        stage("마지막 초계 신호", "항공 초계대와의 별도 전투다. 파일럿과 항공군단이 필요하다. 승리 보상 A.S.6 한 기는 저장 공간이 없으면 수령 대기하며 금·자원은 중복 지급하지 않는다.",
              choice("항공 초계대 전투 · A.S.6 1기·금 200,000·석유 100", "마지막 초계 신호가 멎었다. 회수한 A.S.6 한 기와 계약 보상이 인계되었다.", require_army_type=2, require_job=9, battle_profile="air", reward_machine_id=24, reward_gold=200000, reward_oil=100),
              choice("전투 없이 잔존 기록을 봉인한다", "관측 기록을 봉인해 공항 관리반에 맡겼다. 기체 보상 없이 파멸의 달 후일담이 완료되었다."))], repeat_days=0, required_facility=20, conditions=["final_victory"]),
    event("F3", "카란토의 재건 의뢰", "chain", [
        stage("다시 열 창고의 문", "카란토 점령 전투 뒤 실제 아군 주둔이 확인되었다. 이번 보수는 사건 기록이며 도시를 파괴하지 않는다. 제국의 다른 마을을 다시 적성 지역으로 바꾸지 않는다.",
              choice("건축가와 철 30으로 창고 보수 · 금 60,000", "건축가는 창고의 출입로를 복구했다. 주민 대표가 첫 단계 보수비를 지급했다.", next_stage=1, require_job=12, cost_iron=30, reward_gold=60000),
              choice("현지 인부 고용 · 금 40,000", "인부들이 창고를 정리했다. 군수 지원 담당자들이 다음 회의를 준비했다.", next_stage=1, cost_gold=40000)),
        stage("군수 장부의 빈칸", "기술자는 부품 목록을, 과학자는 기록 양식을 정리할 수 있다. 지원 인원은 사라지지 않으며 병과·건물 기술을 새로 해금하지 않는다.",
              choice("기술자와 철 20 지원 · 석유 80", "기술자는 규격을 통일해 잉여 연료통을 찾아냈다. 석유 80이 인계되었다.", next_stage=2, require_job=11, cost_iron=20, reward_oil=80),
              choice("과학자와 석유 15 지원 · 철 80", "과학자는 중복 주문을 바로잡았다. 남은 철 80을 지원 군단에 인계했다.", next_stage=2, require_job=8, cost_oil=15, reward_iron=80)),
        stage("주민 대표의 보고", "창고 보수와 군수 정리가 끝났다. 카란토에서 보고를 받으면 재건 의뢰가 완료된다. 이전 단계 보상은 다시 지급하지 않는다.",
              choice("카란토 방문 · 금 180,000", "주민 대표가 새 창고 열쇠를 들어 보였다. 카란토 재건 기록과 최종 대금이 인계되었다.", delivery_legs=1, target_roles=["capital"], reward_gold=180000))], repeat_days=0, country=8, conditions=["caranto_player_garrison"]),
    event("F4", "상단 연합의 대수송", "chain", [
        stage("세 번의 계약 이후", "서로 다른 세 지역의 B형 배송 계약을 마친 군단에 대수송 계약이 왔다. 철 50과 석유 40을 준비하고 중간 두 도시와 최종 인계지까지 이동한다. 중간 금 70,000과 최종 금 240,000·철 120을 받는다.",
              choice("민간 수송 계획 · 철 50·석유 40", "상단이 민간 수송 계획을 승인했다. 첫 번째 중간 인계지의 연락처를 받았다.", next_stage=1, require_army_type=3, cost_iron=50, cost_oil=40),
              choice("항공 수송 계획 · 철 50·석유 40", "상단이 항공 수송 계획을 승인했다. 실제 항공 이동으로 중간 인계를 확인한다.", next_stage=1, require_army_type=2, cost_iron=50, cost_oil=40)),
        stage("두 중간 인계지", "접근 가능한 두 도시의 인수 확인을 받는다. 민간·항공 중 현재 운용할 배송 가능 군단을 선택할 수 있다. 인계 기록을 이미 받은 도시는 중복 지급 대상이 아니다.",
              choice("중간 도시 2곳 방문 · 금 70,000", "두 중간 담당자가 인수 장부에 서명했다. 최종 인계지는 남은 운송분을 기다린다.", next_stage=2, delivery_legs=2, target_roles=["near", "far"], reward_gold=70000)),
        stage("최종 인계", "마지막 목적지에서 수송을 마친다. 최종 금 240,000과 철 120은 중간 보상과 별도이며 한 번만 지급한다.",
              choice("마지막 목적지 방문 · 금 240,000·철 120", "상단 연합은 모든 인수증을 확인했다. 장거리 대수송 계약이 정산되었다.", delivery_legs=1, target_roles=["far"], reward_gold=240000, reward_iron=120))], repeat_days=0, conditions=["three_delivery_regions"]),
    event("F5", "민간 기술자들의 약속", "chain", [
        stage("세 사람이 남길 일", "창고 보수·연구 자료·공장 재고 사건을 모두 마쳤다. 건축·자료·정비 작업을 원하는 순서로 하나씩 마친다. 이미 마친 작업은 다시 정산하지 않는다. 지원 인원은 사라지지 않으며 영웅화·기술 해금·주둔 보정 한도 변경도 없다.",
              choice("건축가와 철 20으로 공동 작업 · 금 50,000", "건축가는 '돌아올 곳부터 지어야 한다'며 설계도를 접었다. 공동 작업 대금이 지급되었다.", next_stage=0, project_part=1, require_job=12, cost_iron=20, reward_gold=50000),
              choice("과학자에게 자료 정리 의뢰 · 철 60", "과학자는 실패한 기록도 함께 묶었다. 자료 정리의 답례로 철 60을 받았다.", next_stage=0, project_part=2, require_job=8, reward_iron=60),
              choice("기술자와 철 10으로 부품 정리 · 석유 70", "기술자는 규격이 맞는 부품을 골라낸 뒤 자기 부대로 돌아갔다. 회수한 석유 70이 인계되었다.", next_stage=0, project_part=4, require_job=11, cost_iron=10, reward_oil=70)),
        stage("민간 기술자들의 약속", "세 작업을 모두 마쳤다. 새 지원 인력의 계약을 선택할 수 있다. 인원 여유와 도시의 해당 병과 해금이 필요하며 유료 고용이다. 고용하지 않아도 후일담을 완료한다.",
              choice("기술자 1명 고용 · 금 35,000 / 석유 80", "새 기술자가 계약을 마쳤다. 정비반은 세 사람의 약속을 기록하고 석유 80을 인계했다.", require_job=11, cost_gold=35000, hire_class=11, hire_count=1, reward_oil=80),
              choice("추가 고용 없이 감사 물자만 받는다 · 철 40", "세 지원 병과는 다음에 만날 것을 약속했다. 주민들이 모은 철 40을 받고 후일담을 마쳤다.", reward_iron=40))], repeat_days=0, requires_event=[3, 4, 5]),
    event("F6", "종전 기념제", "festival", [
        stage("지역 해결사의 날", "기념제를 제외한 서로 다른 신규 사건 12종을 마쳤다. 포룸에서 첫 기록을 확인한다. 기념 명칭은 글로 남는 기록이며 숨겨진 전투 능력치는 없다.",
              choice("포룸 방문 · 기념금 100,000", "포룸의 기록관은 군단을 '지역 해결사'로 적었다. 첫 기념금이 지급되었다.", next_stage=1, delivery_legs=1, target_roles=["home"], reward_gold=100000),
              choice("포룸 방문 · 금 30,000 기부", "군단은 기념금을 받지 않고 주민 기금에 금 30,000을 보탰다. 같은 기념 기록이 남았다.", next_stage=1, delivery_legs=1, target_roles=["home"], cost_gold=30000), min_completed=12),
        stage("대륙의 중재자", "기념제를 제외한 서로 다른 신규 사건 24종을 마쳐야 두 번째 기념제를 진행한다. 첫 단계 보상은 이미 기록되어 다시 지급되지 않는다.",
              choice("포룸 방문 · 철 120·석유 120", "기록관은 '대륙의 중재자'라는 두 번째 기록을 남겼다. 주민들의 공동 물자가 인계되었다.", next_stage=2, delivery_legs=1, target_roles=["home"], reward_iron=120, reward_oil=120),
              choice("포룸 방문 · 금 50,000 기부", "군단은 물자 대신 재건 기금에 금 50,000을 보탰다. 두 번째 기념 기록이 남았다.", next_stage=2, delivery_legs=1, target_roles=["home"], cost_gold=50000), min_completed=24),
        stage("서른일곱 번의 발자취", "다른 신규 사건 37종을 모두 마친 뒤 마지막 기념제를 연다. 이 단계를 끝내면 전체 38종 완료다. 본편 엔딩 영상이나 부채 청산 사건을 다시 재생하지 않는다.",
              choice("포룸 방문 · 금 250,000·철 100·석유 100", "기록관은 서른여덟 번째 장을 덮었다. 군단이 걸어온 길은 종전 이후의 역사로 남았다.", delivery_legs=1, target_roles=["home"], reward_gold=250000, reward_iron=100, reward_oil=100),
              choice("포룸 방문 · 금 80,000 기부", "군단은 마지막 기념 보수 대신 금 80,000을 새 출발에 보탰다. 모든 전역 사건의 완료가 기록되었다.", delivery_legs=1, target_roles=["home"], cost_gold=80000), min_completed=37)], repeat_days=0, min_completed=12),
    event("G1", "수송로 경비 전차 납품", "delivery", [
        stage("고블린MK2 한 대의 주문", "포룸 정비창에 HP가 완전히 회복된 미배치 일반 전차 고블린MK2 한 대가 필요하다. 담당 군단이 목적지에 실제 도착하면 재고를 다시 확인해 한 대만 납품한다. 탑승·배치 장비와 보스는 사용하지 않는다.",
              choice("고블린MK2 1대 배송 · 금 35,000", "목적지의 경비 담당자가 고블린MK2 한 대를 인수했다. 기준 대금 25,000과 운송 수당 10,000이 정산되었다.", cost_machine_id=6, delivery_legs=1, target_roles=["near"], reward_gold=35000))], repeat_days=90, required_facility=7),
    event("G2", "항로 재개 항공기 납품", "delivery", [
        stage("드래곤MK2의 새 운항지", "포룸 정비창에 HP가 완전히 회복된 미배치 일반 항공기 드래곤MK2 한 대가 필요하다. 담당 군단은 민간군단도 가능하다. 실제 공항 도착 후 보관 기체 한 대를 인계하며 탑승·배치 항공기와 보스는 사용하지 않는다.",
              choice("드래곤MK2 1대 배송 · 금 340,000", "공항 관리반이 드래곤MK2 한 대를 인수했다. 기준 대금 300,000과 운송 수당 40,000이 정산되었다.", cost_machine_id=1, delivery_legs=1, target_roles=["airport"], reward_gold=340000))], repeat_days=90, required_facility=20),
]
