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
# "contact" and "about" apply to every organisation. "pricing" and "offering"
# only make sense where the site actually sells or lists something -- flagging
# them missing on a language project or a charity is a category error, not a
# finding.
UNIVERSAL_GOALS = {"contact", "about"}
COMMERCIAL_CTA = {"buy now", "shop now", "add to cart", "get a quote", "book now",
                  "start free", "book a demo", "request a demo", "schedule a call"}
COMMERCIAL_SD = ("product", "offer", "service", "pricespecification", "aggregateoffer")
COMMERCIAL_PATH_RE = re.compile(
    r"/(pricing|plans|shop|store|cart|checkout|product|products)\b|/product/", re.I)


def is_commercial(bundle):
    """True when the site plainly sells or lists an offering.

    Stray currency figures (grant amounts, salaries, case-study numbers) are not
    commerce, so a couple of '$' strings do not count. What counts: a real
    purchase CTA, Product/Offer structured data, a pricing/shop URL anywhere in
    the link graph (even if that page was not crawled -- a JS-priced SaaS often
    is not), or prices on a large share of pages (the shape of a catalogue)."""
    pages = bundle.get("pages", [])
    # A pricing/shop URL known to the site, crawled or not.
    graph = bundle.get("link_graph", {}) or {}
    known = list(graph.keys()) + [u for v in graph.values() for u in (v or [])]
    if any(COMMERCIAL_PATH_RE.search(u or "") for u in known):
        return True
    priced_pages = 0
    for p in pages:
        f = p.get("facts", {})
        if set(f.get("cta_matches", [])) & COMMERCIAL_CTA:
            return True
        types = " ".join(str(t).lower() for t in p.get("jsonld_types", []))
        if any(t in types for t in COMMERCIAL_SD):
            return True
        if COMMERCIAL_PATH_RE.search(p.get("url", "")):
            return True
        if f.get("prices"):
            priced_pages += 1
    return priced_pages >= max(3, round(0.4 * len(pages)))


def finding(title, severity, evidence, mechanism, action, priority,
            evidence_tier="correlational", how=None, page=None, status=None):
    sa = {"summary": action, "priority": priority}
    if how:
        sa["how"] = how
    f = {"title": title, "severity": severity, "category": "engagement",
         "evidence": evidence, "mechanism": mechanism, "suggested_action": sa,
         "signal_tier": 1, "evidence_tier": evidence_tier, "source_skill": SKILL}
    if page:
        f["page"] = page
    if status:
        f["status"] = status
    return f


PURCHASE_CTA = {"add to cart", "add to bag", "add to basket", "buy now", "proceed to checkout"}
SHIPPING_RE = re.compile(r"\b(shipping|delivery|returns?|refund|exchange)\b", re.I)
BYLINE_RE = re.compile(r"\b(by [A-Z][a-z]+|author|written by|posted by)\b")
HOURS_RE = re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?\s*[-–—to]*\s*"
                      r"(?:(mon|tue|wed|thu|fri|sat|sun)[a-z]*)?\s*:?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)|"
                      r"\b(opening hours|hours of operation|business hours)\b", re.I)


