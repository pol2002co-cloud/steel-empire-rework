"""Single-objective contracts, independent of the preserved legacy catalogue.

The engine waits for the goal, consumes its one cost and credits the reward.
No character, formation type, route chain or manual claim is required here.
"""
from world_event_catalog import EVENT_CATALOG as LEGACY_EVENT_CATALOG

GOAL_TYPES = {"visit": 1, "supply": 2, "item": 3, "equipment": 4, "build": 5, "occupy": 6}


def simple(ident, goal_type, text, label, result, *, role="any", building=0,
           fixed=0, repeat=60, title=None, **actions):
    old = LEGACY_EVENT_CATALOG[ident]
    kind = {"visit": "visit", "supply": "trade", "item": "trade",
            "equipment": "delivery", "build": "chain", "occupy": "battle"}[goal_type]
    return dict(id=ident, key=old["key"], title=title or old["title"],
                category=old["category"], kind=kind, repeat_days=repeat,
                required_class=0, required_facility=0, country=0,
                min_completed=0, requires_event=[], conditions=[], early=True,
                goal=dict(type=goal_type, target_role=role, building_id=building, target_fixed=fixed),
                stages=[dict(title=title or old["title"], text=text, min_completed=0,
                             choices=[dict(label=label, result=result,
                                           next_stage=-1, actions=actions)])])


