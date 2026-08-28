#!/usr/bin/env python3
"""structured-data-entity-audit checks.

Checks whether facts on the page are stated in a form a machine can parse
unambiguously (schema.org JSON-LD, Open Graph, title/description, llms.txt)
and whether the entity itself is disambiguated from other things that might
share its name (sameAs links to canonical profiles).

Usage: python3 check_structured_data.py <url>
Prints a JSON object {"skill": ..., "site": ..., "findings": [...]} to stdout.
"""
import json
import re
import sys

import page_parser as pp

PRICE_RE = re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d{2})?")
# Deliberately narrow to strong, unambiguous purchase-intent phrases. Broader words like
# "checkout" are too often a product/feature name (e.g. "Stripe Checkout") rather than a
# buy action, and caused false positives on SaaS pricing pages during testing.
BUY_WORDS = re.compile(r"\b(add to cart|buy now|add to bag|add to basket|proceed to checkout)\b", re.I)
GENERIC_TITLES = {"home", "homepage", "untitled", "untitled document", "new page", "index", "welcome"}
KNOWN_ENTITY_PROFILES = ["wikipedia.org", "wikidata.org", "linkedin.com/company", "crunchbase.com",
                          "github.com", "youtube.com", "twitter.com", "x.com", "instagram.com", "facebook.com"]


def finding(title, severity, evidence, mechanism, action_summary, action_priority, how=None):
    sa = {"summary": action_summary, "priority": action_priority}
    if how:
        sa["how"] = how
    return {"title": title, "severity": severity, "category": "discoverability",
            "evidence": evidence, "mechanism": mechanism, "suggested_action": sa}


def extract_ld_types(page):
    """Return (parsed_blocks, invalid_count, type_set)."""
    parsed, invalid, types = [], 0, set()

    def walk(obj):
        if isinstance(obj, dict):
            t = obj.get("@type")
            if isinstance(t, list):
                types.update(str(x) for x in t)
            elif t:
                types.add(str(t))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    for raw in page.ld_json_raw:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            parsed.append(obj)
            walk(obj)
        except json.JSONDecodeError:
            invalid += 1
    return parsed, invalid, types


