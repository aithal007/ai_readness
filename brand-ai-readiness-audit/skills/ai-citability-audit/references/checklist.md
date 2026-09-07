# Citability — checks, thresholds and effect sizes

Full sourcing in
[../../audit-orchestrator/references/evidence-base.md](../../audit-orchestrator/references/evidence-base.md).

## Tier 1 — gatekeepers

Failing one of these can eliminate citation odds regardless of everything else
on the page, so they are audited first and weighted hardest.

| Check | Threshold | Severity | Measured effect |
|---|---|---|---|
| Topic-term coverage | under 50% of title/H1 terms in the first 200 words | high if over half the pages, else medium | OR 221 – >10k, the largest gatekeeper |
| Explicit price | commercial page with no currency figure | high | OR 6.3 – >10k, unanimous across 6 models |
| Stale dates | most recent year ≥3 years old | high | OR 14 – >10k |
| Undated content | no date on ≥half the pages | medium | recent beats undated in every model |
| No quotable evidence | over 250 words with zero statistics, zero attributed quotes and zero outbound links | high if widespread | statistics +30.6%, quotations +41.0% |
| Hedging | over 3 hedge terms per 100 words | medium | OR 2.7 – 599 |
| Missing specs | commercial page with under 3 attribute:value pairs and no table | medium | OR 8.6 – 243 |
| No comparison content | zero comparison markers across ≥2 commercial pages | medium | OR 1.6 – 7.5 |
| Thin pages | under 150 words on ≥half the sample | medium | OR 4.0 – >10k |

**The date asymmetry matters.** An old date measured *worse* than no date,
while a recent date beat both. So never advise stripping dates to look
evergreen — refresh and re-date.

**Commercial-page detection is deliberately strict.** A page counts only on
positive transactional evidence: an actual currency figure, a genuine cart CTA
("add to cart", "buy now", "add to basket", "proceed to checkout"), or a
dedicated `/pricing`-style path. During development, matching the substring
"buy" in a URL wrongly flagged a government guidance page at
`/buying-your-first-home`, and a newsletter "subscribe" link wrongly marked a
government department page commercial. Both were false positives; hence the
narrow list.

## Tier 2 — structure

Only pays once tier 1 passes, so these are capped at medium while any tier-1
gatekeeper is failing.

| Check | Target | Severity |
|---|---|---|
| Long sections | ≥2 sections over 300 words | medium |
| Heading depth | under 2 on a page over 400 words | low |
| Intro summary | under 25 words between H1 and first subheading on a page over 300 words | low |

Reference targets from the structural literature, used as defaults rather than
as measured lifts: heading depth 3–5, sections 150–300 words, structured-format
ratio 0.25–0.35, emphasis density 0.05–0.10.

## Why the tiers are ordered

One head-to-head study found formatting "negligible"; a structural study
measured +17.3%. Both are credible and the scope reconciles them — formatting
cannot rescue a page that fails a gatekeeper. Structure gets a page **found**;
body text gets it **quoted**.

## Position within the page

With 20 candidate documents, a fact in first position was used 75.8% of the
time, in the middle 53.8%, at the end 63.2% — against a 56.1% baseline for not
supplying the document at all. **A fact buried mid-passage performed worse than
not supplying the page**, and the trough deepens as the page grows. That is why
section length and fact position are audited rather than treated as style.

## Never recommend

Keyword stuffing (−8.3%, worst tactic tested); blanket rewriting (−1% to −36%
retrieval); optimizing an already-good page (all nine tactics reduced
visibility); persuasive tone (no significant effect); unique-word enrichment
(negative); bulleting the core claim (fragmentation hurts quotability); and
optimizing a rank-1 page (it can lose 20–30%).
