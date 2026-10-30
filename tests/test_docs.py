"""Docs, demo markup, figure and labelling rules from the spec.
The offers referenced here are SYNTHETIC EXAMPLES; all figures are estimates."""

import glob
import html.parser
import os
import re
import unittest
import xml.dom.minidom

from coop_compare.calc import compare, money
from coop_compare.model import load_offers
from coop_compare.report import DISCLAIMER

from .helpers import ROOT, samples

import importlib.util

_spec = importlib.util.spec_from_file_location("make_figure", os.path.join(ROOT, "tools", "make_figure.py"))
make_figure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_figure)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class _Form(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.controls, self.label_for, self.in_label, self.wrapped = [], set(), 0, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "label":
            self.in_label += 1
            if "for" in a:
                self.label_for.add(a["for"])
        if tag in ("input", "select", "textarea"):
            self.controls.append((a.get("id"), self.in_label > 0, a))

    def handle_endtag(self, tag):
        if tag == "label":
            self.in_label -= 1


class Labelling(unittest.TestCase):
    def test_every_file_with_sample_offers_says_synthetic(self):
        files = ["README.md", "samples/offers.json", "docs/index.html", "docs/app.js",
                 "docs/figure.svg", "docs/money-concepts.md", "docs/CHAPTER.md",
                 "coop_compare/example.py"] + glob.glob(os.path.join(ROOT, "tests", "fixtures", "*.json"))
        for f in files:
            text = read(f) if not os.path.isabs(f) else open(f, encoding="utf-8").read()
            self.assertRegex(text, r"(?i)synthetic", f)
        for t in glob.glob(os.path.join(ROOT, "tests", "test_*.py")):
            body = open(t, encoding="utf-8").read()
            if "samples()" in body or "fixture(" in body or "SAMPLES" in body:
                self.assertIn("SYNTHETIC", body, t)

    def test_sample_labels_say_synthetic(self):
        for o in samples()["offers"]:
            self.assertIn("(synthetic)", o["label"])

    def test_disclaimers(self):
        readme = read("README.md")
        self.assertIn("Disclaimer", readme)
        self.assertIn("not payroll, tax or financial advice", readme)
        page = read("docs/index.html")
        self.assertIn('id="disclaimer"', page)
        self.assertIn("Estimates only.", page)
        self.assertIn("not payroll, tax, or financial advice", page)
        self.assertIn("ESTIMATES ONLY", DISCLAIMER)

    def test_presets_described_as_rough_planning_figures(self):
        self.assertIn("rough 2026 planning figures, not quotes", read("coop_compare/presets.py"))
        self.assertIn("rough 2026 planning figures, not quotes", read("README.md"))


class ReadmeNumbers(unittest.TestCase):
    def test_worked_example_matches_the_calculator(self):
        offers, _ = load_offers(samples())
        cmp = compare(offers)
        readme = read("README.md")
        for r in cmp["results"]:
            for key in ("gross_term", "gross_month", "federal_tax", "provincial_tax", "pension", "ei",
                        "deductions_total", "net_term", "living_term", "takehome_term",
                        "takehome_month", "takehome_week"):
                self.assertIn(money(r[key]), readme, (r["label"], key))
        self.assertIn(money(cmp["ranking"][1]["gap_to_best_month"]), readme)
        self.assertIn("$37.41/hour", readme)

    def test_readme_covers_required_sections(self):
        readme = read("README.md")
        for needle in ("Why headline pay misleads", "pip install -e .", "python -m coop_compare",
                       "A full worked example", "How the tax estimate works", "Overriding presets",
                       "Project structure", "Running the tests", "Disclaimer"):
            self.assertIn(needle, readme)

    def test_money_concepts_lessons(self):
        doc = read("docs/money-concepts.md")
        for needle in ("Gross pay vs net pay", "CPP", "EI", "Marginal vs average", "myth",
                       "different life", "amortis", "Monthly vs whole-term", "Lump sums",
                       "Five beginner mistakes"):
            self.assertIn(needle, doc)
        self.assertEqual(len(re.findall(r"^\d\. \*\*", doc, re.M)), 5)

    def test_chapter_has_thesis_and_figure_description(self):
        doc = read("docs/CHAPTER.md")
        self.assertIn("## Thesis line", doc)
        self.assertIn("figure.svg", doc)
        self.assertIn("$677.93", doc)
        self.assertIn("$1,640.89", doc)


class Figure(unittest.TestCase):
    def test_figure_is_up_to_date_with_the_calculator(self):
        self.assertEqual(read("docs/figure.svg"), make_figure.build())

    def test_figure_is_valid_svg_with_title_and_desc(self):
        dom = xml.dom.minidom.parseString(read("docs/figure.svg"))
        svg = dom.documentElement
        self.assertEqual(svg.getAttribute("role"), "img")
        self.assertEqual(svg.getAttribute("aria-labelledby"), "fig-title fig-desc")
        title = dom.getElementsByTagName("title")[0].firstChild.data
        desc = dom.getElementsByTagName("desc")[0].firstChild.data
        self.assertIn("synthetic", title.lower())
        self.assertIn("estimates", title.lower())
        self.assertIn("SYNTHETIC EXAMPLE", desc)
        self.assertIn("$677.93", desc)
        self.assertIn("$1,640.89", desc)


class Demo(unittest.TestCase):
    def test_every_form_control_has_a_label(self):
        p = _Form()
        p.feed(read("docs/index.html"))
        self.assertGreater(len(p.controls), 15)
        for cid, wrapped, attrs in p.controls:
            self.assertTrue(wrapped or (cid and cid in p.label_for), attrs)

    def test_example_button_and_note_say_synthetic(self):
        page = read("docs/index.html")
        self.assertIn("Load SYNTHETIC EXAMPLE", page)
        self.assertIn("SYNTHETIC EXAMPLE loaded.", page)

    def test_demo_example_matches_samples(self):
        js = read("docs/app.js")
        for o in samples()["offers"]:
            self.assertIn("label: '" + o["label"] + "'", js)
        self.assertIn("hourly_rate: '28', hours_per_week: '37.5'", js)
        self.assertIn("hourly_rate: '24', hours_per_week: '40'", js)
        self.assertIn("rent: '1150'", js)

    def test_demo_has_required_parts_and_no_network(self):
        page = read("docs/index.html")
        js = read("docs/app.js")
        for needle in ('id="add-offer"', 'id="load-example"', 'data-preset-city="Toronto"',
                       'id="be-target"', 'id="be-adjust"', 'id="be-run"', 'id="results"'):
            self.assertIn(needle, page)
        self.assertIn("MAX_OFFERS = 4", js)
        for bad in ("fetch(", "XMLHttpRequest", "WebSocket", "import(", "<script src=\"http"):
            self.assertNotIn(bad, js + page)

    def test_pages_ready(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "docs", ".nojekyll")))
        self.assertIn('<script src="app.js"></script>', read("docs/index.html"))


if __name__ == "__main__":
    unittest.main()