def check_page(url, html, page, findings, label, is_home):
    parsed, invalid, types = extract_ld_types(page)

    if invalid:
        findings.append(finding(
            f"Invalid (unparseable) JSON-LD on {label}",
            "high",
            f"{invalid} of {len(page.ld_json_raw)} <script type=\"application/ld+json\"> block(s) on "
            f"{url} failed to parse as JSON.",
            "A malformed JSON-LD block is typically ignored wholesale by structured-data consumers -- "
            "it contributes nothing even though it looks present in the page source.",
            "Fix the JSON syntax (trailing commas and unescaped quotes are the usual cause) and validate "
            "with a JSON-LD linter before deploying.",
            "high",
        ))

    if is_home:
        if not types:
            findings.append(finding(
                "No schema.org structured data on the homepage",
                "high",
                f"Zero <script type=\"application/ld+json\"> blocks found on {url}.",
                "Structured data is the most explicit, least ambiguous way to state who/what an entity "
                "is; assistants and search engines lean on it heavily when it's present, and fall back to "
                "much noisier text inference when it's absent.",
                "Add Organization (or LocalBusiness) JSON-LD to the homepage with name, url, logo, and sameAs.",
                "high",
            ))
        elif not ({"Organization", "LocalBusiness", "Corporation", "WebSite"} & types):
            findings.append(finding(
                "Homepage JSON-LD does not declare an Organization/WebSite entity",
                "medium",
                f"Types found on {url}: {sorted(types)}.",
                "Without an explicit Organization entity, assistants have less structured basis to "
                "distinguish this brand from unrelated things sharing its name.",
                "Add an Organization or WebSite JSON-LD block on the homepage.",
                "medium",
            ))
        else:
            same_as_present = any(
                isinstance(o, dict) and "sameAs" in o for o in parsed
            ) or any(
                isinstance(o, dict) and isinstance(o.get("@graph"), list) and
                any(isinstance(g, dict) and "sameAs" in g for g in o["@graph"])
                for o in parsed
            )
            if not same_as_present:
                findings.append(finding(
                    "Organization schema has no sameAs links",
                    "medium",
                    f"Organization/WebSite JSON-LD present on {url} but no 'sameAs' property found.",
                    "sameAs links (to Wikipedia, Wikidata, LinkedIn, Crunchbase, official social) are how "
                    "a knowledge-graph-style system disambiguates this entity from unrelated ones with a "
                    "similar or identical name -- without them, name collisions are more likely to cause "
                    "the wrong entity to be cited.",
                    "Add a 'sameAs' array pointing to the brand's official Wikipedia/Wikidata (if any), "
                    "LinkedIn company page, Crunchbase profile, and primary social accounts.",
                    "medium",
                ))

        og_title = any(m["name"] == "og:title" for m in page.meta)
        og_desc = any(m["name"] == "og:description" for m in page.meta)
        twitter_card = any(m["name"] == "twitter:card" for m in page.meta)
        if not (og_title and og_desc):
            findings.append(finding(
                "Missing Open Graph title/description on the homepage",
                "medium",
                f"og:title present={og_title}, og:description present={og_desc} on {url}.",
                "Open Graph tags are a widely-parsed, unambiguous source for 'what is this page about' "
                "used by link previews and many content-ingestion pipelines, AI ones included.",
                "Add og:title, og:description, and og:image meta tags to every indexable page.",
                "medium",
            ))
        if not twitter_card:
            findings.append(finding(
                "Missing Twitter/X card meta tags",
                "low",
                f"No twitter:card meta tag found on {url}.",
                "Low-cost redundant signal for how the page is summarized in previews/ingestion.",
                "Add twitter:card, twitter:title, and twitter:description meta tags.",
                "low",
            ))

        title_text = (page.title or "").strip()
        if not title_text:
            findings.append(finding(
                "Homepage has no <title>", "high", f"Empty or missing <title> on {url}.",
                "The title tag is one of the highest-weight, most explicitly-read signals for what a "
                "page is about; an empty one forces inference from noisier body text.",
                "Set a descriptive <title> that includes the brand name and primary offering.", "high",
            ))
        elif title_text.strip().lower() in GENERIC_TITLES:
            findings.append(finding(
                "Homepage <title> is a generic placeholder",
                "medium", f"<title>{title_text}</title> on {url}.",
                "A generic title ('Home', 'Untitled Document') carries no identifying information, so it "
                "does nothing to establish or disambiguate the brand entity.",
                "Replace with a descriptive title naming the brand and what it does.", "medium",
            ))

        desc = next((m["content"] for m in page.meta if m["name"] == "description"), "")
        if not desc.strip():
            findings.append(finding(
                "Homepage has no meta description", "medium", f"No meta name=\"description\" found on {url}.",
                "Meta description is a commonly-ingested, explicit one-line summary of the page's purpose.",
                "Add a concise, specific meta description (roughly 120-160 characters).", "medium",
            ))

        if not (page.lang or "").strip():
            findings.append(finding(
                "No language declared on <html lang>", "low", f"<html> has no lang attribute on {url}.",
                "Missing language metadata makes locale/entity matching slightly less reliable for "
                "multi-region brands and screen readers alike.",
                "Add a lang attribute (e.g. lang=\"en\") to the <html> element.", "low",
            ))

        if not page.has_favicon:
            findings.append(finding(
                "No favicon declared", "low", f"No <link rel=\"icon\"> found on {url}.",
                "Minor brand-identity/polish signal; some surfaces (browser tabs, some AI browse UIs) show it.",
                "Add a <link rel=\"icon\"> pointing to a favicon asset.", "low",
            ))

    # Product-page heuristic
    looks_like_product = bool(PRICE_RE.search(page.body_text) and BUY_WORDS.search(html))
    if looks_like_product and not ({"Product", "Offer"} & types):
        findings.append(finding(
            f"Page looks like a product/e-commerce page but has no Product/Offer structured data ({label})",
            "medium",
            f"{url}: page text contains a price pattern and explicit purchase-action wording (e.g. "
            f"'add to cart'/'buy now'), but JSON-LD types found are {sorted(types) or '[]'}. "
            "Heuristic match -- confirm this is actually a purchasable item before treating it as a defect; "
            "SaaS/service pricing pages may legitimately use Service or Offer schema instead of Product.",
            "Product/Offer JSON-LD is how price, availability, and identity are stated unambiguously for "
            "shopping-aware assistants and search rich results; without it they must guess from prose, "
            "which is error-prone and often skipped entirely.",
            "If this page sells a discrete item, add Product JSON-LD (name, image, description, "
            "offers.price, offers.priceCurrency, offers.availability). If it's a service/subscription "
            "tier instead, use Service or an Offer under the Organization/SoftwareApplication entity.",
            "medium",
        ))

    looks_like_article = ("<article" in html.lower()) or bool(re.search(r"/blog/|/news/|/article", url))
    if looks_like_article and not ({"Article", "BlogPosting", "NewsArticle"} & types):
        findings.append(finding(
            f"Page looks like an article but has no Article/BlogPosting structured data ({label})",
            "medium",
            f"{url}: matches article/blog URL or markup pattern, but JSON-LD types found are {sorted(types) or '[]'}.",
            "Article schema carries headline, author, and datePublished/datePublished explicitly, which "
            "assistants use for both extraction and freshness judgments.",
            "Add Article or BlogPosting JSON-LD with headline, author, datePublished, and dateModified.",
            "medium",
        ))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"skill": "structured-data-entity-audit", "site": None, "findings": []}))
        return

    findings = []
    base_url, home = pp.resolve_base_url(sys.argv[1])
    if not home or home["status"] is None or home["status"] >= 400:
        findings.append(finding(
            "Could not fetch homepage to audit structured data", "medium",
            f"GET {base_url} -> status={home['status'] if home else None}, error={home['error'] if home else 'n/a'}.",
            "No structured-data checks could run without a successful homepage fetch.",
            "Re-run once the homepage is reachable; see the crawl-render-audit findings for the root cause.",
            "medium",
        ))
        print(json.dumps({"skill": "structured-data-entity-audit", "site": base_url, "findings": findings}))
        return

    html = home["text"] or ""
    page = pp.parse(html)
    check_page(base_url, html, page, findings, "homepage", is_home=True)

    # site_root, not base_url verbatim -- llms.txt lives at the domain root
    # even when the audited URL itself points at a specific path/page.
    llms_txt = pp.fetch(pp.site_root(base_url) + "/llms.txt")
    if not (llms_txt["status"] == 200 and llms_txt["text"].strip().startswith("#")):
        findings.append(finding(
            "No llms.txt found", "low",
            f"GET /llms.txt returned status={llms_txt['status']}.",
            "llms.txt is an emerging, low-cost convention some AI tools check for a curated summary "
            "and link list; it does not replace proper crawlability/schema but is cheap and low-risk to add.",
            "Publish a plain-markdown /llms.txt with an H1 site name, one-paragraph summary, and links to "
            "key pages (docs, pricing, about).", "low",
        ))

    sample = pp.same_domain_links(base_url, page.links, limit=3)
    for u in sample:
        r = pp.fetch(u)
        if r["status"] and r["status"] < 400:
            sub_page = pp.parse(r["text"] or "")
            check_page(u, r["text"] or "", sub_page, findings, u, is_home=False)

    print(json.dumps({"skill": "structured-data-entity-audit", "site": base_url, "findings": findings}))


if __name__ == "__main__":
    main()
