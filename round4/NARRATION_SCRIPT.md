# Round 4 video: narration script

Read this aloud. Timings assume about 150 words a minute. Each **[SHOW]** line is
the file to have on screen while you say the paragraph under it. Every line
number was checked against `submission.zip`, the frozen Round 3 package.

Paths are relative to `brand-ai-readiness-audit/skills/`.

---

## Part 1: thought process (target 2:50, hard cap 3:00)

### 0:00 to 0:20 — the model

**[SHOW]** `audit-orchestrator/SKILL.md`, lines 39 to 44 (the six-row table)

> Our marketplace audits a website for why AI assistants miss it, and why
> visitors don't stay. It is built on one idea. A brand only gets cited if six
> things hold, in order: reachable, identifiable, quotable, answerable, trusted,
> and converting. Each is one skill, so a failure early explains everything later.

### 0:20 to 1:15 — how we found the signals

**[SHOW]** `audit-orchestrator/references/evidence-base.md`, line 15, then line 34

> Every check traces to a measurement, recorded in this evidence base. The core
> is a controlled study of two hundred and fifty-two thousand head-to-head trials
> across six models. It ranks signals by odds ratio of being cited. Topic
> coverage, an explicit price, recency and specifications are the gatekeepers.
>
> Some findings were not obvious. An old date measured worse than no date at all,
> so we never tell a site to strip dates. We tell it to refresh them.

**[SHOW]** same file, line 57, then line 118

> Position matters too. A fact buried mid-passage was used less often than not
> supplying the page at all. That is why section length is audited.
>
> And we wrote down where the field over-claims. Controlled studies show schema
> markup does not cause AI citations, and llms.txt has no measured effect. So
> the audit recommends schema for entity identity, never as a citation lever.

### 1:15 to 2:10 — how severity is assigned

**[SHOW]** `crawl-render-audit/scripts/evidence_collector.py`, line 50

> Severity follows mechanism, not keywords. Every AI crawler is classed by what
> blocking it actually costs. Blocking a search crawler removes citations.
> Blocking a training crawler costs nothing, so it is never a defect.

**[SHOW]** `crawl-render-audit/scripts/analyze_crawl_render.py`, line 143

> A block is only confirmed on a 401 or 403. A rate limit or a timeout is
> hedged, because our own probe might have caused it.

**[SHOW]** `evidence-critic/scripts/critique_findings.py`, lines 88, 156 and 162

> Then a critic argues with every finding before it ships. It drops any finding
> without a concrete anchor, a count, a URL or a measurement. And while a
> gatekeeper is failing, it caps structural findings, because formatting cannot
> rescue a page that fails a gatekeeper.

**[SHOW]** `audit-orchestrator/scripts/finalize_report.py`, line 34

> Finally, "couldn't tell" is never scored as "broken". A site we cannot read
> gets no score at all.

### 2:10 to 2:50 — how the fixes are derived

**[SHOW]** `crawl-render-audit/scripts/analyze_crawl_render.py`, line 26

> Every finding must state its mechanism, why the problem costs visibility, next
> to the fix. A fix without a mechanism does not ship.

**[SHOW]** `evidence-critic/scripts/critique_findings.py`, line 104

> Tactics measured to backfire are stripped mechanically. Keyword stuffing,
> hidden text, and instructions aimed at the model never reach the report.

**[SHOW]** `audit-orchestrator/scripts/finalize_report.py`, lines 157 and 236

> Fixes are then ordered by impact against effort, into do now, next and later,
> so a team starts with what is both serious and cheap.

---

## Part 2: trial run (target 1:55 after trimming, hard cap 2:00)

### Before the run (about 20 seconds)

**[SHOW]** the terminal, then `claude --version`

> This is Claude Code version 2.1.280, driving Claude Sonnet 5. These are the
> skills from our Round 3 package, copied unchanged into the project's skills
> folder. Claude Code finds them through normal skill discovery. There is no
> demo mode.

**[TYPE]** or paste the prompt from REPLAY step 5, including the URL, on camera.

### During the run (trim the waits; keep it continuous)

> The agent loads our entrypoint skill, crawls the site once into an evidence
> file, and runs six analyzers over that one snapshot. Then it does the two
> judgement checks the skill asks for, and the critic reviews every finding.

### Drill into one finding (about 45 seconds)

Use the crawler finding if the run produces it. It shows why an agent sits on
top of the scripts.

> Here is the interesting one. The scripts saw GPTBot and ClaudeBot refused, and
> proposed a critical. The agent checked further. Search and live-fetch agents
> are all served. Only training crawlers are refused, and blocking those costs no
> citations. So the agent downgraded it from critical, and wrote its reasoning
> into the finding.

Say the severity the run actually shows. It was low in two rehearsals and medium
in one.

**[TYPE]** these two commands in PowerShell to prove it live:

```
curl.exe -s -o NUL -w "%{http_code}\n" -A "GPTBot/1.1" https://www.sqlite.org/
curl.exe -s -o NUL -w "%{http_code}\n" -A "OAI-SearchBot/1.0" https://www.sqlite.org/
```

> 403 for the training crawler. 200 for the search crawler.

### Prioritisation (about 20 seconds)

**[SHOW]** `audit_out/audit_report.md`, the "Remediation roadmap" section

> And the fixes come sorted by impact against effort. At the top of Do now is
> publishing a sitemap: medium impact, quick to fix. Everything shown came from
> this one run, written to audit_out.

---

## If the run differs from the rehearsals

Findings vary a little between runs. Narrate what the run actually shows. Never
narrate a finding that is not on screen.

If the crawler finding does not appear, drill into "Homepage has no H1" instead,
and prove it with:

```
curl.exe -s https://www.sqlite.org/ | findstr /i /c:"<h1"
```

No output means no H1.
