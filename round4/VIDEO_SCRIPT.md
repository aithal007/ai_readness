# PSTrio · Round 4 video

## *The Case of the Missing Citation*

Five minutes, hard cap. **Part 1, the method: 3:00. Part 2, the live case: 2:00.**

The idea running through the whole video: an AI assistant ignoring a brand is
a mystery, and our marketplace is the detective. It gathers clues, weighs them,
argues with itself, and hands down a verdict with a sentence attached. In
Part 2 tests a real accusation: our scripts may flag a crawler block, then the
agent checks the evidence before deciding whether the charge stands. Show the
decision this run actually made; the live site and model can change the verdict.

How to read this file:

- **`[SCREEN]`** is what is on screen.
- **`[DO]`** is what you click or type.
- **Quoted blocks** are what you say. Around 150 spoken words make a minute.
- Every code reference was checked against `submission.zip`, the frozen Round 3 package.
- **[READ …]** means say the value visible in this run's report, never a rehearsal number.

---

## Part A · Set up, once, before any take

Do all of this in **Windows Terminal** with a **PowerShell** tab. Each step
says what to type, what you should see, and what to do if you don't.

### A1. Check the tools

```powershell
python --version
node --version
npm --version
```

**You should see** Python 3 and Node.js 20 or later. If `python` is not found,
install Python from python.org and tick "Add python.exe to PATH".

### A2. Make the demo folder with the frozen package

```powershell
New-Item -ItemType Directory -Force C:\PSTrio_demo | Out-Null
Expand-Archive -Path .\PSTrio_video_demo.zip -DestinationPath C:\PSTrio_demo -Force
cd C:\PSTrio_demo
Get-FileHash .\submission.zip -Algorithm SHA256
```

Run these commands from the folder containing `PSTrio_video_demo.zip`.
**You should see** a hash starting `1D5E0F3E4DD12A8C`. If it differs, stop:
the video must use the frozen Round 3 engine.

### A3. Check the GUI

```powershell
Test-Path .\gui\server.py
```

**You should see** `True`. The same package contains the viewer and the
unchanged Round 3 skills. A fresh extraction starts with no GUI history.

### A4. Unpack the package for Part 1 and open it in VS Code

```powershell
python -m zipfile -e submission.zip r3
code r3\brand-ai-readiness-audit
```

**You should see** VS Code open on a folder with `skills`, `tests`, `README.md`
and `ARCHITECTURE.md`. If `code` is not found, open VS Code and use
File, then Open Folder, on `C:\PSTrio_demo\r3\brand-ai-readiness-audit`.

### A5. Install the free agent harness

```powershell
npm install -g @google/gemini-cli
gemini --version
```

