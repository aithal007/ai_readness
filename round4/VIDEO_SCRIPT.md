# PSTrio · Round 4 video script

## *The Case of the Missing Citation*

**Target: 4:30–4:50; hard stop at 5:00.** One live website, one Gemini agent
run, one report. The agent uses the unchanged Round 3 skills. The GUI displays
the files that run wrote; its Engine button is not part of this recording.

This script uses `https://www.adobe.com/`. If the team chooses another site,
change the URL in the prompt, the browser tab, and `REPLAY_PSTrio.txt` together.
Read every score, finding, severity, and HTTP response from the recorded run.

### Legend

- **[SCREEN]** what appears in the recording.
- **[DO]** an action for the presenter.
- **>** spoken words. Bracketed **[READ …]** cues mean use the actual report.
- Waiting time may be cut. Keep the prompt, agent actions, and GUI report from
  the same take and workspace.

---

## Prepare before recording

1. On the recording computer, install Python 3 and Node.js 20+, then install
   [Gemini CLI](https://geminicli.com/docs/get-started/installation/):

   ```powershell
   npm install -g @google/gemini-cli
   gemini
   ```

   Sign in with a personal Google account. Free usage is subject to Google's
   [current quota](https://geminicli.com/docs/resources/quota-and-pricing/).
   Do the browser sign-in off camera. Confirm `gemini --version` works.

2. Extract `PSTrio_video_demo.zip` and open PowerShell in that folder.
   Check the frozen package and make a **fresh** workspace:

   ```powershell
   Get-FileHash .\submission.zip -Algorithm SHA256
   python round4/setup_gemini_demo.py
   ```

   The expected hash is
   `1D5E0F3E4DD12A8C12E205B4723124B4D441CDBF3F76605A2BEFDE9114EC33B1`.
   The setup command checks it and copies eight unchanged skills to
   `demo\gemini_run\.gemini\skills`.

3. Rehearse the complete flow once in a *different* fresh workspace, for
   example `python round4/setup_gemini_demo.py --workspace demo/rehearsal`.
   Check that Gemini finds `audit-orchestrator`, invokes Python and web search,
   and writes both report files. Review the actual findings so the presenter
   knows which row to open. Leave `demo\gemini_run` unused until the take.

4. Arrange three windows: the target website in a browser, PowerShell for
   Gemini, and a second PowerShell tab for opening the report in the GUI.
   Set the recording resolution and font size so commands and evidence URLs
   remain readable.

### Prompt to paste in the recording

```text
Activate the audit-orchestrator skill and audit https://www.adobe.com/ for AI discoverability and on-site engagement. Use today's real date and sample at most 5 pages. On Windows use python for the skill scripts if python3 is unavailable. Write every generated file under ./audit_out/, ending with audit_out/audit_report.json and audit_out/audit_report.md. Perform the skill's off-site web-search corroboration and homepage orientation checks, run the evidence critic, and review surviving findings before finalizing. Leave .gemini/skills unchanged. Summarize the critical and high findings and the remediation roadmap.
```

---

## Part 1 · The mystery and the method (0:00–1:30)

### 0:00–0:20 · Cold open

**[SCREEN]** The chosen website's homepage, then its URL in the address bar.

> A website can be online, polished, and still hard for an AI assistant to
> find or cite. Is a crawler blocked? Is the answer buried? Is the evidence
> stale? Let's investigate one real site instead of guessing.

### 0:20–0:50 · Meet the team of skills

**[SCREEN]** `demo\gemini_run\.gemini\skills` in File Explorer or VS Code;
show the eight skill folders, then open `audit-orchestrator/SKILL.md` at its
six-question table.

> This is our agent skill marketplace. Six specialists check reachability,
> identity, quotable content, answerability, freshness, and on-site
> engagement. One orchestrator gives them a shared crawl, and an evidence
> critic challenges the findings before a report is written.

### 0:50–1:15 · Why an agent matters

**[SCREEN]** The orchestrator procedure, especially its two judgment checks.

> Scripts can collect pages and apply repeatable checks. The agent adds the
> work that needs judgment: searching for independent corroboration, reading
> how the homepage explains itself, and reviewing what the critic kept.

### 1:15–1:30 · Integrity

**[SCREEN]** The setup output with eight skills and the verified zip hash.

> These skills came from our frozen Round 3 package. We have not rewritten
> the engine for this demo. Now let's give the case to a free agent harness.

---

## Part 2 · One live investigation (1:30–4:40)

### 1:30–1:55 · Open the case

**[DO]** In PowerShell from the extracted folder:

```powershell
cd demo/gemini_run
gemini
```

**[DO]** If prompted, trust this fresh workspace. Type `/skills list` and
briefly show `audit-orchestrator`. Paste the prompt above. Approve the skill
activation and Python script calls when Gemini asks.

> The site is Adobe. Gemini is activating our orchestrator skill; the audit
> procedure and scripts are the same ones another capable agent could use.

### 1:55–2:35 · Follow the evidence

**[SCREEN]** Keep a short clip of each moment that actually appears: skill
activation, `run_audit.py`, web search, `critique_findings.py`, and
`finalize_report.py`. Cut only the waits between them.

> The crawler gathers a small page sample once, then all six checks work
> from that same evidence. Gemini searches beyond the site for independent
> context. The critic tests the findings, and the agent reviews the result
> before the report is finalized.

If any step fails, stop the take and fix the error. A terminal summary without
`audit_out/audit_report.json` is not a completed audit.

### 2:35–2:50 · The verdict arrives

**[SCREEN]** Gemini's final response. In a second PowerShell tab, return to
the extracted folder and confirm the file:

```powershell
Test-Path demo/gemini_run/audit_out/audit_report.json
```

It must print `True`.

> We have a report written by this run. Let's inspect the evidence behind
> the verdict, rather than relying on the agent's summary alone.

### 2:50–3:20 · Open the same case file

**[DO]** From the extracted folder:

```powershell
python gui/server.py --engine-only --open demo/gemini_run/audit_out
```

**[SCREEN]** The GUI opens on the imported report. The path banner identifies
the output folder. The GUI says *imported* because Gemini created the files
in the terminal; this command only displays them.

> This viewer opened the JSON from the same Gemini run. The readiness number
> is our audit's prioritization score, not a universal grade. This run shows
> **[READ the actual score, critical count, and high count]**.

### 3:20–4:10 · One finding, one proof, one fix

**[DO]** Open **Findings**. Pick one consequential finding from this run.
Open it, point at its URL and evidence, then its suggested action. Open
**Evidence** if it helps show the underlying crawl record.

> Here is **[READ the finding title and severity]**. The report names the
> affected page and what this run observed. That matters because
> **[PARAPHRASE the report's mechanism]**. The proposed fix is
> **[READ or paraphrase its suggested action]**.

If the report has no critical or high issue, choose a supported medium or low
finding and say so. If it suppressed or downgraded a crawler claim, show that
decision; otherwise do not claim a downgrade.

### 4:10–4:40 · The roadmap and close

**[DO]** Open **Roadmap**, then return to **Overview** for the closing frame.

> The roadmap turns evidence into an order of work: what to do now, what can
> wait, and why. This was one live site, a bounded page sample, eight
> unchanged skills, and an agent that had to show its work. The report and
> evidence are saved so anyone can replay the case.

---

## Final check before sharing the video

- The website shown, prompt URL, and `REPLAY_PSTrio.txt` name the same site.
- The recording shows Gemini activating `audit-orchestrator` and producing
  `audit_report.json` in the same workspace opened by the GUI.
- Every spoken score and finding matches the report on screen.
- The report is described as a five-page sample and the score as this audit's
  own rubric. Agent-only steps are claimed only when Gemini performed them.
- The video stays under five minutes after trimming waits, and the matching
  `REPLAY_PSTrio.txt` is shared with it.
