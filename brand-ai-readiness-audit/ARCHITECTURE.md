# Architecture

The complete design reference for `brand-ai-readiness-audit`. Where
[`README.md`](./README.md) explains *what* the marketplace does and *why* it is
split the way it is, this document explains *how* every part works — every
file, every check, every threshold, the data that flows between skills, and the
reasoning (and live test failures) behind each decision.

## Contents

1. [Design philosophy](#1-design-philosophy)
2. [The causal model](#2-the-causal-model)
3. [Repository layout](#3-repository-layout)
4. [The marketplace manifest](#4-the-marketplace-manifest)
5. [The evidence collector](#5-the-evidence-collector)
6. [The evidence bundle schema](#6-the-evidence-bundle-schema)
7. [Skill: crawl-render-audit](#7-skill-crawl-render-audit)
8. [Skill: structured-data-entity-audit](#8-skill-structured-data-entity-audit)
9. [Skill: ai-citability-audit](#9-skill-ai-citability-audit)
10. [Skill: answerability-probe](#10-skill-answerability-probe)
11. [Skill: freshness-corroboration-audit](#11-skill-freshness-corroboration-audit)
12. [Skill: engagement-audit](#12-skill-engagement-audit)
13. [Skill: evidence-critic](#13-skill-evidence-critic)
14. [Skill: audit-orchestrator](#14-skill-audit-orchestrator)
15. [End-to-end data flow](#15-end-to-end-data-flow)
16. [The report schema](#16-the-report-schema)
17. [Architectural patterns](#17-architectural-patterns)
18. [The evidence base](#18-the-evidence-base)
19. [False-positive guards](#19-false-positive-guards)
20. [Performance](#20-performance)
21. [Spec compliance](#21-spec-compliance)
22. [Known limitations](#22-known-limitations)
23. [Finding states, scoring and the roadmap](#22b-finding-states-scoring-and-the-roadmap)
24. [Testing record](#23-testing-record)
24. [Extending the marketplace](#24-extending-the-marketplace)

---

## 1. Design philosophy

Five commitments shape every file in this repository.

### 1.1 Model the mechanism, not a checklist

Most site audits are a list of best practices with severities attached. That
approach fits the examples its author saw and generalises badly. This
marketplace instead models the **causal chain by which a brand becomes citable**
(§2), and each skill owns one link in that chain. A check exists only because a
specific link can break in a specific way.

The practical consequence is ordering. A page that a crawler cannot fetch does
not benefit from better headings. So findings about later stages are
deliberately suppressed or downgraded while an earlier stage is failing, rather
than being reported as a flat list of equally-weighted problems.

### 1.2 Calibrate against evidence, including inconvenient evidence

Every threshold traces to a measured result, recorded in
[`skills/audit-orchestrator/references/evidence-base.md`](./skills/audit-orchestrator/references/evidence-base.md).
Each finding carries an `evidence_tier`:

| Tier | Meaning |
|---|---|
| `measured` | Controlled study with a reported effect size or odds ratio |
| `correlational` | Observed association, plausible mechanism, confounders not excluded |
| `speculative` | Reasonable mechanism, no measured citation benefit |

This forces honesty in both directions. It is why schema markup is **not**
presented as an AI-citation lever, why a missing `llms.txt` is `speculative` and
never a defect, and why blocking `GPTBot` is recorded as informational rather
than a problem. Each of those is contrary to widespread advice, and each is
what the controlled evidence supports.

### 1.3 A false positive costs more than a miss

An audit's only asset is the reader's trust. One confidently-wrong finding
makes a reader discount the true ones. So:

- Evidence must be **falsifiable** — every `evidence` string must contain
  something checkable (a count, a URL, a named token). `evidence-critic` drops
  findings that fail this.
- Heuristics are labelled as heuristics, in the finding text itself, and each
  skill's SKILL.md carries a Gotchas section naming its own failure modes.
- A dedicated skill exists purely to argue findings down (§13).

### 1.4 Script the deterministic, delegate the judgemental — and never fake the gap

Work that can be deterministic is a bundled script. Work that genuinely cannot
be (reading comprehension; searching *other* domains) is an explicit
agent-performed step in a SKILL.md, with a stated fallback when the tool is
unavailable. What never happens is a script pretending to do the judgemental
part, or an audit silently skipping it.

### 1.5 Degrade loudly

A degraded run that looks identical to a clean run is the worst possible
outcome in a multi-step audit. Every failure surface converts into a visible
`meta` finding: `fetch()` never raises, a crashed analyzer becomes a finding, an
unavailable search tool becomes a finding.

---

## 2. The causal model

A brand gets found, trusted and cited only if six conditions hold, in order.

```
1. REACH       Can a crawler fetch the page at all?
      │        robots.txt · CDN/WAF bot blocking · noindex · HTTP status
      ▼
2. READ        Is the content present as text in the response?
      │        JS render gap · facts locked in images, PDFs, canvas, embeds
      ▼
3. IDENTIFY    Is it clear which organisation this is about?
      │        structured data ladder · @id · sameAs · markup/page parity
      ▼
4. QUOTE       Is this the kind of passage an answer engine lifts?
      │        price · recency · specs · statistics · attribution · hedging
      ▼
5. TRUST       Is it current, self-consistent, and independently corroborated?
      │        stale dates · internal contradictions · source independence
      ▼
6. CONVERT     Does the human who arrives orient and act?
               goal reachability · value proposition · CTAs · dead ends
```

Stages 1–2 are owned by `crawl-render-audit`, 3 by
`structured-data-entity-audit`, 4 by `ai-citability-audit`, 5 by
`freshness-corroboration-audit`, 6 by `engagement-audit`.

`answerability-probe` sits across 2–4 as an **outcome test**: rather than
checking inputs, it asks whether the questions people actually ask about this
kind of organisation can be answered from the site at all.

`evidence-critic` sits after everything, adjudicating.

### Why decompose this way

The rubric distinguishes genuine separation of concerns from padding. The test
applied here: each skill owns a **distinct failure mode** with a **different
fix owner**, and is **independently runnable and independently useful**.

| Skill | Failure mode | Fix owner |
|---|---|---|
| `crawl-render-audit` | Bot cannot reach or read | Infra / platform engineering |
| `structured-data-entity-audit` | Wrong entity, or markup disagrees with page | SEO / web dev |
| `ai-citability-audit` | Readable but not quotable | Content team |
| `answerability-probe` | The answer does not exist anywhere | Content / product marketing |
| `freshness-corroboration-audit` | Stale, contradictory, or uncorroborated | Content / PR / comms |
| `engagement-audit` | Visitor arrives and leaves | UX / design |
| `evidence-critic` | The audit itself is wrong | — (quality control) |

Splitting *reach* from *read* was considered and rejected: both are fixed by
the same team looking at the same response, so they stay in one skill.

---

## 3. Repository layout

```
brand-ai-readiness-audit/            <- marketplace root (this is what gets zipped)
├── marketplace.json                 <- manifest; exactly one entrypoint
├── README.md                        <- what and why
├── ARCHITECTURE.md                  <- this file: how
└── skills/
    ├── audit-orchestrator/          <- ENTRYPOINT
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── report_schema.md     <- the shared finding/report contract
    │   │   └── evidence-base.md     <- effect sizes, sources, do-not-recommend list
    │   └── scripts/
    │       ├── run_audit.py         <- stage 1: collect once, fan out to analyzers
    │       └── finalize_report.py   <- stage 3: IDs, scores, JSON + Markdown
    │
    ├── crawl-render-audit/          <- owns the shared collector
    │   ├── SKILL.md
    │   ├── references/checklist.md
    │   └── scripts/
    │       ├── evidence_collector.py    <- 1,175 lines: the crawl + parse engine
    │       └── analyze_crawl_render.py
    │
    ├── structured-data-entity-audit/
    │   ├── SKILL.md
    │   ├── references/checklist.md
    │   └── scripts/analyze_structured_entity.py
    │
    ├── ai-citability-audit/
    │   ├── SKILL.md
    │   ├── references/checklist.md
    │   └── scripts/analyze_citability.py
    │
    ├── answerability-probe/
    │   ├── SKILL.md
    │   ├── references/question-sets.md
    │   └── scripts/analyze_answerability.py
    │
    ├── freshness-corroboration-audit/
    │   ├── SKILL.md
    │   ├── references/checklist.md
    │   └── scripts/analyze_freshness.py
    │
    ├── engagement-audit/
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── checklist.md
    │   │   └── orientation_rubric.md
    │   └── scripts/analyze_engagement.py
    │
    └── evidence-critic/
        ├── SKILL.md
        └── scripts/critique_findings.py

tests/
└── run_tests.py                      <- 85 zero-dependency regression tests
```

**Code volume:** ~4,400 lines of Python across 10 scripts plus an 85-test suite. The collector is a
third of it because parsing arbitrary real-world HTML with nothing but the
standard library is the hard part.

**Dependencies:** none. Standard library only — `urllib`, `html.parser`, `re`,
`json`, `argparse`, `subprocess`, `datetime`, `collections`. No pip install, no
browser binary, no model weights. This is a deliberate constraint (§17.1).

---

## 4. The marketplace manifest

`marketplace.json` lists all eight skills and marks exactly one entrypoint:

```json
{
  "name": "brand-ai-readiness-audit",
  "version": "2.0.0",
  "description": "...",
  "entrypoint": "audit-orchestrator",
  "skills": [
    { "id": "audit-orchestrator", "path": "skills/audit-orchestrator",
      "entrypoint": true, "owns": "Composes every other skill and emits the final report" },
    { "id": "crawl-render-audit", "path": "skills/crawl-render-audit",
      "owns": "Can a crawler reach the page and read it (also owns the shared evidence collector)" },
    ...
  ]
}
```

The `owns` field is a contest-local extension carrying the one-line statement
of each skill's concern. `entrypoint` appears both as a top-level convenience
key and as a boolean on the entrypoint skill.

Every `id` matches its directory name, every `path` resolves, and exactly one
skill carries `entrypoint: true`. All three are asserted by the validation
script described in §21.

---

## 5. The evidence collector

`skills/crawl-render-audit/scripts/evidence_collector.py` — the engine
underneath everything. It performs **one** bounded crawl and writes a single
JSON bundle that every analyzer then reads.

### 5.1 Why one collector

In the previous version of this marketplace each of four skills fetched the
site independently. That was wrong in three ways: it multiplied network cost by
four, it meant each skill saw a slightly *different* snapshot (so two skills
could legitimately disagree about the same page), and it capped each skill at a
small page sample. Collecting once fixes all three and buys enough headroom to
crawl ~15 pages instead of ~4.

### 5.2 Networking

```python
USER_AGENT    = "BrandAIReadinessAuditBot/2.0 (+read-only audit; ...)"
TIMEOUT       = 10          # seconds per request
MAX_BYTES     = 3_000_000   # response read cap
REQUEST_DELAY = 0.4         # seconds between requests to the same host
```

- **`_throttle(host)`** — module-level `_last_request` dict; sleeps just enough
  to keep ≥0.4s between requests to a given host.
- **`fetch(url, timeout)`** — **never raises**. Returns
  `{url, final_url, status, headers, text, bytes, elapsed_ms, error}`. Handles
  gzip manually, decodes using the declared charset with a UTF-8-replace
  fallback, and catches `HTTPError` (preserving status and body on 4xx/5xx)
  separately from transport failures (`status: None`).
- **`site_root(url)`** — returns `scheme://netloc` with no path. Used for
  well-known files so that auditing `https://example.com/products/widget` still
  resolves `robots.txt`, `sitemap.xml` and `llms.txt` at the domain root.
- **`resolve_entry(raw)`** — accepts `example.com` or a full URL; tries HTTPS
  then HTTP, returning the first response under status 400.

### 5.3 The AI crawler taxonomy

The single most important false-positive guard in the marketplace. Each known
agent carries an operator, a category, and a `citation_impact`:

| `citation_impact` | Meaning | Examples |
|---|---|---|
| `removes` | Blocking genuinely costs citation visibility | `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Googlebot`, `Bingbot`, `Applebot`, `DuckAssistBot` |
| `none` | Training or opt-out token; blocking costs nothing | `GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `CCBot`, `Amazonbot`, `meta-externalagent`, `Bytespider` |
| `intent` | User-triggered fetch; robots.txt is advisory | `ChatGPT-User`, `Claude-User`, `Perplexity-User`, `MistralAI-User`, `meta-externalfetcher` |

Google documents that blocking `Google-Extended` "does not impact a site's
inclusion in Google Search". OpenAI documents that disallowing `GPTBot` opts out
of training only. Refusing training while permitting search is therefore a
legitimate, documented licensing decision — and reporting it as a defect is the
most common error in this problem space.

### 5.4 `analyze_robots(entry_url)`

Fetches `/robots.txt` once and returns a parser plus a structured summary:

- Per-agent `allowed_root` computed with `urllib.robotparser`, joined to the
  taxonomy above.
- `star_allowed_root` for the `*` group.
- **Cloudflare Content Signals** — parses `Content-Signal:` lines into
  `{search|ai-input|ai-train: yes|no}`. These are now injected by the CDN on
  millions of domains; a parser that ignores them misreads modern files.
- Declared `Sitemap:` lines.
- `agents_explicitly_named` — which AI agents appear as literal `User-agent:`
  groups, which distinguishes a deliberate policy from an inherited default.

### 5.5 `probe_user_agents(url)` — network-layer block detection

**robots.txt is only an advisory layer.** CDN and WAF bot management
(Cloudflare's AI-bot blocking, AWS WAF, Akamai) filters on user-agent and IP
*before* robots.txt is ever consulted, and overrides it. A site can publish a
perfectly permissive robots.txt and still be completely invisible to
assistants — a failure undetectable from robots.txt analysis alone.

The probe fetches the same public homepage four times, as a browser and as three
declared AI crawlers, and compares. A block is inferred when the browser
succeeds and an AI user-agent gets 401/403/429/503, a transport failure, or a
body under 35% of the browser's size (the signature of a challenge
interstitial). This is the only place the collector sends a non-default
user-agent, it fetches nothing but the homepage, and its sole purpose is
detection.

### 5.6 `DocParser` — the HTML engine

A single-pass `html.parser.HTMLParser` subclass, ~320 lines, that extracts
everything downstream skills need in one traversal. It is explicitly *not* a
full HTML5 parser; it is a best-effort structural extractor tuned for
real-world markup, wrapped so malformed input never crashes a run.

**Metadata captured:** title, `html lang`, `base href`, all meta tags split into
`meta`/`og`/`twitter`, robots meta, canonical, hreflangs, favicon presence,
feed autodiscovery.

**Structured data captured:** raw JSON-LD script bodies, microdata `itemtype`
values, RDFa `typeof` values, microformats class tokens.

**Structure captured:** headings with levels and text, images with `src`/`alt`,
links with href/text/aria, iframes, script inventory (total, external,
head-blocking, inline bytes), media element counts, form inventory (count,
search affordance, inputs, labelled inputs, off-site action), viewport,
`<noscript>` length, aria-label count.

**Block segmentation — the part that matters most.** The parser maintains a
stack of open block-level elements and, for every text node, attributes its
character count to the enclosing block, tracking separately how much of that
text sits inside an `<a>`. It also tracks whether the block is inside
`nav`/`header`/`footer`/`aside`.

That yields, per block, a **link density** — the standard signal
content-extraction algorithms use to separate article text from navigation
without CSS or a DOM library:

```python
def main_text(self):
    parts = []
    for b in self.blocks:
        if b["boilerplate"] or b["text_len"] < 25:
            continue
        density = b["link_text_len"] / b["text_len"] if b["text_len"] else 1.0
        if density <= 0.45:
            parts.append(b)
    return sum(b["text_len"] - b["link_text_len"] for b in parts)
```

Text inside `script`, `style`, `noscript`, `template` and `svg` is excluded from
body text — but `<noscript>` length is tallied separately, because a populated
noscript block is exactly what distinguishes a considered fallback from an empty
SPA shell.

**Citability instrumentation** is collected in the same pass: emphasis
characters (inside `b`/`strong`/`em`/`i`/`mark`/`u`), unit counts (`p`, `li`,
`tr`, `pre`, `dt`), quote tags (`blockquote`, `q`, `cite`), per-paragraph word
counts, per-section word counts delimited by headings, and intro-summary length
(words between the H1 and the first subheading).

### 5.7 `compute_citability(parser, text, page_url)`

Turns the parsed page into the tier-1 and tier-2 signals consumed by
`ai-citability-audit`. Notable computations:

- **Statistics density** — three regex families (percentages; multipliers and
  magnitudes; unit-suffixed quantities), reported raw and per 100 words.
- **Attributed quotes** — a quoted span of 20–400 characters counts only if an
  attribution verb (`said`, `according to`, `reported by`, …) appears within
  ±120 characters. Quote marks alone are not evidence of attribution.
- **Outbound authority** — distinct external domains, and which of them sit on
  `.gov`, `.edu`, `.ac.uk`, `.org`, `.int`, `.mil`.
- **Hedging** — hedge terms per 100 words, plus hedged numerics
  (`approximately 40%`) counted separately, since a hedged number is a
  specifically weak form of a specifically strong signal.
- **Query-term coverage** — the terms the page claims to be about (title + H1,
  minus stopwords, length > 3) intersected with the first 200 words of body
  text. Reports the fraction covered *and* names the uncovered terms.
- **Fact position** — the fractional offset of the first price match within the
  document, used to detect load-bearing facts stranded mid-page.
- **Structural ratios** — structured-format ratio `F_d` = (li + tr + pre) /
  (li + tr + pre + p); emphasis density `E_d` = emphasised chars / total chars;
  heading depth and skipped levels; section word-count distribution against the
  150–300 band.

### 5.8 `structured_data_verdict(html, page, parser)` — the ladder

Never concludes "no structured data" from missing JSON-LD alone:

| Verdict | Trigger |
|---|---|
| `INVALID_STRUCTURED_DATA` | JSON-LD present but unparseable |
| `STRUCTURED_DATA_PRESENT` | JSON-LD, microdata, RDFa (`typeof`/`vocab`), or microformats2 (`h-*`) |
| `LEGACY_MICROFORMATS_ONLY` | classic `vcard`, `hentry`, `hreview`, `adr` |
| `SOCIAL_META_ONLY` | Open Graph, Twitter cards, or Dublin Core |
| `MACHINE_HINTS_ONLY` | `rel=me`, feed autodiscovery, embedded state blob |
| `NO_STRUCTURED_DATA` | none of the above |

Invalid markup ranks as **worse than absent** because it looks finished, so
nobody revisits it. Note that RDFa detection requires `typeof` or `vocab` —
matching on `rel` alone would fire on every `rel="stylesheet"` in existence.

### 5.9 `extractability_risks(html, text, parser, page)`

Detects facts that are visible to a human but invisible to text extraction.
Fourteen modes, each reported as a **signal, never a certainty**:

fact-bearing images without alt text · image-heavy pages with sparse text ·
text inside SVG · canvas-rendered content · CSS-generated text (`content:`
declarations carrying real words) · unrendered template bindings and surviving
mustaches · facts present only in `data-*` attributes and absent from text ·
PDF-only documents whose link text implies pricing or specs · third-party
embeds (Datawrapper, Flourish, Tableau, Google Docs, Airtable, Typeform) ·
custom elements suggesting shadow DOM · media without captions · obfuscated
contact details · content behind "load more" · prose referencing a table that
does not exist in markup.

### 5.10 The crawl

```
resolve entry → analyze_robots → analyze_sitemap → well-known files
              → probe_user_agents → build homepage record
              → priority-ordered BFS over same-domain links
```

Frontier ordering scores each candidate link against `PRIORITY_WORDS`
(`about`, `pricing`, `product`, `service`, `contact`, `docs`, `faq`, `blog`,
`news`, `team`, `admission`, `program`, `course`, `shop`), so a bounded crawl
spends its budget on pages that carry answers rather than on pagination.

Exclusions applied before fetching:

- `SKIP_PATH_WORDS` — `login`, `signin`, `signup`, `logout`, `cart`,
  `checkout`, `account`, `wp-admin`, `admin`, `basket`, `my-account`. This keeps
  the crawler well clear of anything authenticated-area-adjacent.
- `SKIP_EXTENSIONS` — images, PDFs, archives, CSS/JS, fonts, media, XML.
- `robots.txt` `can_fetch("*", url)` for every URL beyond the entry page.
- Non-HTML `Content-Type` responses are discarded after fetch.

Three hard bounds: `max_pages` (default 15), `max_depth` (default 2), and
`budget_seconds` (default 150) checked every iteration.

Finally the collector builds a `link_graph` of `url -> [outbound internal
urls]`, which is what makes goal-path reachability analysis possible in
`engagement-audit` (§12.2).

---

## 6. The evidence bundle schema

```jsonc
{
  "schema_version": "2.0.0",
  "site": "https://example.com",          // final resolved entry URL
  "domain": "example.com",
  "entry_reachable": true,
  "collected_at": "2026-09-08T12:00:00Z",
  "limits": { "max_pages": 15, "max_depth": 2, "budget_seconds": 150 },

  "robots": {
    "status": 200, "present": true, "bytes": 812,
    "star_allowed_root": true,
    "agents": {
      "GPTBot": { "operator": "OpenAI", "category": "training",
                  "citation_impact": "none", "allowed_root": false }
    },
    "agents_explicitly_named": ["GPTBot"],
    "content_signals": { "search": "yes", "ai-train": "no" },
    "declared_sitemaps": ["https://example.com/sitemap.xml"],
    "raw_excerpt": "..."
  },

  "ua_probe": {
    "probes": { "browser": {...}, "GPTBot": {...},
                "ClaudeBot": {...}, "PerplexityBot": {...} },
    "blocked_agents": [],
    "network_layer_block_suspected": false
  },

  "sitemap": { "checked": [...], "total_urls_found": 42, "sample_urls": [...] },
  "wellknown": { "llms_txt": { "status": 404, "present": false }, "security_txt": {...} },

  "pages": [ /* see below */ ],
  "link_graph": { "https://example.com": ["https://example.com/about", ...] },

  "stats": {
    "pages_fetched": 12, "pages_failed": 1,
    "failures": [{ "url": "...", "status": 404 }],
    "robots_skipped": [], "elapsed_seconds": 30.9, "budget_exhausted": false
  }
}
```

Each page record:

```jsonc
{
  "url": "...", "final_url": "...", "status": 200, "error": null,
  "depth": 1, "elapsed_ms": 210, "html_bytes": 84213, "https": true,
  "headers": { "content-type": "...", "x-robots-tag": "...", "last-modified": "..." },

  "title": "...", "lang": "en", "canonical": "...", "hreflangs": [],
  "robots_meta": "", "meta_description": "...",
  "og": {...}, "twitter": {...}, "has_favicon": true, "feeds": [],

  "jsonld": [...], "jsonld_types": ["Organization", "WebSite"],
  "jsonld_invalid": 0, "jsonld_dates": { "dateModified": "2026-05-01" },
  "microdata_types": [], "rdfa_types": [], "microformats": [],

  "headings": [[1, "..."], [2, "..."]],
  "text_len": 5120, "main_text_len": 3980, "boilerplate_text_len": 1140,
  "link_density": 0.223, "text_sample": "first 2500 chars", "word_count": 812,

  "links_internal": [["url", "anchor text"]], "links_external": [...],
  "images_total": 24, "images_missing_alt": 9,
  "iframes": [], "media_counts": {...}, "scripts": {...},
  "spa_root": false, "noscript_len": 0, "viewport": true,
  "forms": { "count": 1, "search": true, "inputs": 3, "labeled": 3 },
  "aria_labels": 12,

  "facts": {
    "emails": [], "tel_links": [], "phones": [], "prices": [],
    "postal_codes": [], "hours_mentions": 0, "founded_years": [],
    "copyright_years": ["2026"], "updated_years": [],
    "coming_soon": [], "cta_matches": ["get started"], "login_wall": false
  },

  "citability": { "word_count": 812, "tier1": {...}, "tier2": {...} },
  "structured_data": { "verdict": "STRUCTURED_DATA_PRESENT", ... },
  "extractability_risks": [ { "mode": "facts_locked_in_pdf", "examples": [...] } ]
}
```

The bundle is the **single integration contract** in the marketplace. Analyzers
never import each other's code and never re-fetch; they are pure functions over
this JSON. That makes each one independently testable against a saved bundle
with no network access at all.

---

## 7. Skill: crawl-render-audit

Owns stages 1–2 (REACH, READ) and the shared collector.
`allowed-tools: Bash(python3:*) Bash(python:*) Read`

`scripts/analyze_crawl_render.py` (265 lines) reads the bundle and emits
findings, all `category: discoverability`, all `signal_tier: 1`.

### Access checks

| Check | Severity | Condition |
|---|---|---|
| Sitewide `Disallow: /` for `*` | critical | `star_allowed_root` false |
| Search-index crawler blocked | critical | any agent with `citation_impact: removes` disallowed |
| Training crawler blocked | **low, informational** | agents with `citation_impact: none` — explicitly *not* a defect |
| Live-fetch agent blocked | low | `citation_impact: intent`; advisory only |
| Content Signals present | low, or medium if `search=no` | CDN-injected directives that may not reflect owner intent |
| Network-layer block | critical | `ua_probe.network_layer_block_suspected` |
| `noindex` | critical on homepage, else high | meta robots or `X-Robots-Tag` |
| No usable sitemap | medium | no `<loc>` entries found |
| Broken internal links | medium | any 4xx/5xx in the sample |

The training-crawler finding deserves note: it exists *to be reported as
correct configuration*. Its suggested action reads "No action needed unless
contributing to model training is desired. Verified as correctly configured:
search access is preserved." Recording the check ran and passed is more useful
than silence, and prevents a reviewer from re-flagging it later.

### Readability checks

| Check | Severity | Condition |
|---|---|---|
| JS render gap | critical if ≥ half the sample, else high | < 120 words extractable **and** (SPA root **or** ≥ 6 scripts) |
| Facts locked in non-text | high | any high-risk extractability mode present |
| Content only in a state blob | medium | render gap co-occurring with `__NEXT_DATA__`/`__NUXT__`/`__INITIAL_STATE__` |

The render-gap finding carries its own verification instruction in the `how`
field: `curl -A 'GPTBot' <url> | head -c 2000`. If the facts are not in that
output, no non-rendering crawler can see them.

---

## 8. Skill: structured-data-entity-audit

Owns stage 3 (IDENTIFY).
`allowed-tools: Bash(python3:*) Bash(python:*) Read WebSearch`

`scripts/analyze_structured_entity.py` (273 lines).

### Node traversal

`iter_nodes(doc)` walks JSON-LD iteratively, descending into `@graph` arrays and
nested values, so a `WebPage` wrapping `@graph: [Organization, WebSite,
BreadcrumbList]` correctly registers `Organization`. `org_nodes(page)` filters
for the Organization family: `Organization`, `LocalBusiness`, `Corporation`,
`NGO`, `GovernmentOrganization`, `CollegeOrUniversity`,
`EducationalOrganization`, `NewsMediaOrganization`.

### Checks

| Check | Severity |
|---|---|
| JSON-LD present but unparseable | high |
| Nothing on the entire ladder | medium |
| Only legacy microformats or social meta | low |
| Organization missing `@id` / `sameAs`, or social-only `sameAs`, or non-URL values in `sameAs` | medium |
| Conflicting Organization `@id`s across pages | medium |
| Markup name absent from visible page text | low |
| Structured data present but no Organization node | medium |
| Missing/empty `<title>` | high |
| Placeholder `<title>` | medium |
| Meta description missing on ≥ half the pages | low |
| No `html lang` | low |
| No `/llms.txt` | low, **speculative** |

`AUTHORITATIVE_SAMEAS` = wikidata.org, wikipedia.org, linkedin.com/company,
crunchbase.com, ror.org, isni.org. `SOCIAL_SAMEAS` = the usual profiles. The
distinction matters: social-only `sameAs` is flagged because social profiles
corroborate far less than a knowledge-base entry.

### Two deliberate restraints

**Severity is capped at medium for the whole skill.** Everything here is
`signal_tier: 2`. Entity clarity genuinely matters for disambiguation, but the
controlled evidence does not support treating markup gaps as citation-critical.

**The `llms.txt` finding is `speculative` and low.** Its mechanism text states
the counter-evidence directly — 97% of published files received zero requests
across a 137,000-domain study, no significant correlation with citations across
~300,000 domains, and Google has said it does not support it — and its action
tells the user to prioritise sitemaps, crawler access and on-page facts first.

---

## 9. Skill: ai-citability-audit

Owns stage 4 (QUOTE). The flagship analytical skill.
`allowed-tools: Bash(python3:*) Bash(python:*) Read`

`scripts/analyze_citability.py` (379 lines). Uniquely, it accepts `--url` as
well as `--evidence`, shelling out to the collector for standalone use.

### The two-tier model

**Tier 1 — gatekeepers.** Measured odds ratios above 100 in a 252,000-trial
controlled study across six current models. Failing one can eliminate citation
odds regardless of every other strength on the page.

| Check | Threshold | Severity |
|---|---|---|
| Topic-term coverage | < 50% of title/H1 terms in first 200 words | high if > half the pages, else medium |
| Explicit price | commercial page, no currency figure | high |
| Stale dates | most recent year ≥ 3 years old | high |
| Undated content | no date on ≥ half the pages | medium |
| No quotable evidence | > 250 words with zero statistics, zero attributed quotes, zero outbound links | high if widespread, else medium |
| Hedging | > 3 hedge terms per 100 words | medium |
| Missing specs | commercial page, < 3 spec pairs, no table | medium |
| No comparison content | zero comparison markers across ≥ 2 commercial pages | medium |
| Thin pages | < 150 words on ≥ half the sample | medium |

**Tier 2 — structure.** Long sections (≥ 2 over 300 words) → medium; shallow
heading depth on long pages → low; missing intro summary → low.

### Why the ordering is load-bearing

Two credible studies appear to contradict each other: a head-to-head design
found formatting "negligible", while a structural study measured +17.3%. Both
are true under different scopes — formatting cannot rescue a page that fails a
gatekeeper, but does help a page that already passes.

So the analyzer computes whether any tier-1 gatekeeper is failing, and if so
appends a gate sentence to every tier-2 finding's mechanism, telling the reader
to fix tier 1 first. `evidence-critic` independently enforces the same rule by
capping tier-2 severity (§13.4).

### Commercial-page detection

Deliberately strict, and rewritten twice after live false positives (§19.2):

```python
PURCHASE_CTAS = ("add to cart", "buy now", "add to bag",
                 "add to basket", "proceed to checkout")
PRICING_PATH  = ("/pricing", "/plans", "/price", "/product/",
                 "/products/", "/shop/", "/store/")
```

A page qualifies on an actual currency figure, a genuine cart CTA, or a
dedicated pricing path with > 80 words. The missing-price finding fires only on
positive transactional evidence, because otherwise "hiding the price" is
indistinguishable from "not selling anything here". Specs and comparison
findings additionally require ≥ 2 commercial pages before generalising.

### The date asymmetry

Handled explicitly because the naive fix is wrong. An *old* date measured worse
than **no** date; a *recent* date beat both. So the stale-date finding's `how`
field reads: "Do NOT strip dates to look evergreen — undated measured worse
than recently-dated."

---

## 10. Skill: answerability-probe

The outcome test. Spans stages 2–4.
`allowed-tools: Bash(python3:*) Bash(python:*) Read`

`scripts/analyze_answerability.py` (371 lines).

### Why it exists

Every other skill audits an **input**. This one audits the **outcome**: if a
person asked an assistant a normal question about this brand, is the answer
present anywhere in the site's machine-readable text at all? A missing answer
is not a missed best practice — it is the literal reason an assistant says "I
don't have information about that", or fills the gap from a third-party source
the brand does not control.

### Step 1 — entity-type inference

Inferred from evidence, never from a list of known sites, which is what lets it
generalise to unseen sites. Priority order matters:

| Type | Inferred from |
|---|---|
| `education` | education schema types, or `/admission`, `/academics`, `/courses` paths |
| `publisher` | news/blog schema types, or ≥ 3 article-shaped URLs |
| `saas` | `SoftwareApplication`/`WebApplication` schema, **or** pricing path + API/integration/docs vocabulary |
| `ecommerce` | genuine cart CTA, **or** Product/Offer schema **plus** shipping/availability vocabulary |
| `local_business` | local-business schema, **or** opening hours **together with** a postal address |
| `professional_services` | services vocabulary + credentials/accreditation vocabulary |
| `generic_org` | no strong signal |

SaaS is tested **before** ecommerce because software vendors commonly emit
Product schema, and reading one as a shop leads to asking it about shipping.
Local business requires a physical-presence signal, not merely hours-like text.
Both orderings are the direct result of live test failures (§19.3).

### Step 2 — canonical question sets

Universal slots: `identity`, `what_it_does`, `contact`, `location`. Then per
type:

| Type | Additional slots |
|---|---|
| `ecommerce` | price, product specs, shipping/returns, availability |
| `saas` | price, product specs, integrations or docs, trial or signup |
| `local_business` | hours, phone, services, booking |
| `education` | programs, admissions, fees, deadlines |
| `publisher` | authorship, publish dates, topics |
| `professional_services` | services, credentials, case evidence |
| `generic_org` | services, about depth |

### Step 3 — what counts as an answer

Only what a non-JavaScript crawler would see. Each slot has a bespoke resolver
returning `(answered, evidence_string)`:

- **contact** — a published email or `tel:` link. A contact form is explicitly
  *not* an answer; the evidence string says so when a form is the only thing
  present.
- **location** — a postal code in text, or a `PostalAddress` node.
- **price** — an actual currency figure. "Contact us for pricing" reads to an
  extractor as "no price exists".
- **hours** — a real day/time pattern or `OpeningHoursSpecification`.
- **product_specs** — ≥ 3 attribute:value pairs or a spec table.
- **identity** — a meta description, an H1, or Organization/WebSite schema.

### Step 4 — scoring

| Coverage | Severity |
|---|---|
| < 0.50 | critical |
| 0.50–0.74 | high |
| ≥ 0.75 | medium |

The finding names every unanswerable question in full sentence form ("How much
does {brand} cost?"), attaches an `answerability` object with the inferred type,
coverage, and answered/unanswered slot lists, and its suggested action lists the
specific questions to go and answer.

### The second finding

Where unanswerable questions co-occur with extractability risks, a separate
high-severity finding fires: *the answer may exist but in a non-extractable
form*. This is the cheapest class of gap to close, because the content is
already written — it just needs a text equivalent.

`brand_name(bundle)` resolves the brand for question phrasing from Organization
schema `name`, then `og:site_name`, then the title split on separators.

---

## 11. Skill: freshness-corroboration-audit

Owns stage 5 (TRUST).
`allowed-tools: Bash(python3:*) Bash(python:*) Read WebSearch`

Split into a scripted half and an agent half, because the second genuinely
cannot be scripted.

### Part A — scripted (`analyze_freshness.py`, 192 lines)

| Check | Threshold | Severity |
|---|---|---|
| Stale dates | most recent copyright/updated year ≥ 2 years old | medium; high at ≥ 3 |
| Placeholder content | "coming soon", "under construction", "lorem ipsum" | low; medium if the page also carries a year-old date |
| Multiple phone numbers | > 1 distinct value across sampled pages | medium |
| Multiple email addresses | > 1 distinct value across sampled pages | low |
| Many distinct prices | > 6 across the sample | low, **speculative** |
| No on-site corroboration | no outbound links to reference/review platforms and no press language | medium |

Phone numbers are normalised to their last 10 digits before comparison, so
formatting differences do not register as contradictions.

`--today` should always be passed with the agent's real current date, because
sandbox clocks are frequently wrong and every staleness judgement depends on it.

The contact-value checks are worded as **verification prompts**, not
accusations — see §19.4 for why.

### Part B — agent-performed off-site corroboration

A crawl of one domain structurally cannot see other domains. Bounded at 2–4
searches. Three assessments:

**Agreement** — do independent sources state the same core facts?

**Source independence** — the part most audits miss. Three sources repeating a
claim are not three confirmations if two are copies of the brand's own press
release. Each result is classified before counting:

| Class | Counts toward corroboration? |
|---|---|
| The brand's own properties | No |
| Press-release wires and syndication | No |
| Aggregators that copy | No |
| Independent editorial, reference, regulatory, academic | **Yes** |

Where many mentions trace to one origin, that pattern is reported explicitly —
it looks like strength and is not.

**Mistaken identity** — if results for the brand name are dominated by an
unrelated organisation, that is a more urgent version of the missing-`sameAs`
finding from `structured-data-entity-audit`, and the two are cross-referenced.

If no search tool is bound, the procedure requires appending one low-severity
`meta` finding saying the check could not run. Never inventing results is
stated explicitly in both the SKILL.md and the orchestrator's checklist.

### Why off-site is weighted heavily

Roughly three quarters of AI citations point at third-party pages rather than a
brand's own domain, and ranked comparison content is the single largest cited
content format. A site-only audit therefore addresses a minority of the
citation surface — which is why this is a first-class skill rather than a
footnote.

---

## 12. Skill: engagement-audit

Owns stage 6 (CONVERT).
`allowed-tools: Bash(python3:*) Bash(python:*) Read`

`scripts/analyze_engagement.py` (253 lines). All findings
`category: engagement`.

### 12.1 Structural checks

| Check | Threshold | Severity |
|---|---|---|
| Not HTTPS | final resolved URL is `http:` | critical |
| No viewport meta | any sampled page | high |
| No H1 on homepage | zero H1 elements | medium |
| No value proposition | no H1 **and** no meta description | high |
| No on-site search | > 40 internal links, no search input | medium |
| No call to action | ≥ half of pages > 150 words lack CTA phrasing | medium |
| Dead-end pages | substantive page with ≤ 1 internal link | low |
| Missing alt text | > 50% missing across ≥ 8 images | medium |
| Render-blocking scripts | > 4 sync external scripts in `<head>` | medium |
| Unlabelled form fields | ≥ 3 inputs with no label/aria-label/title/placeholder | low |

### 12.2 Goal-path reachability — the distinctive check

Rather than only scoring isolated page attributes, `click_depths(bundle)`
performs a breadth-first search over the collector's `link_graph` from the
homepage, producing `url -> click depth`. Four goals are then matched by URL
pattern:

| Goal | Matched by |
|---|---|
| `contact` | `/contact`, `/get-in-touch`, `/support`, `/help` |
| `pricing` | `/pricing`, `/plans`, `/rates`, `/fees`, `/tuition` |
| `about` | `/about`, `/who-we-are`, `/company`, `/team` |
| `offering` | `/product`, `/services`, `/solutions`, `/shop`, `/courses`, `/programs` |

A goal with no reachable page is high severity when it is `contact`, medium
otherwise. A goal reachable only at depth > 3 is medium. Crucially, a goal is
only reported missing if it appears **neither** in the crawled graph **nor** in
the homepage's links, which prevents penalising a site whose crawl was cut short
by the page budget.

The known failure mode is documented in the SKILL.md: a goal reported
unreachable may exist but be invisible because navigation is rendered
client-side. The instruction is to check the crawl-render findings before
telling a user a page is missing when it is really just unlinked in HTML.

### 12.3 The agent-performed orientation judgement

The script cannot read for comprehension. `references/orientation_rubric.md`
defines three questions answered from the homepage text sample — what is this,
who is it for, what do I do next — with severity guidance (all three fail →
high; one or two → medium; all clear → no finding, explicitly "don't
manufacture one to fill space") and a secondary context-retention note.

---

## 13. Skill: evidence-critic

Quality control. `allowed-tools: Bash(python3:*) Bash(python:*) Read`

`scripts/critique_findings.py` (223 lines). Runs between analysis and report.

### 13.1 Falsifiability

Drops findings with no title, no suggested action, or empty evidence. Then
requires a **concrete anchor** in the evidence:

```python
ANCHOR_RE = re.compile(r"\d"                              # a count or measurement
                       r"|https?://"                      # a URL
                       r"|/\w"                            # a path
                       r"|['\"][^'\"]{2,}['\"]"           # a quoted string
                       r"|[A-Za-z]+[A-Z][A-Za-z]*"        # CamelCase: GPTBot
                       r"|\b[A-Z][A-Za-z]*-[A-Z][A-Za-z]*\b")  # JSON-LD, X-Robots-Tag
```

An unfalsifiable finding is not a finding. This regex was widened after it
wrongly dropped valid findings whose evidence named crawler agents but contained
no digit (§19.5).

### 13.2 Counterproductive-recommendation stripping

Five regex/reason pairs. Any suggested action matching one is dropped with its
reason recorded:

| Pattern | Reason |
|---|---|
| keyword stuffing / keyword density | measured the worst tactic tested, −8.3% visibility |
| hidden text or hidden markup | ignored by every AI system tested, and reads as manipulation |
| model-directed instructions | a classed manipulation pattern |
| removing limitations or caveats | a classed manipulation pattern |
| "rewrite all/every/the entire" | blanket rewriting degraded retrieval up to 36% |

This is a mechanical safety net, not the primary defence — the analyzers are
written not to produce such advice in the first place.

### 13.3 Contradiction checks

Cross-checks specific claims against the bundle that produced them. A "no
structured data" finding is dropped if any sampled page has a non-null verdict
other than `NO_STRUCTURED_DATA`; a "not served over HTTPS" finding is dropped if
every sampled page resolved over HTTPS.

### 13.4 Merging and severity calibration

Near-duplicate detection uses Jaccard similarity over stopword-stripped title
tokens, at a **0.8 threshold**. Merging preserves the higher-severity instance,
adopts the richer evidence, and records both source skills.

Three calibration rules:

1. A tier-2 structural finding is downgraded from critical/high to medium while
   any tier-1 gatekeeper is failing.
2. A finding whose evidence begins `1/N` where N ≥ 3 is downgraded from
   critical/high to medium — one page is not a sitewide problem.
3. A `speculative` finding cannot hold critical or high severity; it is
   downgraded to low.

Every adjustment writes `severity_adjusted_from` onto the finding and appends a
human-readable note to `critic.severity_notes`.

### 13.5 Publishing the suppression list

The output carries a `critic` block with input count, kept count, every drop
with its reason, and every severity adjustment. `finalize_report.py` surfaces
this in both the JSON and the Markdown. Showing what was considered and
rejected is what makes the audit auditable rather than merely assertive.

### 13.6 The judgement half

The SKILL.md defines six questions the agent applies to survivors that the
script cannot: is the evidence sufficient *as worded*; is this a known heuristic
misfire; would the suggested action actually fix it; is severity proportionate
to real-world impact; is this the same issue as another finding; does it
contradict another finding.

---

## 14. Skill: audit-orchestrator

The entrypoint. `allowed-tools: Bash(python3:*) Bash(python:*) Read Write WebSearch`

### 14.1 `run_audit.py` (138 lines)

Stage 1. Resolves the marketplace root via
`pathlib.Path(__file__).resolve().parents[3]`, runs the collector once, then
runs each analyzer against the resulting bundle:

```python
ANALYZERS = [
    ("crawl-render-audit",           "analyze_crawl_render.py",     []),
    ("structured-data-entity-audit", "analyze_structured_entity.py",[]),
    ("ai-citability-audit",          "analyze_citability.py",       []),
    ("answerability-probe",          "analyze_answerability.py",    []),
    ("freshness-corroboration-audit","analyze_freshness.py",  ["--today"]),
    ("engagement-audit",             "analyze_engagement.py",       []),
]
```

**Failure policy is asymmetric and deliberate.** A collector failure is fatal —
nothing downstream can run without evidence, so it exits non-zero. An analyzer
failure is *recorded and survived*: `meta_finding()` produces a low-severity
`category: meta` finding whose mechanism reads "This check could not run, so its
area is UNVERIFIED rather than clean."

An unreachable site short-circuits to a single critical finding rather than
producing six analyzers' worth of noise about an empty bundle.

Progress goes to stderr, the output path to stdout — the standard separation
that keeps the script composable.

### 14.2 `finalize_report.py` (188 lines)

Stage 3. Filters findings missing any required field, sorts, assigns IDs,
computes counts and pillar scores, and writes JSON plus Markdown.

```python
SEV_RANK   = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CAT_RANK   = {"discoverability": 0, "engagement": 1, "meta": 2}
SEV_WEIGHT = {"critical": 25, "high": 12, "medium": 5, "low": 1}
```

Sort key is `(severity rank, category rank, -action priority weight)`, so
`F-001` is always the thing to fix first.

**Pillar scores** map skills to six readiness dimensions — Reachable, Readable,
Quotable, Answerable, Current & corroborated, Engaging — each starting at 100
and losing `SEV_WEIGHT` per finding attributed to it, floored at zero. Overall
is the mean.

These are honest about themselves. The report embeds a `scale_note` stating
they are "this audit's own 0-100 framework … not a validated or externally
comparable metric", and the Markdown prints that note directly under the score
table. The purpose is to make relative weakness legible at a glance, not to
imply measurement precision that does not exist.

**Output discipline:** the full report goes to `--out`; stdout gets only a
compact summary object, because agent harnesses truncate long stdout.

The Markdown renders a score table with bar glyphs, a "Fix these first" section
listing only critical and high findings with their actions, full detail per
finding (severity, category, evidence strength, what we found, why it matters,
what to do, optional how, and any critic adjustment), and finally the
struck-through suppression list.

### 14.3 The SKILL.md procedure

A five-step markdown checklist — collect, add the two judgement checks,
adjudicate, finalize, present — with explicit success conditions per step. Its
Gotchas section carries the six rules most likely to be got wrong: pass
`--today`; blocked training crawlers are not a defect; do not promise schema
causes citations; never recommend from the do-not-recommend list; do not
manufacture findings; and absence of evidence is not a clean bill of health.

---

## 15. End-to-end data flow

```
                                  <url>
                                    │
        ┌───────────────────────────▼───────────────────────────┐
        │  run_audit.py                                          │
        │                                                        │
        │  ┌──────────────────────────────────────────────────┐  │
        │  │ evidence_collector.py        (ONE bounded crawl)  │  │
        │  │  robots + content-signals · UA differential probe │  │
        │  │  sitemap · well-known · BFS ≤15 pages, depth ≤2   │  │
        │  │  DocParser → citability, SD verdict, risks, facts │  │
        │  └───────────────────────┬──────────────────────────┘  │
        │                          ▼                              │
        │                    evidence.json                        │
        │                          │                              │
        │     ┌──────────┬─────────┼─────────┬──────────┬──────┐ │
        │     ▼          ▼         ▼         ▼          ▼      ▼ │
        │  crawl_    structured  citability answer   freshness engage
        │  render     _entity                ability                │
        │     │          │         │         │          │      │  │
        │     └──────────┴─────────┴────┬────┴──────────┴──────┘  │
        │            each: JSON on stdout, tagged source_skill     │
        │            failure → visible "meta" finding              │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
                          raw_findings.json
                                   │
        ┌──────────────────────────▼───────────────────────────────┐
        │  AGENT adds the two judgement findings:                   │
        │   · off-site corroboration + source independence (search) │
        │   · homepage orientation clarity (reading comprehension)  │
        │  No tool available → explicit "meta" finding, never faked  │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
        ┌──────────────────────────▼───────────────────────────────┐
        │  critique_findings.py  +  agent judgement pass            │
        │  drop unfalsifiable · drop contradicted · strip harmful   │
        │  merge duplicates (0.8) · recalibrate severity            │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
                         adjudicated.json
                                   │
        ┌──────────────────────────▼───────────────────────────────┐
        │  finalize_report.py                                       │
        │  filter · sort · assign F-NNN · counts · pillar scores    │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
                audit_report.json   +   audit_report.md
```

**Key relational facts**

- The orchestrator never reimplements a check. It runs scripts and composes.
- Analyzers never import each other. The bundle JSON is the only contract.
- Cross-skill cooperation happens through shared vocabulary, not shared code:
  `answerability-probe` reads the same `extractability_risks` that
  `crawl-render-audit` reports on, and reaches a different conclusion from it.
- `--today` flows one hop, gated per-analyzer by the `wants_today` flag; only
  `analyze_freshness.py` accepts it.
- Category assignment is hardcoded per skill in each script's local `finding()`
  helper. `meta` is reserved exclusively for audit-process failures.

---

## 16. The report schema

Defined once in
[`skills/audit-orchestrator/references/report_schema.md`](./skills/audit-orchestrator/references/report_schema.md).

### Raw finding (analyzer output)

```json
{
  "title": "Commercial pages state no explicit price in extractable text",
  "severity": "critical | high | medium | low",
  "category": "discoverability | engagement | meta",
  "evidence": "3/4 pricing pages contain no currency figure. Examples: ...",
  "mechanism": "Why this actually costs citations or visitors.",
  "signal_tier": 1,
  "evidence_tier": "measured | correlational | speculative",
  "suggested_action": { "summary": "...", "priority": "high", "how": "optional" },
  "source_skill": "ai-citability-audit",
  "page": "optional specific URL"
}
```

### Final report

```json
{
  "site": "example.com",
  "audited_at": "2026-09-08T14:32:00Z",
  "summary": { "total_findings": 10, "critical": 1, "high": 2, "medium": 5, "low": 2 },
  "readiness": { "overall": 78, "pillars": {...}, "scale_note": "..." },
  "audit_scope": { "pages_sampled": 12, "crawl_seconds": 31 },
  "findings": [ { "id": "F-001", "...": "raw finding fields" } ],
  "critic_summary": {
    "findings_considered": 14, "findings_reported": 10,
    "suppressed": [...], "severity_adjustments": [...]
  }
}
```

This is a strict superset of the required minimum — `site`, `audited_at`,
`summary` counts, and per-finding `id`, `title`, `severity`, `evidence`,
`suggested_action`. Everything else (`category`, `mechanism`, `signal_tier`,
`evidence_tier`, `source_skill`, `page`, `readiness`, `audit_scope`,
`critic_summary`, `summary.low`) is additive and safe to ignore.

---

## 17. Architectural patterns

### 17.1 Standard library only

No pip install, no browser binary, no model weights. The marketplace runs on a
bare `python3` anywhere.

The cost is real and acknowledged: no JavaScript execution, so render gaps are
detected heuristically rather than by diffing a rendered DOM. The benefit is
that the marketplace actually runs in an arbitrary agent sandbox, stays far
under the 50 MB submission cap, and has no dependency that can break. For a
portable, provider-neutral skill format this is the correct trade — and the
SKILL.md tells the agent how to verify a render gap manually with `curl` or a
rendering-capable fetch tool when one is available.

### 17.2 Collect once, analyze many

The single most consequential structural decision. One crawl, one snapshot, six
analyzers as pure functions over it. Eliminates redundant network cost,
eliminates snapshot drift between skills, and makes every analyzer testable
offline against a saved bundle.

### 17.3 Fail soft into a finding

`fetch()` returns an error dict instead of raising. `run_audit.py` converts an
analyzer crash into a `meta` finding. SKILL.md procedures convert an
unavailable search tool into a `meta` finding. The architecture treats "this
could not be checked" as itself reportable.

### 17.4 Uniform `finding()` factory

Each analyzer defines a small local `finding()` helper hardcoding its category
and assembling the `suggested_action` sub-dict. Schema consistency by
convention, enforced at the end by `finalize_report.py`'s required-field filter
and `evidence-critic`'s validity pass.

### 17.5 IDs assigned last

Individual analyzers never assign IDs. They are assigned once, globally, after
merging, deduplication and sorting — which is what makes cross-skill merging
possible at all.

### 17.6 Heuristics that declare themselves

Every non-trivial inference is labelled a heuristic in the finding's own
evidence text, documented with named false-positive scenarios in the skill's
`references/checklist.md`, and paired with a Gotchas entry telling the agent how
to verify before reporting with confidence.

### 17.7 Flat progressive disclosure

`SKILL.md` files are flat: a short always-loaded description, a body under ~130
lines, and explicit pointers to `references/` files with a stated
*load-when* condition. No nested reference chains — controlled testing found
multi-level disclosure "never helps and sometimes breaks accuracy outright",
so depth is deliberately avoided.

### 17.8 Script hygiene

Non-interactive (no prompts, ever — a blocking script hangs an agent
indefinitely), `--help` via argparse as the documented interface, structured
JSON on stdout with diagnostics on stderr, meaningful exit codes (0 ok, 1
collector failure, 2 bad/missing input, 3 collector unavailable), idempotent
writes to deterministic paths, and bounded output size.

---

## 18. The evidence base

Full detail in
[`skills/audit-orchestrator/references/evidence-base.md`](./skills/audit-orchestrator/references/evidence-base.md).
Summary of what drives the thresholds:

### Tier-1 odds ratios (252k-trial controlled study, six models)

on-topic term coverage 221–>10k · explicit price 6.3–>10k · recency 14–>10k ·
specifications 8.6–243 · depth of coverage 4.0–>10k · evidence for claims
2.1–>10k · confident vs hedged 2.7–599 · comparison 1.6–7.5 · internal
consistency 1.7–4.1 · retrieval position 1 vs 2 1,795–>10k.

### Content lifts

statistics +30.6% · attributed quotations +41.0% (largest single lift) · citing
sources +27.5% · best pairing +35.8%.

### Position within the page

With 20 candidate documents: first position 75.8%, middle 53.8%, end 63.2%,
against a 56.1% closed-book baseline. **A fact buried mid-passage performed
worse than not supplying the page at all**, and the trough deepens with length.

### Structure

Structural fields measured ~+22% retrieval hit rate and +2.7 mean rank
positions — but the same work found the generator "primarily references body
text when forming responses". Hence: **structure gets you found; body text gets
you quoted.**

### Do not recommend

keyword stuffing (−8.3%) · blanket rewriting (−1% to −36%) · optimizing an
already-good page (all nine tactics reduced visibility) · "apply everything" ·
unique-word enrichment (negative) · persuasive tone (no significant effect) ·
optimizing a rank-1 page (can lose 20–30%) · burying facts mid-page · heavy
bulleting of the core claim · and seven manipulation primitives (unsupported
fit claims, caveat omission, relevance flooding, authority laundering, evidence
padding, salience manipulation, model-directed instructions).

### Where the field over-claims

**Schema** — controlled studies found null or slightly negative effects on AI
citation; 1,885 pages adding JSON-LD saw citations fall 4.6% against controls;
a corrected re-analysis collapsed the association to null once ranking was
controlled. Any schema study that does not control for rank is mostly measuring
rank.

**llms.txt** — 97% of published files received zero requests across 137,000
domains; no significant correlation with citations across ~300,000 domains;
Google has said it does not support it.

**Training-crawler blocks** — cost no citation visibility, per both Google's
and OpenAI's own documentation.

### Honest scope limits

Brand stature dominates on-page factors (~73% visibility for tier-1 global
brands vs ~11% for niche), roughly three quarters of citations point at
third-party pages, and engines differ substantially in how often they cite at
all — so a single blended visibility score would mislead.

---

## 19. False-positive guards

Each of these was found by running the marketplace against real sites and
watching it be wrong. They are documented here because the reasoning matters
more than the patch.

### 19.1 The crawler taxonomy

**Risk:** reporting a blocked `GPTBot` as a defect.
**Guard:** every agent carries `citation_impact`; only `removes` agents raise a
real finding. Training blocks are reported as verified-correct configuration.

### 19.2 Commercial-page detection

**Observed:** a government guidance page at `/buying-your-first-home` was
classified commercial because its URL contained "buy", then flagged for missing
price, missing specs and missing comparisons. Separately, a newsletter
"subscribe" link on a government department page marked it commercial.
**Guard:** URL keyword matching removed entirely. A page now qualifies only on
an actual currency figure, one of five unambiguous cart CTAs, or a dedicated
pricing path segment. "subscribe", "contact us", "get a quote" and "book now"
were removed from the purchase-CTA list as lead-gen rather than transactional.

### 19.3 Entity-type inference

**Observed:** gov.uk inferred as `local_business` — a bare "open" in the hours
regex matched "open government" and "open data" — and then asked about booking.
Postman inferred as `ecommerce` because it emits Product schema, and then asked
about shipping and returns.
**Guard:** the hours pattern now requires a real day/time or an explicit hours
phrase. SaaS is tested before ecommerce. Ecommerce requires a cart CTA or
Product schema *plus* shipping/availability vocabulary. Local business requires
opening hours *plus* a postal-address signal.

### 19.4 Contact-value conflicts

**Observed:** three departmental email addresses at a space agency
(`nasa-brand-partnerships@`, `hq-media@`, …) were reported as a high-severity
contradiction. A large organisation legitimately publishes several contacts.
**Guard:** severity reduced (phones medium, emails low), and the finding
reworded as a verification prompt — the evidence string now states outright
that this "may be legitimate (separate departments or locations) or may be
stale duplicates — the audit cannot tell which".

### 19.5 Critic anchor regex

**Observed:** the falsifiability check required a digit or URL, and so dropped
a valid finding whose evidence listed crawler agent names.
**Guard:** the anchor pattern now also accepts paths, quoted strings, CamelCase
tokens (`GPTBot`) and hyphenated technical tokens (`JSON-LD`).

### 19.6 Critic over-merging

**Observed:** "Conflicting phone numbers across the site's own pages" and
"Conflicting email addresses across the site's own pages" scored exactly 0.6
Jaccard similarity on shared boilerplate words and merged — producing one
finding whose title said phones and whose evidence described emails.
**Guard:** merge threshold raised from 0.6 to 0.8. Genuine cross-skill
duplicates have near-identical titles anyway.

### 19.7 Structured-data verdict ladder

**Risk:** reporting "no structured data" on a site using microdata, RDFa or
microformats. Enormous numbers of themes emit classic microformats.
**Guard:** the six-rung ladder, resolved before any verdict. RDFa detection
requires `typeof` or `vocab`, never bare `rel`.

### 19.8 Single-page generalisation

**Guard:** `evidence-critic` downgrades any critical/high finding whose evidence
begins `1/N` where N ≥ 3. Several analyzers additionally require ≥ 2 qualifying
pages before generalising.

### 19.9 A timeout is not a broken link

**Observed:** on a throttling origin, five perfectly healthy pages timed out and
were reported as `LINK_ROT_WIDESPREAD` — a *critical* finding asserting a broken
deploy that did not exist.
**Guard:** `analyze_crawl_render.py` splits failures by whether an HTTP status
came back. Only real 4xx/5xx count toward link rot. Transport failures become a
separate `not_observable` note saying the pages may be healthy but slow, and
that one attempt cannot tell the difference.

### 19.10 A self-inflicted rate limit is not a bot block

**Observed:** the user-agent differential probe fires four requests at one
origin in quick succession. A throttling host answered the GPTBot probe with
HTTP 429, and the analyzer reported "AI crawler user-agents are blocked at the
network layer" — critical. The audit had provoked the very signal it reported.
**Guard:** only 401/403 now counts as a confirmed block, because those are
policy decisions about the user-agent. 429 (throttle) and 503 (overload) and
transport failures drop to a hedged `medium` that says outright it could not be
confirmed and that a 429 may have been caused by the probe itself. The probe
also spaces its requests a second apart so it stops provoking the condition.

### 19.11 An unreachable site is not a healthy one

**Observed:** a site that could not be read at all produced zero findings, and
the pillar arithmetic — 100 minus nothing — handed back **100/100**. The most
misleading number the report could print.
**Guard:** `run_audit.py` marks short-circuited runs explicitly with
`short_circuited: true`; `critique_findings.py` carries that flag through; and
`finalize_report.py` emits `readiness.overall: null` with a note naming why it
was not scored. A contract test asserts the flag survives the critic, because
losing it silently restores the bug.

### 19.12 A tech aggregator is not an open-source project

**Observed:** adding an `open_source_project` entity type, the first
implementation inferred it from body-text vocabulary — licence words, GitHub
links, "pull request". Hacker News matched all of them, because that is what its
*content* is about, and was asked what licence it is released under.
**Guard:** identity is now inferred only from the site's **own path structure**
(two distinct kinds of `docs` / `learn` / `install` / `community` path, or one
plus explicit licence text). An aggregator publishes none of those. Verified:
rust-lang and fastapi classify correctly, Hacker News does not.

A latent bug surfaced while fixing this: the path regexes were anchored with
`(/|$)` but matched against a **space-joined** string of URLs, so `$` only ever
matched the final URL. Real sites were matching by luck of which path happened
to be last. The terminator is now `(?:/|\s|$)`, and a test with synthetic paths
covers it.

---

## 20. Performance

Measured on a standard consumer machine over residential broadband:

| Site | Pages | Collection | Full pipeline |
|---|---|---|---|
| example.com | 1 | 3.3s | ~4s |
| rust-lang.org | 8 | 8.0s | ~10s |
| gov.uk | 10 | 15.5s | ~18s |
| postman.com | 12 | 30.9s | ~33s |

Comfortably inside the 5-minute target. Defaults are 15 pages, depth 2, a
150-second crawl budget and ~0.4s between requests to a host; the wall-clock
budget is checked every frontier iteration, so a slow site degrades to fewer
pages rather than overrunning.

The dominant cost is network latency, not computation — parsing 12 pages takes
well under a second.

**Politeness:** self-identifying user-agent, per-host throttle, hard page cap,
robots-checked before every non-entry fetch, authenticated-area paths skipped,
non-HTML assets skipped, GET only, and the off-site search step bounded at 2–4
queries.

---

## 21. Spec compliance

Every skill folder independently satisfies the Agent Skills specification.

**Frontmatter uses only the six permitted fields** — `name`, `description`,
`license`, `allowed-tools`, `metadata`, `compatibility`. The allowed-field set
is closed; any extra top-level key is a hard validation failure. `version` and
similar live under `metadata` as string values.

**`allowed-tools` is a space-separated string**, e.g.
`Bash(python3:*) Bash(python:*) Read WebSearch` — never a YAML list, which the
reference parser (strictyaml) would reject outright.

**No BOM.** The reference parser tests `content.startswith("---")` literally, so
a UTF-8 BOM produces a misleading "must start with YAML frontmatter" error.
This is a live risk on Windows, where PowerShell writes BOMs by default; every
SKILL.md here is BOM-free and the validator asserts it.

**No `---` inside frontmatter values**, since parsing splits on it.

**Descriptions** are 476–639 characters (limit 1024), written in the
what-it-does-plus-when-to-use form, with no unquoted colons.

**Names** match their parent directory exactly, are lowercase alphanumeric with
single hyphens, and have no leading, trailing or consecutive hyphens.

**Bodies** are 61–122 lines, well inside the ~500-line recommendation, with
detail pushed to `references/` and every reference carrying a load-when
condition.

A validation script reimplementing all of the reference validator's rules —
including the closed field set, NFKC-normalised name/directory comparison,
length limits, BOM detection, `allowed-tools` format, manifest well-formedness,
single-entrypoint assertion, and existence of every referenced file — is used to
verify the marketplace. Current result: **all 8 skills pass, 1 entrypoint, no
errors.**

---

## 22. Known limitations

Stated plainly, because an audit tool that hides its own limits has no business
auditing anything.

1. **No JavaScript execution.** Render gaps are detected by heuristic (sparse
   text plus an SPA root or heavy scripting), not by diffing a rendered DOM.
   False positives on deliberately minimal pages; false negatives where a hero
   section renders server-side but the substance loads client-side afterwards.
   Mitigated by a documented manual verification step.

2. **Entity-type inference is imperfect.** rust-lang.org infers
   `professional_services` and is asked "what results has it achieved for
   clients?", which is a slightly odd question for a programming language. The
   finding is hedged, and the SKILL.md instructs the agent to verify the
   inferred type before trusting the gaps — but the failure mode is inherent to
   inferring type from signals.

3. **Bounded sampling.** 15 pages on a 10,000-page site is a sample. Priority
   ordering targets high-value pages, but a problem confined to an unsampled
   section will be missed. The report states `pages_sampled` so the reader can
   calibrate.

4. **Regex-based fact extraction.** Phone, price and postal patterns are
   generic and locale-biased toward Latin-script, largely US/UK formats. They
   can miss valid international formats and can pick up unrelated numbers.

5. **Off-site corroboration depends on a search tool.** Without one, that check
   is explicitly skipped and recorded — never guessed.

6. **Pillar scores are not validated.** They are a presentation device with an
   arbitrary (if reasoned) severity weighting, labelled as such in the output.

7. **The main-content extractor is a simplified link-density heuristic**, not a
   full implementation of a mature extraction algorithm. Good enough to separate
   nav from prose; not a research-grade extractor.

8. **Cross-page boilerplate detection is not implemented.** Hashing repeated
   blocks across sampled pages would be the highest-precision boilerplate
   detector available and the multi-page bundle already makes it possible. It is
   the clearest next improvement.

8b. **Entity-type inference remains imperfect for mixed sites.** `django` and
   `postgresql` classify as `professional_services` rather than
   `open_source_project` because the crawl sample did not surface enough
   project-shaped paths. The questions asked are plausible rather than wrong, but
   less specific than they could be. Deepening the crawl on a docs-shaped site
   would help; widening the vocabulary would re-open §19.12.

9. **Language.** Vocabulary lists (CTAs, hedges, hours, comparison markers) are
   English-only. On a non-English site the structural checks still work; the
   vocabulary-driven ones under-report.

10. **`compute_citability` price position is computed but not yet acted on.**
    The signal is collected for mid-page fact burial; only section length
    currently produces a finding from it.

---

## 22b. Finding states, scoring and the roadmap

### Three states, not one

Conflating "broken", "doesn't apply" and "couldn't tell" is how an audit
misleads. Each finding may carry a `status`:

| `status` | Meaning | Counted? | Scored? |
|---|---|---|---|
| *(absent)* | A real defect | Yes | Yes |
| `not_applicable` | The check does not apply to this kind of site | No | No |
| `not_observable` | The site or section could not be seen | No | No |

`finalize_report.py` splits the latter two into `not_assessed[]` with `N-NNN`
ids and renders them under a "Not assessed" heading stating they are coverage
limits, not faults.

### Derived finding fields

Computed in `finalize_report.py` rather than hand-set at ~40 call sites, so they
cannot drift from the findings they describe:

- **`code`** — stable identifier from `CODE_MAP` (a distinctive title substring
  → constant), falling back to a deterministic title slug. `id` is positional
  and reshuffles whenever severities change; `code` is what makes two runs
  diffable.
- **`confidence`** — starts at the evidence tier (measured 0.90 / correlational
  0.75 / speculative 0.50), then −0.15 if the evidence covers one page of many,
  −0.10 if the critic downgraded it, −0.05 for a tier-2 signal, +0.05 if another
  skill corroborated it. Clamped to [0.30, 0.98].
- **`affected_urls`** — `page` plus any URLs already named in the evidence
  string, deduped and capped.
- **`effort`** — quick / moderate / project, from the `EFFORT` table.

### The roadmap

Severity alone is a poor work order: it says what hurts most, not what to pick
up first. `build_roadmap()` buckets by impact **against** effort — critical and
high go to *now* regardless of cost; anything `quick` also goes to *now*,
because deferring it costs more than doing it; `project` work goes to *later*
even at medium severity, because it is a programme rather than a sprint item.
Severity order is preserved inside each bucket.

### Not scoring what was not read

When the run short-circuits, `readiness.overall` is `null` rather than a number.
Five untouched pillars would otherwise average one blocker away into a
healthy-looking score. See §19.11.

## 23. Testing record

### Compliance

The validation script (§21) run against the full marketplace: 8 skills, all
frontmatter valid, name/directory match, no BOM, descriptions within limits,
`allowed-tools` correctly formatted, every referenced file present, manifest
well-formed with exactly one entrypoint. **All checks passed.**

### Regression suite

`python3 tests/run_tests.py` — **85 tests, zero dependencies, no network**,
built from hand-written evidence bundles. Exit 0 = all pass.

Coverage: copyright-range parsing, staleness, commercial-intent gating, blocker
diagnosis across every classified cause, login-wall and app-shell detection
(with negatives), link-rot escalation, timeouts-vs-404s, the user-agent probe's
three confidence levels, redirect loops/chains/HTTP hops, per-site-type
engagement checks (each with a paired negative), entity-type inference including
the aggregator-is-not-a-project case, and the report-layer derivations (`code`,
`confidence`, `affected_urls`, roadmap bucketing).

**Cross-component contract tests** deserve separate mention. A real bug shipped
because `run_audit.py` marked non-defects with a boolean `not_applicable` while
`finalize_report.py` filtered on a `status` string — the two modules disagreed,
so five findings that should not have been counted were counted *and* scored.
No test crossed that boundary. Four now do:

- every `status` value the orchestrator can emit is one the report recognises
- a blocker finding ends up in `not_assessed[]`, not in the severity counts
- `status` survives the critic's deep copy
- `short_circuited` survives the critic and suppresses scoring

Verified by reintroducing the original bug: three contract tests fail, and pass
again once fixed. A regression test that cannot fail is worthless, so this was
checked rather than assumed.

### Functional, on unseen sites

Deliberately spanning categories, none of which any threshold was tuned against:

| Site | Category | C/H/M/L | Secs | Overall | Notable |
|---|---|---|---|---|---|
| fastapi.tiangolo.com | OSS docs | 0/0/4/6 | 15 | 96 | Flags missing licence + community info |
| postgresql.org | OSS project | 0/0/3/7 | 46 | 96 | |
| djangoproject.com | OSS project | 0/1/1/8 | 19 | 96 | |
| rust-lang.org | OSS project | 0/1/4/5 | 21 | 93 | |
| python.org | OSS project | 0/0/7/6 | 12 | 92 | |
| example.com | Minimal static | 1/1/3/2 | 12 | 90 | Answerability coverage 0.17 on a near-empty page |
| books.toscrape.com | E-commerce | 1/1/12/4 | 36 | 82 | Priced-but-unbuyable + no shipping terms, both correct |
| news.ycombinator.com | Aggregator | 1/3/7/6 | 29 | 80 | Homepage genuinely never states what the site is |
| gnu.org | Throttling origin | — | 21 | **not scored** | Could not be read; says so instead of scoring |
| web.whatsapp.com | Login wall | — | 13 | **not scored** | One finding: "not a public content site" |
| *(nonexistent domain)* | DNS failure | 1/0/0/0 | 1 | **not scored** | Named as DNS, not a generic error |

Earlier runs of this same benchmark are what produced §19.9–19.12: gnu.org
originally took 170s and reported non-existent link rot plus a bot block it had
provoked itself, and web.whatsapp.com originally produced a dozen confident
findings about a sign-in screen.

The score ordering matches independent intuition about how well each would be
represented by an assistant, which is
the behaviour generalisation requires.

### Discrimination checks

- gov.uk vs postman.com: commercial findings fire on the SaaS pricing site and
  **not** on the guidance site — the specific false positive that was fixed.
- gov.uk homepage resolves `SOCIAL_META_ONLY` while its sub-pages resolve
  `STRUCTURED_DATA_PRESENT`, confirming the ladder discriminates within a
  single site rather than emitting one verdict per domain.
- excalidraw.com (client-rendered app) correctly triggered the render-gap
  finding at 10 characters of extractable text against 6 scripts and an
  `id="root"` element.

### Discrimination checks, continued

- **Entity type**: rust-lang and fastapi classify as `open_source_project`;
  Hacker News, which links to GitHub constantly, does not (§19.12).
- **Commercial gating**: `books.toscrape.com` (a real catalogue) gets the
  priced-but-unbuyable and shipping-terms findings; `python.org`, whose PSF
  grant pages contain currency figures, does not.
- **Timeout vs defect**: a bundle of five transport failures produces an
  unobservable note; five 404s produces a critical link-rot finding.

### Bugs found and fixed during testing

**Ten**, all documented in §19. Six from earlier rounds (URL-keyword commercial
detection, "subscribe" as purchase intent, two entity-type misclassifications,
an over-strict critic anchor regex, critic over-merging) and four from the
latest benchmark (timeouts as link rot, a self-provoked 429 as a bot block, an
unreachable site scoring 100/100, an aggregator read as an open-source project).

Two further bugs were caught by tests rather than by live output: the
`not_applicable`/`status` mismatch between the orchestrator and the report
(§23), and a path regex anchored with `$` while matching against a space-joined
string, so it only ever matched the last URL (§19.12).

Every one of these was found by reading actual output or writing a test that
crossed a real boundary — none by re-reading the code and reasoning about it.

---

## 24. Extending the marketplace

### Adding a check to an existing skill

1. If it needs new page data, add extraction to `DocParser` or one of the
   `compute_*` functions in `evidence_collector.py`, and bump
   `COLLECTOR_VERSION`.
2. Add the check to the relevant `analyze_*.py`, using the local `finding()`
   helper so category and shape stay consistent.
3. Set `signal_tier` (1 = gatekeeper, 2 = secondary) and `evidence_tier`
   honestly. If you cannot cite a measured result, it is `correlational` at
   best.
4. Ensure the evidence string contains a concrete anchor, or the critic will
   drop it.
5. Add a row to the skill's `references/checklist.md` and, if the check can
   misfire, a Gotchas entry in its SKILL.md.
6. Run against at least three site types before trusting it.

### Adding a skill

1. Create `skills/<name>/` with `SKILL.md`, `scripts/`, `references/`.
2. `name` must match the directory exactly; use only the six permitted
   frontmatter fields.
3. The analyzer takes `--evidence` and emits
   `{"skill", "site", "findings"}` on stdout.
4. Register it in `marketplace.json` (without `entrypoint`) and in
   `ANALYZERS` in `run_audit.py`.
5. Add a pillar in `finalize_report.py` if it represents a new dimension.
6. Re-run the validation script.

Before adding one, apply the decomposition test from §2: does it own a distinct
failure mode with a different fix owner, and is it independently useful? If
not, it belongs inside an existing skill.

### Changing a threshold

Thresholds are not arbitrary. Each traces to `evidence-base.md`. If you change
one, update the evidence base with what justified the change — and if nothing
does, that is a reason not to change it.
