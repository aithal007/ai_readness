# PSTrio · Round 4 video script

Everything for the video, in recording order. Five minutes, hard cap:
**Part 1 (methodology) 3:00, Part 2 (live run) 2:00.**

Every code reference below was checked against `submission.zip`, the frozen
Round 3 package. `[SHOW]` is what is on screen, `[DO]` is the action, and the
quoted blocks are what you say. About 150 spoken words is one minute.

---

## 0. The plan in one paragraph

Part 1 walks through the code: the research behind the signals, how severity
is decided, and how fixes are derived. Every claim is shown in its file at its
line. Part 2 runs the audit **live in the terminal**, with Claude Code driving
our entrypoint skill on `https://www.sqlite.org/`. That run is what the judges
replay from `REPLAY_PSTrio.txt`. When the run finishes, one command opens **the
same run's output folder in our GUI**, and that is where you drill into the
evidence and show the prioritized fixes. The GUI only displays files the run
just wrote, so the whole of Part 2 stays one continuous, real run.

---

## 1. Before you record

### Machine setup (once)

1. **Make a clean demo folder**, e.g. `C:\PSTrio_demo`, containing only `submission.zip`.
2. **Unpack it for Part 1** so the code you show is the submitted package itself:
   ```
   cd C:\PSTrio_demo
   python -m zipfile -e submission.zip r3
   ```
   Open `C:\PSTrio_demo\r3\brand-ai-readiness-audit` in VS Code.
3. **Get the GUI.** Clone the repository next to it:
   ```
   git clone https://github.com/aithal007/ai_readness C:\PSTrio_demo\ai_readness
   ```
   A fresh clone has no old audits in the GUI's history. Do not use a copy
   that shows earlier runs: the history list should hold only the run you record.
4. **Make `claude` a command** (PowerShell, each new window):
   ```powershell
   Set-Alias claude "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-2.1.280-win32-x64\resources\native-binary\claude.exe"
   claude --version
   ```
   It must print `2.1.280 (Claude Code)`. Claude Code updates itself. If it
   prints a different version, change `AGENT_HARNESS` in `REPLAY_PSTrio.txt`
   to match before you submit.
5. **Rehearse the whole of Part 2 once**, then delete the `demo` folder so the
   recorded run starts clean. Also delete `ai_readness\gui\runs` so the GUI's
   history is empty again.

### Screen setup (every take)

- Record at 1920×1080. Close notifications (Focus Assist on).
- **VS Code:** font size 16+, minimap off. Pre-open these tabs, left to right, in this order:
  1. `skills/audit-orchestrator/SKILL.md`
  2. `skills/audit-orchestrator/references/evidence-base.md`
  3. `skills/crawl-render-audit/scripts/evidence_collector.py`
  4. `skills/crawl-render-audit/scripts/analyze_crawl_render.py`
  5. `skills/evidence-critic/scripts/critique_findings.py`
  6. `skills/audit-orchestrator/scripts/finalize_report.py`
  Jump to a line with **Ctrl+G**, type the number, press Enter.
- **Terminal:** Windows Terminal, PowerShell, font 16+, `cd C:\PSTrio_demo`.
- **Browser:** closed. The GUI command opens it.
- Pick one GUI theme (dark reads best on video) and stay with it. The sun or moon button in the top-right corner switches it.

### Who speaks

One voice is fine. For three voices, split at the section breaks: **A** does
1.1 and 1.2, **B** does 1.3, **C** does 1.4 and all of Part 2.

---

## 2. Part 1 · Thought process (target 2:50)

### 1.1 · 0:00–0:20 · Who we are and the model

**[SHOW]** `SKILL.md`, **Ctrl+G 39**, lines 39–44 highlighted (the six-row table).

> We're PSTrio. Our marketplace audits any website for why AI assistants miss
> it, and why visitors don't stay. It rests on one idea: a brand is only cited
> if six things hold, in order. Reachable, identifiable, quotable, answerable,
> trusted, converting. Each is one skill, so an early failure explains
> everything after it.

### 1.2 · 0:20–1:15 · How we found the signals

**[SHOW]** `evidence-base.md`, **Ctrl+G 15**. Let the Tier 1 table fill the screen.

> Every check traces to a measurement, recorded in this evidence base. The core
> is a controlled study of 252,000 head-to-head trials across six models. It
> ranks signals by their odds of being cited. Topic coverage, an explicit
> price, recency and specifications are the gatekeepers.

**[DO]** **Ctrl+G 34**.

> Some findings are not obvious. An old date measured worse than no date at
> all. So we never tell a site to strip dates. We tell it to refresh them.

**[DO]** **Ctrl+G 57**.

> Position matters too. A fact buried mid-passage was used less often than not
> supplying the page at all. That is why section length is audited.

**[DO]** **Ctrl+G 118**.

> And we wrote down where the field over-claims. Controlled studies show schema
> markup does not cause citations, and llms.txt has no measured effect. So we
> recommend schema for identity, never as a citation lever.

