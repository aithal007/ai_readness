#!/usr/bin/env python3
"""Zero-dependency regression tests for the marketplace analyzers.

Run:  python3 tests/run_tests.py
Exit: 0 all pass, 1 one or more failed.

These are deliberately small hand-built evidence bundles that exercise the
false-positive guards and edge-case handling. They do NOT hit the network.
"""
import importlib.util
import pathlib
import re
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def _load(mod_path):
    spec = importlib.util.spec_from_file_location(mod_path.stem, mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


collector = _load(SKILLS / "crawl-render-audit" / "scripts" / "evidence_collector.py")
crawl = _load(SKILLS / "crawl-render-audit" / "scripts" / "analyze_crawl_render.py")
engage = _load(SKILLS / "engagement-audit" / "scripts" / "analyze_engagement.py")
fresh = _load(SKILLS / "freshness-corroboration-audit" / "scripts" / "analyze_freshness.py")
run_audit = _load(SKILLS / "audit-orchestrator" / "scripts" / "run_audit.py")
finalize = _load(SKILLS / "audit-orchestrator" / "scripts" / "finalize_report.py")
critic = _load(SKILLS / "evidence-critic" / "scripts" / "critique_findings.py")
citab = _load(SKILLS / "ai-citability-audit" / "scripts" / "analyze_citability.py")

from datetime import datetime, timezone

TODAY = datetime(2026, 9, 9, tzinfo=timezone.utc)
_results = []


def check(name, fn):
    try:
        fn()
        _results.append((name, None))
    except Exception as e:  # noqa: BLE001
        _results.append((name, "".join(traceback.format_exception_only(type(e), e)).strip()))


def _page(**kw):
    base = {
        "url": "https://x.test/", "final_url": "https://x.test/", "status": 200, "error": None,
        "depth": 0, "https": True, "headers": {}, "title": "X", "lang": "en",
        "meta_description": "", "headings": [[1, "X"]], "jsonld_types": [],
        "text_sample": "hello world " * 30, "word_count": 60,
        "links_internal": [["https://x.test/a", "A"], ["https://x.test/b", "B"]],
        "links_external": [], "images_total": 0, "images_missing_alt": 0,
        "viewport": True, "forms": {"count": 0, "search": False, "inputs": 0, "labeled": 0,
                                    "submits_offsite": False, "has_password": False},
        "scripts": {"total": 1, "external": 0, "head_blocking": 0, "inline_bytes": 0},
        "spa_root": False, "noscript_len": 0,
        "facts": {"emails": [], "tel_links": [], "phones": [], "prices": [], "postal_codes": [],
                  "hours_mentions": 0, "founded_years": [], "copyright_years": [],
                  "updated_years": [], "coming_soon": [], "cta_matches": [], "login_wall": False},
        "citability": {"word_count": 60},
    }
    base.update(kw)
    return base


def _bundle(**kw):
    base = {"schema_version": "2.0.0", "site": "https://x.test/", "domain": "x.test",
            "entry_reachable": True, "robots": {"present": True, "star_allowed_root": True,
                                                "agents": {}, "content_signals": {}},
            "ua_probe": {}, "sitemap": {"total_urls_found": 3}, "wellknown": {},
            "pages": [_page()], "link_graph": {"https://x.test/": []},
            "stats": {"pages_fetched": 1, "failures": []}}
    base.update(kw)
    return base


# --- collector: copyright range parsing -----------------------------------
def t_copyright_range():
    html = '<footer>&copy; 2001-2026 Example Foundation</footer>'
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["copyright_years"] == ["2026"], facts["copyright_years"]


def t_copyright_single_year_still_flags():
    html = '<footer>Copyright 2019 Old Site</footer>'
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["copyright_years"] == ["2019"], facts["copyright_years"]


def t_copyright_endash_range():
    html = '<p>© 2015 – 2026 Foo</p>'
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["copyright_years"] == ["2026"], facts["copyright_years"]


def t_copyright_range_split_by_react_hydration_comment():
    # React/Next.js SSR streaming interpolates each number separately and
    # inserts an empty <!-- --> comment between them, e.g. flipkart.com's
    # real footer markup: "&copy; 2007-<!-- -->2026<!-- --> Flipkart.com".
    # That comment used to sit inside the range's "-" gap and break the
    # range match, so only the (old) start year was ever captured -- a
    # false "stale" finding on a page updated today.
    html = '<footer>&copy; 2007-<!-- -->2026<!-- --> Flipkart.com</footer>'
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["copyright_years"] == ["2026"], facts["copyright_years"]


def t_copyright_range_ending_old_still_flags():
    # item 1: a real range whose END is old must NOT be suppressed
    html = '<footer>© 2005-2019 Abandoned Project</footer>'
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["copyright_years"] == ["2019"], facts["copyright_years"]
    b = _bundle(pages=[_page(facts={**_page()["facts"], "copyright_years": ["2019"]})])
    assert any("stale" in f["title"].lower() for f in fresh.analyze(b, TODAY))


# --- collector: phone extraction must not swallow bare digit runs ---------
def t_phone_rejects_unbroken_digit_run():
    # python.org's homepage shows a "66.66666666666667%" developer-survey
    # stat; stripped of the decimal point that reads as a 15-digit run with
    # no separators at all -- not remotely phone-shaped -- but the old regex
    # had every separator optional, so it matched anyway.
    html = "<p>66.66666666666667% of developers surveyed said so.</p>"
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["phones"] == [], facts["phones"]


def t_phone_still_detects_hyphenated_number():
    html = "<p>Call us at 1-858-712-8966 for support.</p>"
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["phones"] == ["1-858-712-8966"], facts["phones"]


def t_phone_still_detects_spaced_international_number():
    html = "<p>Reach the team on 89 144 233 377 during business hours.</p>"
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["phones"] == ["89 144 233 377"], facts["phones"]


def t_phone_still_detects_parenthesised_number():
    html = "<p>Front desk: (555) 123-4567.</p>"
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["phones"] == ["(555) 123-4567"], facts["phones"]


def t_phone_rejects_tracking_id_style_digit_run():
    html = "<p>Order reference 4021558873321.</p>"
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["phones"] == [], facts["phones"]


# --- collector: crawler must not follow auth-walled signup links ----------
def t_crawlable_skips_github_style_join_path():
    # github.com's own signup flow is /join (not /signup), so it slipped
    # past SKIP_PATH_WORDS: the crawler fetched it, got a 403 (it requires
    # an authenticated session), and the link-rot check then reported a
    # live, working link as "broken" / site-wide link rot.
    assert not collector.crawlable("https://github.com/join?plan=free", "github.com")


def t_crawlable_still_follows_ordinary_content_paths():
    assert collector.crawlable("https://github.com/torvalds/linux", "github.com")


# --- citability: pricing-path check must read the URL PATH, not the whole
# --- URL string (tracking query params can smuggle a path-shaped segment) --
def _citab_page(url, cta_matches=(), has_price=False, word_count=200):
    p = _page(url=url, word_count=word_count,
              facts={**_page()["facts"], "cta_matches": list(cta_matches)})
    p["citability"] = {
        "word_count": word_count,
        "tier1": {
            "has_price": has_price, "query_term_coverage": 1.0, "uncovered_claim_terms": [],
            "hedges_per_100w": 0, "statistics_count": 1, "attributed_quotes": 1,
            "external_domains": 1, "spec_pairs": 99, "has_spec_table": True,
            "comparison_markers": 1,
        },
        "tier2": {
            "sections_over_300w": 0, "sections_in_150_300_band": 0,
            "heading_depth": 2, "intro_summary_words": 30,
        },
    }
    return p


def t_commercial_pages_ignores_pricing_word_in_query_string():
    # github.com's real "Contact Sales" links carry "?ref_page=/pricing" for
    # analytics -- that must not make the contact page itself "commercial".
    pg = _citab_page("https://github.com/enterprise/contact?ref_page=/pricing&ref_cta=Contact",
                     cta_matches=["get started", "sign up", "subscribe"])
    assert citab.commercial_pages([pg]) == []


def t_commercial_pages_still_detects_real_pricing_path():
    pg = _citab_page("https://example.test/pricing", word_count=150)
    assert citab.commercial_pages([pg]) == [pg]


def t_citability_no_price_finding_for_contact_page_with_tracking_query():
    pg = _citab_page("https://github.com/enterprise/contact?ref_page=/pricing&ref_cta=Contact",
                     cta_matches=["get started", "sign up", "subscribe"])
    b = _bundle(pages=[pg])
    titles = [f["title"] for f in citab.analyze(b)]
    assert not any("no explicit price" in t.lower() for t in titles), titles


def t_citability_still_flags_real_pricing_page_missing_a_price():
    pg = _citab_page("https://example.test/pricing", word_count=150)
    b = _bundle(pages=[pg])
    titles = [f["title"] for f in citab.analyze(b)]
    assert any("no explicit price" in t.lower() for t in titles), titles


# --- freshness: stale-date FP now gone -----------------------------------
def t_fresh_no_stale_on_current_range():
    b = _bundle(pages=[_page(facts={**_page()["facts"], "copyright_years": ["2026"]})])
    titles = [f["title"] for f in fresh.analyze(b, TODAY)]
    assert not any("stale" in t.lower() for t in titles), titles


def t_fresh_still_flags_genuinely_old():
    b = _bundle(pages=[_page(facts={**_page()["facts"], "copyright_years": ["2019"]})])
    titles = [f["title"] for f in fresh.analyze(b, TODAY)]
    assert any("stale" in t.lower() for t in titles), titles


# --- engagement: pricing/offering not-applicable on non-commercial -------
def t_engage_non_commercial_no_pricing_fp():
    b = _bundle()  # no prices, no commercial CTA, no Product schema
    fs = engage.analyze(b)
    missing = [f for f in fs if f["title"] == "Common visitor goals have no reachable page"]
    assert not missing or "pricing" not in missing[0]["evidence"], missing
    assert not missing or "offering" not in missing[0]["evidence"], missing


def t_engage_commercial_still_flags_pricing():
    pg = _page(facts={**_page()["facts"], "cta_matches": ["buy now"]})
    b = _bundle(pages=[pg], link_graph={"https://x.test/": []})
    fs = engage.analyze(b)
    missing = [f for f in fs if f["title"] == "Common visitor goals have no reachable page"]
    assert missing and "pricing" in missing[0]["evidence"], [f["title"] for f in fs]


def t_engage_catalogue_prices_are_commercial():
    pgs = [_page(url=f"https://x.test/p{i}", facts={**_page()["facts"], "prices": ["$9"]})
           for i in range(6)]
    b = _bundle(pages=pgs, link_graph={"https://x.test/": []})
    fs = engage.analyze(b)
    missing = [f for f in fs if f["title"] == "Common visitor goals have no reachable page"]
    assert missing and "offering" in missing[0]["evidence"], [f["title"] for f in fs]


def t_engage_contact_always_universal():
    b = _bundle()
    fs = engage.analyze(b)
    missing = [f for f in fs if f["title"] == "Common visitor goals have no reachable page"]
    assert missing and "contact" in missing[0]["evidence"], [f["title"] for f in fs]


# --- run_audit: blocker diagnosis --------------------------------------
def t_diag_dns():
    b = _bundle(entry_reachable=False, pages=[],
                entry_error="URLError: <urlopen error [Errno 11001] getaddrinfo failed>")
    f = run_audit.diagnose_blocker(b)
    assert f and "DNS" in f["title"], f


def t_diag_tls():
    b = _bundle(entry_reachable=False, pages=[],
                entry_error="SSLCertVerificationError: certificate has expired")
    f = run_audit.diagnose_blocker(b)
    assert f and "TLS" in f["title"], f


def t_diag_timeout_undetermined():
    b = _bundle(entry_reachable=False, pages=[], entry_error="TimeoutError: timed out")
    f = run_audit.diagnose_blocker(b)
    assert f and f.get("status") == "not_observable" and "undetermined" in f["title"].lower(), f


def t_diag_403_cdn():
    pg = _page(status=403, headers={"server": "cloudflare", "cf-ray": "abc"},
               text_sample="attention required | cloudflare")
    b = _bundle(pages=[pg])
    f = run_audit.diagnose_blocker(b)
    assert f and ("challenge" in f["title"].lower() or "403" in f["title"]), f
    assert "Cloudflare" in f["title"], f


def t_diag_reachable_returns_none():
    assert run_audit.diagnose_blocker(_bundle()) is None


def t_diag_401():
    pg = _page(status=401, headers={"www-authenticate": "Basic"})
    f = run_audit.diagnose_blocker(_bundle(pages=[pg]))
    assert f and "authentication" in f["title"].lower() and f.get("status") == "not_applicable", f


def t_diag_429():
    pg = _page(status=429, headers={"retry-after": "120"})
    f = run_audit.diagnose_blocker(_bundle(pages=[pg]))
    assert f and "429" in f["title"], f


def t_diag_5xx():
    pg = _page(status=503)
    f = run_audit.diagnose_blocker(_bundle(pages=[pg]))
    assert f and "server error" in f["title"].lower(), f


def t_diag_refused():
    b = _bundle(entry_reachable=False, pages=[],
                entry_error="ConnectionRefusedError: [Errno 111] Connection refused")
    f = run_audit.diagnose_blocker(b)
    assert f and "refused" in f["title"].lower(), f


# ===================================================================
# CLASSIFICATION BATTERY (item 1) -- the short-circuit must catch real
# blocks AND must NOT misclassify thin-but-legitimate content.
# ===================================================================
def _blocked_page(status, *, server=None, cfray=False, body="", wc=15, spa=False):
    h = {}
    if server:
        h["server"] = server
    if cfray:
        h["cf-ray"] = "8ab12"
    return _page(status=status, headers=h, text_sample=body, word_count=wc,
                 citability={"word_count": wc}, spa_root=spa, title="")


def _diag(pg):
    return run_audit.diagnose_auth_wall(_bundle(pages=[pg])) or \
        run_audit.diagnose_blocker(_bundle(pages=[pg]))


# --- blocks that MUST be caught ------------------------------------
def t_cls_plain_403_no_cdn():
    f = _diag(_blocked_page(403, server="nginx", body="Forbidden"))
    assert f and "403" in f["title"] and "Cloudflare" not in f["title"], f


def t_cls_403_akamai():
    f = _diag(_blocked_page(403, server="AkamaiGHost", body="Access Denied. Reference #18.abc"))
    assert f and "403" in f["title"] and "Akamai" in f["title"], f


def t_cls_403_cloudfront():
    f = _diag(_blocked_page(403, server="CloudFront",
                            body="The request could not be satisfied. Request blocked."))
    assert f and "403" in f["title"] and "CloudFront" in f["title"], f


def t_cls_403_generic_waf_still_classified():
    # unknown WAF: no CDN name, but still a 403-block finding (no crash)
    f = _diag(_blocked_page(403, server="Imperva", body="Request unsuccessful. Incapsula"))
    assert f and "403" in f["title"], f


def t_cls_429_rate_limit():
    f = _diag(_blocked_page(429, body="Too Many Requests"))
    assert f and "429" in f["title"], f


def t_cls_cloudflare_challenge_403():
    f = _diag(_blocked_page(403, cfray=True, body="Just a moment...\n__cf_chl_opt", wc=8))
    assert f and "challenge" in f["title"].lower() and "Cloudflare" in f["title"], f


def t_cls_cloudflare_challenge_503():
    f = _diag(_blocked_page(503, cfray=True, body="Checking your browser before accessing", wc=6))
    assert f and "challenge" in f["title"].lower(), f


def t_cls_cloudflare_challenge_200():
    # served with 200 -> would previously sail through as a normal page
    f = _diag(_blocked_page(200, cfray=True, body="Just a moment...\ncf_chl_opt", wc=7))
    assert f and "challenge" in f["title"].lower(), f


def t_cls_akamai_challenge_403_is_a_block():
    f = _diag(_blocked_page(403, server="AkamaiGHost",
                            body="Access Denied\nYou don't have permission", wc=12))
    assert f and ("403" in f["title"] or "challenge" in f["title"].lower()), f
    assert "Akamai" in f["title"], f


def t_cls_cloudfront_block_403():
    f = _diag(_blocked_page(403, server="CloudFront", body="Request blocked", wc=10))
    assert f and "CloudFront" in f["title"], f


# --- legitimate content that MUST NOT be misclassified -----------
def t_cls_genuine_thin_200_not_blocked():
    # a real, sparse page: 200, ~45 words, a couple links, NO spa root,
    # NO password, NO login/challenge text
    pg = _page(status=200, word_count=45, citability={"word_count": 45},
               text_sample="Contact us at the address below. We are open weekdays.",
               links_internal=[["https://x.test/a", "A"], ["https://x.test/b", "B"]])
    assert _diag(pg) is None


def t_cls_thin_200_with_nav_not_blocked():
    pg = _page(status=200, word_count=70, citability={"word_count": 70},
               text_sample="Short landing page for our small studio. Portfolio below.",
               links_internal=[[f"https://x.test/{k}", k]
                               for k in ("work", "about", "contact", "shop", "blog", "hire")])
    assert _diag(pg) is None


def t_cls_200_app_shell_is_flagged():
    pg = _blocked_page(200, body="loading", wc=6, spa=True)
    pg["links_internal"] = []
    f = _diag(pg)
    assert f and f.get("status") == "not_applicable" and "application shell" in f["evidence"], f


def t_cls_200_login_page_is_flagged():
    pg = _page(status=200, word_count=14, citability={"word_count": 14},
               text_sample="Sign in to continue. Forgot password?",
               links_internal=[["https://x.test/help", "Help"]],
               forms={**_page()["forms"], "has_password": True})
    f = _diag(pg)
    assert f and f.get("status") == "not_applicable" and "authentication" in f["title"].lower(), f


def t_cls_real_content_200_never_touched():
    # the normal case: a rich page -> no short-circuit at all
    pg = _page(status=200, word_count=600, citability={"word_count": 600},
               text_sample="We are a research organisation. " * 40,
               links_internal=[[f"https://x.test/{i}", str(i)] for i in range(20)])
    assert _diag(pg) is None


def t_auth_wall_gmail_like():
    pg = _page(status=200, word_count=8, citability={"word_count": 8},
               links_internal=[["https://x.test/help", "Help"]],
               text_sample="Sign in - use your Google Account. Forgot password?",
               forms={**_page()["forms"], "has_password": True},
               facts={**_page()["facts"], "login_wall": False})
    f = run_audit.diagnose_auth_wall(_bundle(pages=[pg]))
    assert f and "authentication" in f["title"].lower() and f.get("status") == "not_applicable", f


def t_auth_wall_normal_site_not_flagged():
    # normal site: header login form but lots of real content + links
    pg = _page(word_count=400, citability={"word_count": 400},
               forms={**_page()["forms"], "has_password": True},
               text_sample="Welcome to our company. " * 40)
    assert run_audit.diagnose_auth_wall(_bundle(pages=[pg])) is None


def t_app_shell_detected():
    pg = _page(status=200, word_count=27, citability={"word_count": 27},
               links_internal=[], spa_root=True, title="")
    f = run_audit.diagnose_auth_wall(_bundle(pages=[pg]))
    assert f and f.get("status") == "not_applicable" and "application shell" in f["evidence"], f


def t_normal_spa_marketing_page_not_flagged():
    # a marketing SPA that server-renders a hero: real words + links present
    pg = _page(status=200, word_count=180, citability={"word_count": 180}, spa_root=True,
               links_internal=[["https://x.test/a", "A"], ["https://x.test/b", "B"],
                               ["https://x.test/c", "C"], ["https://x.test/d", "D"]])
    assert run_audit.diagnose_auth_wall(_bundle(pages=[pg])) is None


def t_mixed_content_site_with_password_field_not_short_circuited():
    # item 8: real content homepage that also has a header login form (password
    # field present) must NOT be treated as "not a public content site".
    pg = _page(status=200, word_count=320, citability={"word_count": 320}, spa_root=True,
               text_sample="We build widgets for teams. " * 30 + " Log in",
               forms={**_page()["forms"], "has_password": True},
               links_internal=[[f"https://x.test/{k}", k] for k in
                               ("about", "pricing", "docs", "blog", "contact", "careers")])
    assert run_audit.diagnose_auth_wall(_bundle(pages=[pg])) is None
    assert run_audit.diagnose_blocker(_bundle(pages=[pg])) is None


def t_engage_na_finding_carries_status():
    fs = engage.analyze(_bundle())  # non-commercial
    na = [f for f in fs if f["title"].startswith("Visitor-goal checks not applicable")]
    assert na and na[0].get("status") == "not_applicable", na


def t_is_commercial_via_pricing_url_in_graph():
    b = _bundle(link_graph={"https://x.test/": ["https://x.test/pricing"]})
    assert engage.is_commercial(b) is True


def t_claims_bare_since_not_founding():
    # "since 2001" with no strong trigger -> not surfaced as a founding claim
    pg = _page(text_sample="Downloads available since 2001. Trusted worldwide.",
               facts={**_page()["facts"], "founded_years": ["2001"]})
    claims = fresh.collect_claims(_bundle(pages=[pg]))
    assert not any(c["kind"] == "founding" for c in claims), claims


def t_claims_strong_founded_is_surfaced():
    pg = _page(text_sample="The Acme Foundation was founded in 1998 to advance research.",
               facts={**_page()["facts"], "founded_years": ["1998"]})
    fs = fresh.analyze(_bundle(pages=[pg, _page(url="https://x.test/a")]), TODAY)
    pc = [f for f in fs if f["title"].startswith("Priority claims")]
    assert pc and "1998" in pc[0]["evidence"], [f["title"] for f in fs]


def t_engage_one_stray_price_is_not_commercial():
    pgs = [_page(url="https://x.test/", facts={**_page()["facts"]}),
           _page(url="https://x.test/story", facts={**_page()["facts"], "prices": ["$2m"]})]
    b = _bundle(pages=pgs, link_graph={"https://x.test/": []})
    fs = engage.analyze(b)
    missing = [f for f in fs if f["title"] == "Common visitor goals have no reachable page"]
    assert not missing or "pricing" not in missing[0]["evidence"], missing[0]["evidence"]


# --- freshness: per-domain claim selection + ladder ---------------------
def t_infer_type_publisher():
    pgs = [_page(url=f"https://x.test/blog/post-{i}", jsonld_types=[]) for i in range(3)]
    assert fresh.infer_type(_bundle(pages=pgs)) == "publisher"


def t_infer_type_ecommerce():
    pg = _page(jsonld_types=["Product", "Offer"], text_sample="free shipping on all returns")
    assert fresh.infer_type(_bundle(pages=[pg])) == "ecommerce"


def t_infer_type_generic_default():
    assert fresh.infer_type(_bundle()) == "generic_org"


def t_claims_jsonld_ranked_first():
    pg = _page(jsonld=[{"@type": "Organization", "name": "Acme",
                        "foundingDate": "1999-01-01", "telephone": "+1-555-0100"}])
    claims = fresh.collect_claims(_bundle(pages=[pg]))
    assert claims and claims[0]["score"] >= 100, claims
    kinds = {c["kind"] for c in claims}
    assert "founding" in kinds and "identity" in kinds, kinds


def t_claims_no_crash_on_garbage_jsonld():
    pg = _page(jsonld=["not a dict", 5, {"@type": None}, {"@graph": "bad"}])
    fresh.collect_claims(_bundle(pages=[pg]))  # must not raise


def t_claims_finding_emitted():
    pg = _page(jsonld=[{"@type": "Organization", "name": "Acme", "foundingDate": "1999"}])
    titles = [f["title"] for f in fresh.analyze(_bundle(pages=[pg]), TODAY)]
    assert "Priority claims to verify against independent sources" in titles, titles


def t_claims_absent_when_nothing_concrete():
    titles = [f["title"] for f in fresh.analyze(_bundle(), TODAY)]
    assert "Priority claims to verify against independent sources" not in titles, titles


def t_claims_weak_signals_suppressed():
    # generic site with only stray prices + a nav blob -> no priority-claims finding
    pgs = [_page(url="https://x.test/",
                 text_sample="Home All Products Books Travel 1000 results found"),
           _page(url="https://x.test/a", facts={**_page()["facts"], "prices": ["$1"]})]
    titles = [f["title"] for f in fresh.analyze(_bundle(pages=pgs), TODAY)]
    assert "Priority claims to verify against independent sources" not in titles, titles


def t_claims_commercial_price_is_kept():
    pgs = [_page(url=f"https://x.test/p{i}", jsonld_types=["Product", "Offer"],
                 text_sample="free shipping returns within 30 days",
                 facts={**_page()["facts"], "prices": ["$9"]}) for i in range(3)]
    fs = fresh.analyze(_bundle(pages=pgs), TODAY)
    pc = [f for f in fs if f["title"].startswith("Priority claims")]
    assert pc and "price" in pc[0]["evidence"], [f["title"] for f in fs]


# --- crawl: link-rot escalation --------------------------------------
def _crawl_bundle(pages_ok, failures):
    b = _bundle(pages=[_page(url=f"https://x.test/p{i}") for i in range(pages_ok)])
    b["stats"] = {"pages_fetched": pages_ok,
                  "failures": [{"url": f"https://x.test/dead{i}", "status": 404}
                               for i in range(failures)]}
    return b


def t_linkrot_critical_when_widespread():
    titles = [(f["title"], f["severity"]) for f in crawl.analyze(_crawl_bundle(6, 4))]
    assert any("Widespread broken links" in t and s == "critical" for t, s in titles), titles


def t_linkrot_medium_when_few():
    titles = [(f["title"], f["severity"]) for f in crawl.analyze(_crawl_bundle(20, 1))]
    assert any("Broken internal links" in t and s == "medium" for t, s in titles), titles


# --- Per-site-type engagement checks ---------------------------------------
# Each positive case is paired with a negative one: the point of gating these
# on site type is that the wrong kind of site never sees them at all.

def _shop_pages(cta=None, text="Great products for sale."):
    return [_page(url=f"https://x.test/product/{i}",
                  text_sample=text,
                  jsonld_types=["Product", "Offer"],
                  facts={**_page()["facts"], "prices": ["$19.99"],
                         "cta_matches": list(cta or [])})
            for i in range(3)]


def t_type_shop_priced_but_unbuyable_is_flagged():
    b = _bundle(pages=_shop_pages(), link_graph={"https://x.test/": ["https://x.test/shop"]})
    titles = [f["title"] for f in engage.type_specific(b, commercial=True)]
    assert any("no visible way to buy" in t for t in titles), titles


def t_type_shop_with_cart_cta_not_flagged():
    b = _bundle(pages=_shop_pages(cta=["add to cart"],
                                  text="Buy now. Free shipping and 30-day returns."))
    titles = [f["title"] for f in engage.type_specific(b, commercial=True)]
    assert not any("no visible way to buy" in t for t in titles), titles
    assert not any("shipping or returns" in t for t in titles), titles


def t_type_shop_checks_do_not_run_on_non_commercial_site():
    # A docs site with no commercial signal must never see shop checks.
    pages = [_page(url=f"https://x.test/docs/{i}", text_sample="API reference for the parser.")
             for i in range(4)]
    out = engage.type_specific(_bundle(pages=pages), commercial=False)
    assert not any("buy" in f["title"].lower() or "shipping" in f["title"].lower()
                   for f in out), [f["title"] for f in out]


def t_type_publisher_undated_articles_flagged():
    pages = [_page(url=f"https://x.test/blog/post-{i}", jsonld_types=["BlogPosting"],
                   jsonld_dates={}, text_sample="Some editorial content here.")
             for i in range(4)]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=False)]
    assert any("without a visible date" in t for t in titles), titles


