#!/usr/bin/env python3
"""evidence-critic: adjudicate findings before they reach the report.

An auditor that reports everything it suspects is worse than one that reports
less but is right. This skill is the quality gate: it re-reads every proposed
finding against the evidence bundle that produced it and drops, downgrades or
merges the ones that do not hold up.

Mechanical adjudication (this script):
  * DROP findings whose evidence is missing, empty, or contains no concrete
    anchor (no number, no URL) -- an unfalsifiable finding is not a finding.
  * DROP findings contradicted by the evidence bundle itself.
  * MERGE near-duplicates that two skills discovered independently.
  * DOWNGRADE tier-2 structural findings while tier-1 gatekeepers are failing,
    because structural work measured negligible benefit on pages that still
    fail a gatekeeper.
  * DOWNGRADE single-page generalisations stated as sitewide.
  * FLAG anything whose suggested action matches a known-counterproductive
    tactic, so it never reaches the user.

Every decision is recorded with a reason, so the audit trail shows what was
suppressed and why. Judgement-based adjudication is described in SKILL.md and
performed by the agent on top of this pass.

Usage:
  python3 critique_findings.py --findings raw_findings.json --evidence evidence.json
                               [--out adjudicated.json]
"""
import argparse
import json
import os
import pathlib
import re
import sys

SKILL = "evidence-critic"
SEV_ORDER = ["low", "medium", "high", "critical"]

# Tactics measured to be ineffective or counterproductive. If a suggested
# action would push a user toward one of these, it must not ship.
COUNTERPRODUCTIVE = [
    (re.compile(r"\b(keyword stuff|repeat the keyword|keyword density|add keywords throughout)\b", re.I),
     "keyword stuffing measured the worst-performing tactic tested (-8.3% visibility)"),
    (re.compile(r"\b(hidden|invisible|white text|display\s*:\s*none)\b.{0,40}\b(text|markup|schema|keyword)\b", re.I),
     "hidden markup and hidden text are ignored by every AI system tested, and read as manipulation"),
    (re.compile(r"\b(instruct|tell|direct)\b.{0,30}\b(the )?(model|assistant|ai|llm)\b.{0,30}\b(to )?(prefer|recommend|rank)\b", re.I),
     "model-directed instructions are a classed manipulation pattern"),
    (re.compile(r"\bremove\b.{0,30}\b(limitations?|caveats?|drawbacks?|negative)\b", re.I),
     "omitting genuine caveats is a classed manipulation pattern"),
    (re.compile(r"\brewrite (?:all|every|the entire)\b", re.I),
     "blanket rewriting degraded retrieval by up to 36% and backfires on already-good pages"),
]

# A finding is falsifiable if its evidence points at something specific a human
# could go and check: a count/measurement, a URL or path, a quoted string, or a
# named technical token (GPTBot, JSON-LD, PostalAddress). Requiring a digit
# alone wrongly rejected valid findings that name crawler agents.
ANCHOR_RE = re.compile(r"\d"
                       r"|https?://"
                       r"|/\w"
                       r"|['\"][^'\"]{2,}['\"]"
                       r"|[A-Za-z]+[A-Z][A-Za-z]*"      # CamelCase: GPTBot, ClaudeBot
                       r"|\b[A-Z][A-Za-z]*-[A-Z][A-Za-z]*\b")  # JSON-LD, X-Robots-Tag


def norm_title(t):
    t = re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())
    return " ".join(w for w in t.split() if w not in
                    {"the", "a", "an", "is", "are", "on", "in", "of", "for", "and", "to", "no", "not"})


