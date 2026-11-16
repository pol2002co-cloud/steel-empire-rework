"""Generate readonly CP949 event tables and embed the validated fixed-base code."""
from pathlib import Path
import hashlib
import re

from world_event_catalog import EVENT_CATALOG as LEGACY_EVENT_CATALOG, CATEGORIES, BATTLE_PROFILES, TARGET_ROLES, STORY_CONDITIONS
from world_event_simple_catalog import SIMPLE_EVENT_CATALOG as EVENT_CATALOG, GOAL_TYPES
from expedition_actions import EXPORTS as EXPEDITION_EXPORTS, PROTOTYPES as EXPEDITION_PROTOTYPES, SOURCE as EXPEDITION_SOURCE

ROOT = Path(__file__).resolve().parent
EXPORTS = ("we_training_done", "we_message", "we_load_begin", "we_load_end", "we_window_close", "we_present", "we_idle", "we_tick", "we_router", "we_test_accept", "we_test_claim", "we_test_progress", "we_test_prerequisite", "we_test_tour")
EXPORTS += EXPEDITION_EXPORTS + ("we_world_reset", "we_ruin_visit", "we_load_game", "we_save", "we_test_ex_start", "we_test_ex_guardian", "we_test_ex_bless", "we_test_ex_recipe", "we_test_ex_state")
KINDS = {name: index for index, name in enumerate(("trade", "delivery", "visit", "battle", "hire", "collection", "chain", "festival"))}
ROLE_INDICES = {name: index+1 for index, name in enumerate(TARGET_ROLES)}
ROLE_MASKS = {name: 1 << index for index, name in enumerate(TARGET_ROLES)}
PREDICATE_MASKS = {name: 1 << index for index, name in enumerate((*STORY_CONDITIONS, "regional_two_types"))}
PROFILE_IDS = {name: index+1 for index, name in enumerate(BATTLE_PROFILES)}
CONDITION_TEXT = {
    "rival_victory": "라이벌 실제 승리 완료",
    "black_power_restored": "블랙파워의 기존 복귀 처리 완료",
    "final_victory": "최후의결전 승리 완료",
    "caranto_player_garrison": "카란토에 살아 있는 아군 군단 주둔",
    "living_companion": "편지 미수령 인물군의 생존 동료 보유",
    "regional_once": "이 나라에서 아직 이 사건을 완료하지 않음",
    "regional_rumor": "이 나라의 소문을 아직 듣지 않았고 폐역 금고도 미완료",
    "three_delivery_regions": "서로 다른 세 나라에서 B형 배송 사건 완료",
    "regional_two_types": "이 나라에서 보수·배송·전투 중 두 종류 이상 완료",
}
CLASS_NAMES = {8: "과학자", 9: "파일럿", 10: "드라이버", 11: "기술자", 12: "건축가", 13: "댄서"}
FACILITY_NAMES = {5: "막사", 6: "창고", 7: "차량공장", 13: "병기창", 17: "연구소", 19: "정비창", 20: "공항"}
ACTION_KEYS = {
    "cost_gold", "cost_iron", "cost_oil", "cost_item_id", "cost_item_count",
    "reward_gold", "reward_iron", "reward_oil", "reward_item_id", "reward_item_count",
    "reward_machine_id", "hire_class", "hire_count", "require_job", "require_army_type",
    "battle_profile", "delivery_legs", "target_roles", "project_part", "cost_machine_id",
}


def _number(value):
    if isinstance(value, str):
        value = int(value, 0)
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError("Expected an unsigned DWORD")
    return value


def c_string(value):
    """Fixed-width octal escapes cannot absorb the next hexadecimal character."""
    if not isinstance(value, str) or "\0" in value:
        raise ValueError("Expected a NUL-free string")
    return '"'+''.join('\\%03o' % byte for byte in value.encode('cp949'))+'"'


def cp949_source(source):
    """Convert narrow string literals, retaining C escapes/comments unchanged."""
    tokens = re.compile(r'(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)|(?P<string>"(?:\\[\s\S]|[^"\\])*")|(?P<char>\'(?:\\[\s\S]|[^\'\\])*\')')
    def replace(match):
        if match.lastgroup != "string":
            return match.group()
        value = match.group()
        return ''.join(ch if ord(ch) < 128 else ''.join('\\%03o' % b for b in ch.encode('cp949')) for ch in value)
    return tokens.sub(replace, source)