def type_specific(bundle, commercial):
    """Checks that only make sense for a particular kind of site.

    Type comes from evidence, never a site list. Each check is gated so that a
    site of a different type simply never sees it -- silence, not a false
    finding.
    """
    out = []
    pages = bundle.get("pages", [])
    if not pages:
        return out
    types = set()
    for p in pages:
        types.update(p.get("jsonld_types", []))
    blob = " ".join(p.get("text_sample", "") for p in pages)

    # --- Shop: priced pages a visitor cannot actually buy from --------------
    if commercial:
        priced = [p for p in pages if p.get("facts", {}).get("prices")]
        buyable = [p for p in priced
                   if set(p.get("facts", {}).get("cta_matches", [])) & PURCHASE_CTA]
        if len(priced) >= 3 and not buyable:
            out.append(finding(
                "Priced pages offer no visible way to buy", "medium",
                f"{len(priced)} sampled page(s) show a price but none carries a purchase action "
                f"(add to cart / buy now). Examples: "
                f"{', '.join(p['url'] for p in priced[:3])}.",
                "A price with no adjacent action makes the visitor hunt for the next step, and an "
                "assistant summarising the page cannot tell a shopper how to proceed. If checkout "
                "is rendered client-side, it is invisible to both.",
                "Put an explicit purchase or enquiry action in the page markup next to each "
                "price, server-rendered rather than injected by script.", "medium",
                evidence_tier="correlational"))
        if priced and not SHIPPING_RE.search(blob):
            out.append(finding(
                "No shipping or returns information found", "medium",
                f"{len(priced)} page(s) show prices, but no shipping, delivery or returns "
                f"vocabulary appears anywhere in {len(pages)} sampled page(s).",
                "Shipping cost and return terms are among the first things a buyer -- and an "
                "assistant answering on a buyer's behalf -- looks for. Their absence stalls the "
                "decision at exactly the point of intent.",
                "Publish shipping and returns terms as plain text and link them from product and "
                "checkout pages.", "medium", evidence_tier="correlational"))

    # --- Publisher: articles with no byline or date -------------------------
    article_pages = [p for p in pages
                     if {"Article", "BlogPosting", "NewsArticle"} & set(p.get("jsonld_types", []))
                     or re.search(r"/(blog|news|article|posts?)/", p.get("url", ""))]
    if len(article_pages) >= 3:
        undated = [p for p in article_pages
                   if not p.get("jsonld_dates") and not p.get("facts", {}).get("updated_years")]
        if len(undated) >= max(2, len(article_pages) // 2):
            out.append(finding(
                "Articles are published without a visible date", "medium",
                f"{len(undated)}/{len(article_pages)} article-shaped pages expose no publication "
                "or update date in text or structured data.",
                "Readers judge an article's relevance by its date before they read it, and "
                "answer engines treat recency as a gate on whether to cite at all. An undated "
                "article is assumed stale.",
                "Show a publication date on every article and mirror it in datePublished / "
                "dateModified.", "medium", evidence_tier="measured"))
        if not BYLINE_RE.search(blob):
            out.append(finding(
                "Articles carry no visible author attribution", "low",
                f"{len(article_pages)} article-shaped page(s) sampled, with no byline or author "
                "vocabulary found in their text.",
                "Named authorship is a core credibility signal for editorial content -- it is how "
                "a reader, and a system weighing sources, tells a considered piece from anonymous "
                "filler.",
                "Attribute articles to a named author with a linked profile, and mark it up with "
                "the author property.", "low", evidence_tier="correlational"))

    # --- Local business: no opening hours anywhere --------------------------
    local = {"LocalBusiness", "Restaurant", "Store", "Hotel", "MedicalBusiness",
             "Dentist", "LodgingBusiness"} & types
    if local and not HOURS_RE.search(blob) and "OpeningHoursSpecification" not in types:
        out.append(finding(
            "A local business publishes no opening hours", "high",
            f"The site declares {sorted(local)} structured data but no opening hours appear in "
            f"text or as OpeningHoursSpecification across {len(pages)} sampled page(s).",
            "Opening hours are the single most asked question about a local business. If they are "
            "not in extractable text, an assistant asked 'are they open now?' cannot answer, and "
            "a visitor may simply go elsewhere.",
            "Publish opening hours as plain text on the homepage and contact page, and mirror "
            "them in OpeningHoursSpecification.", "high", evidence_tier="measured"))

    return out


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
    commercial = is_commercial(bundle)
    missing_goals, deep_goals, na_goals = [], [], []
    for goal, rx in GOALS.items():
        applies = goal in UNIVERSAL_GOALS or commercial
        hits = [(u, d) for u, d in depths.items() if rx.search(u)]
        if not hits:
            if not rx.search(home_links):
                (missing_goals if applies else na_goals).append(goal)
        else:
            best = min(d for _, d in hits)
            if best > 3:
                deep_goals.append((goal, best))

    if na_goals:
        findings.append(finding(
            f"Visitor-goal checks not applicable: {', '.join(na_goals)}",
            "low",
            f"No {', '.join(na_goals)} destination was found, but this site shows no commercial "
            "signals (prices, purchase CTAs, Product/Offer structured data, or a pricing/shop "
            "URL), so these goals do not apply to it.",
            "The audit distinguishes 'goal missing' from 'goal not relevant to this kind of "
            "site' rather than reporting a category error.",
            "No action needed. Add pricing/offering navigation only if the site starts selling "
            "or listing an offering.", "low", evidence_tier="measured",
            status="not_applicable"))

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

    # --- Per-site-type checks -----------------------------------------------
    # The universal checks above apply everywhere. These only run once the
    # evidence says what kind of site this is, because "no add-to-cart button"
    # is a defect on a shop and a category error on a documentation site.
    findings.extend(type_specific(bundle, commercial))

    # --- Orientation and trust affordances ----------------------------------
    # Cheap, high-signal checks in the "understand / navigate / trust" band that
    # structural checks alone miss.
    nav_counts = [p.get("nav_links", 0) for p in pages if p.get("has_nav")]
    if nav_counts:
        top = max(nav_counts)
        if top > 15:
            findings.append(finding(
                "Primary navigation offers too many choices", "low",
                f"The richest <nav> across sampled pages exposes {top} links.",
                "A navigation list this long stops being a map and becomes a search problem. "
                "Visitors scan the first handful and give up; the hierarchy the site intends is "
                "not communicated.",
                "Group navigation into a small number of top-level categories, with the detail "
                "one level down.", "low", evidence_tier="correlational"))
        elif top and top < 3 and len(home.get("links_internal", [])) > 25:
            findings.append(finding(
                "Primary navigation exposes almost nothing", "low",
                f"The site's <nav> carries only {top} link(s) while the homepage links to "
                f"{len(home.get('links_internal', []))} internal pages.",
                "Content the navigation never mentions is reachable only by chance. Both visitors "
                "and crawlers use navigation as the map of what a site contains.",
                "Surface the main sections in the primary navigation.", "low",
                evidence_tier="correlational"))

    deep_pages = [p for p in pages if p.get("depth", 0) >= 2]
    if len(deep_pages) >= 3 and not any(p.get("has_breadcrumbs") for p in pages):
        findings.append(finding(
            "No breadcrumbs on a site with nested content", "low",
            f"{len(deep_pages)} sampled page(s) sit two or more clicks deep and no breadcrumb "
            "navigation (BreadcrumbList markup or a breadcrumb nav landmark) was found.",
            "Someone arriving on a deep page from a search result or an assistant's citation has "
            "no way to tell where they are in the site or how to go up a level. Breadcrumbs also "
            "state the site's hierarchy explicitly for machines.",
            "Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.",
            "low", evidence_tier="correlational"))

    all_links = [(h, t) for p in pages for h, t in p.get("links_internal", [])] + \
                [(h, t) for p in pages for h, t in p.get("links_external", [])]
    joined = " ".join(f"{h} {t}" for h, t in all_links).lower()
    has_privacy = "privacy" in joined
    has_terms = any(w in joined for w in ("terms", "conditions", "legal"))
    if not (has_privacy and has_terms):
        missing = ", ".join(w for w, ok in (("privacy policy", has_privacy),
                                            ("terms / legal", has_terms)) if not ok)
        findings.append(finding(
            "No link to a privacy policy or terms page", "low",
            f"Across {len(pages)} sampled page(s), no link was found to: {missing}.",
            "These pages are a baseline trust signal for visitors deciding whether to transact, "
            "and their absence is conspicuous on any site that collects data. They are also "
            "commonly expected by platforms and reviewers.",
            f"Publish and link {missing} from the site footer.", "low",
            evidence_tier="correlational"))

    vague = [t for _h, t in all_links
             if t.strip().lower() in ("click here", "here", "read more", "more", "link",
                                      "this", "learn more >", "continue")]
    if len(vague) >= 5:
        findings.append(finding(
            "Many links use uninformative anchor text", "low",
            f"{len(vague)} link(s) across sampled pages use generic anchor text such as "
            f"{', '.join(sorted(set(vague))[:4])}.",
            "Anchor text is how both a screen-reader user scanning links and a machine building "
            "a link graph work out what is on the other end. 'Click here' describes nothing, so "
            "the destination's topic is lost.",
            "Rewrite these links so the anchor text names the destination -- 'read the pricing "
            "guide' rather than 'click here'.", "low", evidence_tier="measured"))

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
