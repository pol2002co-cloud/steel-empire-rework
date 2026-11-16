"""Pure catalogue checks; these do not certify native delivery or combat."""
import copy
import unittest

from world_event_catalog import EVENT_CATALOG, BATTLE_PROFILES, TARGET_ROLES, STORY_CONDITIONS, EARLY_EVENT_IDS


ACTION_KEYS = {
    "cost_gold", "cost_iron", "cost_oil", "cost_item_id", "cost_item_count",
    "reward_gold", "reward_iron", "reward_oil", "reward_item_id", "reward_item_count",
    "reward_machine_id", "hire_class", "hire_count", "require_job", "require_army_type",
    "battle_profile", "delivery_legs", "target_roles", "project_part", "cost_machine_id",
}
EVENT_KEYS = {
    "id", "key", "title", "category", "kind", "repeat_days", "required_class",
    "required_facility", "country", "min_completed", "requires_event", "conditions", "stages", "early",
}
KINDS = {"trade", "delivery", "visit", "battle", "hire", "collection", "chain", "festival"}


def validate_catalog(catalog):
    count = len(EVENT_CATALOG)
    assert len(catalog) == count
    assert [e["id"] for e in catalog] == list(range(count))
    assert len({e["title"] for e in catalog}) == count
    for event in catalog:
        assert set(event) == EVENT_KEYS
        ident = event["id"]
        assert event["category"] == ident // 6
        assert event["key"] == chr(ord("A") + ident//6) + str(ident % 6 + 1)
        assert event["kind"] in KINDS
        assert event["required_class"] in (0, 8, 9, 10, 11, 12, 13)
        assert 0 <= event["required_facility"] <= 32
        assert 0 <= event["country"] <= 24
        assert 0 <= event["min_completed"] < count
        assert type(event["early"]) is bool and event["early"] == (ident in EARLY_EVENT_IDS)
        assert set(event["conditions"]) <= set(STORY_CONDITIONS)
        assert len(set(event["requires_event"])) == len(event["requires_event"])
        assert all(0 <= n < count and n != ident for n in event["requires_event"])
        assert event["repeat_days"] == 0 or event["repeat_days"] >= 60
        stages = event["stages"]
        assert 1 <= len(stages) <= 3
        reaches_end = set()
        reachable = {0}
        for index, stage in enumerate(stages):
            assert set(stage) == {"title", "text", "choices", "min_completed"}
            assert stage["title"].strip() and stage["text"].strip()
            assert stage["min_completed"] >= 0
            assert 1 <= len(stage["choices"]) <= 3
            assert len({c["label"] for c in stage["choices"]}) == len(stage["choices"])
            for choice in stage["choices"]:
                assert set(choice) == {"label", "result", "actions", "next_stage"}
                assert choice["label"].strip() and choice["result"].strip()
                next_stage = choice["next_stage"]
                assert -1 <= next_stage < len(stages)
                actions = choice["actions"]
                assert set(actions) <= ACTION_KEYS
                for name, value in actions.items():
                    if name in ("battle_profile", "target_roles"):
                        continue
                    assert type(value) is int and value >= 0
                for prefix in ("cost_item", "reward_item"):
                    assert (prefix+"_id" in actions) == (prefix+"_count" in actions)
                    if prefix+"_id" in actions:
                        assert actions[prefix+"_id"] in (1, 53)
                        assert actions[prefix+"_count"] >= 1
                if "hire_class" in actions:
                    assert actions["hire_class"] in range(1, 14)
                    assert 1 <= actions["hire_count"] <= 3
                    assert actions.get("cost_gold", 0) > 0
                else:
                    assert "hire_count" not in actions
                if "require_job" in actions:
                    assert 8 <= actions["require_job"] <= 13
                if "require_army_type" in actions:
                    assert actions["require_army_type"] in range(4)
                if "battle_profile" in actions:
                    assert actions["battle_profile"] in BATTLE_PROFILES
                    assert actions.get("require_army_type") != 3
                    assert event["repeat_days"] == 0 or event["repeat_days"] >= 90
                    assert not event["early"]
                if "delivery_legs" in actions:
                    assert 1 <= actions["delivery_legs"] <= 3
                    assert len(actions["target_roles"]) == actions["delivery_legs"]
                    assert set(actions["target_roles"]) <= set(TARGET_ROLES)
                else:
                    assert "target_roles" not in actions
                if "reward_machine_id" in actions:
                    assert event["key"] == "F2" and actions["reward_machine_id"] == 24
                    assert actions.get("battle_profile") == "air"
                if "cost_machine_id" in actions:
                    assert ident in (36, 37) and event["early"]
                    assert actions["cost_machine_id"] == {36: 6, 37: 1}[ident]
                    assert actions.get("delivery_legs") == 1
                    assert "require_army_type" not in actions and "battle_profile" not in actions
                    assert event["required_facility"] == {36: 7, 37: 20}[ident]
                if "project_part" in actions:
                    assert ident == 34 and index == 0 and next_stage == 0
                    assert actions["project_part"] in (1, 2, 4)
                    assert actions["require_job"] == {1: 12, 2: 8, 4: 11}[actions["project_part"]]
                if next_stage == index and "project_part" not in actions:
                    assert not actions, "A retry cannot repeatedly pay a reward or consume a cost"
                if next_stage == -1:
                    reaches_end.add(index)
        # Every stage can be entered and every branch can eventually terminate.
        for _ in stages:
            for index in tuple(reachable):
                reachable.update(c["next_stage"] for c in stages[index]["choices"] if c["next_stage"] >= 0)
                if any("project_part" in c["actions"] for c in stages[index]["choices"]):
                    reachable.add(1)  # Root's all-three-parts transition.
            for index, stage in enumerate(stages):
                if any(c["next_stage"] in reaches_end for c in stage["choices"]):
                    reaches_end.add(index)
                if 1 in reaches_end and any("project_part" in c["actions"] for c in stage["choices"]):
                    reaches_end.add(index)
        assert reachable == reaches_end == set(range(len(stages)))
    # Prerequisites must not make each other permanently inaccessible.
    visited, active = set(), set()
    def visit(ident):
        assert ident not in active, "Circular event prerequisites"
        if ident in visited:
            return
        active.add(ident)
        for dependency in catalog[ident]["requires_event"]:
            visit(dependency)
        active.remove(ident)
        visited.add(ident)
    for ident in range(count):
        visit(ident)


class CatalogTests(unittest.TestCase):
    def test_schema_and_all_paths(self):
        validate_catalog(EVENT_CATALOG)

    def test_native_korean_text_and_dialogue_budget(self):
        for event in EVENT_CATALOG:
            self.assertLess(len(event["title"].encode("cp949")), 96)
            for stage in event["stages"]:
                self.assertLess(len(stage["text"].encode("cp949")), 512)
                for choice in stage["choices"]:
                    self.assertLess(len(choice["label"].encode("cp949")), 128)
                    self.assertLess(len(choice["result"].encode("cp949")), 512)

    def test_six_countries_and_milestones(self):
        collection = EVENT_CATALOG[20]
        paths = [s["choices"][0]["actions"] for s in collection["stages"]]
        self.assertEqual(sum(a["delivery_legs"] for a in paths), 6)
        self.assertEqual([r for a in paths for r in a["target_roles"]], ["different_country"]*6)
        festival = EVENT_CATALOG[35]
        self.assertEqual([s["min_completed"] for s in festival["stages"]], [12, 24, len(EVENT_CATALOG)-1])
        self.assertFalse(any(35 in e["requires_event"] for e in EVENT_CATALOG))

    def test_alternate_safe_routes_are_actual_noncombat_choices(self):
        for ident in (7, 11, 16):  # B2, B6, C5
            actions = [c["actions"] for c in EVENT_CATALOG[ident]["stages"][0]["choices"]]
            self.assertTrue(any("battle_profile" in a for a in actions))
            self.assertTrue(any("battle_profile" not in a and "delivery_legs" in a for a in actions))

    def test_early_eligibility_and_two_real_equipment_deliveries(self):
        self.assertEqual(len(EVENT_CATALOG), 38)
        self.assertEqual(sum(e["early"] for e in EVENT_CATALOG), 22)
        for ident in (7, 11, 12, 16, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 35):
            self.assertFalse(EVENT_CATALOG[ident]["early"])
        self.assertEqual([e["key"] for e in EVENT_CATALOG[-2:]], ["G1", "G2"])
        self.assertEqual([e["repeat_days"] for e in EVENT_CATALOG[-2:]], [90, 90])
        self.assertEqual([e["stages"][0]["choices"][0]["actions"]["reward_gold"] for e in EVENT_CATALOG[-2:]], [35000, 340000])

    def test_free_order_parts_and_regional_repeat_guards(self):
        project = EVENT_CATALOG[34]
        self.assertEqual(len(project["stages"]), 2)
        parts = project["stages"][0]["choices"]
        self.assertEqual({c["actions"]["project_part"] for c in parts}, {1, 2, 4})
        self.assertTrue(all(c["next_stage"] == 0 for c in parts))
        for ident in (18, 19, 23):  # D1, D2, D6
            self.assertEqual(EVENT_CATALOG[ident]["conditions"], ["regional_once"])
            self.assertEqual(EVENT_CATALOG[ident]["repeat_days"], 60)
        self.assertEqual(EVENT_CATALOG[17]["conditions"], ["regional_rumor"])
        self.assertEqual(EVENT_CATALOG[33]["conditions"], ["three_delivery_regions"])

    def test_no_story_or_technology_rewrites(self):
        for event in EVENT_CATALOG:
            for stage in event["stages"]:
                for choice in stage["choices"]:
                    self.assertLessEqual(set(choice["actions"]), ACTION_KEYS)
                    self.assertNotIn("unlock", choice["actions"])
                    self.assertNotIn("revive", choice["actions"])
        self.assertEqual(EVENT_CATALOG[30]["conditions"], ["rival_victory", "black_power_restored"])
        self.assertEqual(EVENT_CATALOG[32]["conditions"], ["caranto_player_garrison"])

    def test_bad_profiles_targets_cycles_and_retry_rewards_rejected(self):
        corruptions = (
            lambda c: c[0]["stages"][0]["choices"][0]["actions"].update(battle_profile="unknown"),
            lambda c: c[6]["stages"][0]["choices"][0]["actions"].update(target_roles=["inaccessible"]),
            lambda c: c[0]["requires_event"].append(0),
            lambda c: c[0]["requires_event"].append(1) or c[1]["requires_event"].append(0),
            lambda c: c[19]["stages"][0]["choices"][1]["actions"].update(reward_gold=1),
        )
        for corrupt in corruptions:
            with self.subTest(corrupt=corrupt):
                data = copy.deepcopy(EVENT_CATALOG)
                corrupt(data)
                with self.assertRaises(AssertionError):
                    validate_catalog(data)


if __name__ == "__main__":
    unittest.main()
