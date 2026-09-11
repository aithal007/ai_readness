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

# --- Off-site corroboration: authority ladder (P0 strongest) --------------
# Consumed by SKILL.md Part B and surfaced in the "priority claims" finding so
# the agent verifies down a graded order rather than counting any mention.
SOURCE_LADDER = [
    ("P0", "Government / regulatory registries", "company registers, charity/education "
     "regulators, patent & trademark offices, court records"),
    ("P1", "Structured knowledge bases", "Wikidata, Wikipedia, Crunchbase, ROR, GLEIF/LEI, "
     "OpenCorporates"),
    ("P2", "Established independent news", "national/trade press with a byline and an editor "
     "(NOT the brand's own newsroom or a PR wire)"),
    ("P3", "User & review platforms", "Trustpilot, G2, Glassdoor, Reddit -- for reputation "
     "claims only, weighted low"),
    ("P4", "Other websites", "partners, competitors, industry associations -- context only"),
]

# Per-entity-type: which of the brand's own claims are worth spending the
# bounded off-site query budget on, most important first.
TYPE_CLAIM_PRIORITY = {
    "ecommerce": ["price", "availability", "returns", "identity", "location", "contact"],
    "saas": ["price", "integrations", "founding", "identity", "location"],
    "publisher": ["authorship", "ownership", "founding", "identity", "location"],
    "education": ["accreditation", "programs", "fees", "identity", "location"],
    "local_business": ["hours", "location", "phone", "services", "identity"],
    "professional_services": ["credentials", "services", "location", "identity", "contact"],
    "generic_org": ["identity", "founding", "location", "contact"],
}

_EDU_T = {"CollegeOrUniversity", "EducationalOrganization", "School"}
_LOCAL_T = {"LocalBusiness", "Restaurant", "Store", "MedicalBusiness", "Dentist",
            "LodgingBusiness", "Hotel", "AutoRepair", "HealthAndBeautyBusiness"}
_PUB_T = {"NewsMediaOrganization", "Blog", "NewsArticle", "Periodical"}


def infer_type(bundle):
    """Compact entity-type inference from evidence only (no site list). Mirrors
    answerability-probe's logic; kept self-contained per this codebase's
    one-file-per-analyzer convention. Any failure -> 'generic_org'."""
    try:
        pages = bundle.get("pages", [])
        types, urls, ctas, has_place = set(), [], set(), False
        blob = []
        for p in pages:
            types.update(p.get("jsonld_types", []))
            types.update(t.rsplit("/", 1)[-1] for t in p.get("microdata_types", []))
            urls.append((p.get("url") or "").lower())
            ctas.update(p.get("facts", {}).get("cta_matches", []))
            blob.append(p.get("text_sample", ""))
            if p.get("facts", {}).get("postal_codes"):
                has_place = True
        allurls, text = " ".join(urls), " ".join(blob)
        if types & _EDU_T or re.search(r"/admission|/academics|/programme|/courses?/", allurls):
            return "education"
        if types & _PUB_T or sum(1 for u in urls if re.search(r"/(blog|news|article|posts?)/", u)) >= 3:
            return "publisher"
        if {"SoftwareApplication", "WebApplication"} & types or \
           (re.search(r"/pricing|/plans", allurls)
            and re.search(r"\b(integrat\w+|api|sdk|docs?|webhook|plugin)\b", text, re.I)):
            return "saas"
        if any(c in ctas for c in ("add to cart", "add to bag", "add to basket")) or \
           ({"Product", "Offer"} & types
            and re.search(r"\b(shipping|delivery|returns?|in stock|out of stock)\b", text, re.I)):
            return "ecommerce"
        if types & _LOCAL_T or "PostalAddress" in types:
            return "local_business"
        if re.search(r"\b(accredit\w+|certifi\w+|licens\w+|chartered)\b", text, re.I) and \
           re.search(r"\b(services?|solutions?|what we do)\b", text, re.I):
            return "professional_services"
        return "generic_org"
    except Exception:  # noqa: BLE001
        return "generic_org"


def _iter_jsonld(node):
    if isinstance(node, dict):
        if isinstance(node.get("@graph"), list):
            for n in node["@graph"]:
                yield from _iter_jsonld(n)
        yield node
        for v in node.values():
            if isinstance(v, (dict, list)):
                yield from _iter_jsonld(v)
    elif isinstance(node, list):
        for n in node:
            yield from _iter_jsonld(n)


_JSONLD_CLAIM_KEYS = {
    "foundingDate": "founding", "foundingdate": "founding",
    "legalName": "identity", "name": "identity",
    "telephone": "contact", "email": "contact",
    "priceRange": "price", "numberOfEmployees": "scale",
    "award": "reputation", "duns": "identity", "taxID": "identity",
    "vatID": "identity", "leiCode": "identity", "iso6523Code": "identity",
}


