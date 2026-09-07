# Adobe University Hackathon 2026 — Round 3

**Submission:** [`brand-ai-readiness-audit/`](./brand-ai-readiness-audit/) — an
Agent Skill Marketplace that audits any website for **AI discoverability** (why
assistants miss, misquote or won't cite a brand) and **on-site engagement** (why
visitors who arrive don't stay), then emits one prioritized, evidence-backed
report of findings and fixes.

| | |
|---|---|
| **Packaged submission** | `brand-ai-readiness-audit.zip` (~0.10 MB) |
| **Marketplace docs** | [`brand-ai-readiness-audit/README.md`](./brand-ai-readiness-audit/README.md) |
| **Technical reference** | [`brand-ai-readiness-audit/ARCHITECTURE.md`](./brand-ai-readiness-audit/ARCHITECTURE.md) |
| **Evidence base** | [`skills/audit-orchestrator/references/evidence-base.md`](./brand-ai-readiness-audit/skills/audit-orchestrator/references/evidence-base.md) |
| **Skills** | 8, exactly one entrypoint (`audit-orchestrator`) |
| **Code** | 3,457 lines of Python, standard library only |
| **Runtime** | ~30s for 12 pages (target: under 5 minutes) |

## The model

A brand gets cited only if six conditions hold, in order. Each skill owns one
link in that chain, so a failure early correctly suppresses noise from later
stages.

| Stage | Skill | Question it owns | Fix owner |
|---|---|---|---|
| 1–2 | `crawl-render-audit` | Can a crawler reach the page and read it? | Infra / platform |
| 3 | `structured-data-entity-audit` | Is it clear *who* this is? | SEO / web dev |
| 4 | `ai-citability-audit` | Is this the kind of page answer engines quote? | Content |
| 2–4 | `answerability-probe` | Can real questions about the brand be answered? | Content / product |
| 5 | `freshness-corroboration-audit` | Current, consistent, corroborated? | Content / PR |
| 6 | `engagement-audit` | Does an arriving visitor orient and act? | UX |
| — | `evidence-critic` | Do these findings actually hold up? | quality control |
| — | `audit-orchestrator` | Composes everything, emits the report | entrypoint |

Each owns a distinct failure mode with a different fix owner, and each is
independently runnable — the test applied for whether a split is real rather
than padding.

## What makes it different

**It tests the outcome, not just inputs.** `answerability-probe` infers the
organisation type from evidence, takes the questions people actually ask about
that kind of organisation, and reports which ones cannot be answered from the
site's own extractable text.

**It is calibrated against evidence, including inconvenient evidence.** Every
threshold traces to a measured result, and every finding carries an
`evidence_tier` of `measured`, `correlational` or `speculative`. That leads it
to contradict popular advice where the controlled evidence demands it — schema
markup is not sold as an AI-citation lever, blocking `GPTBot` is not reported as
a defect, and missing `llms.txt` is informational at most.

**It argues with itself before reporting.** `evidence-critic` drops
unfalsifiable and contradicted findings, merges duplicates, recalibrates
severity, and mechanically strips any recommendation matching a
known-counterproductive tactic — then publishes what it suppressed and why.

**It collects once.** A single bounded crawl produces one evidence bundle that
all six analyzers read, so every skill reasons over identical evidence at the
cost of one crawl.

## Quick start

```bash
cd brand-ai-readiness-audit

# 1. Crawl once, run all six analyzers over the shared bundle
python3 skills/audit-orchestrator/scripts/run_audit.py https://example.com \
    --out raw_findings.json --evidence-out evidence.json --today 2026-09-08

# 2. Adjudicate the findings
python3 skills/evidence-critic/scripts/critique_findings.py \
    --findings raw_findings.json --evidence evidence.json --out adjudicated.json

# 3. Assign IDs, score, render
python3 skills/audit-orchestrator/scripts/finalize_report.py adjudicated.json \
    --site example.com --evidence evidence.json \
    --out audit_report.json --md audit_report.md
```

This runs everything except the two steps that genuinely need an agent —
off-site corroboration with source-independence analysis, and homepage
orientation clarity. Both are defined in the relevant `SKILL.md` and are
explicitly skipped-and-recorded rather than faked when unavailable.

Each analyzer also runs standalone against an existing `evidence.json`.

## Guardrails

Recommend-only. Read-only `GET` traffic, `robots.txt` honoured before every
non-entry fetch, self-identifying user-agent, ~0.4s per-host throttle,
authenticated-area paths skipped, non-HTML assets skipped, no authentication,
no form submission, no state-changing request of any kind. Hard-bounded at 15
pages, depth 2, a 150-second crawl budget and 2–4 web searches.
