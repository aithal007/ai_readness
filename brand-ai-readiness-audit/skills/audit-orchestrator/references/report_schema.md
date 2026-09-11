# Report schema

One contract, targeted by every skill in the marketplace.

## Raw finding — what each analyzer emits

```json
{
  "title": "Commercial pages state no explicit price in extractable text",
  "severity": "critical | high | medium | low",
  "category": "discoverability | engagement | meta",
  "evidence": "3/4 pricing pages contain no currency figure. Examples: ...",
  "mechanism": "Why this actually costs citations or visitors, grounded in how the systems behave.",
  "signal_tier": 1,
  "evidence_tier": "measured | correlational | speculative",
  "suggested_action": {
    "summary": "What to change.",
    "priority": "critical | high | medium | low",
    "how": "(optional) concrete implementation note"
  },
  "source_skill": "ai-citability-audit",
  "page": "(optional) the specific URL this concerns"
}
```

`category: meta` is reserved for findings about the audit itself — a check that
could not run. It is not a defect in the site, and it sorts last.

**Evidence must be falsifiable.** Every `evidence` string has to contain
something a human can go and verify: a count, a measurement, a URL, or a named
token. `evidence-critic` drops findings that fail this test, because an
unfalsifiable claim is not a finding.

## Final report — what the orchestrator emits

```json
{
  "site": "example.com",
  "audited_at": "2026-09-07T14:32:00Z",
  "summary": {
    "site": "example.com",
    "audited_at": "2026-09-07T14:32:00Z",
    "total_findings": 10,
    "critical": 1,
    "high": 2,
    "medium": 5,
    "low": 2
  },
  "readiness": {
    "overall": 78,
    "pillars": {
      "crawl_access":     { "label": "Reachable", "score": 88 },
      "machine_readable": { "label": "Readable", "score": 76 },
      "citability":       { "label": "Quotable", "score": 63 },
      "answerability":    { "label": "Answerable", "score": 75 },
      "trust_freshness":  { "label": "Current & corroborated", "score": 90 },
      "engagement":       { "label": "Engaging", "score": 82 }
    },
    "scale_note": "This audit's own 0-100 framework, not a validated metric."
  },
  "audit_scope": { "pages_sampled": 12, "crawl_seconds": 31 },
  "findings": [ { "id": "F-001", "...": "raw finding fields" } ],
  "critic_summary": {
    "findings_considered": 14,
    "findings_reported": 10,
    "suppressed": [ { "title": "...", "reason": "..." } ],
    "severity_adjustments": [ "..." ]
  }
}
```

This is a strict superset of the required minimum (`site`, `audited_at`,
`summary` counts, and per-finding `id`, `title`, `severity`, `evidence`,
`suggested_action`). Everything else is additive.

`critic_summary` is published deliberately. Showing what was considered and
rejected, and why, is what makes the audit auditable rather than merely
assertive.

## Severity

| Severity | Meaning |
|---|---|
| critical | Blocks discoverability or access outright — blocked search crawlers, noindexed homepage, no HTTPS, site unreachable |
| high | A major active cause of lost citations or visitors — a real render gap, missing prices on commercial pages, most core questions unanswerable |
| medium | A real gap that weakens performance without blocking it |
| low | Polish, or a proactive improvement where no defect was found |

## Ordering

Sort by severity, then category (`discoverability` → `engagement` → `meta`),
then by suggested-action priority. IDs `F-001`, `F-002`, ... are assigned after
sorting, so the lowest number is always the thing to fix first.
