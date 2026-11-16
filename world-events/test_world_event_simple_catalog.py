"""Pure data checks for the single-goal catalogue, not a native engine test."""
import copy
import unittest

from world_event_catalog import EVENT_CATALOG as LEGACY
from world_event_simple_catalog import SIMPLE_EVENT_CATALOG as EVENTS, GOAL_TYPES

ACTION_KEYS = {"cost_gold", "cost_iron", "cost_oil", "cost_item_id", "cost_item_count",
               "cost_machine_id", "reward_gold", "reward_iron", "reward_oil",
               "reward_item_id", "reward_item_count", "reward_machine_id"}


def validate(events):
    assert len(events) == len(LEGACY) == 38
    assert [e["id"] for e in events] == list(range(38))
    for old, event in zip(LEGACY, events):
        assert event["key"] == old["key"]
        assert event["category"] == old["category"]
        assert event["early"] is True
        assert all(event[name] == 0 for name in ("required_class", "required_facility", "country", "min_completed"))
        assert event["requires_event"] == event["conditions"] == []
        assert len(event["stages"]) == 1
        stage = event["stages"][0]
        assert stage["min_completed"] == 0 and len(stage["choices"]) == 1
        choice = stage["choices"][0]
        assert choice["next_stage"] == -1
        actions = choice["actions"]
        assert set(actions) <= ACTION_KEYS
        assert all(type(value) is int and value > 0 for value in actions.values())
        assert actions.get("reward_gold", 0) <= 340000
        assert actions.get("reward_iron", 0) <= 100 and actions.get("reward_oil", 0) <= 100
        costs = [name for name in ("cost_gold", "cost_iron", "cost_oil", "cost_item_id", "cost_machine_id") if name in actions]
        assert len(costs) <= 1
        goal = event["goal"]
        assert set(goal) == {"type", "target_role", "building_id", "target_fixed"}
        assert goal["type"] in GOAL_TYPES
        assert goal["target_role"] in ("any", "near", "far", "home", "airport", "capital")
        assert goal["target_fixed"] in (0, 1, 40)
        assert event["repeat_days"] in (0, 60, 90)
        if goal["type"] == "supply":
            assert len(costs) == 1 and costs[0] in ("cost_gold", "cost_iron", "cost_oil")
            assert goal["target_role"] == "any"
            assert actions.get("cost_gold", 0) <= 45000
            assert actions.get("cost_iron", 0) <= 40 and actions.get("cost_oil", 0) <= 20
        elif goal["type"] == "item":
            assert actions.get("cost_item_id") == 1 and actions.get("cost_item_count") == 1
            assert goal["target_role"] == "any"
        elif goal["type"] == "equipment":
            assert event["id"] in (36, 37)
            assert actions.get("cost_machine_id") == {36: 6, 37: 1}[event["id"]]
            assert goal["target_role"] == "any" and event["repeat_days"] == 90
        elif goal["type"] == "build":
            assert goal["building_id"] in (6, 7, 17, 19)
            assert event["repeat_days"] == 0 and not costs
            assert goal["target_role"] == "home" and goal["target_fixed"] == 1
        else:
            assert not costs and goal["target_role"] != "any"
        if goal["type"] != "build":
            assert goal["building_id"] == 0
        if "reward_machine_id" in actions:
            assert event["id"] == 31 and actions["reward_machine_id"] == 24
            assert event["repeat_days"] == 0
        for text in (event["title"], stage["title"], stage["text"], choice["label"], choice["result"]):
            assert text and "\0" not in text and len(text.encode("cp949")) < 512
        assert len(choice["label"].encode("cp949")) < 128


class SimpleCatalogTests(unittest.TestCase):
    def test_all_thirty_eight_single_objective_contracts(self):
        validate(EVENTS)
        self.assertEqual({e["goal"]["type"] for e in EVENTS}, set(GOAL_TYPES))

    def test_no_job_army_routes_prerequisites_or_manual_claim_actions(self):
        forbidden = {"require_job", "require_army_type", "hire_class", "hire_count",
                     "delivery_legs", "target_roles", "battle_profile", "project_part", "manual_claim"}
        for event in EVENTS:
            self.assertFalse(forbidden & event["stages"][0]["choices"][0]["actions"].keys())

    def test_natural_occupation_instead_of_arena(self):
        for ident in range(24, 30):
            self.assertEqual(EVENTS[ident]["goal"]["type"], "occupy")
            self.assertEqual(EVENTS[ident]["repeat_days"], 90)
        self.assertEqual(EVENTS[32]["goal"], dict(type="occupy", target_role="capital", building_id=0, target_fixed=40))

    def test_global_spare_equipment_and_single_aircraft_reward(self):
        for ident in (36, 37):
            goal = EVENTS[ident]["goal"]
            self.assertEqual(goal["type"], "equipment")
            self.assertEqual(goal["target_role"], "any")
        self.assertEqual(EVENTS[31]["goal"]["type"], "visit")
        self.assertEqual(EVENTS[31]["goal"]["target_role"], "airport")
        self.assertEqual(EVENTS[31]["stages"][0]["choices"][0]["actions"]["reward_machine_id"], 24)

    def test_legacy_lists_are_not_mutated_or_shared(self):
        before = copy.deepcopy(LEGACY)
        clone = copy.deepcopy(EVENTS)
        clone[0]["stages"][0]["choices"][0]["actions"]["cost_iron"] = 1
        self.assertEqual(LEGACY, before)
        self.assertGreater(len(LEGACY[30]["stages"]), 1)
        self.assertEqual(LEGACY[35]["stages"][2]["min_completed"], 37)
        for old, new in zip(LEGACY, EVENTS):
            self.assertIsNot(old["stages"], new["stages"])
            self.assertIsNot(old["stages"][0]["choices"], new["stages"][0]["choices"])

    def test_bad_hidden_requirements_and_multiple_costs_rejected(self):
        bad = copy.deepcopy(EVENTS)
        bad[0]["stages"][0]["choices"][0]["actions"]["require_job"] = 8
        with self.assertRaises(AssertionError):
            validate(bad)
        bad = copy.deepcopy(EVENTS)
        bad[0]["stages"][0]["choices"][0]["actions"]["cost_oil"] = 1
        with self.assertRaises(AssertionError):
            validate(bad)
        bad = copy.deepcopy(EVENTS)
        bad[3]["repeat_days"] = 60
        with self.assertRaises(AssertionError):
            validate(bad)


if __name__ == "__main__":
    unittest.main()
