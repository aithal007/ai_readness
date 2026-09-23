# PSTrio · Round 4 video

## *The Case of the Missing Citation*

Five minutes, hard cap. **Part 1, the method: 3:00. Part 2, the live case: 2:00.**

The idea running through the whole video: an AI assistant ignoring a brand is
a mystery, and our marketplace is the detective. It gathers clues, weighs them,
argues with itself, and hands down a verdict with a sentence attached. In
Part 2 the mystery has a real twist: our own scripts accuse sqlite.org of
blocking AI crawlers, the agent investigates, and the evidence acquits it.

How to read this file:

- **`[SCREEN]`** is what is on screen.
- **`[DO]`** is what you click or type.
- **Quoted blocks** are what you say. Around 150 spoken words make a minute.
- Every code reference was checked against `submission.zip`, the frozen Round 3 package.

---

## Part A · Set up, once, before any take

Do all of this in **Windows Terminal** with a **PowerShell** tab. Each step
says what to type, what you should see, and what to do if you don't.

### A1. Check the tools

```powershell
python --version
git --version
```

**You should see** `Python 3.x` and `git version 2.x`. If `python` is not
found, install Python from python.org and tick "Add python.exe to PATH".

### A2. Make the demo folder with the frozen package

```powershell
New-Item -ItemType Directory -Force C:\PSTrio_demo | Out-Null
Copy-Item C:\Users\Parikshith\Desktop\adobe\submission.zip C:\PSTrio_demo\
cd C:\PSTrio_demo
Get-FileHash .\submission.zip -Algorithm SHA256
```

**You should see** a hash starting `1D5E0F3E4DD12A8C`. If it differs, you
copied the wrong zip. Stop and fix that first: the video must use this exact file.

### A3. Get the GUI

```powershell
git clone https://github.com/aithal007/ai_readness
```

**You should see** `Cloning into 'ai_readness'...` and then `done`. A fresh
clone has an empty GUI history, so the only report in the GUI will be the one
you record.

### A4. Unpack the package for Part 1 and open it in VS Code

```powershell
python -m zipfile -e submission.zip r3
code r3\brand-ai-readiness-audit
```

**You should see** VS Code open on a folder with `skills`, `tests`, `README.md`
and `ARCHITECTURE.md`. If `code` is not found, open VS Code and use
File, then Open Folder, on `C:\PSTrio_demo\r3\brand-ai-readiness-audit`.

### A5. Make `claude` a command

Claude Code lives inside the VS Code extension. This makes it callable by name:

```powershell
Set-Alias claude "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-2.1.280-win32-x64\resources\native-binary\claude.exe"
claude --version
```

**You should see** `2.1.280 (Claude Code)`.

- **"The term … is not recognized":** the extension has updated and the folder name changed. Run
  `ls $env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*`, then use the newest folder name.
  **Also change `AGENT_HARNESS` in `REPLAY_PSTrio.txt` to the new version.**
- **To keep the alias in every new tab**, run this once:
  ```powershell
  Add-Content $PROFILE 'Set-Alias claude "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-2.1.280-win32-x64\resources\native-binary\claude.exe"'
  ```

### A6. Sign in once

```powershell
claude
```

If it asks you to log in, follow the prompts. If it asks whether you trust the
folder, choose **Yes**. Then type `/exit` and press Enter.

### A7. Rehearse Part 2 fully, then reset

Run section C end to end once, without recording. Then reset so the real take
starts clean:

```powershell
cd C:\PSTrio_demo
Remove-Item -Recurse -Force demo
Remove-Item -Recurse -Force ai_readness\gui\runs -ErrorAction SilentlyContinue
```

Do the same reset after any failed take.

### A8. Arrange the screen

- **Recorder:** OBS Studio with a Display Capture source at 1920×1080. You can
  cut the dead time afterwards in Clipchamp or any editor. Turn on Focus Assist
  so no notifications appear.
