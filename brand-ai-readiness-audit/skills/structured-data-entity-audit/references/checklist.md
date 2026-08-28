# Structured Data & Entity Audit -- check reference

## Checks performed by `scripts/check_structured_data.py`

| Check | Severity | Why |
|---|---|---|
| Invalid/unparseable JSON-LD | high | A malformed block is typically ignored wholesale by consumers even though it looks present in the source. |
| No JSON-LD at all on homepage | high | Structured data is the least-ambiguous way to state entity facts; its absence forces noisy text inference. |
| JSON-LD present but no Organization/WebSite type | medium | Without an explicit entity type, there's less structured basis for identity. |
| Organization present but no `sameAs` | medium (raise if name is generic/shared) | `sameAs` is the standard mechanism for disambiguating this entity from unrelated ones with a similar name. |
| Missing Open Graph title/description | medium | Widely-parsed, explicit "what is this page" signal used by previews and many ingestion pipelines. |
| Missing Twitter/X card tags | low | Redundant, low-cost signal. |
| Empty/missing `<title>` | high | One of the highest-weight explicit signals of page topic. |
| Generic placeholder `<title>` (e.g. "Home", "Untitled Document") | medium | Carries no identifying information. |
| Missing meta description | medium | A commonly-ingested, explicit one-line summary. |
| No `<html lang>` | low | Minor locale/entity-matching and accessibility signal. |
| No favicon | low | Minor brand-identity polish signal. |
| Product-page pattern (price + purchase wording) without Product/Offer schema | medium, heuristic | See hedging note in SKILL.md -- confirm before treating as a hard defect. |
| Article-page pattern (`<article>` tag or `/blog/`,`/news/` URL) without Article/BlogPosting schema | medium | Article schema carries headline/author/date explicitly, used for both extraction and freshness. |
| No `/llms.txt` | low, proactive | Emerging, cheap, low-risk convention some AI tools check first; not a substitute for real crawlability/schema. |

## `@type` extraction logic

The script walks every parsed JSON-LD object recursively (including
`@graph` arrays and arrays used for multiple `@type` values) and collects
every `@type` string it finds anywhere in the document, not just at the top
level. This means a `WebPage` wrapping an `@graph` of `[Organization,
WebSite, BreadcrumbList]` is correctly seen as containing `Organization`.

## `llms.txt` format, if you recommend adding one

Per the community `llms.txt` convention: a plain markdown file at
`/llms.txt`, starting with a required `# <Project or Site Name>` H1 (the
only mandatory element), optionally followed by a one-line blockquote
summary, free-form context paragraphs, and `##`-delimited markdown link
lists (e.g. `## Docs`, `## Key Pages`) pointing to the most important pages.
Treat this as a cheap, low-risk addition, not a replacement for proper
crawlability, valid JSON-LD, or a real sitemap -- its actual effect on any
given AI system's behavior is unconfirmed and debated; recommend it as a
minor proactive improvement, not as fixing a confirmed defect.

## Known limitations / false-positive risks

- The product/article heuristics are text-pattern matches, not a real
  understanding of page intent -- always sanity-check before reporting them
  as confirmed defects (see SKILL.md step 2).
- `sameAs` absence is flagged at a flat `medium` regardless of how common
  the brand name is; a human/agent judgment call is needed to know whether
  name-collision risk is actually high for this specific brand (see SKILL.md
  step 3).
- The script samples at most 3 internal pages beyond the homepage, chosen
  by URL/link-text heuristics (about/product/pricing/contact/blog) -- it
  will not catch a structured-data gap on a page type it didn't happen to
  sample.
