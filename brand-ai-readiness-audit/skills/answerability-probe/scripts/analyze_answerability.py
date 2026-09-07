#!/usr/bin/env python3
"""answerability-probe: the outcome test.

Every other skill audits an INPUT (is the bot allowed in, is the markup valid,
is the copy quotable). This one audits the OUTCOME: if a real person asked an
assistant a normal question about this brand, is the answer present anywhere in
the site's machine-readable text at all?

Method:
 1. Infer the entity type from the evidence bundle (schema types, transaction
    signals, opening-hours signals, path conventions) -- never from a hardcoded
    site list, so it generalises to sites never seen before.
 2. Take the canonical question set for that entity type. These are the
    questions assistants actually get asked about that kind of organisation.
 3. For each question, look for answer-bearing evidence in the EXTRACTED TEXT
    and structured data -- i.e. what a non-JS-executing crawler would see.
 4. Report each unanswerable question as a concrete, named gap.

A missing answer here is strictly worse than a missing best-practice: it is the
literal reason an assistant would say "I don't have information about that."

Usage:
  python3 analyze_answerability.py --evidence evidence.json
Emits JSON to stdout; diagnostics to stderr. Exit: 0 ok, 2 bad evidence.
"""
import argparse
import json
import os
import re
import sys

SKILL = "answerability-probe"

# --- Entity-type inference --------------------------------------------------
EDU_TYPES = {"CollegeOrUniversity", "EducationalOrganization", "School"}
LOCAL_TYPES = {"LocalBusiness", "Restaurant", "Store", "MedicalBusiness", "Dentist",
               "LodgingBusiness", "Hotel", "AutoRepair", "HealthAndBeautyBusiness"}
PUB_TYPES = {"NewsMediaOrganization", "Blog", "NewsArticle", "Periodical"}

# Slot -> (human question, how we look for an answer)
UNIVERSAL_SLOTS = ["identity", "what_it_does", "contact", "location"]
TYPE_SLOTS = {
    "ecommerce": ["price", "product_specs", "shipping_returns", "availability"],
    "saas": ["price", "product_specs", "integrations_or_docs", "trial_or_signup"],
    "local_business": ["hours", "phone", "services", "booking"],
    "education": ["programs", "admissions", "fees", "deadlines"],
    "publisher": ["authorship", "publish_dates", "topics"],
    "professional_services": ["services", "credentials", "case_evidence"],
    "generic_org": ["services", "about_depth"],
}
QUESTIONS = {
    "identity": "What is {brand}?",
    "what_it_does": "What does {brand} do / offer?",
    "contact": "How do I contact {brand}?",
    "location": "Where is {brand} based / where does it operate?",
    "price": "How much does {brand} cost?",
    "product_specs": "What are the specifications / what's included?",
    "shipping_returns": "What are {brand}'s shipping and return policies?",
    "availability": "Is it in stock / available?",
    "integrations_or_docs": "What does {brand} integrate with / where are the docs?",
    "trial_or_signup": "Is there a free trial and how do I sign up?",
    "hours": "What are {brand}'s opening hours?",
    "phone": "What is {brand}'s phone number?",
    "services": "What services does {brand} provide?",
    "booking": "How do I book / make an appointment?",
    "programs": "What programs or courses does {brand} offer?",
    "admissions": "What are the admission requirements?",
    "fees": "What are the tuition fees?",
    "deadlines": "What are the application deadlines?",
    "authorship": "Who writes {brand}'s content?",
    "publish_dates": "When was this published or updated?",
    "topics": "What topics does {brand} cover?",
    "credentials": "What are {brand}'s qualifications / accreditations?",
    "case_evidence": "What results has {brand} achieved for clients?",
    "about_depth": "Who is behind {brand} and what is its background?",
}

