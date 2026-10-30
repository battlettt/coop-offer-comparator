# Money Tools: chapter notes for the portfolio site

## Chapter heading

**Pay is not what you *keep*.**

## Thesis line

> A paycheque is a promise and take-home is the truth: put two co-op offers
> side by side after the city takes its cut, and the "better" job is
> sometimes the one that pays less.

## Card copy (card 17)

- **Title:** Co-op Offer Comparator
- **Tech line:** 17 / python money tools
- **Meta:** Co-op offer comparison by take-home pay · shipped v1
- **Description:** Co-op Offer Comparator ranks job offers by what you keep,
  not the headline rate: estimated income tax, CPP and EI (each its own
  line), rent, commuting, moving costs and signing bonuses, compared per
  month so a 16-week and a 24-week term are fair to each other. It calls
  offers within $25 a month "about tied", works out what pay one city would
  need to match another, and shows whether a $200 rent guess would flip the
  ranking. A standard-library Python CLI and a static browser demo share
  bit-identical math, and every figure is labelled an estimate.

## The figure

`docs/figure.svg` is a grouped horizontal bar chart. It is generated from
the calculator by `tools/make_figure.py`, so it cannot drift from the code.
It compares **monthly gross pay** (blue) with **monthly take-home** (orange)
for the two SYNTHETIC EXAMPLE offers in `samples/offers.json`:

| Offer (synthetic, 16 weeks) | Gross / month | Take-home / month |
|---|---:|---:|
| Toronto data analyst, $28/h | $4,549.65 | $677.93 |
| Waterloo QA developer, $24/h | $4,159.68 | $1,640.89 |

The bars tell the story at a glance. The Toronto gross bar is the longer
one, but its take-home bar is the shorter one. The chart has a legend and a
direct value label on every bar, so colour is never the only cue. The SVG
`<title>` and `<desc>` state that the figures are a synthetic example and
estimates. The colours passed a colour-vision-deficiency palette check in
both light mode (adjacent ΔE 24.7) and dark mode (ΔE 26.8), and each bar has
at least 3:1 contrast against the surface.

For the site chapter, use an inline version of the same two-offer bar pair
(as Fig. 5), styled like the earlier standalone chapters. Music used an
inline Camelot wheel and Entrepreneurship an inline break-even crossing.
The inline version must carry the same `role="img"`, `<title>` and `<desc>`
wording: synthetic example, estimates.