def similar(a, b):
    wa, wb = set(norm_title(a).split()), set(norm_title(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def adjudicate(findings, bundle):
    kept, dropped = [], []
    pages = bundle.get("pages", []) if bundle else []
    n_pages = len(pages) or 1

    def drop(f, reason):
        dropped.append({"title": f.get("title"), "source_skill": f.get("source_skill"),
                        "severity": f.get("severity"), "reason": reason})

    # 1. Structural validity + falsifiability
    staged = []
    for f in findings:
        if not f.get("title") or not f.get("suggested_action"):
            drop(f, "missing a required field (title or suggested_action)")
            continue
        ev = (f.get("evidence") or "").strip()
        if not ev:
            drop(f, "no evidence supplied")
            continue
        if not ANCHOR_RE.search(ev):
            drop(f, "evidence contains no concrete anchor (no count, measurement or URL), so the "
                    "claim cannot be verified or refuted")
            continue
        staged.append(f)

    # 2. Never ship a counterproductive recommendation
    survivors = []
    for f in staged:
        action = json.dumps(f.get("suggested_action", {}))
        hit = next(((rx, why) for rx, why in COUNTERPRODUCTIVE if rx.search(action)), None)
        if hit:
            drop(f, f"suggested action matches a known-counterproductive tactic: {hit[1]}")
            continue
        survivors.append(f)

    # 3. Contradiction checks against the evidence bundle
    checked = []
    for f in survivors:
        title = (f.get("title") or "").lower()
        if "no structured data" in title:
            verdicts = {p.get("structured_data", {}).get("verdict") for p in pages}
            if verdicts - {"NO_STRUCTURED_DATA", None}:
                drop(f, f"contradicted by evidence: some pages do carry structured data "
                        f"({sorted(v for v in verdicts if v)})")
                continue
        if "not served over https" in title:
            if all(p.get("https", True) for p in pages):
                drop(f, "contradicted by evidence: all sampled pages resolved over HTTPS")
                continue
        checked.append(f)

    # 4. Merge near-duplicates discovered independently by different skills
    merged = []
    for f in sorted(checked, key=lambda x: -SEV_ORDER.index(x.get("severity", "low"))):
        # Threshold is deliberately high. At 0.6, "Conflicting phone numbers
        # across the site's own pages" and "Conflicting email addresses across
        # the site's own pages" merged into one finding whose title and
        # evidence then described different things -- shared boilerplate words
        # ("conflicting", "across", "pages") were enough to pass. Genuine
        # cross-skill duplicates have near-identical titles anyway.
        dupe = next((m for m in merged
                     if m.get("category") == f.get("category")
                     and similar(m.get("title"), f.get("title")) >= 0.8), None)
        if dupe:
            srcs = set(str(dupe.get("source_skill", "")).split(", ")) | {f.get("source_skill", "")}
            dupe["source_skill"] = ", ".join(sorted(s for s in srcs if s))
            if len(f.get("evidence", "")) > len(dupe.get("evidence", "")):
                dupe["evidence"] = f["evidence"]
            dupe.setdefault("corroborated_by", []).append(f.get("source_skill"))
            dropped.append({"title": f.get("title"), "source_skill": f.get("source_skill"),
                            "severity": f.get("severity"),
                            "reason": f"merged into '{dupe.get('title')}' (same underlying issue "
                                      "found independently)"})
            continue
        merged.append(dict(f))

    # 5. Severity calibration
    tier1_failing = any(f.get("signal_tier") == 1 and f.get("severity") in ("critical", "high")
                        for f in merged)
    notes = []
    for f in merged:
        original = f.get("severity", "low")

        if f.get("signal_tier") == 2 and tier1_failing and original in ("critical", "high"):
            f["severity"] = "medium"
            f["suggested_action"]["priority"] = "medium"
            notes.append(f"downgraded '{f['title']}' {original}->medium: structural finding while "
                         "tier-1 gatekeepers are still failing")

        # A claim about one page should not be sold as a sitewide problem.
        m = re.match(r"\s*(\d+)\s*/\s*(\d+)", f.get("evidence", ""))
        if m and n_pages > 2:
            hit, total = int(m.group(1)), int(m.group(2))
            if total >= 3 and hit == 1 and original in ("critical", "high"):
                f["severity"] = "medium"
                f["suggested_action"]["priority"] = "medium"
                notes.append(f"downgraded '{f['title']}' {original}->medium: evidence covers only "
                             f"1 of {total} sampled pages")

        # Speculative mechanisms may not carry high severity.
        if f.get("evidence_tier") == "speculative" and original in ("critical", "high"):
            f["severity"] = "low"
            f["suggested_action"]["priority"] = "low"
            notes.append(f"downgraded '{f['title']}' {original}->low: mechanism is speculative "
                         "rather than measured")

        if f["severity"] != original:
            f["severity_adjusted_from"] = original

    return merged, dropped, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--findings", required=True, help="merged raw findings JSON")
    ap.add_argument("--evidence", help="evidence bundle used to cross-check claims")
    ap.add_argument("--out", default=None,
                    help="default: adjudicated_findings.json next to --findings, so a run's "
                         "files stay together")
    args = ap.parse_args()

    if args.out is None:
        args.out = str(pathlib.Path(args.findings).resolve().parent / "adjudicated_findings.json")

    for path in [args.findings] + ([args.evidence] if args.evidence else []):
        if not os.path.exists(path):
            print(f"error: file not found: {path}", file=sys.stderr)
            sys.exit(2)

    with open(args.findings, encoding="utf-8") as fh:
        payload = json.load(fh)
    findings = payload.get("findings", payload if isinstance(payload, list) else [])
    bundle = {}
    if args.evidence:
        with open(args.evidence, encoding="utf-8") as fh:
            bundle = json.load(fh)

    kept, dropped, notes = adjudicate(findings, bundle)
    out = {"site": payload.get("site") or bundle.get("site"),
           "findings": kept,
           "critic": {"input_count": len(findings), "kept": len(kept),
                      "dropped": dropped, "severity_notes": notes}}
    # Carry run-level context through untouched. The critic adjudicates
    # findings; it must not silently drop metadata the report depends on --
    # losing `short_circuited` here would let an unassessed site be scored.
    for key in ("short_circuited", "pages_sampled", "evidence_file", "collected_at"):
        if payload.get(key) is not None:
            out[key] = payload[key]
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"[{SKILL}] {len(findings)} in -> {len(kept)} kept, {len(dropped)} dropped/merged",
          file=sys.stderr)
    print(args.out)


if __name__ == "__main__":
    main()
