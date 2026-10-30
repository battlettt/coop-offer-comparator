"""Validation and presets. All offers are SYNTHETIC EXAMPLES."""

import unittest

from coop_compare.model import OffersError, format_issues, load_offers, validate
from coop_compare.presets import CITY_PRESETS, PRESET_SOURCE_NOTE, find_preset
from coop_compare.calc import compute_offer

from .helpers import fixture, norm, raw_offer


def codes(raw, level=None):
    _, issues = validate({"offers": [raw] if isinstance(raw, dict) else raw})
    return [i["code"] for i in issues if level is None or i["level"] == level]


class PayStyle(unittest.TestCase):
    def test_both_pay_styles_is_an_error(self):
        self.assertIn("E_BOTH_PAY", codes(raw_offer(annual_salary=50000), "error"))

    def test_neither_pay_style_is_an_error(self):
        self.assertIn("E_NO_PAY", codes(raw_offer(hourly_rate=None, hours_per_week=None), "error"))

    def test_hourly_needs_hours(self):
        self.assertIn("E_MISSING", codes(raw_offer(hours_per_week=None), "error"))

    def test_zero_rate_rejected(self):
        self.assertIn("E_ZERO", codes(raw_offer(hourly_rate=0), "error"))

    def test_hours_over_80_rejected_and_over_60_warned(self):
        self.assertIn("E_RANGE", codes(raw_offer(hours_per_week=81), "error"))
        self.assertIn("W_LONG_HOURS", codes(raw_offer(hours_per_week=65), "warning"))

    def test_text_instead_of_number(self):
        self.assertIn("E_NOT_NUMBER", codes(raw_offer(hourly_rate="25"), "error"))

    def test_boolean_is_not_a_number(self):
        self.assertIn("E_NOT_NUMBER", codes(raw_offer(rent_per_month=True), "error"))


class Money(unittest.TestCase):
    def test_negative_money_rejected_everywhere(self):
        self.assertIn("E_NEGATIVE", codes(raw_offer(rent_per_month=-1), "error"))
        self.assertIn("E_NEGATIVE", codes(raw_offer(commute={"mode": "transit", "transit_pass_per_month": -3}), "error"))
        self.assertIn("E_NEGATIVE", codes(raw_offer(other_monthly=[{"name": "x", "amount": -5}]), "error"))
        self.assertIn("E_NEGATIVE", codes(raw_offer(moving_costs=[{"name": "x", "amount": -5}]), "error"))
        self.assertIn("E_NEGATIVE", codes(raw_offer(lump_sums=[{"name": "x", "amount": -5}]), "error"))

    def test_nan_and_infinity_rejected(self):
        self.assertIn("E_NOT_NUMBER", codes(raw_offer(rent_per_month=float("nan")), "error"))
        self.assertIn("E_NOT_NUMBER", codes(raw_offer(rent_per_month=float("inf")), "error"))

    def test_absurd_amounts_are_typos_not_reports(self):
        self.assertIn("E_RANGE", codes(raw_offer(hourly_rate=1e308), "error"))
        self.assertIn("E_RANGE", codes(raw_offer(rent_per_month=100000001), "error"))
        self.assertEqual(codes(raw_offer(rent_per_month=100000000)), [])

    def test_integer_too_big_for_a_float_is_an_error_not_a_crash(self):
        self.assertIn("E_TERM", codes(raw_offer(term_weeks=10 ** 400), "error"))
        self.assertIn("E_NOT_NUMBER", codes(raw_offer(rent_per_month=10 ** 400), "error"))

    def test_item_needs_a_name(self):
        self.assertIn("E_MISSING", codes(raw_offer(other_monthly=[{"amount": 5}]), "error"))

    def test_item_list_must_be_a_list(self):
        self.assertIn("E_NOT_LIST", codes(raw_offer(moving_costs={"van": 300}), "error"))

    def test_taxable_must_be_boolean(self):
        self.assertIn("E_NOT_BOOL", codes(raw_offer(lump_sums=[{"name": "b", "amount": 1, "taxable": "no"}]), "error"))


class TermAndArrangement(unittest.TestCase):
    def test_term_must_be_positive_whole_number(self):
        for bad in (0, -16, 15.5, "16"):
            self.assertIn("E_TERM", codes(raw_offer(term_weeks=bad), "error"), bad)
        self.assertIn("E_MISSING", codes(raw_offer(term_weeks=None), "error"))

    def test_integer_valued_float_term_accepted(self):
        self.assertEqual(norm(term_weeks=16.0)["term_weeks"], 16)

    def test_arrangement_checked(self):
        self.assertIn("E_ARRANGEMENT", codes(raw_offer(arrangement="office"), "error"))
        self.assertIn("E_MISSING", codes(raw_offer(arrangement=None), "error"))


