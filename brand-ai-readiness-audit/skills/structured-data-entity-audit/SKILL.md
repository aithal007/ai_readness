---
name: structured-data-entity-audit
description: Check whether a website states unambiguously which organisation it belongs to and whether its machine-readable claims match its visible page - JSON-LD validity, microdata, RDFa and microformats detection, Organization entity identity, stable @id, sameAs links to canonical references like Wikidata or LinkedIn, colliding entity declarations from multiple plugins, and title, description and language metadata. Use when an AI assistant confuses a brand with a similarly named organisation, attributes the wrong facts to it, or when auditing schema markup and entity clarity.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read WebSearch
metadata:
  marketplace: brand-ai-readiness-audit
  stage: "2"
---

# Structured Data & Entity Audit

Two questions: is it clear **who** this site belongs to, and do its machine
claims **agree with** what the page actually shows?

## When to use

Stage 2 of the `audit-orchestrator` flow, or standalone when assistants mix a
brand up with something else of the same name, or attribute the wrong facts.

## Inputs

An `evidence.json` bundle from `crawl-render-audit`.

## Procedure

```
python3 scripts/analyze_structured_entity.py --evidence evidence.json
```

Optionally, where the brand name is generic or shared, run one web search for
the name to judge collision risk, and raise the severity of a missing `sameAs`
finding accordingly. The script cannot know how common a name is; you can.

## What it checks

- **The structured-data ladder** — JSON-LD, microdata, RDFa, microformats2,
  legacy microformats, Open Graph, Dublin Core, then machine hints. It reports
  a verdict, not a binary.
- **Validity** — a JSON-LD block that fails to parse is reported as worse than
  absent markup, because it looks finished and so never gets revisited.
- **Entity identity** — a stable `@id`, `sameAs` links to canonical references,
  and whether those references are authoritative or only social profiles.
- **Collisions** — several plugins each declaring their own Organization with
  different `@id` values, which is worse than one sparse declaration.
- **Parity** — whether the name asserted in markup appears in the visible page.
- **Descriptive metadata** — title, meta description, `html lang`.

## Gotchas

- **Never report "no structured data" on the strength of missing JSON-LD.**
  Microdata, RDFa and microformats are structured data too, and because they
  annotate visible text their fact-parity is arguably better than JSON-LD's.
  Enormous numbers of themes emit classic microformats such as `vcard` and
  `hentry`. The analyzer resolves the full ladder first; do not second-guess it
  into a harsher verdict.
- **Do not sell schema as a route to AI citations.** This is the most common
  overclaim in the field. Controlled studies found null or slightly negative
  effects on AI citation — one test of 1,885 pages saw citations *fall* after
  JSON-LD was added, and a rigorous re-analysis collapsed the association to
  null once ranking position was controlled for. Any study that does not
  control for rank is mostly measuring rank. Recommend schema for entity
  disambiguation and search rich results, which are real. What gets a page
  quoted is concrete facts in visible body text.
- **Bare identifier codes do not belong in `sameAs`.** LEI, DUNS, VAT, ISNI and
  tax numbers are not URLs; they belong in `identifier` as a `PropertyValue`.
- **Markup must not assert what the page does not show.** A fact present only
  in JSON-LD is the same class of problem as a fact present only inside an
  image — unverifiable against the page, and discounted accordingly.
- **Do not recommend FAQPage or HowTo markup as a visibility win.** FAQ rich
  results have been heavily restricted since 2023 and HowTo was effectively
  deprecated.

## Output

Findings JSON per `../audit-orchestrator/references/report_schema.md`, with
`category: discoverability`. Full check table in
[references/checklist.md](references/checklist.md).
