---
name: crawl-render-audit
description: Checks whether AI crawlers and search bots can actually reach and read a website -- robots.txt access for named AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, etc.), noindex directives, HTTP/redirect errors, sitemap presence, login/paywall gates, and whether page content only appears after client-side JavaScript runs (a render gap most AI crawlers can't see past). Use when auditing why a brand is invisible to AI assistants or search, or as the first stage of a larger AI-discoverability/engagement audit.
license: MIT
allowed-tools: Bash
---

# Crawl & Render Audit

This is the "can a machine get in, and can it read what's there" check --
the first of the three sequential preconditions for AI discoverability
(access, then legibility, then extractability). If this fails, nothing
downstream matters: a page a crawler can't fetch or can't read is invisible
regardless of how good its content or structured data is.

## When to use

As part of a brand AI-discoverability/engagement audit (normally invoked by
the `audit-orchestrator` skill in this marketplace), or standalone whenever
someone asks why a site isn't showing up in AI assistant answers or search.

## Inputs

A single URL or bare domain (e.g. `example.com` or `https://example.com`).

## Procedure

1. Run the check script, which handles fetching, robots.txt parsing, and
   the render-gap heuristic deterministically:
   ```
   python3 scripts/check_crawl_render.py <url>
   ```
   It prints a JSON object `{"skill": "crawl-render-audit", "site": ..., "findings": [...]}`.
   Each finding already has `title`, `severity`, `category`, `evidence`,
   `mechanism`, and `suggested_action` -- see
   [references/checklist.md](references/checklist.md) for exactly what each
   check does and why, and for a manual fallback procedure if the script
   can't run in the current environment (e.g. no outbound network access).

2. The script fetches the homepage, `robots.txt`, and `sitemap.xml`, then
   samples up to 4 same-domain internal links (favoring about/product/
   pricing/contact/blog pages), skipping any URL `robots.txt` disallows for
   `*`. Total requests per run: roughly 5-9, each throttled ~0.5s apart --
   deliberately small and polite, well under a rate-abuse threshold.

3. If asked to judge JS-render gaps more precisely than the static-HTML
   heuristic allows (e.g. the heuristic is ambiguous, or you have a
   rendering-capable fetch tool available), fetch the page with that tool
   and compare the rendered visible text to the script's raw-HTML text
   extraction. A large gap confirms the finding; a small gap means the
   heuristic's flag was a false positive -- downgrade or drop it.

4. Pass the script's raw findings through unchanged to whatever is composing
   the final report (the `audit-orchestrator` skill, if running inside this
   marketplace). Do not re-invent severities or evidence text -- the script
   already grounds both in what it observed.

## Output

A JSON array of findings in the shape documented in
[../audit-orchestrator/references/report_schema.md](../audit-orchestrator/references/report_schema.md).
Each finding's `category` is `"discoverability"`.