**You should see** a Gemini CLI version. Record that version in
`REPLAY_PSTrio.txt`. Sign-in with a personal Google account has a
[free quota](https://geminicli.com/docs/resources/quota-and-pricing/).

### A6. Sign in once

```powershell
gemini
```

Choose **Sign in with Google**, finish browser sign-in, then type `/quit`.

### A7. Rehearse Part 2 in a separate workspace

Run section C once without recording. At C1, use this setup command instead
of the default, then run C2 onward from `demo/rehearsal`:

```powershell
cd C:\PSTrio_demo
python round4/setup_gemini_demo.py --workspace demo/rehearsal
cd demo/rehearsal
$env:PYTHONUTF8="1"
```

In C5, open `demo/rehearsal/audit_out` for this practice run. Keep
`demo/gemini_run` unused until the recorded take. For another attempt, create
a fresh workspace with a new name and use that same name in the viewer command
and replay manifest.

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

**One continuous agent run.** You may cut out waiting. Keep the prompt, agent
actions, and GUI report from the same workspace; do not join two runs.

### C1 · 0:00–0:15 · The suspect, the detective, the tools

**[SCREEN]** Windows Terminal, Tab 1, in `C:\PSTrio_demo`.
**[DO]** Paste these lines one at a time and press Enter after each:

```powershell
python round4/setup_gemini_demo.py
cd demo/gemini_run
$env:PYTHONUTF8="1"
gemini --version
```

**You should see** the verified `submission.zip` hash, eight skills copied,
then your Gemini CLI version. If setup says the workspace exists, choose a new
workspace name for a new take and update the paths in C5 and the replay file.

> These are our Round 3 skills, copied unchanged out of submission.zip into
> the folder where Gemini finds skills. No demo mode. The detective is a live
> Gemini agent; its version and model are recorded in the replay file.

### C2 · 0:15–0:25 · Open the case

**[DO]** Start the agent:

```powershell
gemini
```

**You should see** Gemini CLI. Trust this fresh workspace if asked. Type
`/skills list` and confirm `audit-orchestrator` appears.

**[DO]** Paste this prompt exactly, **pause one second so `https://www.sqlite.org/` is readable**, then press Enter:

```text
Activate the audit-orchestrator skill and audit https://www.sqlite.org/ for AI discoverability and on-site engagement. Use today's real date and sample at most 5 pages. On Windows use python for the skill scripts if python3 is unavailable. Write every generated file under ./audit_out/, ending with audit_out/audit_report.json and audit_out/audit_report.md. Perform the skill's off-site web-search corroboration and homepage orientation checks, run the evidence critic, and review surviving findings before finalizing. Leave .gemini/skills unchanged. Summarize the critical and high findings and the remediation roadmap.
```

> Today's case: sqlite.org. A site our audit was never tuned on.

### C3 · 0:25–0:55 · The investigation (trim the waits)

The run time varies with the site and model. Keep each of these moments on
screen for a beat, and cut the gaps between them.

| On screen | Say |
|---|---|
| `activate_skill` on `audit-orchestrator` | "It calls our entrypoint skill." |
| A shell call running `run_audit.py` | "One crawl, one evidence file, six analyzers." |
| Web search calls | "It checks the brand's story against independent sources." |
| `critique_findings.py`, then `finalize_report.py` | "The critic cross-examines. Then the verdict is written." |

Approve the skill and Python script calls when Gemini asks. If the run stops
without `audit_out/audit_report.json`, fix the error before recording again.

### C4 · 0:55–1:10 · The twist

**[SCREEN]** The agent's final message in the terminal.

> Here's the twist: our own checks can accuse a site of blocking AI crawlers.
> The agent has to test that charge against the evidence. This run found
> **[READ the actual outcome, including any critical or high count]**.

**[DO]** Type `/quit` to leave Gemini. Check that
`audit_out/audit_report.json` exists before opening the GUI.

### C5 · 1:10–1:18 · Open the case file

**[DO]** Press **Ctrl+Shift+T** for a new terminal tab, then:

```powershell
cd C:\PSTrio_demo
python gui\server.py --engine-only --open demo\gemini_run\audit_out
```

**You should see** the browser open on the imported report. The GUI is only
viewing Gemini's output; `--engine-only` hides its separate Claude launcher.
The score gauge shows the value from this run.

> Same run, now as a case file. The note under the title shows the folder it
> came from.

### C6 · 1:18–1:45 · Exhibit A

**[DO]** Click the **Evidence** tab. The AI crawler table is at the top.

**[SCREEN]** Read the actual crawler rows and responses. If the run did not
observe a crawler block, choose another consequential finding from the report.

> Exhibit A: **[READ the observed response and crawler type, or name the other
> finding you chose]**. **[IF ABOUT CRAWLERS: explain whether this crawler
> serves search or training, using this run's evidence.]**

**[DO]** Click **Findings**, search for the finding you just showed, and open it.

**[SCREEN]** Show the evidence, *Why it matters*, and *Suggested fix*. If this
run shows a critic downgrade, point at it.

> Here is the verdict: **[READ the finding and severity]**. The evidence says
> **[PARAPHRASE what this run observed]**. The proposed fix is **[READ the
> suggested action]**.

**Optional, 10 seconds, if showing a crawler finding.** Probe it outside our
tool. **Ctrl+Shift+T** for a third tab:

```powershell
curl.exe -s -o NUL -w "%{http_code}\n" -A "GPTBot/1.1" https://www.sqlite.org/
curl.exe -s -o NUL -w "%{http_code}\n" -A "OAI-SearchBot/1.0" https://www.sqlite.org/
```

**Read the responses you actually get.** They can change between runs. Type
`curl.exe`, not `curl`: in PowerShell plain `curl` is a different command.

### C7 · 1:45–1:55 · The sentence

**[DO]** Click the **Roadmap** tab.

**[SCREEN]** The roadmap's *Do now*, *Next* and *Later* priorities. Some
buckets can be empty, depending on the report.

> And the sentence, ranked by impact against effort. **[READ the first action
> in this run's roadmap, or say that the report found no urgent action.]**

### C8 · 1:55–2:00 · Case closed

**[DO]** Click the **Overview** tab.

> Same engine as Round 3, guided by a live agent, replayable from our manifest.
> More real cases are open on our site. Case closed.

**After recording:** press **Ctrl+C** in the GUI tab to stop the server.

---

## Part D · If your run differs from the rehearsals

Older Claude rehearsals scored 90–96 with no critical or high findings. Later
live runs contradicted those figures. Gemini can also reach a different
conclusion. **Say only what is on your screen.** Never name a score, severity,
HTTP response, or finding that this run does not show.

- **The crawler finding is critical or high:** show the evidence and say the
  agent kept the charge. Do not claim it downgraded the finding.
- **The crawler finding is low or medium:** show why the report lowered it.
- **There is no crawler finding:** use a supported finding from this report.
  If it flags *Homepage has no H1*, search `H1`, open it, and prove it:
  ```powershell
  curl.exe -s https://www.sqlite.org/ | findstr /i /c:"<h1"
  ```
  On a successful page response, no output supports the missing-H1 finding.
- **The run fails or stalls:** create a fresh workspace and record Part C again
  from the top, using that workspace name throughout.
- **Port 8765 is busy:** the `--open` command hands the report to the GUI that is already running. That's expected.

---

## Part E · Before you upload

The video and `REPLAY_PSTrio.txt` must agree. A mismatch is an integrity failure.

- [ ] The URL typed on camera matches `TEST_SITE_URLS` in the manifest.
- [ ] `gemini --version` and the displayed model match the replay manifest.
- [ ] The prompt is pasted word for word from C2.
- [ ] Nothing under `skills/` was edited, and the zip hash starts `1D5E0F3E`.
- [ ] The report and GUI come from the same agent run and workspace.
- [ ] Part B is at most 3:00, Part C at most 2:00, and the total at most 5:00.
- [ ] Upload the video with `REPLAY_PSTrio.txt` alongside it.

---

## Part F · Known limits of the frozen engine

Changing any script now would make the demo engine differ from the Round 3
one, so these are recorded, not fixed. If a judge asks, say so plainly.

- **The scripts can over-call AI-crawler blocks.** They probe only a few user
  agents. The agent must review the evidence, but a downgrade is not guaranteed.
- **Inline SVG titles leak into page titles** (`evidence_collector.py`, line 547). This can distort term-coverage findings on icon-heavy sites such as stripe.com.
- **Near-duplicate pages use up the page sample**, such as country copies of one pricing page, or CMS fragment URLs on adobe.com.
- **A single-page issue can stay at high.** On lua.org the agent's own summary called two single-page findings overstated, but left them.
- **No JavaScript execution.** Content injected by script is judged as a non-rendering crawler sees it.
