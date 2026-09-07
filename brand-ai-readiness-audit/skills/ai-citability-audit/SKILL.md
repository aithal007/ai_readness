---
name: ai-citability-audit
description: Check whether a page has the properties that measurably separate pages AI answer engines quote from pages they ignore - explicit prices, recency, technical specifications, quotable statistics and attributed evidence, confident rather than hedged claims, coverage of the page's own topic terms, and secondarily its heading depth, section length and emphasis structure. Use when a site is reachable and readable but still never cited, when asked how to get quoted or recommended by ChatGPT, Perplexity or AI Overviews, or as part of a broader AI-readiness or GEO audit.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read
metadata:
  marketplace: brand-ai-readiness-audit
  stage: "3"
---

# AI Citability Audit

Being reachable and readable only qualifies a page to compete. This skill asks
the next question: is it the *kind* of page that actually gets quoted?

## When to use

After `crawl-render-audit` confirms the page is readable, or whenever someone
asks how to get cited or recommended by AI assistants.

## Inputs

An `evidence.json` bundle from `crawl-render-audit`.

## Procedure

```
python3 scripts/analyze_citability.py --evidence evidence.json
```

Given `--url` instead, it will invoke the shared collector itself, which is
slower and only appropriate for standalone use.

## The two tiers, and why the order matters

**Tier 1 — gatekeepers.** In a 252,000-trial controlled study across six
current models, these showed odds ratios above 100. Failing one can eliminate
citation odds regardless of every other strength on the page.

- Coverage of the page's own topic terms in its opening text
- An explicit price on commercial pages
- Recency — and note that an *old* date measured worse than no date, while a
  *recent* date beat both, so the fix is to refresh and re-date, never to strip
  dates
- Technical specifications
- Quotable evidence — statistics, attributed quotes, outbound authority
- Confident rather than hedged claims
- Depth of coverage

**Tier 2 — structure.** Heading depth, 150-300 word sections, emphasis density,
an opening summary. Worth doing, but only after tier 1 passes.

This ordering resolves a real contradiction in the literature. One head-to-head
study found formatting negligible; a structural study measured +17.3%. Both
hold, because formatting cannot rescue a page that fails a gatekeeper. The
analyzer therefore caps tier-2 severity while any tier-1 gatekeeper is failing,
and says so in the finding text.

## Gotchas

- **Never recommend keyword stuffing.** It measured the worst-performing tactic
  tested, at -8.3% visibility. Tier-1 term coverage means stating the subject
  once, early, in plain language — not repetition.
- **Never recommend a blanket rewrite.** Applying the classic optimization
  playbook to body text degraded retrieval by between 1% and 36%. On pages that
  are already well written, all nine tactics tested *reduced* visibility. Target
  specific gaps only.
- **Do not recommend adding persuasive or authoritative tone.** It measured no
  significant improvement. Removing hedges is what is supported — that is a
  precision edit, not a salesmanship edit.
- **Do not tell a top-ranked page to do this.** When every competing source is
  optimized, gains accrue to lower-ranked pages while the top-ranked one can
  lose 20-30%. This work is most valuable for pages that are currently losing.
- **Bulleting everything backfires.** Lists suit specs and comparisons; the
  core quotable claim performs better as prose, because heavy fragmentation
  makes a passage harder to quote coherently.

## Output

Findings JSON per `../audit-orchestrator/references/report_schema.md`, each
carrying `signal_tier` (1 or 2) and `evidence_tier`. Effect sizes and sources
for every threshold are in
[../audit-orchestrator/references/evidence-base.md](../audit-orchestrator/references/evidence-base.md).
