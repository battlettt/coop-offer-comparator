"""Simplified 2026 payroll tables (ESTIMATES, not payroll advice).

Every number in this module is a rough 2026 planning figure. Real payroll
uses many more credits, surtaxes and rules than this. The tables are kept
deliberately small so a beginner can read them, and so the browser demo
(docs/app.js) can carry an identical copy. A parity test checks that the
two copies match exactly.

What is simplified on purpose:
- Income tax uses marginal brackets plus ONE credit: the basic personal
  amount, credited at the lowest bracket rate. No CPP/EI credits, no
  Canada employment amount, no Ontario surtax or health premium, no
  Alberta/BC low-income reductions.
- Quebec residents get the 16.5% federal abatement and pay QPP, the lower
  Quebec EI rate, and QPIP instead of CPP/regular EI.
- CPP2 (the second, higher earnings ceiling) is ignored; co-op earnings
  are far below it.
"""

TAX_YEAR = 2026

WEEKS_PER_YEAR = 52
# Average weeks in a month: 52 weeks / 12 months = 4.333...
# We use the rounded constant 4.333 everywhere (Python AND the demo).
WEEKS_PER_MONTH = 4.333

# (upper limit of bracket, rate). The last bracket has limit None (no cap).
FEDERAL = {
    "brackets": [
        (58523.0, 0.14),
        (117045.0, 0.205),
        (181440.0, 0.26),
        (258482.0, 0.29),
        (None, 0.33),
    ],
    "basic_personal_amount": 16452.0,
}

# Federal tax reduction for Quebec residents (Quebec runs its own programs).
QUEBEC_ABATEMENT = 0.165

PROVINCES = {
    "Ontario": {
        "code": "ON",
        "brackets": [
            (53891.0, 0.0505),
            (107785.0, 0.0915),
            (150000.0, 0.1116),
            (220000.0, 0.1216),
            (None, 0.1316),
        ],
        "basic_personal_amount": 12989.0,
    },
    "British Columbia": {
        "code": "BC",
        "brackets": [
            (50363.0, 0.0506),
            (100728.0, 0.077),
            (115648.0, 0.105),
            (140430.0, 0.1229),
            (190405.0, 0.147),
            (265545.0, 0.168),
            (None, 0.205),
        ],
        "basic_personal_amount": 12932.0,
    },
    "Quebec": {
        "code": "QC",
        "brackets": [
            (54345.0, 0.14),
            (108680.0, 0.19),
            (132245.0, 0.24),
            (None, 0.2575),
        ],
        "basic_personal_amount": 18571.0,
    },
    "Alberta": {
        "code": "AB",
        "brackets": [
            (61200.0, 0.08),
            (154259.0, 0.10),
            (185111.0, 0.12),
            (246813.0, 0.13),
            (370220.0, 0.14),
            (None, 0.15),
        ],
        "basic_personal_amount": 22769.0,
    },
}

# Accepted spellings -> canonical province name.
PROVINCE_ALIASES = {
    "ontario": "Ontario", "on": "Ontario",
    "british columbia": "British Columbia", "bc": "British Columbia",
    "quebec": "Quebec", "québec": "Quebec", "qc": "Quebec",
    "alberta": "Alberta", "ab": "Alberta",
}

# CPP (outside Quebec) / QPP (Quebec). Contributions are charged on
# earnings between the basic exemption and the yearly maximum pensionable
# earnings (YMPE), so there is an annual maximum contribution.
PENSION = {
    "ympe": 74600.0,
    "basic_exemption": 3500.0,
    "cpp_rate": 0.0595,
    "qpp_rate": 0.064,
}

# Employment Insurance premiums are charged on earnings up to the maximum
# insurable earnings (MIE), so there is also an annual maximum premium.
EI = {
    "max_insurable": 68900.0,
    "rate": 0.0163,
    "quebec_rate": 0.0130,
}

# Quebec Parental Insurance Plan (Quebec only).
QPIP = {
    "max_insurable": 103000.0,
    "rate": 0.00494,
}


def tables_snapshot():
    """All tables as plain JSON-able data (used by the demo parity test)."""
    def br(rows):
        return [[limit, rate] for limit, rate in rows]

    return {
        "tax_year": TAX_YEAR,
        "weeks_per_year": WEEKS_PER_YEAR,
        "weeks_per_month": WEEKS_PER_MONTH,
        "federal": {
            "brackets": br(FEDERAL["brackets"]),
            "basic_personal_amount": FEDERAL["basic_personal_amount"],
        },
        "quebec_abatement": QUEBEC_ABATEMENT,
        "provinces": {
            name: {
                "code": p["code"],
                "brackets": br(p["brackets"]),
                "basic_personal_amount": p["basic_personal_amount"],
            }
            for name, p in PROVINCES.items()
        },
        "province_aliases": dict(PROVINCE_ALIASES),
        "pension": dict(PENSION),
        "ei": dict(EI),
        "qpip": dict(QPIP),
    }
