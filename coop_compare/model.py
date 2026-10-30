"""Validate an offers file and turn it into normalised offer dicts.

Design rule: bad input fails loudly. We never silently swap a wrong number
in. Every problem becomes an Issue with a level ("error" or "warning"), a
stable code, the 1-based offer number, the field path, and an actionable
message. Item numbering inside lists also starts at 1.

The browser demo (docs/app.js) carries a line-for-line port of this module;
the parity tests feed both the same fixtures and compare the issue codes,
messages and normalised offers.
"""

import math

from .presets import find_preset
from .tax_tables import PROVINCE_ALIASES

ARRANGEMENTS = ("remote", "hybrid", "onsite")
COMMUTE_MODES = ("transit", "driving", "none")

OFFER_FIELDS = (
    "label", "city", "province", "hourly_rate", "hours_per_week",
    "annual_salary", "term_weeks", "arrangement", "rent_per_month",
    "commute", "other_monthly", "moving_costs", "lump_sums",
)
COMMUTE_FIELDS = {
    "transit": ("mode", "transit_pass_per_month"),
    "driving": ("mode", "km_per_day", "cost_per_km", "parking_per_month", "days_per_week"),
    "none": ("mode",),
}
ALL_COMMUTE_FIELDS = (
    "mode", "transit_pass_per_month", "km_per_day", "cost_per_km",
    "parking_per_month", "days_per_week",
)
DEFAULT_DRIVING_DAYS = {"onsite": 5, "hybrid": 3, "remote": 0}
# Any single amount above this is almost certainly a typo (and would make the
# math overflow), so it is an error rather than a silently absurd report.
MAX_AMOUNT = 100000000


class OffersError(Exception):
    """Raised when an offers file has errors; carries the issue list."""

    def __init__(self, issues):
        self.issues = issues
        super().__init__(format_issues(issues))


def fmt_num(x):
    """Format a number the same way in Python and JavaScript messages."""
    if isinstance(x, bool):
        return "true" if x else "false"
    if is_number(x) and float(x).is_integer() and abs(x) < 1e21:
        return str(int(x))
    return repr(x) if isinstance(x, float) else str(x)


