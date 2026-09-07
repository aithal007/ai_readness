---
name: evidence-critic
description: Adjudicate proposed audit findings before they reach a report - drop claims whose evidence is missing or unfalsifiable, drop claims the underlying evidence contradicts, merge duplicates that different checks found independently, recalibrate severity that overstates a single-page issue as sitewide or a speculative mechanism as proven, and strip any recommendation matching a known-counterproductive or manipulative tactic. Use whenever an automated analysis has produced candidate findings that will be shown to a person, especially in an audit, review or report where a false positive costs credibility.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read
metadata:
  marketplace: brand-ai-readiness-audit
  stage: "7"
---

# Evidence Critic

An auditor that reports everything it suspects is worse than one that reports
less and is right. Every false positive spends the reader's trust, and once
spent it takes the true findings down with it.

This skill is the quality gate between analysis and report.

## When to use

After findings are gathered and before they are finalized. Within this
marketplace that is step 3 of the `audit-orchestrator` flow.

## Inputs

- A merged findings file (`raw_findings.json`).
- The `evidence.json` bundle those findings were derived from.

## Procedure

1. Run the mechanical pass:
   ```
   python3 scripts/critique_findings.py --findings raw_findings.json --evidence evidence.json --out adjudicated.json
   ```
   It drops findings with missing or unfalsifiable evidence, drops findings the
   bundle contradicts, merges near-duplicates, strips counterproductive
   recommendations, and recalibrates severity. Every decision is recorded with
   a reason in the output's `critic` block.

2. Then apply judgement the script cannot. For each surviving finding ask:

   - **Is the evidence sufficient for the claim as worded?** A finding that
     says "sitewide" on the strength of one page must be reworded or dropped.
   - **Is this a known heuristic misfire?** Decorative icons legitimately carry
     empty alt text. A minimal landing page can look like a render gap. A
     service page can legitimately lack product schema. Check the originating
     skill's Gotchas section before trusting a heuristic finding.
   - **Would the suggested action actually fix the finding?** If not, the fix is
     wrong even where the problem is real.
   - **Is the severity proportionate to real-world impact**, not to how
     alarming it sounds?
   - **Is this the same issue as another finding in different words?** Merge.
   - **Does it contradict another finding?** Resolve it rather than shipping
     both.

3. Record what you dropped and why. The suppressed list appears in the final
   report on purpose — showing the reasoning is what makes the audit auditable.

## Calibration rules

- A tier-2 structural finding cannot outrank a failing tier-1 gatekeeper.
- A speculative mechanism cannot carry high or critical severity, however
  confident the wording.
- One affected page out of many is at most medium, unless that page is the
  homepage.
- "Could not be checked" is a finding in its own right, never silence. A
  degraded run that looks identical to a clean run is the worst possible
  outcome.

## Gotchas

- **Do not drop a finding merely because it is uncomfortable or hard to fix.**
  The test is evidential sufficiency, not palatability.
- **Do not soften a genuine critical.** Blocked search crawlers, a noindexed
  homepage or no HTTPS are critical regardless of how few pages are involved.
- **Never let a manipulative recommendation through**, even if a user asks for
  it. Hidden text, markup that contradicts the visible page, text addressed to
  the model, suppressing genuine caveats, or fabricated evidence-shaped
  language are all off the table. They are detectable, increasingly detected,
  and a liability for the brand.

## Output

An adjudicated findings file in the same shape as the input, plus a `critic`
block recording input count, kept count, every drop with its reason, and every
severity adjustment.