def t_type_publisher_dated_articles_not_flagged():
    pages = [_page(url=f"https://x.test/blog/post-{i}", jsonld_types=["BlogPosting"],
                   jsonld_dates={"datePublished": "2026-08-01"},
                   text_sample="Some editorial content by Jane Smith.")
             for i in range(4)]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=False)]
    assert not any("without a visible date" in t for t in titles), titles


def t_type_local_business_without_hours_flagged():
    pages = [_page(jsonld_types=["LocalBusiness"], text_sample="We fix bikes in town.")]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=False)]
    assert any("opening hours" in t for t in titles), titles


def t_type_local_business_with_hours_not_flagged():
    pages = [_page(jsonld_types=["LocalBusiness"],
                   text_sample="Open Mon-Fri 9:00am to 5pm. We fix bikes.")]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=False)]
    assert not any("opening hours" in t for t in titles), titles


# --- Entity-type inference: open-source projects ---------------------------
# An open-source project is a large category that fits none of the commercial
# types. Without it, a language or library falls through to
# professional_services and gets asked what results it achieved "for clients".

answer = _load(SKILLS / "answerability-probe" / "scripts" / "analyze_answerability.py")


def _typed_bundle(paths, text=""):
    return _bundle(pages=[_page(url=f"https://x.test{p}", text_sample=text) for p in paths])


