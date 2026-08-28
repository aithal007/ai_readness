# brand-ai-readiness-audit

An Agent Skill Marketplace that audits a website for two things at once:

- **AI discoverability** -- why an AI assistant might miss, misrepresent, or
  refuse to cite this brand.
- **On-site engagement** -- why a visitor who does arrive doesn't stay.

Point it at a domain and it returns one structured report: findings with
evidence and severity, plus prioritized, mechanism-sound suggested actions.
It never modifies the target site -- every check is a read-only `GET`
request, `robots.txt` is honored, and the whole marketplace runs on a bare
`python3` install with zero pip installs (every script is Python
standard-library only, so it's portable across agent hosts).

## Why it's split this way

Discoverability breaks down into three sequential preconditions that fail
independently: a crawler has to (1) be let in, (2) be able to read the
page, (3) be able to extract the specific fact being asked about -- and
even once all three hold, a machine trusts a fact more when independent
sources agree on it. On-site engagement is a separate concern entirely (it
matters only *after* discovery succeeds). Each skill below owns one of
these failure modes, so it can be tested, reasoned about, and improved
independently instead of living inside one large, tangled checklist.

## Skills

| Skill | Owns | Kind of check |
|---|---|---|
| **`audit-orchestrator`** (entrypoint) | Composes the other four into one report | Runs their scripts, adds two judgment-based findings, merges/dedupes/IDs everything, emits the final schema-compliant report |
| `crawl-render-audit` | Can a crawler get in and read the page | Scripted: `robots.txt` (incl. named AI-crawler rules), noindex directives, HTTP errors, sitemap, login walls, JS-render-gap heuristic |
| `structured-data-entity-audit` | Are facts stated unambiguously; is the entity disambiguated | Scripted: JSON-LD validity/coverage, `sameAs`, Open Graph, title/description, `llms.txt` |
| `freshness-corroboration-audit` | Is content current, internally consistent, and corroborated | Scripted: stale dates, cross-page fact consistency, broken links, on-site corroboration signals -- **plus** a bounded, agent-performed live web-search step for off-site agreement/mistaken-identity, which no single-domain script can check |
| `engagement-audit` | Does a visitor who arrives understand and stay | Scripted: HTTPS, mobile viewport, heading structure, alt text, nav/search affordances, CTA presence, render-blocking scripts -- **plus** an agent-performed reading-comprehension judgment of homepage orientation clarity |

## How the entrypoint composes them

`audit-orchestrator` doesn't re-implement any check. Its procedure
(`skills/audit-orchestrator/SKILL.md`) is:

1. `scripts/run_checks.py <url>` subprocess-runs each sub-skill's own check
   script and merges their JSON output into `raw_findings.json`, tagging
   every finding with which skill produced it. A sub-check that fails to
   run becomes a visible low-severity `"meta"` finding, not a silent gap.
2. The agent appends two findings the scripts structurally can't produce --
   a bounded off-site web-search corroboration check
   (`freshness-corroboration-audit`'s Part B) and a homepage
   orientation-clarity judgment (`engagement-audit`'s step 2) -- to the same
   findings list, in the same shape.
3. `scripts/finalize_report.py` de-duplicates, sorts by severity, assigns
   `F-001`, `F-002`, ... IDs, computes the summary counts, and emits the
   final report (both JSON and a human-readable Markdown rendering).

The exact raw-finding and final-report shapes are defined once, in
`skills/audit-orchestrator/references/report_schema.md`, and every skill
targets that same contract.

## Running it directly (without an agent)

Every check script is independently runnable and prints JSON to stdout:

```
python3 skills/audit-orchestrator/scripts/run_checks.py https://example.com --out raw.json --today 2026-08-27
python3 skills/audit-orchestrator/scripts/finalize_report.py raw.json --site example.com --out audit_report.json --md audit_report.md
```

This produces the scripted two-thirds of the report; the two
agent-performed judgment steps (web-search corroboration, orientation
clarity) are only available when an agent follows the skills' SKILL.md
procedures, since they aren't expressible as a deterministic script.

## Project layout

```
brand-ai-readiness-audit/
├── marketplace.json                  # registers all 5 skills; audit-orchestrator is the entrypoint
├── README.md                         # this file
├── ARCHITECTURE.md                   # detailed file-by-file design doc
└── skills/
    ├── audit-orchestrator/           # entrypoint: composes the other four
    │   ├── SKILL.md
    │   ├── references/report_schema.md
    │   └── scripts/{run_checks.py, finalize_report.py}
    ├── crawl-render-audit/
    ├── structured-data-entity-audit/
    ├── freshness-corroboration-audit/
    └── engagement-audit/
        └── (each: SKILL.md, references/checklist.md, scripts/{check_*.py, page_parser.py})
```

## Example output

`finalize_report.py` renders each finding like this in the Markdown report:

```markdown
## F-001 - Sitewide robots.txt block for AI crawlers (CRITICAL)

- **Category:** discoverability
- **Evidence:** robots.txt disallows User-agent: * for /
- **Why it matters:** Every AI crawler, including ones that would otherwise
  cite this brand, is blocked before it can read a single page.
- **Suggested action:** Remove or scope the sitewide Disallow rule.
  - **How:** Edit /robots.txt to allow at least the homepage and key
    content paths for GPTBot, ClaudeBot, PerplexityBot, and Google-Extended.
```

The accompanying JSON carries the same fields (`id`, `title`, `severity`,
`category`, `evidence`, `mechanism`, `suggested_action`, `source_skill`) plus
a `summary` block with per-severity counts -- see
[`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full schema and how every
script and skill fits together.

## Guardrails

- Read-only `GET` requests only; `robots.txt` is checked before crawling
  any page beyond the homepage.
- A custom, self-identifying `User-Agent` and a ~0.5s per-host delay
  between requests keep every run well short of rate-abusive.
- Each sub-skill samples at most homepage + ~4 same-domain pages; the
  off-site corroboration step is capped at 2-4 web searches. A typical
  audit finishes in well under 5 minutes (observed: under a minute against
  a large, real site during testing).
- Internal-page sampling skips login/signup/cart/checkout/account/admin
  paths and non-HTML assets (images, PDFs, stylesheets, fonts) -- it never
  wanders into an authenticated-area-adjacent page or wastes a request on
  something that was never going to be a content page.
- No authentication, no form submission, no state-changing request of any
  kind, ever.
- Each skill declares its `allowed-tools` in frontmatter (`Bash` for the
  three purely-scripted skills; `Bash WebSearch` for the two whose SKILL.md
  includes an agent-performed live-search step). If a host environment has
  no search tool bound, those two skills degrade gracefully: they emit an
  explicit low-severity `meta` finding saying the check couldn't run,
  rather than fabricating a result or silently skipping it.