RX = {
    # NB: a bare "open" is far too loose -- "open government", "open source",
    # "open data" all match it. Require a real day/time pattern or an explicit
    # hours phrase.
    "hours": re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?\s*[-–—to]*\s*"
                        r"(?:(mon|tue|wed|thu|fri|sat|sun)[a-z]*)?\s*:?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)|"
                        r"\b(opening hours|hours of operation|business hours|open daily|"
                        r"open \d{1,2}(?::\d{2})?\s*(?:am|pm))\b", re.I),
    "shipping_returns": re.compile(r"\b(shipping|delivery|returns?|refund|exchange) (policy|within|cost|fee|"
                                   r"period|days)\b|\bfree (shipping|delivery|returns?)\b|"
                                   r"\b\d+[- ]day (returns?|refund|money[- ]back)\b", re.I),
    "availability": re.compile(r"\b(in stock|out of stock|sold out|availability|back ?order|"
                               r"ships? (?:in|within)|lead time)\b", re.I),
    "integrations": re.compile(r"\b(integrat\w+|api|sdk|documentation|docs|webhook|plugin|connector)\b", re.I),
    "trial": re.compile(r"\b(free trial|start free|try (?:it )?free|sign up|get started free|"
                        r"free (?:plan|tier))\b", re.I),
    "booking": re.compile(r"\b(book (?:a|an|now|online)|make (?:a|an) (?:appointment|reservation|booking)|"
                          r"schedule (?:a|an)|reserve (?:a|your)|appointment)\b", re.I),
    "programs": re.compile(r"\b(bachelor|master|b\.?tech|m\.?tech|mba|ph\.?d|diploma|degree|course|"
                           r"programme|program|curriculum|major|undergraduate|postgraduate)\b", re.I),
    "admissions": re.compile(r"\b(admission|eligibility|entry requirement|how to apply|application "
                             r"process|prerequisite|cut ?off|entrance exam)\b", re.I),
    "fees": re.compile(r"\b(tuition|fee structure|fees?|scholarship|financial aid|cost per (?:credit|year|"
                       r"semester))\b", re.I),
    "deadlines": re.compile(r"\b(deadline|last date|closing date|apply by|applications? (?:open|close))\b", re.I),
    "credentials": re.compile(r"\b(accredit\w+|certifi\w+|licens\w+|iso ?\d+|registered|chartered|"
                              r"member of|award|qualification)\b", re.I),
    "case_evidence": re.compile(r"\b(case stud\w+|success stor\w+|testimonial|results?|client stor\w+|"
                                r"we helped|portfolio)\b", re.I),
    "services": re.compile(r"\b(services?|solutions?|what we do|offerings?|capabilit\w+|specialt\w+)\b", re.I),
    "authorship": re.compile(r"\b(by |author|written by|editorial team|our writers|contributor)\b", re.I),
}


def infer_entity_type(bundle):
    pages = bundle.get("pages", [])
    types, text, urls, ctas = set(), [], [], set()
    for p in pages:
        types.update(p.get("jsonld_types", []))
        types.update(t.rsplit("/", 1)[-1] for t in p.get("microdata_types", []))
        text.append(p.get("text_sample", ""))
        urls.append(p["url"].lower())
        ctas.update(p.get("facts", {}).get("cta_matches", []))
    blob = " ".join(text)
    allurls = " ".join(urls)
    reasons = []

    if types & EDU_TYPES or re.search(r"/admission|/academics|/programme|/courses?/", allurls):
        reasons.append(f"schema types {sorted(types & EDU_TYPES) or '[]'} / education paths")
        return "education", reasons
    if types & PUB_TYPES or (sum(1 for u in urls if re.search(r"/(blog|news|article|posts?)/", u)) >= 3):
        reasons.append("news/blog schema types or 3+ article-shaped URLs")
        return "publisher", reasons
    # SaaS is checked BEFORE ecommerce: software vendors commonly emit Product
    # schema too, and misreading one as a shop asks it about shipping and
    # returns, which is nonsense for software.
    if "SoftwareApplication" in types or "WebApplication" in types or \
       (re.search(r"/pricing|/plans", allurls) and RX["integrations"].search(blob)):
        reasons.append("SoftwareApplication schema, or a pricing/plans path plus "
                       "API/integration/docs vocabulary")
        return "saas", reasons
    # Ecommerce needs an actual transaction signal, not merely Product schema.
    has_cart = any(c in ctas for c in ("add to cart", "add to bag", "add to basket"))
    if has_cart or ({"Product", "Offer"} & types and
                    (RX["shipping_returns"].search(blob) or RX["availability"].search(blob))):
        reasons.append("cart CTA present" if has_cart else
                       "Product/Offer schema plus shipping/availability vocabulary")
        return "ecommerce", reasons
    # Local business needs a physical-presence signal, not just hours-like text.
    has_place = bool(types & LOCAL_TYPES) or "PostalAddress" in types or \
        any(p.get("facts", {}).get("postal_codes") for p in pages)
    if types & LOCAL_TYPES or (RX["hours"].search(blob) and has_place):
        reasons.append(f"local-business schema {sorted(types & LOCAL_TYPES) or ''}"
                       " or opening hours together with a postal address")
        return "local_business", reasons
    if RX["credentials"].search(blob) and RX["services"].search(blob):
        reasons.append("services plus credentials/accreditation vocabulary")
        return "professional_services", reasons
    reasons.append("no strong type signal; treated as a generic organisation")
    return "generic_org", reasons


