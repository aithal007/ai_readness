# Crawl & Render Audit -- check reference

## Why these checks, specifically

Search engines and AI assistants find content the same basic way: a crawler
has to (1) be let in, (2) be able to read what's on the page, (3) be able to
pick out the specific fact being asked about. Fail step 1 or 2 and step 3
never gets a chance -- the page is invisible to that system even though a
human sees it fine. This skill only covers steps 1 and 2; structured-data
extractability (step 3) is `structured-data-entity-audit`'s job.

## Checks performed by `scripts/check_crawl_render.py`

| Check | Severity if failed | Why |
|---|---|---|
| `robots.txt` disallows `*` sitewide | critical | Blocks every well-behaved crawler, AI or otherwise. |
| `robots.txt` disallows named AI crawlers | critical/high | Named rules override `*`; that specific assistant will never fetch the site. |
| No `/sitemap.xml` | medium | Sitemaps are the most reliable discovery path for pages with few inbound internal links. |
| `X-Robots-Tag: noindex` header | critical | Explicit, machine-authoritative exclusion from indexing. |
| `<meta name="robots" content="noindex">` | critical | Same effect via HTML instead of headers. |
| Homepage returns 4xx/5xx | critical | An error on the homepage blocks the whole domain by definition. |
| No `<link rel="canonical">` | low | Ambiguity about which URL variant is authoritative can split signal across duplicates. |
| JS-render gap (see below) | high | Most AI crawlers do not execute JavaScript; client-only content is invisible to them. |
| No `<noscript>` fallback on a JS-heavy page | medium | Compounds the render-gap issue; there's no plain-text fallback either. |
| Login/paywall wording with thin visible text | high | Gated content is invisible to anonymous crawlers. |
| Broken links in the sampled internal pages | medium/high | Wastes crawl budget and is a quality/freshness signal. |

## The render-gap heuristic, precisely

The script never executes JavaScript (it's stdlib-only Python, by design,
for portability -- see the marketplace README). It approximates "does this
page need JS to show its real content" with two static signals combined:

- **Visible text extracted from raw HTML is very short** (under ~250
  characters after stripping `<script>`/`<style>`/`<noscript>`), **and**
- Either a **known SPA root element** is present (`id="root"`, `id="app"`,
  `id="__next"`, `id="__nuxt"`, etc.) **or** there are **6+ `<script>` tags**.

This is a heuristic, not proof. False positives happen (a genuinely
minimal, mostly-image landing page). False negatives happen too (a
framework that does partial SSR for the hero section but loads the rest of
the content via client-side fetch after mount -- the raw HTML will look
"non-empty" even though most of the substance is still missing). When the
result is ambiguous or high-stakes, verify manually:

```
curl -A GPTBot <url> | less     # what a non-rendering crawler actually sees
```

or, if a rendering-capable fetch tool is available in the current
environment, fetch the rendered DOM and diff its visible text against the
script's raw-HTML extraction.

## AI crawler user-agent tokens checked against robots.txt

`GPTBot`, `ChatGPT-User`, `OAI-SearchBot`, `ClaudeBot`, `Claude-User`,
`Claude-SearchBot`, `anthropic-ai`, `PerplexityBot`, `Perplexity-User`,
`Google-Extended`, `Applebot-Extended`, `CCBot`, `Amazonbot`,
`Meta-ExternalAgent`, `Bytespider`, `Diffbot`. This list changes over time
as new assistants ship their own fetchers -- treat it as illustrative, not
exhaustive, and don't hesitate to check for a newer bot name by hand if the
target's `robots.txt` mentions one not in this list.

## Politeness / guardrails

- Custom, self-identifying `User-Agent` on every request.
- ~0.5s delay between requests to the same host.
- At most homepage + `robots.txt` + `sitemap.xml` + 4 sampled internal pages
  per run.
- Every sampled URL beyond the homepage is checked against `robots.txt`
  `Disallow` rules for `*` before fetching; disallowed URLs are skipped, not
  fetched.
- No authentication attempted, no forms submitted, no state-changing
  requests (GET only).