SIMPLE_EVENT_CATALOG = [
    simple(0, "supply", "철 40을 준비하면 장터 교환을 자동 정산한다. 도시 방문이나 담당 군단 지정은 필요 없다.",
           "철 40 납품 → 금 24,000", "상인이 철 40을 인수하고 금 24,000을 지급했다.", cost_iron=40, reward_gold=24000),
    simple(1, "item", "아군 어느 군단이든 가방에 예비 5mm 권총 한 정을 준비하면 납품한다. 장착품은 사용하지 않는다.",
           "예비 5mm 권총 1정 → 금 2,600", "민병대가 권총을 인수했다. 기준 대금과 소액 수당이 정산되었다.", cost_item_id=1, cost_item_count=1, reward_gold=2600),
    simple(2, "supply", "축제 준비금 30,000을 제공하면 주민 모금과 진행 수당을 함께 정산한다. 댄서나 공연 조작은 필요 없다.",
           "금 30,000 지원 → 금 35,000", "주민 모금이 마감되었다. 준비금과 수당 금 35,000을 받았다.", cost_gold=30000, reward_gold=35000),
    simple(3, "build", "포룸에 완공된 창고가 있으면 보수 지원금을 받는다. 이미 지은 창고도 인정하며 추가 철이나 건축가는 요구하지 않는다.",
           "창고 완공 확인 → 금 50,000", "창고의 보관 상태가 확인되어 지원금이 정산되었다.", role="home", fixed=1, building=6, repeat=0, reward_gold=50000),
    simple(4, "build", "포룸에 완공된 연구소가 있으면 자료 정리 의뢰를 마친다. 과학자나 퀴즈 답을 요구하지 않는다.",
           "연구소 완공 확인 → 금 35,000", "연구소의 자료 보관 공간이 확인되었다. 정리 수당을 받았다.", role="home", fixed=1, building=17, repeat=0, reward_gold=35000),
    simple(5, "build", "포룸의 차량공장 완공을 확인하면 예비 부품 정리 물자를 인계한다. 기술자 지정은 없다.",
           "차량공장 완공 확인 → 석유 40", "차량공장의 부품 보관소가 준비되어 석유 40이 인계되었다.", role="home", fixed=1, building=7, repeat=0, reward_oil=40),

    simple(6, "visit", "어느 아군 군단이든 표시된 연락도시 한 곳에 실제로 들어가면 전령 문서 전달이 완료된다.",
           "연락도시 한 곳 방문 → 금 60,000", "연락소가 문서 수령을 확인했다. 운송료가 자동 정산되었다.", role="near", reward_gold=60000),
    simple(7, "visit", "상단의 안전 확인서를 표시된 도시 한 곳에 전달한다. 별도 경비대 전투나 전투군단 지정은 없다.",
           "상단 연락도시 방문 → 금 80,000", "상단은 연락도시의 운송 준비를 확인하고 계약금을 지급했다.", role="near", repeat=90, reward_gold=80000),
    simple(8, "visit", "표시된 관측도시 한 곳을 방문하면 기록 회수를 마친다. 과학자·파일럿이나 여러 도시 방문을 요구하지 않는다.",
           "관측도시 한 곳 방문 → 금 70,000·석유 15", "관측 담당자가 기록을 인계했다. 회수 수당과 석유를 받았다.", role="far", reward_gold=70000, reward_oil=15),
    simple(9, "supply", "철 25를 준비하면 항공 부품용 자재를 납품한다. 항공군단이나 공항 이동 없이 공통 자원에서 정산한다.",
           "철 25 납품 → 금 35,000", "정비반이 항공 부품용 철을 인수하고 대금을 지급했다.", cost_iron=25, reward_gold=35000),
    simple(10, "visit", "어느 아군 군단이든 표시된 보급도시 한 곳을 방문하면 보급선 재개 확인이 끝난다. 연속 운송이나 민간 병종 제한은 없다.",
           "보급도시 한 곳 방문 → 금 65,000", "보급소가 새 운송 연락을 확인했다. 한 구간의 계약이 정산되었다.", role="near", reward_gold=65000),
    simple(11, "supply", "화물 매입금 45,000을 준비하면 반환 보수를 정산한다. 소문 수집·추격·별도 전투는 없다.",
           "금 45,000 지급 → 금 70,000", "현지 중개인이 화물 반환을 마쳤다. 반환 보수 금 70,000이 지급되었다.", cost_gold=45000, repeat=90, reward_gold=70000),

    simple(12, "visit", "초청장에 적힌 연락도시 한 곳을 방문한다. 실제 모의전이나 전투 손실을 발생시키지 않는 문서 전달 의뢰다.",
           "훈련 연락도시 방문 → 금 50,000", "훈련 담당자가 초청장 답신을 받았다. 전달 수당이 정산되었다.", role="near", repeat=90, title="훈련장 초청장 전달", reward_gold=50000),
    simple(13, "visit", "어느 아군 군단이든 포룸에 들어가 청년들의 훈련 상담을 확인한다. 인물을 추가 고용하지 않고 상담 지원금만 받는다.",
           "포룸 방문 → 금 30,000", "신병 상담 접수가 확인되었다. 군단에 상담 지원금이 지급되었다.", role="home", fixed=1, reward_gold=30000),
    simple(14, "supply", "연회용 철제 식기 자재 10을 준비하면 보급 담당자가 연회 지원을 정산한다. 댄서·군단장 지정은 없다.",
           "철 10 지원 → 금 18,000", "보급 담당자가 식기 자재를 인수하고 연회 협조금을 지급했다.", cost_iron=10, reward_gold=18000),
    simple(15, "visit", "표시된 시험도시 한 곳을 방문해 수송로 기록을 전달한다. 차량이나 드라이버의 보유 여부는 검사하지 않는다.",
           "시험도시 한 곳 방문 → 금 75,000·석유 20", "지방 정부가 수송로 자료를 접수하고 운행 조사 수당을 지급했다.", role="far", reward_gold=75000, reward_oil=20),
    simple(16, "visit", "공항이 있는 목적지 한 곳을 방문하면 항공 교류 자료를 전달한다. 어느 아군 군단이든 가능하며 공중전은 없다.",
           "공항도시 한 곳 방문 → 금 80,000·석유 20", "비행장 관리반이 교류 자료를 받았다. 전달 수당이 정산되었다.", role="airport", repeat=90, reward_gold=80000, reward_oil=20),
    simple(17, "visit", "표시된 연락도시 한 곳에서 병사의 제보서를 받는다. 정보료·지역 소문 선행 조건·다른 사건 완료를 요구하지 않는다.",
           "제보 도시 한 곳 방문 → 금 25,000", "떠돌이 병사의 제보서를 접수했다. 정보 전달 협조금이 지급되었다.", role="near", reward_gold=25000),

    simple(18, "supply", "현지 잔해 수거비 20,000을 준비하면 회수 물자를 받는다. 기술자나 별도 전장 방문은 필요 없다.",
           "금 20,000 지급 → 철 40·석유 15", "수거인들이 회수한 철과 석유를 인계했다.", cost_gold=20000, repeat=0, reward_iron=40, reward_oil=15),
    simple(19, "visit", "표시된 폐역 연락도시 한 곳을 방문하면 보관료를 인계받는다. 소문 선행 조건이나 번호 퍼즐은 없다.",
           "폐역 연락도시 방문 → 금 45,000", "역무원이 보관 장부를 확인하고 남은 보관료를 지급했다.", role="near", repeat=0, reward_gold=45000),
    simple(20, "visit", "표시된 자료 보관도시 한 곳을 방문해 기록 사본을 받는다. 여섯 나라 순회나 중간 수집 기록은 요구하지 않는다.",
           "자료 보관도시 방문 → 금 60,000", "보관 담당자가 기록 사본을 인계했다. 한 번의 자료 회수가 정산되었다.", role="far", repeat=0, reward_gold=60000),
    simple(21, "visit", "어느 아군 군단이든 포룸의 전령소를 방문해 안부 편지를 전달한다. 특정 동료의 소속·생존·인물군 조건은 검사하지 않는다.",
           "포룸 전령소 방문 → 금 30,000", "전령소가 안부 편지를 접수했다. 전달 협조금을 받았다.", role="home", fixed=1, repeat=0, reward_gold=30000),
    simple(22, "supply", "정비 기록 복사에 사용할 석유 20을 제공하면 공항 관리반의 지원 물자를 받는다. 항공 임무 선행 완료나 파일럿 지정은 없다.",
           "석유 20 제공 → 금 30,000·석유 40", "관리반이 정비 기록을 정리하고 협조금과 연료를 인계했다.", cost_oil=20, repeat=0, reward_gold=30000, reward_oil=40),
    simple(23, "visit", "표시된 국경 연락도시 한 곳을 방문하면 주민 감사장을 받는다. 지역별 도움 종류 수나 다른 사건 완료 조건은 없다.",
           "국경 연락도시 방문 → 금 50,000", "주민 대표가 감사장을 건네고 방문 협조금을 지급했다.", role="far", repeat=0, reward_gold=50000),

    simple(24, "occupy", "표시된 적 점령 도시를 평소 게임 방식으로 탈환한다. 어느 아군 전투군단이든 가능하며 별도 임시 전투를 만들지 않는다.",
           "적 점령 도시 탈환 → 금 120,000", "도시의 아군 점거를 확인했다. 보급로 확보 보수가 지급되었다.", role="near", repeat=90, reward_gold=120000),
    simple(25, "occupy", "표시된 적 점령 도시를 원래 전투와 점령 규칙으로 확보한다. 특정 국가·이야기 완료·특수 편성 조건은 없다.",
           "적 점령 도시 확보 → 금 130,000", "아군 도시 점거가 확인되었다. 통행로 정상화 보수가 정산되었다.", role="near", repeat=90, title="낡은 통행 명령의 분견대", reward_gold=130000),
    simple(26, "occupy", "표시된 적 점령 도시를 평소 전투로 확보하면 통행 분쟁 의뢰가 끝난다. 자동 외교 변경이나 별도 경비대 소환은 없다.",
           "분쟁 도시 점거 → 금 120,000", "분쟁 도시의 아군 점거를 확인해 계약 보수가 지급되었다.", role="near", repeat=90, reward_gold=120000),
    simple(27, "occupy", "표시된 적 점령 도시를 확보한다. 별도 포병 관측소 전장을 만들지 않고 기존 도시 전투의 결과만 확인한다.",
           "적 점령 도시 확보 → 금 150,000·철 30", "아군 점거가 확인되어 관측로 확보 보수가 지급되었다.", role="far", repeat=90, reward_gold=150000, reward_iron=30),
    simple(28, "occupy", "표시된 적 점령 도시를 탈환해 구조 연락로를 확보한다. 의료 물품·지원 병과·실시간 구조대 호위는 요구하지 않는다.",
           "구조 연락도시 탈환 → 금 140,000", "도시의 아군 점거로 퇴로 확보가 확인되었다. 계약금이 지급되었다.", role="near", repeat=90, reward_gold=140000),
    simple(29, "occupy", "표시된 적 점령 도시를 어느 아군 전투군단으로든 확보한다. 정예 임시 군단이나 새 보스는 생성하지 않는다.",
           "수배 대상 도시 확보 → 금 170,000", "도시 점거 확인서가 발급되어 현상 계약금이 정산되었다.", role="far", repeat=90, reward_gold=170000),

    simple(30, "supply", "재건용 철 40을 준비하면 블랙파워 연락 담당자에게 납품한다. 라이벌 완료·본거지 점령·복귀 기록 조건은 없다.",
           "철 40 납품 → 금 60,000", "연락 담당자가 재건 자재를 접수하고 대금을 지급했다.", cost_iron=40, repeat=0, reward_gold=60000),
    simple(31, "visit", "현재 접근 가능한 공항도시 한 곳에 항로 자료를 전달한다. 최종전·엑제로스 진입·연속 전투 조건 없이 한 번만 정산한다.",
           "공항도시 방문 → A.S.6 1기·금 50,000", "공항 관리반이 자료를 인수하고 포룸 정비창에 A.S.6 한 기를 인계했다.", role="airport", repeat=0, title="공항의 항로 관측 자료", reward_machine_id=24, reward_gold=50000),
    simple(32, "occupy", "카란토를 평소 게임의 전투·점령 방식으로 확보한다. 이미 아군이 주둔 중이면 점거 상태를 확인한다. 추가 건축가·자재·후속 단계는 없다.",
           "카란토 점거 확인 → 금 180,000", "카란토의 아군 점거가 확인되어 재건 협조금이 정산되었다.", role="capital", fixed=40, repeat=0, reward_gold=180000),
    simple(33, "visit", "표시된 상단 인계도시 한 곳에 도착하면 수송 계약이 끝난다. 배송 완료 횟수·지역 수·중간 경유지는 요구하지 않는다.",
           "상단 인계도시 방문 → 금 120,000·철 40", "상단이 한 번의 인계를 확인하고 운송료와 철을 지급했다.", role="far", repeat=0, title="상단 연합의 수송 계약", reward_gold=120000, reward_iron=40),
    simple(34, "build", "포룸에 완공된 정비창을 마련하면 기술 지원 의뢰가 완료된다. 기술자·과학자·건축가나 세 작업의 순서를 요구하지 않는다.",
           "정비창 완공 확인 → 금 50,000·석유 70", "정비창이 준비되어 기술 지원 물자와 협조금이 지급되었다.", role="home", fixed=1, building=19, repeat=0, reward_gold=50000, reward_oil=70),
    simple(35, "visit", "어느 아군 군단이든 포룸의 기념 행사 장소를 방문하면 한 번의 기념 보상을 받는다. 종전이나 다른 사건 완료 수를 요구하지 않는다.",
           "포룸 행사 방문 → 금 100,000·철 50", "군단의 방문이 행사 명부에 남았다. 기념 보수가 정산되었다.", role="home", fixed=1, repeat=0, title="군단 활동 기념제", reward_gold=100000, reward_iron=50),

    simple(36, "equipment", "포룸 정비창에 완전히 수리된 미배치·무승무원인 고블린MK2 한 대를 준비하면 자동 납품한다. 배송 군단 지정이나 도시 이동은 요구하지 않는다.",
           "예비 고블린MK2 1대 → 금 35,000", "포룸의 예비 고블린MK2 한 대를 납품하고 대금을 받았다.", cost_machine_id=6, repeat=90, reward_gold=35000),
    simple(37, "equipment", "포룸 정비창에 완전히 수리된 미배치·무승무원인 드래곤MK2 한 대를 준비하면 자동 납품한다. 별도 파일럿 지정이나 배송 이동 조건은 없다.",
           "예비 드래곤MK2 1대 → 금 340,000", "포룸의 예비 드래곤MK2 한 대를 납품하고 대금을 받았다.", cost_machine_id=1, repeat=90, reward_gold=340000),
]
