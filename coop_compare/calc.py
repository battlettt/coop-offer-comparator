"""All the money math, in one place. Every figure is an ESTIMATE.

Formulas (weeks = term length in weeks, months = weeks / 4.333):

  gross_term     = hourly_rate * hours_per_week * weeks          (hourly)
                 = annual_salary * weeks / 52                    (salary)
  gross_month    = gross_term / months

  annualised     = gross_term * 52 / weeks       (what a full year at this pay would be)
  income tax     = tax(annualised) * weeks / 52  (federal and provincial, each its own line)
  CPP/QPP        = rate * max(0, min(gross_term, YMPE) - 3500 * weeks / 52), capped at the annual max
  EI             = rate * min(gross_term, max insurable earnings)
  QPIP           = rate * min(gross_term, max insurable)             (Quebec only)
  net_term       = gross_term - all deductions

  living_month   = rent + commute + other monthly costs
  living_term    = living_month * months
  lump tax       = tax(annualised + taxable lumps) - tax(annualised)   (bonus method)
  lump_net       = lump sums - lump tax
  takehome_term  = net_term - living_term - moving_costs + lump_net
  takehome_month = takehome_term / months
  takehome_week  = takehome_term / weeks

Nothing is rounded inside this module; reports round to cents at the end.

Note on sums: Python 3.12's built-in sum() uses compensated summation for
floats, while JavaScript's plain loop does not. To keep the demo and this
module bit-for-bit identical, every total here is a plain left-to-right loop.
"""

import math

from .tax_tables import (
    EI, FEDERAL, PENSION, PROVINCES, QPIP, QUEBEC_ABATEMENT,
    WEEKS_PER_MONTH, WEEKS_PER_YEAR,
)

TIE_THRESHOLD = 25.0      # dollars per month: closer than this is "about tied"
RENT_SHIFT = 200.0        # sensitivity: rent +/- this many dollars per month


def round2(x):
    """Round half up to cents. Identical to the demo's Math.floor(x*100+0.5)/100."""
    return math.floor(x * 100 + 0.5) / 100


def add_up(values):
    total = 0.0
    for v in values:
        total = total + v
    return total


def bracket_tax(income, brackets):
    """Tax from marginal brackets: each slice of income is taxed at its own rate."""
    tax = 0.0
    lower = 0.0
    for limit, rate in brackets:
        if income <= lower:
            break
        top = income if limit is None else min(income, limit)
        tax = tax + (top - lower) * rate
        if limit is None:
            break
        lower = limit
    return tax


def marginal_rate(income, brackets):
    lower = 0.0
    for limit, rate in brackets:
        if limit is None or income < limit:
            return rate
        lower = limit
    return brackets[-1][1]


def annual_income_tax(income, province):
    """Simplified annual income tax: returns (federal, provincial)."""
    fb = FEDERAL["brackets"]
    federal = bracket_tax(income, fb) - FEDERAL["basic_personal_amount"] * fb[0][1]
    if federal < 0:
        federal = 0.0
    if province == "Quebec":
        federal = federal * (1 - QUEBEC_ABATEMENT)
    p = PROVINCES[province]
    pb = p["brackets"]
    provincial = bracket_tax(income, pb) - p["basic_personal_amount"] * pb[0][1]
    if provincial < 0:
        provincial = 0.0
    return federal, provincial


def combined_marginal_rate(income, province):
    fed = marginal_rate(income, FEDERAL["brackets"])
    if province == "Quebec":
        fed = fed * (1 - QUEBEC_ABATEMENT)
    return fed + marginal_rate(income, PROVINCES[province]["brackets"])


def gross_for_term(offer):
    if offer["pay_style"] == "hourly":
        return offer["hourly_rate"] * offer["hours_per_week"] * offer["term_weeks"]
    return offer["annual_salary"] * offer["term_weeks"] / WEEKS_PER_YEAR


def commute_per_month(offer):
    mode = offer["commute_mode"]
    if mode == "transit":
        return offer["transit_pass_per_month"]
    if mode == "driving":
        return (offer["km_per_day"] * offer["cost_per_km"] * offer["days_per_week"] * WEEKS_PER_MONTH
                + offer["parking_per_month"])
    return 0.0


