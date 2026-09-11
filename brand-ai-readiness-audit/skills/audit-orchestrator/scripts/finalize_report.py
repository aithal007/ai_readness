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
import re
import sys

SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CAT_RANK = {"discoverability": 0, "engagement": 1, "meta": 2}
SEV_WEIGHT = {"critical": 25, "high": 12, "medium": 5, "low": 1}
REQUIRED = ("title", "severity", "evidence", "suggested_action")
# A finding may carry status="not_applicable" (the check does not apply to this
# kind of site) or "not_observable" (the site or section could not be seen, so
# we cannot tell whether it is a problem). Neither is a defect: they are listed
# separately and are NOT counted in the severity summary or the pillar scores.
NON_DEFECT_STATUS = ("not_applicable", "not_observable")

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


# --- Stable finding codes ---------------------------------------------------
# `id` (F-001...) is positional: it reshuffles the moment severities change, so
# two runs of the same site are not diffable by id. `code` is stable for the
# life of a check, which is what lets you track "did STALE_DATES get fixed?"
# across runs, sites and time.
#
# The map is keyed on a distinctive substring of the title, matched in order.
# Anything unmatched falls back to a slug of the title, which is still stable
# unless the title itself is reworded.
CODE_MAP = [
    ("robots.txt blocks all", "ROBOTS_BLOCKS_ALL"),
    ("Search-index crawlers", "SEARCH_CRAWLERS_BLOCKED"),
    ("Training crawlers are blocked", "TRAINING_CRAWLERS_BLOCKED_OK"),
    ("Live user-fetch agents", "LIVE_FETCH_BLOCKED"),
    ("Content Signals", "CONTENT_SIGNALS_PRESENT"),
    ("network layer", "NETWORK_LAYER_BLOCK"),
    ("excluded from indexing", "NOINDEX"),
    ("requires JavaScript", "JS_RENDER_GAP"),
    ("locked in non-text", "FACTS_IN_NON_TEXT"),
    ("state blob", "CONTENT_IN_STATE_BLOB"),
    ("Widespread broken links", "LINK_ROT_WIDESPREAD"),
    ("Broken internal links", "BROKEN_LINKS"),
    ("XML sitemap", "NO_SITEMAP"),
    ("fails to parse", "INVALID_STRUCTURED_DATA"),
    ("No structured data", "NO_STRUCTURED_DATA"),
    ("weak or legacy structured data", "WEAK_STRUCTURED_DATA"),
    ("not unambiguously identified", "ENTITY_AMBIGUOUS"),
    ("Conflicting Organization", "ENTITY_ID_COLLISION"),
    ("does not appear in the visible", "MARKUP_PAGE_MISMATCH"),
    ("no Organization entity", "NO_ORGANIZATION_NODE"),
    ("no title element", "NO_TITLE"),
    ("generic placeholder", "PLACEHOLDER_TITLE"),
    ("no meta description", "NO_META_DESCRIPTION"),
    ("No language declared", "NO_HTML_LANG"),
    ("llms.txt", "NO_LLMS_TXT"),
    ("topic terms are missing", "WEAK_TERM_COVERAGE"),
    ("no explicit price", "NO_PRICE"),
    ("visibly stale dates", "STALE_DATES"),
    ("stale dates", "STALE_DATES"),
    ("publish no date", "UNDATED_CONTENT"),
    ("no quotable evidence", "NO_QUOTABLE_EVIDENCE"),
    ("heavily hedged", "HEDGED_CLAIMS"),
    ("structured specifications", "NO_SPECS"),
    ("comparison against alternatives", "NO_COMPARISON"),
    ("very thin", "THIN_PAGES"),
    ("bury facts mid-passage", "LONG_SECTIONS"),
    ("almost no heading structure", "WEAK_HEADINGS"),
    ("without a summary paragraph", "NO_INTRO_SUMMARY"),
    ("core questions about this brand", "UNANSWERABLE_QUESTIONS"),
    ("non-extractable form", "ANSWERS_NOT_EXTRACTABLE"),
    ("Placeholder or 'coming soon'", "PLACEHOLDER_CONTENT"),
    ("Conflicting phone", "CONFLICTING_PHONES"),
    ("Conflicting email", "CONFLICTING_EMAILS"),
    ("phone numbers published", "MULTIPLE_PHONE_NUMBERS"),
    ("email addresses published", "MULTIPLE_EMAIL_ADDRESSES"),
    ("distinct price points", "MANY_PRICES"),
    ("third-party corroboration", "NO_CORROBORATION"),
    ("Priority claims", "PRIORITY_CLAIMS"),
    ("not served over HTTPS", "NO_HTTPS"),
    ("mobile viewport", "NO_VIEWPORT"),
    ("Visitor-goal checks not applicable", "GOALS_NOT_APPLICABLE"),
    ("visitor goals have no reachable", "GOALS_UNREACHABLE"),
    ("buried several clicks", "GOALS_BURIED"),
    ("no H1", "NO_H1"),
    ("no value proposition", "NO_VALUE_PROP"),
    ("on-site search", "NO_SITE_SEARCH"),
    ("no clear next action", "NO_CTA"),
    ("Dead-end pages", "DEAD_END_PAGES"),
    ("no alt text", "MISSING_ALT_TEXT"),
    ("Render-blocking scripts", "RENDER_BLOCKING_SCRIPTS"),
    ("accessible labels", "UNLABELLED_FORM_FIELDS"),
    ("not a public content site", "NOT_PUBLIC_SITE"),
    ("does not resolve", "DNS_FAILURE"),
    ("TLS/certificate", "TLS_ERROR"),
    ("refused the connection", "CONNECTION_REFUSED"),
    ("before timeout", "TIMEOUT_UNDETERMINED"),
    ("challenge page", "BOT_CHALLENGE"),
    ("403 to non-browser", "CDN_403"),
    ("HTTP authentication", "HTTP_AUTH_WALL"),
    ("rate-limited", "RATE_LIMITED"),
    ("blocked for this network", "GEO_BLOCKED"),
    ("server error", "SERVER_ERROR"),
    ("gated and their content", "GATED_PAGES_NOT_ASSESSED"),
    ("may be filtered, but this could not", "POSSIBLE_UA_FILTERING"),
    ("did not respond in time", "SLOW_OR_FLAKY_PAGES"),
    ("Redirect loop", "REDIRECT_LOOP"),
    ("long redirect chains", "LONG_REDIRECT_CHAIN"),
    ("passes through plain HTTP", "REDIRECT_VIA_HTTP"),
    ("too many choices", "NAV_TOO_MANY_ITEMS"),
    ("navigation exposes almost nothing", "NAV_TOO_SPARSE"),
    ("No breadcrumbs", "NO_BREADCRUMBS"),
    ("privacy policy or terms", "NO_PRIVACY_OR_TERMS"),
    ("uninformative anchor text", "VAGUE_ANCHOR_TEXT"),
    ("no visible way to buy", "PRICED_BUT_UNBUYABLE"),
    ("shipping or returns", "NO_SHIPPING_RETURNS"),
    ("published without a visible date", "ARTICLES_UNDATED"),
    ("no visible author attribution", "ARTICLES_UNATTRIBUTED"),
    ("local business publishes no opening hours", "NO_OPENING_HOURS"),
    ("did not complete", "ANALYZER_FAILED"),
]

