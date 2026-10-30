"""Command-line interface: python -m coop_compare <command> ...

Exit codes: 0 ok, 1 input errors (bad offers file), 2 usage errors.
"""

import argparse
import json
import os
import sys

from . import __version__
from .calc import breakeven, breakeven_text, compare, compute_offer, money, with_pay
from .example import EXAMPLE_JSON
from .model import format_issue, format_issues, has_errors, validate
from .report import DISCLAIMER, explain, render


def _read(path):
    """Load a JSON file; returns (data, error_message)."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return None, "1. ERROR E_FILE (file): cannot find " + path + ". Run `python -m coop_compare init` to create an example."
    except json.JSONDecodeError as exc:
        return None, ("1. ERROR E_JSON (file): " + path + " is not valid JSON (line " + str(exc.lineno)
                      + ", column " + str(exc.colno) + ": " + exc.msg + ").")


def _load(path, err):
    """Return (offers, warnings) or None after printing numbered errors."""
    data, problem = _read(path)
    if problem:
        print(problem, file=err)
        return None
    offers, issues = validate(data)
    if has_errors(issues):
        print("Cannot compare: fix these problems in " + path + " first.", file=err)
        print(format_issues(issues), file=err)
        return None
    return offers, [i for i in issues if i["level"] == "warning"]


def _find(offers, label, err):
    want = label.strip().lower()
    for o in offers:
        if o["label"].lower() == want:
            return o
    print("1. ERROR E_LABEL: no offer is labelled \"" + label + "\". Labels in this file:", file=err)
    for o in offers:
        print("   - " + o["label"], file=err)
    return None


def cmd_compare(args, out, err):
    loaded = _load(args.offers, err)
    if loaded is None:
        return 1
    offers, warnings = loaded
    text = render(args.format, compare(offers), offers, warnings)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print("Wrote " + args.format + " report to " + args.out, file=out)
    else:
        out.write(text)
    return 0


def cmd_explain(args, out, err):
    loaded = _load(args.offers, err)
    if loaded is None:
        return 1
    offers, _ = loaded
    o = _find(offers, args.label, err)
    if o is None:
        return 1
    out.write(explain(o, compute_offer(o)))
    return 0


def cmd_breakeven(args, out, err):
    loaded = _load(args.offers, err)
    if loaded is None:
        return 1
    offers, _ = loaded
    a = _find(offers, args.target, err)
    if a is None:
        return 1
    b = _find(offers, args.adjust, err)
    if b is None:
        return 1
    be = breakeven(a, b)
    out.write("BREAK-EVEN: what would " + b["label"] + " have to pay to match " + a["label"] + "?\n")
    out.write("Costs (rent, commute, other, moving, lump sums) stay fixed; only pay moves.\n\n")
    out.write("  " + a["label"] + " monthly take-home: " + money(be["target_takehome_month"]) + "\n")
    out.write("  " + b["label"] + " monthly take-home now: " + money(be["current_takehome_month"]) + "\n\n")
    out.write("  " + breakeven_text(be) + "\n\n")
    if be["reachable"] and be["required_pay"]:
        check = compute_offer(with_pay(b, be["required_pay"]))["takehome_month"]
        out.write("  Check: at that pay, " + b["label"] + " takes home " + money(check) + "/month.\n\n")
    out.write("DISCLAIMER: " + DISCLAIMER + "\n")
    return 0


def cmd_validate(args, out, err):
    data, problem = _read(args.offers)
    if problem:
        print(problem, file=err)
        return 1
    offers, issues = validate(data)
    errors = [i for i in issues if i["level"] == "error"]
    warnings = [i for i in issues if i["level"] == "warning"]
    if issues:
        stream = err if errors else out
        print(format_issues(issues), file=stream)
    print(("INVALID" if errors else "OK") + ": " + str(len(errors)) + " error(s), " + str(len(warnings))
          + " warning(s), " + str(len(offers)) + " valid offer(s).", file=out)
    return 1 if errors else 0


def cmd_init(args, out, err):
    path = os.path.join(os.getcwd(), args.name)
    if os.path.exists(path) and not args.force:
        print("1. ERROR E_EXISTS: " + path + " already exists; refusing to overwrite. Use --force to replace it.", file=err)
        return 1
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(EXAMPLE_JSON)
    print("Wrote a SYNTHETIC EXAMPLE offers file to " + path + ".", file=out)
    print("Edit it with your real offers, then run: python -m coop_compare compare " + args.name, file=out)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="coop_compare",
        description="Compare co-op job offers by estimated take-home pay after tax, rent and commuting.",
        epilog="All figures are estimates, not payroll or tax advice.")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compare", help="side-by-side comparison, ranking, break-even and sensitivity")
    c.add_argument("offers")
    c.add_argument("--format", choices=("text", "json", "html", "csv"), default="text")
    c.add_argument("--out", help="write the report to this file instead of the screen")
    c.set_defaults(func=cmd_compare)

    e = sub.add_parser("explain", help="plain-English walkthrough of one offer")
    e.add_argument("offers")
    e.add_argument("label")
    e.set_defaults(func=cmd_explain)

    b = sub.add_parser("breakeven", help="pay offer ADJUST needs to match offer TARGET's monthly take-home")
    b.add_argument("offers")
    b.add_argument("target", help="label of the offer to match")
    b.add_argument("adjust", help="label of the offer whose pay moves")
    b.set_defaults(func=cmd_breakeven)

    v = sub.add_parser("validate", help="check an offers file; exit 1 if it has errors")
    v.add_argument("offers")
    v.set_defaults(func=cmd_validate)

    i = sub.add_parser("init", help="write an example offers.json (synthetic) here")
    i.add_argument("--force", action="store_true", help="overwrite an existing file")
    i.add_argument("--name", default="offers.json", help=argparse.SUPPRESS)
    i.set_defaults(func=cmd_init)
    return p


def main(argv=None, out=None, err=None):
    out = out or sys.stdout
    err = err or sys.stderr
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    return args.func(args, out, err)
