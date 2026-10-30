"""Reports: text, JSON, HTML, CSV, plus the beginner `explain` walkthrough.

All rounding happens here (to cents, half up) so the numbers in every
format are identical. Every report ends with the disclaimer.
"""

import csv
import html
import io
import json

from .calc import RENT_SHIFT, TIE_THRESHOLD, money, round2
from .model import fmt_num
from .presets import PRESET_SOURCE_NOTE
from .tax_tables import PENSION, TAX_YEAR, WEEKS_PER_MONTH

DISCLAIMER = (
    "ESTIMATES ONLY, not payroll, tax, or financial advice. Income tax, CPP/QPP, EI "
    "and QPIP use simplified " + str(TAX_YEAR) + " brackets and rates; city rent and "
    "transit presets are " + PRESET_SOURCE_NOTE + ". Your real paycheque and tax "
    "return will differ. Check numbers that matter with your employer's payroll "
    "team or the CRA / Revenu Quebec."
)

ASSUMPTIONS = [
    "A month is " + str(WEEKS_PER_MONTH) + " weeks (52 / 12), so a term of W weeks lasts W / "
    + str(WEEKS_PER_MONTH) + " months. Whole-term money is computed from weeks, never from rounded months.",
    "Income tax: the term's pay is annualised (scaled to a full year), taxed with simplified "
    + str(TAX_YEAR) + " federal + provincial brackets and the basic personal amount, then scaled back to the term.",
    "CPP/QPP and EI assume this term is your only job this calendar year; their annual maximums only bind on high pay.",
    "Lump sums (signing bonus, relocation) are taxed with the bonus method: tax on (annualised pay + lump) minus tax on annualised pay.",
    "Offers closer than " + money(TIE_THRESHOLD) + "/month are reported as about tied.",
]

SOURCE_WORDS = {
    "user": "you supplied",
    "preset": "city preset (estimate)",
    "default": "default (Ontario)",
    "assumed": "assumed (not supplied)",
    "n/a": "not used",
}

# Lines shown in the side-by-side table: (key, label, kind)
TABLE_LINES = [
    ("gross_term", "Gross pay, whole term", "money"),
    ("federal_tax", "Federal income tax (est.)", "money"),
    ("provincial_tax", "Provincial income tax (est.)", "money"),
    ("pension", "CPP / QPP (est.)", "money"),
    ("ei", "EI (est.)", "money"),
    ("qpip", "QPIP (Quebec only, est.)", "money"),
    ("deductions_total", "Total deductions", "money"),
    ("effective_deduction_rate", "Effective deduction rate", "pct"),
    ("net_term", "Net pay, whole term", "money"),
    ("rent_month", "Rent per month", "money"),
    ("commute_month", "Commute per month", "money"),
    ("other_month", "Other costs per month", "money"),
    ("living_month", "Living costs per month", "money"),
    ("living_term", "Living costs, whole term", "money"),
    ("moving_total", "One-time moving costs", "money"),
    ("moving_per_month", "  moving, spread per month", "money"),
    ("lump_net", "Lump sums after tax", "money"),
    ("takehome_term", "TAKE-HOME, whole term", "money"),
    ("takehome_month", "TAKE-HOME per month", "money"),
    ("takehome_week", "TAKE-HOME per week", "money"),
]


def pct(x):
    return "%.1f%%" % (round2(x * 100))


def _fmt(value, kind):
    if kind == "pct":
        return pct(value)
    return money(value)


def rounded(value):
    """Recursively round floats to cents (rates to 4 decimals stay readable)."""
    if isinstance(value, float):
        return round2(value)
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rounded(v) for v in value]
    return value


