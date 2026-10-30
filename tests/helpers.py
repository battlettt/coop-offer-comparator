"""Shared test helpers. Offers built here are SYNTHETIC EXAMPLES (made up)."""

import json
import os

from coop_compare.model import load_offers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
SAMPLES = os.path.join(ROOT, "samples", "offers.json")
APP_JS = os.path.join(ROOT, "docs", "app.js")


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


def samples():
    with open(SAMPLES, encoding="utf-8") as fh:
        return json.load(fh)


def raw_offer(**overrides):
    """A plain SYNTHETIC hourly offer in Waterloo; override any field."""
    o = {
        "label": "Synthetic offer",
        "city": "Waterloo",
        "hourly_rate": 25.0,
        "hours_per_week": 40,
        "term_weeks": 16,
        "arrangement": "onsite",
        "rent_per_month": 1200,
        "commute": {"mode": "transit", "transit_pass_per_month": 100},
    }
    for k, v in overrides.items():
        if v is None:
            o.pop(k, None)
        else:
            o[k] = v
    return o


def norm(**overrides):
    offers, _ = load_offers({"offers": [raw_offer(**overrides)]})
    return offers[0]


def norm_many(*raws):
    offers, _ = load_offers({"offers": list(raws)})
    return offers
