#!/usr/bin/env python3
"""crawl-render-audit checks.

Verifies the first, sequential precondition for AI discoverability: the
crawler can get in (robots.txt / index directives), can read the page
(status codes, redirects), and the page's real content exists as plain
text rather than only appearing after client-side JavaScript runs (most
AI crawlers -- GPTBot, ClaudeBot, PerplexityBot, etc. -- fetch raw HTML
and do not execute JavaScript).

Usage: python3 check_crawl_render.py <url>
Prints a JSON object {"skill": ..., "site": ..., "findings": [...]} to stdout.
Never raises: fetch/parse failures become findings, not crashes.
"""
import json
import re
import sys

import page_parser as pp

LOGIN_WALL_PATTERNS = [
    r"sign in to (?:continue|view|read)", r"log in to (?:continue|view|read)",
    r"subscribe to (?:continue|read|view)", r"become a member to (?:continue|read)",
    r"create a free account to continue",
]

SPA_ROOT_PATTERN = re.compile(
    r'id=["\'](root|app|__next|__nuxt|app-root|react-root|ng-app)["\']', re.I
)


def finding(title, severity, evidence, mechanism, action_summary, action_priority, how=None):
    sa = {"summary": action_summary, "priority": action_priority}
    if how:
        sa["how"] = how
    return {"title": title, "severity": severity, "category": "discoverability",
            "evidence": evidence, "mechanism": mechanism, "suggested_action": sa}


def check_robots(base_url, findings):
    rp, raw, status = pp.robots_check(base_url)
    if status == 200 and raw:
        blocked = [ua for ua in pp.AI_CRAWLERS if not pp.allowed(rp, base_url, ua)]
        star_blocked = not pp.allowed(rp, base_url, "*")
        if star_blocked:
            findings.append(finding(
                "robots.txt blocks all crawlers, including AI assistants, from the homepage",
                "critical",
                f"robots.txt at {base_url.rstrip('/')}/robots.txt disallows '*' for {base_url}.",
                "A blanket Disallow for '*' is honored by every well-behaved crawler, including "
                "GPTBot, ClaudeBot, and PerplexityBot -- the site cannot be found, cited, or "
                "quoted by any AI assistant that respects robots.txt while this is in place.",
                "Remove the blanket Disallow (or scope it to genuinely private paths only) so "
                "public pages are crawlable.", "critical",
            ))
        elif blocked:
            findings.append(finding(
                f"robots.txt explicitly blocks {len(blocked)} named AI crawler(s)",
                "critical" if len(blocked) >= len(pp.AI_CRAWLERS) // 2 else "high",
                f"Disallowed for: {', '.join(blocked)} (checked against {base_url}).",
                "Named AI-crawler rules override the generic '*' rule for that bot. Each blocked "
                "user-agent will not fetch this site, so answers from that assistant's search/browse "
                "feature will never cite it, regardless of how good the content is.",
                "Confirm each block is intentional. If any assistant should be able to find and cite "
                "this site, remove its Disallow rule (e.g. GPTBot, ClaudeBot, PerplexityBot, "
                "Google-Extended, OAI-SearchBot are the highest-traffic AI fetchers as of 2026).",
                "high",
            ))
    # Sitemap check (helps discovery; not fetching it counts as a miss, not a crawl of new pages)
    sitemap_declared = "sitemap:" in raw.lower() if raw else False
    # Use the site root, not base_url verbatim: if the audited URL has a path
    # (e.g. https://example.com/products/widget, or a bare .../index.html),
    # sitemap.xml still lives at the domain root, not under that path.
    sm = pp.fetch(pp.site_root(base_url) + "/sitemap.xml")
    sitemap_ok = sm["status"] == 200 and "<url" in (sm["text"] or "").lower()
    if not sitemap_ok:
        findings.append(finding(
            "No XML sitemap found at /sitemap.xml",
            "medium",
            f"GET /sitemap.xml returned status={sm['status']}" + ("" if sitemap_declared else "; robots.txt does not declare one either."),
            "A sitemap is the most reliable way for a crawler to discover the full set of pages "
            "worth indexing, especially ones with few internal links pointing to them.",
            "Publish an XML sitemap covering all public pages and reference it with a 'Sitemap:' line in robots.txt.",
            "medium",
        ))
    return rp


def check_index_directives(url, resp, page, findings, label):
    robots_header = resp["headers"].get("X-Robots-Tag", "")
    if "noindex" in robots_header.lower():
        findings.append(finding(
            f"X-Robots-Tag: noindex on {label}",
            "critical",
            f"Response header X-Robots-Tag='{robots_header}' on {url}.",
            "This header tells every compliant crawler to drop the page from its index entirely -- "
            "it will never surface in search or be cited by an AI assistant, independent of content quality.",
            "Remove the noindex directive from this response header unless the page is deliberately private.",
            "critical",
        ))
    if "noindex" in (page.robots_meta or "").lower():
        findings.append(finding(
            f"<meta name=\"robots\" content=\"noindex\"> on {label}",
            "critical",
            f"Meta robots tag content='{page.robots_meta}' found on {url}.",
            "Same effect as the header version: the page is explicitly excluded from indexing.",
            "Remove the noindex value from the robots meta tag unless the page is deliberately private.",
            "critical",
        ))