def encode_roles(roles):
    if not isinstance(roles, list) or len(roles) > 6:
        raise ValueError("At most six sequential destination roles are supported")
    sequence, masks = 0, 0
    for index, role in enumerate(roles):
        if role not in ROLE_INDICES:
            raise ValueError("Unknown destination role: "+str(role))
        sequence |= ROLE_INDICES[role] << (4*index)
        masks |= ROLE_MASKS[role]
    return masks, sequence


def predicates(event):
    names = list(event["conditions"])
    if event["id"] == 23 and "goal" not in event:
        names.append("regional_two_types")
    if len(set(names)) != len(names) or any(name not in PREDICATE_MASKS for name in names):
        raise ValueError("Unknown or duplicate event prerequisite")
    return sum(PREDICATE_MASKS[name] for name in names)


def condition_text(event, catalog=EVENT_CATALOG):
    if "goal" in event:
        goal = event["goal"]
        text = ["본편 도중에도 발동 / 목표 하나만 확인하여 자동 완료·정산"]
        descriptions = {
            "visit": "어느 아군 군단이든 표시된 도시 한 곳 방문",
            "supply": "표시된 자원 한 종류를 확보하면 자동 납품; 부족하면 대기",
            "item": "어느 아군 군단이든 가방의 지정 예비 물품 한 개 준비; 장착품 제외",
            "equipment": "포룸 정비창의 HP가 남아 있는 미배치·무승무원 일반 장비 한 대 준비",
            "build": "포룸에 "+FACILITY_NAMES.get(goal["building_id"], "해당 건물")+" 완공; 이미 지은 건물도 인정",
            "occupy": "표시된 적 도시를 기존 게임 규칙으로 점거; 임시 전투나 편성 제한 없음",
        }
        if goal["type"] not in descriptions:
            raise ValueError("Unknown single goal")
        text.append(descriptions[goal["type"]])
        if goal["target_fixed"]:
            text.append("목표 도시: "+{1: "포룸", 40: "카란토"}.get(goal["target_fixed"], "표시된 도시"))
        text.append("최소 반복 간격 %d일" % event["repeat_days"] if event["repeat_days"] else "한 번만 정산")
        text.append("병과·군단 종류·선행 사건·종전·수동 수령 조건 없음")
        return " / ".join(text)
    text = ["본편 도중에도 발동 / 지역 소식에서 수락" if event["early"] else "최후의결전 승리 이후 / 지역 소식에서 수락"]
    if event["min_completed"]:
        text.append("기념제를 제외한 신규 사건 %d종 완료" % event["min_completed"])
    if event["requires_event"]:
        text.append("선행: "+", ".join(catalog[n]["title"] for n in event["requires_event"]))
    if event["required_class"]:
        text.append("필요 병과: "+CLASS_NAMES[event["required_class"]])
    if event["required_facility"]:
        facility = event["required_facility"]
        text.append("완공 시설: "+FACILITY_NAMES.get(facility, "건물 %d" % facility))
    if event["country"]:
        text.append("발생 지역: "+{8: "에투루리아 제국"}.get(event["country"], "해당 국가"))
    names = list(event["conditions"])+(["regional_two_types"] if event["id"] == 23 else [])
    text.extend(CONDITION_TEXT[name] for name in names)
    if event["id"] == 19:
        text.append("해당 나라에서 떠돌이 병사의 소문 확인")
    text.append("최소 반복 간격 %d일" % event["repeat_days"] if event["repeat_days"] else "일회성 후일담")
    text.append("각 선택의 물자·병과·군단 조건을 추가 확인")
    if any(c["actions"].get("cost_machine_id") for s in event["stages"] for c in s["choices"]):
        text.append("포룸 정비창의 HP가 완전히 회복된 미배치 일반 장비 1대를 실제 도착 후 납품")
    return " / ".join(text)


