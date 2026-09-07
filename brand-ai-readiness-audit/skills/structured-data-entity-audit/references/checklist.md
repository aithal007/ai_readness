# Structured data & entity — checks and thresholds

## The verdict ladder

Resolved in order. The point is to never report "no structured data" on the
strength of missing JSON-LD alone.

| Verdict | Trigger |
|---|---|
| `INVALID_STRUCTURED_DATA` | a JSON-LD block exists but fails to parse |
| `STRUCTURED_DATA_PRESENT` | JSON-LD, microdata (`itemscope`/`itemtype`/`itemprop`), RDFa (`typeof`/`vocab`), or microformats2 (`h-*`) |
| `LEGACY_MICROFORMATS_ONLY` | classic microformats — `vcard`, `hentry`, `hreview`, `adr` |
| `SOCIAL_META_ONLY` | Open Graph, Twitter cards or Dublin Core only |
| `MACHINE_HINTS_ONLY` | `rel=me`, feed autodiscovery, or an embedded state blob |
| `NO_STRUCTURED_DATA` | none of the above |

Invalid markup is reported as **worse than absent**, because it looks finished
and so never gets revisited.

## Checks

| Check | Severity |
|---|---|
| JSON-LD present but unparseable | high |
| Nothing on the whole ladder | medium |
| Only legacy or social-meta markup | low |
| Organization node missing `@id`, `sameAs`, or with social-only `sameAs` | medium |
| Non-URL values inside `sameAs` | medium (part of the identity finding) |
| Conflicting Organization `@id`s across pages | medium |
| Markup name absent from visible page text | low |
| No Organization node despite other markup | medium |
| Missing or empty `<title>` | high |
| Placeholder `<title>` ("Home", "Untitled") | medium |
| Meta description missing on ≥half the pages | low |
| No `html lang` | low |
| No `/llms.txt` | low, **speculative** |

## Entity identity — what good looks like

A stable `@id` (`https://example.com/#org`), one canonical Organization per
site, and `sameAs` pointing at authoritative references rather than only social
profiles. Priority order: Wikidata and the official URL first; then Wikipedia
and the LinkedIn company page; then Crunchbase; then ROR for research
organisations and ISNI for publishers and cultural bodies.

Bare identifier codes — LEI, DUNS, VAT, ISNI numbers, tax IDs — are **not URLs**
and belong in `identifier` as a `PropertyValue`, never in `sameAs`.

The identity spine that actually resolves "which entity is this page about" is
`WebPage → isPartOf → WebSite → publisher → Organization`, plus
`WebPage.about → Organization`. `sameAs` alone does not do it.

## Honest scope

Recommend schema for **entity disambiguation** and **search rich results**.
Do not present it as a route to AI citations. Controlled evidence points to
null or slightly negative effects there: 1,885 pages adding JSON-LD saw
AI-Overview citations fall 4.6% against controls; visibility distributions were
near-identical across schema-coverage buckets; facts planted in FAQ schema went
unused by every platform tested; and a corrected re-analysis collapsed the
association to null once ranking position was controlled for.

Also: do not recommend FAQPage or HowTo as visibility wins — FAQ rich results
have been heavily restricted since 2023 and HowTo was effectively deprecated.

## Known limits

- The `@type` walk collects types from anywhere in the document including
  `@graph` and multi-value arrays, so a `WebPage` wrapping a graph is read
  correctly — but the analyzer does not validate property-level completeness
  against schema.org.
- Name-collision risk cannot be judged from the site alone. Where a brand name
  is generic, raise the `sameAs` finding's severity using a web search.
