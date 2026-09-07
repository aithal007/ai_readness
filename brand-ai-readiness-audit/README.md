# brand-ai-readiness-audit

An Agent Skill Marketplace that audits any website for two things at once:

- **AI discoverability** — why an assistant misses, misquotes, or refuses to
  cite this brand.
- **On-site engagement** — why a visitor who does arrive doesn't stay.

Point the entrypoint at a domain and it returns one prioritized report:
findings with falsifiable evidence and severity, plus mechanism-sound fixes.

**Recommend-only.** Read-only `GET` traffic, `robots.txt` honoured, no
authentication, no form submission, no state-changing request. Nothing here
alters a live site.

**Zero dependencies.** Every script is Python standard library only, so the
marketplace runs on a bare `python3` with no pip install and no browser binary.

> **Full technical reference:** [`ARCHITECTURE.md`](./ARCHITECTURE.md) documents
> every file, check, threshold and design decision — including the live test
> failures that produced each false-positive guard.

## The model it is built on

A brand gets cited only if six things hold, **in order**. A failure early makes
everything later irrelevant — which is exactly why the work is decomposed this
way rather than into one large checklist.

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

## The skills

| Skill | The question it owns | Who fixes it |
|---|---|---|
| **`audit-orchestrator`** *(entrypoint)* | Composes everything, emits the report | — |
| `crawl-render-audit` | Can a crawler reach the page and read it? | Infra / platform |
| `structured-data-entity-audit` | Is it clear *who* this is, and do markup and page agree? | SEO / dev |
| `ai-citability-audit` | Is this the kind of page answer engines actually quote? | Content |
| `answerability-probe` | Can real questions about the brand be answered at all? | Content / product |
| `freshness-corroboration-audit` | Is it current, consistent, and independently corroborated? | Content / PR |
| `engagement-audit` | Does an arriving visitor orient, act, and get there? | UX |
| `evidence-critic` | Do these findings actually hold up? | — |

Each owns a **distinct failure mode with a different fix owner**, and each is
independently runnable and independently useful. That is the test for whether a
split is real rather than padding.

## Three things that make this different

### 1. It tests the outcome, not just the inputs

Every conventional audit checks inputs — is the bot allowed in, is the markup
valid. `answerability-probe` checks the **outcome**: it infers the organisation
type from evidence, takes the questions people actually ask about that kind of
organisation, and reports which ones cannot be answered from the site's own
extractable text. An unanswerable question is the literal reason an assistant
says "I don't have information about that", or fills the gap from a source the
brand doesn't control.

### 2. It is calibrated against evidence, including where the evidence is
inconvenient

Every threshold traces to a measured result recorded in
[`skills/audit-orchestrator/references/evidence-base.md`](skills/audit-orchestrator/references/evidence-base.md),
and every finding carries an `evidence_tier` of `measured`, `correlational` or
`speculative` so a reader can see how much weight it bears.

That cuts against popular advice where the evidence demands it:

- **Schema markup is not sold as an AI-citation lever.** Controlled studies
  found null or slightly negative effects; one test of 1,885 pages saw
  citations *fall*. It is recommended for entity identity and rich results,
  which are real.
- **Blocking `GPTBot` is not reported as a defect.** It is a training crawler.
  Google states blocking `Google-Extended` does not affect Search inclusion.
  Refusing training while allowing search is a documented, legitimate choice —
  and flagging it is the most common false positive in this space.
- **Missing `llms.txt` is informational at most.** Of 137,000 domains studied,
  97% of published files received zero requests.
- The marketplace maintains a **do-not-recommend list** — keyword stuffing
  (−8.3%, the worst tactic tested), blanket rewrites (up to −36% retrieval),
  hidden text, and anything classed as manipulation. `evidence-critic`
  mechanically strips any recommendation matching it.

### 3. It argues with itself before it reports

`evidence-critic` re-reads every proposed finding against the evidence that
produced it and drops the ones that don't hold: unfalsifiable claims, claims
the bundle contradicts, duplicates found independently by two skills,
single-page issues overstated as sitewide, speculative mechanisms carrying high
severity. What it suppressed — and why — is published in the report, because a
suppression list is what makes an audit auditable rather than merely assertive.

## How the entrypoint composes it

1. **Collect once.** `run_audit.py` crawls the site a single time into
   `evidence.json`, then runs all six analyzers against that one snapshot. Every
   skill therefore reasons over *identical* evidence — no drift, no contradictory
   findings from differently-timed fetches, and one crawl budget instead of six.
2. **Add what scripts can't do.** Two steps need judgement: off-site
   corroboration with **source-independence** analysis (three sources are not
   three confirmations if two are copies of one press release), and homepage
   orientation clarity. Both are agent-performed and explicitly *not* faked in
   code.
3. **Adjudicate.** `evidence-critic` runs, mechanically then by judgement.
4. **Finalize.** `finalize_report.py` assigns IDs, computes severity counts and
   pillar scores, and writes the JSON report plus a readable Markdown version.

