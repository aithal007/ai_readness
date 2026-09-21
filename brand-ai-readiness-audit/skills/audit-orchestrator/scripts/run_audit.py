#!/usr/bin/env python3
"""Stage 1 of the audit: collect one evidence snapshot, then run every scripted
analyzer against it.

Collect-once/analyze-many is deliberate. If each skill fetched the site
separately they would each see a slightly different snapshot, findings could
contradict each other for no reason, and the crawl budget would be spent
several times over. One bundle means every skill reasons over identical
evidence, and the whole audit costs a single crawl.

Failure policy: a collector failure is fatal (nothing downstream can run); an
analyzer failure is recorded as a visible "meta" finding and the run continues
degraded. A degraded run must never look like a clean one.

Usage:
  python3 run_audit.py <url> [--out raw_findings.json] [--evidence-out evidence.json]
                            [--today YYYY-MM-DD] [--max-pages 15]
Prints the raw findings path to stdout; progress to stderr.
Exit: 0 ok, 1 collector failed, 2 bad arguments.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime

# (skill id, script, extra args) -- every analyzer reads the shared bundle.
ANALYZERS = [
    ("crawl-render-audit", "analyze_crawl_render.py", []),
    ("structured-data-entity-audit", "analyze_structured_entity.py", []),
    ("ai-citability-audit", "analyze_citability.py", []),
    ("answerability-probe", "analyze_answerability.py", []),
    ("freshness-corroboration-audit", "analyze_freshness.py", ["--today"]),
    ("engagement-audit", "analyze_engagement.py", []),
]


def _blocker_finding(title, evidence, mechanism, action, priority="critical",
                     status=None, evidence_tier="measured"):
    """Build the single finding emitted when the site cannot be audited normally.

    `status` must be one of the values finalize_report.py recognises --
    "not_applicable" (the audit does not apply to this kind of URL) or
    "not_observable" (we could not see enough to judge). Anything else stays a
    real, counted defect.

    The distinction is deliberate and not cosmetic:
      * A DNS failure, TLS error, refused connection, 5xx or CDN bot-block is a
        genuine defect -- the site really is broken or really is invisible.
      * A login wall or a private application shell is NOT a defect; the audit
        simply does not apply to it.
      * A bare timeout or an unrecognised transport error is neither -- we
        cannot tell, so it must not be scored either way.
    """
    f = {"title": title, "severity": priority, "category": "discoverability",
         "evidence": evidence, "mechanism": mechanism,
         "suggested_action": {"summary": action, "priority": priority},
         "signal_tier": 1, "evidence_tier": evidence_tier,
         "source_skill": "crawl-render-audit"}
    if status:
        f["status"] = status
    return f


def diagnose_auth_wall(bundle):
    """The gmail.com case: the entry returns 200 but there is no public content --
    it is a login screen or a private app shell. One honest finding, not a pile."""
    pages = bundle.get("pages") or []
    if not pages:
        return None
    home = pages[0]
    if not isinstance(home.get("status"), int) or home["status"] >= 400:
        return None
    facts = home.get("facts", {})
    forms = home.get("forms", {})
    wc = (home.get("citability", {}) or {}).get("word_count", home.get("word_count", 0))
    n_links = len(home.get("links_internal", []))
    sample = (home.get("text_sample") or "").lower()
    phrase = any(s in sample for s in (
        "sign in", "log in", "login", "sign-in", "forgot password", "keep me signed in",
        "stay signed in", "use your google account", "enter your password"))

    # Case A: a server-rendered login / paywall page.
    login_signals = sum([
        bool(facts.get("login_wall")),
        bool(forms.get("has_password")),
        (wc < 60 and n_links <= 5 and phrase),
    ])
    # Case B: a client-rendered application shell (gmail, web.whatsapp, figma...):
    # SPA marker + almost no static text + almost no crawlable links.
    app_shell = bool(home.get("spa_root")) and wc < 40 and n_links <= 3

    # Case C: a server-side consent GATE -- the page really has nothing behind
    # it until a cookie is accepted (rare; distinct from the ordinary footer
    # disclosure almost every site carries, which does not trip this flag at
    # all -- see CONSENT_WALL_RE). Same multi-signal discipline as case A: the
    # flag alone is not enough, the page must also be thin.
    consent_signals = sum([
        bool(facts.get("consent_wall")),
        (wc < 60 and n_links <= 5),
    ])

    if login_signals >= 2:
        kind = "a login wall"
    elif app_shell:
        kind = "a client-rendered application shell"
    elif consent_signals >= 2:
        kind = "a cookie-consent gate"
    else:
        return None

    if kind == "a cookie-consent gate":
        return _blocker_finding(
            "Entry point is gated behind a cookie-consent wall",
            f"The homepage of {bundle.get('site')} returned HTTP {home['status']} but exposes "
            f"only {wc} words of static text and {n_links} crawlable link(s), gated behind "
            "consent-required language rather than showing the page's real content.",
            "A server-side consent gate has nothing an AI assistant can reach, read or cite "
            "until a cookie is accepted -- which no compliant crawler will do. Running the "
            "content, engagement and corroboration checks here would only produce findings "
            "about the consent notice.",
            "Serve the underlying page content to first-time / anonymous visitors and crawlers; "
            "gate only what genuinely requires consent (e.g. personalised ads), not the page "
            "itself.",
            priority="medium", status="not_applicable", evidence_tier="correlational")

    return _blocker_finding(
        "Entry point is not a public content site (authentication / application shell)",
        f"The homepage of {bundle.get('site')} returned HTTP {home['status']} but exposes only "
        f"{wc} words of static text and {n_links} crawlable link(s)"
        + (", a password field" if forms.get("has_password") else "")
        + (", sign-in language" if phrase else "")
        + (", and a single-page-app root element" if home.get("spa_root") else "")
        + f". This is {kind}, not a public content site.",
        "A login wall or private application shell has nothing an AI assistant can reach, read or "
        "cite. Running the content, engagement and corroboration checks against it would only "
        "produce findings about the sign-in / loading screen.",
        "If public discoverability is intended, publish marketing / informational pages without "
        "authentication and server-render their content (the application itself can stay a "
        "client-rendered gated app). If this URL is meant to be private, no action is needed.",
        priority="medium", status="not_applicable", evidence_tier="correlational")


def diagnose_blocker(bundle):
    """Classify *why* the site could not be crawled, instead of one generic bucket.
    Returns a single finding dict, or None if the site is genuinely crawlable."""
    pages = bundle.get("pages") or []
    home = pages[0] if pages else {}
    err = (bundle.get("entry_error") or "").lower()
    site = bundle.get("site")

    if not bundle.get("entry_reachable"):
        ev = f"Entry fetch of {site} failed: {bundle.get('entry_error')}."
        if any(s in err for s in ("getaddrinfo", "name or service not known",
                                  "nodename nor servname", "name resolution")):
            return _blocker_finding(
                "Domain does not resolve (DNS failure)", ev,
                "The hostname has no usable DNS record, so no crawler -- AI or search -- can "
                "locate the origin at all.",
                "Check the domain is registered and not expired, and that its DNS A/AAAA or "
                "CNAME records point at the live host.")
        if any(s in err for s in ("ssl", "certificate", "cert_", "sslcert", "hostname mismatch")):
            return _blocker_finding(
                "TLS/certificate error prevents a secure connection", ev,
                "Clients abort the handshake before any content is sent when the certificate is "
                "expired, issued for a different hostname, or served without its intermediate "
                "chain.",
                "Reissue or reinstall the certificate for this exact hostname and include the "
                "full intermediate chain; verify with an SSL checker.")
        if any(s in err for s in ("refused", "no route", "unreachable", "connection reset")):
            return _blocker_finding(
                "The origin refused the connection", ev,
                "The server is down, not listening on 80/443, or a network firewall drops the "
                "connection before HTTP is spoken.",
                "Confirm the web server is running and listening on ports 80 and 443, and that no "
                "firewall or security group blocks inbound traffic.")
        if "tim" in err and "out" in err:  # timed out / timeout
            return _blocker_finding(
                "The origin did not respond before timeout -- cause undetermined", ev,
                "No response arrived in the request window. A slow origin, a firewall silently "
                "dropping the packet, and a WAF black-holing non-browser traffic all look "
                "identical from one failed request.",
                "Check origin health and response time, then check firewall / WAF logs for "
                "silently dropped requests from non-browser user-agents.",
                status="not_observable")
        return _blocker_finding(
            "Site did not respond to an unauthenticated request -- cause undetermined", ev,
            "A plain GET failed in a way that does not match a known signature. Possible causes: "
            "DNS, TLS, a firewall drop, or silent WAF filtering.",
            "Verify DNS resolves, the TLS certificate is valid, and the origin answers an "
            "anonymous external GET; then inspect WAF / CDN logs.",
            status="not_observable")

    status = home.get("status")
    hdrs = {k.lower(): (v or "") for k, v in (home.get("headers") or {}).items()}
    body = (home.get("text_sample") or "").lower()
    server = hdrs.get("server", "").lower()
    cdn = ("Cloudflare" if "cloudflare" in server or "cf-ray" in hdrs
           else "Akamai" if "akamai" in server
           else "AWS CloudFront" if "cloudfront" in server
           else None)
    wc = (home.get("citability", {}) or {}).get("word_count", home.get("word_count", 999))

    # A challenge/interstitial served with HTTP 200 (Cloudflare "under attack",
    # some WAFs) would otherwise sail through as a normal reachable page. The
    # markers below are verbatim challenge-page text that does not occur on real
    # content, and we still require the page to be thin.
    strong_challenge = any(s in body for s in (
        "just a moment...", "__cf_chl", "cf-chl-", "cf_chl_opt",
        "checking your browser before accessing", "verify you are human",
        "enable javascript and cookies to continue", "attention required! | cloudflare",
        "please wait while we verify"))
    if strong_challenge and wc < 120:
        return _blocker_finding(
            "A bot-detection challenge page is served instead of content"
            + (f" ({cdn})" if cdn else ""),
            f"The homepage of {site} returned HTTP {status} with a JavaScript / CAPTCHA "
            "interstitial in place of content.",
            "The origin or its CDN answers non-browser clients with a challenge. Every crawler "
            "that does not execute JavaScript -- most AI crawlers -- sees the challenge, never "
            "the content.",
            "In the CDN bot-management settings, allow the AI / search crawlers you want citing "
            "you, or exempt them from the challenge."
            + (f" This is {cdn}'s bot-management layer, not robots.txt." if cdn else ""))

    if not isinstance(status, int) or status < 400:
        return None  # genuinely reachable -- let the normal fan-out run

    ev = f"The homepage of {site} returned HTTP {status}" + (f" via {cdn}" if cdn else "") + "."
    challenge = any(s in body for s in ("just a moment", "checking your browser", "cf_chl",
                                        "__cf_chl", "enable javascript and cookies",
                                        "attention required", "verify you are human"))
    regional = any(s in body for s in ("not available in your", "unavailable in your country",
                                       "in your region", "geo"))

    if status == 401:
        return _blocker_finding(
            "The entire site is behind HTTP authentication", ev,
            "A 401 with no anonymous content means there is nothing public to crawl, read or "
            "cite.", "If public discoverability is intended, expose the content pages without "
            "authentication; the application can stay gated.",
            priority="high", status="not_applicable")
    if status == 429:
        return _blocker_finding(
            "The origin rate-limited the first request (HTTP 429)", ev,
            "The site returns 429 before any page can be read, so the crawl gets nothing -- and "
            "so would an assistant fetching the page for a user.",
            "Relax rate limiting for identified read-only crawlers, or publish a crawl-delay the "
            "audit can honour.", priority="high")
    if status == 451 or (status == 403 and regional):
        return _blocker_finding(
            "Content is blocked for this network / region", ev,
            "A 451 or regional 403 means the origin serves this network no content; coverage "
            "from other regions may differ.",
            "If global reach is intended, review the geo-blocking rule; otherwise the "
            "restriction is deliberate and no action is needed.",
            priority="high", status="not_observable")
    if challenge:
        return _blocker_finding(
            "A bot-detection challenge page is served instead of content"
            + (f" ({cdn})" if cdn else ""), ev,
            "The origin or its CDN answers non-browser clients with a JavaScript / CAPTCHA "
            "interstitial. Every crawler that does not execute JavaScript -- which is most AI "
            "crawlers -- sees the challenge, never the content.",
            "In the CDN bot-management settings, allow the AI / search crawlers you want citing "
            "you, or exempt them from the challenge."
            + (f" This is {cdn}'s bot-management layer, not robots.txt." if cdn else ""))
    if status == 403:
        return _blocker_finding(
            "The origin returns 403 to non-browser clients"
            + (f" ({cdn} bot-management)" if cdn else ""), ev,
            "A 403 to a plain crawler while browsers get through is the signature of CDN / WAF "
            "bot filtering, which sits above robots.txt and overrides it -- the site can be "
            "permissive in robots.txt and still be invisible to assistants.",
            "Review the CDN / WAF bot-management rules and allow the search / AI crawlers you "
            "want to be cited by." + (f" In {cdn} this is the bot-management rule set." if cdn
                                      else ""))
    if 500 <= status < 600:
        return _blocker_finding(
            f"The origin returned a server error (HTTP {status}) on the homepage", ev,
            "A 5xx on the entry page means the site is currently broken for everyone, crawlers "
            "and visitors alike.",
            "Check application and server logs for the error behind this status, and re-audit "
            "once it is resolved.")
    return _blocker_finding(
        f"The homepage returned HTTP {status}", ev,
        "A 4xx on the entry URL means there is no readable content at the address given.",
        "Confirm the correct public URL for the site and that it returns 200 to an anonymous "
        "GET.", priority="high")


def meta_finding(skill, err):
    return {
        "title": f"{skill} analyzer did not complete",
        "severity": "low", "category": "meta",
        "evidence": f"{err}"[:400],
        "mechanism": "This check could not run, so its area is UNVERIFIED rather than clean. "
                     "A degraded run that looks identical to a clean one is the most dangerous "
                     "outcome in a multi-step audit, so the gap is recorded explicitly.",
        "suggested_action": {
            "summary": f"Re-run {skill}'s analyzer against the evidence bundle to see the "
                       "underlying error before treating this area as passing.",
            "priority": "low"},
        "signal_tier": 1, "evidence_tier": "measured", "source_skill": skill,
    }


def _default_run_dir(url):
    """audit_runs/<domain>-<timestamp>/ -- so running against several sites (or
    the same site twice) never silently overwrites a previous run's files.

    Only used when --out / --evidence-out are omitted; passing either
    explicitly is unaffected and behaves exactly as before."""
    domain = re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].lower()
    domain = re.sub(r"[^a-z0-9.\-_]", "_", domain) or "site"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return pathlib.Path("audit_runs") / f"{domain}-{stamp}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("url")
    ap.add_argument("--out", default=None,
                    help="default: audit_runs/<domain>-<timestamp>/raw_findings.json")
    ap.add_argument("--evidence-out", default=None,
                    help="default: audit_runs/<domain>-<timestamp>/evidence.json")
    ap.add_argument("--today", default=None,
                    help="ISO date to treat as today; pass the agent's real current date")
    ap.add_argument("--max-pages", type=int, default=15)
    ap.add_argument("--budget-seconds", type=int, default=150)
    args = ap.parse_args()

    if args.out is None or args.evidence_out is None:
        run_dir = _default_run_dir(args.url)
        run_dir.mkdir(parents=True, exist_ok=True)
        if args.out is None:
            args.out = str(run_dir / "raw_findings.json")
        if args.evidence_out is None:
            args.evidence_out = str(run_dir / "evidence.json")
        print(f"[orchestrator] no --out/--evidence-out given; writing this run to "
              f"{run_dir}/", file=sys.stderr)

    root = pathlib.Path(__file__).resolve().parents[3]
    collector = root / "skills" / "crawl-render-audit" / "scripts" / "evidence_collector.py"
    if not collector.exists():
        print(f"error: collector not found at {collector}", file=sys.stderr)
        sys.exit(2)

    # --- Stage 1: collect once (idempotent: overwrites a deterministic path)
    print(f"[orchestrator] collecting evidence from {args.url} ...", file=sys.stderr)
    try:
        subprocess.run([sys.executable, str(collector), args.url,
                        "--out", args.evidence_out,
                        "--max-pages", str(args.max_pages),
                        "--budget-seconds", str(args.budget_seconds)],
                       check=True, capture_output=True, text=True,
                       timeout=args.budget_seconds + 120)
    except Exception as e:
        print(f"error: evidence collection failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    with open(args.evidence_out, encoding="utf-8") as fh:
        bundle = json.load(fh)
    stats = bundle.get("stats", {})
    print(f"[orchestrator] collected {stats.get('pages_fetched')} page(s) in "
          f"{stats.get('elapsed_seconds')}s", file=sys.stderr)

    # Stop before the fan-out when there is nothing to audit: an unreachable or
    # blocked origin (diagnosed by cause), or a login wall / private app shell.
    # Each of these emits ONE honest finding instead of a pile of derived noise.
    blocker = diagnose_auth_wall(bundle) or diagnose_blocker(bundle)
    if blocker:
        print(f"[orchestrator] not crawlable: {blocker['title']}", file=sys.stderr)
        # Flag the short circuit explicitly. The report must not score a site
        # whose content was never analysed -- five untouched pillars would
        # otherwise average away the one blocker into a healthy-looking number.
        payload = {"site": bundle.get("site", args.url), "evidence_file": args.evidence_out,
                   "pages_sampled": stats.get("pages_fetched", 0),
                   "short_circuited": True, "findings": [blocker]}
        pathlib.Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(args.out)
        return

    # --- Stage 2: fan out over the shared bundle ---------------------------
    all_findings = []
    # The analyzers are pure functions over the same immutable bundle: none of
    # them touches the network or writes shared state, so they can all run at
    # once. Wall-clock becomes the slowest analyzer rather than their sum, which
    # matters on large sites where the sequential fan-out approached the runtime
    # budget. Results are re-sorted into ANALYZERS order afterwards so the output
    # stays byte-identical to a sequential run -- concurrency must not make the
    # report non-deterministic.
    def _run_one(entry):
        skill, script, extra = entry
        path = root / "skills" / skill / "scripts" / script
        if not path.exists():
            return skill, None, f"analyzer script missing at {path}"
        cmd = [sys.executable, str(path), "--evidence", args.evidence_out]
        if "--today" in extra and args.today:
            cmd += ["--today", args.today]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if not proc.stdout.strip():
                raise RuntimeError(f"no output (exit {proc.returncode}): {proc.stderr[-300:]}")
            found = json.loads(proc.stdout).get("findings", [])
            for f in found:
                f.setdefault("source_skill", skill)
            return skill, found, None
        except Exception as e:  # noqa: BLE001 -- any analyzer failure degrades, never aborts
            return skill, None, f"{type(e).__name__}: {e}"

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ANALYZERS)) as pool:
        for skill, found, err in pool.map(_run_one, ANALYZERS):
            results[skill] = (found, err)

    for skill, _script, _extra in ANALYZERS:      # deterministic order
        found, err = results.get(skill, (None, "analyzer did not run"))
        if err is not None:
            print(f"[orchestrator] {skill} FAILED: {err}", file=sys.stderr)
            all_findings.append(meta_finding(skill, err))
        else:
            print(f"[orchestrator] {skill}: {len(found)} finding(s)", file=sys.stderr)
            all_findings.extend(found)

    # Inaccessible content is not missing content: pages that returned 200 but
    # are themselves a login / paywall gate were still analysed for "missing X"
    # by the scripts above. Flag that so the coverage is honest -- as a
    # not_observable note, not a defect.
    walled = [p.get("url") for p in bundle.get("pages", [])
              if p.get("facts", {}).get("login_wall")]
    if walled:
        all_findings.append({
            "title": "Some sampled pages are gated and their content was not assessed",
            "severity": "low", "status": "not_observable", "category": "meta",
            "evidence": f"{len(walled)} of {len(bundle.get('pages', []))} sampled page(s) "
                        f"returned 200 but present a sign-in / subscribe gate: "
                        + ", ".join(walled[:4]) + ". Any 'missing' signal on these pages reflects "
                        "what a logged-out visitor sees, which may not be the full page.",
            "mechanism": "A gate that returns 200 looks like a normal page to a scripted check, "
                         "so absence of content behind it would otherwise be reported as a "
                         "defect. It is a coverage limit, not a fault.",
            "suggested_action": {"summary": "If these pages hold public-facing content, expose a "
                                 "logged-out version so crawlers and assistants can read it.",
                                 "priority": "low"},
            "signal_tier": 1, "evidence_tier": "measured", "source_skill": "crawl-render-audit"})

    payload = {"site": bundle.get("site", args.url), "evidence_file": args.evidence_out,
               "collected_at": bundle.get("collected_at"),
               "pages_sampled": stats.get("pages_fetched"), "findings": all_findings}
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[orchestrator] {len(all_findings)} raw finding(s) -> {args.out}", file=sys.stderr)
    print(args.out)


if __name__ == "__main__":
    main()