def t_oss_project_detected_from_own_paths():
    b = _typed_bundle(["/", "/community", "/tools/install", "/learn"])
    t, why = answer.infer_entity_type(b)
    assert t == "open_source_project", (t, why)


def t_oss_project_detected_from_one_path_plus_licence():
    b = _typed_bundle(["/", "/docs/intro"], text="Released under the MIT License. Free software.")
    t, why = answer.infer_entity_type(b)
    assert t == "open_source_project", (t, why)


def t_aggregator_linking_to_github_is_not_an_oss_project():
    # The Hacker News case: a tech aggregator's body text is full of
    # open-source vocabulary and repository links, but it publishes no
    # project-shaped paths of its own.
    b = _typed_bundle(
        ["/", "/ask", "/from", "/newsfaq.html"],
        text="Show HN: my open-source parser on github.com/foo/bar, licensed under MIT. "
             "Pull request welcome. Source code and contributors listed.")
    t, why = answer.infer_entity_type(b)
    assert t != "open_source_project", (t, why)


def t_oss_slots_do_not_ask_about_clients():
    b = _typed_bundle(["/", "/community", "/download"])
    t, _why = answer.infer_entity_type(b)
    slots = answer.UNIVERSAL_SLOTS + answer.TYPE_SLOTS[t]
    assert "case_evidence" not in slots, slots
    assert {"install", "documentation", "license", "community"} <= set(slots), slots


