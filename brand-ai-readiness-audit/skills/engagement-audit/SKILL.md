---
name: engagement-audit
description: Checks whether a visitor who does arrive at the site actually stays -- HTTPS, mobile viewport, heading structure, image alt-text coverage, on-site search and navigation landmarks for large sites, a clear primary call-to-action, render-blocking scripts, plus a qualitative read of whether the homepage orients a first-time visitor (what is this, who is it for, what do I do next). Use when auditing why visitors bounce after arriving, or as part of a larger AI-discoverability/engagement audit.
license: MIT
allowed-tools: Bash
---

# Engagement Audit

Discoverability gets a visitor (human or an agent browsing on their behalf)
*to* the site. This skill covers what happens once they're there: can they
tell what the site is, orient themselves, trust it, and find the thing
they came for -- or do they bounce. Most checks here are mechanical
(HTTPS, viewport, headings, alt text); one is a qualitative reading-
comprehension judgment a script can't make on its own.

## When to use

As part of a brand AI-discoverability/engagement audit (normally invoked by
`audit-orchestrator`), or standalone when investigating high bounce rates
or low on-site conversion.

## Inputs

A single URL or bare domain.

## Procedure

1. Run the check script:
   ```
   python3 scripts/check_engagement.py <url>
   ```
   It fetches the homepage and checks HTTPS, viewport meta, heading
   structure (`<h1>` count, skipped levels), image alt-text coverage,
   navigation/search affordances (scaled to the site's link count), primary
   CTA wording, and render-blocking head scripts. Full detail and
   thresholds in [references/checklist.md](references/checklist.md).

2. **Orientation & value-proposition clarity (do this yourself, not via the
   script)**: read the homepage's visible text (the script's `body_text`
   extraction, or fetch the page yourself) and judge, using the rubric in
   [references/orientation_rubric.md](references/orientation_rubric.md):
   does a first-time visitor learn, within roughly the first screenful of
   text, (a) what this brand/product/site is, (b) who it's for, and (c) what
   to do next? Quote the specific text (or lack of it) as evidence. This is
   a judgment call the mechanical checks can't make -- a page can pass every
   structural check and still fail to say what it is.

3. Turn that judgment into a finding using the same shape the script emits
   (`title`, `severity`, `category: "engagement"`, `evidence`, `mechanism`,
   `suggested_action`) and append it to the script's findings list.

## Output

A JSON array of findings (script output plus the agent-authored orientation
finding) in the shape documented in
[../audit-orchestrator/references/report_schema.md](../audit-orchestrator/references/report_schema.md).
Each finding's `category` is `"engagement"`.
