# Freshness & corroboration — checks and thresholds

## Part A — scripted

| Check | Threshold | Severity |
|---|---|---|
| Stale dates | most recent copyright/updated year ≥2 years old | medium; high at ≥3 years |
| Placeholder content | "coming soon", "under construction", "lorem ipsum" | low; medium if the page also carries a year-old date |
| Conflicting phone numbers | more than one distinct number across sampled pages | high |
| Conflicting email addresses | more than one distinct address across sampled pages | medium |
| Many distinct prices | over 6 across the sample | low, **speculative** — a prompt to spot-check, not a defect |
| No on-site corroboration | no outbound links to reference or review platforms and no press language | medium |

Phone numbers are normalised to their last 10 digits before comparison, so
formatting differences do not register as contradictions.

**Always pass `--today`** with the real current date. Sandbox clocks are
frequently wrong and every staleness judgement depends on it.

## Part B — agent-performed, not scriptable

A crawl of one domain cannot see other domains. This half needs live search and
is bounded at **two to four queries**.

### Source independence — the part most audits miss

Three sources repeating a claim are not three confirmations if two are copies
of the brand's own press release. Classify each result before counting it:

| Class | Counts toward corroboration? |
|---|---|
| The brand's own properties | No |
| Press-release wires and syndication | No |
| Aggregators and scraper sites that copy | No |
| Independent editorial, reference, regulatory or academic sources | **Yes** |

Where many mentions all trace to one origin, report that pattern explicitly. It
looks like strength and is not.

### Mistaken identity

If results for the brand name are dominated by an unrelated organisation, that
is a more urgent version of the missing-`sameAs` finding from
`structured-data-entity-audit`. Cross-reference the two.

### Phrasing

Two to four searches is a sample. Write "no independent coverage found in a
brief search", never "no independent coverage exists".

## Why off-site matters disproportionately

Roughly three quarters of AI citations point at third-party pages rather than
the brand's own domain, and ranked comparison and "best of" content is the
single largest cited content format. A site-only audit therefore addresses a
minority of the citation surface.

## Never recommend

Astroturfed reviews, self-owned "independent" comparison sites, unlabelled
sponsored placements, or any other manufactured corroboration — all are classed
manipulation patterns and are increasingly detected. Also never recommend
removing dates to appear evergreen: undated content measured worse than
recently-dated content.

## Known limits

- Phone and price regexes are generic and can pick up unrelated numbers. Treat
  a single flagged contradiction as worth a look, not as proof.
- Year detection requires proximity to "copyright", "©", "updated" or
  "last modified", so a historical year mentioned in prose does not misfire.