# --- Timeouts are not defects ----------------------------------------------
# Both guards below came from a live run against a slow host, where five healthy
# pages timed out and were reported as "link rot", and two AI user-agents timed
# out and were reported as a confirmed network-layer block. A timeout means the
# audit could not tell -- which is a different claim from "this is broken".

def t_timeouts_are_not_reported_as_link_rot():
    b = _bundle(pages=[_page(url=f"https://x.test/p{i}") for i in range(3)])
    b["stats"] = {"pages_fetched": 3,
                  "failures": [{"url": f"https://x.test/slow{i}", "status": None,
                                "error": "URLError: <urlopen error timed out>"}
                               for i in range(5)]}
    fs = crawl.analyze(b)
    titles = [f["title"] for f in fs]
    assert not any("link rot" in t.lower() or "Broken internal links" in t
                   for t in titles), titles
    slow = [f for f in fs if "did not respond in time" in f["title"]]
    assert slow and slow[0].get("status") == "not_observable", fs


def t_real_http_errors_still_reported_as_link_rot():
    b = _bundle(pages=[_page(url=f"https://x.test/p{i}") for i in range(3)])
    b["stats"] = {"pages_fetched": 3,
                  "failures": [{"url": f"https://x.test/dead{i}", "status": 404}
                               for i in range(5)]}
    titles = [(f["title"], f["severity"]) for f in crawl.analyze(b)]
    assert any("Widespread broken links" in t and s == "critical" for t, s in titles), titles


