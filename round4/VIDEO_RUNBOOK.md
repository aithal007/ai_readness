# Round 4 video runbook

Everything here was rehearsed against the frozen Round 3 package (`final_adobe`).
Line numbers refer to that package and were checked against it.

## Integrity gates: what must match

The video and `REPLAY_<team>.txt` must agree on every item below. A mismatch is an
integrity failure, so check them last, after the video is cut.

| Item | Value in REPLAY | Say and show on camera |
|---|---|---|
| Site URL | `https://www.sqlite.org/` | type exactly this URL |
| Model | Claude Sonnet 5, `claude-sonnet-5` | state it aloud; it appears in the harness banner |
| Harness | Claude Code v2.1.278 | state it aloud |
| Engine | byte-identical to Round 3 | show `ENGINE_IDENTICAL` |

If you record with a different model, site or harness, edit `REPLAY_TEAMNAME.txt` to
match before submitting. Rename the file to your real team name.

**Which Claude Code.** Version 2.1.278 is the VS Code extension's bundled binary. The
`claude` command is not on this machine's PATH. Either record inside the VS Code
extension and write "Claude Code (VS Code extension) v2.1.278" in REPLAY, or install
the CLI and re-check the version string it reports. Do not leave the two disagreeing.

## Part 1: thought process (3:00)

Anchor every claim to a file. Open each one on screen as you say it.

**1. How the signals were found (about 1:00).**
"Answer engines only cite a page if six things hold in order, so the audit is six
skills in that order, not one big checklist." Show the six-row table in
`skills/audit-orchestrator/SKILL.md`. Then the research behind it:
`skills/audit-orchestrator/references/evidence-base.md`.

- Line 15, Tier 1: the gatekeepers, ranked by measured odds ratios.
- Line 51: position effects. Where in the page a fact sits changes whether it is quoted.
- Line 85: the do-not-recommend list, things measured to be ineffective or manipulative.
- Line 118: where the field over-claims. Say plainly that the audit will not promise
  schema markup causes citations, because the controlled studies show no effect.

**2. How severities are assigned (about 1:00).**
"Severity follows mechanism and evidence strength, and it is argued with before it ships."

- Evidence tiers become a computed confidence: `skills/audit-orchestrator/scripts/finalize_report.py`
  lines 211 to 231 (`_TIER_BASE`, `confidence_of`).
- Crawlers are classed by what blocking them costs, not by name:
  `skills/crawl-render-audit/scripts/evidence_collector.py` line 50 (`citation_impact`:
  removes, none, or intent). That is why refusing a training crawler is not a defect
  (`audit-orchestrator/SKILL.md` line 108).
- A refusal is only "confirmed" on HTTP 401 or 403, while 429, 503 and timeouts are hedged:
  `skills/crawl-render-audit/scripts/analyze_crawl_render.py` line 143.
- Three finding states, so "we could not tell" is never scored as a defect:
  `finalize_report.py` line 34 (`NON_DEFECT_STATUS`).
- The critic drops, merges and recalibrates: `skills/evidence-critic/scripts/critique_findings.py`
  line 79 (`adjudicate`), with the recalibration recorded at line 186 (`severity_adjusted_from`).

**3. How the fixes are derived (about 1:00).**
"Every finding must state the mechanism, not just the symptom, and manipulation is stripped."

- Each finding carries `mechanism` and `suggested_action`:
  `skills/crawl-render-audit/scripts/analyze_crawl_render.py` line 26 (`finding`).
- Recommendations on the do-not-recommend list are removed mechanically:
  `critique_findings.py` lines 42 to 50.
- Fixes are ordered by impact against effort, not severity alone:
  `finalize_report.py` line 157 (`EFFORT`) and line 236 (`build_roadmap`).

## Part 2: trial run (2:00 after trimming)

The real run takes about 6 minutes. Trimming idle waits is allowed. Cutting between the
URL you type and the findings that appear is not, so keep the Skill call, the tool
activity and the report visible and in order.

1. **Wiring, one line.** Show `ENGINE_IDENTICAL` from REPLAY step 1. Say: "These skills are
   byte-identical to what we submitted in Round 3, and the agent finds them through
   Claude Code's normal skill discovery. There is no demo mode."
2. **Say the harness and model aloud.** Claude Sonnet 5 driving Claude Code v2.1.278.
3. **Start the harness** with the REPLAY step 2 command. Approve the Skill prompt if asked.
4. **Paste the REPLAY step 3 prompt.** Type or paste it verbatim.
5. **Show the Skill call** to `audit-orchestrator`, then the collector and analyzers running.
6. **Drill into one finding.** Use the crawler finding. It is the best demonstration
   of why an agent sits on top of the scripts:
   - The scripts alone report a critical: "AI crawlers blocked at the network layer".
   - The agent re-probed with five more user agents. The search and live-fetch agents
     (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot) all get 200.
     Only GPTBot and ClaudeBot get 403.
   - Blocking training crawlers costs no citation visibility, so the agent downgraded it to low.
   - Prove it in one command, on camera:
     `curl -s -o /dev/null -w "%{http_code}\n" -A "GPTBot/1.1" https://www.sqlite.org/`
     prints 403, and the same with `OAI-SearchBot/1.0` prints 200.
7. **Show the prioritisation.** Open the roadmap in `audit_out/audit_report.md` and point out
   now, next and later, bucketed by impact against effort.
8. **Optionally show a second, easy-to-verify finding:** the homepage has no H1.
   `curl -s https://www.sqlite.org/ | grep -ci "<h1"` prints 0.

## What to expect, and what not to promise

Stable across two rehearsals: zero critical, zero high, no XML sitemap (medium), homepage
without an H1 (medium), training crawlers refused while search agents are served (low).
Score 94 to 96 and 12 to 16 findings. Structured data came out medium once and low once.

Do not say the output is identical between runs. Say the substance is stable and the
wording varies.

## Known engine limits (the engine is frozen, so avoid, do not fix)

Changing any script after Round 3 makes the demo engine differ from the submitted one,
which is an integrity failure. These are real defects found while rehearsing. Steer around
them and be honest if a judge trips one.

- **Inline SVG titles corrupt the page title.** The collector appends text from every
  `<title>` element, including ones inside SVG icons, so a page title becomes "Pricing &
  Fees" followed by "Stripe logo" repeated. This produces a false high finding about
  weak term coverage. Seen on stripe.com. Cause: `evidence_collector.py`, line 547.
- **Locale variants eat the crawl budget.** On stripe.com, 13 of 15 sampled pages were
  country copies of the pricing page.
- **The scripted crawler probe over-claims.** It probes only GPTBot and ClaudeBot and
  calls a 403 a critical block. Without the agent's review the score on sqlite.org is 70
  instead of about 95. This is why the demo must be agent-driven, not scripted.
- **Duplicate stale-date findings.** Two checks can each report stale dates, which the
  scripts do not merge. The agent merged them in both rehearsals.

## Do not

- Do not record a different site than the one in REPLAY without editing REPLAY.
- Do not edit any file under `skills/` before recording.
- Do not splice takes. If a run fails, record it again from the top.
