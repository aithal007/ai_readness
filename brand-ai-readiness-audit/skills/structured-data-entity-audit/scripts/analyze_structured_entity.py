#!/usr/bin/env python3
"""structured-data-entity-audit: is it clear WHO this is, and do the machine
claims match the visible page?

Two guards define this skill:

1. NEVER report "no structured data" without resolving the full ladder.
   Microdata, RDFa and microformats are structured data too, and because they
   annotate the visible text directly their fact-parity is arguably better than
   JSON-LD's. Millions of themes emit classic microformats. Calling those sites
   unmarked is a textbook false positive.

2. NEVER oversell schema as an AI-citation lever. The best-controlled studies
   found null or slightly negative effects on AI citation; one controlled test
   of 1,885 pages saw citations fall after adding JSON-LD. Schema earns its
   keep for search rich results and for entity disambiguation -- which is real
   and is what this skill actually checks -- not as a route to being quoted.

Usage: python3 analyze_structured_entity.py --evidence evidence.json
"""
import argparse
import json
import os
import re
import sys

SKILL = "structured-data-entity-audit"
ORG_TYPES = {"Organization", "LocalBusiness", "Corporation", "NGO", "GovernmentOrganization",
             "CollegeOrUniversity", "EducationalOrganization", "NewsMediaOrganization"}
AUTHORITATIVE_SAMEAS = ("wikidata.org", "wikipedia.org", "linkedin.com/company",
                        "crunchbase.com", "ror.org", "isni.org")
SOCIAL_SAMEAS = ("twitter.com", "x.com", "facebook.com", "instagram.com",
                 "youtube.com", "github.com", "tiktok.com")
GENERIC_TITLES = {"home", "homepage", "untitled", "untitled document", "new page",
                  "index", "welcome", "site", "my site"}


def finding(title, severity, evidence, mechanism, action, priority,
            evidence_tier="correlational", how=None, page=None):
    sa = {"summary": action, "priority": priority}
    if how:
        sa["how"] = how
    f = {"title": title, "severity": severity, "category": "discoverability",
         "evidence": evidence, "mechanism": mechanism, "suggested_action": sa,
         "signal_tier": 2, "evidence_tier": evidence_tier, "source_skill": SKILL}
    if page:
        f["page"] = page
    return f


def iter_nodes(doc):
    stack = [doc]
    while stack:
        n = stack.pop()
        if isinstance(n, list):
            stack.extend(n)
        elif isinstance(n, dict):
            if "@graph" in n:
                stack.append(n["@graph"])
            yield n
            stack.extend(v for v in n.values() if isinstance(v, (dict, list)))


def org_nodes(page):
    out = []
    for doc in page.get("jsonld", []):
        for n in iter_nodes(doc):
            t = n.get("@type")
            types = {t} if isinstance(t, str) else set(t or [])
            if types & ORG_TYPES:
                out.append(n)
    return out