def _choice_values(choice, stage_count, simple=False):
    actions = choice["actions"]
    if set(actions)-ACTION_KEYS:
        raise ValueError("Unsupported action fields: "+", ".join(sorted(set(actions)-ACTION_KEYS)))
    next_stage = choice["next_stage"]
    if type(next_stage) is not int or not -1 <= next_stage < stage_count:
        raise ValueError("Invalid next stage")
    for name, value in actions.items():
        if name not in ("battle_profile", "target_roles"):
            if _number(value) > 0x7fffffff:
                raise ValueError("An action value exceeds the native signed-int range")
    role_names = actions.get("target_roles", [])
    roles, sequence = encode_roles(role_names)
    legs = actions.get("delivery_legs", 0)
    if type(legs) is not int or not 0 <= legs <= 6 or len(role_names) != legs:
        raise ValueError("Each delivery leg needs exactly one target role")
    profile = actions.get("battle_profile")
    if profile is not None and profile not in PROFILE_IDS:
        raise ValueError("Unknown battle profile")
    if "cost_machine_id" in actions and (actions["cost_machine_id"] not in (1, 6) or legs != (0 if simple else 1) or profile is not None):
        raise ValueError("Equipment delivery has an unsupported machine or route")
    army_type = actions.get("require_army_type", -1)
    if army_type not in (-1, 0, 1, 2, 3):
        raise ValueError("Invalid army type")
    for prefix in ("cost_item", "reward_item"):
        if (prefix+"_id" in actions) != (prefix+"_count" in actions):
            raise ValueError("Item ID and count must be paired")
    get = lambda name: str(actions.get(name, 0))
    cost = "{"+",".join(get("cost_"+name) for name in ("gold", "iron", "oil"))+"}"
    reward = "{"+",".join(get("reward_"+name) for name in ("gold", "iron", "oil"))+"}"
    fields = [c_string(choice["label"]), c_string(choice["result"]), str(next_stage), cost, reward]
    fields.extend(get(name) for name in ("cost_item_id", "cost_item_count", "reward_item_id", "reward_item_count", "reward_machine_id", "hire_class", "hire_count", "require_job"))
    fields.extend((str(army_type), str(PROFILE_IDS.get(profile, 0)), str(legs), str(roles), get("project_part"), str(sequence)+"u", get("cost_machine_id")))
    return "{"+",".join(fields)+"}"


