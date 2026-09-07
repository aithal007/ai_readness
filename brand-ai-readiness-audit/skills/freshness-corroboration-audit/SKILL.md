---
name: freshness-corroboration-audit
description: Check whether a website's facts are current, agree with each other, and are backed by anyone other than the brand itself - stale copyright and updated dates, placeholder content that outlived its promise, contradictory phone numbers or emails across the site's own pages, and third-party corroboration including whether apparently independent sources actually trace back to a single press release. Use when an AI assistant repeats outdated or wrong facts about a brand, gives low-confidence or hedged answers about it, or when auditing content freshness and external trust signals.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read WebSearch
metadata:
  marketplace: brand-ai-readiness-audit
  stage: "5"
---

# Freshness & Corroboration Audit

Two halves, deliberately using different tools.

**Part A is scripted** — staleness, temporal contradictions, and facts that
disagree with each other across the site's own pages.

**Part B is agent-performed** — whether independent sources agree, and whether
they are genuinely independent. A single-domain crawl structurally cannot see
other domains, so that step is done with live search rather than faked.

## When to use

Stage 5 of the `audit-orchestrator` flow, or standalone when assistants give
outdated, inconsistent or oddly hedged answers about a brand.

## Inputs

An `evidence.json` bundle, and today's real date.

## Part A — scripted

```
python3 scripts/analyze_freshness.py --evidence evidence.json --today <YYYY-MM-DD>
```

Always pass `--today` with the real current date. Sandbox clocks are often
wrong, and every staleness judgement depends on it.

Checks stale copyright and updated years, placeholder or "coming soon" content
that has outlived its promise, conflicting phone numbers and email addresses
across pages, and on-site corroboration signals.

## Part B — off-site corroboration and source independence

Do this yourself; it cannot be scripted.

1. From the bundle, note the brand name and three to five core identity claims
   — what it does, category, founding year, headquarters, flagship offering.
2. Run **two to four** web searches. Keep it bounded; this must stay fast and
   must not hammer a search backend. Useful shapes are the brand name alone,
   the brand name with "wikipedia" or "crunchbase" or "linkedin", and the brand
   name with a specific claim you want to verify.
3. Assess three things:

   **Agreement.** Do independent sources state the same core facts? Note any
   source that contradicts the site.

   **Source independence.** This is the part most audits miss. Three sources
   repeating a claim are not three confirmations if two of them are copies of
   the brand's own press release. Classify each source as the brand's own
   property, a press-release wire or syndication, an aggregator that copies,
   or genuinely independent editorial, reference or regulatory content. Count
   only the last group toward corroboration strength. Where many mentions all
   trace to a single origin, report that pattern explicitly — it looks like
   strength and is not.

   **Mistaken identity.** Does the name collide with an unrelated organisation?
   If results for the brand name are dominated by something else, that is a
   more urgent version of the missing-`sameAs` finding from
   `structured-data-entity-audit`; cross-reference it.

4. Write findings in the standard raw-finding shape and append them to the same
   findings list. Do not emit a separate report.

If no search tool is available, append one low-severity `meta` finding saying
the off-site check could not run. Never invent search results.

## Gotchas

- **Phrase Part B modestly.** Two to four searches is a sample. Write "no
  independent coverage found in a brief search", never "no independent coverage
  exists".
- **Never recommend deleting dates to look evergreen.** Undated content
  measured worse than recently-dated content. Refresh and re-date instead.
- **Do not recommend manufacturing corroboration.** Astroturfed reviews,
  self-owned "independent" comparison sites and unlabelled sponsored placements
  are classed manipulation patterns and are increasingly detected. The
  legitimate route is real coverage, accurate profiles on reference sites, and
  genuine third-party listings.
- **Most citations point away from the brand's own domain.** Own-site fixes
  address only a small share of the surface; the off-site footprint is most of
  it. Weight recommendations accordingly.

## Output

Findings JSON per `../audit-orchestrator/references/report_schema.md`. Check
table in [references/checklist.md](references/checklist.md).