### 1.3 · 1:15–2:10 · How severity is assigned

**[SHOW]** `evidence_collector.py`, **Ctrl+G 50**.

> Severity follows mechanism, not keywords. Every AI crawler is classed by
> what blocking it costs. Blocking a search crawler removes citations. Blocking
> a training crawler costs nothing, so it is never a defect.

**[DO]** `analyze_crawl_render.py`, **Ctrl+G 143**.

> A block only counts as confirmed on a 401 or 403. A rate limit or a timeout
> is hedged, because our own probe might have caused it.

**[DO]** `critique_findings.py`, **Ctrl+G 88**, then **Ctrl+G 156**.

> Then a critic argues with every finding before it ships. It drops any claim
> without a concrete anchor: a count, a URL, a measurement. And while a
> gatekeeper is failing, it caps structural findings, because formatting
> cannot rescue a page that fails a gatekeeper.

**[DO]** `finalize_report.py`, **Ctrl+G 34**, then **Ctrl+G 211**.

> "Couldn't tell" is never scored as "broken", and a site we cannot read gets
> no score at all. Confidence is computed from the evidence, never typed in.

### 1.4 · 2:10–2:50 · How the fixes are derived

**[SHOW]** `analyze_crawl_render.py`, **Ctrl+G 26** (the `finding()` helper).

> Every finding carries its mechanism, why the problem costs visibility, right
> next to the fix. A fix without a mechanism doesn't ship.

**[DO]** `critique_findings.py`, **Ctrl+G 41**.

> Tactics measured to backfire are stripped automatically: keyword stuffing,
> hidden text, instructions aimed at the model.

**[DO]** `finalize_report.py`, **Ctrl+G 157**, then **Ctrl+G 236**.

> And fixes are ordered by impact against effort, into do now, next and later,
> so a ten-minute fix is never queued behind a content programme. Let's run it.

**[CUT]** to the terminal.

---

## 3. Part 2 · Live run (target 1:55 after trimming)

This must be **one continuous take**. You may cut out waiting. You may not cut
between typing the URL and the findings appearing, or join two runs.

### 2.1 · 0:00–0:15 · Wiring, harness, model

**[SHOW]** Terminal in `C:\PSTrio_demo`, showing only `submission.zip`, `r3`, `ai_readness`.
**[DO]** Paste REPLAY steps 1 to 3, then set the encoding and check the version. Step 1 re-extracts over the `r3` folder from setup, which is fine: same bytes.

```powershell
python -m zipfile -e submission.zip r3
python -c "import shutil, os; shutil.copytree('r3/brand-ai-readiness-audit/skills', 'demo/.claude/skills'); os.makedirs('demo/audit_out')"
cd demo
$env:PYTHONUTF8="1"
claude --version
```

> These are our Round 3 skills, copied unchanged from submission.zip into the
> project's skills folder, where Claude Code discovers them. No demo mode. The
> harness is Claude Code 2.1.280, and the model is Claude Sonnet 5.

### 2.2 · 0:15–0:25 · Start the agent and enter the URL

**[DO]** REPLAY step 4:

```powershell
claude --model claude-sonnet-5 --allowedTools Skill Bash Read Write Glob Grep WebSearch
```

**[DO]** Paste the REPLAY step 5 prompt. **Keep `https://www.sqlite.org/` readable on screen for a second** before pressing Enter.

> A site our audit has never been tuned on: sqlite.org.

### 2.3 · 0:25–0:55 · The agent works (trim the waits)

Keep each of these moments on screen for a beat. Cut the gaps between them.

| Moment | What is on screen | Say |
|---|---|---|
| Skill call | `Skill(audit-orchestrator)` | "It invokes our entrypoint skill." |
| Crawl | a Bash call running `run_audit.py` | "One crawl into an evidence file, then six analyzers over that snapshot." |
| Research | `WebSearch` calls | "It checks the brand's facts against independent sources." |
| Review | `critique_findings.py`, then `finalize_report.py` | "The critic reviews every finding, then the report is written." |

If a permission prompt appears, approve it on camera. That is fine.

### 2.4 · 0:55–1:10 · The agent's answer

**[SHOW]** The agent's final message in the terminal.

> No critical or high findings. The interesting part is what it changed. The
> scripts flagged a critical crawler block. The agent checked further and
> downgraded it, and it explains why here.

### 2.5 · 1:10–1:20 · Open the same run in the GUI

**[DO]** Open a second terminal tab in `C:\PSTrio_demo`:

```powershell
python ai_readness\gui\server.py --open demo\audit_out
```

The browser opens on the **Overview**. The gauge sweeps to the score.

**[SHOW]** Point the cursor at the blue banner: *"Opened from a run's output folder … \demo\audit_out"*.

> This is our GUI, showing the files that run just wrote, unchanged. Readiness
> in the 90s, zero critical, zero high.

