---
name: structured-data-entity-audit
description: Checks whether a site states its facts in a form a machine can parse unambiguously -- schema.org JSON-LD validity and coverage (Organization, Product/Offer, Article), sameAs entity-disambiguation links, Open Graph/Twitter meta tags, title/meta-description quality, language declaration, and llms.txt presence. Use when auditing why an AI assistant misrepresents, confuses, or can't extract clean facts about a brand, or as part of a larger AI-discoverability/engagement audit.
license: MIT
allowed-tools: Bash WebSearch
---

# Structured Data & Entity Audit

Once a crawler can reach and read a page (see `crawl-render-audit`), the
next question is whether the facts on it are stated *explicitly* enough to
extract correctly, and whether the entity itself is disambiguated from
anything else that might share its name. Machines extract explicit,
structured facts far more reliably than facts implied only in prose --
and they trust an entity more when it's clearly linked to canonical
external profiles (Wikipedia, Wikidata, LinkedIn, Crunchbase) that rule out
mistaken identity.

## When to use

As part of a brand AI-discoverability/engagement audit (normally invoked by
`audit-orchestrator`), or standalone when an AI assistant is citing wrong
facts, confusing the brand with something else of the same name, or simply
never mentioning it despite good content.

## Inputs

A single URL or bare domain.

## Procedure

1. Run the check script:
   ```
   python3 scripts/check_structured_data.py <url>
   ```
   It fetches the homepage plus a small sample of internal pages, parses
   every `<script type="application/ld+json">` block, and checks Open
   Graph/Twitter meta, title/description quality, `<html lang>`, favicon,
   and `/llms.txt`. See [references/checklist.md](references/checklist.md)
   for the full check list, the `@type` coverage logic, and known heuristic
   limitations.

2. Product/Article structured-data findings are **heuristic** (they infer
   "this looks like a product/article page" from price patterns, purchase
   wording, or an `<article>` tag). Before treating one as a confirmed
   defect, sanity-check the page: a SaaS pricing page that mentions a price
   is not necessarily missing anything by lacking `Product` schema -- it may
   correctly need `Service`/`Offer` under an `Organization` instead. The
   script's evidence text already flags this ambiguity; preserve that
   hedging in the final report rather than overstating confidence.

3. For the entity-disambiguation check (`sameAs` on the Organization
   entity): if the brand name is generic or shared with other entities (a
   common word, a name reused across industries), treat a missing `sameAs`
   as more urgent than the script's default `medium` severity -- this is a
   judgment call the script can't make on its own since it doesn't know how
   common the name is. Use a web search of the brand name if you want to
   confirm name collisions before upgrading severity.

## Output

A JSON array of findings in the shape documented in
[../audit-orchestrator/references/report_schema.md](../audit-orchestrator/references/report_schema.md).
Each finding's `category` is `"discoverability"`.
