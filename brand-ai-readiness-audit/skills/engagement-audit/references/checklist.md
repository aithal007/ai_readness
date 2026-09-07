# Engagement — checks and thresholds

| Check | Threshold | Severity |
|---|---|---|
| Not HTTPS | final resolved URL is `http:` | critical |
| No viewport meta | any sampled page | high |
| Unreachable visitor goal | no page or homepage link matching the goal | high if `contact`, else medium |
| Goal buried | shortest path over 3 clicks from the homepage | medium |
| No H1 on homepage | zero H1 elements | medium |
| No value proposition | no H1 **and** no meta description | high |
| No on-site search | over 40 internal links and no search input found | medium |
| No call to action | ≥half of pages over 150 words have no CTA phrasing | medium |
| Dead-end pages | substantive page with ≤1 internal link | low |
| Missing alt text | over 50% of images across ≥8 images | medium |
| Render-blocking scripts | over 4 sync external scripts in `<head>` | medium |
| Unlabelled form fields | ≥3 inputs with no label, aria-label, title or placeholder | low |

## Goal-path reachability

The distinctive check. Rather than scoring isolated page attributes, it walks
the crawled link graph breadth-first from the homepage and measures click depth
to the destinations visitors actually arrive for:

| Goal | Matched by |
|---|---|
| `contact` | `/contact`, `/get-in-touch`, `/support`, `/help` |
| `pricing` | `/pricing`, `/plans`, `/rates`, `/fees`, `/tuition` |
| `about` | `/about`, `/who-we-are`, `/company`, `/team` |
| `offering` | `/product`, `/services`, `/solutions`, `/shop`, `/courses`, `/programs` |

A goal is only reported missing if it appears neither in the crawled graph nor
in the homepage's links, which avoids penalising a site whose crawl was cut
short by the page budget.

**The most common false positive here**: the page exists but the navigation is
rendered client-side, so it never appeared in the crawl. Always check the
crawl-render findings before telling someone a page is missing when it is
really just unlinked in HTML.

## Known limits

- **Alt-text coverage** counts every `<img>` with a `src`, including decorative
  icons that correctly carry `alt=""`. A low percentage means review, not that
  every instance is a defect.
- **CTA detection** is a fixed vocabulary (buy now, shop now, add to cart, get
  started, start free, sign up, book a demo, request a demo, contact us, try
  free, subscribe, get a quote, apply now, book now, schedule a call). A clear
  but unusually worded CTA will read as missing.
- **The 40-link search threshold** is a rough "too large to browse by hand"
  heuristic, not a precise cutoff.
- **Performance** is inferred from markup only — script counts and blocking
  attributes. No page is actually timed, so this is a structural proxy for load
  behaviour rather than a measurement of it.

## Never recommend

Chatbots, popups or newsletter interstitials as engagement fixes. Nothing in
the evidence base supports them, and interstitials harm both experience and
crawlability.