def to_json(cmp, offers, warnings):
    """JSON report: every money figure rounded to cents; rates kept to 4 decimals."""
    results = []
    for r in cmp["results"]:
        d = {}
        for k, v in r.items():
            if k in ("effective_deduction_rate", "average_income_tax_rate", "marginal_tax_rate"):
                d[k] = round(v, 4)
            elif k == "term_months":
                d[k] = round(v, 4)
            else:
                d[k] = rounded(v)
        results.append(d)
    doc = {
        "tool": "coop-offer-comparator",
        "tax_year": TAX_YEAR,
        "disclaimer": DISCLAIMER,
        "assumptions": ASSUMPTIONS,
        "results": results,
        "ranking": rounded(cmp["ranking"]),
        "breakeven": rounded(cmp["breakeven"]),
        "sensitivity": rounded(cmp["sensitivity"]),
        "warnings": warnings,
        "inputs": offers,
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def _table(headers, rows, left=1):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    def line(cells):
        out = []
        for i, cell in enumerate(cells):
            out.append(cell.ljust(widths[i]) if i < left else cell.rjust(widths[i]))
        return "  ".join(out).rstrip()
    sep = "  ".join("-" * w for w in widths)
    return "\n".join([line(headers), sep] + [line(r) for r in rows])


def _source_lines(r):
    s = r["sources"]
    parts = ["province: " + SOURCE_WORDS[s["province"]], "rent: " + SOURCE_WORDS[s["rent"]]]
    if s["transit"] != "n/a":
        parts.append("transit pass: " + SOURCE_WORDS[s["transit"]])
    if s["parking"] != "n/a":
        parts.append("parking: " + SOURCE_WORDS[s["parking"]])
    if s["driving_days"] != "n/a":
        parts.append("driving days: " + SOURCE_WORDS[s["driving_days"]])
    return "; ".join(parts)


def to_text(cmp, offers, warnings):
    res = cmp["results"]
    out = []
    out.append("CO-OP OFFER COMPARISON (take-home after tax, rent and commuting) -- ESTIMATES")
    out.append("=" * 78)
    out.append("")
    out.append("Offers:")
    for i, r in enumerate(res):
        out.append("  #" + str(i + 1) + "  " + r["label"] + " -- " + r["city"] + ", " + r["province"]
                   + ", " + r["arrangement"] + ", " + str(r["term_weeks"]) + " weeks ("
                   + ("%.2f" % round2(r["term_months"])) + " months)")
    out.append("")
    out.append("SIDE BY SIDE")
    headers = [""] + ["#" + str(i + 1) for i in range(len(res))]
    rows = [[label] + [_fmt(r[key], kind) for r in res] for key, label, kind in TABLE_LINES]
    out.append(_table(headers, rows))
    out.append("")
    out.append("RANKING (by monthly take-home; whole-term shown alongside)")
    rk = []
    for row in cmp["ranking"]:
        r = res[row["index"]]
        rk.append([str(row["rank"]), r["label"], money(r["takehome_month"]), money(r["takehome_term"]),
                   money(row["gap_to_best_month"]), "yes" if row["about_tied"] else "no"])
    out.append(_table(["rank", "offer", "per month", "whole term", "gap/month", "about tied"], rk, left=2))
    out.append("")
    out.append("Verdicts:")
    for row in cmp["ranking"]:
        out.append("  " + str(row["rank"]) + ". " + row["label"] + ": " + row["verdict"])
    out.append("")
    out.append("PER-OFFER BREAKDOWN")
    for i, r in enumerate(res):
        out.append("  #" + str(i + 1) + " " + r["label"])
        out.append("     gross " + money(r["gross_term"]) + " - deductions " + money(r["deductions_total"])
                   + " (" + pct(r["effective_deduction_rate"]) + ") = net " + money(r["net_term"]))
        out.append("     net " + money(r["net_term"]) + " - living " + money(r["living_term"])
                   + " - moving " + money(r["moving_total"]) + " + lump sums after tax "
                   + money(r["lump_net"]) + " = take-home " + money(r["takehome_term"]))
        out.append("     per month " + money(r["takehome_month"]) + ", per week " + money(r["takehome_week"]))
        if r["lump_gross"] > 0:
            out.append("     lump sums: " + money(r["lump_gross"]) + " before tax, est. tax "
                       + money(r["lump_tax"]) + " (shown separately, not folded into monthly pay)")
        out.append("     where the numbers came from: " + _source_lines(r))
    out.append("")
    out.append("BREAK-EVEN (same salary buys a different life)")
    if not cmp["breakeven"]:
        out.append("  Only one offer, so there is nothing to break even against.")
    for be in cmp["breakeven"]:
        out.append("  " + be["text"])
    out.append("")
    out.append("SENSITIVITY (rent " + money(RENT_SHIFT) + "/month higher or lower)")
    srows = []
    for s in cmp["sensitivity"]:
        srows.append([s["label"], money(s["rent_down"]["takehome_month"]), money(s["base"]),
                      money(s["rent_up"]["takehome_month"]),
                      "yes" if s["fragile"] else "no"])
    out.append(_table(["offer", "rent -200", "as entered", "rent +200", "rank changes?"], srows))
    out.append("")
    if warnings:
        out.append("WARNINGS")
        for k, w in enumerate(warnings):
            out.append("  " + str(k + 1) + ". offer " + str(w["offer"]) + " " + w["code"] + ": " + w["message"])
        out.append("")
    out.append("ASSUMPTIONS")
    for a in ASSUMPTIONS:
        out.append("  - " + a)
    out.append("")
    out.append("DISCLAIMER: " + DISCLAIMER)
    return "\n".join(out) + "\n"


CSV_COLUMNS = [
    "rank", "label", "city", "province", "arrangement", "term_weeks", "term_months",
    "gross_term", "gross_month", "federal_tax", "provincial_tax", "pension", "ei", "qpip",
    "deductions_total", "effective_deduction_rate", "net_term", "net_month",
    "rent_month", "commute_month", "other_month", "living_month", "living_term",
    "moving_total", "moving_per_month", "lump_gross", "lump_tax", "lump_net",
    "takehome_term", "takehome_month", "takehome_week", "gap_to_best_month",
    "about_tied", "rent_source", "transit_source", "verdict",
]


def _csv_safe(text):
    """Stop spreadsheet apps from running a label like =HYPERLINK(...) as a formula."""
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


def to_csv(cmp, offers, warnings):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    for row in cmp["ranking"]:
        r = cmp["results"][row["index"]]
        vals = []
        for col in CSV_COLUMNS:
            if col in ("rank", "gap_to_best_month", "about_tied", "verdict", "label"):
                v = row[col]
            elif col == "rent_source":
                v = r["sources"]["rent"]
            elif col == "transit_source":
                v = r["sources"]["transit"]
            else:
                v = r[col]
            if col in ("effective_deduction_rate",):
                v = "%.4f" % v
            elif col == "term_months":
                v = "%.4f" % v
            elif isinstance(v, bool):
                v = "yes" if v else "no"
            elif isinstance(v, float):
                v = "%.2f" % round2(v)
            elif isinstance(v, str):
                v = _csv_safe(v)
            vals.append(v)
        w.writerow(vals)
    w.writerow(["#disclaimer", DISCLAIMER])
    return buf.getvalue()


def to_html(cmp, offers, warnings):
    e = html.escape
    res = cmp["results"]
    p = []
    p.append("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
             "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
             "<title>Co-op offer comparison (estimates)</title>\n<style>\n"
             "body{font:16px/1.5 system-ui,sans-serif;color:#1a1a1a;background:#fff;max-width:72rem;margin:2rem auto;padding:0 1rem}\n"
             "table{border-collapse:collapse;margin:1rem 0;width:100%}\n"
             "th,td{border:1px solid #888;padding:.35rem .6rem;text-align:right}\n"
             "th:first-child,td:first-child{text-align:left}\n"
             "caption{text-align:left;font-weight:600;padding:.25rem 0}\n"
             ".total td,.total th{font-weight:700;background:#f1f1ef}\n"
             ".disclaimer{border:2px solid #8a4b00;background:#fff7ec;padding:.75rem 1rem}\n"
             "@media print{.disclaimer{break-inside:avoid}}\n"
             "</style>\n</head>\n<body>\n<main>\n")
    p.append("<h1>Co-op offer comparison</h1>\n<p>Take-home pay after estimated tax, rent and commuting. "
             "All figures are estimates.</p>\n")
    p.append("<table>\n<caption>Side by side</caption>\n<thead><tr><th scope=\"col\">Line</th>")
    for r in res:
        p.append("<th scope=\"col\">" + e(r["label"]) + "</th>")
    p.append("</tr></thead>\n<tbody>\n")
    for key, label, kind in TABLE_LINES:
        cls = " class=\"total\"" if key.startswith("takehome") else ""
        p.append("<tr" + cls + "><th scope=\"row\">" + e(label.strip()) + "</th>")
        for r in res:
            p.append("<td>" + e(_fmt(r[key], kind)) + "</td>")
        p.append("</tr>\n")
    p.append("</tbody>\n</table>\n")
    p.append("<h2 id=\"ranking\">Ranking</h2>\n<table>\n<caption>Ranked by monthly take-home</caption>\n"
             "<thead><tr><th scope=\"col\">Rank</th><th scope=\"col\">Offer</th><th scope=\"col\">Per month</th>"
             "<th scope=\"col\">Whole term</th><th scope=\"col\">Gap to best / month</th><th scope=\"col\">Verdict</th></tr></thead>\n<tbody>\n")
    for row in cmp["ranking"]:
        r = res[row["index"]]
        p.append("<tr><td>" + str(row["rank"]) + "</td><td>" + e(r["label"]) + "</td><td>"
                 + money(r["takehome_month"]) + "</td><td>" + money(r["takehome_term"]) + "</td><td>"
                 + money(row["gap_to_best_month"]) + "</td><td style=\"text-align:left\">"
                 + e(row["verdict"]) + "</td></tr>\n")
    p.append("</tbody>\n</table>\n")
    p.append("<h2>Where the numbers came from</h2>\n<ul>\n")
    for r in res:
        p.append("<li><strong>" + e(r["label"]) + "</strong>: " + e(_source_lines(r)) + "</li>\n")
    p.append("</ul>\n<h2>Break-even</h2>\n<ul>\n")
    if not cmp["breakeven"]:
        p.append("<li>Only one offer, so there is nothing to break even against.</li>\n")
    for be in cmp["breakeven"]:
        p.append("<li>" + e(be["text"]) + "</li>\n")
    p.append("</ul>\n<h2>Sensitivity to rent (&plusmn;" + money(RENT_SHIFT) + "/month)</h2>\n<table>\n"
             "<caption>Monthly take-home if rent changes</caption>\n<thead><tr><th scope=\"col\">Offer</th>"
             "<th scope=\"col\">Rent &minus;200</th><th scope=\"col\">As entered</th><th scope=\"col\">Rent +200</th>"
             "<th scope=\"col\">Rank changes?</th></tr></thead>\n<tbody>\n")
    for s in cmp["sensitivity"]:
        p.append("<tr><td>" + e(s["label"]) + "</td><td>" + money(s["rent_down"]["takehome_month"])
                 + "</td><td>" + money(s["base"]) + "</td><td>" + money(s["rent_up"]["takehome_month"])
                 + "</td><td>" + ("yes" if s["fragile"] else "no") + "</td></tr>\n")
    p.append("</tbody>\n</table>\n")
    if warnings:
        p.append("<h2>Warnings</h2>\n<ol>\n")
        for w in warnings:
            p.append("<li>offer " + str(w["offer"]) + " " + e(w["code"]) + ": " + e(w["message"]) + "</li>\n")
        p.append("</ol>\n")
    p.append("<h2>Assumptions</h2>\n<ul>\n")
    for a in ASSUMPTIONS:
        p.append("<li>" + e(a) + "</li>\n")
    p.append("</ul>\n</main>\n<footer>\n<p class=\"disclaimer\"><strong>Disclaimer:</strong> "
             + e(DISCLAIMER) + "</p>\n</footer>\n</body>\n</html>\n")
    return "".join(p)


def render(fmt, cmp, offers, warnings):
    return {"text": to_text, "json": to_json, "html": to_html, "csv": to_csv}[fmt](cmp, offers, warnings)


def explain(offer, r):
    """A beginner walkthrough of ONE offer, with the arithmetic shown."""
    o = offer
    weeks = r["term_weeks"]
    months = r["term_months"]
    L = []
    add = L.append
    add("HOW " + r["label"] + " GOES FROM GROSS PAY TO TAKE-HOME (estimates)")
    add("=" * 78)
    add("")
    add("Step 1. How long is the term?")
    add("  " + str(weeks) + " weeks. A month is about " + str(WEEKS_PER_MONTH) + " weeks (52 weeks / 12 months),")
    add("  so the term is " + str(weeks) + " / " + str(WEEKS_PER_MONTH) + " = " + ("%.4f" % months) + " months.")
    add("  Money for the whole term is worked out from weeks; months are only used to")
    add("  turn whole-term totals into per-month figures.")
    add("")
    add("Step 2. Gross pay (before anything is taken off)")
    if o["pay_style"] == "hourly":
        add("  " + money(o["hourly_rate"]) + "/hour x " + fmt_num(o["hours_per_week"]) + " hours/week x "
            + str(weeks) + " weeks = " + money(r["gross_term"]))
    else:
        add("  " + money(o["annual_salary"]) + "/year x " + str(weeks) + " / 52 weeks = " + money(r["gross_term"]))
    add("  Per month: " + money(r["gross_term"]) + " / " + ("%.4f" % months) + " = " + money(r["gross_month"]))
    add("")
    add("Step 3. Payroll deductions (each one is its own line)")
    add("  Income tax is set by YEARLY brackets, so we first ask: what would a full year")
    add("  at this pay be? " + money(r["gross_term"]) + " x 52 / " + str(weeks) + " = "
        + money(r["annualised_income"]) + " a year.")
    add("  Tax on that year (simplified " + str(TAX_YEAR) + " " + r["province"] + " + federal brackets), scaled back to")
    add("  " + str(weeks) + " of 52 weeks:")
    add("    federal income tax     " + money(r["federal_tax"]))
    add("    provincial income tax  " + money(r["provincial_tax"]))
    add("  Your marginal rate (the rate on your NEXT dollar) is about " + pct(r["marginal_tax_rate"]) + ";")
    add("  your average income-tax rate is only about " + pct(r["average_income_tax_rate"])
        + ", because lower slices of income")
    add("  are taxed at lower rates.")
    add("  " + r["pension_name"] + " (pension): " + ("%.2f" % round2(PENSION["qpp_rate" if r["province"] == "Quebec" else "cpp_rate"] * 100))
        + "% of pay above a small exemption (" + money(PENSION["basic_exemption"]) + "/year, so "
        + money(PENSION["basic_exemption"] * weeks / 52)
        + " for " + str(weeks) + " weeks)")
    add("    = " + money(r["pension"]) + ". A short term is nowhere near a full year's maximum.")
    add("  EI (employment insurance): " + money(r["ei"]))
    if r["qpip"] > 0:
        add("  QPIP (Quebec parental insurance): " + money(r["qpip"]))
    add("  Total deductions: " + money(r["deductions_total"]) + " = " + pct(r["effective_deduction_rate"]) + " of gross.")
    add("")
    add("Step 4. Net pay (what lands in your bank account)")
    add("  " + money(r["gross_term"]) + " - " + money(r["deductions_total"]) + " = " + money(r["net_term"])
        + " for the term (" + money(r["net_month"]) + "/month).")
    add("")
    add("Step 5. Living costs while you are there")
    add("  rent " + money(r["rent_month"]) + " (" + SOURCE_WORDS[r["sources"]["rent"]] + ")")
    if o["commute_mode"] == "transit":
        add("  transit pass " + money(r["commute_month"]) + " (" + SOURCE_WORDS[r["sources"]["transit"]] + ")")
    elif o["commute_mode"] == "driving":
        add("  driving " + fmt_num(o["km_per_day"]) + " km/day x " + money(o["cost_per_km"]) + "/km x "
            + fmt_num(o["days_per_week"]) + " days/week x " + str(WEEKS_PER_MONTH) + " weeks/month + parking "
            + money(o["parking_per_month"]) + " = " + money(r["commute_month"]))
    else:
        add("  no commute (remote)")
    for item in o["other_monthly"]:
        add("  " + item["name"] + " " + money(item["amount"]))
    add("  = " + money(r["living_month"]) + "/month x " + ("%.4f" % months) + " months = "
        + money(r["living_term"]) + " for the term.")
    add("")
    add("Step 6. One-time costs and one-time money (kept separate from monthly pay)")
    if o["moving_costs"]:
        for item in o["moving_costs"]:
            add("  moving cost: " + item["name"] + " " + money(item["amount"]))
        add("  total " + money(r["moving_total"]) + ", which is like " + money(r["moving_per_month"])
            + "/month when spread over the term.")
    else:
        add("  no one-time moving costs.")
    if o["lump_sums"]:
        for item in o["lump_sums"]:
            add("  lump sum: " + item["name"] + " " + money(item["amount"])
                + ("" if item["taxable"] else " (not taxed)"))
        add("  estimated tax on the lump sums " + money(r["lump_tax"]) + ", so you keep "
            + money(r["lump_net"]) + ".")
    else:
        add("  no signing bonus or relocation lump sum.")
    add("")
    add("Step 7. Take-home (what is left after living there)")
    add("  " + money(r["net_term"]) + " - " + money(r["living_term"]) + " - " + money(r["moving_total"])
        + " + " + money(r["lump_net"]) + " = " + money(r["takehome_term"]) + " for the whole term")
    add("  per month: " + money(r["takehome_term"]) + " / " + ("%.4f" % months) + " = " + money(r["takehome_month"]))
    add("  per week:  " + money(r["takehome_term"]) + " / " + str(weeks) + " = " + money(r["takehome_week"]))
    add("  Compare offers by the per-month (or per-week) figure: a longer term always")
    add("  looks bigger on the whole-term total.")
    add("")
    add("DISCLAIMER: " + DISCLAIMER)
    return "\n".join(L) + "\n"
