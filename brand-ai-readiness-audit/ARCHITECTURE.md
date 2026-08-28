# Architecture

This document is the detailed, file-by-file companion to [`README.md`](./README.md).
Where the README explains *what* the project does and *why* it's split this way, this
document explains *how* every file works: what each script computes, what data flows
between skills, and the design patterns and known limitations behind the code.

Contents:

1. [Repository layout](#1-repository-layout)
2. [Marketplace manifest](#2-marketplace-manifest)
3. [The shared engine: `page_parser.py`](#3-the-shared-engine-page_parserpy)
4. [`audit-orchestrator` (entrypoint)](#4-audit-orchestrator-entrypoint)
5. [`crawl-render-audit`](#5-crawl-render-audit)
6. [`structured-data-entity-audit`](#6-structured-data-entity-audit)
7. [`freshness-corroboration-audit`](#7-freshness-corroboration-audit)
8. [`engagement-audit`](#8-engagement-audit)
9. [End-to-end data flow](#9-end-to-end-data-flow)
10. [Architectural patterns](#10-architectural-patterns)
11. [Known limitations / latent gaps](#11-known-limitations--latent-gaps)

---

## 1. Repository layout

```
brand-ai-readiness-audit/
├── marketplace.json
├── README.md
├── ARCHITECTURE.md
└── skills/
    ├── audit-orchestrator/
    │   ├── SKILL.md
    │   ├── references/report_schema.md
    │   └── scripts/
    │       ├── run_checks.py
    │       └── finalize_report.py
    ├── crawl-render-audit/
    │   ├── SKILL.md
    │   ├── references/checklist.md
    │   └── scripts/
    │       ├── check_crawl_render.py
    │       └── page_parser.py
    ├── structured-data-entity-audit/
    │   ├── SKILL.md
    │   ├── references/checklist.md
    │   └── scripts/
    │       ├── check_structured_data.py
    │       └── page_parser.py
    ├── freshness-corroboration-audit/
    │   ├── SKILL.md
    │   ├── references/checklist.md
    │   └── scripts/
    │       ├── check_freshness.py
    │       └── page_parser.py
    └── engagement-audit/
        ├── SKILL.md
        ├── references/{checklist.md, orientation_rubric.md}
        └── scripts/
            ├── check_engagement.py
            └── page_parser.py
```

Every leaf skill folder is **self-contained**: it has its own copy of `page_parser.py`
and its own check script, and can be run standalone with nothing but a bare `python3`.
`audit-orchestrator` is the only skill that reaches into the others' folders (by path,
at runtime), and it does so only to invoke their scripts as subprocesses — never by
importing their code.

---

## 2. Marketplace manifest

### `marketplace.json`

The manifest Claude Code reads to register the five skills:

```json
{
  "name": "brand-ai-readiness-audit",
  "version": "1.0.0",
  "skills": [
    { "id": "audit-orchestrator", "path": "skills/audit-orchestrator", "entrypoint": true },
    { "id": "crawl-render-audit", "path": "skills/crawl-render-audit" },
    { "id": "structured-data-entity-audit", "path": "skills/structured-data-entity-audit" },
    { "id": "freshness-corroboration-audit", "path": "skills/freshness-corroboration-audit" },
    { "id": "engagement-audit", "path": "skills/engagement-audit" }
  ]
}
```

`"entrypoint": true` on `audit-orchestrator` is what makes it the one skill users/agents
invoke directly; the other four are composable sub-skills that can also be invoked
individually for a narrower check.

---

## 3. The shared engine: `page_parser.py`

This module is **duplicated byte-for-byte** in all four sub-skill `scripts/` folders
(`crawl-render-audit`, `structured-data-entity-audit`, `freshness-corroboration-audit`,
`engagement-audit`). It is not imported from a shared package — it's copy-pasted so each
skill folder stays independently runnable and distributable. See
[§10.1](#101-duplication-over-shared-imports) for the rationale.

### Constants

```python
USER_AGENT = "BrandAIReadinessAuditBot/1.0 (+read-only compliance audit; ...)"
TIMEOUT = 10
MAX_BYTES = 3_000_000
REQUEST_DELAY = 0.5
AI_CRAWLERS = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-User",
               "Claude-SearchBot", "anthropic-ai", "PerplexityBot", "Perplexity-User",
               "Google-Extended", "Applebot-Extended", "CCBot", "Amazonbot",
               "Meta-ExternalAgent", "Bytespider", "Diffbot"]
```

### Networking helpers

- **`_throttle(host)`** — module-level `_last_request_time` dict; sleeps just enough to
  keep ≥0.5s between requests to the same host.
- **`fetch(url, timeout=TIMEOUT, extra_headers=None)`** — GETs a URL via `urllib.request`.
  **Never raises** — always returns `{url, status, headers, text, error}`. Handles gzip
  manually (checks `Content-Encoding`), decodes using the response's declared charset with
  a utf-8-replace fallback, and catches both `HTTPError` (captures status/body even on
  4xx/5xx) and any other exception (network failure → `status: None`).
- **`resolve_base_url(raw)`** — accepts a bare domain or full URL. If no scheme is given,
  tries `https://` then `http://`, returning the first that fetches with `status < 400`,
  else the last attempt's failure result. Every script's `main()` starts by calling this.
- **`site_root(url)`** — returns `scheme://netloc` with no path, so well-known root files
  (`robots.txt`, `sitemap.xml`, `llms.txt`) resolve correctly even when the audited URL
  has a path component (e.g. `https://example.com/products/widget`).
- **`robots_check(base_url)`** — fetches `/robots.txt` once, parses with
  `urllib.robotparser.RobotFileParser`, returns `(rp, raw_text, status)`.
- **`allowed(rp, url, user_agent="*")`** — wraps `rp.can_fetch`, defaulting to `True`
  (permissive) on any parser exception.

### `PageParser(HTMLParser)`

A single-pass, best-effort structural HTML extractor — explicitly *not* a full HTML5
parser. State captured while parsing:

| Field | What it holds |
|---|---|
| `title` | `<title>` text |
| `lang` | `<html lang="...">` |
| `meta` | list of `{name, content}`, keyed by `name` or `property` (lowercased) — this is how `property="og:title"` gets captured |
| `canonical` | `<link rel=canonical>` href |
| `hreflangs` | list of hreflang links |
| `ld_json_raw` | raw text of every `<script type="application/ld+json">` block |
| `scripts` | list of `{src, head, async_defer, type}` per `<script>` |
| `headings` | list of `(level:int, text:str)` |
| `images` | list of `{src, alt}` |
| `links` | list of `(href, text)` |
| `forms_search` | `True` if any `input[type=search]`, `role="search"`, or `name` containing "search" is found |
| `viewport` | `True` if a viewport meta tag exists |
| `robots_meta` | content of `<meta name="robots">` |
| `noscript_text_len` | character count of text inside `<noscript>` |
| `body_text_parts` | stripped text chunks inside `<body>`, excluding script/style/noscript |
| `has_nav` | `True` if a `<nav>` tag exists |

Parsing subtlety: `<script>`/`<style>`/`<noscript>` push onto a `_skip_stack` so their
inner text isn't counted as body text — **except** `noscript` text is separately tallied
into `noscript_text_len` (used by `crawl-render-audit`'s render-gap heuristic).
`handle_startendtag` handles self-closing tags like `<script src="..." />` by calling
`handle_starttag` then immediately popping the skip stack, so the parser never gets
"stuck" inside a script tag with no matching close tag.

- **`body_text`** property: `" ".join(self.body_text_parts)`.
- **`has_favicon`** property: checks for a sentinel `{"name": "_has_favicon", "content": "1"}`
  pushed into `meta` when a `<link rel="icon"|"shortcut icon">` is seen.

**`parse(html)`** — module function; instantiates `PageParser`, calls `.feed(html)`
wrapped in try/except so malformed HTML never crashes a check, returns the parser.

### Link filtering and sampling

```python
_SKIP_PATH_WORDS = ("login", "signin", "sign-in", "signup", "sign-up", "logout",
                     "cart", "checkout", "account", "wp-admin", "admin")
_SKIP_EXTENSIONS  = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
                     ".zip", ".css", ".js", ".mp4", ".mp3", ".woff", ".woff2", ".xml")
```

**`same_domain_links(base_url, links, limit=6)`** — the internal-page sampler used by
every check script. Filters out fragment/mailto/tel/javascript hrefs, resolves relative
URLs with `urljoin`, restricts to the same netloc, excludes the base URL and duplicates,
excludes skip-extensions and skip-path-words, then **scores** each remaining candidate
by matching `priority_words = ["about", "product", "pricing", "contact", "blog", "news",
"shop"]` against the combined href + link text (earlier words score higher via
`len(priority_words) - i`), sorts descending, and returns up to `limit`. This is the
single mechanism that decides which "~4 same-domain pages" get sampled across the whole
project, and it's why sampling favors about/product/pricing/contact/blog pages over
arbitrary internal links.

---

## 4. `audit-orchestrator` (entrypoint)

Frontmatter: `allowed-tools: Bash WebSearch` — needs `WebSearch` because it performs the
off-site corroboration step on behalf of `freshness-corroboration-audit` itself.

### `SKILL.md` — the 5-step procedure

1. **Normalize the target** — confirm a single concrete domain, not a brand name or
   search query.
2. **Run scripted checks**: `python3 run_checks.py <url> --out raw_findings.json --today
   <YYYY-MM-DD>`.
3. **Add two judgment findings the scripts structurally can't produce**:
   - `freshness-corroboration-audit`'s Part B (2–4 bounded live web searches for
     off-site agreement / mistaken-identity).
   - `engagement-audit`'s step 2 (homepage orientation-clarity judgment, scored against
     `references/orientation_rubric.md`).
   If no search tool is bound in the host, emit a low-severity `meta` finding instead of
   skipping or fabricating.
4. **Finalize**: `python3 finalize_report.py raw_findings.json --site <url> --out
   audit_report.json --md audit_report.md`.
5. **Present the result**, leading with critical/high findings and their
   `mechanism`/`suggested_action`, without manufacturing filler findings.

### `references/report_schema.md` — the shared contract

Two shapes, targeted by every skill in the project:

**Raw finding** (no `id` yet — emitted by scripts and by agent judgment steps):

```json
{
  "title": "...", "severity": "critical|high|medium|low",
  "category": "discoverability|engagement|meta",
  "evidence": "...", "mechanism": "...",
  "suggested_action": { "summary": "...", "priority": "...", "how": "(optional)" }
}
```

**Final report** (emitted only by `finalize_report.py`):

```json
{
  "site": "...", "audited_at": "ISO8601 UTC",
  "summary": { "total_findings": N, "critical": N, "high": N, "medium": N, "low": N },
  "findings": [ { "id": "F-001", "...raw fields...", "source_skill": "..." } ]
}
```

This is documented as a strict superset of a smaller required schema (`site`,
`audited_at`, `summary.total_findings/critical/high/medium`, per-finding
`id/title/severity/evidence/suggested_action`) — `category`, `mechanism`,
`source_skill`, and `summary.low` are additive extensions on top of that minimum.

**Severity rubric** (canonical, referenced by every skill's checklist):

| Severity | Meaning |
|---|---|
| **critical** | Actively blocks discoverability/access outright (robots.txt blocks all, noindex homepage, no HTTPS) |
| **high** | Major, likely-active cause of poor citation/engagement (real JS-render gap, missing homepage structured data, no viewport) |
| **medium** | Real but non-blocking gap (missing sitemap, inconsistent facts, no search on a large site) |
| **low** | Polish / proactive (no favicon, no llms.txt, no blog) |

**Ordering/dedup rule**: sort by severity, then by category (`discoverability` →
`engagement` → `meta`) within a tier, then assign sequential `F-NNN` IDs. Exact
`(title, category)` duplicates across sub-skills are merged, keeping the richer evidence.

### `scripts/run_checks.py`

```
python3 run_checks.py <url> [--out raw_findings.json] [--today YYYY-MM-DD]
```

Subprocess-drives each sub-skill's check script and merges their JSON output.

```python
SUB_SKILLS = [
    ("crawl-render-audit", "check_crawl_render.py", False),
    ("structured-data-entity-audit", "check_structured_data.py", False),
    ("freshness-corroboration-audit", "check_freshness.py", True),
    ("engagement-audit", "check_engagement.py", False),
]
```

Only `check_freshness.py` accepts/needs `--today`.

`main()`:
- Computes `root = Path(__file__).resolve().parents[3]` — walks up from
  `skills/audit-orchestrator/scripts/` to the marketplace root — to locate
  `root/skills/<skill_id>/scripts/<script_name>` for each sub-skill. This is how the
  orchestrator "finds" its siblings with no package/`sys.path` machinery at all.
- Builds `cmd = [sys.executable, str(script_path), args.url]` (+ `--today` if
  applicable) and runs each via `subprocess.run(cmd, capture_output=True, text=True,
  timeout=100)`.
- Parses stdout as JSON, tags each finding with `f.setdefault("source_skill", skill_id)`.
- **Failure handling**: any exception (empty stdout, timeout, bad JSON) is caught and
  converted into one low-severity `category: "meta"` finding titled `"{skill_id} check
  module did not complete"` with the exception text as evidence. This is the exact
  mechanism behind the README's "a sub-check that fails becomes a visible low-severity
  meta finding, not a silent gap."
- Writes `{"site": args.url, "findings": all_findings}` to `--out` and prints only the
  output path (contrast with `finalize_report.py`, which prints the full report).

### `scripts/finalize_report.py`

```
python3 finalize_report.py raw_findings.json [--site example.com] [--out audit_report.json] [--md audit_report.md]
```

```python
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CATEGORY_ORDER = {"discoverability": 0, "engagement": 1, "meta": 2}
REQUIRED_FINDING_FIELDS = ("title", "severity", "evidence", "suggested_action")
```

`main()`:
1. Loads raw findings; `site = args.site or data.get("site", "")`.
2. **Validation**: drops any finding missing a required field — "drop anything malformed
   rather than let it corrupt the report."
3. **Dedup**: keys on `(title, category)`; keeps whichever duplicate has the longer
   `evidence` string.
4. **Sort**: by `(SEVERITY_ORDER[...], CATEGORY_ORDER[...])`.
5. **ID assignment + summary counts**: `enumerate(deduped, start=1)` → `f"F-{i:03d}"`;
   unrecognized severities default to `"low"`; a `counts` dict accumulates per severity.
6. Writes the final report (`site`, `audited_at` = UTC now as `%Y-%m-%dT%H:%M:%SZ`,
   `summary`, `findings`) to `--out`, and **prints the full JSON to stdout**.
7. If `--md` is given, renders one `## F-NNN - Title (SEVERITY)` section per finding with
   Category / Evidence / "Why it matters" (mechanism) / Suggested action (+ optional
   "How") bullets — this is the format shown in the README's example output.

---

## 5. `crawl-render-audit`

Owns **Precondition 1**: can a crawler get in, and can it read the page. `allowed-tools:
Bash` only — no required agent judgment step, though SKILL.md optionally invites manual
JS-render verification when the heuristic is ambiguous.

### `SKILL.md`

Runs `python3 scripts/check_crawl_render.py <url>` — homepage + `robots.txt` +
`sitemap.xml` + up to 4 sampled internal links (≈5–9 total requests, ~0.5s apart). If the
JS-render-gap heuristic is ambiguous, the agent can optionally fetch the page with a
rendering-capable tool and diff visible text against the script's raw-HTML extraction to
confirm/downgrade the finding. Findings are passed through unchanged — the skill doesn't
re-invent severity or evidence.

### `references/checklist.md`

Full check table (robots.txt sitewide block = critical; named AI-crawler block =
critical/high; no sitemap = medium; `X-Robots-Tag: noindex` = critical; `<meta
robots noindex>` = critical; homepage 4xx/5xx = critical; no canonical = low; JS-render
gap = high; no noscript fallback = medium; login/paywall wording = high; broken links =
medium/high).

**Render-gap heuristic**, precisely: flag if visible-text-from-raw-HTML < ~250 chars
**and** (a known SPA root id is present **or** ≥6 `<script>` tags). Documented as a
heuristic with both false-positive risk (a minimal image-heavy landing page) and
false-negative risk (partial SSR + client fetch for the rest). Suggests manual
verification via `curl -A GPTBot <url> | less`.

### `scripts/check_crawl_render.py`

```
python3 check_crawl_render.py <url>
```
→ `{"skill": "crawl-render-audit", "site": ..., "findings": [...]}`

```python
LOGIN_WALL_PATTERNS = [r"sign in to (?:continue|view|read)", r"log in to (?:continue|view|read)",
                        r"subscribe to (?:continue|read|view)", r"become a member to (?:continue|read)",
                        r"create a free account to continue"]
SPA_ROOT_PATTERN = re.compile(r'id=["\'](root|app|__next|__nuxt|app-root|react-root|ng-app)["\']', re.I)
```

`finding(...)` hardcodes `"category": "discoverability"`.

- **`check_robots(base_url, findings)`** — calls `pp.robots_check`. Computes `blocked =
  [ua for ua in pp.AI_CRAWLERS if not pp.allowed(rp, base_url, ua)]` and `star_blocked =
  not pp.allowed(rp, base_url, "*")`. `*` blocked → critical (sitewide). Else any named
  AI crawler blocked → severity `"critical" if len(blocked) >= len(AI_CRAWLERS)//2 else
  "high"`. Separately fetches `site_root(base_url) + "/sitemap.xml"`, flags medium if it
  doesn't return 200 with `"<url"` in the body. Returns `rp` for reuse when sampling
  internal pages.
- **`check_index_directives(url, resp, page, findings, label)`** — checks
  `X-Robots-Tag` header and `page.robots_meta` for `"noindex"` (both critical). Called
  once per page (homepage + each sampled internal page).
- **`check_render_gap(url, html, page, findings, label)`** — implements the heuristic
  above (`text_len < 250 and (spa_root or many_scripts)` → high); if also
  `page.noscript_text_len < 100` → additional medium finding for missing noscript
  fallback.
- **`check_login_wall(url, html, page, findings, label)`** — regex-matches
  `LOGIN_WALL_PATTERNS` against lowercased HTML → high on match.
- **`main()`** — resolves base URL; total fetch failure → critical "did not respond",
  exits early; `status >= 400` → critical "Homepage returned HTTP {status}" but
  continues. Runs all four checks above on the homepage, flags missing canonical (low),
  samples up to 4 internal links via `pp.same_domain_links` **skipping any URL
  disallowed by `robots.txt` for `"*"`** before fetching, tracks broken links
  (`status is None or >= 400`), re-runs `check_index_directives`/`check_render_gap` on
  each successfully-fetched sub-page. Broken-links finding severity is `"high"` if *all*
  sampled URLs were broken, else `"medium"`.

---

## 6. `structured-data-entity-audit`

Owns **Precondition 2/3**: are facts stated unambiguously, and is the entity
disambiguated. `allowed-tools: Bash WebSearch` — `WebSearch` is optional/judgment-only,
used to confirm brand-name collision risk before upgrading `sameAs`-missing severity.

### `SKILL.md`

Two judgment calls layered on the script:
1. Product/Article structured-data findings are heuristic (price pattern + purchase
   wording, or an `<article>` tag/blog URL) — sanity-check before reporting with high
   confidence (e.g. a SaaS pricing page may correctly use Service/Offer instead of
   Product).
2. `sameAs`-missing is scripted at a flat `medium`; if the brand name is
   generic/shared, the agent should judge it as more urgent — optionally confirmed with
   a web search.

### `references/checklist.md`

Check table (invalid JSON-LD = high; no JSON-LD at all on homepage = high; JSON-LD
present but no Organization/WebSite type = medium; Organization but no `sameAs` =
medium/raise-if-generic; missing OG title/desc = medium; missing Twitter card = low;
empty `<title>` = high; generic placeholder title = medium; missing meta description =
medium; no `<html lang>` = low; no favicon = low; product page without Product schema =
medium/heuristic; article page without Article schema = medium; no `/llms.txt` =
low/proactive).

**`@type` extraction**: recursively walks every parsed JSON-LD object (including
`@graph` arrays and multi-value `@type` arrays), collecting every `@type` string found
anywhere — so `WebPage` wrapping `@graph: [Organization, WebSite, BreadcrumbList]`
correctly registers `Organization` as present.

**`llms.txt` convention** documented in detail (required `# <Site Name>` H1, optional
blockquote summary, free-form paragraphs, `##`-delimited link lists) — framed as a
cheap, unconfirmed-effect, proactive addition, not a substitute for real crawlability or
schema.

### `scripts/check_structured_data.py`

```
python3 check_structured_data.py <url>
```

```python
PRICE_RE = re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d{2})?")
BUY_WORDS = re.compile(r"\b(add to cart|buy now|add to bag|add to basket|proceed to checkout)\b", re.I)
GENERIC_TITLES = {"home", "homepage", "untitled", "untitled document", "new page", "index", "welcome"}
KNOWN_ENTITY_PROFILES = ["wikipedia.org", "wikidata.org", "linkedin.com/company", "crunchbase.com",
                          "github.com", "youtube.com", "twitter.com", "x.com", "instagram.com", "facebook.com"]
```

`BUY_WORDS` is deliberately narrowed to strong, unambiguous purchase phrases (excludes
generic "checkout") because broader words caused false positives on SaaS pricing pages
during testing (e.g. a product literally named "Stripe Checkout"). `KNOWN_ENTITY_PROFILES`
is defined but **not referenced elsewhere in the script** — the `sameAs` check only tests
for the key's presence, not which domains it points to, so this list is currently
vestigial (see [§11](#11-known-limitations--latent-gaps)).

- **`extract_ld_types(page)`** → `(parsed, invalid, types)`. A recursive `walk(obj)`
  closure collects every `@type` value (string or list) from any dict anywhere in the
  JSON-LD tree, across all top-level `<script type="application/ld+json">` blocks.
  Invalid JSON blocks are counted separately (`invalid`) rather than raising.
- **`check_page(url, html, page, findings, label, is_home)`** — the main per-page check,
  called once for the homepage and once per sampled internal page.
  - Always: invalid JSON-LD count (high); product-page heuristic
    (`PRICE_RE.search(page.body_text) and BUY_WORDS.search(html)`, checked against
    `{"Product", "Offer"} & types`, medium, heavily hedged evidence text); article-page
    heuristic (`<article>` tag or URL matches `/blog/|/news/|/article`, checked against
    `{"Article", "BlogPosting", "NewsArticle"} & types`, medium).
  - Only if `is_home`: no JSON-LD at all (high); JSON-LD present but no
    Organization/WebSite-family type in `{"Organization", "LocalBusiness",
    "Corporation", "WebSite"}` (medium); Organization present but no `sameAs` — checked
    both at top level and inside any `@graph` array (medium, flat regardless of
    name-collision risk per SKILL.md's judgment note); missing OG title/description
    (medium); missing Twitter card (low); empty/missing `<title>` (high) vs. a generic
    placeholder title matched against `GENERIC_TITLES` (medium); missing meta
    description (medium); no `<html lang>` (low); no favicon via `page.has_favicon`
    (low).
- **`main()`** — resolves base URL; fetch failure → medium "Could not fetch homepage",
  exits early. Otherwise parses homepage, calls `check_page(..., is_home=True)`, fetches
  `site_root(base_url) + "/llms.txt"` and flags low severity unless `status == 200` and
  the text starts with `#`. Samples up to **3** internal links (one fewer than
  `crawl-render-audit`'s 4) and calls `check_page(..., is_home=False)` on each.

---

## 7. `freshness-corroboration-audit`

Owns **Precondition 3** (currency/consistency) plus the off-site corroboration/
disambiguation trust layer. `allowed-tools: Bash WebSearch` — the skill most reliant on
`WebSearch`, since its Part B (agreement across *other* domains) is structurally
impossible for a single-domain script to check.

### `SKILL.md` — two-part procedure

- **Part A (scripted)**: `python3 scripts/check_freshness.py <url> --today <YYYY-MM-DD>`.
- **Part B (agent-performed, not scriptable)**:
  1. Note the brand name and 3–5 core identity facts from the homepage.
  2. Run 2–4 web searches (e.g. `"<brand>" wikipedia`, `"<brand>" review OR crunchbase OR
     linkedin`).
  3. Check **agreement** (do independent, non-brand-owned, non-syndicated sources state
     the same facts?) and **mistaken identity** (does the name collide with an unrelated
     entity? — cross-reference `structured-data-entity-audit`'s `sameAs`-missing finding
     when available; treat this as a more urgent version of the same underlying risk).
  4. Append findings in the standard raw-finding shape to the same list — not a separate
     report. Phrase modestly ("no independent mentions found in a brief search," not "no
     independent mentions exist"). If no search tool is available: skip Part B, emit one
     low-severity `meta` finding stating so.

### `references/checklist.md`

Check table (stale copyright/updated year ≥2yr = medium, ≥3yr = high; stale JSON-LD
`dateModified`/`datePublished` >18mo = medium; inconsistent phone numbers across own
pages = high; broken internal links = medium; zero on-site corroboration signals = low;
no discoverable blog/news = low/proactive).

**Year-staleness detection**: looks for a 4-digit 19xx/20xx year immediately following
"copyright"/"©"/"updated"/"last updated" anywhere in raw page text, compares the newest
such year to `--today` (or system clock — SKILL.md explicitly recommends always passing
`--today` since a sandboxed clock can be wrong).

**Internal-consistency detection**: extracts phone-number-shaped and price-shaped tokens
from homepage + up to 4 sampled internal pages, flags when the same fact type has more
than one distinct value across pages. Deliberately does **not** determine which value is
"correct" — only that a contradiction exists, which is itself the defect.

### `scripts/check_freshness.py`

```
python3 check_freshness.py <url> [--today YYYY-MM-DD]
```

The only sub-script that accepts `--today`:
`datetime.strptime(args.today, "%Y-%m-%d").replace(tzinfo=timezone.utc)`, falling back to
`datetime.now(timezone.utc)` if missing/invalid.

```python
YEAR_RE      = re.compile(r"(?:©|copyright)\D{0,12}((?:19|20)\d{2})", re.I)
PHONE_RE     = re.compile(r"(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
PRICE_RE     = re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d{2})?")
UPDATED_RE   = re.compile(r"(?:last updated|updated on|updated)\D{0,6}((?:19|20)\d{2})", re.I)
CORROBORATION_DOMAINS = ["g2.com", "trustpilot.com", "capterra.com", "wikipedia.org", "wikidata.org",
                          "linkedin.com", "github.com", "youtube.com", "crunchbase.com", "bbb.org"]
PRESS_WORDS  = re.compile(r"\b(as seen in|featured in|as featured on|in the press|press coverage)\b", re.I)
```

- **`newest_year(text)`** — combines matches from both `YEAR_RE` and `UPDATED_RE`,
  returns `max(years)` or `None`.
- **`main()`** — resolves base URL; fetch failure → medium finding, early exit. Otherwise:
  - `year = newest_year(html)`; if `age = now.year - year >= 2` → finding, severity
    `"high" if age >= 3 else "medium"`.
  - Scans every `page.ld_json_raw` block for `dateModified"..."` / `datePublished"..."`
    via regex (not full JSON parsing — a lighter-weight approach than
    `structured-data-entity-audit` uses, since only two keys are needed), parses each as
    an ISO date, flags any where `(now - d).days > 545` (~18 months) → one aggregated
    medium finding listing all stale key/value pairs.
  - **Cross-page consistency**: `sample_urls = [base_url] + pp.same_domain_links(base_url,
    page.links, limit=4)`. Reuses the already-fetched homepage response instead of
    refetching it. Extracts phone numbers and price tokens into
    `facts["phone"][value] = {urls...}` / `facts["price"][value] = {urls...}`, checks
    `sub.links` against `CORROBORATION_DOMAINS`, checks raw text against `PRESS_WORDS`,
    checks the URL itself against `/blog/|/news/`. Tracks broken links separately.
  - Broken-links finding **deliberately reuses the exact title** `"Broken links
    encountered while sampling internal pages"` used by `crawl-render-audit` — a code
    comment explains this is intentional, so `finalize_report.py`'s `(title, category)`
    dedup key collapses the two independently-discovered instances into one finding
    instead of double-reporting the same broken links.
  - `len(facts["phone"]) > 1` → high "Inconsistent phone numbers across pages," listing
    up to 4 numbers with the URLs where each was seen. (`facts["price"]` is collected but
    **never turned into a finding** — see [§11](#11-known-limitations--latent-gaps).)
  - No `corroboration_hits` and no `press_seen` → low "No visible third-party
    corroboration signals on-site," which also nudges the agent toward Part A→Part B
    handoff: this on-site gap is exactly what the off-site web-search step exists to
    check further.
  - No blog/news-like URL found → low, proactive.

Part B (off-site corroboration) has no code counterpart — it's purely an agent procedure
in `SKILL.md`, using whatever `WebSearch` tool is bound in the host environment. This is
the clearest example in the project of the scripted-vs-judgment split.

---

## 8. `engagement-audit`

Owns: does an arriving visitor understand and stay. `allowed-tools: Bash` only — its one
judgment step (orientation clarity) needs no external tool, only the text the script
already fetched.

### `SKILL.md`

Runs `check_engagement.py`, then the agent performs **step 2: orientation & value-
proposition clarity** — reads the homepage's visible text and judges, per
`references/orientation_rubric.md`, whether a first-time visitor learns (a) what this
is, (b) who it's for, (c) what to do next, within roughly the first screenful. Quotes
specific text as evidence. Appends the resulting finding (`category: "engagement"`) to
the script's findings list in the same shape.

### `references/checklist.md`

Check table (not HTTPS = critical; no viewport meta = high; no `<h1>` = medium; multiple
`<h1>` = low; skipped heading levels = low; <50% images with alt text = medium; no
`<nav>` despite 15+ links = low; no on-site search despite 40+ links = medium; no CTA
wording = medium; 5+ render-blocking head scripts = medium).

Full CTA word list (mirrors the script's regex): buy now, shop now, add to cart, get
started, start free, sign up, book (a) demo, request a demo, contact us, try (it) free,
subscribe, learn more, download, book now — deliberately broad (includes soft CTAs like
"learn more") to avoid false-flagging low-pressure sites.

Documented limitations: alt-text coverage counts every `<img src>` including legitimately
decorative icons that should carry `alt=""`, so a low percentage is a prompt to look
closer, not automatic proof; the 15/40-link thresholds for nav/search are rough "clearly
too large to browse by hand" heuristics; CTA detection is a fixed word list, so
differently-worded-but-clear CTAs can false-positive as missing.

### `references/orientation_rubric.md`

The scoring rubric for the skill's one agent-judgment step. Three questions, answered
using **only** page text (never domain-name inference or prior knowledge):

1. **What is this?** — a one-sentence statement of what the brand/product/org is or does.
2. **Who is it for?** — any audience/use-case indication, even implicit; a page that
   "could describe almost anything to almost anyone" is weaker.
3. **What do I do next?** — an unambiguous next action visible near the top (overlaps
   with, but is qualitatively deeper than, the script's mechanical CTA-word-list check).

**Severity guidance**:
- All three fail → `high`, category `engagement` ("a fundamental orientation failure,
  not a polish issue").
- One or two fail → `medium`.
- All three clearly answered → no finding (explicitly: don't manufacture one to fill
  space).

**Secondary judgment call — context retention**: while reading, also note whether the
page offers state-persistence cues (breadcrumbs, account/cart indicator, "continue where
you left off," session-aware search). Absence is a much softer signal — raise only as
`low`, and only if the site's own structure (multi-step flow, large catalog) suggests
visitors would actually benefit from it.

### `scripts/check_engagement.py`

```
python3 check_engagement.py <url>
```

```python
CTA_WORDS = re.compile(r"\b(buy now|shop now|add to cart|get started|start free|sign up|"
                        r"book (?:a )?demo|request a demo|contact us|try (?:it )?free|"
                        r"subscribe|learn more|download|book now)\b", re.I)
```

`finding(...)` here hardcodes `"category": "engagement"` — the one script that differs
from the other three's `"discoverability"`.

`main()` (homepage only — no internal-page sampling, unlike the other three scripts):
- Fetch failure → medium finding, early exit.
- **HTTPS**: `urlparse(home["url"]).scheme != "https"` → critical. Checks the *final
  resolved URL* after `resolve_base_url`'s https-then-http fallback, so a site that only
  serves plain HTTP is correctly flagged.
- **Viewport**: `not page.viewport` → high.
- **Heading structure**: `h1_count == 0` → medium; `> 1` → low. Then
  `skipped = any(b - a > 1 for a, b in zip(levels, levels[1:]) if b > a)` — flags only
  forward skips (h1→h3), not backward jumps (h3→h1, which is normal when starting a new
  section) → low.
- **Alt-text coverage**: `content_images = [im for im in page.images if im.get("src")]`;
  if non-empty and `coverage < 0.5` → medium.
- **Nav landmark**: `not page.has_nav and len(page.links) > 15` → low.
- **On-site search**: `not page.forms_search and len(page.links) > 40` → medium.
- **CTA**: `not CTA_WORDS.search(html)` → medium.
- **Render-blocking scripts**: `blocking = [s for s in page.scripts if s["head"] and not
  s["async_defer"] and s.get("src")]`; `len(blocking) > 4` → medium.

This is the only one of the four scripts that never calls `pp.same_domain_links` — it
audits solely the homepage, consistent with its checklist focusing on structural/
orientation signals that are meaningfully first-impression-specific.

---

## 9. End-to-end data flow

```
                         ┌─────────────────────────────┐
                         │   audit-orchestrator (entry) │
                         └──────────────┬───────────────┘
                                        │
                1. run_checks.py <url> --out raw_findings.json --today <date>
                                        │
        ┌──────────────┬───────────────┼───────────────┬──────────────────┐
        ▼              ▼               ▼               ▼
 check_crawl_render check_structured  check_freshness  check_engagement
     .py              _data.py         .py              .py
 (crawl-render-    (structured-data- (freshness-      (engagement-audit)
  audit)            entity-audit)     corroboration-
                                       audit, Part A)
        │              │               │               │
        └──────┬───────┴───────┬───────┴───────┬───────┘
               │  each subprocess prints JSON to stdout:
               │  {"skill": ..., "site": ..., "findings": [...]}
               ▼
     run_checks.py merges all findings, sets source_skill,
     converts any subprocess failure into a "meta" finding
               │
               ▼
        raw_findings.json  {"site": ..., "findings": [...]}
               │
   2. Agent appends judgment-based findings directly into this file's
      "findings" array (same raw-finding shape):
        - freshness-corroboration-audit Part B (live WebSearch, 2-4 queries)
        - engagement-audit step 2 (orientation_rubric.md judgment)
               │
               ▼
   3. finalize_report.py raw_findings.json --site <url>
                          --out audit_report.json --md audit_report.md
        - drops malformed findings
        - dedupes by (title, category), keeping richer evidence
        - sorts by severity then category
        - assigns F-001, F-002, ... IDs
        - computes summary counts
        - writes JSON + optional Markdown
               │
               ▼
        audit_report.json / audit_report.md  (final deliverable)
```

Key relational facts:

- **`audit-orchestrator` never reimplements a check.** It only subprocess-invokes the
  other four skills' scripts (via paths computed from
  `Path(__file__).resolve().parents[3]`) and later performs the two things that literally
  cannot be scripts: live web search across other domains, and reading-comprehension
  judgment of homepage prose.
- **Every script is independently runnable** without the orchestrator — each prints its
  own `{"skill", "site", "findings"}` JSON to stdout, testable/debuggable in isolation.
  Enabled by the `page_parser.py` duplication (no cross-skill import dependency).
- **Cross-skill dedup handshake**: `crawl-render-audit` and
  `freshness-corroboration-audit` both independently detect "broken links" and
  deliberately use the identical finding title so `finalize_report.py`'s
  `(title, category)` key merges them into one finding instead of reporting the same
  broken link twice.
- **Cross-referencing at the judgment layer**: `structured-data-entity-audit`'s
  `sameAs`-missing (flat medium) and `freshness-corroboration-audit`'s Part B
  mistaken-identity check are designed to be cross-referenced by the agent — a
  mistaken-identity finding from live search is "a more urgent version of the
  sameAs-missing finding."
- **Category assignment**: `crawl-render-audit`, `structured-data-entity-audit`, and
  `freshness-corroboration-audit` all hardcode `category: "discoverability"` in their
  local `finding()` helpers; `engagement-audit` hardcodes `category: "engagement"`.
  `"meta"` is reserved exclusively for audit-process-failure findings (from
  `run_checks.py`'s exception handler, or an agent's "no search tool available"
  fallback) — never from a script's normal check logic.
- **`--today` flows one hop**: only `audit-orchestrator`'s `run_checks.py` and
  `freshness-corroboration-audit`'s `check_freshness.py` know about it; the other three
  scripts have no time-sensitivity and ignore it entirely (`run_checks.py`'s
  `wants_today` flag gates whether `--today` is passed through per sub-skill).

---

## 10. Architectural patterns

### 10.1 Duplication over shared imports

`page_parser.py` is copy-pasted identically into all four sub-skill folders rather than
factored into a shared package. This keeps every skill folder self-contained and
independently distributable — a deliberate tradeoff (a little maintenance duplication)
in favor of portability, not an oversight.

### 10.2 Uniform `finding()` factory

Every check script defines its own small `finding(title, severity, evidence, mechanism,
action_summary, action_priority, how=None)` helper that hardcodes that skill's
`category` and assembles the `suggested_action` sub-dict. This enforces schema-shape
consistency by convention rather than a shared validation library — the only code-level
enforcement is `finalize_report.py`'s `REQUIRED_FINDING_FIELDS` filter at the end of the
pipeline.

### 10.3 Fail-soft-into-a-finding, at every level

- `page_parser.fetch()` never raises — it returns an error dict.
- `run_checks.py` converts a subprocess crash into a `meta` finding.
- SKILL.md procedures convert an unavailable `WebSearch` tool into a `meta` finding.

The architecture treats "the audit couldn't check X" as itself a reportable, honest
finding rather than a silent gap or a crash — a philosophy applied consistently across
scripts and skill procedures alike.

### 10.4 Two-tier scripted/judgment split

Marked explicitly by each skill's `allowed-tools` frontmatter: `crawl-render-audit`
(`Bash` only) and `structured-data-entity-audit`/`engagement-audit` are effectively
fully scripted-or-self-contained, while `freshness-corroboration-audit` (and
transitively `audit-orchestrator`) declare `Bash WebSearch` because they have a step
that structurally cannot be a deterministic script (searching other domains).
`structured-data-entity-audit` also declares `WebSearch`, but only for an optional
confidence-boosting judgment call, not a required step.

### 10.5 Raw-finding vs. final-report shape separation

IDs (`F-001`...) are deliberately **not** assigned by individual check scripts — they're
assigned once, globally, after merging and deduping, by `finalize_report.py`. This is
what makes cross-skill dedup (the broken-links title-collision case) possible at all.

### 10.6 Site-root vs. base-URL distinction

Multiple scripts call `pp.site_root(base_url)` rather than `base_url` directly when
resolving well-known root files (`/robots.txt`, `/sitemap.xml`, `/llms.txt`),
specifically to handle an audited URL that itself has a path
(e.g. `https://example.com/products/widget`).

### 10.7 Heuristic-with-documented-limitations

Nearly every non-trivial check (JS-render gap, product/article schema inference,
`sameAs` urgency, phone/price extraction, year-staleness) is explicitly labeled a
heuristic in `references/checklist.md`, with named false-positive/false-negative
scenarios, and SKILL.md procedures instruct the agent to sanity-check or hedge before
reporting with high confidence. The rubric-and-hedging documentation is as much a part
of the architecture as the code that implements the heuristic.

---

## 11. Known limitations / latent gaps

- **`KNOWN_ENTITY_PROFILES`** in `check_structured_data.py` is defined but never
  referenced — the `sameAs` check only tests for the key's presence, not which domains
  it points to. Either vestigial or a placeholder for a not-yet-built check.
- **`facts["price"]` in `check_freshness.py`** is collected identically to
  `facts["phone"]` (per-page price tokens, grouped by value), but only the phone branch
  (`len(facts["phone"]) > 1`) ever produces a finding. Price inconsistency is silently
  collected and never surfaced — a plausible next feature to add (mirror the phone
  branch: `len(facts["price"]) > 1` → a medium/high finding).
- **Heuristic false-positive/negative surfaces** are real and documented per-skill in
  each `references/checklist.md` (JS-render gap on image-heavy landing pages; CTA
  word-list missing differently-worded CTAs; alt-text coverage counting decorative
  icons; year-regex word-proximity edge cases). These are inherent to a zero-dependency,
  no-headless-browser design and are mitigated by hedged evidence text and agent
  sanity-checks rather than eliminated outright.
- **`sameAs`-missing severity is always flat `medium`** in the script; only the agent's
  judgment layer (informed by `freshness-corroboration-audit` Part B) can raise it. A
  site with a truly generic/collision-prone name gets the same script-level severity as
  one with an obviously unique name until an agent applies that judgment.
