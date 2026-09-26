# Agent-driven video demo with Gemini CLI

For the final recording, follow [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) and share
its matching [REPLAY_PSTrio.txt](REPLAY_PSTrio.txt). This page is the short
setup guide.

This version keeps the original agent idea. Gemini activates the submitted
`audit-orchestrator` skill, runs its scripts, performs the two judgment checks,
and writes a report. The GUI then displays **that same agent run**. The
scripted Engine button is not used for the recorded audit.

Gemini CLI offers free use with a personal Google account, subject to its
[current quotas](https://geminicli.com/docs/resources/quota-and-pricing/).
The recording computer needs Python 3, Node.js 20+, internet access, and a
personal Google account. See the official
[install](https://geminicli.com/docs/get-started/installation/) and
[sign-in](https://geminicli.com/docs/get-started/authentication/) instructions.

## Prepare on your friend's Windows computer

1. Extract `PSTrio_gemini_video_demo.zip`. Open PowerShell in the extracted
   folder and check the tools:

   ```powershell
   python --version
   node --version
   npm --version
   ```

2. Install Gemini CLI and sign in once:

   ```powershell
   npm install -g @google/gemini-cli
   gemini
   ```

   Choose **Sign in with Google** using a personal account. Exit the first
   session after sign-in. A company or school account may need a Google Cloud
   project. Do not put credentials in this project folder.

3. From the extracted folder, create a fresh workspace with the verified
   Round 3 skills:

   ```powershell
   python round4/setup_gemini_demo.py
   cd demo/gemini_run
   gemini
   ```

   The setup command checks the frozen `submission.zip` hash and copies all
   eight skills into `.gemini/skills/` without changing them. Trust this
   workspace when Gemini asks. Run `/skills list` and check that
   `audit-orchestrator` appears. If it does not, use `/skills reload` or
   restart Gemini after trusting the folder.

4. Paste this prompt, replacing the URL only if the video uses another site:

   ```text
   Activate the audit-orchestrator skill and audit https://www.adobe.com/ for AI discoverability and on-site engagement. Use today's real date and sample at most 5 pages. On Windows use python for the skill scripts if python3 is unavailable. Write every generated file under ./audit_out/, ending with audit_out/audit_report.json and audit_out/audit_report.md. Perform the skill's off-site web-search corroboration and homepage orientation checks, run the evidence critic, and review surviving findings before finalizing. Leave .gemini/skills unchanged. Summarize the critical and high findings and the remediation roadmap.
   ```

   Approve activation of `audit-orchestrator` and the Python script calls.
   The terminal should show the skill, script execution, web search, critic,
   and final report. This is the agent action to capture on video.

5. Confirm the report exists in another PowerShell tab from the extracted
   folder:

   ```powershell
   Test-Path demo/gemini_run/audit_out/audit_report.json
   ```

   It must print `True`. If Gemini stopped early, read its error and rerun in
   a **new** workspace, for example
   `python round4/setup_gemini_demo.py --workspace demo/gemini_run_2`.

6. Open the same report in the GUI from the extracted folder:

   ```powershell
   python gui/server.py --engine-only --open demo/gemini_run/audit_out
   ```

   The page says **imported** because the GUI is viewing Gemini's files; the
   agent work happened in the terminal. Show **Overview**, one **Finding**
   with its evidence, **Evidence**, and **Roadmap**. Read scores and severities
   from the actual report on screen.

For the recording, keep the prompt, agent steps, and report from one run.
Waiting time can be cut. Do not claim the agent downgraded a crawler finding
unless this run's report actually shows that decision. If the report is
missing, the run did not complete.

Suggested edit: show the website and prompt for 15 seconds; the skill
activation, Python crawl, web search, critic, and final report for about 45
seconds after trimming waits; then spend about a minute on the GUI's Overview,
one Finding and its Evidence, and Roadmap. Say the actual numbers shown in the
report. Keep the terminal result and GUI report from the same workspace.

The original agent and the scripted engine use the same frozen skill files.
The model's judgment can change results between runs, so there is no fixed
expected score.
