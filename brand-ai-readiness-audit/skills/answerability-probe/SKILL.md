---
name: answerability-probe
description: Test whether an AI assistant could actually answer the ordinary questions people ask about a brand using only that brand's own machine-readable content - what it is, what it costs, where it is, how to contact it, what is included, opening hours, programs, policies. Infers the organisation type from evidence rather than assumptions, then checks the canonical question set for that type against extractable text and reports each unanswerable question as a named gap. Use when a brand is described inaccurately or vaguely by AI assistants, when asked what an assistant would say about a company, or as part of a broader AI-readiness audit.
license: MIT
allowed-tools: Bash(python3:*) Bash(python:*) Read
metadata:
  marketplace: brand-ai-readiness-audit
  stage: "4"
---

# Answerability Probe

Every other skill audits an **input** — is the bot allowed in, is the markup
valid, is the copy quotable. This one audits the **outcome**.

If a person asked an assistant a normal question about this brand, is the
answer present anywhere in the site's machine-readable text at all? A missing
answer here is not a missed best practice. It is the literal reason an
assistant says "I don't have information about that", or worse, fills the gap
from a third-party source the brand does not control.

## When to use

Whenever a brand is being described inaccurately, incompletely or generically
by assistants, and as stage 4 of the `audit-orchestrator` flow.

## Inputs

An `evidence.json` bundle from `crawl-render-audit`.

## Procedure

```
python3 scripts/analyze_answerability.py --evidence evidence.json
```

The script:

1. **Infers the organisation type** from evidence — schema types, transaction
   signals, opening-hours patterns paired with a postal address, path
   conventions. It never matches against a list of known sites, so it
   generalises to sites it has never seen.
2. **Selects the canonical question set** for that type. A shop is asked about
   price, stock, shipping and returns; a university about programs, admissions,
   fees and deadlines; a local business about hours, phone and booking.
3. **Looks for answer-bearing evidence** in what a non-JavaScript crawler would
   actually see — extracted text plus structured data.
4. **Reports each unanswerable question by name**, with coverage as a fraction.

It also separates two very different failures: a fact that is **absent**, and a
fact that **exists but is locked** in an image, PDF, embed or client-side
template. The second is far cheaper to fix, because the content already exists.

## Reading the result

`coverage` below 0.5 is critical — most of what people ask cannot be answered
from the site. Between 0.5 and 0.75 is high. Above that, the named gaps are
still worth closing but the brand is broadly answerable.

## Gotchas

- **Check the inferred entity type before trusting the gaps.** If it is wrong,
  the question set is wrong and the findings are noise. The finding's evidence
  states the type and why it was inferred, so verify that line first. During
  development, a government guidance site was briefly misread as a local
  business and asked about booking, and a developer-tools vendor was misread as
  a shop and asked about shipping — both were fixed by tightening inference,
  but the failure mode is inherent.
- **A form is not an answer.** A contact form does not answer "how do I contact
  them" for an extractor; a published email or phone number does.
- **Do not treat every gap as equally urgent.** Weight them by how likely a
  real customer is to ask that question of this kind of organisation.
- **Answerable does not mean cited.** This skill measures whether the answer
  exists at all. Whether the page is the kind that gets quoted is
  `ai-citability-audit`'s question.

## Output

Findings JSON per `../audit-orchestrator/references/report_schema.md`. The main
finding carries an `answerability` object with the inferred entity type,
coverage fraction, and the answered and unanswered slot names.
