---
name: crawl-render-audit
description: Check whether AI and search crawlers can actually reach a website and read what is on it - robots.txt rules interpreted by crawler purpose, CDN and WAF blocking that silently overrides robots.txt, noindex directives, JavaScript render gaps that leave pages blank to non-rendering bots, and facts locked inside images, PDFs, canvas or client-side templates. Also collects the shared evidence bundle every other skill in this marketplace reads. Use when a brand is missing from AI answers entirely, when a site looks fine to humans but empty to bots, or as the first stage of a broader AI-readiness audit.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read
metadata:
  marketplace: brand-ai-readiness-audit
  stage: "1"
---

# Crawl & Render Audit

Precondition 1. If a crawler cannot fetch the page, or fetches it and finds
nothing readable, no other improvement matters.

This skill also owns `scripts/evidence_collector.py`, the single bounded crawl
that produces the `evidence.json` every other analyzer in this marketplace
consumes.

## When to use

As stage 1 of the `audit-orchestrator` flow, or standalone when a site is
absent from AI answers and you need to know whether it is even reachable.

## Inputs

A URL or bare domain.

## Procedure

1. Collect the evidence bundle (skip if the orchestrator already did):
   ```
   python3 scripts/evidence_collector.py <url> --out evidence.json --max-pages 15
   ```
   Crawls the homepage plus a prioritized same-domain sample, honouring
   robots.txt for every URL beyond the entry page, throttled, and hard-bounded
   by page count, depth and wall-clock budget.

2. Analyze it:
   ```
   python3 scripts/analyze_crawl_render.py --evidence evidence.json
   ```
   Emits findings JSON on stdout.

3. If the render-gap finding is ambiguous and you have a rendering-capable
   fetch tool, fetch the page rendered and compare its visible text to
   `text_sample` in the bundle. A large gap confirms it; a small gap means the
   heuristic misfired and the finding should be dropped.

## What it checks

Access — sitewide `Disallow`, per-agent rules resolved **by crawler purpose**,
Cloudflare Content Signals directives, network-layer bot blocking, `noindex`
via meta tag or `X-Robots-Tag`, sitemap availability, broken internal links.

Readability — JavaScript render gap (little extractable text alongside a
client-render root or heavy scripting, with the `<noscript>` fallback measured),
and facts locked in non-text elements (fact-bearing images without alt text,
PDF-only documents, canvas, third-party embeds, unrendered template bindings,
values living only in `data-` attributes).

## Gotchas

- **Blocking a training crawler is not a defect.** GPTBot, ClaudeBot,
  Google-Extended, Applebot-Extended and CCBot are training or opt-out tokens.
  Google states plainly that blocking Google-Extended does not affect inclusion
  in Google Search. Blocking these costs no citation visibility, and reporting
  it as a problem is the single most common false positive in this domain. The
  analyzer records it as informational only — keep it that way.
- **Only these blocks actually cost visibility**: OAI-SearchBot,
  Claude-SearchBot, PerplexityBot, Googlebot, Bingbot, Applebot,
  DuckAssistBot, plus the live user-fetch agents.
- **robots.txt is not the whole story.** CDN and WAF bot management blocks
  before robots.txt is consulted and overrides it, so a permissive robots.txt
  can coexist with total invisibility. That is what the user-agent differential
  probe in the collector exists to catch; treat a positive there as serious.
- **The render-gap test is a heuristic.** A deliberately minimal page can trip
  it. Confirm with `curl -A GPTBot <url>` before reporting with confidence.

## Output

Findings JSON in the shape defined by
`../audit-orchestrator/references/report_schema.md`, all with
`category: discoverability`. Details of every check, its threshold and the
evidence behind it are in [references/checklist.md](references/checklist.md).