def generate_header(state, actions, journal, catalog=EVENT_CATALOG, tour_actions=None, storage=None):
    """Produce an ASCII-only include after C has declared Choice/Stage/Event."""
    count = len(EVENT_CATALOG)
    if len(catalog) != count or [e["id"] for e in catalog] != list(range(count)):
        raise ValueError("Expected the complete ordered event catalogue")
    journal = journal.get("event_journal", journal)
    macros = {"S_BASE": state["base"], "S_MAGIC": state["magic"], "S_DONE": state["done_address"],
              "S_LAST_DAY": state["last_day_address"], "S_NEXT_OFFER": state["next_offer_address"],
              "UI_SELECT": journal["select"], "UI_SPEECH": journal["speech"]}
    for name in ("getslot", "completed", "count_completed", "tick", "rng", "can_offer", "schedule", "finish", "clear", "reserve_battle"):
        macros["S_"+name.upper()] = state[name]
    for name in ("find_item", "take_item", "give_item", "hire", "give_machine", "battle", "known", "find_machine", "take_machine"):
        macros["A_"+name.upper()] = actions[name]
    macros["A_PERFORM"] = (tour_actions or actions)["perform"]
    macros["E_NATIVE_SAVE"] = (storage or {}).get("native_save", 0)
    lines = ["/* Generated own event text and native adapter addresses. */", "#ifndef WORLD_EVENT_GENERATED_H", "#define WORLD_EVENT_GENERATED_H"]
    lines.extend("#define %s 0x%xu" % (name, _number(value)) for name, value in sorted(macros.items()))
    lines.extend("#define P_%s %du" % (name.upper(), mask) for name, mask in PREDICATE_MASKS.items())
    lines.extend("#define R_%s %du" % (name.upper(), mask) for name, mask in ROLE_MASKS.items())
    lines.extend("#define K_%s %d" % (name.upper(), value) for name, value in KINDS.items())
    lines.append("#define WORLD_EVENT_COUNT %d" % count)
    lines.append("#define LEGACY_EVENT_COUNT %d" % len(LEGACY_EVENT_CATALOG))
    for table_name, prefix, table_catalog in (("EVENTS", "", catalog), ("LEGACY_EVENTS", "LEGACY_", LEGACY_EVENT_CATALOG)):
        for event in table_catalog:
            ident, stages = event["id"], event["stages"]
            if not 1 <= len(stages) <= 3:
                raise ValueError("Expected one to three stages")
            for stage_index, stage in enumerate(stages):
                choices = stage["choices"]
                if not 1 <= len(choices) <= 3:
                    raise ValueError("Expected one to three choices")
                lines.append("static const Choice %sCH_%d_%d[]={" % (prefix, ident, stage_index))
                lines.extend(_choice_values(c, len(stages), simple="goal" in event)+"," for c in choices)
                lines.append("};")
            lines.append("static const Stage %sST_%d[]={" % (prefix, ident))
            for stage_index, stage in enumerate(stages):
                lines.append("{%s,%s,%sCH_%d_%d,%d,%d}," % (c_string(stage["title"]), c_string(stage["text"]), prefix, ident, stage_index, len(stage["choices"]), _number(stage.get("min_completed", 0))))
            lines.append("};")
        lines.append("static const Event %s[]={" % table_name)
        for event in table_catalog:
            low = high = 0
            for dependency in event["requires_event"]:
                if type(dependency) is not int or not 0 <= dependency < len(table_catalog):
                    raise ValueError("Invalid event dependency")
                if dependency < 32:
                    low |= 1 << dependency
                else:
                    high |= 1 << (dependency-32)
            fields = [c_string(event["key"]), c_string(event["title"]), c_string(condition_text(event, table_catalog))]
            fields.extend(str(_number(event[name])) for name in ("category",))
            fields.append(str(KINDS[event["kind"]]))
            fields.extend(str(_number(event[name])) for name in ("repeat_days", "required_class", "required_facility", "country", "min_completed"))
            fields.extend((str(low)+"u", str(high)+"u", str(predicates(event))+"u", str(len(event["stages"])), prefix+"ST_%d" % event["id"], str(int(event["early"]))))
            goal = event.get("goal")
            if goal is None:
                fields.extend(("0", "0", "0", "0"))
            else:
                if set(goal) != {"type", "target_role", "building_id", "target_fixed"} or goal["type"] not in GOAL_TYPES:
                    raise ValueError("Invalid single goal fields")
                role = goal["target_role"]
                if role != "any" and role not in ROLE_MASKS:
                    raise ValueError("Unknown single goal role")
                building, target = _number(goal["building_id"]), _number(goal["target_fixed"])
                if building > 32 or target not in (0, 1, 40):
                    raise ValueError("Invalid building or fixed city")
                fields.extend((str(GOAL_TYPES[goal["type"]]), str(building), str(target), str(ROLE_MASKS.get(role, 0))))
            lines.append("{"+",".join(fields)+"},")
        lines.append("};")
    lines.extend(("#endif", ""))
    return "\n".join(lines)


