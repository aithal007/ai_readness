# Round 4 video runbook

Everything here was rehearsed against the frozen Round 3 package, `submission.zip`
(SHA-256 `1d5e0f3e…33b1`). Word-for-word narration is in `NARRATION_SCRIPT.md`.

## 1. Integrity gates: what must match

The video and `REPLAY_<team>.txt` must agree on every row. A mismatch is an
integrity failure, so check this table last, after the video is cut.

| Item | Value in REPLAY | How the video shows it |
|---|---|---|
| Site URL | `https://www.sqlite.org/` | typed on camera inside the prompt |
| Model | Claude Sonnet 5, `claude-sonnet-5` | Claude Code's startup banner, and you say it |
| Harness | Claude Code v2.1.280 | run `claude --version` on camera |
| Engine | `submission.zip`, unchanged | show the install steps, or `setup_demo.py --verify-only` |
| Prompt | REPLAY step 5, verbatim | typed or pasted on camera |

**Claude Code auto-updates.** It went from 2.1.278 to 2.1.280 during our rehearsals.
Run `claude --version` just before recording. If it prints anything other than
2.1.280, change `AGENT_HARNESS` in REPLAY to match. Do not leave them disagreeing.

**Rename the manifest** to `REPLAY_<YourTeamName>.txt` before submitting.

## 2. One-time setup on this Windows machine

The `claude` command is not on PATH here. The binary ships inside the VS Code
extension. In PowerShell, alias it for the session:

```powershell
Set-Alias claude "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-2.1.280-win32-x64\resources\native-binary\claude.exe"
claude --version
```

If the extension has updated, the folder name changes. List the folders with
`ls $env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*` and use the newest.

## 3. Recording sequence

Do this in one continuous take. Trimming idle waits afterwards is allowed.
Cutting between the typed URL and the findings is not.

1. Open PowerShell in an empty folder containing `submission.zip`.
2. Run REPLAY steps 1 to 3 on camera: unpack, install the skills, `cd demo`.
   This is your "wiring" line: the skills on screen are the submitted package, copied unchanged.
3. `$env:PYTHONUTF8="1"`, then `claude --version`. Say the harness and model aloud.
4. Start Claude Code with the REPLAY step 4 command.
5. Paste the REPLAY step 5 prompt. The URL is visible in it.
6. Let it run. You should see a `Skill` call to `audit-orchestrator` first. Trim waits.
7. When it finishes, read its summary on screen, then open `audit_out\audit_report.md`.
8. Drill into one finding with live proof (below), then show the roadmap.

The agent run took 2 to 7 minutes in rehearsal.

## 4. The drill-in

**First choice: the crawler finding.** It shows an agent correcting its own scripts.

- The scripts propose "AI crawler user-agents are blocked at the network layer" as critical.
- The agent downgrades it, because only training crawlers are refused and those do
  not affect citation. It landed at low twice and medium once. Narrate the severity
  the run actually shows.
- Prove it live:

```
curl.exe -s -o NUL -w "%{http_code}\n" -A "GPTBot/1.1" https://www.sqlite.org/
curl.exe -s -o NUL -w "%{http_code}\n" -A "OAI-SearchBot/1.0" https://www.sqlite.org/
```

Expected output is 403, then 200. In PowerShell, type `curl.exe`, because plain
`curl` is an alias for a different command there.

**Backup: the missing H1.** Use it if the crawler finding is phrased unclearly.

```
curl.exe -s https://www.sqlite.org/ | findstr /i /c:"<h1"
```

No output means no H1.

**Prioritisation.** Scroll to "Remediation roadmap" in the `.md` report. In every
rehearsal, the sitemap was in "Do now".

## 5. What to expect

Across three rehearsals on this harness and model:

| | Run 1 | Run 2 | Run 3 (headless) |
|---|---|---|---|
| Critical / high | 0 / 0 | 0 / 0 | 0 / 0 |
| Training crawlers refused | low | low | medium |
| No XML sitemap | medium | medium | medium |
| Homepage has no H1 | medium | medium | low |
| No structured data | medium | low | medium |
| Readiness score | 94 | 96 | 90 |
| Findings | 16 | 12 | 20 |

Say the substance is stable and the wording varies. Never say the output is identical.

## 6. If a judge picks their own site

We also ran the full agent flow on `https://www.adobe.com/`, which the engine had
never seen. It scored 82, with four high findings centred on facts and prices that
are not in the server-rendered HTML. The agent noticed that 6 of the 15 sampled
pages were CMS fragment endpoints and suppressed a misleading noindex finding on
its own. After that crawl, adobe.com started timing out requests from this
machine, so a judge who re-runs it quickly may see timeouts. The engine reports a
timeout as "could not observe", never as a defect.

## 7. Known limits of the frozen engine

Changing any script now would make the demo engine differ from the submitted one,
which is an integrity failure. So these are recorded, not fixed.

- **Inline SVG titles corrupt page titles.** The collector appends text from every
  `<title>` element, including ones inside SVG icons. Seen on stripe.com, where it
  produced a false high finding about term coverage. Cause:
  `crawl-render-audit/scripts/evidence_collector.py`, line 547.
- **Near-duplicate pages eat the crawl budget.** Country copies of one page on
  stripe.com, CMS fragments on adobe.com.
- **The scripts alone over-call AI crawler blocks.** They probe only GPTBot and
  ClaudeBot and treat a 403 as critical. The agent's review corrects this, which
  is why the demo must be agent-driven.
- **Stale dates can be reported twice**, once by each of two skills, without a merge.

## 8. Do not

- Do not edit anything under `skills/`, or in `submission.zip`, before recording.
- Do not record a different site, model or harness version without editing REPLAY.
- Do not splice takes. If a run fails, record again from the top.
- Do not narrate a finding that is not on screen.