- **VS Code:** font size 16 or more, minimap off. Open these six tabs, left to right:
  1. `skills/audit-orchestrator/SKILL.md`
  2. `skills/audit-orchestrator/references/evidence-base.md`
  3. `skills/crawl-render-audit/scripts/evidence_collector.py`
  4. `skills/crawl-render-audit/scripts/analyze_crawl_render.py`
  5. `skills/evidence-critic/scripts/critique_findings.py`
  6. `skills/audit-orchestrator/scripts/finalize_report.py`

  Jump to a line with **Ctrl+G**, type the number, and press Enter.
- **Windows Terminal:** font size 16 or more. Tab 1 in `C:\PSTrio_demo`.
- **Browser:** one tab on https://aithal007.github.io/ai_readness/ for the cold open.

### Who speaks

One voice works. For three voices, split at the chapter breaks: **P1** does
the cold open and chapter I, **P2** does chapter II, and **P3** does chapter III
and all of Part 2.

---

## Part B · The method (target 2:55)

### Cold open · 0:00–0:15

**[SCREEN]** The browser on https://aithal007.github.io/ai_readness/. The big headline, *Why don't AI assistants cite this brand?*, fills the frame.

> Ask an AI assistant about a website. Sometimes it quotes it. Sometimes it
> acts as if the site doesn't exist. We're PSTrio, and we built the detective
> that finds out why.

### Chapter I · The clues · 0:15–1:10

**[SCREEN]** VS Code, `SKILL.md`. **Ctrl+G 39**. Lines 39 to 44 show the six-row table.

> A brand only gets cited if six things hold, in order. Reachable,
> identifiable, quotable, answerable, trusted, converting. One skill for each,
> so the first failure explains everything after it.

**[DO]** `evidence-base.md`, **Ctrl+G 15**. Let the Tier 1 table fill the screen.

> Every clue we look for comes from a measurement. The core is a controlled
> study of 252,000 head-to-head trials across six AI models. Topic coverage,
> an explicit price, recency and specifications decide who gets cited.

**[DO]** **Ctrl+G 34**.

> Some clues are counter-intuitive. An old date scored worse than no date at
> all. So we never say strip your dates. We say refresh them.

**[DO]** **Ctrl+G 57**.

> A fact buried mid-page was used less often than no page at all. So we audit
> where facts sit, not just whether they exist.

**[DO]** **Ctrl+G 118**.

> And we wrote down the myths. Schema markup doesn't cause citations, and
> llms.txt has no measured effect. Our audit won't sell either as a cure.

### Chapter II · Weighing the evidence · 1:10–2:10

**[SCREEN]** `evidence_collector.py`, **Ctrl+G 50**.

> A good detective weighs motive, not appearance. Every AI crawler is classed
> by what blocking it costs. Blocking a search crawler costs citations.
> Blocking a training crawler costs nothing, so it's never a crime.

**[DO]** `analyze_crawl_render.py`, **Ctrl+G 143**.

> A block only counts as proven on a 401 or a 403. A rate limit or a timeout
> is circumstantial, because our own probe might have caused it.

**[DO]** `critique_findings.py`, **Ctrl+G 88**, then **Ctrl+G 156**.

> Then a critic cross-examines every finding. No anchor, no count, no URL:
> thrown out. And while a gatekeeper is failing, cosmetic findings are capped,
> because formatting can't save a page that fails a gatekeeper.

**[DO]** `finalize_report.py`, **Ctrl+G 34**, then **Ctrl+G 211**.

> "We couldn't tell" is never scored as "guilty", and a site we can't read gets
> no score at all. Confidence is computed from the evidence, never typed in.

### Chapter III · The verdict and the sentence · 2:10–2:55

**[SCREEN]** `analyze_crawl_render.py`, **Ctrl+G 26**, the `finding()` helper.

> Every verdict states its reason, the mechanism, right next to the fix.

**[DO]** `critique_findings.py`, **Ctrl+G 41**.

> Fixes measured to backfire are struck out automatically: keyword stuffing,
> hidden text, instructions aimed at the model.

**[DO]** `finalize_report.py`, **Ctrl+G 157**, then **Ctrl+G 236**.

> And the sentence is prioritized: do now, next and later, weighed by impact
> against effort. Enough theory. Let's open a real case.