def t_mixed_timeouts_and_404s_counted_separately():
    b = _bundle(pages=[_page(url=f"https://x.test/p{i}") for i in range(10)])
    b["stats"] = {"pages_fetched": 10,
                  "failures": [{"url": "https://x.test/dead", "status": 404},
                               {"url": "https://x.test/slow", "status": None,
                                "error": "timed out"}]}
    fs = crawl.analyze(b)
    broken = [f for f in fs if "Broken internal links" in f["title"]]
    assert broken and "dead" in broken[0]["evidence"], fs
    assert "slow" not in broken[0]["evidence"], broken[0]["evidence"]


def t_ua_probe_explicit_403_is_confirmed_block():
    b = _bundle(ua_probe={"network_layer_block_suspected": True,
                          "blocked_agents": [{"agent": "GPTBot", "status": 403,
                                              "error": "HTTP 403"}]})
    fs = [(f["title"], f["severity"]) for f in crawl.analyze(b)]
    assert any("blocked at the network layer" in t and s == "critical" for t, s in fs), fs


def t_ua_probe_429_is_not_a_confirmed_block():
    # 429 is a throttle -- and our own probe may have provoked it.
    b = _bundle(ua_probe={"network_layer_block_suspected": True,
                          "blocked_agents": [{"agent": "GPTBot", "status": 429,
                                              "error": "HTTP 429"}]})
    fs = crawl.analyze(b)
    titles = [(f["title"], f["severity"]) for f in fs]
    assert not any("blocked at the network layer" in t for t, _s in titles), titles
    hedged = [f for f in fs if "could not be confirmed" in f["title"]]
    assert hedged, titles
    assert "rate limiting" in hedged[0]["evidence"], hedged[0]["evidence"]


def t_ua_probe_timeout_is_hedged_not_asserted():
    b = _bundle(ua_probe={"network_layer_block_suspected": True,
                          "blocked_agents": [{"agent": "GPTBot", "status": None,
                                              "error": "TimeoutError"}]})
    fs = crawl.analyze(b)
    titles = [(f["title"], f["severity"]) for f in fs]
    assert not any("blocked at the network layer" in t for t, _s in titles), titles
    hedged = [f for f in fs if "could not be confirmed" in f["title"]]
    assert hedged and hedged[0]["severity"] == "medium", titles


