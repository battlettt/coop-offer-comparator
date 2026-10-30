"""Demo parity: docs/app.js (run under Node) must give EXACTLY the same
validation issues, normalised offers, numbers, rankings, verdicts,
break-even and sensitivity results as the Python package on shared
fixtures (the SYNTHETIC EXAMPLE samples plus tests/fixtures/*.json)."""

import glob
import json
import os
import shutil
import subprocess
import unittest

from coop_compare.calc import compare
from coop_compare.model import has_errors, validate
from coop_compare.presets import presets_snapshot
from coop_compare.tax_tables import tables_snapshot

from .helpers import APP_JS, FIXTURES, ROOT, SAMPLES

NODE = shutil.which("node")
FILES = [SAMPLES] + sorted(glob.glob(os.path.join(FIXTURES, "*.json")))


def python_run(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    offers, issues = validate(data)
    result = {"issues": issues, "offers": offers,
              "compare": compare(offers) if offers and not has_errors(issues) else None}
    return json.loads(json.dumps(result))  # same JSON round trip as the JS side


@unittest.skipIf(NODE is None, "node is not installed; parity tests need it")
class DemoParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = subprocess.run([NODE, os.path.join(ROOT, "tests", "js_runner.js"), APP_JS] + FILES,
                           capture_output=True, text=True, check=True)
        cls.js = json.loads(p.stdout)

    def test_tax_tables_identical(self):
        py = json.loads(json.dumps(tables_snapshot()))
        self.assertEqual(self.js["tables"], py)

    def test_presets_identical(self):
        py = json.loads(json.dumps(presets_snapshot()))
        self.assertEqual(self.js["presets"], py)

    def test_every_fixture_identical(self):
        self.assertEqual(len(self.js["runs"]), len(FILES))
        for path, run in zip(FILES, self.js["runs"]):
            py = python_run(path)
            name = os.path.basename(path)
            with self.subTest(fixture=name, part="issues"):
                self.assertEqual(run["issues"], py["issues"])
            with self.subTest(fixture=name, part="offers"):
                self.assertEqual(run["offers"], py["offers"])
            with self.subTest(fixture=name, part="compare"):
                self.assertEqual(run["compare"], py["compare"])

    def test_numbers_are_bit_identical_not_just_close(self):
        run = self.js["runs"][0]
        py = python_run(SAMPLES)
        for a, b in zip(run["compare"]["results"], py["compare"]["results"]):
            for key in ("gross_term", "deductions_total", "net_term", "living_term", "lump_tax",
                        "takehome_term", "takehome_month", "takehome_week"):
                self.assertEqual(float(a[key]).hex(), float(b[key]).hex(), key)

    def test_fixtures_cover_the_interesting_paths(self):
        runs = {os.path.basename(f): r for f, r in zip(FILES, self.js["runs"])}
        self.assertIsNone(runs["invalid.json"]["compare"])
        mixed = runs["mixed_provinces.json"]["compare"]["results"]
        self.assertEqual({r["province"] for r in mixed}, {"Quebec", "British Columbia", "Alberta", "Ontario"})
        self.assertTrue(any(r["about_tied"] for r in runs["tied.json"]["compare"]["ranking"]))


@unittest.skipIf(NODE is None, "node is not installed")
class DemoSyntax(unittest.TestCase):
    def test_app_js_parses(self):
        p = subprocess.run([NODE, "--check", APP_JS], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
