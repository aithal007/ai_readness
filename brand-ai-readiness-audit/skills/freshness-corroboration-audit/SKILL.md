---
name: freshness-corroboration-audit
description: Checks whether a site's facts look current and internally consistent (stale copyright/updated dates, contradictory phone numbers or prices across its own pages, broken links), plus whether independent third-party sources corroborate the brand's identity -- both on-site signals (press mentions, review-platform links, canonical profile links) and, via live web search, off-site agreement across other domains. Use when auditing why an AI assistant gives outdated, inconsistent, or low-confidence answers about a brand, or as part of a larger AI-discoverability/engagement audit.
license: MIT
allowed-tools: Bash WebSearch
---

# Freshness & Corroboration Audit

Machines trust a fact more when independent sources agree on it, and trust
it less when the source itself looks stale or self-contradictory. This
skill has two halves that use different tools on purpose:

- **Self-consistency and freshness** (on this site only) -- fully scripted,
  deterministic.
- **Cross-web corroboration** (do other, independent sources agree, and is
  this brand's identity unambiguous out there) -- requires live web search,
  so it's an agent-performed step, not a script. A static script fetching
  only the target domain cannot verify agreement across *other* domains.

## When to use

As part of a brand AI-discoverability/engagement audit (normally invoked by
`audit-orchestrator`), or standalone when an assistant's answers about a
brand seem outdated, inconsistent, or oddly low-confidence.

## Inputs

A single URL or bare domain. Optionally, today's date (`--today
YYYY-MM-DD`) if the agent's known current date should override the system
clock -- pass this so "how stale is this" is judged against the actual
current date, not whatever the runtime environment's clock says.

## Procedure

### Part A -- scripted self-consistency checks

```
python3 scripts/check_freshness.py <url> --today <YYYY-MM-DD>
```

This fetches the homepage plus a small same-domain sample, and checks:
copyright/last-updated year staleness, stale `dateModified`/`datePublished`
in JSON-LD, inconsistent phone numbers or prices across the site's own
pages, broken internal links, and on-site corroboration signals (links to
review platforms, press mentions, canonical profile links). Full detail in
[references/checklist.md](references/checklist.md).

### Part B -- agent-performed off-site corroboration (do this yourself, not via a script)

1. Note the brand name and 3-5 core identity facts from the homepage (what
   it is/does, category, HQ or founding facts if stated, flagship
   product/service name).
2. Run a small number of web searches (2-4 is usually enough; don't do more
   -- this must stay fast and avoid hammering a search backend) for the
   brand name plus one or two of those facts, e.g. `"<brand>" wikipedia`,
   `"<brand>" review OR crunchbase OR linkedin`.
3. Check two things from the results:
   - **Agreement**: do independent sources (not the brand's own site, not
     syndicated press releases) state the same core facts? If the brand has
     essentially no independent footprint beyond its own site, that's a
     finding.
   - **Mistaken identity**: does the name collide with an unrelated entity
     (a different company, a common word, a similarly-named product)? If
     search results for the brand name are dominated by something else,
     that's a more urgent version of the `sameAs`-missing finding from
     `structured-data-entity-audit` -- cross-reference it if that skill's
     findings are available.
4. Turn each observation into a finding using the exact same shape the
   script emits (see [references/finding_shape.md](../audit-orchestrator/references/report_schema.md)):
   `title`, `severity`, `category: "discoverability"`, `evidence` (cite the
   specific sources/queries used), `mechanism`, `suggested_action`. Append
   these to the same findings list the script produced -- don't emit a
   separate report.

Keep Part B's evidence honest about its own limits: 2-4 searches is a
sample, not an exhaustive audit. Phrase findings as "no independent mentions
found in a brief search" rather than "no independent mentions exist."

If no live web-search tool is available in the current environment, skip
Part B rather than guessing or fabricating results, and say so explicitly:
emit one low-severity `category: "meta"` finding noting that off-site
corroboration could not be checked. An unverifiable claim reported as
"passing" is worse than an honestly-missing check.

## Output

A JSON array of findings (script output from Part A plus agent-authored
findings from Part B) in the shape documented in
[../audit-orchestrator/references/report_schema.md](../audit-orchestrator/references/report_schema.md).