# --- Redirect hygiene -------------------------------------------------------

def _chain_bundle(chain):
    return _bundle(pages=[_page(redirect_chain=chain)])


def t_redirect_loop_flagged():
    chain = [{"from": "https://x.test/a", "status": 302, "to": "https://x.test/b"},
             {"from": "https://x.test/b", "status": 302, "to": "https://x.test/a"}]
    titles = [f["title"] for f in crawl.analyze(_chain_bundle(chain))]
    assert any("Redirect loop" in t for t in titles), titles


def t_long_redirect_chain_flagged():
    chain = [{"from": f"https://x.test/{i}", "status": 301, "to": f"https://x.test/{i+1}"}
             for i in range(4)]
    titles = [f["title"] for f in crawl.analyze(_chain_bundle(chain))]
    assert any("long redirect chains" in t for t in titles), titles


def t_single_redirect_not_flagged():
    chain = [{"from": "http://x.test/", "status": 301, "to": "https://x.test/"}]
    titles = [f["title"] for f in crawl.analyze(_chain_bundle(chain))]
    assert not any("redirect" in t.lower() for t in titles), titles


def t_http_hop_in_chain_flagged():
    chain = [{"from": "https://x.test/a", "status": 301, "to": "http://x.test/b"},
             {"from": "http://x.test/b", "status": 301, "to": "https://x.test/c"}]
    titles = [f["title"] for f in crawl.analyze(_chain_bundle(chain))]
    assert any("plain HTTP" in t for t in titles), titles


# --- Report-layer derivations ----------------------------------------------

def t_finding_code_is_stable_and_known():
    assert finalize.finding_code({"title": "Pages carry visibly stale dates"}) == "STALE_DATES"
    assert finalize.finding_code({"title": "Site is not served over HTTPS"}) == "NO_HTTPS"
    # Unknown titles still get a deterministic, non-empty code.
    c1 = finalize.finding_code({"title": "Some brand new check fires"})
    c2 = finalize.finding_code({"title": "Some brand new check fires"})
    assert c1 == c2 and c1 and c1 == c1.upper(), c1


def t_confidence_reflects_evidence_quality():
    strong = finalize.confidence_of({"evidence_tier": "measured", "evidence": "8/10 pages"})
    weak = finalize.confidence_of({"evidence_tier": "speculative", "evidence": "1/12 pages"})
    assert strong > weak, (strong, weak)
    # A single page out of many lowers confidence in an otherwise-measured claim.
    one = finalize.confidence_of({"evidence_tier": "measured", "evidence": "1/12 pages fail"})
    many = finalize.confidence_of({"evidence_tier": "measured", "evidence": "9/12 pages fail"})
    assert one < many, (one, many)
    assert 0.3 <= weak <= 0.98


def t_affected_urls_lifted_from_evidence():
    urls = finalize.affected_urls({"evidence": "Broken: https://x.test/a and https://x.test/b.",
                                   "page": "https://x.test/home"})
    assert urls[0] == "https://x.test/home"
    assert "https://x.test/a" in urls and "https://x.test/b" in urls
    assert not any(u.endswith(".") for u in urls), urls


def t_roadmap_puts_cheap_fixes_in_now_bucket():
    fs = [{"id": "F-001", "code": "NOINDEX", "title": "noindex", "severity": "medium",
           "effort": "quick", "suggested_action": {"summary": "remove it"}},
          {"id": "F-002", "code": "NO_SITE_SEARCH", "title": "search", "severity": "medium",
           "effort": "project", "suggested_action": {"summary": "build search"}}]
    rm = finalize.build_roadmap(fs)
    assert [r["id"] for r in rm["now"]] == ["F-001"], rm
    assert [r["id"] for r in rm["later"]] == ["F-002"], rm


def t_roadmap_high_severity_always_now():
    fs = [{"id": "F-001", "code": "X", "title": "x", "severity": "critical",
           "effort": "project", "suggested_action": {"summary": "big job"}}]
    assert [r["id"] for r in finalize.build_roadmap(fs)["now"]] == ["F-001"]


# --- Cross-component contract tests ---------------------------------------
# These exist because a real bug shipped through the gap they cover:
# run_audit.py marked blocker findings with a boolean `not_applicable`, while
# finalize_report.py filters on a `status` string. Nothing tested that boundary,
# so five "not a defect" findings were silently counted as defects and scored
# against the pillars. Every test below crosses a module boundary on purpose.

def _statuses_run_audit_can_emit():
    """Every status value diagnose_* actually produces, by exercising them."""
    out = set()
    cases = [
        _bundle(entry_reachable=False, entry_error="TimeoutError: timed out"),
        _bundle(entry_reachable=False, entry_error="OSError: something unrecognised"),
        _bundle(pages=[_page(status=401)]),
        _bundle(pages=[_page(status=451)]),
    ]
    for b in cases:
        f = run_audit.diagnose_blocker(b)
        if f and f.get("status"):
            out.add(f["status"])
    shell = _page(status=200, word_count=6, citability={"word_count": 6},
                  spa_root=True, links_internal=[], text_sample="Loading")
    f = run_audit.diagnose_auth_wall(_bundle(pages=[shell]))
    if f and f.get("status"):
        out.add(f["status"])
    return out


def t_contract_every_emitted_status_is_recognised_by_finalize():
    emitted = _statuses_run_audit_can_emit()
    assert emitted, "diagnose_* produced no statuses at all - test is not exercising them"
    unknown = emitted - set(finalize.NON_DEFECT_STATUS)
    assert not unknown, (
        f"run_audit emits status {sorted(unknown)} which finalize_report does not recognise; "
        f"it recognises {sorted(finalize.NON_DEFECT_STATUS)}. Such findings would be counted "
        "as real defects.")


