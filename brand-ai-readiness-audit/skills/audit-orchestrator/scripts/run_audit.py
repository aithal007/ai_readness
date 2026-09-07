#!/usr/bin/env python3
"""Stage 1 of the audit: collect one evidence snapshot, then run every scripted
analyzer against it.

Collect-once/analyze-many is deliberate. If each skill fetched the site
separately they would each see a slightly different snapshot, findings could
contradict each other for no reason, and the crawl budget would be spent
several times over. One bundle means every skill reasons over identical
evidence, and the whole audit costs a single crawl.

Failure policy: a collector failure is fatal (nothing downstream can run); an
analyzer failure is recorded as a visible "meta" finding and the run continues
degraded. A degraded run must never look like a clean one.

Usage:
  python3 run_audit.py <url> [--out raw_findings.json] [--evidence-out evidence.json]
                            [--today YYYY-MM-DD] [--max-pages 15]
Prints the raw findings path to stdout; progress to stderr.
Exit: 0 ok, 1 collector failed, 2 bad arguments.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

# (skill id, script, extra args) -- every analyzer reads the shared bundle.
ANALYZERS = [
    ("crawl-render-audit", "analyze_crawl_render.py", []),
    ("structured-data-entity-audit", "analyze_structured_entity.py", []),
    ("ai-citability-audit", "analyze_citability.py", []),
    ("answerability-probe", "analyze_answerability.py", []),
    ("freshness-corroboration-audit", "analyze_freshness.py", ["--today"]),
    ("engagement-audit", "analyze_engagement.py", []),
]


def meta_finding(skill, err):
    return {
        "title": f"{skill} analyzer did not complete",
        "severity": "low", "category": "meta",
        "evidence": f"{err}"[:400],
        "mechanism": "This check could not run, so its area is UNVERIFIED rather than clean. "
                     "A degraded run that looks identical to a clean one is the most dangerous "
                     "outcome in a multi-step audit, so the gap is recorded explicitly.",
        "suggested_action": {
            "summary": f"Re-run {skill}'s analyzer against the evidence bundle to see the "
                       "underlying error before treating this area as passing.",
            "priority": "low"},
        "signal_tier": 1, "evidence_tier": "measured", "source_skill": skill,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("url")
    ap.add_argument("--out", default="raw_findings.json")
    ap.add_argument("--evidence-out", default="evidence.json")
    ap.add_argument("--today", default=None,
                    help="ISO date to treat as today; pass the agent's real current date")
    ap.add_argument("--max-pages", type=int, default=15)
    ap.add_argument("--budget-seconds", type=int, default=150)
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parents[3]
    collector = root / "skills" / "crawl-render-audit" / "scripts" / "evidence_collector.py"
    if not collector.exists():
        print(f"error: collector not found at {collector}", file=sys.stderr)
        sys.exit(2)

    # --- Stage 1: collect once (idempotent: overwrites a deterministic path)
    print(f"[orchestrator] collecting evidence from {args.url} ...", file=sys.stderr)
    try:
        subprocess.run([sys.executable, str(collector), args.url,
                        "--out", args.evidence_out,
                        "--max-pages", str(args.max_pages),
                        "--budget-seconds", str(args.budget_seconds)],
                       check=True, capture_output=True, text=True,
                       timeout=args.budget_seconds + 120)
    except Exception as e:
        print(f"error: evidence collection failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    with open(args.evidence_out, encoding="utf-8") as fh:
        bundle = json.load(fh)
    stats = bundle.get("stats", {})
    print(f"[orchestrator] collected {stats.get('pages_fetched')} page(s) in "
          f"{stats.get('elapsed_seconds')}s", file=sys.stderr)

    if not bundle.get("entry_reachable"):
        print("[orchestrator] site unreachable; emitting single critical finding", file=sys.stderr)
        payload = {"site": args.url, "evidence_file": args.evidence_out, "findings": [{
            "title": "Site did not respond to an unauthenticated request",
            "severity": "critical", "category": "discoverability",
            "evidence": f"Entry fetch of {args.url} failed: {bundle.get('entry_error')}.",
            "mechanism": "If a plain GET fails, no crawler can reach the site at all and nothing "
                         "else can be assessed.",
            "suggested_action": {"summary": "Verify DNS, TLS and that the origin answers anonymous "
                                            "external GET requests.", "priority": "critical"},
            "signal_tier": 1, "evidence_tier": "measured", "source_skill": "crawl-render-audit"}]}
        pathlib.Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(args.out)
        return

    # --- Stage 2: fan out over the shared bundle ---------------------------
    all_findings = []
    for skill, script, extra in ANALYZERS:
        path = root / "skills" / skill / "scripts" / script
        if not path.exists():
            all_findings.append(meta_finding(skill, f"analyzer script missing at {path}"))
            continue
        cmd = [sys.executable, str(path), "--evidence", args.evidence_out]
        if "--today" in extra and args.today:
            cmd += ["--today", args.today]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if not proc.stdout.strip():
                raise RuntimeError(f"no output (exit {proc.returncode}): {proc.stderr[-300:]}")
            found = json.loads(proc.stdout).get("findings", [])
            for f in found:
                f.setdefault("source_skill", skill)
            all_findings.extend(found)
            print(f"[orchestrator] {skill}: {len(found)} finding(s)", file=sys.stderr)
        except Exception as e:
            print(f"[orchestrator] {skill} FAILED: {e}", file=sys.stderr)
            all_findings.append(meta_finding(skill, f"{type(e).__name__}: {e}"))

    payload = {"site": bundle.get("site", args.url), "evidence_file": args.evidence_out,
               "collected_at": bundle.get("collected_at"),
               "pages_sampled": stats.get("pages_fetched"), "findings": all_findings}
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[orchestrator] {len(all_findings)} raw finding(s) -> {args.out}", file=sys.stderr)
    print(args.out)


if __name__ == "__main__":
    main()
