#!/usr/bin/env python3
"""freshness-corroboration-audit: is this current, self-consistent, and backed
by anyone other than the brand itself?

Scripted half (this file): staleness, temporal contradictions, and facts that
disagree with each other across the site's own pages.

Agent half (SKILL.md Part B): off-site corroboration and SOURCE INDEPENDENCE --
whether independent sources agree, or whether an apparently well-corroborated
claim actually traces back to a single press release echoed by aggregators.
A single-domain script cannot check other domains, so that step is deliberately
not scripted rather than faked.

Usage: python3 analyze_freshness.py --evidence evidence.json [--today YYYY-MM-DD]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

SKILL = "freshness-corroboration-audit"
CORROBORATION_DOMAINS = ("g2.com", "trustpilot.com", "capterra.com", "wikipedia.org",
                         "wikidata.org", "linkedin.com", "github.com", "youtube.com",
                         "crunchbase.com", "bbb.org", "glassdoor.com", "producthunt.com")
PRESS_RE = re.compile(r"\b(as seen in|featured in|as featured on|in the press|press coverage|"
                      r"media coverage|award[- ]winning)\b", re.I)


def finding(title, severity, evidence, mechanism, action, priority,
            evidence_tier="measured", how=None):
    sa = {"summary": action, "priority": priority}
    if how:
        sa["how"] = how
    return {"title": title, "severity": severity, "category": "discoverability",
            "evidence": evidence, "mechanism": mechanism, "suggested_action": sa,
            "signal_tier": 1, "evidence_tier": evidence_tier, "source_skill": SKILL}


def analyze(bundle, today):
    findings = []
    pages = bundle.get("pages", [])
    if not pages:
        return findings
    year = today.year

    # --- Staleness ---------------------------------------------------------
    stale = []
    for p in pages:
        yrs = [int(y) for y in p["facts"]["copyright_years"] + p["facts"]["updated_years"]]
        if yrs and max(yrs) <= year - 2:
            stale.append((p["url"], max(yrs)))
    if stale:
        worst = year - min(y for _, y in stale)
        findings.append(finding(
            "Visibly stale dates on the site",
            "high" if worst >= 3 else "medium",
            f"{len(stale)} page(s) show a most-recent year at least 2 years old (checked against "
            f"{today.date().isoformat()}): " +
            "; ".join(f"{u} -> {y}" for u, y in stale[:4]) + ".",
            "Recency measured as a citation gatekeeper -- recent content beat old content by odds "
            "ratios above 10,000 across models. A visibly stale year also tells a human visitor "
            "the site may no longer be maintained.",
            "Review these pages, update what has changed, and set an accurate current date. "
            "Auto-generate the footer copyright year.",
            "high" if worst >= 3 else "medium",
            how="Do not simply bump the date without reviewing content -- and do not delete dates "
                "to look evergreen, since undated content measured worse than recently-dated."))

    # --- Temporal contradictions -------------------------------------------
    coming = [p for p in pages if p["facts"]["coming_soon"]]
    if coming:
        aged = [p for p in coming
                if any(int(y) <= year - 1 for y in
                       p["facts"]["copyright_years"] + p["facts"]["updated_years"])]
        findings.append(finding(
            "Placeholder or 'coming soon' content is still published",
            "medium" if aged else "low",
            f"{len(coming)} page(s) contain placeholder language "
            f"({', '.join(sorted({m for p in coming for m in p['facts']['coming_soon']})[:4])})"
            + (f", of which {len(aged)} also carry a date a year or more old" if aged else "") +
            ". Examples: " + ", ".join(p["url"] for p in coming[:3]) + ".",
            "Placeholder text that has outlived its promise is a direct contradiction of the "
            "site's own currency, and it is exactly the sort of low-value passage that gets "
            "quoted back at a brand when an assistant summarises the page.",
            "Publish the real content or remove the placeholder page; keep 'coming soon' only "
            "where a specific date is stated.",
            "medium" if aged else "low", evidence_tier="correlational"))

    # --- Cross-page fact contradictions ------------------------------------
    # NB: severity is deliberately restrained and the wording is a verification
    # prompt rather than an accusation. A large or multi-site organisation
    # legitimately publishes several departmental contacts -- during testing a
    # space agency's three separate press/partnership addresses were flagged as
    # a contradiction, which they are not. What this check can honestly detect
    # is "several distinct values exist"; only a human can say whether that is
    # by design or a stale duplicate.
    for key, label, plural, sev in (("phones", "phone number", "phone numbers", "medium"),
                                    ("emails", "email address", "email addresses", "low")):
        values = {}
        for p in pages:
            for v in set(p["facts"].get(key, [])):
                norm = re.sub(r"\D", "", v)[-10:] if key == "phones" else v.lower()
                if norm:
                    values.setdefault(norm, {"raw": v, "urls": set()})["urls"].add(p["url"])
        if len(values) > 1:
            detail = "; ".join(f"{d['raw']} on {len(d['urls'])} page(s)" for d in list(values.values())[:4])
            findings.append(finding(
                f"Multiple distinct {plural} published across the site",
                sev,
                f"{len(values)} distinct {plural} found across {len(pages)} sampled pages: {detail}. "
                "This may be legitimate (separate departments or locations) or may be stale "
                "duplicates -- the audit cannot tell which, so this is a verification prompt.",
                "Internal consistency measured a citation advantage (OR 1.7-4.1). Where two values "
                "genuinely compete for the same role, neither a visitor nor a machine can tell "
                "which is current, so the fact becomes unusable and the source less trustworthy. "
                "Where they belong to different departments, this is fine and no action is needed.",
                f"Confirm each {label} is intentional and current. If any is a stale duplicate of "
                f"another, consolidate to one canonical {label} served from a single template "
                "include so it cannot drift again.", sev))

    prices = {}
    for p in pages:
        for v in set(p["facts"].get("prices", [])):
            prices.setdefault(v, set()).add(p["url"])
    if len(prices) > 6:
        findings.append(finding(
            "Many distinct price points across sampled pages",
            "low",
            f"{len(prices)} distinct price strings found across {len(pages)} pages "
            f"(e.g. {sorted(prices)[:5]}).",
            "Not a defect on its own -- a real catalogue has many prices. Flagged so a human can "
            "confirm the same item is not quoted at different prices in different places, which "
            "is the contradiction case that does damage.",
            "Spot-check that any single product or plan shows one consistent price everywhere it "
            "appears.", "low", evidence_tier="speculative"))

    # --- On-site corroboration signals -------------------------------------
    ext_hits, press = set(), False
    for p in pages:
        for href, _ in p.get("links_external", []):
            for d in CORROBORATION_DOMAINS:
                if d in href:
                    ext_hits.add(d)
        if PRESS_RE.search(p.get("text_sample", "")):
            press = True
    if not ext_hits and not press:
        findings.append(finding(
            "No third-party corroboration signals anywhere on the site",
            "medium",
            f"Across {len(pages)} sampled pages there are no outbound links to independent "
            f"reference or review sources ({', '.join(CORROBORATION_DOMAINS[:6])}...) and no "
            "press-mention language.",
            "Only a small share of AI citations point at a brand's own domain -- the large "
            "majority point at third-party pages discussing it. A brand whose claims appear "
            "nowhere but its own site has nothing for an assistant to corroborate against, and "
            "self-assertion alone is weak evidence.",
            "Build and then reference independent presence: a Wikidata item, an accurate LinkedIn "
            "and Crunchbase profile, listings on the review platforms your category uses, and "
            "coverage in real publications.", "medium", evidence_tier="correlational",
            how="Getting included in credible third-party comparison and 'best of' roundups is "
                "unusually high-leverage: ranked listicles account for the single largest share "
                "of content citations in AI answers."))

    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--today", help="ISO date to treat as today (recommended: the agent's real "
                                    "current date, since sandbox clocks are often wrong)")
    args = ap.parse_args()
    if not os.path.exists(args.evidence):
        print(f"error: evidence file not found: {args.evidence}", file=sys.stderr)
        sys.exit(2)
    today = datetime.now(timezone.utc)
    if args.today:
        try:
            today = datetime.strptime(args.today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"warning: bad --today {args.today!r}, using system clock", file=sys.stderr)
    with open(args.evidence, encoding="utf-8") as fh:
        bundle = json.load(fh)
    json.dump({"skill": SKILL, "site": bundle.get("site"), "findings": analyze(bundle, today)},
              sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
