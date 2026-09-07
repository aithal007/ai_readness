---
name: audit-orchestrator
description: Audit any website for the reasons AI assistants fail to find, trust or cite a brand, and the reasons visitors who arrive do not stay, then emit one prioritized report of findings with evidence, severity and fixes. Use this whenever someone asks why a brand is invisible, misquoted, stale or bouncing in AI apps, asks for an AI-discoverability, GEO, LLM-visibility, AI-readiness or answer-engine audit, or simply points at a domain and asks what is wrong with it for AI search - even if they do not use any of those terms. This is the entrypoint skill for the brand-ai-readiness-audit marketplace and it composes all the other skills in it.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read Write WebSearch
metadata:
  marketplace: brand-ai-readiness-audit
  role: entrypoint
  version: "2.0"
---

# Brand AI-Readiness Audit — orchestrator

Runs the whole marketplace against one site and produces a single report.

**Recommend-only.** Everything here is read-only GET traffic. No skill ever
modifies the target site, submits a form, authenticates, or takes any
state-changing action.

## When to use

Any request to diagnose a site's visibility in AI assistants or its on-site
engagement. If the user names a brand but not a domain, get the canonical
domain first.

## Inputs

- A URL or bare domain (required).
- Today's real date, if you know it. Pass it through as `--today`; sandbox
  clocks are frequently wrong and staleness findings depend on it.

## The model this audit is built on

A brand gets cited only if six things hold, in order. Each skill owns one, and
a failure early makes everything later irrelevant.

| # | Question | Skill |
|---|---|---|
| 1 | Can a crawler reach and read the page? | `crawl-render-audit` |
| 2 | Is it clear who this is, and do markup and page agree? | `structured-data-entity-audit` |
| 3 | Is the page the kind of page answer engines quote? | `ai-citability-audit` |
| 4 | Can real questions about the brand actually be answered? | `answerability-probe` |
| 5 | Is it current, self-consistent and corroborated elsewhere? | `freshness-corroboration-audit` |
| 6 | Does a visitor who arrives orient and act? | `engagement-audit` |

`evidence-critic` then adjudicates every proposed finding before it reaches the
report.

## Procedure

Work through this checklist in order. Do not skip a step silently — if one
cannot run, record it and say so in the final report.

- [ ] **Step 1 — Collect once.** From this skill's `scripts/` directory:
  ```
  python3 run_audit.py <url> --out raw_findings.json --evidence-out evidence.json --today <YYYY-MM-DD>
  ```
  This crawls the site **once** into `evidence.json` and then runs all six
  analyzers against that single snapshot, so every skill reasons over identical
  evidence. It prints per-skill progress to stderr and the findings path to
  stdout. Typical cost is 10-15 pages in well under a minute.

  Success condition: `raw_findings.json` exists and parses, and stderr shows a
  line for all six analyzers. Any analyzer that failed appears as a `meta`
  finding — read those, because that area is **unverified, not clean**.

  If collection itself fails, stop and report that the site was unreachable.
  Do not fabricate findings.

- [ ] **Step 2 — Add the two judgement checks scripts cannot do.** Both append
  to `raw_findings.json`'s `findings` array in the same shape as the scripted
  ones (see `references/report_schema.md`).

  **2a. Off-site corroboration and source independence.** Follow Part B of
  `freshness-corroboration-audit`'s SKILL.md. This needs live web search
  because a single-domain crawl structurally cannot see other domains. It
  matters more than it looks: only a small share of AI citations point at a
  brand's own site, so the off-site picture is most of the surface.
  If no search tool is available, append one low-severity `meta` finding saying
  the check could not run. Never invent search results.

  **2b. Homepage orientation.** Follow step 2 of `engagement-audit`'s SKILL.md,
  scoring against its `references/orientation_rubric.md`, using the
  `text_sample` already captured in `evidence.json`.

- [ ] **Step 3 — Adjudicate.** From `skills/evidence-critic/scripts/`:
  ```
  python3 critique_findings.py --findings raw_findings.json --evidence evidence.json --out adjudicated.json
  ```
  Then apply the judgement review in `evidence-critic`'s SKILL.md to what
  survives. Removing a weak finding is a better outcome than shipping it.

- [ ] **Step 4 — Finalize.** From this skill's `scripts/` directory:
  ```
  python3 finalize_report.py adjudicated.json --site <domain> --evidence evidence.json --out audit_report.json --md audit_report.md
  ```
  Assigns IDs, computes severity counts and pillar scores, and writes both the
  JSON report and a readable Markdown version.

- [ ] **Step 5 — Present.** Lead with critical and high findings and what to do
  about them. Give the user the report path. If any step degraded, open with
  what is missing and why.

## Gotchas

- **Pass `--today`.** Without it, staleness is judged against the machine
  clock, which is often wrong in a sandbox.
- **Blocked training crawlers are not a defect.** Refusing GPTBot, ClaudeBot
  or Google-Extended while allowing the search crawlers is a documented,
  legitimate licensing choice that costs no citation visibility. The analyzers
  already encode this. Never "upgrade" such a finding to a problem.
- **Do not promise that schema markup causes AI citations.** The best-controlled
  studies show null or slightly negative effects. Structured data is worth
  recommending for entity identity and search rich results, and the skills word
  it that way. Keep that wording.
- **Never recommend anything on the do-not-recommend list** in
  `references/evidence-base.md` — keyword stuffing, hidden text, blanket
  rewrites, stripping caveats, or text addressed to the model. These are
  measured to be ineffective, manipulative, or both, and the critic will strip
  them anyway.
- **Do not manufacture findings to fill space.** A short report on a healthy
  site is a correct result. Say so plainly.
- **Absence of evidence is not a clean bill of health.** If a check could not
  run, the report must say the area is unverified.

## Output

A single JSON report matching `references/report_schema.md`, plus a Markdown
rendering. Required fields per finding are `id`, `title`, `severity`,
`evidence` and `suggested_action`; summary carries `site`, `audited_at` and
counts by severity. Everything else in the schema is additive.
