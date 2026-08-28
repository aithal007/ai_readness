# Orientation & value-proposition clarity rubric

Used in SKILL.md step 2. Read the homepage's visible text (roughly the
first screenful -- the earliest headings and paragraphs in document order)
and answer these three questions. Quote the actual text you're basing each
answer on; if a question can't be answered from the text, that's the
finding.

1. **What is this?** Can you state, in one sentence, what the
   brand/product/organization actually is or does, using only what's stated
   on the page (not prior knowledge or inference from the domain name)?
2. **Who is it for?** Is there any indication of the intended audience or
   use case, even implicitly (e.g. "for engineering teams", "for small
   restaurants")? A page that could describe almost anything to almost
   anyone is a weaker signal than one with a specific audience in view.
3. **What do I do next?** Is there an unambiguous next action visible near
   the top of the page (this overlaps with, but is a qualitative check on
   top of, the script's mechanical CTA-word-list check)?

## Severity guidance

- All three fail (page doesn't say what it is, who it's for, or what to do)
  -> `high`, category `engagement`. This is a fundamental orientation
  failure, not a polish issue.
- One or two fail -> `medium`.
- All three are clearly answered in the first screenful -> no finding; note
  it as a pass, don't manufacture a finding to fill space.

## Context retention (secondary judgment call, same step)

While reading, also note whether the page offers any cues that state
persists across a visit or return trip -- breadcrumbs, a visible
account/cart indicator, "continue where you left off" type affordances, a
session-aware search. Their absence is a much softer signal than the three
orientation questions above (many sites legitimately don't need this) --
only raise it as a `low` finding if the site's own structure (e.g. a
multi-step flow, a large product catalog) suggests visitors would benefit
from it and it's genuinely missing.
