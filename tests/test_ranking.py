"""Ranking, the about-tied rule, break-even, and rent sensitivity.
All offers are SYNTHETIC EXAMPLES; all figures are estimates."""

import unittest

from coop_compare.calc import (
    TIE_THRESHOLD, breakeven, breakeven_text, compare, compute_offer, rank, round2,
    sensitivity, with_pay,
)
from coop_compare.model import load_offers

from .helpers import fixture, norm, norm_many, raw_offer, samples


def results_for(*rents, **kw):
    offers = norm_many(*[raw_offer(label="R" + str(i), rent_per_month=r, **kw) for i, r in enumerate(rents)])
    return offers, [compute_offer(o) for o in offers]


class Ranking(unittest.TestCase):
    def test_ranks_by_monthly_takehome_highest_first(self):
        _, res = results_for(1500, 900, 1200)
        rows = rank(res)
        self.assertEqual([r["label"] for r in rows], ["R1", "R2", "R0"])
        self.assertEqual([r["rank"] for r in rows], [1, 2, 3])

    def test_gap_to_best(self):
        _, res = results_for(1000, 1300)
        rows = rank(res)
        self.assertEqual(rows[0]["gap_to_best_month"], 0)
        self.assertAlmostEqual(rows[1]["gap_to_best_month"], 300, places=6)

    def test_monthly_not_whole_term_decides(self):
        # A 24-week offer has a bigger whole-term total but less per month.
        short = raw_offer(label="short", hourly_rate=30.0, term_weeks=16)
        long_ = raw_offer(label="long", hourly_rate=24.0, term_weeks=24)
        offers = norm_many(short, long_)
        res = [compute_offer(o) for o in offers]
        self.assertGreater(res[1]["takehome_term"], res[0]["takehome_term"])
        self.assertEqual(rank(res)[0]["label"], "short")

    def test_within_25_a_month_is_about_tied(self):
        _, res = results_for(1200, 1210)
        rows = rank(res)
        self.assertTrue(rows[1]["about_tied"])
        self.assertIn("about tied", rows[0]["verdict"])
        self.assertIn("About tied", rows[1]["verdict"])

    def test_exactly_25_is_tied_but_26_is_not(self):
        _, res = results_for(1000, 1025)
        self.assertTrue(rank(res)[1]["about_tied"])
        _, res = results_for(1000, 1026)
        rows = rank(res)
        self.assertFalse(rows[1]["about_tied"])
        self.assertIn("Best monthly take-home", rows[0]["verdict"])
        self.assertEqual(TIE_THRESHOLD, 25)

    def test_tie_fixture(self):
        offers, _ = load_offers(fixture("tied.json"))
        rows = compare(offers)["ranking"]
        self.assertEqual([r["about_tied"] for r in rows], [False, True, False])
        self.assertIn("B (synthetic)", rows[0]["verdict"])

    def test_exact_ties_keep_input_order(self):
        _, res = results_for(1000, 1000)
        self.assertEqual([r["label"] for r in rank(res)], ["R0", "R1"])

    def test_single_offer(self):
        _, res = results_for(1000)
        rows = rank(res)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["verdict"].startswith("Only offer"))


