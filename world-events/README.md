# 신규 전역 이벤트 자체 작성 소스

world_event_simple_catalog.py는 38종의 단일 목표·자동 완료 사건 데이터입니다.
world_event_catalog.py는 기존 진행 카드·보상의 호환성 유지를 위한 이전 사건 데이터입니다.
world_event_state.py는 저장 상태, world_event_actions.py는 원본 함수 연결,
world_event_native.c는 사건 UI·목표 진행, world_events_patch.py는 CP949 표와 고정 주소 코드 생성을 담당합니다.
world_tour_actions.py는 일반 댄서·영웅 댄서의 자체 자동 공연 정산 연결을 담당합니다.
expedition_native.c와 expedition_catalog.py는 별도 파견대·유적·제작의 UI와 규칙을 담당합니다.
expedition_actions.py는 원본 인원 편성·경험치·귀환 처리와 연결하고,
expedition_storage.py/expedition_storage.h는 원본 저장 함수와 손상 검사·안전한 추가 기록을 연결합니다.
ruin_visits.py는 네 실제 유적의 원본 스크립트 진입을 관찰하며 기존 이야기 처리를 유지합니다.
world_event_compile.py는 개발 워크스페이스의 검증된 프로젝트 로컬 Zig를 사용합니다.

원본 실행 파일·게임 데이터·기준 인물 표·저장·메모리 덤프·개인 검증 자료·컴파일러는 포함하지 않습니다.
이 폴더만으로 게임을 실행하거나 전체 리워크를 재빌드할 수 없습니다.
실행 파일 연결과 통합 검사는 개발자의 원본 보유 워크스페이스와 이전 누적 패치 모듈이 필요합니다.
검사 파일은 구현 검토용으로 포함하며 실제 게임 장기 플레이 검증을 대신하지 않습니다.
test_world_event_simple_catalog.py와 test_world_event_simple.py는 새 목표와 상태 이행을 검사합니다.
test_goal_occupation.py는 원본 도시 진입·철수 함수와 군사 점령 판정을 검사합니다.
test_ruin_guardians.py는 연간 3단계 진행·승패·저장·보상 중복 방지를 검사합니다.
test_ruin_guardian_actions.py는 12개 편성의 원본 전투 생성·배치·장비·정리 경로를 검사합니다.
test_expedition_auto.py는 실제 성공률·추가 지급률 기준의 자동 편성을 전수 조합과 비교합니다.
test_quest_usability.py, test_expedition_usability.py, test_ruin_random.py는 목표 안내·반복 파견·연간 추첨을 검사합니다.
