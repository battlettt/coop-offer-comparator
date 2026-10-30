"""Core math: gross, deductions, net, take-home, lump sums, moving costs.
Every offer here is a SYNTHETIC EXAMPLE; every figure is an estimate."""

import unittest

from coop_compare import calc
from coop_compare.calc import (
    annual_income_tax, bracket_tax, compute_offer, money, round2,
)
from coop_compare.tax_tables import EI, FEDERAL, PENSION, PROVINCES, QPIP, WEEKS_PER_MONTH

from .helpers import norm


class GrossPay(unittest.TestCase):
    def test_hourly_gross_is_rate_times_hours_times_weeks(self):
        r = compute_offer(norm(hourly_rate=25.0, hours_per_week=40, term_weeks=16))
        self.assertEqual(r["gross_term"], 25 * 40 * 16)

    def test_salary_gross_is_prorated_by_weeks_over_52(self):
        o = norm(hourly_rate=None, hours_per_week=None, annual_salary=52000, term_weeks=16)
        r = compute_offer(o)
        self.assertAlmostEqual(r["gross_term"], 16000.0, places=9)
        self.assertEqual(r["pay_style"], "salary")

    def test_salary_and_hourly_agree_when_equivalent(self):
        h = compute_offer(norm(hourly_rate=25.0, hours_per_week=40, term_weeks=16))
        s = compute_offer(norm(hourly_rate=None, hours_per_week=None, annual_salary=25 * 40 * 52, term_weeks=16))
        self.assertAlmostEqual(h["takehome_month"], s["takehome_month"], places=6)

    def test_term_months_uses_4_333_weeks_per_month(self):
        r = compute_offer(norm(term_weeks=16))
        self.assertEqual(WEEKS_PER_MONTH, 4.333)
        self.assertAlmostEqual(r["term_months"], 16 / 4.333, places=12)
        self.assertAlmostEqual(r["gross_month"], r["gross_term"] / (16 / 4.333), places=9)

    def test_whole_term_money_comes_from_weeks_not_rounded_months(self):
        # 17 weeks = 3.923 months. Rounding to 4 months would overstate living costs.
        r = compute_offer(norm(term_weeks=17))
        self.assertAlmostEqual(r["living_term"], r["living_month"] * 17 / 4.333, places=9)
        self.assertNotAlmostEqual(r["living_term"], r["living_month"] * 4, places=2)

    def test_any_positive_whole_term_length_works(self):
        for weeks in (1, 8, 12, 16, 24, 52):
            r = compute_offer(norm(term_weeks=weeks))
            self.assertGreater(r["gross_term"], 0)


class IncomeTax(unittest.TestCase):
    def test_bracket_tax_only_taxes_each_slice_at_its_rate(self):
        b = [(10000.0, 0.10), (20000.0, 0.20), (None, 0.30)]
        self.assertAlmostEqual(bracket_tax(5000, b), 500)
        self.assertAlmostEqual(bracket_tax(15000, b), 1000 + 1000)
        self.assertAlmostEqual(bracket_tax(25000, b), 1000 + 2000 + 1500)
        self.assertEqual(bracket_tax(0, b), 0)

    def test_moving_into_a_higher_bracket_only_taxes_the_extra_more(self):
        b = FEDERAL["brackets"]
        limit = b[0][0]
        below = bracket_tax(limit, b)
        above = bracket_tax(limit + 100, b)
        self.assertAlmostEqual(above - below, 100 * b[1][1], places=6)

    def test_basic_personal_amount_means_low_income_pays_no_income_tax(self):
        fed, prov = annual_income_tax(12000, "Ontario")
        self.assertEqual((fed, prov), (0.0, 0.0))

    def test_federal_tax_formula(self):
        fed, _ = annual_income_tax(54600, "Ontario")
        expected = 54600 * 0.14 - FEDERAL["basic_personal_amount"] * 0.14
        self.assertAlmostEqual(fed, expected, places=6)

    def test_quebec_gets_federal_abatement(self):
        on_fed, _ = annual_income_tax(60000, "Ontario")
        qc_fed, _ = annual_income_tax(60000, "Quebec")
        self.assertAlmostEqual(qc_fed, on_fed * (1 - 0.165), places=6)

    def test_each_supported_province_has_its_own_tax(self):
        taxes = {p: annual_income_tax(60000, p)[1] for p in PROVINCES}
        self.assertEqual(len(set(round(t, 2) for t in taxes.values())), 4)

    def test_tax_is_annualised_then_prorated_back_to_the_term(self):
        o = norm(hourly_rate=28.0, hours_per_week=37.5, term_weeks=16)
        r = compute_offer(o)
        self.assertAlmostEqual(r["annualised_income"], 16800 * 52 / 16, places=6)
        fed, prov = annual_income_tax(r["annualised_income"], "Ontario")
        self.assertAlmostEqual(r["federal_tax"], fed * 16 / 52, places=9)
        self.assertAlmostEqual(r["provincial_tax"], prov * 16 / 52, places=9)

    def test_annualising_gives_more_tax_than_taxing_four_months_as_a_year(self):
        # Taxing only $16,800 as if it were a whole year mostly hides under the
        # basic personal amount; payroll annualises, so withholding is higher.
        r = compute_offer(norm(hourly_rate=28.0, hours_per_week=37.5, term_weeks=16))
        naive_fed, naive_prov = annual_income_tax(r["gross_term"], "Ontario")
        self.assertGreater(r["federal_tax"] + r["provincial_tax"], naive_fed + naive_prov)

    def test_marginal_rate_exceeds_average_rate(self):
        r = compute_offer(norm(hourly_rate=28.0, hours_per_week=37.5))
        self.assertGreater(r["marginal_tax_rate"], r["average_income_tax_rate"])
        self.assertAlmostEqual(r["marginal_tax_rate"], 0.14 + 0.0915, places=9)


