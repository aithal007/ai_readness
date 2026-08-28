#!/usr/bin/env python3
"""Runs every scripted sub-skill check against one target site and writes a
merged, not-yet-finalized findings list to a JSON file.

This only runs the deterministic, script-based checks. The orchestrator
SKILL.md separately instructs the agent to append two kinds of
judgment-based findings this script cannot produce on its own:
  - off-site corroboration (needs live web search across other domains)
  - on-site orientation / value-proposition clarity (needs reading
    comprehension of the homepage text, not a regex)
Both are appended to the same findings list, in the same shape, before
finalize_report.py is run.

Usage: python3 run_checks.py <url> [--out raw_findings.json] [--today YYYY-MM-DD]
"""
import argparse
import json
import pathlib
import subprocess
import sys

SUB_SKILLS = [
    ("crawl-render-audit", "check_crawl_render.py", False),
    ("structured-data-entity-audit", "check_structured_data.py", False),
    ("freshness-corroboration-audit", "check_freshness.py", True),
    ("engagement-audit", "check_engagement.py", False),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="raw_findings.json")
    ap.add_argument("--today", default=None, help="ISO date (YYYY-MM-DD) to treat as 'now' for freshness checks")
    args = ap.parse_args()

    # .../skills/audit-orchestrator/scripts/run_checks.py -> up 3 = marketplace root
    root = pathlib.Path(__file__).resolve().parents[3]
    all_findings = []

    for skill_id, script_name, wants_today in SUB_SKILLS:
        script_path = root / "skills" / skill_id / "scripts" / script_name
        cmd = [sys.executable, str(script_path), args.url]
        if wants_today and args.today:
            cmd += ["--today", args.today]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=100)
            stdout = proc.stdout.strip()
            if not stdout:
                raise RuntimeError(f"empty stdout (exit {proc.returncode}): {proc.stderr[-500:]}")
            payload = json.loads(stdout)
            findings = payload.get("findings", [])
            for f in findings:
                f.setdefault("source_skill", skill_id)
            all_findings.extend(findings)
        except Exception as e:
            all_findings.append({
                "title": f"{skill_id} check module did not complete",
                "severity": "low",
                "category": "meta",
                "evidence": f"{type(e).__name__}: {e}",
                "mechanism": "This automated check could not finish (network issue, timeout, or an "
                             "unexpected page structure), so its findings are missing here -- treat this "
                             "area as unverified rather than clean, not as a passing result.",
                "suggested_action": {
                    "summary": f"Re-run the {skill_id} script directly against the target to see the "
                                "underlying error, and fix the root cause (network access, timeout, or a "
                                "parsing edge case) before trusting this section of the report.",
                    "priority": "low",
                },
                "source_skill": skill_id,
            })

    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps({"site": args.url, "findings": all_findings}, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
