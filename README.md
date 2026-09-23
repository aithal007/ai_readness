# Brand AI-Readiness Audit

**Adobe University Hackathon 2026 · Round 4 finalist**

An Agent Skill Marketplace that audits any website for two things at once:

- **AI discoverability.** Why an AI assistant misses, misquotes, or refuses to cite this brand.
- **On-site engagement.** Why a visitor who does arrive doesn't stay.

Point it at a domain and it returns one prioritized report: findings with
falsifiable evidence and a severity, the mechanism that makes each one matter,
and a fix, bucketed into what to do now, next and later.

**Recommend-only.** Read-only `GET` traffic, `robots.txt` honoured, no
authentication, no form submission. Nothing here ever changes a live site.

**Zero dependencies.** Python standard library only. No pip install, no browser
binary, no model weights. The whole package is 0.18 MB.

| | |
|---|---|
| Skills | 8, in [agentskills.io](https://agentskills.io) format, exactly one entrypoint |
| Code | 4,925 lines of Python across 10 scripts, plus 1,475 lines of tests |
| Tests | 119 behavioural tests and a spec gate, all offline |
| Runtime | 12 to 46 seconds per site for the scripted engine, 2 to 7 minutes agent-driven |
| Interfaces | Any agent harness that reads `SKILL.md`, the command line, or the local web GUI |

---

## Contents

1. [Quick start](#quick-start)
2. [The model it is built on](#the-model-it-is-built-on)
3. [The skills](#the-skills)
4. [What makes it different](#what-makes-it-different)
5. [Architecture](#architecture)
6. [What a finding carries](#what-a-finding-carries)
7. [The web GUI](#the-web-gui)
8. [Guardrails](#guardrails)
9. [Validation and results](#validation-and-results)
10. [Repository layout](#repository-layout)
11. [Known limitations](#known-limitations)
12. [Engine integrity](#engine-integrity)

---

## Quick start

There are three ways to run it. All three execute the same frozen engine in
`submission.zip`.

**1. The web GUI.** Easiest way to explore a report.

```bash
python3 gui/server.py
# opens http://127.0.0.1:8765
```

Type a domain, press **Run audit**, and browse the result. See [The web GUI](#the-web-gui).

**2. An AI agent.** The way the marketplace is meant to be used. The agent runs
the scripts, adds the two checks that need judgement, and reviews every finding.

```bash
python3 -m zipfile -e submission.zip r3
python3 -c "import shutil, os; shutil.copytree('r3/brand-ai-readiness-audit/skills', 'demo/.claude/skills'); os.makedirs('demo/audit_out')"
cd demo
claude --model claude-sonnet-5 --allowedTools Skill Bash Read Write Glob Grep WebSearch
```

Then ask: *"Use the audit-orchestrator skill to audit https://example.com for AI
discoverability and on-site engagement. Use today's real date. Write every
output file into ./audit_out/."* The skills are provider-neutral, so any harness
that reads `SKILL.md` files works the same way.

**3. Scripts only.** Deterministic, with no LLM.

```bash
cd brand-ai-readiness-audit
python3 skills/audit-orchestrator/scripts/run_audit.py https://example.com --out raw.json --evidence-out evidence.json
python3 skills/evidence-critic/scripts/critique_findings.py --findings raw.json --evidence evidence.json --out adjudicated.json
python3 skills/audit-orchestrator/scripts/finalize_report.py adjudicated.json --site example.com --evidence evidence.json --out audit_report.json --md audit_report.md
```

This produces everything except the two judgement steps and the agent's review.

---

## The model it is built on

A brand gets cited only if six things hold, **in order**. A failure early makes
everything later irrelevant, which is why the work is split this way instead of
into one long checklist.

```
        ┌─────────────────────── audit-orchestrator (entrypoint) ───────────────────────┐
        │  crawls ONCE into evidence.json, then fans out over that single snapshot      │
        └───────────────────────────────────┬──────────────────────────────────────────┘
                                            │
   1 REACH ────► 2 IDENTITY ────► 3 QUOTABLE ────► 4 ANSWERABLE ────► 5 TRUST ────► 6 CONVERT
   crawl-render   structured-      ai-citability-   answerability-     freshness-    engagement-
   -audit         data-entity      audit            probe              corroboration -audit
        │              │                │                │                  │             │
        └──────────────┴────────────────┴────────┬───────┴──────────────────┴─────────────┘
                                                 ▼
                                         evidence-critic
                                (drops, merges, recalibrates, strips)
                                                 ▼
                                    audit_report.json + .md
```

---

## The skills

| Skill | The question it owns | Who fixes it |
|---|---|---|
| **`audit-orchestrator`** *(entrypoint)* | Composes everything and emits the report | — |
| `crawl-render-audit` | Can a crawler reach the page and read it? | Infra / platform |
| `structured-data-entity-audit` | Is it clear *who* this is, and do markup and page agree? | SEO / dev |
| `ai-citability-audit` | Is this the kind of page answer engines actually quote? | Content |
| `answerability-probe` | Can real questions about the brand be answered at all? | Content / product |
| `freshness-corroboration-audit` | Is it current, consistent, and independently corroborated? | Content / PR |
| `engagement-audit` | Does an arriving visitor orient, act, and get there? | UX |
| `evidence-critic` | Do these findings actually hold up? | — |

Each skill owns a **distinct failure mode with a different fix owner**, and
each runs on its own. That is the test for whether a split is real rather than
padding.

---

## What makes it different

### 1. It tests the outcome, not just the inputs

Conventional audits check inputs: is the bot allowed in, is the markup valid.
`answerability-probe` checks the **outcome**. It infers what kind of
organisation this is from the evidence, takes the questions people actually ask
about that kind of organisation, and reports which ones the site's own
extractable text cannot answer. An unanswerable question is the literal reason
an assistant says "I don't have information about that", or fills the gap from
a source the brand doesn't control.

### 2. It is calibrated against evidence, including inconvenient evidence

Every threshold traces to a measured result recorded in the
[evidence base](brand-ai-readiness-audit/skills/audit-orchestrator/references/evidence-base.md).
Every finding carries an `evidence_tier` of `measured`, `correlational` or
`speculative`, so a reader can see how much weight it bears. The core is a
controlled study of 252,000 head-to-head trials across six models, which ranks
signals by their odds ratio of being cited.

That cuts against popular advice where the evidence demands it:

- **An old date is worse than no date.** So the audit says refresh and re-date, never strip dates.
- **A fact buried mid-passage was used less often than not supplying the page at all.** So section length and fact position are audited.
- **Schema markup is not sold as an AI-citation lever.** Controlled studies found null or slightly negative effects. It is recommended for entity identity and rich results, which are real.
- **Blocking `GPTBot` is not a defect.** It is a training crawler. Refusing training while allowing search is a documented, legitimate choice, and flagging it is the most common false positive in this space.
- **A missing `llms.txt` is informational at most.** Of 137,000 domains studied, 97% of published files received zero requests.
- **A do-not-recommend list** covers keyword stuffing (−8.3%, the worst tactic tested), blanket rewrites, hidden text, and anything classed as manipulation. `evidence-critic` strips any recommendation matching it.

### 3. It tells "gated" and "paywalled" apart from "missing"

A page behind a server-side cookie-consent gate, or an article marked
`isAccessibleForFree: false` in its own JSON-LD, is not "no content". It is
content the audit correctly declined to score. Both are detected narrowly, so
neither trades one false-positive class for another.

### 4. It separates "broken", "not applicable" and "couldn't tell"

- A **defect** is counted and scored.
- **`not_applicable`** means the check doesn't apply to this kind of site. A language project has no pricing page.
- **`not_observable`** means the page couldn't be seen: gated, blocked, or timed out.

The last two go into a separate `not_assessed[]` list and are excluded from
counts and scores. Two consequences follow. A timeout is not a broken link. And
a site that couldn't be assessed gets **no score at all**, not 100/100.

### 5. It argues with itself before it reports

`evidence-critic` re-reads every proposed finding against the evidence that
produced it. It drops unfalsifiable claims, claims the evidence contradicts,
duplicates, single-page issues overstated as sitewide, and speculative
mechanisms carrying high severity. What it suppressed, and why, is published in
the report. A suppression list is what makes an audit auditable.

---

## Architecture

The full technical reference is
[`ARCHITECTURE.md`](brand-ai-readiness-audit/ARCHITECTURE.md): 24 sections
covering every file, check, threshold and design decision.

### End-to-end data flow

```
                                  <url>
                                    │
        ┌───────────────────────────▼───────────────────────────┐
        │  run_audit.py                                          │
        │  ┌──────────────────────────────────────────────────┐  │
        │  │ evidence_collector.py        (ONE bounded crawl)  │  │
        │  │  robots + content-signals · UA differential probe │  │
        │  │  sitemap · well-known · BFS ≤15 pages, depth ≤2   │  │
        │  │  DocParser → citability, SD verdict, risks, facts │  │
        │  └───────────────────────┬──────────────────────────┘  │
        │                          ▼                              │
        │                    evidence.json                        │
        │     ┌──────────┬─────────┼─────────┬──────────┬──────┐ │
        │     ▼          ▼         ▼         ▼          ▼      ▼ │
        │  crawl_    structured  citability answer   freshness engage
        │  render     _entity                ability                │
        │     └──────────┴─────────┴────┬────┴──────────┴──────┘  │
        │        six analyzers in parallel, deterministic order    │
        │        an analyzer crash becomes a visible "meta" finding │
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
        │  merge duplicates · recalibrate severity                  │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
        ┌──────────────────────────▼───────────────────────────────┐
        │  finalize_report.py                                       │
        │  codes · confidence · effort · pillar scores · roadmap    │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
                audit_report.json   +   audit_report.md
```

### Design decisions that matter most

- **Collect once, analyze many.** One crawl, one snapshot, six analyzers as pure
  functions over it. No redundant network cost, no drift between skills, and
  every analyzer is testable offline against a saved bundle.
- **Analyzers never import each other.** The evidence bundle is the only
  contract. The orchestrator runs scripts and composes. It never reimplements a check.
- **Crawlers are classed by what blocking them costs.** Each known AI user agent
  carries a `citation_impact`: blocking a search-index crawler *removes*
  citations, a live-fetch agent blocks *live answers*, and a training crawler
  costs *nothing*. A block counts as confirmed only on HTTP 401 or 403. A rate
  limit or timeout is hedged, because the probe itself might have caused it.
- **Structured data is judged on a ladder.** JSON-LD, then microdata, RDFa,
  microformats, legacy markup, Open Graph and machine hints. Weak markup is not
  reported as "no markup".
- **Severity is calibrated twice.** Once in each analyzer from the evidence
  tier, and again in the critic. While any gatekeeper finding is critical or
  high, structural findings are capped, because formatting cannot rescue a page
  that fails a gatekeeper.
- **Confidence is derived, never hand-set.** It starts from the evidence tier
  (measured 0.90, correlational 0.75, speculative 0.50). It drops when only one
  of several pages showed the problem or the critic lowered the severity, and
  rises when two skills found the same issue independently.
- **The roadmap weighs impact against effort.** Critical and high findings go to
  *now*, and so does anything quick to fix. Remaining medium work goes to
  *next*. Low-severity items and long-running programmes go to *later*. So a
  ten-minute config fix isn't queued behind a content programme.
- **Fail soft into a finding.** A failed fetch returns an error record, a
  crashed analyzer becomes a `meta` finding, and a missing search tool is
  recorded. A degraded run never looks identical to a clean one.

---

## What a finding carries

Beyond the required `id`, `title`, `severity`, `evidence` and `suggested_action`:

| Field | Why |
|---|---|
| `mechanism` | Why the problem costs visibility. A fix without a mechanism does not ship. |
| `code` | Stable identifier such as `STALE_DATES`. `id` reshuffles between runs; `code` lets two audits be compared. |
| `confidence` | 0 to 1, derived as described above |
| `affected_urls` | The specific pages |
| `effort` | quick, moderate or project, which feeds the roadmap |
| `evidence_tier` | measured, correlational or speculative |
| `signal_tier` | 1 is a gatekeeper, 2 is secondary |
| `severity_adjusted_from` | Present when the critic changed the severity |
| `status` | Present only on non-defects: `not_applicable` or `not_observable` |

The report also carries readiness scores for the six pillars, the roadmap, the
critic's suppression list, and a `not_assessed` list. The full schema is in
[`report_schema.md`](brand-ai-readiness-audit/skills/audit-orchestrator/references/report_schema.md).

---

## The web GUI

A local web interface for running audits and reading reports. It lives in
[`gui/`](gui/), uses the Python standard library only, and needs no build step
and no internet access beyond the site being audited.

```bash
python3 gui/server.py                 # http://127.0.0.1:8765
python3 gui/server.py --port 9000 --no-browser
```

**What it does**

- **Two run modes.** *Engine* runs the scripted pipeline: deterministic, no
  LLM, about a minute. *Agent* drives Claude Code headless over the same
  skills, with the judgement checks and the review of every finding. Agent mode
  appears only when a Claude Code binary is found; set `CLAUDE_BIN` to point at one.
- **Live progress.** The stages, each analyzer as it reports, and a streamed
  log. In agent mode, every tool call the agent makes is shown as it happens.
- **Overview.** Readiness score, the weakest pillars, findings by severity,
  six pillar bars, and the fixes to make first.
- **Findings.** Search, filter by severity, pillar or skill, and sort by
  severity, confidence or effort. Each finding expands to its evidence,
  mechanism, fix and affected pages.
- **Roadmap.** Do now, next and later, as three columns.
- **Evidence.** Every AI crawler with its operator, type, what blocking it costs,
  its `robots.txt` rule and the live probe result. Also the site files and
  every page sampled.
- **Review.** The critic's suppressions and severity changes, the areas not
  assessed, and in agent mode the agent's own summary.
- **Compare.** Two audits matched by stable finding code: resolved, new, and
  still present.
- **Import.** Drop in any `audit_report.json`, for example from an interactive
  agent session, with its `evidence.json` and `.md` if you have them.
- Light and dark themes, keyboard search with `/`, and a layout that works down to phone width.

**How it stays separate from the engine.** The GUI never edits the
marketplace. On start it checks `submission.zip` against its published SHA-256,
unpacks it into a cache, and runs those scripts exactly as shipped. The header
shows the verified hash. After each agent run it re-hashes the skills the agent
worked with and reports whether they are unchanged.

**Security.** The server binds to `127.0.0.1`, rejects requests whose `Host`
header is not local, and requires a custom header on every request that
changes state, so other websites open in the browser cannot drive it. It
accepts only `http` and `https` targets. Run IDs and static paths are checked
against traversal. All report text is escaped before display, because reports
quote content scraped from arbitrary websites.

---

## Guardrails

- Read-only `GET` only. `robots.txt` is checked before any page beyond the entry
  point. Self-identifying user agent, about 0.4 seconds between requests to a host.
- Login, signup, cart, checkout, account and admin paths are skipped outright,
  as are non-HTML assets.
- Hard-bounded: 15 pages, depth 2, a 150-second crawl budget, and 2 to 4 web searches.
- The one probe that sends non-default user agents does so only to *detect*
  network-level AI-bot blocking, which `robots.txt` analysis cannot see. It
  fetches the same public homepage and nothing more, spaced a second apart.

---

## Validation and results

**Spec compliance.** `python3 tests/validate_spec.py` checks the Agent Skills
rules: the closed six-field frontmatter, name and directory agreement,
encoding, exactly one entrypoint, every referenced file present, the required
report fields, and the 50 MB limit. It was verified by injecting faults, which
it caught.

**Regression suite.** `python3 tests/run_tests.py` runs 119 tests with no
network and no dependencies, built from hand-written evidence bundles. Every
false-positive guard has a paired negative case. Cross-component contract tests
check that the orchestrator, critic and report agree on the finding schema.
They exist because a real bug shipped through that gap once.

**Scripted benchmark.** Eleven sites never used during development:

| Site | Type | C/H/M/L | Score | Notable |
|---|---|---|---|---|
| fastapi.tiangolo.com | OSS docs | 0/0/4/6 | 96 | Flags missing licence and community info |
| postgresql.org | OSS project | 0/0/3/7 | 96 | |
| djangoproject.com | OSS project | 0/1/1/8 | 96 | |
| python.org | OSS project | 0/0/7/6 | 92 | |
| rust-lang.org | OSS project | 0/1/4/5 | 93 | |
| books.toscrape.com | E-commerce | 1/1/12/4 | 82 | Priced but unbuyable, no shipping terms |
| news.ycombinator.com | Aggregator | 1/3/7/6 | 80 | Homepage never states what the site is |
| example.com | Minimal | 1/1/3/2 | 90 | Answers almost no core questions |
| gnu.org | Throttling origin | — | not scored | Could not be read, and says so |
| web.whatsapp.com | Login wall | — | not scored | "Not a public content site" |
| *(dead domain)* | DNS failure | 1/0/0/0 | not scored | Named as DNS, not a generic error |

Two consecutive scripted runs against the same site produce identical findings.

**Agent-driven runs.** Claude Code with Claude Sonnet 5, on sites never used in development:

| Site | Runs | Result |
|---|---|---|
| sqlite.org | 3 | Zero critical and zero high every time, readiness 90 to 96. The scripts flag a critical AI-crawler block. The agent checks further, finds that only the training crawlers are refused while every search crawler is served, and downgrades it. Independent requests confirm this. |
| adobe.com | 1 | Readiness 82. The agent noticed that 6 of the 15 pages sampled were CMS fragment endpoints and suppressed a misleading noindex finding on its own. |
| lua.org | 1, from the GUI | Readiness 82, 0 critical, 3 high. No page sets a mobile viewport, confirmed independently. The other two high findings each rest on a single page. The agent's own summary says they overstate the evidence and should be medium at most, but it left the report unchanged. |

**Ten real false positives** were found by running against live sites and then
fixed. Each is documented with what was observed and what guard was added in
[`ARCHITECTURE.md` §19](brand-ai-readiness-audit/ARCHITECTURE.md#19-false-positive-guards).

---

## Repository layout

```
.
├── README.md                     this file
├── submission.zip                the frozen engine, SHA-256 verified
├── brand-ai-readiness-audit/     the same package, unpacked for reading
│   ├── marketplace.json          manifest; exactly one entrypoint
│   ├── README.md                 marketplace README
│   ├── ARCHITECTURE.md           full technical reference
│   ├── tests/                    validate_spec.py, run_tests.py
│   └── skills/
│       ├── audit-orchestrator/   ENTRYPOINT: run_audit.py, finalize_report.py
│       │   └── references/       report_schema.md, evidence-base.md
│       ├── crawl-render-audit/   evidence_collector.py, the shared crawl engine
│       ├── structured-data-entity-audit/
│       ├── ai-citability-audit/
│       ├── answerability-probe/
│       ├── freshness-corroboration-audit/
│       ├── engagement-audit/
│       └── evidence-critic/
├── gui/                          local web GUI (not part of the engine)
│   ├── server.py                 standard-library server and job runner
│   └── static/                   index.html, app.css, app.js
└── round4/                       Round 4 reproduction materials
```

---

## Known limitations

An audit tool that hides its own limits has no business auditing anything.

- **No JavaScript execution.** Render gaps are detected heuristically, not by
  diffing a rendered page. Sites that inject prices or content by script are
  judged on what a non-rendering crawler sees, which is also what many AI crawlers see.
- **Sampling is bounded at 15 pages.** Near-duplicate pages can use up that
  budget, such as country copies of one pricing page, or CMS fragment URLs.
- **Inline SVG titles leak into page titles.** The collector reads every
  `<title>` element, including ones inside SVG icons, which can distort
  term-coverage findings on icon-heavy sites.
- **The scripts alone over-call AI-crawler blocks.** They probe only a few user
  agents. The agent's review corrects this, which is why agent-driven runs are
  the intended use.
- **Entity-type inference is imperfect**, and the fact patterns lean towards
  English and Latin script.
- **Off-site corroboration needs a search tool.** Without one it is skipped and recorded.
- **Pillar scores are a presentation device**, not a validated metric.

The full list is in [`ARCHITECTURE.md` §22](brand-ai-readiness-audit/ARCHITECTURE.md#22-known-limitations).

---

## Engine integrity

`submission.zip` is the exact package submitted in Round 3. Round 4 requires
the live demo to run that package unchanged, so nothing in it has been edited
since. Its fingerprint:

```
SHA-256  1d5e0f3e4dd12a8c12e205b4723124b4d441cdbf3f76605a2befde9114ec33b1
```

If a single byte changed, this value would change. `brand-ai-readiness-audit/`
is the same package unpacked so the code can be read on GitHub, and it is
byte-identical to the archive. The GUI verifies this hash every time it
starts. Check it yourself:

```bash
python3 -c "import hashlib; print(hashlib.sha256(open('submission.zip','rb').read()).hexdigest())"
```