def compute_offer(offer):
    """Full breakdown for one normalised offer (raw floats, unrounded)."""
    weeks = offer["term_weeks"]
    province = offer["province"]
    months = weeks / WEEKS_PER_MONTH
    year_share = weeks / WEEKS_PER_YEAR

    gross = gross_for_term(offer)
    annualised = gross * WEEKS_PER_YEAR / weeks
    fed_annual, prov_annual = annual_income_tax(annualised, province)
    federal_tax = fed_annual * year_share
    provincial_tax = prov_annual * year_share

    quebec = province == "Quebec"
    pension_rate = PENSION["qpp_rate"] if quebec else PENSION["cpp_rate"]
    pension_max = (PENSION["ympe"] - PENSION["basic_exemption"]) * pension_rate
    pensionable = min(gross, PENSION["ympe"]) - PENSION["basic_exemption"] * year_share
    if pensionable < 0:
        pensionable = 0.0
    pension = min(pensionable * pension_rate, pension_max)

    ei_rate = EI["quebec_rate"] if quebec else EI["rate"]
    ei = min(gross, EI["max_insurable"]) * ei_rate
    qpip = min(gross, QPIP["max_insurable"]) * QPIP["rate"] if quebec else 0.0

    deductions = add_up([federal_tax, provincial_tax, pension, ei, qpip])
    net = gross - deductions

    commute = commute_per_month(offer)
    other = add_up(i["amount"] for i in offer["other_monthly"])
    living_month = add_up([offer["rent_per_month"], commute, other])
    living_term = living_month * months
    moving = add_up(i["amount"] for i in offer["moving_costs"])

    lump_gross = add_up(i["amount"] for i in offer["lump_sums"])
    lump_taxable = add_up(i["amount"] for i in offer["lump_sums"] if i["taxable"])
    lump_tax = 0.0
    if lump_taxable > 0:
        f2, p2 = annual_income_tax(annualised + lump_taxable, province)
        lump_tax = (f2 + p2) - (fed_annual + prov_annual)
    lump_net = lump_gross - lump_tax

    takehome_term = net - living_term - moving + lump_net
    annual_tax = fed_annual + prov_annual

    return {
        "label": offer["label"],
        "city": offer["city"],
        "province": province,
        "arrangement": offer["arrangement"],
        "pay_style": offer["pay_style"],
        "term_weeks": weeks,
        "term_months": months,
        "gross_term": gross,
        "gross_month": gross / months,
        "annualised_income": annualised,
        "federal_tax": federal_tax,
        "provincial_tax": provincial_tax,
        "pension": pension,
        "pension_name": "QPP" if quebec else "CPP",
        "ei": ei,
        "qpip": qpip,
        "deductions_total": deductions,
        "effective_deduction_rate": deductions / gross if gross > 0 else 0.0,
        "average_income_tax_rate": annual_tax / annualised if annualised > 0 else 0.0,
        "marginal_tax_rate": combined_marginal_rate(annualised, province),
        "net_term": net,
        "net_month": net / months,
        "rent_month": offer["rent_per_month"],
        "commute_month": commute,
        "other_month": other,
        "living_month": living_month,
        "living_term": living_term,
        "moving_total": moving,
        "moving_per_month": moving / months,
        "lump_gross": lump_gross,
        "lump_tax": lump_tax,
        "lump_net": lump_net,
        "takehome_term": takehome_term,
        "takehome_month": takehome_term / months,
        "takehome_week": takehome_term / weeks,
        "sources": {
            "province": offer["province_source"],
            "rent": offer["rent_source"],
            "transit": offer["transit_source"],
            "parking": offer["parking_source"],
            "driving_days": offer["days_source"],
        },
    }


def with_pay(offer, value):
    """Copy of an offer with its pay (hourly rate or salary) replaced."""
    o = dict(offer)
    if o["pay_style"] == "hourly":
        o["hourly_rate"] = value
    else:
        o["annual_salary"] = value
    return o


def with_rent(offer, rent):
    o = dict(offer)
    o["rent_per_month"] = rent
    return o


def current_pay(offer):
    return offer["hourly_rate"] if offer["pay_style"] == "hourly" else offer["annual_salary"]


def rank(results):
    """Rank by monthly take-home (highest first); input order breaks exact ties.

    Returns a list of dicts: rank, index (into results), gap_to_best_month,
    about_tied (within TIE_THRESHOLD of the best), verdict.
    """
    order = list(range(len(results)))
    order.sort(key=lambda i: -results[i]["takehome_month"])
    best = results[order[0]]
    rows = []
    for pos, i in enumerate(order):
        r = results[i]
        gap = best["takehome_month"] - r["takehome_month"]
        rows.append({
            "rank": pos + 1,
            "index": i,
            "label": r["label"],
            "gap_to_best_month": gap,
            "about_tied": pos > 0 and round2(gap) <= TIE_THRESHOLD,
        })
    for row in rows:
        row["verdict"] = _verdict(row, rows, results)
    return rows


