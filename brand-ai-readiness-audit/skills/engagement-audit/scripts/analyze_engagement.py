#!/usr/bin/env python3
"""engagement-audit: once a visitor arrives, can they orient, act, and get where
they were going?

Discoverability wins the click. This skill covers what happens after it.

The distinctive check here is GOAL-PATH REACHABILITY: rather than only scoring
isolated page attributes, it walks the crawled link graph and measures how many
clicks from the homepage it takes to reach the things visitors actually come
for -- contact, pricing, product/service detail, support. A goal that is
unreachable in the crawl is one a visitor has to hunt for, and an agent
browsing on their behalf usually gives up sooner than a human does.

Usage: python3 analyze_engagement.py --evidence evidence.json
"""
import argparse
import json
import os
import re
import sys
from collections import deque
from urllib.parse import urlparse

SKILL = "engagement-audit"

GOALS = {
    "contact": re.compile(r"/(contact|get-in-touch|reach-us|support|help)\b|contact", re.I),
    "pricing": re.compile(r"/(pricing|plans|price|rates|fees|tuition)\b|pricing|plans", re.I),
    "about": re.compile(r"/(about|who-we-are|our-story|company|team)\b|about", re.I),
    "offering": re.compile(r"/(product|products|services|solutions|shop|store|courses|programs)\b",
                           re.I),
}


def finding(title, severity, evidence, mechanism, action, priority,
            evidence_tier="correlational", how=None, page=None):
    sa = {"summary": action, "priority": priority}
    if how:
        sa["how"] = how
    f = {"title": title, "severity": severity, "category": "engagement",
         "evidence": evidence, "mechanism": mechanism, "suggested_action": sa,
         "signal_tier": 1, "evidence_tier": evidence_tier, "source_skill": SKILL}
    if page:
        f["page"] = page
    return f


def click_depths(bundle):
    """BFS the crawled link graph from the homepage, returning url -> depth."""
    graph = bundle.get("link_graph", {})
    start = bundle.get("site")
    if start not in graph:
        start = next(iter(graph), None)
    depths = {}
    if not start:
        return depths
    q = deque([(start, 0)])
    depths[start] = 0
    while q:
        url, d = q.popleft()
        for nxt in graph.get(url, []):
            if nxt not in depths:
                depths[nxt] = d + 1
                q.append((nxt, d + 1))
    return depths


