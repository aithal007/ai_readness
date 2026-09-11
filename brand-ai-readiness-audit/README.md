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

## Verify this submission in under a minute

Neither command touches the network, and both are standard library only.

```bash
python3 tests/validate_spec.py    # packaging + spec + report contract  -> ALL CHECKS PASSED
python3 tests/run_tests.py        # behavioural regression suite        -> 85/85 passed
```

`validate_spec.py` is the mechanical gate: frontmatter key set, name/directory
agreement, encoding and BOM, exactly one declared entrypoint, every declared
skill directory present, the required report fields, and total size against the
50 MB limit. It exits non-zero on any failure.

To see it work end to end, point it at any domain — see
[Running it without an agent](#running-it-without-an-agent).

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

## What makes this different

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

### 3. It knows the difference between "broken", "not applicable", and "couldn't tell"

Most audits have one bucket: *finding*. This one has three, because conflating
them is how audits mislead people.

- A **defect** is counted and scored.
- **`not_applicable`** — the check doesn't apply to this kind of site. A
  language project has no pricing page; saying so is a category error, not a
  finding.
- **`not_observable`** — the site or section couldn't be seen (gated, blocked,
  timed out), so whether it's a problem is unknown.

The last two are split into a separate `not_assessed[]` array, excluded from
the severity counts and the pillar scores, and printed under a "Not assessed"
heading that says plainly they are coverage limits rather than faults.

Two consequences that fall out of taking this seriously:

- A **timeout is not a broken link.** When five healthy pages on a slow host
  timed out, the audit called it "link rot" — wrong. Timeouts are now reported
  separately as unobservable.
- A site that **couldn't be assessed gets no score at all**, not 100/100. An
  unread site is not a healthy one.

### 4. It argues with itself before it reports

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

## What a finding carries

Beyond the required `id`, `title`, `severity`, `evidence` and
`suggested_action`, each finding adds:

| Field | Why |
|---|---|
| `code` | Stable identifier (`STALE_DATES`). `id` is positional and reshuffles between runs; `code` lets you diff two audits and ask "did this get fixed?" |
| `confidence` | 0–1, **derived** from evidence tier, sample size and any critic downgrade — never hand-set, so it can't drift from the finding |
| `affected_urls` | The specific pages, lifted into a structured field |
| `effort` | quick / moderate / project — feeds the roadmap |
| `evidence_tier` | measured / correlational / speculative |
| `signal_tier` | 1 = gatekeeper, 2 = secondary |
| `status` | present only on non-defects (see above) |

The report also carries a **remediation roadmap** bucketing work into *now /
next / later* by impact **against effort** — so a ten-minute config fix isn't
queued behind a content programme just because its severity is lower.

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
├── tests/
│   ├── validate_spec.py      packaging + spec gate (run before submitting)
│   └── run_tests.py          85 behavioural tests, no network
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

**Spec compliance.** `python3 tests/validate_spec.py` — every skill passes the
Agent Skills rules: closed six-field frontmatter, name/directory match,
space-separated `allowed-tools`, no BOM, descriptions within limits, all
referenced files present, manifest well-formed with exactly one entrypoint. It
also asserts the report contract and the 50 MB size limit. Verified to actually
catch faults by injecting a bogus frontmatter key and a second entrypoint;
both were caught and the run exited non-zero.

**Regression suite.** `python3 tests/run_tests.py` — **85 tests, no network, no
dependencies**, built from hand-written evidence bundles. They cover every
false-positive guard, each with a paired negative case, plus cross-component
*contract* tests that assert the orchestrator, critic and report agree on the
finding schema. Those exist because a real bug shipped through that exact gap:
`run_audit` marked non-defects with a boolean while `finalize_report` filtered
on a string, so five "not a defect" findings were silently counted and scored.
Nothing tested that boundary. Now three tests do, and they fail if the bug is
reintroduced.

**Live benchmark**, eleven unseen sites across open-source, documentation,
government, aggregator, e-commerce, minimal-static and hostile inputs:

| Site | Type | C/H/M/L | Score | Notable |
|---|---|---|---|---|
| fastapi.tiangolo.com | OSS docs | 0/0/4/6 | 96 | Flags missing licence + community info |
| postgresql.org | OSS project | 0/0/3/7 | 96 | |
| djangoproject.com | OSS project | 0/1/1/8 | 96 | |
| python.org | OSS project | 0/0/7/6 | 92 | |
| rust-lang.org | OSS project | 0/1/4/5 | 93 | |
| books.toscrape.com | E-commerce | 1/1/12/4 | 82 | Correctly flags priced-but-unbuyable, no shipping terms |
| news.ycombinator.com | Aggregator | 1/3/7/6 | 80 | Homepage never states what the site is |
| example.com | Minimal | 1/1/3/2 | 90 | Answerability coverage 0.17 |
| gnu.org | Throttling origin | — | **not scored** | Could not be read; says so |
| web.whatsapp.com | Login wall | — | **not scored** | One finding: "not a public content site" |
| *(dead domain)* | DNS failure | 1/0/0/0 | **not scored** | Named as DNS, not a generic error |

Max runtime 46s; most sites finish in 12–30s, well inside the 5-minute budget.

**Ten real false positives** were found by running against live sites and
fixed — URL-keyword commercial detection, "subscribe" read as purchase intent,
three entity-type misclassifications (including a tech aggregator read as an
open-source project because it *links* to GitHub), timeouts reported as link
rot, a self-inflicted rate limit reported as a bot block, an over-strict critic
filter, critic over-merging, and an unreachable site scoring 100/100. Each is
documented with what was observed and what guard was added in
[`ARCHITECTURE.md` §19](./ARCHITECTURE.md#19-false-positive-guards).

## Known limitations

Stated plainly, because an audit tool that hides its own limits has no business
auditing anything. No JavaScript execution, so render gaps are heuristic.
Entity-type inference is imperfect. Sampling is bounded at 15 pages. Fact
regexes are English- and Latin-script-biased. Off-site corroboration needs a
search tool and is skipped-and-recorded without one. Pillar scores are a
presentation device, not a validated metric. Full list in
[`ARCHITECTURE.md` §22](./ARCHITECTURE.md#22-known-limitations).