class CppEiQpip(unittest.TestCase):
    def test_cpp_on_a_short_term_uses_a_prorated_exemption(self):
        r = compute_offer(norm(hourly_rate=25.0, hours_per_week=40, term_weeks=16))
        expected = (16000 - 3500 * 16 / 52) * 0.0595
        self.assertAlmostEqual(r["pension"], expected, places=9)
        self.assertEqual(r["pension_name"], "CPP")

    def test_a_four_month_term_pays_far_less_than_a_full_year_maximum(self):
        r = compute_offer(norm(hourly_rate=25.0, hours_per_week=40, term_weeks=16))
        max_cpp = (PENSION["ympe"] - PENSION["basic_exemption"]) * PENSION["cpp_rate"]
        self.assertLess(r["pension"], max_cpp / 2)
        self.assertLess(r["ei"], EI["max_insurable"] * EI["rate"] / 2)

    def test_cpp_and_ei_are_capped_at_the_annual_maximum(self):
        o = norm(hourly_rate=None, hours_per_week=None, annual_salary=240000, term_weeks=52)
        r = compute_offer(o)
        self.assertAlmostEqual(r["pension"], (74600 - 3500) * 0.0595, places=9)
        self.assertAlmostEqual(r["ei"], 68900 * 0.0163, places=9)

    def test_high_paid_short_term_still_capped(self):
        # $200/h for 16 weeks = $128,000 gross, above both annual ceilings.
        r = compute_offer(norm(hourly_rate=200.0, hours_per_week=40, term_weeks=16))
        self.assertAlmostEqual(r["ei"], EI["max_insurable"] * EI["rate"], places=9)
        self.assertAlmostEqual(r["pension"], (PENSION["ympe"] - PENSION["basic_exemption"]) * PENSION["cpp_rate"], places=9)

    def test_quebec_uses_qpp_quebec_ei_rate_and_qpip(self):
        o = norm(city="Montreal", rent_per_month=1500)
        r = compute_offer(o)
        g = r["gross_term"]
        self.assertEqual(r["province"], "Quebec")
        self.assertEqual(r["pension_name"], "QPP")
        self.assertAlmostEqual(r["pension"], (g - 3500 * 16 / 52) * 0.064, places=9)
        self.assertAlmostEqual(r["ei"], g * 0.0130, places=9)
        self.assertAlmostEqual(r["qpip"], g * QPIP["rate"], places=9)

    def test_outside_quebec_there_is_no_qpip(self):
        self.assertEqual(compute_offer(norm())["qpip"], 0.0)

    def test_tiny_term_never_has_negative_cpp(self):
        r = compute_offer(norm(hourly_rate=1.0, hours_per_week=1, term_weeks=1))
        self.assertEqual(r["pension"], 0.0)


