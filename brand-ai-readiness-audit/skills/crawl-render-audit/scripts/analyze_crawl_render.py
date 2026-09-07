#!/usr/bin/env python3
"""crawl-render-audit: can a machine reach the page, and read what's on it?

Precondition 1 of AI discoverability. If this fails nothing downstream matters:
a page a crawler cannot fetch, or cannot read, is invisible no matter how good
its content or markup is.

The false-positive guard that matters most here is the CRAWLER TAXONOMY.
Refusing training crawlers while allowing search crawlers is a documented,
legitimate licensing choice -- per Google, blocking Google-Extended "does not
impact a site's inclusion in Google Search"; per OpenAI, disallowing GPTBot
only opts out of model training. Flagging those is the most common false
positive in this whole problem space, so this skill never does.

Usage: python3 analyze_crawl_render.py --evidence evidence.json
Emits JSON to stdout; diagnostics to stderr. Exit: 0 ok, 2 bad evidence.
"""
import argparse
import json
import os
import sys

SKILL = "crawl-render-audit"


def finding(title, severity, evidence, mechanism, action, priority,
            evidence_tier="measured", how=None, page=None):
    sa = {"summary": action, "priority": priority}
    if how:
        sa["how"] = how
    f = {"title": title, "severity": severity, "category": "discoverability",
         "evidence": evidence, "mechanism": mechanism, "suggested_action": sa,
         "signal_tier": 1, "evidence_tier": evidence_tier, "source_skill": SKILL}
    if page:
        f["page"] = page
    return f


