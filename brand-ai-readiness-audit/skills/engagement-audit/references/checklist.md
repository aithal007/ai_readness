# Engagement Audit -- check reference

## Checks performed by `scripts/check_engagement.py`

| Check | Severity | Why |
|---|---|---|
| Not served over HTTPS | critical | Browsers actively warn visitors off; many AI browse/fetch tools refuse or downgrade insecure requests. |
| No mobile viewport meta tag | high | Mobile browsers render the desktop layout zoomed out; reliably drives mobile bounces. |
| No `<h1>` | medium | Removes the clearest structural cue of page topic. |
| Multiple `<h1>` | low | Dilutes the single-topic structural signal. |
| Heading levels skip (e.g. h1 -> h3) | low | Breaks the implied outline for assistive tech and any outline-parsing system. |
| <50% of images have alt text | medium | Alt text is the plain-text stand-in for image content; without it, facts conveyed only visually are invisible to screen readers and text-only systems. |
| No `<nav>` landmark despite 15+ links | low | Landmark helps distinguish primary navigation from body/footer content. |
| No on-site search despite 40+ links | medium | Large sites are hard to orient in via navigation alone; task-focused visitors bounce rather than dig. |
| No CTA-style wording detected | medium | Without an obvious next action, visitors have to guess what they're supposed to do. |
| 5+ render-blocking `<script>` tags in `<head>` | medium | Delays first paint; slow pages measurably lose visitors before any content renders. |

## CTA word list

`buy now`, `shop now`, `add to cart`, `get started`, `start free`,
`sign up`, `book (a) demo`, `request a demo`, `contact us`, `try (it) free`,
`subscribe`, `learn more`, `download`, `book now`. This is intentionally
broad (includes softer CTAs like "learn more") to avoid false-flagging
sites with a legitimate, low-pressure primary action.

## Known limitations / false-positive risks

- Alt-text coverage counts every `<img>` with a `src`, including small
  decorative icons that legitimately warrant `alt=""` rather than
  descriptive text -- a low percentage is a prompt to look closer, not
  automatic proof every missing alt is a real gap.
- The on-site-search and nav-landmark thresholds (15/40 links) are rough
  heuristics calibrated for "clearly too large to browse by hand," not a
  precise cutoff -- don't treat a site just under the threshold as
  automatically fine.
- CTA detection is a fixed word list; a site with a genuinely clear but
  differently-worded call to action can be a false positive. Spot-check
  before reporting with high confidence.

## Orientation rubric

See [references/orientation_rubric.md](references/orientation_rubric.md)
for the qualitative check described in SKILL.md step 2.