def brand_name(bundle):
    pages = bundle.get("pages", [])
    if not pages:
        return "this brand"
    home = pages[0]
    for node in home.get("jsonld", []):
        for n in _iter_nodes(node):
            if isinstance(n, dict) and n.get("@type") in (
                    "Organization", "LocalBusiness", "Corporation", "WebSite",
                    "CollegeOrUniversity", "EducationalOrganization") and n.get("name"):
                return str(n["name"])[:80]
    og = home.get("og", {}).get("og:site_name")
    if og:
        return og[:80]
    title = home.get("title", "")
    return (re.split(r"[|\-–—:]", title)[0].strip() or "this brand")[:80]


def _iter_nodes(doc):
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


def slot_answered(slot, bundle):
    """Return (answered: bool, evidence: str). Only counts evidence a
    non-JS-executing extractor would actually see."""
    pages = bundle.get("pages", [])
    blob = " ".join(p.get("text_sample", "") for p in pages)
    all_types = set()
    for p in pages:
        all_types.update(p.get("jsonld_types", []))

    def any_fact(key):
        return [v for p in pages for v in p.get("facts", {}).get(key, [])]

    if slot == "identity":
        home = pages[0]
        desc = (home.get("meta_description") or "").strip()
        h1 = next((h[1] for h in home.get("headings", []) if h[0] == 1), "")
        ok = bool(desc) or bool(h1) or bool({"Organization", "WebSite"} & all_types)
        return ok, (f"meta description present ({len(desc)} chars); H1={h1[:60]!r}" if ok
                    else "homepage has no meta description, no H1 and no Organization schema")
    if slot == "what_it_does":
        home = pages[0]
        words = home.get("citability", {}).get("word_count", 0)
        ok = words >= 60
        return ok, (f"homepage exposes {words} words of extractable text" if ok else
                    f"homepage exposes only {words} words of extractable text")
    if slot == "contact":
        emails, tels = any_fact("emails"), any_fact("tel_links")
        has_form = any(p.get("forms", {}).get("count", 0) for p in pages)
        ok = bool(emails or tels)
        return ok, (f"{len(set(emails))} email(s), {len(set(tels))} tel: link(s) found" if ok
                    else ("no email or tel: link in extractable text" +
                          ("; a contact form exists but a form is not an extractable fact"
                           if has_form else "")))
    if slot == "location":
        addr = any_fact("postal_codes")
        has_addr_schema = "PostalAddress" in all_types
        ok = bool(addr) or has_addr_schema
        return ok, ("PostalAddress schema present" if has_addr_schema else
                    (f"postal code(s) found in text: {sorted(set(addr))[:2]}" if ok
                     else "no postal address or PostalAddress schema found"))
    if slot == "price":
        prices = any_fact("prices")
        ok = bool(prices)
        return ok, (f"{len(set(prices))} distinct price string(s) in extractable text, "
                    f"e.g. {sorted(set(prices))[:3]}" if ok
                    else "no currency figure anywhere in the extracted text of the sampled pages")
    if slot == "product_specs":
        specs = max((p["citability"]["tier1"]["spec_pairs"] for p in pages), default=0)
        tables = any(p["citability"]["tier1"]["has_spec_table"] for p in pages)
        ok = specs >= 3 or tables
        return ok, (f"max {specs} attribute:value pairs; spec table present={tables}" if ok
                    else f"no spec table and at most {specs} attribute:value pairs on any page")
    if slot == "phone":
        tels, phones = any_fact("tel_links"), any_fact("phones")
        ok = bool(tels or phones)
        return ok, (f"{len(set(tels or phones))} phone value(s) found" if ok
                    else "no phone number in extractable text")
    if slot == "hours":
        ok = bool(RX["hours"].search(blob)) or "OpeningHoursSpecification" in all_types
        return ok, ("opening-hours pattern or OpeningHoursSpecification found" if ok
                    else "no opening hours in text or schema")
    if slot == "publish_dates":
        dated = sum(1 for p in pages if p.get("jsonld_dates") or p["facts"]["updated_years"])
        ok = dated >= max(1, len(pages) // 3)
        return ok, f"{dated}/{len(pages)} sampled pages expose a date"
    if slot == "about_depth":
        ok = any(re.search(r"/about", p["url"], re.I) and p["citability"]["word_count"] > 120
                 for p in pages)
        return ok, ("an /about page with substantive text was found" if ok
                    else "no substantive /about page in the sampled crawl")
    if slot == "topics":
        headings = sum(len(p.get("headings", [])) for p in pages)
        ok = headings >= 8
        return ok, f"{headings} headings across sampled pages"
    if slot == "integrations_or_docs":
        ok = bool(RX["integrations"].search(blob))
        return ok, ("integration/API/docs vocabulary present" if ok
                    else "no integration, API or documentation vocabulary found")

    key = {"shipping_returns": "shipping_returns", "availability": "availability",
           "trial_or_signup": "trial", "booking": "booking", "programs": "programs",
           "admissions": "admissions", "fees": "fees", "deadlines": "deadlines",
           "credentials": "credentials", "case_evidence": "case_evidence",
           "services": "services", "authorship": "authorship"}.get(slot)
    if key:
        ok = bool(RX[key].search(blob))
        return ok, (f"matched {key} vocabulary in extractable text" if ok
                    else f"no {slot.replace('_', ' ')} information found in extractable text")
    return True, "slot not evaluated"


def analyze(bundle):
    findings = []
    pages = bundle.get("pages", [])
    if not pages:
        return findings
    etype, reasons = infer_entity_type(bundle)
    brand = brand_name(bundle)
    slots = UNIVERSAL_SLOTS + TYPE_SLOTS.get(etype, [])

    answered, missing = [], []
    for slot in slots:
        ok, ev = slot_answered(slot, bundle)
        (answered if ok else missing).append((slot, ev))

    coverage = len(answered) / len(slots) if slots else 1.0
    detail = "; ".join(f"{QUESTIONS[s].format(brand=brand)} -> {e}" for s, e in missing[:6])

    if missing:
        if coverage < 0.5:
            sev, prio = "critical", "critical"
        elif coverage < 0.75:
            sev, prio = "high", "high"
        else:
            sev, prio = "medium", "medium"
        findings.append({
            "title": f"{len(missing)} of {len(slots)} core questions about this brand cannot be "
                     f"answered from its own extractable content",
            "severity": sev, "category": "discoverability",
            "evidence": f"Entity type inferred as '{etype}' ({reasons[0]}). Sampled "
                        f"{len(pages)} page(s). Unanswerable: {detail}.",
            "mechanism": "An assistant answering a question about a brand builds the answer from "
                         "what it can reach, read and quote at that moment. Where the answer is "
                         "not present as extractable text, the assistant either omits the brand "
                         "entirely or fills the gap from a third-party source it does not control "
                         "-- which is how brands get described inaccurately. Each gap below is a "
                         "specific question your site currently cannot answer.",
            "suggested_action": {
                "summary": "Publish each missing fact as plain, visible text on a relevant page: "
                           + ", ".join(QUESTIONS[s].format(brand=brand) for s, _ in missing[:5]),
                "priority": prio,
                "how": "Put the answer in body text, not only in an image, a PDF, a form, or a "
                       "JS-rendered widget. Stating it once, plainly, is enough."},
            "signal_tier": 1, "evidence_tier": "measured", "source_skill": SKILL,
            "answerability": {"entity_type": etype, "coverage": round(coverage, 2),
                              "answered": [s for s, _ in answered],
                              "unanswered": [s for s, _ in missing]},
        })

    # Facts that exist but only in a form a crawler cannot read are a distinct,
    # more actionable failure than facts that are simply absent.
    locked = [r for p in pages for r in p.get("extractability_risks", [])]
    if locked and missing:
        modes = sorted({r["mode"] for r in locked})
        findings.append({
            "title": "Some missing answers may exist on the page but in a non-extractable form",
            "severity": "high", "category": "discoverability",
            "evidence": f"Detected extractability risks across sampled pages: {', '.join(modes[:6])}. "
                        f"These co-occur with {len(missing)} unanswerable question(s).",
            "mechanism": "A fact rendered inside an image, canvas, PDF, third-party embed or "
                         "client-side template is visible to a human but absent for a text "
                         "extractor. This is the most recoverable class of gap -- the content "
                         "already exists and only needs a text equivalent.",
            "suggested_action": {
                "summary": "Add a plain-text equivalent beside each non-textual element carrying a "
                           "fact (prices in images, spec tables as graphics, PDF-only documents).",
                "priority": "high",
                "how": "A short HTML table or paragraph next to the visual is sufficient; the "
                       "visual can stay."},
            "signal_tier": 1, "evidence_tier": "measured", "source_skill": SKILL,
        })
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evidence", required=True, help="evidence.json from evidence_collector.py")
    args = ap.parse_args()
    if not os.path.exists(args.evidence):
        print(f"error: evidence file not found: {args.evidence}", file=sys.stderr)
        sys.exit(2)
    with open(args.evidence, encoding="utf-8") as fh:
        bundle = json.load(fh)
    findings = analyze(bundle) if bundle.get("entry_reachable") else []
    json.dump({"skill": SKILL, "site": bundle.get("site"), "findings": findings},
              sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