A failed analyzer becomes a visible `meta` finding, never a silent gap — a
degraded run that looks identical to a clean one is the worst outcome in a
multi-step audit.

## Running it without an agent

```bash
python3 skills/audit-orchestrator/scripts/run_audit.py https://example.com \
    --out raw_findings.json --evidence-out evidence.json --today 2026-09-07
python3 skills/evidence-critic/scripts/critique_findings.py \
    --findings raw_findings.json --evidence evidence.json --out adjudicated.json
python3 skills/audit-orchestrator/scripts/finalize_report.py adjudicated.json \
    --site example.com --evidence evidence.json --out audit_report.json --md audit_report.md
```

Each analyzer also runs standalone against an `evidence.json`.

This produces everything except the two judgement steps, which need an agent
following the SKILL.md procedures.

## Guardrails

- Read-only `GET` only. `robots.txt` checked before any page beyond the entry
  point. Self-identifying user-agent, ~0.4s between requests to a host.
- Login, signup, cart, checkout, account and admin paths are skipped outright,
  as are non-HTML assets.
- Hard-bounded: 15 pages, depth 2, 150-second crawl budget, 2–4 web searches.
  Observed runtime is **~30 seconds for 12 pages**, well inside the 5-minute
  target.
- The one probe that sends non-default user-agents does so only to *detect*
  CDN-level AI-bot blocking — a failure mode invisible to `robots.txt` analysis
  — and it fetches the same public homepage, nothing more.

## Layout

```
brand-ai-readiness-audit/
├── marketplace.json          manifest; exactly one entrypoint
├── README.md                 this file
├── ARCHITECTURE.md           full technical reference
└── skills/
    ├── audit-orchestrator/   ENTRYPOINT — run_audit.py, finalize_report.py
    │   └── references/       report_schema.md, evidence-base.md
    ├── crawl-render-audit/   evidence_collector.py (the shared crawl engine)
    ├── structured-data-entity-audit/
    ├── ai-citability-audit/
    ├── answerability-probe/
    ├── freshness-corroboration-audit/
    ├── engagement-audit/
    └── evidence-critic/
```

3,457 lines of Python across 10 scripts. Every skill folder holds a `SKILL.md`,
its analyzer in `scripts/`, and its detailed check tables in `references/`.

## What a report looks like

```
# AI Discoverability & Engagement Audit — rust-lang.org
_Audited 2026-09-08T18:47:05Z · 8 pages sampled in 8.0s_

**8 findings** — 0 critical · 2 high · 3 medium · 3 low

| Pillar                 | Score              |
|------------------------|--------------------|
| Reachable              | █████████░ 95/100  |
| Readable               | █████████░ 93/100  |
| Quotable               | █████████░ 94/100  |
| Answerable             | ████████░░ 88/100  |
| Current & corroborated | ██████████ 100/100 |
| Engaging               | ████████░░ 83/100  |

## Fix these first
- F-001 · 2 of 7 core questions about this brand cannot be answered from
  its own extractable content — Publish each missing fact as plain text...
```

Each finding carries evidence, the mechanism explaining why it matters,
a prioritized action, an `evidence_tier`, and any severity adjustment the
critic applied. The report ends with the critic's struck-through suppression
list.

## Validation and testing

Every skill passes the Agent Skills specification rules — closed six-field
frontmatter, name/directory match, space-separated `allowed-tools`, no BOM,
descriptions within limits, all referenced files present, manifest well-formed
with exactly one entrypoint.

Tested end-to-end on six unseen sites spanning minimal-static, open-source,
government-guidance, government-media, SaaS and aggregator categories:

| Site | Findings | Overall | Notable |
|---|---|---|---|
| rust-lang.org | 8 | 92 | Cleanest; appropriate for well-maintained docs |
| nasa.gov | 12 | 88 | Correctly flagged facts locked in non-text |
| postman.com | 10 | 87 | Correctly flagged JS-rendered prices |
| news.ycombinator.com | 17 | 79 | Critical: homepage never states what the site is |

Six real false positives were found by running against live sites and fixed —
URL-keyword commercial detection, "subscribe" read as purchase intent, two
entity-type misclassifications, an over-strict critic filter, and critic
over-merging. Each is documented in
[`ARCHITECTURE.md` §19](./ARCHITECTURE.md#19-false-positive-guards).

## Known limitations

Stated plainly, because an audit tool that hides its own limits has no business
auditing anything. No JavaScript execution, so render gaps are heuristic.
Entity-type inference is imperfect. Sampling is bounded at 15 pages. Fact
regexes are English- and Latin-script-biased. Off-site corroboration needs a
search tool and is skipped-and-recorded without one. Pillar scores are a
presentation device, not a validated metric. Full list in
[`ARCHITECTURE.md` §22](./ARCHITECTURE.md#22-known-limitations).
