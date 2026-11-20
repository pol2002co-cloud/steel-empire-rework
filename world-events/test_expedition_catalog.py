"""Single-screen mission data and generated native C layout contract."""
import re,unittest
from expedition_catalog import *
from world_events_patch import c_string


class CatalogTests(unittest.TestCase):
    def test_mission_contract(self):
        self.assertEqual(len(MISSIONS),7)
        self.assertEqual([(m['days'],m['cost'],m['gold'],m['xp'],m['job']) for m in MISSIONS],
            [(30,10000,45000,400,0),(30,20000,80000,200,11),(30,30000,120000,180,10),
             (30,15000,60000,400,8),(7,5000,15000,150,12),(15,10000,30000,250,11),(30,20000,60000,450,8)])
        for mission in MISSIONS:
            self.assertEqual(set(mission),{'name','text','days','cost','gold','xp','job'})
            self.assertLess(mission['cost'],mission['gold'])
            self.assertNotIn('required',mission)
            self.assertLessEqual(len(mission['name'].encode('cp949')),48)
            self.assertLessEqual(len(mission['text'].encode('cp949')),230)

    def test_recipes_use_existing_native_machine_ids_and_factories(self):
        self.assertEqual([(r['machine'],r['gold'],r['iron'],r['oil'],r['days'],r['factory']) for r in RECIPES],
                         [(6,20000,20,10,7,7),(1,240000,30,40,10,10),(24,400000,80,60,15,10)])
        for recipe in RECIPES:
            self.assertEqual(set(recipe),{'name','machine','gold','iron','oil','days','factory'})
            self.assertGreater(recipe['days'],0)
            self.assertNotIn(recipe['machine'],range(17,22))

    def test_legend_recipes_use_model_order_and_earned_progress(self):
        from legend_machines import MODELS
        self.assertEqual([r['name'] for r in LEGEND_RECIPES],[m['name'] for m in MODELS])
        self.assertEqual([(r['required'],r['gold'],r['iron'],r['oil'],r['days'],r['factory']) for r in LEGEND_RECIPES],
                    [(2,700000,200,80,18,9),(1,900000,240,120,24,9),(3,650000,120,160,18,12),(2,1000000,180,220,24,12)])
        header=generate_catalog_header(c_string)
        self.assertIn('#define EX_RECIPE_COUNT 7u',header)
        self.assertIn('#define EX_STANDARD_RECIPES 3u',header)
        for recipe,model in zip(LEGEND_RECIPES,MODELS):
            self.assertIn(c_string(recipe['condition']),header)
            self.assertIn(c_string('HP %d · 방어 %d · 사거리 %d · 공격 대인 %d / 대공 %d / 대기갑 %d / 대벽 %d'%(
                    model['hp'],model['defense'],model['reach'],*model['attack'])),header)

    def test_four_real_ruins_and_passive_artifacts(self):
        self.assertEqual(tuple(town for _,town in RUINS),(20,41,52,0))
        self.assertEqual(len(ARTIFACTS),2)
        self.assertEqual((COMPASS_SUCCESS,SEAL_BONUS_GOLD,SUCCESS_CAP,BONUS_GOLD_CAP),(5,10,95,50))
        self.assertEqual((INITIAL_SLOTS,MAX_HEROES,MAX_GENERICS),(4,3,20))
        self.assertEqual((BLESS_GOLD,BLESS_IRON,BLESS_OIL,BLESS_XP,PRESERVE_BONUS,DEEP_GUARANTEE),(20000,20,10,120,50,3))

    def test_cp949_ascii_header_and_field_order(self):
        header=generate_catalog_header(c_string)
        header.encode('ascii')
        self.assertEqual(header,generate_catalog_header(c_string))
        self.assertEqual(header.count('static const EXMission '),1)
        self.assertEqual(header.count('static const EXRecipe '),1)
        self.assertEqual(header.count('static const EXRuin '),1)
        self.assertIn('30u,10000u,45000u,400u,0u}',header)
        self.assertIn('6u,20000u,20u,10u,7u,7u}',header)
        literals=re.findall(r'"((?:\\.|[^"\\])*)"',header)
        decoded=[bytes(int(o,8) for o in re.findall(r'\\([0-7]{3})',s)).decode('cp949') for s in literals]
        self.assertIn(MISSIONS[0]['name'],decoded)
        self.assertIn(RUINS[3][0],decoded)
        self.assertIn(ARTIFACTS[1][1],decoded)


if __name__=='__main__':unittest.main()