**[CUT]** to Windows Terminal.

---

## Part C · The live case: sqlite.org (target 1:55 after trimming)

**One continuous take.** You may cut out waiting. You may not cut between
typing the URL and the findings appearing, and you may not join two takes.

### C1 · 0:00–0:15 · The suspect, the detective, the tools

**[SCREEN]** Windows Terminal, Tab 1, in `C:\PSTrio_demo`.
**[DO]** Paste these lines one at a time and press Enter after each:

```powershell
python -m zipfile -e submission.zip r3
python -c "import shutil, os; shutil.copytree('r3/brand-ai-readiness-audit/skills', 'demo/.claude/skills'); os.makedirs('demo/audit_out')"
cd demo
$env:PYTHONUTF8="1"
claude --version
```

**You should see** no output from the first four lines, then `2.1.280 (Claude Code)`.
If the second line says `FileExistsError`, you skipped the reset in A7: do it and start the take again.

> These are our Round 3 skills, copied unchanged out of submission.zip into
> the folder where Claude Code finds skills. No demo mode. The detective is
> Claude Sonnet 5, running in Claude Code 2.1.280.

### C2 · 0:15–0:25 · Open the case

**[DO]** Start the agent:

```powershell
claude --model claude-sonnet-5 --allowedTools Skill Bash Read Write Glob Grep WebSearch
```

**You should see** the Claude Code welcome box. If it asks whether you trust
the folder, choose **Yes**.

**[DO]** Paste this prompt exactly, **pause one second so `https://www.sqlite.org/` is readable**, then press Enter:

```text
Use the audit-orchestrator skill to audit https://www.sqlite.org/ for AI discoverability and on-site engagement. Use today's real date. Write every output file into ./audit_out/, ending with audit_out/audit_report.json and audit_out/audit_report.md. Then summarise the critical and high findings and the remediation roadmap.
```

> Today's case: sqlite.org. A site our audit was never tuned on.

### C3 · 0:25–0:55 · The investigation (trim the waits)

The whole run takes 2 to 7 minutes. Keep each of these moments on screen for
a beat, and cut the gaps between them.

| On screen | Say |
|---|---|
| `Skill(audit-orchestrator)` | "It calls our entrypoint skill." |
| A Bash call running `run_audit.py` | "One crawl, one evidence file, six analyzers." |
| `WebSearch` calls | "It checks the brand's story against independent sources." |
| `critique_findings.py`, then `finalize_report.py` | "The critic cross-examines. Then the verdict is written." |

If a permission prompt appears, press Enter on **Yes**. That's fine on camera.

### C4 · 0:55–1:10 · The twist

**[SCREEN]** The agent's final message in the terminal.

> Here's the twist. Our scripts accused sqlite.org of blocking AI crawlers:
> a critical finding. The agent didn't take that on trust. It probed further,
> and it overruled our own scripts. Zero critical, zero high.

**[DO]** Type `/exit` and press Enter to leave Claude Code.

### C5 · 1:10–1:18 · Open the case file

**[DO]** Press **Ctrl+Shift+T** for a new terminal tab, then:

```powershell
cd C:\PSTrio_demo
python ai_readness\gui\server.py --open demo\audit_out
```

**You should see** five lines: `opened : …\demo\audit_out`, `engine : submission.zip (verified)`,
`sha256 : 1d5e0f3e…`, `agent : Claude Code 2.1.280`, and `open : http://127.0.0.1:8765/#/run/…`. The browser
opens on the report, and the readiness number counts up.

> Same run, now as a case file. The note under the title shows the folder it
> came from.

### C6 · 1:18–1:45 · Exhibit A

**[DO]** Click **EVIDENCE**. The AI crawler table is at the top.

**[SCREEN]** GPTBot and ClaudeBot rows have a red edge, **403** in *Live probe*, and
*None (training only)* under *Cost of blocking*. The PerplexityBot row shows **200**.

> Exhibit A. GPTBot and ClaudeBot get a 403. They're training crawlers: blocking
> them costs no citations. PerplexityBot, a search crawler, gets through.

