# One-website video demo (no Claude Code)

Use this path when the goal is to record a working audit of one website. It
uses the frozen `submission.zip` through the local GUI. Python 3 and internet
access are required; no model login or API key is needed.

## Before recording

1. Copy this project or extract `PSTrio_video_demo.zip` onto the recording
   computer. Keep `submission.zip`, `gui/`, and `start_video_demo.cmd` together.
2. Double-click `start_video_demo.cmd`. Or open PowerShell in that folder,
   check Python, and start the GUI manually:

   ```powershell
   python --version
   python gui/server.py --engine-only
   ```

   The terminal should say `engine : submission.zip (verified)` and open
   `http://127.0.0.1:8765/`. Leave the terminal running.
3. Rehearse once with `www.adobe.com` (or the one website you plan to show).
   In **New audit**, enter the domain, select **5 pages**, and click **Run
   audit**. Engine is the only mode shown. Wait for the report. A site can take
   more than a minute to respond; Adobe completed in a local 3-page check on
   2026-09-26.
4. Read the report you will show. Scores and findings can change when the
   website changes. Confirm that `audit_report.json` appears in the run's
   downloads before recording any claims.

## Recording outline (about two minutes on screen)

1. **Intro (10 seconds):** Show the target website in one browser tab. Say:
   "We're auditing this website for AI discoverability and on-site engagement."
2. **Live run (20 seconds plus waiting):** In the local GUI, enter the same
   domain, select **5 pages**, and click **Run audit**. Show the collection,
   six analyzers, evidence critic, and report stages. Waiting time can be cut
   from the video, while preserving the start and the completed report from
   the same run.
3. **Result (60 seconds):** Show **Overview** for the score and counts,
   **Findings** for one issue and its suggested action, **Evidence** for the
   supporting crawl data, then **Roadmap** for the order of fixes. Read the
   numbers and severity from this run's screen.
4. **Close (10 seconds):** Say: "This is the scripted engine from our frozen
   package. It sampled the pages shown here and produced a report with the
   evidence behind each finding." Download the JSON or Markdown report if
   you want to show the file.

This demo does not include the agent's off-site corroboration, homepage
judgment, or manual review. Describe the results as **engine-only**. If the
recording rules specifically require an agent-driven audit, use an authorized
agent harness and the skill instructions instead of calling this agent-reviewed.

## If something fails

- **`python` not found:** install Python 3 and reopen PowerShell.
- **`submission.zip` missing or unverified:** get the exact repository package;
  the expected SHA-256 starts `1d5e0f3e4dd12a8c`.
- **Website cannot be reached:** check internet access and try the same URL in
  a browser. A failed run is not a completed audit.
- **Port 8765 in use:** stop the earlier GUI process or use
  `python gui/server.py --engine-only --port 8766`.

Press **Ctrl+C** in PowerShell to stop the GUI after recording.