def collect_claims(bundle):
    """Rank the brand's own factual claims by how much they merit an off-site
    check. Structured (JSON-LD) > repeated across pages > concrete homepage
    text > loose regex fact."""
    pages = bundle.get("pages", [])
    if not pages:
        return []
    home_url = pages[0].get("url", "")
    scored = {}  # (kind, value_lc) -> dict

    def add(kind, value, url, base):
        value = str(value).strip()
        if not value or len(value) > 160:
            return
        key = (kind, value.lower())
        e = scored.setdefault(key, {"kind": kind, "value": value, "score": 0,
                                    "pages": set(), "where": set()})
        e["score"] = max(e["score"], base)
        e["pages"].add(url)

    site_type = infer_type(bundle)
    priced_pages, price_example = 0, None
    for p in pages:
        url = p.get("url", "")
        for node in _iter_jsonld(p.get("jsonld", []) or []):
            if not isinstance(node, dict):
                continue
            for k, kind in _JSONLD_CLAIM_KEYS.items():
                v = node.get(k)
                if isinstance(v, str) and v.strip():
                    add(kind, v, url, 100)
                    scored[(kind, v.strip().lower())]["where"].add("JSON-LD")
            addr = node.get("address")
            if isinstance(addr, dict):
                loc = ", ".join(str(addr[x]) for x in
                                ("streetAddress", "addressLocality", "addressRegion",
                                 "postalCode", "addressCountry") if addr.get(x))
                if loc:
                    add("location", loc, url, 100)
                    scored[("location", loc.lower())]["where"].add("JSON-LD")
        # From regex-mined facts, only the ones reliable enough to hand an agent
        # for verification. Bare phone/postcode regex hits are too noisy on code,
        # tutorials and hex colours to surface as "claims".
        f = p.get("facts", {})
        txt = p.get("text_sample", "") or ""
        for y in f.get("founded_years", []):
            if not (str(y).isdigit() and 1600 <= int(y) <= 2100):
                continue
            # "founded/established in YYYY" is a real founding claim; a bare
            # "since YYYY" is often "available since", "member since" etc. --
            # only surface the strong form.
            strong = re.search(rf"\b(founded|established|incorporated)\b[^.]{{0,25}}\b{y}\b",
                               txt, re.I)
            if strong:
                add("founding", f"founded / established {y}", url, 35)
        for t in f.get("tel_links", [])[:2]:
            add("contact", f"tel: {t}", url, 30)
        if f.get("prices"):
            priced_pages += 1
            price_example = price_example or sorted(f["prices"])[0]

    # One price claim, and only where the site actually sells something --
    # grant amounts and case-study figures are not a price to verify.
    if priced_pages and site_type in ("ecommerce", "saas"):
        add("price", f"pricing shown on {priced_pages} page(s), e.g. {price_example}",
            home_url, 25)

    # concrete homepage claims: first ~220 words, real sentences carrying a
    # number. Reject Title-Case blobs (nav menus, breadcrumb trails).
    home_text = (pages[0].get("text_sample", "") or "")[:1600]
    picked = 0
    for sent in re.split(r"(?<=[.!?])\s+", home_text):
        sent = " ".join(sent.split())
        if not (24 <= len(sent) <= 200) or picked >= 2:
            continue
        if not re.search(r"\b\d[\d,]{2,}\b|\b(?:19|20)\d{2}\b|\d+\s?%", sent):
            continue
        words = [w for w in sent.split() if w[:1].isalpha()]
        if words and sum(1 for w in words if w[:1].isupper()) / len(words) > 0.6:
            continue  # looks like a menu / breadcrumb, not a statement
        add("headline_stat", sent[:140], home_url, 18)
        picked += 1

    order = TYPE_CLAIM_PRIORITY.get(site_type, TYPE_CLAIM_PRIORITY["generic_org"])
    out = []
    for e in scored.values():
        s = e["score"]
        if len(e["pages"]) >= 2:
            s += 40
        if e["kind"] in order[:3]:
            s += 30
        elif e["kind"] in order:
            s += 15
        out.append({**e, "score": s, "pages": sorted(e["pages"]), "where": sorted(e["where"])})
    out.sort(key=lambda e: -e["score"])
    return out[:6]


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

    # --- Which claims to corroborate off-site, and in what source order ---
    try:
        site_type = infer_type(bundle)
        claims = collect_claims(bundle)
        # Only surface this when there is at least one claim genuinely worth an
        # off-site check -- structured data (has a source in `where`), or a
        # typed fact that scored high. A lone homepage stat or phone is not it.
        if any(c["where"] or c["score"] >= 50 for c in claims):
            lines = []
            for i, c in enumerate(claims, 1):
                where = ", ".join(c["where"]) or "page text"
                span = f"on {len(c['pages'])} page(s)" if len(c["pages"]) > 1 else "on 1 page"
                lines.append(f"{i}. [{c['kind']}] {c['value']} (from {where}, {span})")
            ladder = "; ".join(f"{tier} {label}" for tier, label, _ in SOURCE_LADDER)
            findings.append(finding(
                "Priority claims to verify against independent sources",
                "low",
                f"Inferred site type: {site_type}. The claims most worth spending the bounded "
                f"off-site query budget on (Part B):\n" + "\n".join(lines),
                "Off-site corroboration is where most of the citation surface is -- assistants "
                "trust a fact more when independent sources agree, and a claim that lives only on "
                "the brand's own site has nothing to check it against. Verifying the highest-value "
                "claims first, and weighting sources by authority, spends a small query budget "
                "where it matters.",
                "For each claim above, search independent sources working DOWN this ladder and "
                f"stop at the first tier that settles it: {ladder}. Count a claim corroborated "
                "only when a source that is NOT the brand, NOT a press-release wire, and NOT an "
                "aggregator copying one origin agrees with it. Record CONTRADICTED / CONFIRMED / "
                "UNCORROBORATED per claim (uncorroborated is not the same as false).",
                "low", evidence_tier="correlational",
                how="P0/P1 (registries, Wikidata/Crunchbase) settle identity, founding year and "
                    "location cheaply. Reserve P2 news for disputed or reputational claims. P3 "
                    "review sites only for reputation, weighted low."))
    except Exception as exc:  # noqa: BLE001 - never let this optional step break the run
        print(f"note: claim-selection step skipped: {type(exc).__name__}: {exc}", file=sys.stderr)

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