# Rough implementation cost, used only to bucket the roadmap. "quick" = a config
# or copy change; "moderate" = template/content work; "project" = engineering or
# an ongoing programme.
EFFORT = {
    "ROBOTS_BLOCKS_ALL": "quick", "SEARCH_CRAWLERS_BLOCKED": "quick",
    "TRAINING_CRAWLERS_BLOCKED_OK": "quick", "LIVE_FETCH_BLOCKED": "quick",
    "CONTENT_SIGNALS_PRESENT": "quick", "NETWORK_LAYER_BLOCK": "quick",
    "NOINDEX": "quick", "NO_SITEMAP": "quick", "NO_HTML_LANG": "quick",
    "NO_TITLE": "quick", "PLACEHOLDER_TITLE": "quick", "NO_LLMS_TXT": "quick",
    "NO_VIEWPORT": "quick", "NO_HTTPS": "quick", "NO_H1": "quick",
    "INVALID_STRUCTURED_DATA": "quick", "RENDER_BLOCKING_SCRIPTS": "quick",
    "UNLABELLED_FORM_FIELDS": "quick", "MANY_PRICES": "quick",
    "NO_META_DESCRIPTION": "moderate", "NO_STRUCTURED_DATA": "moderate",
    "WEAK_STRUCTURED_DATA": "moderate", "ENTITY_AMBIGUOUS": "moderate",
    "ENTITY_ID_COLLISION": "moderate", "MARKUP_PAGE_MISMATCH": "moderate",
    "NO_ORGANIZATION_NODE": "moderate", "STALE_DATES": "moderate",
    "UNDATED_CONTENT": "moderate", "PLACEHOLDER_CONTENT": "moderate",
    "CONFLICTING_PHONES": "moderate", "CONFLICTING_EMAILS": "moderate",
    "BROKEN_LINKS": "moderate", "MISSING_ALT_TEXT": "moderate",
    "NO_PRICE": "moderate", "NO_SPECS": "moderate", "NO_CTA": "moderate",
    "NO_VALUE_PROP": "moderate", "NO_INTRO_SUMMARY": "moderate",
    "WEAK_HEADINGS": "moderate", "LONG_SECTIONS": "moderate",
    "HEDGED_CLAIMS": "moderate", "WEAK_TERM_COVERAGE": "moderate",
    "DEAD_END_PAGES": "moderate", "GOALS_BURIED": "moderate",
    "MULTIPLE_PHONE_NUMBERS": "quick", "MULTIPLE_EMAIL_ADDRESSES": "quick",
    "NO_PRIVACY_OR_TERMS": "quick", "REDIRECT_LOOP": "quick",
    "LONG_REDIRECT_CHAIN": "quick", "REDIRECT_VIA_HTTP": "quick",
    "NO_BREADCRUMBS": "moderate", "NAV_TOO_MANY_ITEMS": "moderate",
    "NAV_TOO_SPARSE": "moderate", "VAGUE_ANCHOR_TEXT": "moderate",
    "PRICED_BUT_UNBUYABLE": "moderate", "NO_SHIPPING_RETURNS": "moderate",
    "ARTICLES_UNDATED": "moderate", "ARTICLES_UNATTRIBUTED": "moderate",
    "NO_OPENING_HOURS": "quick", "POSSIBLE_UA_FILTERING": "quick",
    "SLOW_OR_FLAKY_PAGES": "project",
    "JS_RENDER_GAP": "project", "FACTS_IN_NON_TEXT": "project",
    "CONTENT_IN_STATE_BLOB": "project", "LINK_ROT_WIDESPREAD": "project",
    "UNANSWERABLE_QUESTIONS": "project", "ANSWERS_NOT_EXTRACTABLE": "project",
    "NO_QUOTABLE_EVIDENCE": "project", "NO_COMPARISON": "project",
    "THIN_PAGES": "project", "NO_CORROBORATION": "project",
    "PRIORITY_CLAIMS": "project", "NO_SITE_SEARCH": "project",
    "GOALS_UNREACHABLE": "project",
}

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def finding_code(f):
    title = (f.get("title") or "")
    low = title.lower()
    for needle, code in CODE_MAP:
        if needle.lower() in low:
            return code
    slug = _SLUG_STRIP.sub("_", low).strip("_")
    return "_".join(slug.split("_")[:5]).upper() or "UNCODED"