def _describe(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value + '"'
    if isinstance(value, (list, tuple)):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return fmt_num(value)


def is_number(x):
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        return False
    try:
        return math.isfinite(float(x))
    except OverflowError:  # an integer too large to be a float
        return False


class _Collector:
    def __init__(self):
        self.issues = []

    def error(self, code, offer, field, message):
        self.issues.append({"level": "error", "code": code, "offer": offer,
                            "field": field, "message": message})

    def warning(self, code, offer, field, message):
        self.issues.append({"level": "warning", "code": code, "offer": offer,
                            "field": field, "message": message})


def _money(c, n, obj, key, path, required, positive=False):
    """Read a non-negative (or strictly positive) number. Returns value or None."""
    if key not in obj or obj[key] is None:
        if required:
            c.error("E_MISSING", n, path, "missing required field `" + path + "`.")
        return None
    v = obj[key]
    if not is_number(v):
        c.error("E_NOT_NUMBER", n, path,
                "`" + path + "` must be a number, got " + _describe(v) + ".")
        return None
    if v < 0:
        c.error("E_NEGATIVE", n, path,
                "`" + path + "` cannot be negative, got " + fmt_num(v)
                + ". Enter costs and pay as positive amounts.")
        return None
    if positive and v == 0:
        c.error("E_ZERO", n, path, "`" + path + "` must be greater than 0.")
        return None
    if v > MAX_AMOUNT:
        c.error("E_RANGE", n, path,
                "`" + path + "` is " + fmt_num(v) + "; anything over " + fmt_num(MAX_AMOUNT)
                + " is treated as a typo.")
        return None
    return float(v)


def _items(c, n, obj, key, allow_taxable):
    raw = obj.get(key)
    if raw is None:
        return []
    if not isinstance(raw, list):
        c.error("E_NOT_LIST", n, key,
                "`" + key + "` must be a list of {\"name\": ..., \"amount\": ...} items.")
        return []
    out = []
    for i, item in enumerate(raw):
        path = key + "[" + str(i + 1) + "]"
        if not isinstance(item, dict):
            c.error("E_NOT_OBJECT", n, path,
                    "`" + path + "` must be an object like {\"name\": \"phone\", \"amount\": 50}.")
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            c.error("E_MISSING", n, path + ".name",
                    "missing required field `" + path + ".name` (a short description).")
            name = None
        amount = _money(c, n, item, "amount", path + ".amount", True)
        allowed = ("name", "amount", "taxable") if allow_taxable else ("name", "amount")
        for k in item:
            if k not in allowed and not k.startswith("_"):
                c.warning("W_UNKNOWN_FIELD", n, path + "." + k,
                          "unknown field `" + path + "." + k + "` was ignored.")
        taxable = True
        if allow_taxable and "taxable" in item:
            if isinstance(item["taxable"], bool):
                taxable = item["taxable"]
            else:
                c.error("E_NOT_BOOL", n, path + ".taxable",
                        "`" + path + ".taxable` must be true or false.")
        if name is not None and amount is not None:
            entry = {"name": name.strip(), "amount": amount}
            if allow_taxable:
                entry["taxable"] = taxable
            out.append(entry)
    return out


def _offer(c, n, o, seen_labels):
    if not isinstance(o, dict):
        c.error("E_NOT_OBJECT", n, "", "offer " + str(n) + " must be a JSON object.")
        return None
    start = len(c.issues)

    for k in o:
        if k not in OFFER_FIELDS and not k.startswith("_"):
            c.warning("W_UNKNOWN_FIELD", n, k, "unknown field `" + k + "` was ignored.")

    label = o.get("label")
    if not isinstance(label, str) or not label.strip():
        c.error("E_MISSING", n, "label",
                "missing required field `label` (e.g. \"Employer - Role\").")
        label = None
    else:
        label = label.strip()
        if label.lower() in seen_labels:
            c.error("E_DUPLICATE_LABEL", n, "label",
                    "label \"" + label + "\" is used by more than one offer; labels must be unique.")
        seen_labels.add(label.lower())

    city = o.get("city")
    preset_name, preset = None, None
    if not isinstance(city, str) or not city.strip():
        c.error("E_MISSING", n, "city", "missing required field `city`.")
        city = None
    else:
        city = city.strip()
        preset_name, preset = find_preset(city)
        if preset is None:
            c.warning("W_NO_PRESET", n, "city",
                      "no preset for city \"" + city + "\"; rent and transit must come from your file.")
        else:
            city = preset_name

    province, province_source = None, None
    if "province" in o and o["province"] is not None:
        raw = o["province"]
        canon = PROVINCE_ALIASES.get(raw.strip().lower()) if isinstance(raw, str) else None
        if canon is None:
            c.error("E_PROVINCE", n, "province",
                    "unsupported province " + _describe(raw)
                    + "; use Ontario, British Columbia, Quebec, or Alberta.")
        else:
            province, province_source = canon, "user"
            if preset is not None and preset["province"] != canon:
                c.warning("W_PROVINCE_MISMATCH", n, "province",
                          city + " is in " + preset["province"] + " but province is "
                          + canon + "; tax uses " + canon + ".")
    elif preset is not None:
        province, province_source = preset["province"], "preset"
    else:
        province, province_source = "Ontario", "default"

    # ---- pay: exactly one style ----
    has_hourly = "hourly_rate" in o or "hours_per_week" in o
    has_salary = "annual_salary" in o
    pay_style, hourly_rate, hours_per_week, annual_salary = None, None, None, None
    if has_hourly and has_salary:
        c.error("E_BOTH_PAY", n, "pay",
                "give EITHER `hourly_rate` + `hours_per_week` OR `annual_salary`, not both.")
    elif not has_hourly and not has_salary:
        c.error("E_NO_PAY", n, "pay",
                "no pay given; add `hourly_rate` + `hours_per_week` OR `annual_salary`.")
    elif has_hourly:
        pay_style = "hourly"
        hourly_rate = _money(c, n, o, "hourly_rate", "hourly_rate", True, positive=True)
        hours_per_week = _money(c, n, o, "hours_per_week", "hours_per_week", True, positive=True)
        if hours_per_week is not None and hours_per_week > 80:
            c.error("E_RANGE", n, "hours_per_week",
                    "`hours_per_week` is " + fmt_num(hours_per_week) + "; it must be 80 or less.")
            hours_per_week = None
        elif hours_per_week is not None and hours_per_week > 60:
            c.warning("W_LONG_HOURS", n, "hours_per_week",
                      "`hours_per_week` is " + fmt_num(hours_per_week) + "; double-check that is right.")
    else:
        pay_style = "salary"
        annual_salary = _money(c, n, o, "annual_salary", "annual_salary", True, positive=True)

    # ---- term ----
    term_weeks = None
    tw = o.get("term_weeks")
    if tw is None:
        c.error("E_MISSING", n, "term_weeks",
                "missing required field `term_weeks` (co-op terms are usually 16).")
    elif not is_number(tw) or not float(tw).is_integer() or tw <= 0:
        c.error("E_TERM", n, "term_weeks",
                "`term_weeks` must be a positive whole number of weeks, got " + _describe(tw) + ".")
    else:
        term_weeks = int(tw)

    # ---- arrangement ----
    arrangement = o.get("arrangement")
    if arrangement is None:
        c.error("E_MISSING", n, "arrangement",
                "missing required field `arrangement` (remote, hybrid, or onsite).")
    elif arrangement not in ARRANGEMENTS:
        c.error("E_ARRANGEMENT", n, "arrangement",
                "`arrangement` must be remote, hybrid, or onsite, got " + _describe(arrangement) + ".")
        arrangement = None

    # ---- rent ----
    rent, rent_source = None, None
    if "rent_per_month" in o and o["rent_per_month"] is not None:
        rent = _money(c, n, o, "rent_per_month", "rent_per_month", True)
        rent_source = "user"
    elif preset is not None:
        rent, rent_source = preset["rent_per_month"], "preset"
    else:
        c.error("E_MISSING", n, "rent_per_month",
                "missing `rent_per_month` and there is no city preset to start from.")

    # ---- commute ----
    commute = o.get("commute")
    mode = None
    transit, transit_source = 0.0, "n/a"
    km, cost_km, parking, days = 0.0, 0.0, 0.0, 0.0
    parking_source, days_source = "n/a", "n/a"
    if commute is None:
        if arrangement == "remote":
            mode = "none"
        else:
            c.error("E_MISSING", n, "commute",
                    "missing `commute`; add {\"mode\": \"transit\"}, {\"mode\": \"driving\", ...}, or {\"mode\": \"none\"} if remote.")
    elif not isinstance(commute, dict):
        c.error("E_NOT_OBJECT", n, "commute",
                "`commute` must be an object like {\"mode\": \"transit\"}.")
    else:
        mode = commute.get("mode")
        if mode not in COMMUTE_MODES:
            c.error("E_COMMUTE_MODE", n, "commute.mode",
                    "`commute.mode` must be transit, driving, or none, got " + _describe(mode) + ".")
            mode = None
        for k in commute:
            if k.startswith("_"):
                continue
            if k not in ALL_COMMUTE_FIELDS:
                c.warning("W_UNKNOWN_FIELD", n, "commute." + k,
                          "unknown field `commute." + k + "` was ignored.")
            elif mode is not None and k not in COMMUTE_FIELDS[mode]:
                c.warning("W_IGNORED_FIELD", n, "commute." + k,
                          "`commute." + k + "` is ignored when the mode is " + mode + ".")

    if mode == "none" and arrangement == "onsite":
        c.error("E_ONSITE_NO_COMMUTE", n, "commute.mode",
                "an onsite job needs a commute; use transit or driving (walking or cycling: transit with transit_pass_per_month 0).")
    elif mode == "none" and arrangement == "hybrid":
        c.warning("W_HYBRID_NO_COMMUTE", n, "commute.mode",
                  "hybrid job with no commute cost; add one unless you really walk or cycle.")
    elif mode in ("transit", "driving") and arrangement == "remote":
        c.warning("W_REMOTE_COMMUTE", n, "commute.mode",
                  "remote job with a " + mode + " cost; it is counted, but check you need it.")

    if mode == "transit":
        if commute.get("transit_pass_per_month") is not None:
            transit = _money(c, n, commute, "transit_pass_per_month", "commute.transit_pass_per_month", True)
            transit_source = "user"
        elif preset is not None:
            transit, transit_source = preset["transit_pass_per_month"], "preset"
        else:
            c.error("E_MISSING", n, "commute.transit_pass_per_month",
                    "missing `commute.transit_pass_per_month` and there is no city preset to start from.")
    elif mode == "driving":
        km = _money(c, n, commute, "km_per_day", "commute.km_per_day", True)
        cost_km = _money(c, n, commute, "cost_per_km", "commute.cost_per_km", True)
        if commute.get("parking_per_month") is not None:
            parking = _money(c, n, commute, "parking_per_month", "commute.parking_per_month", True)
            parking_source = "user"
        else:
            parking, parking_source = 0.0, "assumed"
            c.warning("W_ASSUMED", n, "commute.parking_per_month",
                      "no `commute.parking_per_month`; assuming free parking (0).")
        if commute.get("days_per_week") is not None:
            d = commute.get("days_per_week")
            if not is_number(d) or d <= 0 or d > 7:
                c.error("E_RANGE", n, "commute.days_per_week",
                        "`commute.days_per_week` must be more than 0 and at most 7, got " + _describe(d) + ".")
                days = None
            else:
                days, days_source = float(d), "user"
        elif arrangement is not None:
            days, days_source = float(DEFAULT_DRIVING_DAYS[arrangement]), "assumed"
            c.warning("W_ASSUMED", n, "commute.days_per_week",
                      "no `commute.days_per_week`; assuming " + fmt_num(days)
                      + " driving days a week for a " + arrangement + " job.")

    other = _items(c, n, o, "other_monthly", False)
    moving = _items(c, n, o, "moving_costs", False)
    lumps = _items(c, n, o, "lump_sums", True)

    if any(i["level"] == "error" for i in c.issues[start:]):
        return None
    return {
        "label": label,
        "city": city,
        "province": province,
        "province_source": province_source,
        "pay_style": pay_style,
        "hourly_rate": hourly_rate,
        "hours_per_week": hours_per_week,
        "annual_salary": annual_salary,
        "term_weeks": term_weeks,
        "arrangement": arrangement,
        "rent_per_month": rent,
        "rent_source": rent_source,
        "commute_mode": mode,
        "transit_pass_per_month": transit,
        "transit_source": transit_source,
        "km_per_day": km,
        "cost_per_km": cost_km,
        "parking_per_month": parking,
        "parking_source": parking_source,
        "days_per_week": days,
        "days_source": days_source,
        "other_monthly": other,
        "moving_costs": moving,
        "lump_sums": lumps,
    }


def validate(data):
    """Return (offers, issues). `offers` only contains offers without errors."""
    c = _Collector()
    if isinstance(data, list):
        raw_offers = data
    elif isinstance(data, dict):
        for k in data:
            if k != "offers" and not k.startswith("_"):
                c.warning("W_UNKNOWN_FIELD", None, k, "unknown top-level field `" + k + "` was ignored.")
        raw_offers = data.get("offers")
    else:
        raw_offers = None
    if not isinstance(raw_offers, list):
        c.error("E_NO_OFFERS", None, "offers",
                "the file must be an object with an `offers` list (run `init` for an example).")
        return [], c.issues
    if len(raw_offers) == 0:
        c.error("E_NO_OFFERS", None, "offers", "the `offers` list is empty; add at least one offer.")
        return [], c.issues
    offers = []
    seen = set()
    for i, o in enumerate(raw_offers):
        norm = _offer(c, i + 1, o, seen)
        if norm is not None:
            offers.append(norm)
    return offers, c.issues


def has_errors(issues):
    return any(i["level"] == "error" for i in issues)


def format_issue(number, issue):
    where = "file" if issue["offer"] is None else "offer " + str(issue["offer"])
    if issue["field"]:
        where += ", " + issue["field"]
    return (str(number) + ". " + issue["level"].upper() + " " + issue["code"]
            + " (" + where + "): " + issue["message"])


def format_issues(issues):
    """Number issues: errors first, then warnings (numbering starts at 1)."""
    ordered = ([i for i in issues if i["level"] == "error"]
               + [i for i in issues if i["level"] == "warning"])
    return "\n".join(format_issue(k + 1, i) for k, i in enumerate(ordered))


def load_offers(data):
    """Validate and return (offers, warnings); raise OffersError on any error."""
    offers, issues = validate(data)
    if has_errors(issues):
        raise OffersError(issues)
    return offers, [i for i in issues if i["level"] == "warning"]
