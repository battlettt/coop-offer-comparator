"""City presets: ESTIMATES, not quotes.

Each preset is a rough 2026 planning figure for a typical one-bedroom
apartment and a regular adult monthly transit pass. They are starting
points only: real listings vary a lot by neighbourhood, building, and
whether you share. Any value you put in your offers file overrides the
preset, and every report says which numbers came from a preset and which
you supplied.

Sources (described, not quoted): rough 2026 planning figures based on the
general level of public rental listings and published transit fares in
each city. They are not quotes and are not updated automatically.
"""

PRESET_SOURCE_NOTE = (
    "rough 2026 planning figures, not quotes: typical one-bedroom rent and "
    "a regular adult monthly transit pass"
)

CITY_PRESETS = {
    "Toronto": {"province": "Ontario", "rent_per_month": 2450.0, "transit_pass_per_month": 160.0},
    "Waterloo": {"province": "Ontario", "rent_per_month": 1900.0, "transit_pass_per_month": 100.0},
    "Ottawa": {"province": "Ontario", "rent_per_month": 2050.0, "transit_pass_per_month": 136.0},
    "Vancouver": {"province": "British Columbia", "rent_per_month": 2700.0, "transit_pass_per_month": 110.0},
    "Montreal": {"province": "Quebec", "rent_per_month": 1750.0, "transit_pass_per_month": 104.0},
    "Calgary": {"province": "Alberta", "rent_per_month": 1750.0, "transit_pass_per_month": 118.0},
}

# Accepted spellings -> canonical preset city name.
CITY_ALIASES = {name.lower(): name for name in CITY_PRESETS}
CITY_ALIASES["montréal"] = "Montreal"


def find_preset(city):
    """Return (canonical_name, preset) or (None, None) if there is no preset."""
    if not isinstance(city, str):
        return None, None
    key = city.strip().lower()
    name = CITY_ALIASES.get(key)
    if name is None:
        return None, None
    return name, CITY_PRESETS[name]


def presets_snapshot():
    return {
        "source_note": PRESET_SOURCE_NOTE,
        "cities": {k: dict(v) for k, v in CITY_PRESETS.items()},
        "aliases": dict(CITY_ALIASES),
    }
