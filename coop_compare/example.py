"""The example offers file written by `python -m coop_compare init`.

SYNTHETIC EXAMPLE: the offers below are made up for teaching. JSON has no
comments, so explanations live in keys that start with "_" (the validator
ignores them). samples/offers.json is an identical copy; a test checks it.
"""

EXAMPLE_JSON = r"""{
  "_note": "SYNTHETIC EXAMPLE. These two co-op offers are made up for teaching. They are not real employers, real offers, or real pay. Every tax, rent and transit figure computed from them is an ESTIMATE, not payroll advice.",
  "offers": [
    {
      "_comment": "SYNTHETIC EXAMPLE: higher hourly rate in a pricier city, with a moving bill and a signing bonus.",
      "label": "Toronto data analyst (synthetic)",
      "city": "Toronto",
      "hourly_rate": 28.0,
      "hours_per_week": 37.5,
      "term_weeks": 16,
      "arrangement": "hybrid",
      "_rent_note": "rent_per_month left out on purpose: the Toronto preset (an estimate) fills it in.",
      "commute": {"mode": "transit"},
      "other_monthly": [
        {"name": "phone plan", "amount": 45},
        {"name": "groceries", "amount": 380}
      ],
      "moving_costs": [
        {"name": "moving van", "amount": 350}
      ],
      "lump_sums": [
        {"name": "signing bonus", "amount": 1000, "taxable": true}
      ]
    },
    {
      "_comment": "SYNTHETIC EXAMPLE: lower hourly rate, shared apartment near campus, no move.",
      "label": "Waterloo QA developer (synthetic)",
      "city": "Waterloo",
      "hourly_rate": 24.0,
      "hours_per_week": 40,
      "term_weeks": 16,
      "arrangement": "onsite",
      "rent_per_month": 1150,
      "commute": {"mode": "transit"},
      "other_monthly": [
        {"name": "phone plan", "amount": 45},
        {"name": "groceries", "amount": 380}
      ]
    }
  ]
}
"""
