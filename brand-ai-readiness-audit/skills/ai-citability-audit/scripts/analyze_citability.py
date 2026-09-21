#!/usr/bin/env python3
"""ai-citability-audit: is this page the KIND of page answer engines quote?

Reads an evidence bundle produced by crawl-render-audit's evidence_collector.py
and evaluates the signals that measurably separate cited from uncited pages.

Two tiers, and the ORDER IS LOAD-BEARING:

  TIER 1 -- gatekeepers. Measured odds ratios above 100 in a 252k-trial
    controlled study across 6 current LLMs. Failing one of these can eliminate
    citation odds regardless of every other strength on the page.

  TIER 2 -- structure. Only pays off once tier 1 passes. A head-to-head study
    found formatting "negligible", while a structural study measured +17.3%;
    both are true, because formatting cannot rescue a page that fails a
    gatekeeper. So tier-2 findings are deliberately capped at medium severity
    and are explicitly gated on tier 1 being clean.

Every threshold traces to a specific measured result -- see
references/evidence-base.md for the effect size and source behind each.

Usage:
  python3 analyze_citability.py --evidence evidence.json
  python3 analyze_citability.py --url https://example.com   (collects first)

Emits JSON to stdout: {"skill", "site", "findings": [...]}; diagnostics to stderr.
Exit codes: 0 ok, 2 bad/missing evidence, 3 collector unavailable for --url.
"""
import argparse
import json
import os
import subprocess
import sys
from urllib.parse import urlparse

SKILL = "ai-citability-audit"


def finding(title, severity, evidence, mechanism, action, priority,
            tier, evidence_tier, how=None, page=None):
    sa = {"summary": action, "priority": priority}
    if how:
        sa["how"] = how
    f = {"title": title, "severity": severity, "category": "discoverability",
         "evidence": evidence, "mechanism": mechanism, "suggested_action": sa,
         "signal_tier": tier, "evidence_tier": evidence_tier, "source_skill": SKILL}
    if page:
        f["page"] = page
    return f


def load_evidence(args):
    if args.evidence:
        if not os.path.exists(args.evidence):
            print(f"error: evidence file not found: {args.evidence}", file=sys.stderr)
            sys.exit(2)
        with open(args.evidence, encoding="utf-8") as fh:
            return json.load(fh)
    here = os.path.dirname(os.path.abspath(__file__))
    collector = os.path.normpath(os.path.join(
        here, "..", "..", "crawl-render-audit", "scripts", "evidence_collector.py"))
    if not os.path.exists(collector):
        print("error: no --evidence given and the shared collector was not found at\n"
              f"  {collector}\nRun crawl-render-audit's evidence_collector.py first and "
              "pass its output with --evidence.", file=sys.stderr)
        sys.exit(3)
    out = os.path.join(os.getcwd(), "evidence.json")
    print(f"[{SKILL}] collecting evidence -> {out}", file=sys.stderr)
    subprocess.run([sys.executable, collector, args.url, "--out", out],
                   check=True, capture_output=True, text=True, timeout=280)
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


# Purchase-intent CTAs. Deliberately narrow: a page is only treated as
# commercial on POSITIVE evidence of a transaction, never on a URL keyword
# alone. A guidance article at /buying-your-first-home is not a product page,
# and flagging it for "no price" would be a false positive.
# Only unambiguous transaction actions. "subscribe" (newsletter), "contact us",
# "get a quote" and "book now" are lead-gen or engagement CTAs that appear on
# plenty of pages selling nothing -- during testing "subscribe" on a government
# department's newsletter link wrongly marked the page commercial.
PURCHASE_CTAS = ("add to cart", "buy now", "add to bag", "add to basket",
                 "proceed to checkout")
PRICING_PATH = ("/pricing", "/plans", "/price", "/product/", "/products/", "/shop/", "/store/")


def commercial_pages(pages):
    """Pages where a buyer-intent question would land.

    Requires positive transactional evidence: an actual currency figure, a
    purchase CTA, or a dedicated pricing/product path segment. Substring
    matching on words like 'buy' anywhere in a URL is far too loose.
    """
    out = []
    for p in pages:
        # Path only -- not the full URL. A tracking/referrer query param such
        # as "?ref_page=/pricing" on an unrelated page (observed live on
        # github.com's own /enterprise/contact links) contains a PRICING_PATH
        # segment without the page itself being a pricing page.
        path = urlparse(p["url"]).path.lower()
        ctas = set(p.get("facts", {}).get("cta_matches", []))
        has_price = p["citability"]["tier1"]["has_price"]
        has_cta = any(c in ctas for c in PURCHASE_CTAS)
        on_pricing_path = any(seg in path for seg in PRICING_PATH)
        if has_price or has_cta or (on_pricing_path and p["citability"]["word_count"] > 80):
            out.append(p)
    return out


