"""Regenerate docs/figure.svg from the SYNTHETIC EXAMPLE in samples/offers.json.

    python tools/make_figure.py

The figure compares monthly gross pay with monthly take-home for the two
synthetic sample offers. Numbers come straight from the calculator, so the
figure can never drift from the code (tests/test_docs.py checks this).
Every figure is an estimate.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from coop_compare.calc import compare, money  # noqa: E402
from coop_compare.model import load_offers  # noqa: E402

W, LEFT, BAR_W, BAR_H, GAP = 680, 24, 470, 22, 2
SCALE_MAX = 5000.0


def bar(x, y, w, h, cls, tip):
    """Bar anchored square at the baseline with a 4px rounded data end."""
    r = min(4.0, w / 2)
    d = ("M%.1f %.1f H%.1f Q%.1f %.1f %.1f %.1f V%.1f Q%.1f %.1f %.1f %.1f H%.1f Z"
         % (x, y, x + w - r, x + w, y, x + w, y + r, y + h - r, x + w, y + h, x + w - r, y + h, x))
    return '<path d="%s" class="%s"><title>%s</title></path>' % (d, cls, tip)


def build():
    with open(os.path.join(ROOT, "samples", "offers.json"), encoding="utf-8") as fh:
        offers, _ = load_offers(json.load(fh))
    results = compare(offers)["results"]
    rows = []
    y = 104
    for r in results:
        name = r["label"].replace(" (synthetic)", "")
        rows.append('<text x="%d" y="%d" class="name">%s, %d weeks (synthetic)</text>'
                    % (LEFT, y - 8, name, r["term_weeks"]))
        for key, cls, word in (("gross_month", "gross", "gross"), ("takehome_month", "take", "take-home")):
            v = r[key]
            w = max(1.0, BAR_W * v / SCALE_MAX)
            tip = "%s: %s %s per month (estimate)" % (name, money(v), word)
            rows.append(bar(LEFT, y, w, BAR_H, cls, tip))
            rows.append('<text x="%.1f" y="%d" class="val">%s %s</text>'
                        % (LEFT + w + 8, y + 16, money(v), word))
            y += BAR_H + GAP
        y += 52
    last_bar = y - 52
    height = last_bar + 22
    t, s = results
    desc = ("SYNTHETIC EXAMPLE, all figures are estimates, not payroll advice. Grouped horizontal bars "
            "compare monthly gross pay with monthly take-home (after estimated tax, CPP, EI, rent, "
            "commuting and moving, plus an after-tax signing bonus) for two made-up 16-week co-op offers. "
            "%s: %s gross, %s take-home per month. %s: %s gross, %s take-home per month. "
            "The offer with the higher hourly rate keeps less each month."
            % (t["label"], money(t["gross_month"]), money(t["takehome_month"]),
               s["label"], money(s["gross_month"]), money(s["takehome_month"])))
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="fig-title fig-desc" font-family="system-ui, -apple-system, 'Segoe UI', sans-serif">
  <title id="fig-title">Gross pay vs take-home pay per month: two synthetic co-op offers (estimates)</title>
  <desc id="fig-desc">{desc}</desc>
  <style>
    .bg {{ fill: #fcfcfb }} .ink {{ fill: #0b0b0b }} .name {{ fill: #0b0b0b; font-size: 14px; font-weight: 600 }}
    .val {{ fill: #0b0b0b; font-size: 13px }} .muted {{ fill: #52514e; font-size: 12px }}
    .gross {{ fill: #2a78d6 }} .take {{ fill: #eb6834 }} .axis {{ stroke: #52514e; stroke-width: 1 }}
    @media (prefers-color-scheme: dark) {{
      .bg {{ fill: #1a1a19 }} .ink, .name, .val {{ fill: #f0efec }} .muted {{ fill: #c3c2b7 }}
      .gross {{ fill: #3987e5 }} .take {{ fill: #d95926 }} .axis {{ stroke: #c3c2b7 }}
    }}
  </style>
  <rect class="bg" width="{W}" height="{H}" rx="8"/>
  <text x="{L}" y="32" class="ink" font-size="17" font-weight="700">Same job hunt, different life: gross vs take-home per month</text>
  <text x="{L}" y="52" class="muted">SYNTHETIC EXAMPLE. Estimates only (simplified 2026 tax; rent and transit are rough planning figures).</text>
  <rect x="{L}" y="64" width="14" height="14" rx="2" class="gross"/><text x="{L2}" y="76" class="val">Gross pay per month</text>
  <rect x="{L3}" y="64" width="14" height="14" rx="2" class="take"/><text x="{L4}" y="76" class="val">Take-home per month (after tax, rent, commute, moving)</text>
  <line x1="{L}" y1="86" x2="{L}" y2="{AX}" class="axis"/>
  {rows}
</svg>
""".format(W=W, H=height, L=LEFT, L2=LEFT + 20, L3=LEFT + 190, L4=LEFT + 210, AX=last_bar,
           desc=desc, rows="\n  ".join(rows))
    return svg


if __name__ == "__main__":
    out = os.path.join(ROOT, "docs", "figure.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build())
    print("wrote " + out)
