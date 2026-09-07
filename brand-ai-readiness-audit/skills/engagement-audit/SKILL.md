---
name: engagement-audit
description: Check whether a visitor who arrives on a website can orient, act and reach what they came for - HTTPS and mobile viewport, whether common goals like contact, pricing, about and products are reachable within a few clicks of the homepage, whether the homepage states a value proposition at all, dead-end pages, missing on-site search, absent calls to action, render-blocking scripts, image alt text and unlabelled form fields. Use when a site gets traffic but visitors bounce or do not convert, when auditing on-site experience, or as the engagement half of a broader AI-readiness audit.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read
metadata:
  marketplace: brand-ai-readiness-audit
  stage: "6"
---

# Engagement Audit

Discoverability wins the click. This covers what happens next — and it is where
discoverability gains leak away if the arriving visitor cannot orient.

## When to use

Stage 6 of the `audit-orchestrator` flow, or standalone when investigating
bounce and conversion problems.

## Inputs

An `evidence.json` bundle from `crawl-render-audit`.

## Procedure

1. Run the structural checks:
   ```
   python3 scripts/analyze_engagement.py --evidence evidence.json
   ```

2. **Judge homepage orientation yourself.** The script cannot read for
   comprehension. Using the homepage `text_sample` in the bundle, answer the
   three questions in
   [references/orientation_rubric.md](references/orientation_rubric.md) —
   what is this, who is it for, what do I do next — quoting the actual text you
   based each answer on. Append the result as a finding in the standard shape.

## The distinctive check — goal-path reachability

Rather than only scoring isolated page attributes, the script walks the crawled
link graph and measures how many clicks it takes to reach the destinations
visitors actually come for: contact, pricing, about, and the product or service
detail. A goal with no crawlable path from the homepage is one a visitor has to
hunt for — and an agent browsing on their behalf gives up sooner than a person
does, reporting instead that it could not find the information.

## Gotchas

- **A goal reported unreachable may exist but be invisible to the crawl.** The
  usual cause is navigation rendered client-side. Check the crawl-render
  findings before telling the user a page is missing when it is really just
  unlinked in HTML.
- **Alt-text coverage is a prompt, not a verdict.** Decorative icons correctly
  use empty alt. A low percentage means review, not that every instance is a
  defect.
- **CTA detection is a fixed vocabulary.** A clear but unusually worded call to
  action will read as missing. Spot-check before reporting confidently.
- **Do not recommend adding a chatbot, popup or newsletter interstitial as an
  engagement fix.** Nothing in the evidence base supports it, and interstitials
  actively harm both experience and crawlability.
- **Engagement findings are not discoverability findings.** Keep the categories
  distinct so the report stays legible to the different teams that own them.

## Output

Findings JSON per `../audit-orchestrator/references/report_schema.md`, all with
`category: engagement`. Thresholds and rationale in
[references/checklist.md](references/checklist.md).