def analyze(bundle):
    findings = []
    pages = [p for p in bundle.get("pages", []) if p.get("citability")]
    if not pages:
        return findings
    home = pages[0]
    total_words = sum(p["citability"]["word_count"] for p in pages)

    # ---------------- TIER 1: gatekeepers ----------------

    # Query-term coverage: does the page's opening actually contain the terms it
    # claims to be about? Largest measured gatekeeper of all.
    weak_cov = [p for p in pages
                if (p["citability"]["tier1"]["query_term_coverage"] or 1) < 0.5
                and p["citability"]["word_count"] > 120]
    if weak_cov:
        ex = weak_cov[0]
        findings.append(finding(
            "Page topic terms are missing from the opening text",
            "high" if len(weak_cov) > len(pages) / 2 else "medium",
            f"{len(weak_cov)}/{len(pages)} sampled pages have under 50% of their own "
            f"title/H1 terms present in the first 200 words. Example: {ex['url']} "
            f"covers {int((ex['citability']['tier1']['query_term_coverage'] or 0)*100)}% "
            f"-- missing: {', '.join(ex['citability']['tier1']['uncovered_claim_terms'][:6]) or 'n/a'}.",
            "Term coverage between the query and the passage is the single largest measured "
            "gatekeeper for citation (odds ratios above 10,000 across 6 models). This is about "
            "COVERAGE, not repetition -- stating the subject once, early, in plain text. "
            "Keyword stuffing measured WORSE than doing nothing (-8.3%), so do not repeat terms.",
            "Restate the page's actual subject in plain language in the first paragraph, using "
            "the same words a person would type when asking about it.",
            "high", tier=1, evidence_tier="measured",
            how="Aim for the first 150-200 words to naturally contain the title/H1 terms once each.",
            page=ex["url"]))

    # Explicit price on commercial pages -- unanimous gatekeeper, OR > 100.
    comm = commercial_pages(pages)
    # Only claim a missing price where the page itself shows transactional
    # intent (a purchase CTA or a dedicated pricing path). Otherwise we cannot
    # distinguish "hiding the price" from "not selling anything here".
    priceless = [p for p in comm
                 if not p["citability"]["tier1"]["has_price"]
                 and (any(c in set(p.get("facts", {}).get("cta_matches", []))
                          for c in PURCHASE_CTAS)
                      or any(seg in urlparse(p["url"]).path.lower() for seg in PRICING_PATH))]
    if priceless:
        findings.append(finding(
            "Commercial pages state no explicit price in extractable text",
            "high",
            f"{len(priceless)}/{len(comm)} pricing/product-like pages contain no currency "
            f"figure in the extracted text. Examples: "
            f"{', '.join(p['url'] for p in priceless[:3])}.",
            "A visible price is a citation gatekeeper: its absence measured an OR above 100 "
            "against being cited, unanimously across all 6 models tested -- missing price alone "
            "can eliminate citation odds regardless of other content strengths. 'Contact us for "
            "pricing' reads to an answer engine as 'no price exists'.",
            "Publish a real figure, a starting-from figure, or an explicit range as plain text "
            "on each commercial page.",
            "high", tier=1, evidence_tier="measured",
            how="Even 'from $49/month' or 'typical projects run $5,000-$15,000' is extractable; "
                "'request a quote' is not."))

    # Recency. An OLD date measured WORSE than no date; a RECENT date beats both.
    stale, undated = [], []
    for p in pages:
        yrs = [int(y) for y in (p["facts"]["updated_years"] + p["facts"]["copyright_years"])]
        jd = p.get("jsonld_dates", {})
        if not yrs and not jd:
            undated.append(p)
        elif yrs and max(yrs) <= _current_year(bundle) - 3:
            stale.append((p, max(yrs)))
    if stale:
        findings.append(finding(
            "Pages carry visibly stale dates",
            "high",
            f"{len(stale)} sampled page(s) show a most-recent date 3+ years old. Examples: " +
            "; ".join(f"{p['url']} -> {y}" for p, y in stale[:3]) + ".",
            "Recency is a unanimous citation gatekeeper (recent vs old measured OR above 10,000). "
            "Critically, an OLD date scored WORSE than showing no date at all -- but a RECENT "
            "date beats both. So the fix is to genuinely refresh and re-date, never to delete dates.",
            "Review and update these pages, then set an accurate visible 'last updated' date and "
            "a matching dateModified.",
            "high", tier=1, evidence_tier="measured",
            how="Do NOT strip dates to look evergreen -- undated measured worse than recently-dated."))
    if undated and len(undated) >= max(2, len(pages) // 2):
        findings.append(finding(
            "Most pages publish no date at all",
            "medium",
            f"{len(undated)}/{len(pages)} sampled pages expose no visible updated/copyright year "
            "and no JSON-LD date field.",
            "A recent timestamp measured a clear citation advantage over no timestamp in every "
            "model tested. Undated content forces an answer engine to guess at currency, and it "
            "guesses conservatively.",
            "Add an accurate, visible published/updated date to substantive pages, mirrored in "
            "dateModified.",
            "medium", tier=1, evidence_tier="measured"))

    # Evidence for claims: statistics, attributed quotes, outbound authority.
    thin = [p for p in pages
            if p["citability"]["word_count"] > 250
            and p["citability"]["tier1"]["statistics_count"] == 0
            and p["citability"]["tier1"]["attributed_quotes"] == 0
            and p["citability"]["tier1"]["external_domains"] == 0]
    if thin:
        findings.append(finding(
            "Substantive pages contain no quotable evidence",
            "high" if len(thin) >= max(2, len(pages) // 2) else "medium",
            f"{len(thin)}/{len(pages)} pages over 250 words contain zero statistics, zero "
            f"attributed quotes and zero outbound links to any external domain. Examples: "
            f"{', '.join(p['url'] for p in thin[:3])}.",
            "Adding statistics measured the largest single content lift in the original GEO study "
            "(+30.6% visibility; up to +37% subjective impression on a live engine), and quotations "
            "the largest overall (+41%). Claims backed by evidence beat unbacked claims by odds "
            "ratios from 2.1 up to >10,000. Answer engines quote body text -- give them something "
            "concrete and attributable to lift.",
            "Add specific, verifiable figures and attributed statements to the body copy of these "
            "pages -- concrete numbers with units and dates, named sources for claims.",
            "high", tier=1, evidence_tier="measured",
            how="One real statistic per ~100 words of substantive copy is a reasonable target; "
                "attribute each to a named, linkable source."))

    # Hedging suppresses citation.
    hedgy = [p for p in pages if p["citability"]["tier1"]["hedges_per_100w"] > 3.0
             and p["citability"]["word_count"] > 200]
    if hedgy:
        ex = hedgy[0]
        findings.append(finding(
            "Key claims are heavily hedged",
            "medium",
            f"{len(hedgy)} page(s) exceed 3 hedging terms per 100 words "
            f"(e.g. {ex['url']} at {ex['citability']['tier1']['hedges_per_100w']}/100w; "
            f"{ex['citability']['tier1']['hedged_numbers']} hedged numeric claims).",
            "Confidently-stated claims measured a citation advantage over hedged equivalents "
            "(OR 2.7-599). Note the precise finding: REMOVING hedges is what is supported. "
            "Adding persuasive or authoritative tone measured NO significant improvement, so this "
            "is about precision, not salesmanship.",
            "Replace hedged quantities with exact figures where you know them "
            "('approximately 40%' -> '38%'), and drop filler qualifiers around facts you can state "
            "plainly.",
            "medium", tier=1, evidence_tier="measured",
            how="Do not overcorrect into promotional language -- that measured no benefit and "
                "risks being read as manipulation."))

    # Specs / comparisons -- completeness differentiators on commercial pages.
    # Require a real sample before generalising about the commercial surface.
    if len(comm) >= 2:
        nospec = [p for p in comm if p["citability"]["tier1"]["spec_pairs"] < 3
                  and not p["citability"]["tier1"]["has_spec_table"]]
        if nospec:
            findings.append(finding(
                "Product pages lack structured specifications",
                "medium",
                f"{len(nospec)}/{len(comm)} commercial pages expose fewer than 3 "
                f"attribute:value spec pairs and no spec table. Examples: "
                f"{', '.join(p['url'] for p in nospec[:3])}.",
                "Presence of technical specifications measured OR 8.6-243 for citation across "
                "models -- it is one of the strongest completeness differentiators, because it "
                "gives the engine discrete attributes it can match against a specific question.",
                "Add a specification table or definition list of concrete attributes and values "
                "to each product/service page.",
                "medium", tier=1, evidence_tier="measured"))
        nocomp = [p for p in comm if p["citability"]["tier1"]["comparison_markers"] == 0]
        if nocomp and len(nocomp) == len(comm):
            findings.append(finding(
                "No comparison against alternatives anywhere in the sampled pages",
                "medium",
                f"None of the {len(comm)} commercial pages contain comparison language "
                "(vs / compared to / alternative to / instead of).",
                "Pages that compare against alternatives measured OR 1.6-7.5 for citation. "
                "Separately, ranked comparison and 'best-of' content accounts for the single "
                "largest share of content citations in AI answers (~36%) -- far more than any "
                "brand's own marketing pages.",
                "Publish an honest comparison page covering how you differ from named "
                "alternatives, including where you are not the right fit.",
                "medium", tier=1, evidence_tier="correlational",
                how="Omitting genuine limitations is classed as a manipulation pattern and is "
                    "increasingly detected -- state trade-offs honestly."))

    # ---------------- TIER 2: structure (gated on tier 1) ----------------
    tier1_failures = [f for f in findings if f["signal_tier"] == 1
                      and f["severity"] in ("critical", "high")]
    gate = (" Fix the tier-1 gatekeeper findings first -- structural work measured negligible "
            "benefit on pages that still fail a gatekeeper." if tier1_failures else "")

    long_secs = [p for p in pages if p["citability"]["tier2"]["sections_over_300w"] >= 2]
    if long_secs:
        ex = long_secs[0]
        findings.append(finding(
            "Content sections run long enough to bury facts mid-passage",
            "medium",
            f"{len(long_secs)} page(s) have 2+ sections over 300 words "
            f"(e.g. {ex['url']}: {ex['citability']['tier2']['sections_over_300w']} long sections, "
            f"{ex['citability']['tier2']['sections_in_150_300_band']} in the 150-300 band).",
            "Information in the middle of a long passage is retrieved markedly worse than "
            "information at its start or end -- and in controlled testing, a fact in the middle "
            "position scored BELOW the baseline of not supplying the document at all. The trough "
            "deepens as the passage grows." + gate,
            "Break long sections into 150-300 word chunks under their own descriptive subheadings, "
            "and move each section's key fact to its opening sentence.",
            "medium", tier=2, evidence_tier="measured",
            page=ex["url"]))

    shallow = [p for p in pages if p["citability"]["word_count"] > 400
               and p["citability"]["tier2"]["heading_depth"] < 2]
    if shallow:
        findings.append(finding(
            "Long pages have almost no heading structure",
            "low",
            f"{len(shallow)} page(s) exceed 400 words with heading depth below 2. Examples: "
            f"{', '.join(p['url'] for p in shallow[:3])}.",
            "Structural fields (title, headings, meta description) measured a ~+22% retrieval "
            "hit-rate improvement -- they help a document get FOUND. They do not make it quoted; "
            "body-text evidence does that." + gate,
            "Add a descriptive heading hierarchy (H2/H3) that names the questions each section "
            "answers.",
            "low", tier=2, evidence_tier="measured"))

    no_intro = [p for p in pages if p["citability"]["word_count"] > 300
                and p["citability"]["tier2"]["intro_summary_words"] < 25]
    if no_intro:
        findings.append(finding(
            "Pages open without a summary paragraph",
            "low",
            f"{len(no_intro)} page(s) over 300 words have under 25 words between the H1 and the "
            f"first subheading. Examples: {', '.join(p['url'] for p in no_intro[:3])}.",
            "Retrieval favours content that answers early, and the opening position is the "
            "strongest slot in a passage. Some engine architectures weight the opening especially "
            "heavily when judging a batch of retrieved documents." + gate,
            "Open each substantive page with a 40-120 word summary that directly answers the "
            "question the page exists to answer.",
            "low", tier=2, evidence_tier="measured"))

    if total_words and len(pages) > 2:
        thin_pages = [p for p in pages if p["citability"]["word_count"] < 150]
        if len(thin_pages) >= max(2, len(pages) // 2):
            findings.append(finding(
                "Most sampled pages are very thin",
                "medium",
                f"{len(thin_pages)}/{len(pages)} sampled pages contain under 150 words of "
                "extracted text.",
                "Depth of coverage measured OR 4-10,000+ for citation. Thin pages rarely contain "
                "enough quotable substance to be selected as a source, and they also suggest the "
                "real content may not be reaching the extractor at all -- cross-check the "
                "crawl-render findings for a rendering gap before treating this as purely editorial.",
                "Expand the substantive pages with concrete detail, or consolidate thin pages into "
                "fewer, richer ones.",
                "medium", tier=1, evidence_tier="measured"))

    return findings


def _current_year(bundle):
    try:
        return int(bundle.get("collected_at", "2026")[:4])
    except (ValueError, TypeError):
        return 2026


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evidence", help="path to evidence.json from evidence_collector.py")
    ap.add_argument("--url", help="collect evidence for this URL first (slower)")
    args = ap.parse_args()
    if not args.evidence and not args.url:
        ap.error("provide --evidence (preferred) or --url")

    bundle = load_evidence(args)
    findings = analyze(bundle) if bundle.get("entry_reachable") else []
    json.dump({"skill": SKILL, "site": bundle.get("site"), "findings": findings},
              sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