# --- Confidence -------------------------------------------------------------
# Derived, never hand-set, so it cannot drift from the finding it describes.
_TIER_BASE = {"measured": 0.90, "correlational": 0.75, "speculative": 0.50}
_ONE_OF_N = re.compile(r"^\s*1\s*/\s*(\d+)")


def confidence_of(f):
    """How sure the audit is that this is a real defect, on the evidence it has.

    Starts from how well-evidenced the underlying mechanism is, then adjusts for
    how much of the site actually showed the problem and whether the critic had
    to pull the severity down.
    """
    c = _TIER_BASE.get(f.get("evidence_tier"), 0.75)
    ev = f.get("evidence") or ""
    m = _ONE_OF_N.match(ev)
    if m and int(m.group(1)) >= 3:
        c -= 0.15                      # a single page is a weak basis for a site claim
    if f.get("severity_adjusted_from"):
        c -= 0.10                      # the critic already doubted it
    if f.get("corroborated_by"):
        c += 0.05                      # two skills found it independently
    if f.get("signal_tier") == 2:
        c -= 0.05                      # secondary signal
    return round(max(0.30, min(0.98, c)), 2)


def build_roadmap(findings):
    """Sequence the fixes: what to do now, next, and later.

    Severity alone is a poor work order -- it tells you what hurts most, not
    what to pick up first. A critical config change that takes ten minutes
    should not sit behind a medium-severity content programme. So the roadmap
    buckets by impact AGAINST effort:

      now   -- critical/high, or anything cheap enough to do immediately
      next  -- the rest of the medium-severity work
      later -- low severity, and long-running programmes

    Ordering inside each bucket stays severity-first.
    """
    now, nxt, later = [], [], []
    for f in findings:
        sev, effort = f["severity"], f.get("effort", "unknown")
        if sev in ("critical", "high"):
            now.append(f)              # impact overrides cost
        elif effort == "quick":
            now.append(f)              # cheap enough that deferring costs more than doing
        elif effort == "project":
            later.append(f)            # a programme, not a sprint item -- plan it, don't queue it
        elif sev == "medium":
            nxt.append(f)
        else:
            later.append(f)
    key = lambda f: (SEV_RANK.get(f["severity"], 3), f["id"])
    return {
        "now": [{"id": f["id"], "code": f["code"], "title": f["title"],
                 "severity": f["severity"], "effort": f.get("effort"),
                 "action": f.get("suggested_action", {}).get("summary", "")}
                for f in sorted(now, key=key)],
        "next": [{"id": f["id"], "code": f["code"], "title": f["title"],
                  "severity": f["severity"], "effort": f.get("effort"),
                  "action": f.get("suggested_action", {}).get("summary", "")}
                 for f in sorted(nxt, key=key)],
        "later": [{"id": f["id"], "code": f["code"], "title": f["title"],
                   "severity": f["severity"], "effort": f.get("effort"),
                   "action": f.get("suggested_action", {}).get("summary", "")}
                  for f in sorted(later, key=key)],
        "note": "Bucketed by impact against implementation cost, so a cheap fix is not "
                "queued behind an expensive one. Severity order is preserved within each "
                "bucket.",
    }