**[DO]** Click **FINDINGS**, type `crawler` in the search box, and click the finding to open it.

**[SCREEN]** Evidence and *Why it matters* on the left, *What to do* on the right. If the
row shows **critic: critical → low**, point at it.

> So the charge came down from critical, with the evidence, the reasoning and
> the fix side by side. The fix: state the policy in robots.txt. Nothing to unblock.

**Optional, 10 seconds.** Prove it outside our tool. **Ctrl+Shift+T** for a third tab:

```powershell
curl.exe -s -o NUL -w "%{http_code}\n" -A "GPTBot/1.1" https://www.sqlite.org/
curl.exe -s -o NUL -w "%{http_code}\n" -A "OAI-SearchBot/1.0" https://www.sqlite.org/
```

**You should see** `403`, then `200`. Type `curl.exe`, not `curl`: in PowerShell
plain `curl` is a different command.

### C7 · 1:45–1:55 · The sentence

**[DO]** Click **ROADMAP**.

**[SCREEN]** Three columns: *i. Do now*, *ii. Next*, *iii. Later*. *Do now* includes *No usable XML sitemap found*.

> And the sentence, ranked by impact against effort. Do now: publish a sitemap.
> Medium impact, quick fix. The big, low-value work waits.

### C8 · 1:55–2:00 · Case closed

**[DO]** Click **OVERVIEW**.

> Same engine as Round 3, running live, replayable from our manifest. More
> real cases are open on our site. Case closed.

**After recording:** press **Ctrl+C** in the GUI tab to stop the server.

---

## Part D · If your run differs from the rehearsals

Three rehearsals on this harness and model produced:

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Critical / high | 0 / 0 | 0 / 0 | 0 / 0 |
| Crawler finding | low | low | medium |
| Critic chip shown | yes | yes | no |
| No XML sitemap | medium | medium | medium |
| Homepage has no H1 | medium | medium | low |
| Readiness | 94 | 96 | 90 |

**Say only what is on your screen.** Never name a score, severity or finding
that your run does not show.

- **The crawler finding is medium, or has no critic chip:** say "the charge came down from critical" and point at the evidence text, which says the agent re-probed.
- **There is no crawler finding:** use *Homepage has no H1* instead. Search `H1`, open it, and prove it:
  ```powershell
  curl.exe -s https://www.sqlite.org/ | findstr /i /c:"<h1"
  ```
  No output means no H1.
- **The run fails or stalls:** do the reset in A7 and record Part C again from the top.
- **Port 8765 is busy:** the `--open` command hands the report to the GUI that is already running. That's expected.

---

## Part E · Before you upload

The video and `REPLAY_PSTrio.txt` must agree. A mismatch is an integrity failure.

- [ ] The URL typed on camera is exactly `https://www.sqlite.org/`.
- [ ] `claude --version` on camera matches `AGENT_HARNESS` in the manifest.
- [ ] You say Claude Sonnet 5, and the command uses `--model claude-sonnet-5`.
- [ ] The prompt is pasted word for word from C2.
- [ ] Nothing under `skills/` was edited, and the zip hash starts `1D5E0F3E`.
- [ ] The GUI history showed only this run.
- [ ] Part B is at most 3:00, Part C at most 2:00, and the total at most 5:00.
- [ ] Upload the video with `REPLAY_PSTrio.txt` alongside it.

---

## Part F · Known limits of the frozen engine

Changing any script now would make the demo engine differ from the Round 3
one, so these are recorded, not fixed. If a judge asks, say so plainly.

- **The scripts alone over-call AI-crawler blocks.** They probe only a few user agents. The agent's review corrects this, which is why the demo is agent-driven.
- **Inline SVG titles leak into page titles** (`evidence_collector.py`, line 547). This can distort term-coverage findings on icon-heavy sites such as stripe.com.
- **Near-duplicate pages use up the 15-page sample**, such as country copies of one pricing page, or CMS fragment URLs on adobe.com.
- **A single-page issue can stay at high.** On lua.org the agent's own summary called two single-page findings overstated, but left them.
- **No JavaScript execution.** Content injected by script is judged as a non-rendering crawler sees it.