def emit(put, asm, address, patch, journal, build_dir=None, read=None):
    from world_event_state import emit as emit_state
    from world_event_actions import emit as emit_actions
    from world_tour_actions import emit as emit_tour
    from world_event_compile import compile_image, REWORK_END
    state = emit_state(put, asm, address)["world_event_state"]
    actions = emit_actions(put, asm, address, patch)["world_event_actions"]
    tour_actions = emit_tour(put, asm, address)["world_tour_actions"]
    from expedition_storage import emit as emit_storage
    from expedition_catalog import generate_catalog_header
    from ruin_guardians import generate_header as generate_guardian_header
    if read is None:
        raise ValueError("The verified original executable reader is required")
    storage=emit_storage(put,asm,address,read)
    build = Path(build_dir).resolve() if build_dir is not None else ROOT/"world-events-build-v0110"
    build.mkdir(parents=True, exist_ok=True)
    header = generate_header(state, actions, journal, tour_actions=tour_actions, storage=storage)
    source = cp949_source(EXPEDITION_PROTOTYPES+"\n"+(ROOT/"world_event_native.c").read_text(encoding="utf-8-sig")+"\n"+(ROOT/"expedition_native.c").read_text(encoding="utf-8-sig")+"\n"+EXPEDITION_SOURCE)
    (build/"expedition_catalog_generated.h").write_text(generate_catalog_header(c_string),encoding="ascii")
    (build/"ruin_guardians_generated.h").write_text(generate_guardian_header(),encoding="ascii")
    (build/"expedition_storage.h").write_bytes((ROOT/"expedition_storage.h").read_bytes())
    header_path = build/"world_event_generated.h"
    source_path = build/"world_event_native_cp949.c"
    header_path.write_text(header, encoding="ascii")
    source_path.write_text(source, encoding="utf-8")
    current = address()
    if current % 16:
        raise ValueError("Native helper allocator must retain 16-byte alignment")
    base = (current+0xffff)&~0xffff
    if base >= REWORK_END:
        raise ValueError("No 64K-aligned event image slot remains in .rework")
    mapped, exports = compile_image(source_path, build, base, build/"world_events.dll", EXPORTS)
    if base+len(mapped) >= REWORK_END:
        raise ValueError("Event image leaves no allocator capacity")
    if base != current:
        placed = put(bytes(base-current))
        if placed != current or address() != base:
            raise ValueError("Helper allocator did not preserve fixed-base padding")
    placed = put(mapped)
    if placed != base:
        raise ValueError("Event image was not embedded at its linked address")
    from world_event_dispatch import emit as emit_dispatch
    dispatch=emit_dispatch(put,asm,address,patch,exports)
    from retraining_notice_patch import emit as emit_retraining_notice
    retraining_notice=emit_retraining_notice(put,asm,address,patch,exports)
    from ruin_visits import emit as emit_ruins
    ruins=emit_ruins(put,asm,address,patch,exports)
    metadata = dict(
        expeditions=dict(storage=storage,ruins=ruins,slots=4,max_heroes=3,max_generics=20,save_footer=True),retraining_notice=retraining_notice, dispatch=dispatch, idle=hex(exports["we_idle"]), tick=hex(exports["we_tick"]), router=hex(exports["we_router"]),
        exports={name: hex(value) for name, value in exports.items()},
        state=state, actions=actions, tour_actions=tour_actions, image_base=hex(base), image_size=len(mapped),
        mapped_sha256=hashlib.sha256(mapped).hexdigest(),
        generated_header_sha256=hashlib.sha256(header.encode("ascii")).hexdigest(),
        compiled_source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        events=len(EVENT_CATALOG), stages=sum(len(e["stages"]) for e in EVENT_CATALOG),
        choices=sum(len(s["choices"]) for e in EVENT_CATALOG for s in e["stages"]),
        legacy_events=len(LEGACY_EVENT_CATALOG),
        legacy_stages=sum(len(e["stages"]) for e in LEGACY_EVENT_CATALOG),
        legacy_choices=sum(len(s["choices"]) for e in LEGACY_EVENT_CATALOG for s in e["stages"]),
        goal_types=GOAL_TYPES,
        early_event_ids=[e["id"] for e in EVENT_CATALOG if e["early"]],
        categories=list(CATEGORIES), kind_ids=KINDS, role_indices=ROLE_INDICES,
        role_masks=ROLE_MASKS, predicate_masks=PREDICATE_MASKS, profiles=PROFILE_IDS,
        resources=dict(gold=hex(0x46e5d8), iron=hex(0x46e5dc), oil=hex(0x46e5e0),
                       script_globals=hex(0x48d398), world_pointer=hex(0x48c3d8)),
        automatic_dialogue=dict(entry="we_idle",message_entry="we_message",window_message=0x86e0,controller_state=3,warmup_ms=1000,offer_seen_bit=30,ready_seen_bit=31,notification_card_word=5,accepted_day_mask=0x3fffffff,busy_global=82,busy_bit=31),
        reserved_globals=[*range(31, 85), 87], encoding="CP949 narrow strings; fixed-width C octal escapes",
        safety="Readonly fixed-base C image, no imports/TLS/writable sections; stock saves and native battle rules retained.")
    return {"world_events": metadata}