class BreakEven(unittest.TestCase):
    def test_recomputing_at_break_even_rate_matches_target(self):
        offers, _ = load_offers(samples())
        toronto, waterloo = offers
        be = breakeven(waterloo, toronto)
        self.assertTrue(be["reachable"])
        self.assertGreater(be["required_pay"], toronto["hourly_rate"])
        check = compute_offer(with_pay(toronto, be["required_pay"]))["takehome_month"]
        self.assertAlmostEqual(check, be["target_takehome_month"], places=6)
        self.assertEqual(round2(be["required_pay"]), 37.41)

    def test_rounded_up_rate_is_at_least_enough(self):
        offers, _ = load_offers(samples())
        be = breakeven(offers[1], offers[0])
        need = -(-be["required_pay"] * 100 // 1) / 100
        self.assertGreaterEqual(compute_offer(with_pay(offers[0], need))["takehome_month"],
                                be["target_takehome_month"] - 1e-9)

    def test_salary_break_even(self):
        a = raw_offer(label="A", city="Waterloo", rent_per_month=1100)
        b = raw_offer(label="B", city="Vancouver", rent_per_month=None, hourly_rate=None, hours_per_week=None,
                      annual_salary=50000, commute={"mode": "transit"})
        oa, ob = norm_many(a, b)
        be = breakeven(oa, ob)
        self.assertEqual(be["pay_style"], "salary")
        got = compute_offer(with_pay(ob, be["required_pay"]))["takehome_month"]
        self.assertAlmostEqual(got, compute_offer(oa)["takehome_month"], places=5)
        self.assertIn("/year", breakeven_text(be))

    def test_offer_already_ahead_could_pay_less(self):
        offers, _ = load_offers(samples())
        be = breakeven(offers[0], offers[1])  # Waterloo already beats Toronto
        self.assertLess(be["change"], 0)
        self.assertIn("already matches", breakeven_text(be))
        got = compute_offer(with_pay(offers[1], be["required_pay"]))["takehome_month"]
        self.assertAlmostEqual(got, be["target_takehome_month"], places=6)

    def test_same_offer_breaks_even_at_its_own_pay(self):
        o = norm()
        be = breakeven(o, o)
        self.assertAlmostEqual(be["required_pay"], o["hourly_rate"], places=6)

    def test_matches_even_at_zero_pay(self):
        poor = norm(label="poor", rent_per_month=50000)
        cheap = norm(label="cheap", rent_per_month=0)
        be = breakeven(poor, cheap)
        self.assertEqual(be["required_pay"], 0.0)
        self.assertIn("even at zero pay", breakeven_text(be))

    def test_text_mentions_both_rates_and_percent(self):
        offers, _ = load_offers(samples())
        text = breakeven_text(breakeven(offers[1], offers[0]))
        self.assertIn("$37.41/hour instead of $28.00/hour (+33.6%)", text)

    def test_compare_includes_break_even_against_best(self):
        offers, _ = load_offers(fixture("mixed_provinces.json"))
        cmp = compare(offers)
        self.assertEqual(len(cmp["breakeven"]), len(offers) - 1)
        best = cmp["ranking"][0]["label"]
        for be in cmp["breakeven"]:
            self.assertEqual(be["target_label"], best)


class Sensitivity(unittest.TestCase):
    def test_rent_up_and_down_200(self):
        offers, res = results_for(1200, 1500)
        s = sensitivity(offers, res, 0)
        self.assertAlmostEqual(s["rent_up"]["takehome_month"], res[0]["takehome_month"] - 200, places=6)
        self.assertAlmostEqual(s["rent_down"]["takehome_month"], res[0]["takehome_month"] + 200, places=6)
        self.assertEqual(s["rent_up"]["rent"], 1400)
        self.assertEqual(s["rent_down"]["rent"], 1000)

    def test_fragile_ranking_is_flagged(self):
        offers, _ = load_offers({"offers": [raw_offer(label="A", rent_per_month=1200),
                                            raw_offer(label="B", rent_per_month=1300)]})
        cmp = compare(offers)
        a = [s for s in cmp["sensitivity"] if s["label"] == "A"][0]
        self.assertTrue(a["fragile"])
        self.assertEqual(a["rent_up"]["rank"], 2)

    def test_robust_ranking_is_not_flagged(self):
        offers, _ = load_offers(samples())
        self.assertFalse(any(s["fragile"] for s in compare(offers)["sensitivity"]))

    def test_rent_never_goes_below_zero(self):
        offers, res = results_for(100)
        s = sensitivity(offers, res, 0)
        self.assertEqual(s["rent_down"]["rent"], 0.0)


if __name__ == "__main__":
    unittest.main()