def analyze(bundle):
    findings = []
    if not bundle.get("entry_reachable"):
        return [finding(
            "Site did not respond to an unauthenticated request",
            "critical",
            f"Entry fetch of {bundle.get('site')} failed: {bundle.get('entry_error')}.",
            "If a plain GET fails, no crawler -- AI or search -- can reach the site at all.",
            "Verify the domain resolves and the origin answers anonymous GET requests from "
            "external networks.", "critical")]

    robots = bundle.get("robots", {})
    pages = bundle.get("pages", [])

    # --- Access: robots.txt, correctly interpreted by crawler purpose --------
    if robots.get("present") and not robots.get("star_allowed_root", True):
        findings.append(finding(
            "robots.txt blocks all compliant crawlers from the site root",
            "critical",
            f"robots.txt disallows the root for User-agent: *. Excerpt: "
            f"{robots.get('raw_excerpt', '')[:300]!r}",
            "A blanket Disallow for '*' is honoured by every well-behaved crawler, including the "
            "search-index bots that feed AI answers. Nothing else in this report can take effect "
            "while it stands.",
            "Remove the sitewide Disallow, or narrow it to genuinely private paths.", "critical"))

    agents = robots.get("agents", {})
    blocked_search = [t for t, a in agents.items()
                      if not a["allowed_root"] and a["citation_impact"] == "removes"]
    blocked_training = [t for t, a in agents.items()
                        if not a["allowed_root"] and a["citation_impact"] == "none"]
    blocked_intent = [t for t, a in agents.items()
                      if not a["allowed_root"] and a["citation_impact"] == "intent"]

    if blocked_search:
        findings.append(finding(
            "Search-index crawlers that feed AI answers are blocked",
            "critical",
            f"robots.txt disallows the root for: {', '.join(sorted(blocked_search))}. "
            f"These are search/citation crawlers, not training crawlers.",
            "These specific agents build the index assistants draw on when answering. Blocking "
            "one removes the brand from that assistant's answers entirely -- e.g. OpenAI states "
            "sites opted out of OAI-SearchBot 'will not be shown in ChatGPT search answers'. "
            "This is distinct from refusing training crawlers, which costs no visibility.",
            "Allow the search-index agents while keeping any training-crawler restrictions you "
            "want. The two are independent controls.", "critical",
            how="Refusing training (GPTBot, ClaudeBot, Google-Extended) while allowing search "
                "(OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot) is the documented "
                "way to keep citation visibility without contributing training data."))

    if blocked_training and not blocked_search:
        findings.append(finding(
            "Training crawlers are blocked (informational -- no citation impact)",
            "low",
            f"robots.txt disallows: {', '.join(sorted(blocked_training))}. Search-index crawlers "
            "remain allowed.",
            "This is a legitimate content-licensing choice and does NOT reduce the brand's "
            "visibility in AI answers. Recorded so the configuration is visible and deliberate, "
            "not because it is a defect.",
            "No action needed unless contributing to model training is desired. Verified as "
            "correctly configured: search access is preserved.", "low",
            evidence_tier="measured"))

    if blocked_intent:
        findings.append(finding(
            "Live user-fetch agents are disallowed (advisory only)",
            "low",
            f"robots.txt disallows: {', '.join(sorted(blocked_intent))}.",
            "These agents fetch a page when a user explicitly asks about it. Operators state "
            "robots.txt may not apply to user-triggered fetches, so treat this as a declaration "
            "of intent rather than an effective block.",
            "If real-time citation is wanted, allow these agents; enforcement, if needed, must "
            "happen at the network layer rather than in robots.txt.", "low"))

    signals = robots.get("content_signals") or {}
    if signals:
        findings.append(finding(
            "Cloudflare Content Signals directives are present in robots.txt",
            "medium" if signals.get("search") == "no" else "low",
            f"Content-Signal directives found: {signals}.",
            "These CDN-injected directives declare permitted uses (search / ai-input / ai-train) "
            "separately from crawl permission, and are frequently added by the CDN rather than by "
            "the site owner -- so the stated policy may not be the one intended. "
            + ("'search=no' asks engines not to include the site in search-derived answers."
               if signals.get("search") == "no" else ""),
            "Confirm these directives match your intended policy, and that they were a deliberate "
            "choice rather than a CDN default.", "medium" if signals.get("search") == "no" else "low",
            evidence_tier="correlational"))

    # --- Access: network-layer blocking, which robots.txt cannot reveal -----
    probe = bundle.get("ua_probe", {})
    if probe.get("network_layer_block_suspected"):
        detail = "; ".join(f"{b['agent']}: {b.get('error') or b.get('status')}"
                           for b in probe["blocked_agents"])
        findings.append(finding(
            "AI crawler user-agents are blocked at the network layer",
            "critical",
            f"The same URL returned a normal response to a browser user-agent but not to declared "
            f"AI crawlers -- {detail}. robots.txt does not disallow these agents, so the block is "
            "happening above it.",
            "CDN and WAF bot management (Cloudflare's AI-bot blocking, AWS WAF, Akamai) filters by "
            "user-agent and IP before robots.txt is ever consulted, and overrides it. A site can "
            "publish a perfectly permissive robots.txt and still be completely invisible to "
            "assistants. This failure is undetectable from robots.txt alone.",
            "Check the CDN/WAF bot-management settings and allow the AI search crawlers you want "
            "citing you.", "critical",
            how="In Cloudflare this is the 'Block AI Bots' / bot-management rule set, not "
                "robots.txt. Note that some plans block AI crawlers by default."))

    # --- Access: index directives ------------------------------------------
    noindex = [p for p in pages
               if "noindex" in (p.get("robots_meta") or "").lower()
               or "noindex" in (p.get("headers", {}).get("x-robots-tag") or "").lower()]
    if noindex:
        home_blocked = any(p["url"] == bundle.get("site") for p in noindex)
        findings.append(finding(
            "Pages are explicitly excluded from indexing",
            "critical" if home_blocked else "high",
            f"{len(noindex)}/{len(pages)} sampled pages carry a noindex directive: " +
            "; ".join(p["url"] for p in noindex[:4]) + ".",
            "noindex removes a page from every compliant index, so it can never be retrieved or "
            "cited regardless of content quality. It is frequently left behind by accident after "
            "a staging deploy.",
            "Remove noindex from any page that should be publicly findable; keep it only where "
            "exclusion is deliberate (thin, duplicate, or genuinely private pages).",
            "critical" if home_blocked else "high"))

    # --- Read: render gap ---------------------------------------------------
    render_gap = [p for p in pages
                  if p["citability"]["word_count"] < 120
                  and (p.get("spa_root") or p["scripts"]["total"] >= 6)
                  and p["status"] == 200]
    if render_gap:
        ex = render_gap[0]
        findings.append(finding(
            "Page content requires JavaScript to appear",
            "critical" if len(render_gap) >= max(2, len(pages) // 2) else "high",
            f"{len(render_gap)}/{len(pages)} sampled pages return under 120 words of extractable "
            f"text while carrying a client-render root or 6+ scripts. Example: {ex['url']} -- "
            f"{ex['citability']['word_count']} words, {ex['scripts']['total']} scripts, "
            f"SPA root={ex.get('spa_root')}, noscript fallback={ex['noscript_len']} chars.",
            "Most AI crawlers fetch raw HTML and do not execute JavaScript. Content assembled "
            "client-side is simply absent for them -- the page looks blank to the very systems "
            "you want quoting it, while looking complete to every human who checks.",
            "Server-side render or pre-render the primary content so it is present in the initial "
            "HTML response.", "critical" if len(render_gap) >= max(2, len(pages) // 2) else "high",
            how="Verify with: curl -A 'GPTBot' <url> | head -c 2000 — if the facts aren't in that "
                "output, a crawler cannot see them.",
            page=ex["url"]))

    # --- Read: facts locked in non-text -------------------------------------
    risk_counts = {}
    for p in pages:
        for r in p.get("extractability_risks", []):
            risk_counts.setdefault(r["mode"], []).append(p["url"])
    high_risk = {"fact_bearing_image_without_alt", "facts_locked_in_pdf",
                 "unrendered_template_binding", "third_party_embed_content",
                 "canvas_rendered_content", "fact_only_in_data_attribute"}
    hits = {m: u for m, u in risk_counts.items() if m in high_risk}
    if hits:
        detail = "; ".join(f"{m} on {len(u)} page(s) (e.g. {u[0]})" for m, u in list(hits.items())[:4])
        findings.append(finding(
            "Facts appear to be locked in non-text elements",
            "high",
            f"Detected: {detail}.",
            "A fact carried only by an image, a PDF, a canvas, a third-party embed or an "
            "unrendered template is invisible to text extraction. The information already exists "
            "-- it just cannot be read -- which makes this among the cheapest gaps to close.",
            "Add a plain-text equivalent alongside each of these elements: real HTML text for "
            "prices and specs shown as images, an HTML summary beside PDF-only documents, and "
            "descriptive alt text on fact-bearing graphics.", "high"))

    if any(p.get("structured_data", {}).get("embedded_state_blob") for p in pages) and render_gap:
        findings.append(finding(
            "Content exists in an embedded JSON state blob but not in rendered HTML",
            "medium",
            "Pages with a render gap also embed a framework state blob "
            "(__NEXT_DATA__ / __NUXT__ / __INITIAL_STATE__).",
            "The facts are being shipped to the browser as JSON and rendered by script. Some "
            "extractors mine these blobs, but most do not, and none are obliged to -- relying on "
            "it is fragile.",
            "Render the same values into the served HTML rather than depending on the client to "
            "hydrate them.", "medium", evidence_tier="correlational"))

    # --- Discovery ----------------------------------------------------------
    sm = bundle.get("sitemap", {})
    if sm.get("total_urls_found", 0) == 0:
        findings.append(finding(
            "No usable XML sitemap found",
            "medium",
            "No sitemap was retrievable from robots.txt declarations or /sitemap.xml.",
            "A sitemap is the most reliable way for a crawler to discover pages that have few "
            "inbound internal links. It is far better evidenced than newer conventions such as "
            "llms.txt, which measurably almost nothing reads.",
            "Publish an XML sitemap covering all public pages and reference it from robots.txt "
            "with a Sitemap: line.", "medium"))

    failures = bundle.get("stats", {}).get("failures", [])
    if failures:
        findings.append(finding(
            "Broken internal links encountered while crawling",
            "medium",
            "; ".join(f"{f['url']} -> {f.get('status') or f.get('error')}" for f in failures[:5]),
            "Dead internal links waste crawl budget and signal neglect to both crawlers and "
            "visitors.",
            "Fix or remove the broken links listed above, then re-check navigation and footer "
            "links sitewide.", "medium"))

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
