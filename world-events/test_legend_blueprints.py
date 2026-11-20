"""Legendary forge via the compiled F8 menu and actual save appendix.

Only the depot insertion boundary is controlled here so full/failure results
are deterministic. The vehicle suite exercises the actual insertion routine.
"""
import struct
import unittest

from expedition_catalog import LEGEND_RECIPES
from legend_machines import MODELS
from test_expedition_native import (
    CASH, E, HOURS, SAVE_BYTES, UC_HOOK_CODE, UC_X86_REG_EAX, UC_X86_REG_ESP,
    advance, invoke, pump_ex, r, ready, ret, route, state, tp, visit, w,
)


def wallet(u):
    return tuple(r(u, address) for address in CASH)


def record_progress(u, model, amount):
    if model == 2:
        w(u, state(u) + 20, amount)
        return
    # Historical visits in the prior year, with no pending annual dialogue.
    for index in range(amount):
        record = visit(u, index)
        w(u, record, 1)
        w(u, record + 8, 1)
        if model == 1:
            w(u, record + 4, 1)
        elif model == 3:
            w(u, record + 20, 1 + index % 2)


def forge(u, model, confirm=0):
    return route(u, [3, 2, 1, 3, model, confirm, 3])


def building_state(u, ident, value):
    w(u, tp(1) + 0x53000 + (ident - 1) * 0x300 + 8, value)


def depot(u, results):
    calls = []
    pc = int(E['legend_machines']['give_legend'], 16)

    def insert(uc, pc, size, ctx):
        sp = uc.reg_read(UC_X86_REG_ESP)
        calls.append((r(uc, sp + 4), r(uc, sp + 8)))
        uc.reg_write(UC_X86_REG_EAX, results.pop(0))
        ret(uc, 8)

    u.hook_add(UC_HOOK_CODE, insert, begin=pc, end=pc)
    return calls


class LegendBlueprints(unittest.TestCase):
    def test_inspect_before_unlock_and_produce_each_model_via_f8(self):
        for index, (recipe, model) in enumerate(zip(LEGEND_RECIPES, MODELS)):
            with self.subTest(model=recipe['name']):
                u = ready()
                w(u, HOURS, 400 * 24)
                before = wallet(u)
                record_progress(u, index, recipe['required'] - 1)
                forge(u, index, -1)
                self.assertEqual(wallet(u), before)
                self.assertEqual(r(u, state(u) + 328), 0)
                speech = [body for title, body in u.data['texts'] if title == model['name']]
                self.assertTrue(any(f"HP {model['hp']}" in body for body in speech))
                self.assertTrue(any(f"{recipe['required'] - 1}/{recipe['required']}" in body
                                    and recipe['condition'] in body for body in speech))
                self.assertIn(6 + index, u.data['art_scenes'])
                self.assertTrue(all(len(rows) <= 5 for rows in u.data['selections']))
                record_progress(u, index, recipe['required'])
                forge(u, index, 1)
                self.assertEqual(wallet(u), before)
                self.assertEqual(r(u, state(u) + 328), 0)
                forge(u, index)
                self.assertEqual(r(u, state(u) + 328), 4 + index)
                self.assertTrue(r(u, state(u) + 12) & (8 << index))
                self.assertEqual(r(u, state(u) + 332), 400 + recipe['days'])
                paid = tuple(value - recipe[key] for value, key in zip(before, ('gold', 'iron', 'oil')))
                self.assertEqual(wallet(u), paid)
                self.assertFalse(invoke(u, 'we_test_ex_recipe', 3 + index))
                self.assertEqual(wallet(u), paid)
                calls = depot(u, [2, 0, 1])
                advance(u, recipe['days'] - 1)
                self.assertFalse(pump_ex(u))
                for pending in (True, True, False):
                    advance(u, 1)
                    self.assertTrue(pump_ex(u))
                    self.assertEqual(r(u, state(u) + 328), 4 + index if pending else 0)
                    self.assertFalse(pump_ex(u))
                    self.assertEqual(wallet(u), paid)
                self.assertEqual(calls, [(tp(1), index)] * 3)
                self.assertEqual(u.data['art_scenes'][-1], 6 + index)
                self.assertEqual(sum(title == '전설 설계도 해금' for title, body in u.data['texts']), 1)

    def test_resources_and_finished_buildings(self):
        for index in (0, 3):
            u = ready()
            recipe = LEGEND_RECIPES[index]
            r_id = 3 + index
            w(u, state(u) + 12, 127)
            for i, key in enumerate(('gold', 'iron', 'oil')):
                w(u, CASH[i], recipe[key] - 1)
                before = wallet(u)
                self.assertFalse(invoke(u, 'we_test_ex_recipe', r_id))
                self.assertEqual(wallet(u), before)
                w(u, CASH[i], recipe[key])
            building_state(u, recipe['factory'], 2)
            self.assertFalse(invoke(u, 'we_test_ex_recipe', r_id))
            building_state(u, recipe['factory'], 1)
            for research in (17, 18):
                building_state(u, research, 2)
            self.assertFalse(invoke(u, 'we_test_ex_recipe', r_id))
            building_state(u, 17, 1)
            self.assertTrue(invoke(u, 'we_test_ex_recipe', r_id))
            self.assertEqual(wallet(u), (0, 0, 0))
        for bad_id in (7, 0xffffffff):
            self.assertFalse(invoke(u, 'we_test_ex_recipe', bad_id))

    def test_saved_legacy_progress_unlocks_after_loading_and_keeps_paid_order(self):
        from test_expedition_save import load, ready_save, save

        u = ready_save()
        w(u, HOURS, 400 * 24)
        for index, recipe in enumerate(LEGEND_RECIPES):
            record_progress(u, index, recipe['required'])
        w(u, state(u) + 12, 7)
        self.assertTrue(save(u))
        load(u)
        self.assertEqual(r(u, state(u) + 12), 7)
        forge(u, 3)
        self.assertEqual(r(u, state(u) + 12), 127)
        self.assertEqual(r(u, state(u) + 328), 7)
        paid = wallet(u)
        expected = bytes(u.mem_read(state(u), SAVE_BYTES))
        self.assertTrue(save(u))
        raw = bytes(u.files['data']['Steel0.Sav'])
        footer = struct.unpack('<8I', raw[-32:])
        self.assertEqual(footer[3], 340)
        self.assertEqual(raw[footer[4]:-32], expected)
        load(u)
        self.assertEqual(bytes(u.mem_read(state(u), SAVE_BYTES)), expected)
        calls = depot(u, [1])
        advance(u, LEGEND_RECIPES[3]['days'])
        self.assertTrue(pump_ex(u))
        self.assertFalse(pump_ex(u))
        self.assertEqual(calls, [(tp(1), 3)])
        self.assertEqual(wallet(u), paid)


if __name__ == '__main__':
    unittest.main()
