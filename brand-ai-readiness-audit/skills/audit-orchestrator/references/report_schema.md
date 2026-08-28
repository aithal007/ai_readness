# Audit report schema

This is the shape every skill in this marketplace targets. Sub-skills
(`crawl-render-audit`, `structured-data-entity-audit`,
`freshness-corroboration-audit`, `engagement-audit`) each produce a list of
**raw findings** in a slightly looser shape (no `id` yet, since IDs are
assigned once across the merged set); `audit-orchestrator` turns that into
the **final report**.

## Raw finding shape (what each sub-skill's script/procedure emits)

```json
{
  "title": "No JSON-LD structured data on product pages",
  "severity": "critical | high | medium | low",
  "category": "discoverability | engagement | meta",
  "evidence": "Crawled 12 product pages; 0/12 contain schema.org markup.",
  "mechanism": "One sentence on *why* this hurts discoverability/engagement -- ties the finding back to how crawlers/assistants actually behave, not just 'this is best practice.'",
  "suggested_action": {
    "summary": "Add Product/Offer JSON-LD to every product page.",
    "priority": "critical | high | medium | low",
    "how": "(optional) a concrete, mechanism-sound implementation note."
  }
}
```

`category: "meta"` is reserved for findings about the audit process itself
(e.g. a sub-check that failed to run) -- it is not a discoverability or
engagement defect on the site, and `finalize_report.py` sorts it last.

## Final report shape (what `audit-orchestrator` emits)

```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": {
    "total_findings": 6,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 0
  },
  "findings": [
    {
      "id": "F-001",
      "title": "No JSON-LD structured data on product pages",
      "severity": "high",
      "category": "discoverability",
      "evidence": "Crawled 12 product pages; 0/12 contain schema.org markup.",
      "mechanism": "...",
      "suggested_action": {
        "summary": "Add Product/Offer JSON-LD to every product page.",
        "priority": "high"
      },
      "source_skill": "structured-data-entity-audit"
    }
  ]
}
```

This is a strict superset of the contest's minimum required shape (`site`,
`audited_at`, `summary.total_findings/critical/high/medium`, and per-finding
`id/title/severity/evidence/suggested_action`). The additional fields
(`category`, `mechanism`, `source_skill`, `summary.low`) are additive and
should never be relied on by anything that only expects the minimum shape.

## Severity definitions

- **critical** -- actively blocks discoverability or access outright (e.g.
  robots.txt blocking all crawlers, `noindex` on the homepage, no HTTPS).
  Fix immediately; nothing else matters until this is resolved.
- **high** -- a major, likely-active cause of poor citation/engagement (e.g.
  a real JS-render gap, missing homepage structured data, no mobile
  viewport). Fix soon.
- **medium** -- a real gap that measurably weakens discoverability or
  engagement but isn't actively blocking anything (e.g. missing sitemap,
  inconsistent facts across pages, no on-site search on a large site).
- **low** -- polish-level or proactive/beyond-defect suggestions (e.g. no
  favicon, no llms.txt, no blog section). Worth doing, not urgent.

## Ordering

`finalize_report.py` sorts findings by severity (critical -> high -> medium
-> low), then by category (`discoverability` -> `engagement` -> `meta`)
within a severity tier, then assigns `F-001`, `F-002`, ... in that order.
Exact-duplicate `(title, category)` pairs across sub-skills (e.g. the same
issue independently found on two sampled pages) are de-duplicated, keeping
whichever instance has the richer evidence text.
