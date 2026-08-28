#!/usr/bin/env python3
"""freshness-corroboration-audit checks.

Two families of check: (1) is content stale or internally inconsistent
(different pages on the same site stating different values for the same
fact), and (2) are there visible on-site signals of external corroboration
(press, reviews, canonical profiles) -- systems trust a fact more when it's
repeated consistently across independent sources, and this script can only
check the on-site half of that; the off-site half (searching other domains)
is done by the agent per this skill's SKILL.md, not by this script.

Usage: python3 check_freshness.py <url> [--today YYYY-MM-DD]
Prints a JSON object {"skill": ..., "site": ..., "findings": [...]} to stdout.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone

import page_parser as pp

YEAR_RE = re.compile(r"(?:©|copyright)\D{0,12}((?:19|20)\d{2})", re.I)
PHONE_RE = re.compile(r"(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
PRICE_RE = re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d{2})?")
UPDATED_RE = re.compile(r"(?:last updated|updated on|updated)\D{0,6}((?:19|20)\d{2})", re.I)
CORROBORATION_DOMAINS = ["g2.com", "trustpilot.com", "capterra.com", "wikipedia.org", "wikidata.org",
                          "linkedin.com", "github.com", "youtube.com", "crunchbase.com", "bbb.org"]
PRESS_WORDS = re.compile(r"\b(as seen in|featured in|as featured on|in the press|press coverage)\b", re.I)


def finding(title, severity, evidence, mechanism, action_summary, action_priority, how=None):
    sa = {"summary": action_summary, "priority": action_priority}
    if how:
        sa["how"] = how
    return {"title": title, "severity": severity, "category": "discoverability",
            "evidence": evidence, "mechanism": mechanism, "suggested_action": sa}


def newest_year(text):
    years = [int(y) for y in YEAR_RE.findall(text)] + [int(y) for y in UPDATED_RE.findall(text)]
    return max(years) if years else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--today", default=None)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    if args.today:
        try:
            now = datetime.strptime(args.today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    findings = []
    base_url, home = pp.resolve_base_url(args.url)
    if not home or home["status"] is None or home["status"] >= 400:
        findings.append(finding(
            "Could not fetch homepage to audit freshness", "medium",
            f"GET {base_url} -> status={home['status'] if home else None}.",
            "No freshness/corroboration checks could run without a successful homepage fetch.",
            "Re-run once the homepage is reachable.", "medium",
        ))
        print(json.dumps({"skill": "freshness-corroboration-audit", "site": base_url, "findings": findings}))
        return

    html = home["text"] or ""
    page = pp.parse(html)

    year = newest_year(html)
    if year is not None:
        age = now.year - year
        if age >= 2:
            findings.append(finding(
                "Stale copyright/last-updated year on the homepage",
                "high" if age >= 3 else "medium",
                f"Most recent year found near a copyright/'updated' marker on {base_url} is {year} "
                f"({age} year(s) old, checked against {now.date().isoformat()}).",
                "A visibly stale date is a low-effort, high-signal cue -- both to human visitors and to "
                "systems weighing freshness -- that the page may not reflect current facts.",
                "Update the footer/copyright year (ideally auto-generated) and, if the page content "
                "genuinely hasn't changed, add a visible 'last reviewed' date to signal it was still checked.",
                "high" if age >= 3 else "medium",
            ))

    ld_dates = []
    for raw in page.ld_json_raw:
        for key in ("dateModified", "datePublished"):
            m = re.search(key + r'"\s*:\s*"([^"]+)"', raw)
            if m:
                ld_dates.append((key, m.group(1)))
    stale_ld = []
    for key, val in ld_dates:
        try:
            d = datetime.fromisoformat(val.replace("Z", "+00:00"))
            if (now - d).days > 545:
                stale_ld.append((key, val))
        except ValueError:
            continue
    if stale_ld:
        findings.append(finding(
            "JSON-LD date fields are over 18 months old",
            "medium",
            "; ".join(f"{k}={v}" for k, v in stale_ld) + f" on {base_url}.",
            "dateModified/datePublished are read directly by systems that reason about content freshness; "
            "a stale value undersells content that may actually be current, or correctly flags stale content.",
            "Update dateModified whenever the page's substance changes; don't let it silently go stale.",
            "medium",
        ))

    # Internal consistency: phone numbers and prices should agree across pages of the same site.
    sample_urls = [base_url] + pp.same_domain_links(base_url, page.links, limit=4)
    facts = {"phone": {}, "price": {}}
    corroboration_hits = set()
    press_seen = False
    blog_like_found = False
    broken = []
    for u in sample_urls:
        r = home if u == base_url else pp.fetch(u)
        if r["status"] is None or r["status"] >= 400:
            if u != base_url:
                broken.append((u, r["status"]))
            continue
        text = r["text"] or ""
        sub = pp.parse(text) if u != base_url else page
        for ph in set(PHONE_RE.findall(sub.body_text)):
            facts["phone"].setdefault(ph, set()).add(u)
        for pr in set(PRICE_RE.findall(sub.body_text)):
            facts["price"].setdefault(pr, set()).add(u)
        for href, _ in sub.links:
            for dom in CORROBORATION_DOMAINS:
                if dom in href:
                    corroboration_hits.add(dom)
        if PRESS_WORDS.search(text):
            press_seen = True
        if re.search(r"/blog/|/news/", u):
            blog_like_found = True

    if broken:
        # Title matches crawl-render-audit's broken-link finding exactly (same
        # underlying phenomenon, independently sampled) so audit-orchestrator's
        # (title, category) de-dup in finalize_report.py collapses the two
        # into one finding instead of reporting the same broken links twice.
        findings.append(finding(
            "Broken links encountered while sampling internal pages",
            "medium",
            "; ".join(f"{u} -> {code}" for u, code in broken),
            "Dead links are a direct staleness signal and erode trust for both visitors and crawlers.",
            "Fix or remove the broken links listed in evidence.",
            "medium",
        ))

    if len(facts["phone"]) > 1:
        detail = "; ".join(f"{num} on {sorted(urls)}" for num, urls in list(facts["phone"].items())[:4])
        findings.append(finding(
            "Inconsistent phone numbers across pages of the same site",
            "high",
            detail,
            "When the same fact type appears with different values on different pages of the same "
            "domain, it directly undermines self-corroboration -- a system (or visitor) has no way to "
            "know which value is correct, and may pick the wrong one or discount the site's reliability.",
            "Establish one canonical phone number (ideally sourced from a single CMS field/include) and "
            "audit all pages for the stale alternates found in evidence.",
            "high",
        ))

    if not corroboration_hits and not press_seen:
        findings.append(finding(
            "No visible third-party corroboration signals on-site",
            "low",
            f"Sampled {len(sample_urls)} page(s) on {base_url}; found no outbound links to "
            f"{', '.join(CORROBORATION_DOMAINS)} and no 'as seen in' / press-mention wording.",
            "Facts repeated consistently across independent sources are trusted more than facts that "
            "live in only one place; a site with zero visible links to reviews, press, or canonical "
            "profiles gives assistants nothing to corroborate it against.",
            "Add a visible press/reviews section linking to independent coverage, review platforms "
            "(G2/Trustpilot/Capterra as relevant), and the brand's canonical Wikipedia/LinkedIn/Crunchbase "
            "profiles where they exist. (The agent running this audit should also independently web-search "
            "the brand name per this skill's SKILL.md to check off-site agreement, which this script cannot do.)",
            "low",
        ))

    if not blog_like_found:
        findings.append(finding(
            "No discoverable blog/news section",
            "low",
            f"None of the sampled links from {base_url} matched a /blog/ or /news/ pattern.",
            "A visible cadence of dated updates is one of the more reliable freshness signals a site can "
            "offer; its absence isn't necessarily wrong for every site type, but it's worth a deliberate check.",
            "If there is content marketing / product-update value in doing so, add a dated blog or "
            "changelog section; skip this if the site type genuinely doesn't need one.",
            "low",
        ))

    print(json.dumps({"skill": "freshness-corroboration-audit", "site": base_url, "findings": findings}))


if __name__ == "__main__":
    main()