def check_render_gap(url, html, page, findings, label):
    text_len = len(page.body_text)
    script_bytes = sum(len(s.get("src") or "") for s in page.scripts) + html.count("<script")
    spa_root = bool(SPA_ROOT_PATTERN.search(html))
    many_scripts = len(page.scripts) >= 6
    if text_len < 250 and (spa_root or many_scripts):
        evidence = (f"{label}: only {text_len} characters of visible body text extracted from raw HTML, "
                    f"vs {len(page.scripts)} <script> tags" + (" and a client-rendering root element "
                    f"({SPA_ROOT_PATTERN.search(html).group(0)})" if spa_root else "") + ".")
        findings.append(finding(
            f"Content on {label} appears to require JavaScript to render",
            "high",
            evidence,
            "Most AI crawlers and browse tools fetch raw HTML and do not execute JavaScript. If the "
            "meaningful text only appears after client-side rendering, the page looks empty to them "
            "even though a human visitor sees it fine -- the facts on it cannot be extracted or cited.",
            "Server-side render (or statically pre-render / use an SSG) the primary content so it is "
            "present in the initial HTML response, or at minimum provide full-content fallback via "
            "<noscript> or a prerendering proxy for known bot user-agents.",
            "high",
            how="Verify with `curl -A GPTBot <url> | less` -- if the key facts aren't in that output, a crawler can't see them either.",
        ))
        if page.noscript_text_len < 100:
            findings.append(finding(
                f"No meaningful <noscript> fallback on {label}",
                "medium",
                f"{label}: <noscript> text totals {page.noscript_text_len} characters.",
                "A populated <noscript> block is the standard fallback for non-JS-executing readers; "
                "leaving it empty compounds the render-gap issue above.",
                "Add a concise plain-text summary of the page's key facts inside <noscript>.",
                "medium",
            ))


def check_login_wall(url, html, page, findings, label):
    low = html.lower()
    for pat in LOGIN_WALL_PATTERNS:
        if re.search(pat, low):
            findings.append(finding(
                f"Key content on {label} appears gated behind a login/paywall prompt",
                "high",
                f"Matched pattern /{pat}/ in page text on {url}; visible body text is only {len(page.body_text)} characters.",
                "Content that requires authentication to read is invisible to anonymous crawlers, so "
                "it cannot be indexed, extracted, or cited even if it's the most important content on the page.",
                "Expose a substantive, crawlable summary or the full content for anonymous/crawler "
                "requests, reserving the gate for genuinely account-specific actions.",
                "high",
            ))
            break


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"skill": "crawl-render-audit", "site": None,
                           "findings": [finding("No URL provided", "low", "Missing argv[1].",
                                                 "Script requires a target URL.", "Re-run with a URL.", "low")]}))
        return

    raw_input_url = sys.argv[1]
    findings = []
    base_url, home = pp.resolve_base_url(raw_input_url)

    if not home or home["status"] is None:
        findings.append(finding(
            "Site did not respond to a plain HTTP(S) GET",
            "critical",
            f"Fetch of {base_url} failed: {home['error'] if home else 'unknown error'}.",
            "If a basic GET fails, no crawler -- AI or otherwise -- can reach the site at all.",
            "Verify the domain resolves and the server responds to unauthenticated GET requests from external IPs.",
            "critical",
        ))
        print(json.dumps({"skill": "crawl-render-audit", "site": base_url, "findings": findings}))
        return

    if home["status"] >= 400:
        findings.append(finding(
            f"Homepage returned HTTP {home['status']}",
            "critical",
            f"GET {base_url} -> {home['status']}.",
            "An error status on the homepage blocks indexing of the entire domain by definition.",
            "Fix the homepage response so it returns 200 for anonymous requests.",
            "critical",
        ))

    html = home["text"] or ""
    page = pp.parse(html)

    rp = check_robots(base_url, findings)
    check_index_directives(base_url, home, page, findings, "the homepage")
    check_render_gap(base_url, html, page, findings, "the homepage")
    check_login_wall(base_url, html, page, findings, "the homepage")

    if not page.canonical:
        findings.append(finding(
            "No canonical link tag on the homepage",
            "low",
            f"No <link rel=\"canonical\"> found in {base_url}.",
            "Without a canonical, crawlers must guess which URL variant (with/without trailing slash, "
            "query params, http/https) is authoritative, which can split ranking/citation signal across duplicates.",
            "Add a self-referencing <link rel=\"canonical\"> to every page.",
            "low",
        ))

    # Sample a few internal pages, respecting robots.txt, to catch broken links / repeat render gaps.
    sample = pp.same_domain_links(base_url, page.links, limit=4)
    broken = []
    for u in sample:
        if not pp.allowed(rp, u, "*"):
            continue
        r = pp.fetch(u)
        if r["status"] is None or r["status"] >= 400:
            broken.append((u, r["status"]))
            continue
        sub_page = pp.parse(r["text"] or "")
        check_index_directives(u, r, sub_page, findings, u)
        check_render_gap(u, r["text"] or "", sub_page, findings, u)

    if broken:
        findings.append(finding(
            "Broken links encountered while sampling internal pages",
            "medium" if len(broken) < len(sample) else "high",
            "; ".join(f"{u} -> {code}" for u, code in broken),
            "Broken internal links waste crawl budget and are a freshness/quality signal search and "
            "AI systems weigh when deciding how much to trust and re-crawl a site.",
            "Fix or remove the broken links found above; re-check navigation and footer links sitewide.",
            "medium",
        ))

    print(json.dumps({"skill": "crawl-render-audit", "site": base_url, "findings": findings}))


if __name__ == "__main__":
    main()
