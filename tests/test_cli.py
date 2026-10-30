"""CLI behaviour. Uses the SYNTHETIC EXAMPLE samples and fixtures."""

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

from coop_compare.cli import main
from coop_compare.example import EXAMPLE_JSON

from .helpers import FIXTURES, ROOT, SAMPLES


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


class Cli(unittest.TestCase):
    def test_compare_text(self):
        code, out, _ = run("compare", SAMPLES)
        self.assertEqual(code, 0)
        self.assertIn("RANKING", out)
        self.assertIn("DISCLAIMER", out)

    def test_compare_every_format_to_file(self):
        with tempfile.TemporaryDirectory() as d:
            for fmt in ("text", "json", "html", "csv"):
                path = os.path.join(d, "r." + fmt)
                code, out, _ = run("compare", SAMPLES, "--format", fmt, "--out", path)
                self.assertEqual(code, 0)
                self.assertIn("Wrote " + fmt, out)
                with open(path, encoding="utf-8") as fh:
                    body = fh.read()
                if fmt == "json":
                    json.loads(body)
                if fmt == "csv":
                    self.assertGreater(len(list(csv.reader(io.StringIO(body)))), 2)
                self.assertIn("ESTIMATES ONLY", body)

    def test_compare_refuses_invalid_file_with_numbered_errors(self):
        code, _, err = run("compare", os.path.join(FIXTURES, "invalid.json"))
        self.assertEqual(code, 1)
        self.assertIn("1. ERROR E_BOTH_PAY", err)

    def test_missing_and_malformed_files(self):
        code, _, err = run("compare", "/nonexistent/offers.json")
        self.assertEqual(code, 1)
        self.assertIn("E_FILE", err)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{not json")
        try:
            code, _, err = run("validate", fh.name)
            self.assertEqual(code, 1)
            self.assertIn("E_JSON", err)
            self.assertIn("line 1", err)
        finally:
            os.unlink(fh.name)

    def test_explain(self):
        code, out, _ = run("explain", SAMPLES, "waterloo qa developer (synthetic)")
        self.assertEqual(code, 0)
        self.assertIn("Step 7", out)
        self.assertIn("$1,640.89", out)

    def test_explain_unknown_label_lists_labels(self):
        code, _, err = run("explain", SAMPLES, "nope")
        self.assertEqual(code, 1)
        self.assertIn("E_LABEL", err)
        self.assertIn("Toronto data analyst (synthetic)", err)

    def test_breakeven_subcommand_checks_its_answer(self):
        code, out, _ = run("breakeven", SAMPLES, "Waterloo QA developer (synthetic)",
                           "Toronto data analyst (synthetic)")
        self.assertEqual(code, 0)
        self.assertIn("$37.41/hour", out)
        self.assertIn("Check: at that pay, Toronto data analyst (synthetic) takes home $1,640.89/month.", out)
        self.assertIn("DISCLAIMER", out)

    def test_validate_ok_and_errors(self):
        code, out, _ = run("validate", SAMPLES)
        self.assertEqual(code, 0)
        self.assertIn("OK: 0 error(s)", out)
        code, out, err = run("validate", os.path.join(FIXTURES, "invalid.json"))
        self.assertEqual(code, 1)
        self.assertIn("INVALID: 16 error(s), 3 warning(s)", out)
        self.assertIn("19. WARNING", err)

    def test_validate_warnings_only_exits_zero(self):
        code, out, _ = run("validate", os.path.join(FIXTURES, "unknown_city.json"))
        self.assertEqual(code, 0)
        self.assertIn("W_NO_PRESET", out)
        self.assertIn("W_UNKNOWN_FIELD", out)

    def test_init_writes_synthetic_example_and_refuses_overwrite(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                code, out, _ = run("init")
                self.assertEqual(code, 0)
                self.assertIn("SYNTHETIC EXAMPLE", out)
                with open("offers.json", encoding="utf-8") as fh:
                    data = json.load(fh)
                self.assertIn("SYNTHETIC EXAMPLE", data["_note"])
                code, _, err = run("init")
                self.assertEqual(code, 1)
                self.assertIn("--force", err)
                code, _, _ = run("init", "--force")
                self.assertEqual(code, 0)
                code, _, _ = run("validate", "offers.json")
                self.assertEqual(code, 0)
            finally:
                os.chdir(old)

    def test_example_matches_samples_file(self):
        with open(SAMPLES, encoding="utf-8") as fh:
            self.assertEqual(json.loads(EXAMPLE_JSON), json.load(fh))

    def test_usage_errors_exit_2(self):
        err = io.StringIO()
        sys_stderr = sys.stderr
        sys.stderr = err
        try:
            self.assertEqual(main(["compare"]), 2)
            self.assertEqual(main(["compare", SAMPLES, "--format", "pdf"]), 2)
        finally:
            sys.stderr = sys_stderr

    def test_python_dash_m_entry_point(self):
        p = subprocess.run([sys.executable, "-m", "coop_compare", "compare", SAMPLES, "--format", "json"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["tool"], "coop-offer-comparator")


if __name__ == "__main__":
    unittest.main()