class Commute(unittest.TestCase):
    def test_onsite_with_no_commute_is_an_error(self):
        self.assertIn("E_ONSITE_NO_COMMUTE", codes(raw_offer(commute={"mode": "none"}), "error"))

    def test_hybrid_with_no_commute_is_a_warning(self):
        c = codes(raw_offer(arrangement="hybrid", commute={"mode": "none"}))
        self.assertIn("W_HYBRID_NO_COMMUTE", c)
        self.assertNotIn("E_ONSITE_NO_COMMUTE", c)

    def test_remote_with_transit_pass_is_a_warning_not_an_error(self):
        offers, issues = validate({"offers": [raw_offer(arrangement="remote")]})
        self.assertEqual(len(offers), 1)
        self.assertEqual([i["code"] for i in issues], ["W_REMOTE_COMMUTE"])

    def test_remote_without_commute_defaults_to_none(self):
        self.assertEqual(norm(arrangement="remote", commute=None)["commute_mode"], "none")

    def test_onsite_without_commute_is_missing(self):
        self.assertIn("E_MISSING", codes(raw_offer(commute=None), "error"))

    def test_bad_mode(self):
        self.assertIn("E_COMMUTE_MODE", codes(raw_offer(commute={"mode": "bike"}), "error"))

    def test_driving_needs_km_and_cost(self):
        c = codes(raw_offer(commute={"mode": "driving"}), "error")
        self.assertEqual(c.count("E_MISSING"), 2)

    def test_driving_assumptions_are_warned_about(self):
        o = raw_offer(commute={"mode": "driving", "km_per_day": 10, "cost_per_km": 0.3})
        self.assertEqual(codes(o, "warning"), ["W_ASSUMED", "W_ASSUMED"])
        n = norm(commute={"mode": "driving", "km_per_day": 10, "cost_per_km": 0.3})
        self.assertEqual((n["parking_per_month"], n["days_per_week"]), (0.0, 5.0))
        self.assertEqual((n["parking_source"], n["days_source"]), ("assumed", "assumed"))

    def test_driving_days_range(self):
        o = raw_offer(commute={"mode": "driving", "km_per_day": 10, "cost_per_km": 0.3,
                               "parking_per_month": 0, "days_per_week": 8})
        self.assertIn("E_RANGE", codes(o, "error"))

    def test_fields_for_another_mode_are_warned(self):
        o = raw_offer(commute={"mode": "transit", "transit_pass_per_month": 100, "km_per_day": 5})
        self.assertEqual(codes(o), ["W_IGNORED_FIELD"])


class FileLevel(unittest.TestCase):
    def test_unknown_fields_are_warnings(self):
        self.assertEqual(codes(raw_offer(colour="blue")), ["W_UNKNOWN_FIELD"])
        _, issues = validate({"offers": [raw_offer()], "extra": 1})
        self.assertEqual([i["code"] for i in issues], ["W_UNKNOWN_FIELD"])

    def test_underscore_keys_are_comments(self):
        self.assertEqual(codes(raw_offer(_comment="hi")), [])

    def test_missing_or_empty_offers(self):
        self.assertEqual([i["code"] for i in validate({})[1]], ["E_NO_OFFERS"])
        self.assertEqual([i["code"] for i in validate({"offers": []})[1]], ["E_NO_OFFERS"])
        self.assertEqual([i["code"] for i in validate("nope")[1]], ["E_NO_OFFERS"])

    def test_bare_list_accepted(self):
        offers, issues = validate([raw_offer()])
        self.assertEqual((len(offers), issues), (1, []))

    def test_duplicate_labels(self):
        c = codes([raw_offer(label="Same"), raw_offer(label="same ")], "error")
        self.assertEqual(c, ["E_DUPLICATE_LABEL"])

    def test_offer_must_be_object(self):
        self.assertEqual(codes([5], "error"), ["E_NOT_OBJECT"])

    def test_errors_are_numbered_errors_first(self):
        _, issues = validate(fixture("invalid.json"))
        text = format_issues(issues).splitlines()
        self.assertTrue(text[0].startswith("1. ERROR E_BOTH_PAY (offer 1, pay):"))
        self.assertTrue(all(line.startswith(str(k + 1) + ". ") for k, line in enumerate(text)))
        first_warning = [k for k, line in enumerate(text) if " WARNING " in line][0]
        self.assertTrue(all(" ERROR " in line for line in text[:first_warning]))

    def test_invalid_fixture_catches_every_problem(self):
        _, issues = validate(fixture("invalid.json"))
        errs = {i["code"] for i in issues if i["level"] == "error"}
        for code in ("E_BOTH_PAY", "E_NO_PAY", "E_NEGATIVE", "E_ONSITE_NO_COMMUTE", "E_TERM",
                     "E_PROVINCE", "E_DUPLICATE_LABEL", "E_NOT_NUMBER", "E_RANGE",
                     "E_ARRANGEMENT", "E_COMMUTE_MODE", "E_NOT_OBJECT", "E_NOT_BOOL"):
            self.assertIn(code, errs)

    def test_load_offers_raises_with_issues(self):
        with self.assertRaises(OffersError) as ctx:
            load_offers({"offers": [raw_offer(rent_per_month=-1)]})
        self.assertIn("E_NEGATIVE", str(ctx.exception))


