#!/usr/bin/env python3
"""Final stage: turn adjudicated findings into the audit report.

Assigns stable IDs, computes the severity summary and pillar readiness scores,
orders everything by what to fix first, and renders a Markdown companion a
non-expert can act on without understanding crawler internals.

The pillar scores are this audit's own framework, not a validated metric, and
the report says so in the output. They exist to make relative weakness legible
at a glance, not to imply measurement precision that does not exist.

Usage:
  python3 finalize_report.py adjudicated_findings.json --site example.com
        [--evidence evidence.json] [--out audit_report.json] [--md audit_report.md]
Prints a compact summary to stdout (the full report goes to --out, because
harnesses truncate long stdout).
"""
import argparse
import datetime
import json
import os
import pathlib
import sys

SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CAT_RANK = {"discoverability": 0, "engagement": 1, "meta": 2}
SEV_WEIGHT = {"critical": 25, "high": 12, "medium": 5, "low": 1}
REQUIRED = ("title", "severity", "evidence", "suggested_action")

PILLARS = {
    "crawl_access": ("Reachable", {"crawl-render-audit"}),
    "machine_readable": ("Readable", {"crawl-render-audit", "structured-data-entity-audit"}),
    "citability": ("Quotable", {"ai-citability-audit"}),
    "answerability": ("Answerable", {"answerability-probe"}),
    "trust_freshness": ("Current & corroborated", {"freshness-corroboration-audit"}),
    "engagement": ("Engaging", {"engagement-audit"}),
}


def score_pillar(findings, skills):
    penalty = sum(SEV_WEIGHT.get(f["severity"], 1)
                  for f in findings
                  if any(s in (f.get("source_skill") or "") for s in skills))
    return max(0, 100 - penalty)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("findings_file")
    ap.add_argument("--site")
    ap.add_argument("--evidence")
    ap.add_argument("--out", default="audit_report.json")
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    if not os.path.exists(args.findings_file):
        print(f"error: file not found: {args.findings_file}", file=sys.stderr)
        sys.exit(2)
    with open(args.findings_file, encoding="utf-8") as fh:
        payload = json.load(fh)

    findings = [f for f in payload.get("findings", []) if all(k in f for k in REQUIRED)]
    site = args.site or payload.get("site", "")

    meta = {}
    if args.evidence and os.path.exists(args.evidence):
        with open(args.evidence, encoding="utf-8") as fh:
            b = json.load(fh)
        meta = {"pages_sampled": b.get("stats", {}).get("pages_fetched"),
                "crawl_seconds": b.get("stats", {}).get("elapsed_seconds"),
                "collected_at": b.get("collected_at")}

    findings.sort(key=lambda f: (SEV_RANK.get(f.get("severity"), 3),
                                 CAT_RANK.get(f.get("category"), 2),
                                 -SEV_WEIGHT.get(f.get("suggested_action", {}).get("priority"), 0)))

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    out_findings = []
    for i, f in enumerate(findings, 1):
        sev = f.get("severity") if f.get("severity") in counts else "low"
        counts[sev] += 1
        rec = {
            "id": f"F-{i:03d}",
            "title": f.get("title"),
            "severity": sev,
            "category": f.get("category", "meta"),
            "evidence": f.get("evidence"),
            "mechanism": f.get("mechanism", ""),
            "evidence_tier": f.get("evidence_tier", "correlational"),
            "signal_tier": f.get("signal_tier"),
            "suggested_action": f.get("suggested_action", {}),
            "source_skill": f.get("source_skill", ""),
        }
        for opt in ("page", "answerability", "severity_adjusted_from", "corroborated_by"):
            if f.get(opt) is not None:
                rec[opt] = f[opt]
        out_findings.append(rec)

    pillars = {key: {"label": label, "score": score_pillar(out_findings, skills)}
               for key, (label, skills) in PILLARS.items()}
    overall = round(sum(p["score"] for p in pillars.values()) / len(pillars))

    report = {
        "site": site,
        "audited_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_findings": len(out_findings),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
        },
        "readiness": {
            "overall": overall,
            "pillars": pillars,
            "scale_note": "Scores are this audit's own 0-100 framework (100 = no findings in that "
                          "pillar), intended to show relative weakness at a glance. They are not a "
                          "validated or externally comparable metric.",
        },
        "audit_scope": meta,
        "findings": out_findings,
    }
    if payload.get("critic"):
        report["critic_summary"] = {
            "findings_considered": payload["critic"].get("input_count"),
            "findings_reported": payload["critic"].get("kept"),
            "suppressed": payload["critic"].get("dropped", []),
            "severity_adjustments": payload["critic"].get("severity_notes", []),
        }

    pathlib.Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.md:
        L = [f"# AI Discoverability & Engagement Audit — {site}", "",
             f"_Audited {report['audited_at']}"
             + (f" · {meta.get('pages_sampled')} pages sampled in {meta.get('crawl_seconds')}s_"
                if meta else "_"), "",
             f"**{report['summary']['total_findings']} findings** — "
             f"{counts['critical']} critical · {counts['high']} high · "
             f"{counts['medium']} medium · {counts['low']} low", "",
             "## Readiness at a glance", "",
             "| Pillar | Score |", "|---|---|"]
        for p in pillars.values():
            bar = "█" * (p["score"] // 10) + "░" * (10 - p["score"] // 10)
            L.append(f"| {p['label']} | `{bar}` {p['score']}/100 |")
        L += ["", f"_{report['readiness']['scale_note']}_", ""]

        crit = [f for f in out_findings if f["severity"] in ("critical", "high")]
        if crit:
            L += ["## Fix these first", ""]
            for f in crit:
                L.append(f"- **{f['id']} · {f['title']}** — {f['suggested_action'].get('summary')}")
            L.append("")

        L += ["## All findings", ""]
        for f in out_findings:
            L += [f"### {f['id']} · {f['title']}", "",
                  f"- **Severity:** {f['severity']}  ·  **Category:** {f['category']}  ·  "
                  f"**Evidence strength:** {f['evidence_tier']}",
                  f"- **What we found:** {f['evidence']}"]
            if f.get("mechanism"):
                L.append(f"- **Why it matters:** {f['mechanism']}")
            sa = f["suggested_action"]
            L.append(f"- **Do this ({sa.get('priority')}):** {sa.get('summary')}")
            if sa.get("how"):
                L.append(f"  - _How:_ {sa['how']}")
            if f.get("severity_adjusted_from"):
                L.append(f"  - _Severity adjusted from {f['severity_adjusted_from']} by the "
                         "evidence critic._")
            L.append("")

        if report.get("critic_summary", {}).get("suppressed"):
            L += ["## Suppressed by the evidence critic", "",
                  "Candidate findings that did not survive verification — listed so the audit's "
                  "reasoning is auditable:", ""]
            for d in report["critic_summary"]["suppressed"][:15]:
                L.append(f"- ~~{d.get('title')}~~ — {d.get('reason')}")
            L.append("")
        pathlib.Path(args.md).write_text("\n".join(L), encoding="utf-8")

    print(json.dumps({"site": site, "summary": report["summary"],
                      "readiness_overall": overall,
                      "report": args.out, "markdown": args.md}, indent=1))


if __name__ == "__main__":
    main()