def money(x):
    """Format dollars the same way in Python and the demo: -$1,234.56."""
    r = round2(x)
    sign = "-" if r < 0 else ""
    whole_cents = "%.2f" % abs(r)
    whole, cents = whole_cents.split(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return sign + "$" + ",".join(groups) + "." + cents


def _verdict(row, rows, results):
    if len(rows) == 1:
        return "Only offer: " + money(results[row["index"]]["takehome_month"]) + "/month take-home."
    best = rows[0]
    if row["rank"] == 1:
        tied = [r["label"] for r in rows[1:] if r["about_tied"]]
        if tied:
            return ("Highest monthly take-home, but about tied with " + ", ".join(tied)
                    + " (within " + money(TIE_THRESHOLD) + "/month): treat them as equal on money "
                    "and decide on the job itself.")
        nxt = rows[1]
        return ("Best monthly take-home: " + money(nxt["gap_to_best_month"])
                + "/month more than " + nxt["label"] + ".")
    if row["about_tied"]:
        return ("About tied with " + best["label"] + ": only " + money(row["gap_to_best_month"])
                + "/month behind, which is inside the estimate's margin.")
    return (money(row["gap_to_best_month"]) + "/month less take-home than " + best["label"] + ".")


def breakeven(target_offer, offer, iterations=100):
    """Pay `offer` would need for its monthly take-home to equal `target_offer`'s.

    Costs are held fixed; only the hourly rate (or salary) of `offer` moves.
    Take-home rises with pay, so we bisect between 0 and an upper bound.
    """
    target = compute_offer(target_offer)["takehome_month"]
    now = current_pay(offer)
    now_month = compute_offer(offer)["takehome_month"]

    def f(pay):
        return compute_offer(with_pay(offer, pay))["takehome_month"]

    result = {
        "target_label": target_offer["label"],
        "label": offer["label"],
        "pay_style": offer["pay_style"],
        "current_pay": now,
        "current_takehome_month": now_month,
        "target_takehome_month": target,
        "required_pay": None,
        "change": None,
        "change_pct": None,
        "reachable": True,
    }
    if f(0.0) >= target:
        required = 0.0
    else:
        lo = 0.0
        hi = now * 2 if now > 0 else 1.0
        steps = 0
        while f(hi) < target and steps < 40:
            hi = hi * 2
            steps = steps + 1
        if f(hi) < target:
            result["reachable"] = False
            return result
        for _ in range(iterations):
            mid = (lo + hi) / 2
            if f(mid) < target:
                lo = mid
            else:
                hi = mid
        required = hi
    result["required_pay"] = required
    result["change"] = required - now
    result["change_pct"] = (required - now) / now if now > 0 else None
    return result


def breakeven_text(be):
    unit = "/hour" if be["pay_style"] == "hourly" else "/year"
    if not be["reachable"]:
        return ("No realistic " + ("hourly rate" if be["pay_style"] == "hourly" else "salary")
                + " lets " + be["label"] + " match " + be["target_label"] + ".")
    need = math.ceil(be["required_pay"] * 100) / 100
    if be["required_pay"] == 0:
        return (be["label"] + " matches " + be["target_label"]
                + " even at zero pay (its costs are that much lower).")
    pct = ""
    if be["change_pct"] is not None:
        tenths = math.floor(abs(be["change_pct"]) * 1000 + 0.5) / 10
        pct = " (" + ("+" if be["change"] >= 0 else "-") + ("%.1f" % tenths) + "%)"
    if be["change"] > 0:
        return (be["label"] + " would need " + money(need) + unit + " instead of "
                + money(be["current_pay"]) + unit + pct + " to match the monthly take-home of "
                + be["target_label"] + ".")
    return (be["label"] + " already matches " + be["target_label"] + "; it could pay as little as "
            + money(need) + unit + " instead of " + money(be["current_pay"]) + unit + pct
            + " and still keep up.")


def sensitivity(offers, results, index, shift=RENT_SHIFT):
    """Monthly take-home if this offer's rent were `shift` higher / lower,
    and where it would then rank (other offers unchanged)."""
    offer = offers[index]
    base = results[index]["takehome_month"]
    out = {"shift": shift, "base": base}
    for key, delta in (("rent_up", shift), ("rent_down", -shift)):
        new_rent = offer["rent_per_month"] + delta
        if new_rent < 0:
            new_rent = 0.0
        r = compute_offer(with_rent(offer, new_rent))
        trial = list(results)
        trial[index] = r
        ranked = rank(trial)
        new_rank = [row["rank"] for row in ranked if row["index"] == index][0]
        out[key] = {"rent": new_rent, "takehome_month": r["takehome_month"], "rank": new_rank}
    return out


def compare(offers):
    """Everything a report needs, from a list of normalised offers."""
    results = [compute_offer(o) for o in offers]
    ranking = rank(results)
    best_index = ranking[0]["index"]
    base_rank = {row["index"]: row["rank"] for row in ranking}
    sens = []
    for i in range(len(offers)):
        s = sensitivity(offers, results, i)
        s["label"] = results[i]["label"]
        s["rank"] = base_rank[i]
        s["fragile"] = s["rent_up"]["rank"] != s["rank"] or s["rent_down"]["rank"] != s["rank"]
        sens.append(s)
    pairs = []
    for row in ranking[1:]:
        be = breakeven(offers[best_index], offers[row["index"]])
        be["text"] = breakeven_text(be)
        pairs.append(be)
    return {
        "results": results,
        "ranking": ranking,
        "breakeven": pairs,
        "sensitivity": sens,
    }
