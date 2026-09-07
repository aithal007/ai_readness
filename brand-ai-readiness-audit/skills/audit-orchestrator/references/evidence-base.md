# Evidence base

Every check in this marketplace traces to something measured. This file records
what, how strongly, and — just as important — what the evidence does **not**
support.

Findings carry an `evidence_tier` so a reader can tell the difference:

| Tier | Meaning |
|---|---|
| `measured` | Controlled study with a reported effect size or odds ratio |
| `correlational` | Observed association, plausible mechanism, confounders not excluded |
| `speculative` | Reasonable mechanism, no measured citation benefit |

## Tier 1 — gatekeepers

From a controlled study of 252,000 trials across six current models, testing
pairs of candidate sources head to head. Odds ratios are for being cited.
Values reported as ">10k" indicate a decisive win rather than a literal ratio.

| Signal | Odds ratio range | Note |
|---|---|---|
| On-topic / query-term coverage | 221 – >10k | Largest single gatekeeper measured |
| Explicit price present | 6.3 – >10k | Unanimous across all six models |
| Recency (recent vs old) | 14 – >10k | See the date asymmetry below |
| Technical specifications present | 8.6 – 243 | Strongest completeness differentiator |
| Depth of coverage | 4.0 – >10k | Thin pages rarely carry quotable substance |
| Evidence supporting claims | 2.1 – >10k | Significant in 4+ of 6 models |
| Confident vs hedged claims | 2.7 – 599 | *Removing hedges* is what is supported |
| Comparison against alternatives | 1.6 – 7.5 | Moderate but consistent |
| Internal consistency | 1.7 – 4.1 | Self-contradiction is measurably costly |
| Retrieval position 1 vs 2 | 1,795 – >10k | Dominates everything; on-page work is conditional on it |

**The date asymmetry.** A recent date beat both alternatives. An *old* date
measured worse than **no** date (no-vs-old odds 1.3–2.3). So the correct advice
is always refresh-and-re-date, and never strip dates to appear evergreen.

## Content lifts

From the original generative-engine-optimization study, replicated on a live
engine:

- Adding statistics: **+30.6%** visibility, up to **+37%** subjective impression
- Adding attributed quotations: **+41.0%**, the largest single lift measured
- Citing sources: **+27.5%**
- Best pairing tested (fluency + statistics): **+35.8%**

A later feature-level study independently reproduced the ranking:
statistics > cite-sources > quotation > structure > language.

## Position within the page

From the long-context retrieval literature. With 20 candidate documents, a fact
in first position was used 75.8% of the time, in the middle 53.8%, at the end
63.2%. The closed-book baseline — not supplying the document at all — was 56.1%.

**A fact buried mid-passage performed worse than not supplying the page.** The
trough deepens as the passage grows (61.2% → 53.8% → 50.9% at 10, 20 and 30
documents). This is why section length and fact position are audited at all.

Related: keeping related facts adjacent matters, since separating evidence with
intervening material degrades multi-hop retrieval.

## Tier 2 — structure

Structural fields (title, meta description, heading hierarchy) measured roughly
**+22% retrieval hit rate** and **+2.7 mean rank positions**. But the same work
found that the generator "primarily references body text when forming
responses". So the division of labour is:

**structure gets you found; body text gets you quoted.**

Target ranges from a structural-engineering study, used as defaults to check
against rather than as measured lifts: heading depth 3–5, sections of 150–300
words, structured-format ratio 0.25–0.35, emphasis density 0.05–0.10.

## The tier ordering exists to resolve a real contradiction

One head-to-head study concluded formatting has "negligible impact". A
structural study measured +17.3%. Both are credible, and they are reconciled by
scope: the head-to-head design tests pages that may fail a gatekeeper, where
formatting cannot rescue them; the structural study measured already-relevant
pages. Hence tier 2 is capped in severity while tier 1 is failing.

## Do not recommend

Each of these is either measured ineffective, measured harmful, or classed as
manipulation. `evidence-critic` strips recommendations matching them.

**Measured counterproductive**

- **Keyword stuffing** — −8.3% visibility, the worst tactic tested. Distinct
  from tier-1 term *coverage*, which means stating the subject once, early.
- **Blanket body-text rewriting** — degraded retrieval by 1–36% across the
  eight classic tactics; a learned-rewrite variant was worst at −36%.
- **Optimizing an already-good page** — on already-fluent pages, all nine
  tactics tested *reduced* visibility. A saturation effect.
- **"Apply everything"** — combined body plus structural work underperformed
  structural-only.
- **Unique-word / lexical enrichment** — negative on human-written pages.
- **Persuasive or authoritative tone** — no significant improvement.
- **Optimizing a rank-1 page** — in a fully optimized field the top-ranked page
  *lost* 20–30% to these same tactics.
- **Burying key facts mid-page** — worse than not supplying the page.
- **Heavy bulleting of the core claim** — fragmentation makes a passage harder
  to quote coherently. Lists suit specs; prose suits the claim.

**Manipulation — never recommend at any strength**

Seven primitives, all detectable and increasingly detected: unsupported fit
claims; omitting caveats that affect fit; relevance flooding; authority
laundering (astroturfed reviews, self-owned "independent" comparison sites,
unlabelled sponsorship); evidence padding (evidence-shaped language with no
real source); salience manipulation; and any text addressed to the model
itself. Hidden markup belongs here too — across five AI systems tested, none
used hidden page JSON-LD, injected JSON-LD, hidden microdata or hidden RDFa.

## Where the field over-claims

**Schema markup does not cause AI citations.** The uncontrolled studies showing
a benefit do not adjust for ranking position, and any schema study that does
not control for rank is mostly measuring rank. The controlled work points the
other way: 1,885 pages adding JSON-LD saw AI-Overview citations fall 4.6%
relative to controls; visibility distributions were near-identical across
schema-coverage buckets; facts planted in FAQ schema went unused by every
platform tested; and a corrected re-analysis collapsed the association to null.

Schema remains worth recommending for **entity disambiguation** and **search
rich results**. This marketplace words it that way everywhere.

**llms.txt has no demonstrated effect.** Of 137,000 domains studied, 97% of
published llms.txt files received zero requests; a ~300,000-domain study found
no significant correlation with AI citations; Google has said it does not
support it. Reported here as `speculative`, never scored as a defect.

**Blocking training crawlers costs nothing.** Google states blocking
Google-Extended "does not impact a site's inclusion in Google Search"; OpenAI
states disallowing GPTBot only opts out of training. Only search-index and
live-fetch agents affect citation visibility.

## Scope and honesty limits

- Brand stature dominates on-page factors. Observed visibility ran ~73% for
  tier-1 global brands, ~44% mid-market, ~11% niche. On-page work cannot close
  that gap, and an audit should not imply otherwise.
- Roughly three quarters of AI citations point at third-party pages rather than
  the brand's own domain, and ranked comparison content is the single largest
  cited content format. A site-only audit therefore addresses a minority of the
  surface — which is why off-site corroboration is a first-class check here.
- Engines differ substantially in how often they cite sources at all, so a
  single blended "AI visibility score" would be misleading.
- Several figures above come from 2026 preprints of varying rigour. Directions
  are corroborated across independent sources; exact decimals should not be
  quoted to users as settled fact.
