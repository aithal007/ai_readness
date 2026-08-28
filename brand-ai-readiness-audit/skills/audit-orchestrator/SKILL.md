---
name: audit-orchestrator
description: Entrypoint for a full brand AI-readiness audit -- runs crawl-render-audit, structured-data-entity-audit, freshness-corroboration-audit, and engagement-audit against a target website, merges their findings, and emits a single structured report (findings with evidence and severity, plus prioritized suggested actions) covering both AI discoverability (why a brand is missed or misrepresented by AI assistants) and on-site engagement (why visitors who arrive don't stay). Use this when asked to audit a website's AI discoverability, GEO, or on-site engagement, or to explain why a brand is invisible/stale/bouncing in AI apps.
license: MIT
allowed-tools: Bash WebSearch
---

# Brand AI-Readiness Audit -- Orchestrator

This is the entrypoint skill for the `brand-ai-readiness-audit` marketplace.
It composes the marketplace's four concern-specific skills into one audit
and emits a single report. It does not duplicate their checks -- it runs
them, collects what they produce, and is responsible for turning that into
a clear, prioritized, schema-compliant report a non-expert can act on.

**Recommend-only.** This skill (and every skill it composes) only reads
public pages over plain GET requests and reports findings. Nothing here
modifies the target site, submits forms, authenticates, or takes any
state-changing action.

## When to use

Whenever asked to audit a website for AI discoverability/citation problems,
GEO issues, or on-site engagement problems -- or to explain why a brand is
"invisible", "stale", or "bouncing" in AI apps.

## Inputs

- A target URL or bare domain (required).
- Today's date, if known precisely by the calling agent/environment
  (recommended -- passed through to the freshness checks so staleness is
  judged against the real current date rather than a possibly-wrong system
  clock).

## Procedure

### 1. Normalize the target

Confirm you have a single, specific domain to audit (not a search query or
an ambiguous brand name). If given only a brand name, ask for or infer the
canonical domain before proceeding.

### 2. Run the scripted checks

From this skill's `scripts/` directory:

```
python3 run_checks.py <url> --out raw_findings.json --today <YYYY-MM-DD>
```

This subprocess-invokes each sub-skill's own check script
(`crawl-render-audit/scripts/check_crawl_render.py`,
`structured-data-entity-audit/scripts/check_structured_data.py`,
`freshness-corroboration-audit/scripts/check_freshness.py`,
`engagement-audit/scripts/check_engagement.py`), tags each finding with
`source_skill`, and writes the merged (not yet finalized) list to
`raw_findings.json`. If any sub-check fails to run (network issue, timeout),
`run_checks.py` records that as a low-severity `"meta"` finding instead of
silently dropping that section of the audit -- read the output for any of
these before treating a "clean" area as actually verified.

Total runtime is normally well under the 5-minute budget: each sub-skill
fetches a handful of pages (homepage + a small same-domain sample, typically
5-10 requests total per skill) at a throttled rate. See each sub-skill's
`references/checklist.md` for its exact request budget.

### 3. Add the two judgment-based checks the scripts can't do

Two of the four sub-skills each have one step that requires reasoning a
static script can't do on its own -- read their SKILL.md for the exact
procedure, then append the resulting finding(s) to `raw_findings.json`'s
`"findings"` array, in the same shape the scripts use (see
[references/report_schema.md](references/report_schema.md) for the exact
raw-finding shape):

- **`freshness-corroboration-audit`, Part B**: a small number (2-4) of live
  web searches to check whether independent sources corroborate the brand's
  core facts and identity (off-site agreement / mistaken-identity risk --
  something no single-domain fetch can check).
- **`engagement-audit`, step 2**: a reading-comprehension judgment of
  whether the homepage orients a first-time visitor (what is this, who's it
  for, what do I do next), using the rubric in that skill's
  `references/orientation_rubric.md`.

Do not skip these two steps -- they cover real, distinct failure modes (off-
site trust/disambiguation, and on-site orientation) that the mechanical
checks structurally cannot catch.

If no live web-search tool is available in the current environment, do not
fabricate search results or skip the step silently: append a single
low-severity `"meta"`-category finding stating that off-site corroboration
could not be checked (no search tool available), so the final report is
honest about what it did and didn't verify, exactly like `run_checks.py`
already does for a sub-check that fails to run. The orientation-clarity
judgment never needs this fallback -- it only reads text the scripts already
fetched, so it can always run.

### 4. Finalize the report

```
python3 finalize_report.py raw_findings.json --site <url> --out audit_report.json --md audit_report.md
```

This assigns `F-001`, `F-002`, ... IDs in severity order, de-duplicates
exact repeats, computes the summary counts, and writes both the JSON report
(the required deliverable) and a human-readable Markdown version. See
[references/report_schema.md](references/report_schema.md) for the exact
final schema and severity definitions.

### 5. Present the result

Return the JSON report (it already satisfies the required minimum schema:
`site`, `audited_at`, `summary.total_findings/critical/high/medium`, and
per-finding `id/title/severity/evidence/suggested_action`). Lead with the
critical/high findings and their suggested actions; a non-expert reading
the report should immediately understand what's broken, why it matters, and
what to do about it, without needing to understand crawler internals
first -- that's what each finding's `mechanism` field is for.

If nothing scripted or judged rose to a genuine defect in some area, don't
manufacture a finding to fill space -- a short area is a legitimate result,
not a failure of the audit.

## Composition summary

| Sub-skill | Category | Covers |
|---|---|---|
| `crawl-render-audit` | discoverability | Can a crawler get in and read the page (robots.txt, indexing directives, JS-render gaps, login walls) |
| `structured-data-entity-audit` | discoverability | Are facts stated explicitly/unambiguously (schema.org, Open Graph, entity disambiguation, llms.txt) |
| `freshness-corroboration-audit` | discoverability | Is content current and internally consistent; do independent sources corroborate it |
| `engagement-audit` | engagement | Does a visitor who arrives understand the site, trust it, and know what to do next |

## Output

A single JSON object matching [references/report_schema.md](references/report_schema.md).