class NetAndTakeHome(unittest.TestCase):
    def setUp(self):
        self.o = norm(hourly_rate=28.0, hours_per_week=37.5, term_weeks=16, rent_per_month=2000,
                      other_monthly=[{"name": "phone", "amount": 45}, {"name": "food", "amount": 380}],
                      moving_costs=[{"name": "van", "amount": 350}, {"name": "deposit", "amount": 150}],
                      lump_sums=[{"name": "signing bonus", "amount": 1000}])
        self.r = compute_offer(self.o)

    def test_each_deduction_is_its_own_line_and_they_add_up(self):
        r = self.r
        parts = r["federal_tax"] + r["provincial_tax"] + r["pension"] + r["ei"] + r["qpip"]
        self.assertAlmostEqual(r["deductions_total"], parts, places=9)
        self.assertAlmostEqual(r["effective_deduction_rate"], r["deductions_total"] / r["gross_term"], places=12)

    def test_net_is_gross_minus_deductions(self):
        self.assertAlmostEqual(self.r["net_term"], self.r["gross_term"] - self.r["deductions_total"], places=9)

    def test_living_costs(self):
        r = self.r
        self.assertEqual(r["living_month"], 2000 + 100 + 45 + 380)
        self.assertAlmostEqual(r["living_term"], r["living_month"] * 16 / 4.333, places=9)

    def test_moving_costs_shown_separately_and_amortised(self):
        r = self.r
        self.assertEqual(r["moving_total"], 500)
        self.assertAlmostEqual(r["moving_per_month"], 500 / (16 / 4.333), places=9)

    def test_lump_sum_taxed_by_bonus_method_and_kept_separate(self):
        r = self.r
        fed, prov = annual_income_tax(r["annualised_income"], "Ontario")
        f2, p2 = annual_income_tax(r["annualised_income"] + 1000, "Ontario")
        self.assertAlmostEqual(r["lump_tax"], (f2 + p2) - (fed + prov), places=9)
        self.assertAlmostEqual(r["lump_net"], 1000 - r["lump_tax"], places=9)
        # never folded into monthly gross or net pay
        self.assertEqual(r["gross_term"], 28 * 37.5 * 16)
        self.assertAlmostEqual(r["net_month"], r["net_term"] / r["term_months"], places=9)

    def test_untaxed_lump_sum_has_no_tax(self):
        r = compute_offer(norm(lump_sums=[{"name": "relocation", "amount": 1500, "taxable": False}]))
        self.assertEqual(r["lump_tax"], 0.0)
        self.assertEqual(r["lump_net"], 1500)

    def test_takehome_whole_term_formula(self):
        r = self.r
        expected = r["net_term"] - r["living_term"] - r["moving_total"] + r["lump_net"]
        self.assertAlmostEqual(r["takehome_term"], expected, places=9)

    def test_takehome_month_and_week(self):
        r = self.r
        self.assertAlmostEqual(r["takehome_month"], r["takehome_term"] / (16 / 4.333), places=9)
        self.assertAlmostEqual(r["takehome_week"], r["takehome_term"] / 16, places=9)

    def test_takehome_month_two_ways(self):
        # cross-check: per-month pieces rebuild the same monthly take-home
        r = self.r
        m = r["term_months"]
        alt = r["net_month"] - r["living_month"] - r["moving_total"] / m + r["lump_net"] / m
        self.assertAlmostEqual(alt, r["takehome_month"], places=9)

    def test_moving_costs_lower_takehome_by_exactly_their_total(self):
        without = compute_offer(norm(hourly_rate=28.0, hours_per_week=37.5, rent_per_month=2000))
        with_ = compute_offer(norm(hourly_rate=28.0, hours_per_week=37.5, rent_per_month=2000,
                                   moving_costs=[{"name": "van", "amount": 500}]))
        self.assertAlmostEqual(without["takehome_term"] - with_["takehome_term"], 500, places=9)

    def test_driving_commute_cost(self):
        o = norm(arrangement="onsite", commute={"mode": "driving", "km_per_day": 30, "cost_per_km": 0.35,
                                                "parking_per_month": 80, "days_per_week": 5})
        self.assertAlmostEqual(compute_offer(o)["commute_month"], 30 * 0.35 * 5 * 4.333 + 80, places=9)

    def test_remote_no_commute_costs_nothing(self):
        o = norm(arrangement="remote", commute={"mode": "none"})
        self.assertEqual(compute_offer(o)["commute_month"], 0.0)

    def test_hand_checked_sample_numbers(self):
        # SYNTHETIC EXAMPLE Toronto offer from samples/offers.json, checked by hand.
        o = norm(label="Toronto", city="Toronto", hourly_rate=28.0, hours_per_week=37.5, arrangement="hybrid",
                 rent_per_month=None, commute={"mode": "transit"},
                 other_monthly=[{"name": "phone plan", "amount": 45}, {"name": "groceries", "amount": 380}],
                 moving_costs=[{"name": "moving van", "amount": 350}],
                 lump_sums=[{"name": "signing bonus", "amount": 1000}])
        r = compute_offer(o)
        self.assertEqual(round2(r["federal_tax"]), 1643.30)
        self.assertEqual(round2(r["provincial_tax"]), 655.52)
        self.assertEqual(round2(r["pension"]), 935.52)
        self.assertEqual(round2(r["ei"]), 273.84)
        self.assertEqual(round2(r["lump_tax"]), 231.50)
        self.assertEqual(round2(r["takehome_month"]), 677.93)


class Formatting(unittest.TestCase):
    def test_round2_is_half_up(self):
        self.assertEqual(round2(0.125), 0.13)
        self.assertEqual(round2(2.675), 2.68)  # Python's round() would give 2.67
        self.assertEqual(round2(-1.005), -1.0)

    def test_money(self):
        self.assertEqual(money(1234567.891), "$1,234,567.89")
        self.assertEqual(money(0), "$0.00")
        self.assertEqual(money(-962.966), "-$962.97")
        self.assertEqual(money(999.999), "$1,000.00")

    def test_add_up_is_a_plain_left_to_right_loop(self):
        vals = [0.1] * 10
        total = 0.0
        for v in vals:
            total += v
        self.assertEqual(calc.add_up(vals), total)


if __name__ == "__main__":
    unittest.main()