class Presets(unittest.TestCase):
    def test_six_cities_with_rent_and_transit(self):
        self.assertEqual(sorted(CITY_PRESETS),
                         ["Calgary", "Montreal", "Ottawa", "Toronto", "Vancouver", "Waterloo"])
        for p in CITY_PRESETS.values():
            self.assertGreater(p["rent_per_month"], 0)
            self.assertGreater(p["transit_pass_per_month"], 0)

    def test_presets_are_labelled_as_estimates(self):
        self.assertIn("not quotes", PRESET_SOURCE_NOTE)

    def test_find_preset_is_case_and_accent_insensitive(self):
        self.assertEqual(find_preset(" toronto ")[0], "Toronto")
        self.assertEqual(find_preset("Montréal")[0], "Montreal")
        self.assertEqual(find_preset("Halifax"), (None, None))

    def test_preset_fills_missing_rent_and_transit_and_says_so(self):
        o = norm(city="Toronto", rent_per_month=None, commute={"mode": "transit"})
        self.assertEqual(o["rent_per_month"], CITY_PRESETS["Toronto"]["rent_per_month"])
        self.assertEqual(o["transit_pass_per_month"], CITY_PRESETS["Toronto"]["transit_pass_per_month"])
        self.assertEqual((o["rent_source"], o["transit_source"], o["province_source"]),
                         ("preset", "preset", "preset"))

    def test_user_value_overrides_preset(self):
        o = norm(city="Toronto", rent_per_month=1400, commute={"mode": "transit", "transit_pass_per_month": 0})
        self.assertEqual((o["rent_per_month"], o["rent_source"]), (1400, "user"))
        self.assertEqual((o["transit_pass_per_month"], o["transit_source"]), (0, "user"))
        self.assertEqual(compute_offer(o)["sources"]["rent"], "user")

    def test_preset_city_sets_province(self):
        self.assertEqual(norm(city="Vancouver")["province"], "British Columbia")
        self.assertEqual(norm(city="calgary")["province"], "Alberta")

    def test_unknown_city_is_a_warning_and_defaults_to_ontario(self):
        offers, issues = validate({"offers": [raw_offer(city="Halifax")]})
        self.assertEqual([i["code"] for i in issues], ["W_NO_PRESET"])
        self.assertEqual((offers[0]["province"], offers[0]["province_source"]), ("Ontario", "default"))

    def test_unknown_city_without_rent_or_pass_is_an_error_not_a_guess(self):
        c = codes(raw_offer(city="Halifax", rent_per_month=None, commute={"mode": "transit"}), "error")
        self.assertEqual(c, ["E_MISSING", "E_MISSING"])

    def test_province_override_and_mismatch_warning(self):
        offers, issues = validate({"offers": [raw_offer(city="Toronto", province="QC")]})
        self.assertEqual(offers[0]["province"], "Quebec")
        self.assertEqual([i["code"] for i in issues], ["W_PROVINCE_MISMATCH"])

    def test_province_aliases_and_unsupported(self):
        self.assertEqual(norm(city="Halifax", province="bc")["province"], "British Columbia")
        self.assertIn("E_PROVINCE", codes(raw_offer(province="Nova Scotia"), "error"))


if __name__ == "__main__":
    unittest.main()
