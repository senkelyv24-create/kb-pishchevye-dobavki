import unittest

from kb.engine import consult, get_additive, search


class SearchTests(unittest.TestCase):
    def test_exact_code_cyrillic_e(self):
        result = search("Е102")
        self.assertEqual(result["items"][0]["code"], "E102")
        self.assertEqual(result["items"][0]["reason"], "точный индекс")

    def test_soda_alias(self):
        result = search("сода")
        self.assertEqual(result["items"][0]["code"], "E500")

    def test_stevia_keeps_two_objects(self):
        codes = [item["code"] for item in search("стевия", per_page=10)["items"]]
        self.assertIn("E960", codes)
        self.assertIn("STEVIA-LEAF", codes)

    def test_prefix_carotenoids(self):
        codes = [item["code"] for item in search("E160", per_page=10)["items"]]
        self.assertEqual(codes[0], "E160a")

    def test_group_and_excluded_filters(self):
        result = search("", "preservative", "excluded", per_page=20)
        codes = {item["code"] for item in result["items"]}
        self.assertEqual(codes, {"E201"})
        self.assertTrue(all(item["group"] == "preservative" for item in result["items"]))

    def test_glutamate(self):
        self.assertEqual(search("глутамат")["items"][0]["code"], "E621")


class ConsultTests(unittest.TestCase):
    def test_excluded_forbids(self):
        report = consult("E201")
        self.assertEqual(report["verdict"]["level"], "forbid")
        self.assertTrue(any(hit["id"] == "R01" for hit in report["fired"]))

    def test_children_dye_warns(self):
        report = consult("E102, E330")
        codes = {(hit["id"], hit["code"]) for hit in report["fired"]}
        self.assertIn(("R02", "E102"), codes)
        self.assertEqual(report["verdict"]["level"], "warn")

    def test_polyol_threshold(self):
        low = consult("E420", polyol_share="8")
        high = consult("E420", polyol_share="12")
        self.assertTrue(any(hit["id"] == "R06" for hit in low["fired"]))
        self.assertTrue(any(hit["id"] == "R05" for hit in high["fired"]))
        self.assertEqual(high["verdict"]["level"], "warn")

    def test_baby_food_stays_open(self):
        report = consult("E300", category="детское питание")
        self.assertTrue(any(hit["id"] == "R10" for hit in report["fired"]))
        self.assertEqual(report["verdict"]["level"], "check")
        self.assertNotEqual(report["verdict"]["level"], "forbid")

    def test_benzene_only_for_drinks(self):
        drinks = consult("E211, E300", category="напитки")
        meat = consult("E211, E300", category="мясная продукция")
        self.assertTrue(any(hit["id"] == "R13" for hit in drinks["fired"]))
        self.assertFalse(any(hit["id"] == "R13" for hit in meat["fired"]))

    def test_titanium_divergence(self):
        report = consult("E171")
        self.assertTrue(any(hit["id"] == "R12" for hit in report["fired"]))
        self.assertEqual(report["verdict"]["level"], "info")

    def test_unknown_code(self):
        report = consult("E999")
        self.assertEqual(report["unknown"], ["E999"])
        self.assertEqual(report["verdict"]["level"], "check")

    def test_aspartame_label(self):
        report = consult("E951")
        self.assertTrue(any(hit["id"] == "R03" for hit in report["fired"]))

    def test_fact_count(self):
        self.assertGreaterEqual(len(search("", per_page=100)["items"]), 40)
        self.assertEqual(get_additive("e330")["name_ru"], "Лимонная кислота")


if __name__ == "__main__":
    unittest.main()