def t_contract_blocker_finding_lands_in_not_assessed():
    """End-to-end: a not_applicable blocker must leave findings[] empty, appear in
    not_assessed[], and not dent the pillar scores."""
    import json as _json
    import subprocess
    import tempfile
    shell = _page(status=200, word_count=6, citability={"word_count": 6},
                  spa_root=True, links_internal=[], text_sample="Loading")
    blocker = run_audit.diagnose_auth_wall(_bundle(pages=[shell]))
    assert blocker is not None
    with tempfile.TemporaryDirectory() as td:
        src = pathlib.Path(td) / "f.json"
        out = pathlib.Path(td) / "r.json"
        src.write_text(_json.dumps({"site": "x.test", "findings": [blocker]}), encoding="utf-8")
        script = SKILLS / "audit-orchestrator" / "scripts" / "finalize_report.py"
        r = subprocess.run([sys.executable, str(script), str(src), "--site", "x.test",
                            "--out", str(out)], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        rep = _json.loads(out.read_text(encoding="utf-8"))
    assert rep["summary"]["total_findings"] == 0, rep["summary"]
    assert rep.get("not_assessed") and rep["not_assessed"][0]["id"] == "N-001", rep.get("not_assessed")
    # A site we never read must NOT score as a healthy one.
    assert rep["readiness"]["overall"] is None, rep["readiness"]
    assert "Not scored" in rep["readiness"]["scale_note"], rep["readiness"]


def t_contract_short_circuit_flag_survives_the_critic():
    """run_audit marks an unassessed run; the critic must carry that through or
    finalize_report will score a site whose content was never analysed."""
    import json as _json, subprocess, tempfile
    blocker = run_audit.diagnose_blocker(
        _bundle(entry_reachable=False, pages=[],
                entry_error="URLError: <urlopen error [Errno 11001] getaddrinfo failed>"))
    with tempfile.TemporaryDirectory() as td:
        raw = pathlib.Path(td) / "raw.json"
        adj = pathlib.Path(td) / "adj.json"
        rep = pathlib.Path(td) / "rep.json"
        raw.write_text(_json.dumps({"site": "x.test", "short_circuited": True,
                                    "pages_sampled": 0, "findings": [blocker]}), encoding="utf-8")
        c = SKILLS / "evidence-critic" / "scripts" / "critique_findings.py"
        r = subprocess.run([sys.executable, str(c), "--findings", str(raw), "--out", str(adj)],
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert _json.loads(adj.read_text(encoding="utf-8")).get("short_circuited") is True
        fin = SKILLS / "audit-orchestrator" / "scripts" / "finalize_report.py"
        r = subprocess.run([sys.executable, str(fin), str(adj), "--site", "x.test",
                            "--out", str(rep)], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        d = _json.loads(rep.read_text(encoding="utf-8"))
    # A domain that does not resolve is a real, counted finding -- but the site
    # must not be given a readiness score off five pillars nobody looked at.
    assert d["summary"]["critical"] == 1, d["summary"]
    assert d["readiness"]["overall"] is None, d["readiness"]


def t_contract_critic_preserves_status():
    """The critic deep-copies findings; status must survive it, or a
    not-applicable note silently becomes a counted defect again."""
    shell = _page(status=200, word_count=6, citability={"word_count": 6},
                  spa_root=True, links_internal=[], text_sample="Loading")
    blocker = run_audit.diagnose_auth_wall(_bundle(pages=[shell]))
    kept, _dropped, _notes = critic.adjudicate([blocker], _bundle(pages=[shell]))
    assert kept, "critic dropped the blocker finding entirely"
    assert kept[0].get("status") == "not_applicable", kept[0]


# ===================================================================
# NEW: consent/cookie-wall detection (narrow: server-side gate, not
# every page that merely mentions cookies in a footer notice)
# ===================================================================
def t_consent_wall_fact_strong_phrase():
    html = "<p>Please accept cookies to continue using this site.</p>"
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["consent_wall"] is True, facts


def t_consent_wall_fact_not_triggered_by_footer_notice():
    # An ordinary footer disclosure must NOT trip this -- the page still has
    # its content, this is not a gate.
    html = ("<p>We use cookies to improve your experience and analyse traffic. "
            "See our cookie policy for details.</p>" + "<p>Real article text. </p>" * 30)
    facts = collector.extract_facts(collector.parse_html(html).all_text, html,
                                    collector.parse_html(html))
    assert facts["consent_wall"] is False, facts


def t_consent_wall_short_circuits_when_thin():
    pg = _page(status=200, word_count=20, citability={"word_count": 20},
               links_internal=[], text_sample="Accept cookies to continue. We value your privacy.",
               facts={**_page()["facts"], "consent_wall": True})
    f = run_audit.diagnose_auth_wall(_bundle(pages=[pg]))
    assert f and f.get("status") == "not_applicable" and "consent" in f["title"].lower(), f


def t_consent_wall_not_flagged_when_content_present():
    # thin-page + consent flag alone is not enough if the page actually has
    # real content and normal navigation -- require the same multi-signal
    # discipline as the login wall.
    pg = _page(status=200, word_count=500, citability={"word_count": 500},
               text_sample="We use cookies. " + "Full article content here. " * 60,
               links_internal=[[f"https://x.test/{i}", str(i)] for i in range(10)],
               facts={**_page()["facts"], "consent_wall": True})
    assert run_audit.diagnose_auth_wall(_bundle(pages=[pg])) is None


# ===================================================================
# NEW: soft paywall via isAccessibleForFree in JSON-LD (structured,
# high-precision signal -- not a heuristic guess)
# ===================================================================
def t_paywall_jsonld_isaccessibleforfree_false_detected():
    html = ('<script type="application/ld+json">{"@type":"NewsArticle",'
            '"isAccessibleForFree":false,"headline":"X"}</script>' + "<p>Full text. </p>" * 50)
    parser = collector.parse_html(html)
    assert collector.jsonld_paywalled(parser) is True


def t_paywall_jsonld_true_not_flagged():
    html = ('<script type="application/ld+json">{"@type":"NewsArticle",'
            '"isAccessibleForFree":true}</script>' + "<p>Full text. </p>" * 50)
    parser = collector.parse_html(html)
    assert collector.jsonld_paywalled(parser) is False


def t_paywall_no_jsonld_signal_not_flagged():
    html = "<p>Subscribe to our newsletter for updates.</p>" + "<p>Full text. </p>" * 50
    parser = collector.parse_html(html)
    assert collector.jsonld_paywalled(parser) is False


def t_paywall_subscribe_cta_alone_is_not_a_paywall_finding():
    # A subscribe/newsletter CTA with no isAccessibleForFree signal must NOT
    # be reported as a paywall -- that would be lead-gen, not a content gate.
    pg = _page(facts={**_page()["facts"], "cta_matches": ["subscribe"]}, paywalled=False)
    findings = crawl.analyze(_bundle(pages=[pg]))
    assert not any("paywall" in f["title"].lower() for f in findings), \
        [f["title"] for f in findings]


def t_paywall_finding_emitted_when_structured_signal_present():
    pg1 = _page(url="https://x.test/a", paywalled=True)
    pg2 = _page(url="https://x.test/b", paywalled=False)
    findings = crawl.analyze(_bundle(pages=[pg1, pg2]))
    pw = [f for f in findings if "paywall" in f["title"].lower()]
    assert pw, [f["title"] for f in findings]
    assert "1" in pw[0]["evidence"] and "2" in pw[0]["evidence"], pw[0]["evidence"]


def t_paywall_finding_absent_when_no_pages_marked():
    pg = _page(paywalled=False)
    findings = crawl.analyze(_bundle(pages=[pg]))
    assert not any("paywall" in f["title"].lower() for f in findings)


# ===================================================================
# NEW: default output layout -- each run gets its own folder unless
# the caller passes explicit --out / --evidence-out paths (in which
# case behaviour is byte-for-byte unchanged from before).
# ===================================================================
def t_default_run_dir_is_domain_and_timestamp():
    d = run_audit._default_run_dir("https://www.Example.com:8443/path?q=1")
    parts = d.parts
    assert parts[0] == "audit_runs", d
    assert re.match(r"^www\.example\.com_8443-\d{8}-\d{6}$", parts[1]), d


def t_default_run_dir_sanitizes_unsafe_characters():
    d = run_audit._default_run_dir("https://ex ample.com/a:b*c")
    name = d.parts[1]
    assert not any(c in name for c in ' :*/\\"<>|?'), name


def t_default_run_dir_never_empty_on_garbage_input():
    d = run_audit._default_run_dir("not a url at all")
    assert d.parts[0] == "audit_runs" and d.parts[1], d


def t_critique_out_defaults_next_to_findings():
    import json as _json, subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        raw = pathlib.Path(td) / "raw.json"
        raw.write_text(_json.dumps({"site": "x.test", "findings": []}), encoding="utf-8")
        c = SKILLS / "evidence-critic" / "scripts" / "critique_findings.py"
        r = subprocess.run([sys.executable, str(c), "--findings", str(raw)],
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        expected = pathlib.Path(td) / "adjudicated_findings.json"
        assert expected.exists(), f"{expected} was not created; stdout={r.stdout}"


def t_critique_explicit_out_still_honoured():
    # Backward compatibility: an explicit --out must land exactly there, not
    # be redirected next to --findings.
    import json as _json, subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        sub = pathlib.Path(td) / "inputs"
        sub.mkdir()
        raw = sub / "raw.json"
        raw.write_text(_json.dumps({"site": "x.test", "findings": []}), encoding="utf-8")
        out = pathlib.Path(td) / "elsewhere.json"
        c = SKILLS / "evidence-critic" / "scripts" / "critique_findings.py"
        r = subprocess.run([sys.executable, str(c), "--findings", str(raw), "--out", str(out)],
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert out.exists()
        assert not (sub / "adjudicated_findings.json").exists()


def t_finalize_out_defaults_next_to_findings_file():
    import json as _json, subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        adj = pathlib.Path(td) / "adjudicated.json"
        adj.write_text(_json.dumps({"site": "x.test", "findings": []}), encoding="utf-8")
        fin = SKILLS / "audit-orchestrator" / "scripts" / "finalize_report.py"
        r = subprocess.run([sys.executable, str(fin), str(adj), "--site", "x.test"],
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        expected = pathlib.Path(td) / "audit_report.json"
        assert expected.exists(), f"{expected} was not created; stdout={r.stdout}"


def t_finalize_explicit_out_still_honoured():
    import json as _json, subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        sub = pathlib.Path(td) / "inputs"
        sub.mkdir()
        adj = sub / "adjudicated.json"
        adj.write_text(_json.dumps({"site": "x.test", "findings": []}), encoding="utf-8")
        out = pathlib.Path(td) / "elsewhere.json"
        fin = SKILLS / "audit-orchestrator" / "scripts" / "finalize_report.py"
        r = subprocess.run([sys.executable, str(fin), str(adj), "--site", "x.test",
                            "--out", str(out)], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert out.exists()
        assert not (sub / "audit_report.json").exists()


# ===================================================================
# NEW: the github.com case -- stray currency figures on policy/DEI
# pages must not be counted as "priced pages", and a SaaS pricing page
# with a "get started" CTA is buyable even though it's not a literal
# "buy now" / "add to cart".
# ===================================================================
def t_shop_check_ignores_stray_prices_on_policy_pages():
    pages = [
        _page(url="https://x.test/pricing", jsonld_types=[],
              facts={**_page()["facts"], "prices": ["$21"],
                     "cta_matches": ["get started", "sign up"]}),
        _page(url="https://x.test/about/diversity", jsonld_types=[],
              facts={**_page()["facts"], "prices": ["$15,000"], "cta_matches": []}),
        _page(url="https://x.test/about/report", jsonld_types=[],
              facts={**_page()["facts"], "prices": ["$1,500", "$20,000"], "cta_matches": []}),
        _page(url="https://x.test/security/advanced", jsonld_types=[],
              facts={**_page()["facts"], "prices": [], "cta_matches": ["sign up"]}),
    ]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=True)]
    assert not any("no visible way to buy" in t for t in titles), titles
    assert not any("shipping or returns" in t for t in titles), titles


def t_shop_check_saas_pricing_page_counts_get_started_as_buyable():
    pages = [_page(url=f"https://x.test/pricing", jsonld_types=[],
                   facts={**_page()["facts"], "prices": ["$0", "$21", "$4"],
                          "cta_matches": ["get started", "start free", "sign up"]})]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=True)]
    assert not any("no visible way to buy" in t for t in titles), titles


def t_shop_check_real_goods_shop_still_flagged_for_missing_shipping():
    pages = [_page(url=f"https://x.test/product/{i}", jsonld_types=["Product", "Offer"],
                   text_sample="Buy this today.",
                   facts={**_page()["facts"], "prices": ["$19.99"], "cta_matches": []})
             for i in range(3)]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=True)]
    assert any("no visible way to buy" in t for t in titles), titles
    assert any("shipping or returns" in t for t in titles), titles


def t_shop_check_catalogue_with_no_markup_still_counted():
    # A real catalogue site with no schema and no CTA at all (this is the
    # shape of a scraping-practice fixture, and of many real small shops)
    # must still be counted as priced -- only specific non-commercial
    # sections are excluded, not "anything lacking markup".
    pages = [_page(url=f"https://x.test/catalogue/book-{i}", jsonld_types=[],
                   text_sample="A great book.",
                   facts={**_page()["facts"], "prices": ["$51.77"], "cta_matches": []})
             for i in range(5)]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=True)]
    assert any("no visible way to buy" in t for t in titles), titles
    assert any("shipping or returns" in t for t in titles), titles


def t_shop_check_saas_pricing_alone_not_flagged_for_shipping():
    # Shipping/returns is a goods concept -- a bare SaaS /pricing page with no
    # cart/product path must not be told to publish shipping terms.
    pages = [_page(url="https://x.test/pricing", jsonld_types=[],
                   facts={**_page()["facts"], "prices": ["$21"],
                          "cta_matches": ["get started"]})]
    titles = [f["title"] for f in engage.type_specific(_bundle(pages=pages), commercial=True)]
    assert not any("shipping or returns" in t for t in titles), titles


for _n, _f in sorted((k, v) for k, v in globals().items() if k.startswith("t_")):
    check(_n, _f)

_fail = [(n, e) for n, e in _results if e]
for n, e in _results:
    print(f"  {'PASS' if not e else 'FAIL'}  {n}" + (f"\n        {e}" if e else ""))
print(f"\n{len(_results) - len(_fail)}/{len(_results)} passed")
sys.exit(1 if _fail else 0)
