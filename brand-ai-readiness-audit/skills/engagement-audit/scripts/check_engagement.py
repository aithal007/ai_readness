#!/usr/bin/env python3
"""engagement-audit checks.

Checks the on-site half of the problem: once a visitor (human or an agent
browsing on a human's behalf) actually lands on the page, does the site
help them orient, find their way around, trust it, and act -- or does it
lose them. These are mechanical/structural checks; the qualitative
orientation/value-proposition judgment is done by the agent per this
skill's SKILL.md, not by this script.

Usage: python3 check_engagement.py <url>
Prints a JSON object {"skill": ..., "site": ..., "findings": [...]} to stdout.
"""
import json
import re
import sys
from urllib.parse import urlparse

import page_parser as pp

CTA_WORDS = re.compile(
    r"\b(buy now|shop now|add to cart|get started|start free|sign up|book (?:a )?demo|"
    r"request a demo|contact us|try (?:it )?free|subscribe|learn more|download|book now)\b", re.I
)


def finding(title, severity, evidence, mechanism, action_summary, action_priority, how=None):
    sa = {"summary": action_summary, "priority": action_priority}
    if how:
        sa["how"] = how
    return {"title": title, "severity": severity, "category": "engagement",
            "evidence": evidence, "mechanism": mechanism, "suggested_action": sa}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"skill": "engagement-audit", "site": None, "findings": []}))
        return

    findings = []
    base_url, home = pp.resolve_base_url(sys.argv[1])
    if not home or home["status"] is None or home["status"] >= 400:
        findings.append(finding(
            "Could not fetch homepage to audit engagement", "medium",
            f"GET {base_url} -> status={home['status'] if home else None}.",
            "No engagement checks could run without a successful homepage fetch.",
            "Re-run once the homepage is reachable.", "medium",
        ))
        print(json.dumps({"skill": "engagement-audit", "site": base_url, "findings": findings}))
        return

    html = home["text"] or ""
    page = pp.parse(html)

    if urlparse(home["url"]).scheme != "https":
        findings.append(finding(
            "Site is not served over HTTPS",
            "critical",
            f"Final resolved URL was {home['url']}.",
            "Browsers actively warn visitors off non-HTTPS sites, and most AI browse/fetch tools "
            "refuse or downgrade insecure requests -- this blocks both human trust and machine access.",
            "Serve the site over HTTPS with a valid certificate and redirect all HTTP traffic to HTTPS.",
            "critical",
        ))

    if not page.viewport:
        findings.append(finding(
            "No mobile viewport meta tag",
            "high",
            f"No <meta name=\"viewport\"> found on {base_url}.",
            "Without it, mobile browsers render the desktop layout zoomed out, which reliably drives "
            "mobile visitors to bounce immediately.",
            'Add <meta name="viewport" content="width=device-width, initial-scale=1">.',
            "high",
        ))

    h1_count = sum(1 for lvl, _ in page.headings if lvl == 1)
    if h1_count == 0:
        findings.append(finding(
            "No <h1> on the homepage", "medium", f"0 <h1> elements found on {base_url}.",
            "A missing top-level heading removes the clearest structural cue for what the page is about, "
            "for both visitors scanning quickly and any system parsing the page's outline.",
            "Add exactly one <h1> stating the core value proposition.", "medium",
        ))
    elif h1_count > 1:
        findings.append(finding(
            "Multiple <h1> elements on the homepage", "low", f"{h1_count} <h1> elements found on {base_url}.",
            "Multiple competing top-level headings dilute the page's structural signal of its single main topic.",
            "Reduce to a single <h1>; demote the others to <h2> or lower.", "low",
        ))

    levels = [lvl for lvl, _ in page.headings]
    skipped = any(b - a > 1 for a, b in zip(levels, levels[1:]) if b > a)
    if skipped:
        findings.append(finding(
            "Heading levels skip a level (e.g. h1 straight to h3)", "low",
            f"Heading sequence found: {levels}.",
            "Skipped heading levels break the implied outline of the page, making it harder to parse "
            "structure for screen readers and any system building a page outline.",
            "Use headings in strict, non-skipping order (h1 -> h2 -> h3, ...).", "low",
        ))

    content_images = [im for im in page.images if (im.get("src") or "")]
    with_alt = [im for im in content_images if (im.get("alt") or "").strip()]
    if content_images:
        coverage = len(with_alt) / len(content_images)
        if coverage < 0.5:
            findings.append(finding(
                "Most images have no alt text", "medium",
                f"{len(with_alt)}/{len(content_images)} images ({coverage:.0%}) have non-empty alt text on {base_url}.",
                "Alt text is the plain-text stand-in for image content -- without it, any fact conveyed "
                "only through an image (a diagram, an infographic, a screenshot of pricing) is invisible "
                "to screen readers and to any system that only reads text.",
                "Add descriptive alt text to all meaningful images; use alt=\"\" only for purely decorative ones.",
                "medium",
            ))

    if not page.has_nav and len(page.links) > 15:
        findings.append(finding(
            "No semantic <nav> landmark despite many links", "low",
            f"{len(page.links)} links found on {base_url} but no <nav> element.",
            "A <nav> landmark helps both assistive technology and content-parsing systems distinguish "
            "primary navigation from body content and footer boilerplate.",
            "Wrap the primary navigation menu in a <nav> element.", "low",
        ))

    if not page.forms_search and len(page.links) > 40:
        findings.append(finding(
            "No on-site search despite a large link surface", "medium",
            f"{len(page.links)} links found on {base_url} with no search input/role detected.",
            "Sites this large are hard to orient in via navigation alone; visitors with a specific task "
            "in mind (and agents browsing on their behalf) will bounce rather than dig through menus.",
            "Add a visible on-site search box, ideally with autocomplete over key content types.",
            "medium",
        ))

    if not CTA_WORDS.search(html):
        findings.append(finding(
            "No clear primary call-to-action detected on the homepage", "medium",
            f"No CTA-style wording (e.g. 'Get started', 'Contact us', 'Buy now') found in {base_url}.",
            "Without an obvious next action, an arriving visitor has to work out for themselves what "
            "they're supposed to do, which measurably increases bounce.",
            "Add one unambiguous primary CTA above the fold stating the single most important next action.",
            "medium",
        ))

    blocking = [s for s in page.scripts if s["head"] and not s["async_defer"] and s.get("src")]
    if len(blocking) > 4:
        findings.append(finding(
            "Multiple render-blocking scripts in <head>", "medium",
            f"{len(blocking)} external <script> tags in <head> without async/defer on {base_url}.",
            "Render-blocking scripts delay first paint; slow-loading pages measurably lose visitors "
            "before they see any content at all.",
            "Add async/defer to non-critical head scripts, or move them to just before </body>.",
            "medium",
        ))

    print(json.dumps({"skill": "engagement-audit", "site": base_url, "findings": findings}))


if __name__ == "__main__":
    main()