_URL_RE = re.compile(r"https?://[^\s,;)\]]+")


def affected_urls(f, limit=12):
    """The specific URLs a finding concerns, so a reader can go and look.

    Analyzers already name examples inside the evidence string; this lifts them
    into a structured field rather than requiring every call site to pass them.
    """
    urls = []
    if f.get("page"):
        urls.append(f["page"])
    for u in _URL_RE.findall(f.get("evidence") or ""):
        urls.append(u.rstrip(".,;"))
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:limit]


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

    all_valid = [f for f in payload.get("findings", []) if all(k in f for k in REQUIRED)]
    findings = [f for f in all_valid if f.get("status") not in NON_DEFECT_STATUS]
    not_assessed = [f for f in all_valid if f.get("status") in NON_DEFECT_STATUS]
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
            "code": finding_code(f),
            "title": f.get("title"),
            "severity": sev,
            "confidence": confidence_of(f),
            "category": f.get("category", "meta"),
            "evidence": f.get("evidence"),
            "mechanism": f.get("mechanism", ""),
            "evidence_tier": f.get("evidence_tier", "correlational"),
            "signal_tier": f.get("signal_tier"),
            "suggested_action": f.get("suggested_action", {}),
            "source_skill": f.get("source_skill", ""),
        }
        urls = affected_urls(f)
        if urls:
            rec["affected_urls"] = urls
        for opt in ("page", "answerability", "severity_adjusted_from", "corroborated_by",
                    "status"):
            if f.get(opt) is not None:
                rec[opt] = f[opt]
        rec["effort"] = EFFORT.get(rec["code"], "unknown")
        out_findings.append(rec)

    not_assessed_out = []
    for j, f in enumerate(sorted(not_assessed, key=lambda x: x.get("title", "")), 1):
        na = {
            "id": f"N-{j:03d}",
            "title": f.get("title"),
            "status": f.get("status"),
            "category": f.get("category", "meta"),
            "evidence": f.get("evidence"),
            "mechanism": f.get("mechanism", ""),
            "suggested_action": f.get("suggested_action", {}),
            "source_skill": f.get("source_skill", ""),
        }
        if f.get("page") is not None:
            na["page"] = f["page"]
        not_assessed_out.append(na)

    pillars = {key: {"label": label, "score": score_pillar(out_findings, skills)}
               for key, (label, skills) in PILLARS.items()}
    overall = round(sum(p["score"] for p in pillars.values()) / len(pillars))

    # A site that could not be assessed at all must not score as a healthy one.
    # When the run short-circuited -- unreachable origin, login wall, private app
    # shell -- there are no findings to deduct, so the arithmetic would hand back
    # a perfect 100 for a site we never actually read. That is the most
    # misleading number this report could print, so it prints none.
    unassessed_run = payload.get("short_circuited") or (not out_findings and
                                                        bool(not_assessed_out))
    if unassessed_run:
        reason = (out_findings or not_assessed_out or [{}])[0].get(
            "title", "the site could not be assessed")
        readiness = {
            "overall": None,
            "pillars": {k: {"label": v["label"], "score": None} for k, v in pillars.items()},
            "scale_note": f"Not scored: {reason}. No pages were assessed, so a score would be "
                          "meaningless -- an unread site is not a healthy one.",
        }
    else:
        readiness = {
            "overall": overall,
            "pillars": pillars,
            "scale_note": "Scores are this audit's own 0-100 framework (100 = no findings in that "
                          "pillar), intended to show relative weakness at a glance. They are not a "
                          "validated or externally comparable metric.",
        }

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
        "readiness": readiness,
        "audit_scope": meta,
        "roadmap": build_roadmap(out_findings),
        "findings": out_findings,
    }
    if not_assessed_out:
        report["not_assessed"] = not_assessed_out
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
        for p in readiness["pillars"].values():
            if p["score"] is None:
                L.append(f"| {p['label']} | not scored |")
            else:
                bar = "█" * (p["score"] // 10) + "░" * (10 - p["score"] // 10)
                L.append(f"| {p['label']} | `{bar}` {p['score']}/100 |")
        L += ["", f"_{readiness['scale_note']}_", ""]

        rm = report["roadmap"]
        if any(rm[b] for b in ("now", "next", "later")):
            L += ["## Remediation roadmap", "",
                  f"_{rm['note']}_", ""]
            for bucket, heading in (("now", "Do now"),
                                    ("next", "Do next"),
                                    ("later", "Later / ongoing")):
                if rm[bucket]:
                    L += [f"### {heading}", ""]
                    for r in rm[bucket]:
                        L.append(f"- **{r['id']} · {r['title']}** "
                                 f"({r['severity']}, {r['effort']} effort) — {r['action']}")
                    L.append("")

        L += ["## All findings", ""]
        for f in out_findings:
            L += [f"### {f['id']} · {f['title']}", "",
                  f"- **Code:** `{f['code']}`  ·  **Severity:** {f['severity']}  ·  "
                  f"**Confidence:** {f['confidence']:.0%}  ·  **Category:** {f['category']}  ·  "
                  f"**Evidence strength:** {f['evidence_tier']}",
                  f"- **What we found:** {f['evidence']}"]
            if f.get("affected_urls"):
                shown = ", ".join(f["affected_urls"][:5])
                more = len(f["affected_urls"]) - 5
                L.append(f"- **Affected URLs:** {shown}" + (f" (+{more} more)" if more > 0 else ""))
            if f.get("mechanism"):
                L.append(f"- **Why it matters:** {f['mechanism']}")
            sa = f["suggested_action"]
            L.append(f"- **Do this ({sa.get('priority')}, {f.get('effort')} effort):** "
                     f"{sa.get('summary')}")
            if sa.get("how"):
                L.append(f"  - _How:_ {sa['how']}")
            if f.get("severity_adjusted_from"):
                L.append(f"  - _Severity adjusted from {f['severity_adjusted_from']} by the "
                         "evidence critic._")
            L.append("")

        if not_assessed_out:
            L += ["## Not assessed", "",
                  "Checks that do not apply to this kind of site, or areas that could not be "
                  "observed (blocked, gated, or unreachable). Listed so the report is honest "
                  "about its own coverage — these are **not** defects and are not scored:", ""]
            for f in not_assessed_out:
                lbl = "not applicable" if f["status"] == "not_applicable" else "not observable"
                L.append(f"- **{f['id']} · {f['title']}** ({lbl}) — {f['evidence']}")
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
                      "readiness_overall": readiness["overall"],
                      "report": args.out, "markdown": args.md}, indent=1))


if __name__ == "__main__":
    main()
