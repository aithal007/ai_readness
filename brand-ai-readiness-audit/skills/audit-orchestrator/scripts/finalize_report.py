#!/usr/bin/env python3
"""Assigns finding IDs, de-dupes, computes the severity summary, and emits
the final schema-compliant audit report from a merged raw-findings file
(the output of run_checks.py, optionally with agent-authored qualitative
findings appended to its "findings" array in the same shape).

Usage:
  python3 finalize_report.py raw_findings.json [--site example.com]
      [--out audit_report.json] [--md audit_report.md]
"""
import argparse
import datetime
import json
import pathlib

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CATEGORY_ORDER = {"discoverability": 0, "engagement": 1, "meta": 2}
REQUIRED_FINDING_FIELDS = ("title", "severity", "evidence", "suggested_action")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_findings_file")
    ap.add_argument("--site", default=None)
    ap.add_argument("--out", default="audit_report.json")
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.raw_findings_file).read_text(encoding="utf-8"))
    site = args.site or data.get("site", "")
    findings = data.get("findings", [])

    # Drop anything malformed rather than letting it corrupt the report.
    findings = [f for f in findings if all(k in f for k in REQUIRED_FINDING_FIELDS)]

    # De-dupe exact (title, category) repeats (e.g. the same issue found on
    # both the homepage and a sampled sub-page), keeping the richer evidence.
    seen = {}
    for f in findings:
        key = (f.get("title", ""), f.get("category", ""))
        if key not in seen or len(f.get("evidence", "")) > len(seen[key].get("evidence", "")):
            seen[key] = f
    deduped = list(seen.values())

    deduped.sort(key=lambda f: (
        SEVERITY_ORDER.get(f.get("severity", "low"), 3),
        CATEGORY_ORDER.get(f.get("category", "meta"), 2),
    ))

    report_findings = []
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for i, f in enumerate(deduped, start=1):
        sev = f.get("severity", "low")
        if sev not in counts:
            sev = "low"
        counts[sev] += 1
        report_findings.append({
            "id": f"F-{i:03d}",
            "title": f.get("title", ""),
            "severity": sev,
            "category": f.get("category", "meta"),
            "evidence": f.get("evidence", ""),
            "mechanism": f.get("mechanism", ""),
            "suggested_action": f.get("suggested_action", {}),
            "source_skill": f.get("source_skill", ""),
        })

    report = {
        "site": site,
        "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_findings": len(report_findings),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
        },
        "findings": report_findings,
    }

    pathlib.Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if args.md:
        lines = [
            f"# AI Discoverability & Engagement Audit -- {site}", "",
            f"_Audited: {report['audited_at']}_", "",
            f"**{report['summary']['total_findings']} findings** -- "
            f"{counts['critical']} critical, {counts['high']} high, {counts['medium']} medium, {counts['low']} low",
            "",
        ]
        for f in report_findings:
            lines.append(f"## {f['id']} - {f['title']} ({f['severity'].upper()})")
            lines.append(f"- **Category:** {f['category']}")
            lines.append(f"- **Evidence:** {f['evidence']}")
            if f.get("mechanism"):
                lines.append(f"- **Why it matters:** {f['mechanism']}")
            sa = f.get("suggested_action", {})
            lines.append(f"- **Suggested action ({sa.get('priority', '')}):** {sa.get('summary', '')}")
            if sa.get("how"):
                lines.append(f"  - How: {sa['how']}")
            lines.append("")
        pathlib.Path(args.md).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