def analyze(bundle):
    findings = []
    pages = [p for p in bundle.get("pages", []) if p.get("structured_data")]
    if not pages:
        return findings
    home = pages[0]
    verdicts = [p["structured_data"]["verdict"] for p in pages]

    invalid = [p for p in pages if p.get("jsonld_invalid")]
    if invalid:
        findings.append(finding(
            "Structured data is present but fails to parse",
            "high",
            f"{len(invalid)} page(s) contain a <script type=\"application/ld+json\"> block that is "
            f"not valid JSON. Examples: {', '.join(p['url'] for p in invalid[:3])}.",
            "A malformed block is discarded wholesale by consumers, so it contributes nothing "
            "while appearing present in the source. This is strictly worse than having no markup: "
            "it looks done, so nobody revisits it.",
            "Fix the JSON syntax (trailing commas and unescaped quotes are the usual causes) and "
            "validate before deploying.", "high", evidence_tier="measured",
            how="Paste the block into any JSON linter, or run: python -m json.tool < block.json"))

    no_sd = [p for p in pages if p["structured_data"]["verdict"] == "NO_STRUCTURED_DATA"]
    legacy = [p for p in pages if p["structured_data"]["verdict"] == "LEGACY_MICROFORMATS_ONLY"]
    social_only = [p for p in pages if p["structured_data"]["verdict"] == "SOCIAL_META_ONLY"]

    if len(no_sd) == len(pages):
        findings.append(finding(
            "No structured data of any kind on the sampled pages",
            "medium",
            f"All {len(pages)} sampled pages resolve to NO_STRUCTURED_DATA -- no JSON-LD, "
            "microdata, RDFa, microformats, Open Graph or Dublin Core markup was found.",
            "Structured data is a legitimate aid for search rich results and, more importantly "
            "here, for stating entity identity unambiguously. Note the honest scope: controlled "
            "studies do NOT show schema markup causing more AI citations -- so this is worth doing "
            "for identity and search, not as a route to being quoted. What gets a page quoted is "
            "concrete facts in visible body text.",
            "Add an Organization (or LocalBusiness) JSON-LD block on the homepage with name, url, "
            "logo, a stable @id and sameAs links.", "medium",
            how="Keep the markup's claims identical to the visible page text -- asserting facts in "
                "markup that the page does not show is its own failure mode."))
    elif legacy or social_only:
        findings.append(finding(
            "Only weak or legacy structured data is present",
            "low",
            f"Verdicts across sampled pages: {sorted(set(verdicts))}. "
            f"{len(legacy)} page(s) carry only classic microformats, {len(social_only)} only "
            "social meta tags.",
            "These formats are read by fewer consumers than JSON-LD and typically carry less "
            "entity detail, but they ARE structured data -- this is a gap in richness, not an "
            "absence of markup.",
            "Add an Organization JSON-LD block alongside the existing markup rather than replacing "
            "it.", "low"))

    # --- Entity identity ----------------------------------------------------
    orgs = org_nodes(home)
    if orgs:
        org = orgs[0]
        same = org.get("sameAs")
        same = [same] if isinstance(same, str) else list(same or [])
        auth = [u for u in same if any(d in str(u) for d in AUTHORITATIVE_SAMEAS)]
        social = [u for u in same if any(d in str(u) for d in SOCIAL_SAMEAS)]
        problems = []
        if not org.get("@id"):
            problems.append("no stable @id")
        if not same:
            problems.append("no sameAs links at all")
        elif not auth:
            problems.append(f"sameAs has only social profiles ({len(social)}), no authoritative "
                            "reference (Wikidata / Wikipedia / LinkedIn company / Crunchbase / ROR)")
        nonurl = [u for u in same if not str(u).startswith("http")]
        if nonurl:
            problems.append(f"{len(nonurl)} non-URL value(s) in sameAs")

        if problems:
            findings.append(finding(
                "Organization entity is not unambiguously identified",
                "medium",
                f"Homepage Organization node: {', '.join(problems)}. "
                f"name={org.get('name', '(missing)')!r}.",
                "Where several organisations share a name, a system has to guess which one a page "
                "refers to, and a wrong guess means the brand is described with someone else's "
                "facts. sameAs links to canonical references are the standard mechanism for "
                "resolving that, and a stable @id lets every page point at one identity rather "
                "than asserting a new one each time.",
                "Add a stable @id (e.g. https://yourdomain/#org) and a sameAs array pointing to "
                "your Wikidata item, Wikipedia article, LinkedIn company page and Crunchbase "
                "profile where they exist.", "medium",
                how="Bare identifier codes (LEI, DUNS, VAT, ISNI numbers) are not URLs and belong "
                    "in `identifier` as a PropertyValue, not in sameAs."))

        # Parity: markup must not assert what the page does not show.
        name = str(org.get("name") or "")
        if name and name.lower() not in (home.get("text_sample", "") + home.get("title", "")).lower():
            findings.append(finding(
                "Organization name in markup does not appear in the visible page text",
                "low",
                f"JSON-LD declares name={name!r}, which was not found in the homepage's extracted "
                "text or title.",
                "Structured data is meant to describe what the page shows. A claim present only in "
                "markup is unverifiable against the page and is discounted accordingly -- and it "
                "is the same class of problem as a fact that exists only inside an image.",
                "Make the organisation name visible in the page text (header, footer or about "
                "section) so markup and content agree.", "low"))

        ids = [n.get("@id") for p in pages for n in org_nodes(p) if n.get("@id")]
        distinct = {i for i in ids if i}
        if len(distinct) > 1:
            findings.append(finding(
                "Conflicting Organization identities across pages",
                "medium",
                f"{len(distinct)} different @id values assert an Organization across the sampled "
                f"pages: {sorted(distinct)[:4]}.",
                "Multiple emitters (a theme plus an SEO plugin plus custom code) each declaring "
                "their own Organization produces colliding entities, which is worse than a single "
                "sparse one -- consumers cannot tell which is authoritative.",
                "Consolidate to one canonical Organization @id per site and have other nodes "
                "reference it rather than redeclaring it.", "medium"))
    elif not no_sd:
        findings.append(finding(
            "Structured data present but no Organization entity is declared",
            "medium",
            f"Homepage markup types: {sorted(set(home.get('jsonld_types', [])))[:8]}; no "
            "Organization-family node found.",
            "Page-level markup describes content, but nothing states who publishes it. Without an "
            "entity node there is no anchor for identity or for sameAs disambiguation.",
            "Add an Organization node and link page-level nodes to it via publisher/about.",
            "medium"))

    # --- Basic descriptive metadata ----------------------------------------
    title = (home.get("title") or "").strip()
    if not title:
        findings.append(finding(
            "Homepage has no title element", "high",
            f"No <title> found on {home['url']}.",
            "The title is among the highest-weight structural fields for retrieval -- structural "
            "fields measured roughly +22% retrieval hit-rate. An empty one forces the engine to "
            "infer the page's subject from noisier signals.",
            "Set a descriptive title naming the brand and what it does.", "high",
            evidence_tier="measured"))
    elif title.lower() in GENERIC_TITLES:
        findings.append(finding(
            "Homepage title is a generic placeholder", "medium",
            f"<title>{title}</title> on {home['url']}.",
            "A placeholder title carries no identifying information, so it neither establishes the "
            "entity nor helps the page match a relevant query.",
            "Replace with a specific title naming the brand and its primary offering.", "medium",
            evidence_tier="measured"))

    nodesc = [p for p in pages if not (p.get("meta_description") or "").strip()]
    if len(nodesc) >= max(2, len(pages) // 2):
        findings.append(finding(
            "Most pages have no meta description", "low",
            f"{len(nodesc)}/{len(pages)} sampled pages expose no meta description.",
            "The description is a structural field used in retrieval and as an explicit one-line "
            "statement of page purpose.",
            "Write a specific description (roughly 120-160 characters) for each substantive page.",
            "low", evidence_tier="measured"))

    if not (home.get("lang") or "").strip():
        findings.append(finding(
            "No language declared on the html element", "low",
            f"<html> has no lang attribute on {home['url']}.",
            "Missing language metadata weakens locale and entity matching, and degrades screen "
            "reader pronunciation.",
            'Add a lang attribute, e.g. <html lang="en">.', "low"))

    # llms.txt: reported honestly as speculative, never scored as a defect.
    if not bundle.get("wellknown", {}).get("llms_txt", {}).get("present"):
        findings.append(finding(
            "No llms.txt (optional, unproven -- informational only)", "low",
            "GET /llms.txt returned no usable file.",
            "llms.txt is an emerging convention with, as of 2026, no demonstrated citation "
            "benefit: a 137,000-domain study found 97% of published files received zero requests, "
            "a ~300,000-domain study found no significant correlation with AI citations, and "
            "Google has said it does not support it. Listed for completeness only.",
            "Optional. Prioritise sitemap.xml, crawler access and visible on-page facts first -- "
            "all three are far better evidenced. Add llms.txt only if it is cheap and you accept "
            "it may do nothing.", "low", evidence_tier="speculative"))

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
