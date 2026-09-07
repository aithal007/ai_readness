# Adobe University Hackathon 2026 — Round 3

Submission: **[`brand-ai-readiness-audit/`](./brand-ai-readiness-audit/)** — an
Agent Skill Marketplace that audits any website for AI discoverability (why
assistants miss, misquote or won't cite a brand) and on-site engagement (why
visitors who arrive don't stay), and emits one prioritized, evidence-backed
report.

- **Full documentation:** [`brand-ai-readiness-audit/README.md`](./brand-ai-readiness-audit/README.md)
- **Evidence base behind every threshold:** [`skills/audit-orchestrator/references/evidence-base.md`](./brand-ai-readiness-audit/skills/audit-orchestrator/references/evidence-base.md)
- **Packaged submission:** `brand-ai-readiness-audit.zip`

## At a glance

Eight skills, one entrypoint (`audit-orchestrator`). A single bounded crawl
produces one shared evidence bundle that every analyzer reads, so all skills
reason over identical evidence at the cost of one crawl.

| Stage | Skill | Question |
|---|---|---|
| 1 | `crawl-render-audit` | Can a crawler reach the page and read it? |
| 2 | `structured-data-entity-audit` | Is it clear who this is? |
| 3 | `ai-citability-audit` | Is this the kind of page answer engines quote? |
| 4 | `answerability-probe` | Can real questions about the brand be answered? |
| 5 | `freshness-corroboration-audit` | Current, consistent, corroborated? |
| 6 | `engagement-audit` | Does an arriving visitor orient and act? |
| — | `evidence-critic` | Do these findings actually hold up? |

Standard-library Python only, read-only `GET` traffic, `robots.txt` honoured,
~30 seconds for 12 pages.

## Quick start

```bash
cd brand-ai-readiness-audit
python3 skills/audit-orchestrator/scripts/run_audit.py https://example.com \
    --out raw_findings.json --evidence-out evidence.json --today 2026-09-08
python3 skills/evidence-critic/scripts/critique_findings.py \
    --findings raw_findings.json --evidence evidence.json --out adjudicated.json
python3 skills/audit-orchestrator/scripts/finalize_report.py adjudicated.json \
    --site example.com --evidence evidence.json --out audit_report.json --md audit_report.md
```