def analyze(bundle):
    findings = []
    pages = bundle.get("pages", [])
    if not pages:
        return findings
    home = pages[0]

    # --- Trust and access basics -------------------------------------------
    if not home.get("https", True):
        findings.append(finding(
            "Site is not served over HTTPS", "critical",
            f"Final resolved URL was {home.get('final_url')}.",
            "Browsers display an active security warning on non-HTTPS pages, which drives "
            "immediate abandonment, and many automated fetchers refuse or downgrade insecure "
            "requests -- so this damages human trust and machine access at the same time.",
            "Serve the whole site over HTTPS with a valid certificate and redirect all HTTP "
            "traffic to it.", "critical", evidence_tier="measured"))

    noviewport = [p for p in pages if not p.get("viewport")]
    if noviewport:
        findings.append(finding(
            "No mobile viewport declaration", "high",
            f"{len(noviewport)}/{len(pages)} sampled pages have no viewport meta tag "
            f"(e.g. {noviewport[0]['url']}).",
            "Without it, mobile browsers render the desktop layout scaled down, so text is "
            "unreadable without pinch-zoom. On mobile traffic this reliably drives immediate "
            "bounces before any content is read.",
            'Add <meta name="viewport" content="width=device-width, initial-scale=1"> to every '
            "page.", "high", evidence_tier="measured"))

    # --- Goal-path reachability --------------------------------------------
    depths = click_depths(bundle)
    reachable_urls = set(depths)
    home_links = " ".join(t for _, t in home.get("links_internal", [])) + " " + \
                 " ".join(h for h, _ in home.get("links_internal", []))
    missing_goals, deep_goals = [], []
    for goal, rx in GOALS.items():
        hits = [(u, d) for u, d in depths.items() if rx.search(u)]
        if not hits:
            if not rx.search(home_links):
                missing_goals.append(goal)
        else:
            best = min(d for _, d in hits)
            if best > 3:
                deep_goals.append((goal, best))

    if missing_goals:
        findings.append(finding(
            "Common visitor goals have no reachable page",
            "high" if "contact" in missing_goals else "medium",
            f"No page or homepage link matching these goals was found in the crawl: "
            f"{', '.join(missing_goals)}. Crawl reached {len(reachable_urls)} internal URL(s) "
            f"from the homepage.",
            "These are the destinations visitors arrive looking for. If a goal has no discoverable "
            "path from the homepage, the visitor must guess a URL or leave -- and an assistant "
            "browsing on their behalf will simply report that it could not find the information.",
            "Add clear, crawlable navigation links to each missing destination, using plain "
            "labels ('Contact', 'Pricing') rather than icons or JavaScript-only menus.",
            "high" if "contact" in missing_goals else "medium",
            how="If these pages do exist, the problem is that they are not linked in crawlable "
                "HTML -- check whether the navigation is rendered client-side."))

    if deep_goals:
        findings.append(finding(
            "Key destinations are buried several clicks deep",
            "medium",
            "; ".join(f"{g}: shortest path {d} clicks from the homepage" for g, d in deep_goals),
            "Every additional click between arrival and the intended destination sheds visitors. "
            "Depth also correlates with crawl priority, so buried pages are both harder for people "
            "to reach and less likely to be indexed.",
            "Link these destinations from the primary navigation or the homepage so they sit "
            "within two clicks.", "medium"))

    # --- Orientation --------------------------------------------------------
    h1s = [h for h in home.get("headings", []) if h[0] == 1]
    if not h1s:
        findings.append(finding(
            "Homepage has no H1", "medium",
            f"No H1 element found on {home['url']}.",
            "The H1 is the clearest single statement of what a page is -- for a scanning visitor, "
            "for assistive technology, and for any system building a page outline.",
            "Add exactly one H1 stating plainly what the organisation does.", "medium",
            evidence_tier="measured"))

    if not home.get("meta_description") and not h1s:
        findings.append(finding(
            "Homepage states no value proposition in extractable text", "high",
            f"{home['url']} has neither an H1 nor a meta description, and exposes "
            f"{home['citability']['word_count']} words of extracted text.",
            "A first-time visitor has nothing telling them what this is or whether they are in the "
            "right place, and neither does any machine reading the page.",
            "State in one sentence, near the top of the homepage, what the organisation does and "
            "who it is for.", "high"))

    # --- Interaction affordances -------------------------------------------
    total_links = len(home.get("links_internal", []))
    has_search = any(p.get("forms", {}).get("search") for p in pages)
    if not has_search and total_links > 40:
        findings.append(finding(
            "No on-site search on a large site", "medium",
            f"Homepage exposes {total_links} internal links and no search input was detected on "
            f"any of the {len(pages)} sampled pages.",
            "Past a certain size, browsing stops working and visitors arrive with a specific "
            "question. Without search they must navigate a hierarchy someone else designed.",
            "Add a visible site search field in the header.", "medium"))

    no_cta = [p for p in pages if not p.get("facts", {}).get("cta_matches")
              and p["citability"]["word_count"] > 150]
    if len(no_cta) >= max(2, len(pages) // 2):
        findings.append(finding(
            "Most substantive pages offer no clear next action", "medium",
            f"{len(no_cta)}/{len(pages)} sampled pages with over 150 words contain no "
            "call-to-action phrasing.",
            "A page that informs but does not offer a next step leaves the visitor to invent one, "
            "which most will not do. This is where discoverability gains leak away.",
            "Give each substantive page one obvious next action appropriate to its intent.",
            "medium"))

    dead_ends = [p["url"] for p in pages
                 if len(p.get("links_internal", [])) <= 1 and p["citability"]["word_count"] > 150]
    if dead_ends:
        findings.append(finding(
            "Dead-end pages with no onward navigation", "low",
            f"{len(dead_ends)} substantive page(s) contain at most one internal link: "
            f"{', '.join(dead_ends[:3])}.",
            "A page with nowhere to go next ends the session. It also traps crawlers, since link "
            "structure is how they discover the rest of the site.",
            "Add contextual links onward from these pages to related content and the primary "
            "navigation.", "low"))

    # --- Readability of the interface --------------------------------------
    imgs = sum(p.get("images_total", 0) for p in pages)
    noalt = sum(p.get("images_missing_alt", 0) for p in pages)
    if imgs >= 8 and noalt / imgs > 0.5:
        findings.append(finding(
            "Most images have no alt text", "medium",
            f"{noalt}/{imgs} images across sampled pages have empty or missing alt attributes.",
            "Alt text is the text stand-in for an image. Without it, any information carried "
            "visually is unavailable to screen-reader users and to text extraction alike. Note "
            "that purely decorative icons legitimately use empty alt, so treat this as a prompt "
            "to review rather than proof that every instance is wrong.",
            "Add descriptive alt text to images that carry meaning; keep alt=\"\" for purely "
            "decorative ones.", "medium", evidence_tier="measured"))

    blocking = max((p["scripts"]["head_blocking"] for p in pages), default=0)
    if blocking > 4:
        findings.append(finding(
            "Render-blocking scripts delay first paint", "medium",
            f"Up to {blocking} synchronous external scripts load in <head> without async or defer.",
            "Each blocking script postpones the moment anything appears on screen. Abandonment "
            "rises sharply with load time, and the visitors lost this way leave before seeing any "
            "content at all.",
            "Add async or defer to non-critical head scripts, or move them before </body>.",
            "medium", evidence_tier="measured"))

    unlabeled = sum(max(0, p.get("forms", {}).get("inputs", 0) - p.get("forms", {}).get("labeled", 0))
                    for p in pages)
    if unlabeled >= 3:
        findings.append(finding(
            "Form fields without accessible labels", "low",
            f"{unlabeled} input field(s) across sampled pages have no label, aria-label, title or "
            "placeholder.",
            "Unlabelled fields are ambiguous for every visitor and unusable with a screen reader, "
            "and forms are usually the last step before a conversion.",
            "Give every input a visible <label> (placeholders alone are not labels).", "low",
            evidence_tier="measured"))

    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evidence", required=True)
    args = ap.parse_args()
    if not os.path.exists(args.evidence):
        print(f"error: evidence file not found: {args.evidence}", file=sys.stderr)
        sys.exit(2)
    with open(args.evidence, encoding="utf-8") as fh:
        bundle = json.load(fh)
    json.dump({"skill": SKILL, "site": bundle.get("site"), "findings": analyze(bundle)},
              sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
