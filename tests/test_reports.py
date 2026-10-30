"""Report formats and the explain walkthrough. Uses the SYNTHETIC EXAMPLE samples."""

import csv
import html.parser
import io
import json
import re
import unittest

from coop_compare.calc import compare, compute_offer, money
from coop_compare.model import load_offers
from coop_compare.report import DISCLAIMER, explain, render

from .helpers import fixture, samples


class _Tags(html.parser.HTMLParser):
    VOID = {"meta", "br", "img", "input", "link", "hr"}

    def __init__(self):
        super().__init__()
        self.stack, self.ok = [], True

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.ok = False


class Reports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.offers, cls.warnings = load_offers(samples())
        cls.cmp = compare(cls.offers)

    def r(self, fmt):
        return render(fmt, self.cmp, self.offers, self.warnings)

    def test_text_has_disclaimer_ranking_breakeven_and_sensitivity(self):
        t = self.r("text")
        self.assertIn("DISCLAIMER: " + DISCLAIMER, t)
        self.assertTrue(t.rstrip().endswith(DISCLAIMER))
        for section in ("SIDE BY SIDE", "RANKING", "Verdicts:", "PER-OFFER BREAKDOWN", "BREAK-EVEN",
                        "SENSITIVITY", "ASSUMPTIONS"):
            self.assertIn(section, t)
        self.assertIn("$677.93", t)
        self.assertIn("$1,640.89", t)

    def test_text_shows_each_deduction_line(self):
        t = self.r("text")
        for line in ("Federal income tax", "Provincial income tax", "CPP / QPP", "EI (est.)",
                     "Total deductions", "Effective deduction rate"):
            self.assertIn(line, t)

    def test_text_shows_provenance(self):
        t = self.r("text")
        self.assertIn("rent: city preset (estimate)", t)
        self.assertIn("rent: you supplied", t)

    def test_json_parses_and_matches_text_numbers(self):
        doc = json.loads(self.r("json"))
        t = self.r("text")
        self.assertEqual(doc["disclaimer"], DISCLAIMER)
        for res in doc["results"]:
            for key in ("gross_term", "deductions_total", "net_term", "takehome_term", "takehome_month",
                        "takehome_week", "federal_tax", "provincial_tax", "pension", "ei"):
                self.assertIn(money(res[key]), t, key)
        self.assertEqual(doc["ranking"][0]["label"], "Waterloo QA developer (synthetic)")
        self.assertEqual(doc["results"][0]["takehome_month"], 677.93)
        self.assertEqual(doc["results"][1]["takehome_month"], 1640.89)

    def test_json_money_is_rounded_to_cents(self):
        doc = json.loads(self.r("json"))
        for res in doc["results"]:
            self.assertEqual(res["living_term"], round(res["living_term"], 2))

    def test_csv_parses_with_one_row_per_offer_and_disclaimer(self):
        rows = list(csv.reader(io.StringIO(self.r("csv"))))
        header = rows[0]
        self.assertIn("takehome_month", header)
        body = rows[1:-1]
        self.assertEqual(len(body), 2)
        rec = dict(zip(header, body[0]))
        self.assertEqual(rec["rank"], "1")
        self.assertEqual(rec["takehome_month"], "1640.89")
        self.assertEqual(rows[-1], ["#disclaimer", DISCLAIMER])
        doc = json.loads(self.r("json"))
        by_label = {r["label"]: r for r in doc["results"]}
        for row in body:
            rec = dict(zip(header, row))
            self.assertAlmostEqual(float(rec["takehome_term"]), by_label[rec["label"]]["takehome_term"], places=2)

    def test_html_has_disclaimer_ranking_and_balanced_tags(self):
        h = self.r("html")
        self.assertIn(DISCLAIMER.split(".")[0], h)
        self.assertIn('id="ranking"', h)
        self.assertIn("Waterloo QA developer (synthetic)", h)
        self.assertIn('<html lang="en">', h)
        p = _Tags()
        p.feed(h)
        self.assertTrue(p.ok and not p.stack)

    def test_html_escapes_labels(self):
        offers, _ = load_offers({"offers": [dict(samples()["offers"][1], label="<b>x</b> & co")]})
        h = render("html", compare(offers), offers, [])
        self.assertNotIn("<b>x</b>", h)
        self.assertIn("&lt;b&gt;x&lt;/b&gt; &amp; co", h)

    def test_csv_neutralises_formula_labels(self):
        offers, _ = load_offers({"offers": [dict(samples()["offers"][1], label="=HYPERLINK(\"x\")")]})
        rows = list(csv.reader(io.StringIO(render("csv", compare(offers), offers, []))))
        self.assertEqual(rows[1][1], "'=HYPERLINK(\"x\")")

    def test_warnings_appear_in_reports(self):
        offers, warnings = load_offers(fixture("unknown_city.json"))
        cmp = compare(offers)
        self.assertIn("W_NO_PRESET", render("text", cmp, offers, warnings))
        self.assertIn("W_UNKNOWN_FIELD", render("html", cmp, offers, warnings))
        self.assertEqual(len(json.loads(render("json", cmp, offers, warnings))["warnings"]), 2)

    def test_single_offer_reports(self):
        offers, _ = load_offers(fixture("unknown_city.json"))
        t = render("text", compare(offers), offers, [])
        self.assertIn("nothing to break even against", t)

    def test_lump_sum_shown_separately(self):
        t = self.r("text")
        self.assertIn("lump sums: $1,000.00 before tax, est. tax $231.50", t)


class Explain(unittest.TestCase):
    def test_walkthrough_shows_arithmetic_from_gross_to_takehome(self):
        offers, _ = load_offers(samples())
        o = offers[0]
        r = compute_offer(o)
        t = explain(o, r)
        self.assertIn("$28.00/hour x 37.5 hours/week x 16 weeks = $16,800.00", t)
        self.assertIn("$16,800.00 x 52 / 16 = $54,600.00", t)
        self.assertIn("$16,800.00 - $3,508.18 = $13,291.82", t)
        self.assertIn("= $2,503.31 for the whole term", t)
        self.assertIn("per month: $2,503.31 / 3.6926 = $677.93", t)
        self.assertIn("marginal rate", t)
        self.assertIn("city preset (estimate)", t)
        self.assertTrue(t.rstrip().endswith(DISCLAIMER))
        steps = re.findall(r"^Step (\d)\.", t, re.M)
        self.assertEqual(steps, [str(i) for i in range(1, 8)])

    def test_walkthrough_for_salary_driving_quebec(self):
        offers, _ = load_offers(fixture("mixed_provinces.json"))
        for o in offers:
            t = explain(o, compute_offer(o))
            self.assertIn("Step 7", t)
        qc = explain(offers[0], compute_offer(offers[0]))
        self.assertIn("/year x 16 / 52 weeks", qc)
        self.assertIn("QPP", qc)
        self.assertIn("QPIP", qc)
        drv = explain(offers[2], compute_offer(offers[2]))
        self.assertIn("km/day", drv)


if __name__ == "__main__":
    unittest.main()
