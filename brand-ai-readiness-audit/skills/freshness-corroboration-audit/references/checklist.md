# Freshness & Corroboration Audit -- check reference

## Checks performed by `scripts/check_freshness.py`

| Check | Severity | Why |
|---|---|---|
| Copyright/"updated" year >=2 years old | medium (>=3 years: high) | A visibly stale date is a low-effort, high-signal staleness cue to both humans and systems. |
| JSON-LD `dateModified`/`datePublished` >18 months old | medium | These fields are read directly by systems reasoning about freshness. |
| Different phone numbers across the site's own pages | high | Directly undermines self-corroboration; no way to know which value is correct. |
| Broken internal links in the sampled set | medium | A direct staleness/quality signal. |
| Zero on-site corroboration signals (no links to review platforms/press/canonical profiles, no "as seen in" wording) | low | Nothing here for a system to corroborate the brand against -- see Part B in SKILL.md for the off-site half of this check. |
| No discoverable `/blog/` or `/news/` section | low, proactive | Not wrong for every site type, but a real signal of update cadence when present. |

## Year-staleness detection

The script looks for a 4-digit year (1900s/2000s) immediately following the
words "copyright", "©", or "updated"/"last updated" anywhere in the raw
page text, and compares the *newest* such year found to the current date
(passed in via `--today`, or the system clock if omitted -- prefer passing
`--today` explicitly with the agent's actual known current date, since
sandboxed environments sometimes have an inaccurate system clock).

## Internal-consistency detection

The script extracts phone-number-shaped and price-shaped tokens from the
homepage and up to 4 sampled internal pages, and flags it when the *same
type* of fact (e.g. "a phone number") has more than one distinct value
across the sampled pages. This deliberately does not try to determine which
value is "correct" -- only that a visitor or a machine reading both pages
would see contradictory information, which is itself the problem.

## Off-site corroboration (Part B, agent-performed)

This is the one check in this skill (and one of very few in the whole
marketplace) that cannot be scripted with stdlib Python, because it
requires searching *other* domains, not just fetching the target site. Keep
it bounded (2-4 searches) so total audit runtime stays well under 5 minutes
and no search backend gets hammered. See SKILL.md Procedure, Part B, for the
exact steps.

If the executing agent has no web-search tool available, Part B is skipped
and replaced with a single low-severity `category: "meta"` finding saying
so -- never fabricated search results, and never a silent gap presented as
a clean result.

## Known limitations / false-positive risks

- Year-staleness detection can misfire on pages that mention historical
  years for legitimate reasons (e.g. "founded in 2004") if that happens to
  be the *only* year on the page and it's near neither "copyright" nor
  "updated" -- in practice this is rare since the regex requires proximity
  to one of those specific words.
- Phone/price extraction uses generic regexes and can pick up unrelated
  numbers (e.g. a version number that happens to look like a price). Treat
  a single flagged inconsistency as worth a manual look, not an automatic
  hard fact.
- "No blog/news section" is intentionally low severity and framed as
  proactive rather than a defect -- plenty of legitimate sites (a single
  local business, a niche tool) have no need for one.