### 2.6 · 1:20–1:45 · Drill into one finding

**[DO]** Click **Evidence**. The AI crawler table is at the top.

**[SHOW]** The **GPTBot** and **ClaudeBot** rows: red edge, live probe **403**, cost of blocking *None (training only)*. Then the **PerplexityBot** row: live probe **200**, cost *Removes citations*. PerplexityBot is the only search crawler the engine probes itself; the others show *not probed*.

> Here's the evidence. GPTBot and ClaudeBot get a 403. They're training
> crawlers, and blocking them costs no citations. PerplexityBot, a search
> crawler, gets a 200.

**[DO]** Click **Findings**, type `crawler` in the search box, and expand the crawler finding.

**[SHOW]** Evidence, then *Why it matters*, then *Suggested fix*. In two of three rehearsals the card also carried the chip **critic: critical → low**. If yours has it, point at it. If not, the evidence text itself says the agent re-probed the search crawlers.

> The scripts called this critical. The agent brought it down, and the
> evidence, the mechanism and the fix sit side by side. The fix is to state the
> policy in robots.txt. No unblocking needed.

**Optional, if time allows (10 seconds).** Prove it outside our tool, in the terminal:

```powershell
curl.exe -s -o NUL -w "%{http_code}\n" -A "GPTBot/1.1" https://www.sqlite.org/
curl.exe -s -o NUL -w "%{http_code}\n" -A "OAI-SearchBot/1.0" https://www.sqlite.org/
```

That prints 403, then 200.

### 2.7 · 1:45–1:55 · Prioritized fixes

**[DO]** Click **Roadmap**.

**[SHOW]** The three numbered lanes. **Do now** includes *No usable XML sitemap found* (medium, quick). It came first in two of three rehearsals.

> Fixes come prioritized by impact against effort. Do now: publish a sitemap,
> medium impact, a quick fix. The bigger, lower-impact work waits.

**[DO]** Optional: in **Findings**, switch **Sort** to *effort* for one second.

### 2.8 · 1:55–2:00 · Close

**[SHOW]** Overview.

> Same engine as Round 3, running live, and reproducible from our replay file.
> Thanks from PSTrio.

---

## 4. If the run differs from the rehearsals

Across three rehearsals on this harness and model:

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Critical / high | 0 / 0 | 0 / 0 | 0 / 0 |
| Crawler finding | low | low | medium |
| No XML sitemap | medium | medium | medium |
| Homepage has no H1 | medium | medium | low |
| Readiness | 94 | 96 | 90 |
| Findings | 16 | 12 | 20 |

**Narrate what your run actually shows.** Never name a severity, score or
finding that is not on screen.

- **Crawler finding at medium, or titled differently:** use the same drill-in and say "downgraded from critical".
- **No crawler finding at all:** drill into **Homepage has no H1** instead. In Findings, search `H1`, expand it, then prove it:
  ```powershell
  curl.exe -s https://www.sqlite.org/ | findstr /i /c:"<h1"
  ```
  No output means no H1.
- **The run fails or stalls:** stop and record Part 2 again from the top, in a fresh `demo` folder. Never splice takes.
- **The GUI port is busy:** the `--open` command hands the report to the GUI that is already running and opens it there. That is expected.

---

## 5. Integrity checklist (tick before uploading)

The video and `REPLAY_PSTrio.txt` must agree. A mismatch is an integrity failure.

- [ ] Site typed on camera is exactly `https://www.sqlite.org/`, the value of `TEST_SITE_URLS`.
- [ ] `claude --version` on camera matches `AGENT_HARNESS` (2.1.280).
- [ ] The model you say and the `--model` flag both read Claude Sonnet 5 / `claude-sonnet-5`, matching `LLM_MODEL`.
- [ ] The prompt pasted is REPLAY step 5, word for word.
- [ ] Nothing under `skills/` was edited. `submission.zip` SHA-256 still starts `1d5e0f3e`.
- [ ] The GUI history showed only this run.
- [ ] Part 1 is at most 3:00, Part 2 at most 2:00, total at most 5:00.
- [ ] Submit the video with `REPLAY_PSTrio.txt` alongside.

---

## 6. Known limits of the frozen engine

Changing any script now would make the demo engine differ from the Round 3
one, so these are recorded rather than fixed. If a judge asks, say so plainly.

- **The scripts alone over-call AI-crawler blocks.** They probe only a few user agents. The agent's review corrects this, which is why the demo is agent-driven.
- **Inline SVG titles leak into page titles** (`evidence_collector.py`, line 547), which can distort term-coverage findings on icon-heavy sites such as stripe.com.
- **Near-duplicate pages use up the 15-page sample**, e.g. country copies of one pricing page, or CMS fragment URLs on adobe.com.
- **A single-page issue can stay at high.** On lua.org the agent's own summary said two single-page findings were overstated, but it left them.
- **No JavaScript execution.** Script-injected content is judged as a non-rendering crawler sees it.
