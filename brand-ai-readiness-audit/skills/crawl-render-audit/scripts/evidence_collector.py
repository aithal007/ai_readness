#!/usr/bin/env python3
"""Bounded, robots-respecting evidence collector for the brand-ai-readiness-audit
marketplace.

Collects ONE deterministic snapshot of a site that every analyzer skill then reads,
so all skills reason over identical evidence instead of each re-crawling and
seeing a slightly different site.

Design constraints (deliberate):
  * Python standard library ONLY -- no pip installs, runs on a bare python3.
  * Read-only GET requests. Never authenticates, never submits a form.
  * Honors robots.txt for every URL beyond the entry page.
  * Hard-bounded: max pages, max depth, per-request timeout, global deadline.
  * Never raises on bad input -- malformed HTML/network errors become recorded
    facts in the bundle, not crashes.

Usage:
  python3 evidence_collector.py <url> [--out evidence.json] [--max-pages 15]
                                      [--max-depth 2] [--budget-seconds 150]

Writes the evidence bundle as JSON and prints the output path.
"""
import argparse
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

COLLECTOR_VERSION = "2.0.0"

USER_AGENT = ("BrandAIReadinessAuditBot/2.0 "
              "(+read-only audit; bounded same-domain sample; honors robots.txt)")
TIMEOUT = 10
MAX_BYTES = 3_000_000
REQUEST_DELAY = 0.4

# ---------------------------------------------------------------------------
# AI crawler taxonomy.
#
# CATEGORISED BECAUSE BLOCKING IS NOT ALWAYS A DEFECT. This table is the single
# most important false-positive guard in the whole marketplace.
#
# `citation_impact` answers: if this agent is disallowed, does the brand
# actually stop appearing in that assistant's answers?
#   "removes"  -> yes; blocking genuinely costs citation visibility
#   "none"     -> no; this is a training/opt-out token. Per Google, blocking
#                 Google-Extended "does not impact a site's inclusion in Google
#                 Search nor is it used as a ranking signal". Per OpenAI,
#                 disallowing GPTBot only opts out of model training.
#                 Refusing training while allowing search is a legitimate,
#                 documented licensing choice -- NEVER report it as a defect.
#   "intent"   -> user-triggered fetchers. OpenAI states robots.txt "may not
#                 apply" to ChatGPT-User; treat a Disallow here as a statement
#                 of intent, not as effective blocking.
# ---------------------------------------------------------------------------
AI_AGENTS = {
    # token: (operator, category, citation_impact)
    "GPTBot":               ("OpenAI",       "training",     "none"),
    "OAI-SearchBot":        ("OpenAI",       "search-index", "removes"),
    "ChatGPT-User":         ("OpenAI",       "live-fetch",   "intent"),
    "ClaudeBot":            ("Anthropic",    "training",     "none"),
    "Claude-SearchBot":     ("Anthropic",    "search-index", "removes"),
    "Claude-User":          ("Anthropic",    "live-fetch",   "intent"),
    "anthropic-ai":         ("Anthropic",    "legacy",       "none"),
    "PerplexityBot":        ("Perplexity",   "search-index", "removes"),
    "Perplexity-User":      ("Perplexity",   "live-fetch",   "intent"),
    "Googlebot":            ("Google",       "search-index", "removes"),
    "Google-Extended":      ("Google",       "training",     "none"),
    "Applebot":             ("Apple",        "search-index", "removes"),
    "Applebot-Extended":    ("Apple",        "training",     "none"),
    "Bingbot":              ("Microsoft",    "search-index", "removes"),
    "DuckAssistBot":        ("DuckDuckGo",   "search-index", "removes"),
    "MistralAI-User":       ("Mistral",      "live-fetch",   "intent"),
    "CCBot":                ("Common Crawl", "training",     "none"),
    "Amazonbot":            ("Amazon",       "training",     "none"),
    "meta-externalagent":   ("Meta",         "training",     "none"),
    "meta-externalfetcher": ("Meta",         "live-fetch",   "intent"),
    "Bytespider":           ("ByteDance",    "training",     "none"),
}

# Cloudflare Content Signals Policy directives, now present on millions of
# domains and auto-injected into robots.txt by the CDN. A parser that doesn't
# recognise these misreads modern robots.txt files.
CONTENT_SIGNALS_RE = re.compile(
    r"(?im)^\s*content-signal:\s*(.+)$")
SIGNAL_PAIR_RE = re.compile(r"(search|ai-input|ai-train)\s*=\s*(yes|no)", re.I)

BLOCK_TAGS = {"div", "section", "article", "main", "p", "li", "td", "th", "blockquote",
              "header", "footer", "nav", "aside", "figure", "figcaption", "form",
              "h1", "h2", "h3", "h4", "h5", "h6", "pre", "dd", "dt"}
BOILERPLATE_TAGS = {"nav", "header", "footer", "aside"}
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}

SPA_ROOT_RE = re.compile(r'id=["\'](root|app|__next|__nuxt|app-root|react-root|ng-app|svelte)["\']', re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3,5}\)?[\s.-]?\d{3}[\s.-]?\d{3,4}\b")
PRICE_RE = re.compile(r"(?:[$€£₹¥]|USD|EUR|GBP|INR)\s?\d[\d,]*(?:\.\d{2})?", re.I)
ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b|\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b")
HOURS_RE = re.compile(
    r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?\s*(?:-|–|to|through)?\s*"
    r"(?:(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?)?\s*:?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)", re.I)
FOUNDED_RE = re.compile(r"\b(?:founded|established|est\.|since|incorporated)\s+(?:in\s+)?((?:19|20)\d{2})\b", re.I)
# Capture an optional range end so "© 2001-2026" reads as 2026, not 2001. A bare
# start year with no range is by far the most common false "stale" trigger.
# React/Next.js SSR streaming often interpolates each number as its own text
# node and drops an empty "<!-- -->" comment between them (observed live on
# flipkart.com: "&copy; 2007-<!-- -->2026<!-- --> Flipkart.com"), so the gap
# around the dash must tolerate an HTML comment, not just whitespace.
_CY_GAP = r"(?:<!--.*?-->|\s)*"
COPYRIGHT_YEAR_RE = re.compile(
    r"(?:©|&copy;|copyright)\D{0,15}((?:19|20)\d{2})"
    rf"(?:{_CY_GAP}(?:-|&[nm]dash;|[‐-―]){_CY_GAP}((?:19|20)\d{{2}}))?",
    re.I | re.DOTALL,
)
UPDATED_YEAR_RE = re.compile(r"(?:last updated|updated on|last modified|reviewed)\D{0,10}((?:19|20)\d{2})", re.I)
COMING_SOON_RE = re.compile(r"\b(coming soon|launching soon|under construction|check back soon|"
                            r"page (?:is )?(?:currently )?unavailable|lorem ipsum)\b", re.I)
CTA_RE = re.compile(r"\b(buy now|shop now|add to cart|get started|start free|sign up|"
                    r"book (?:a )?demo|request a demo|contact us|try (?:it )?free|"
                    r"subscribe|get a quote|apply now|book now|schedule a call)\b", re.I)
LOGIN_WALL_RE = re.compile(r"\b(sign in to (?:continue|view|read)|log in to (?:continue|view|read)|"
                           r"subscribe to (?:continue|read|view)|create a free account to continue|"
                           r"members only)\b", re.I)
# Deliberately narrow: a server-side consent GATE ("accept cookies or you get
# nothing"), not the ordinary footer disclosure almost every site carries
# ("we use cookies to improve your experience"). The trigger requires an
# explicit "to continue/access/view" clause -- ordinary disclosure text does
# not have one, so it never matches.
CONSENT_WALL_RE = re.compile(
    r"\b(accept (?:all )?cookies to (?:continue|view|access|read)|"
    r"please accept (?:our )?cookies? to (?:continue|view|access)|"
    r"you must accept (?:our use of )?cookies to (?:continue|access)|"
    r"enable cookies to (?:continue|access|view)|"
    r"consent is required to (?:access|view) this (?:site|page|content))\b", re.I)

SKIP_PATH_WORDS = ("login", "signin", "sign-in", "signup", "sign-up", "join", "logout", "cart",
                   "checkout", "account", "wp-admin", "admin", "basket", "my-account")
SKIP_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".zip",
                   ".css", ".js", ".mp4", ".mp3", ".woff", ".woff2", ".ttf", ".xml", ".rss",
                   ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".dmg", ".exe")
# Link text / URL fragments that indicate a page worth sampling, highest value first.
PRIORITY_WORDS = ["about", "pricing", "price", "product", "service", "contact", "docs",
                  "faq", "blog", "news", "team", "admission", "program", "course", "shop"]

_last_request = {}


# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------
def _throttle(host):
    last = _last_request.get(host, 0)
    wait = REQUEST_DELAY - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _last_request[host] = time.time()


class _ChainRecorder(urllib.request.HTTPRedirectHandler):
    """urllib follows redirects silently and keeps only the final URL, so a
    three-hop chain and a direct hit look identical. Recording the hops lets the
    audit report chains that waste crawl budget, loops that strand a crawler,
    and downgrades to plain HTTP in the middle of an otherwise-HTTPS journey."""

    def __init__(self):
        super().__init__()
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append({"from": req.full_url, "status": code, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _rate_limit_pause(headers, attempt):
    """Honour Retry-After when a host asks us to slow down.

    Without this the crawl records a page that would have succeeded as a
    failure, and keeps hammering a host that explicitly asked it to stop --
    which is the behaviour the guardrails exist to prevent.
    """
    raw = (headers or {}).get("retry-after", "")
    try:
        wait = float(str(raw).strip())
    except (TypeError, ValueError):
        wait = 0.0
    if wait <= 0:
        wait = 2.0 * (attempt + 1)          # polite exponential-ish fallback
    return max(0.5, min(wait, 10.0))        # never stall the whole run on one host


def fetch(url, timeout=TIMEOUT, _attempt=0):
    """GET a URL. Never raises; returns a dict describing what happened.

    Retries at most twice on HTTP 429, waiting for whatever the host asked for.
    """
    _throttle(urlparse(url).netloc)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    recorder = _ChainRecorder()
    opener = urllib.request.build_opener(recorder)
    started = time.time()
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(MAX_BYTES)
            if resp.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                text = raw.decode(charset, errors="replace")
            except (LookupError, TypeError):
                text = raw.decode("utf-8", errors="replace")
            return {"url": url, "final_url": resp.geturl(), "status": resp.status,
                    "headers": {k.lower(): v for k, v in resp.headers.items()},
                    "text": text, "bytes": len(raw), "redirect_chain": recorder.chain,
                    "elapsed_ms": int((time.time() - started) * 1000), "error": None}
    except urllib.error.HTTPError as e:
        hdrs = {k.lower(): v for k, v in (e.headers or {}).items()}
        if e.code == 429 and _attempt < 2:
            pause = _rate_limit_pause(hdrs, _attempt)
            print(f"[collector] 429 from {urlparse(url).netloc}; waiting {pause:.1f}s "
                  f"(attempt {_attempt + 1}/2)", file=sys.stderr)
            time.sleep(pause)
            return fetch(url, timeout=timeout, _attempt=_attempt + 1)
        body = ""
        try:
            body = e.read(MAX_BYTES).decode("utf-8", errors="replace")
        except Exception:
            pass
        return {"url": url, "final_url": url, "status": e.code, "headers": hdrs,
                "text": body, "bytes": len(body), "redirect_chain": recorder.chain,
                "elapsed_ms": int((time.time() - started) * 1000), "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"url": url, "final_url": url, "status": None, "headers": {}, "text": "",
                "bytes": 0, "redirect_chain": recorder.chain,
                "elapsed_ms": int((time.time() - started) * 1000),
                "error": f"{type(e).__name__}: {e}"}


def site_root(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def resolve_entry(raw):
    """Accept 'example.com' or a full URL; try https then http."""
    candidates = [raw] if "://" in raw else [f"https://{raw}", f"http://{raw}"]
    last = None
    for c in candidates:
        r = fetch(c)
        last = r
        if r["status"] and r["status"] < 400:
            return r
    return last


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------
class DocParser(HTMLParser):
    """Single-pass structural extractor.

    Beyond tags/metadata it segments the document into blocks and tracks, per
    block, how much of the text sits inside links and whether the block is
    inside nav/header/footer/aside. That is what lets us separate real article
    text from navigation boilerplate without CSS or a DOM library -- the
    link-density heuristic used by mainstream content-extraction algorithms.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.lang = ""
        self.base_href = None
        self.meta = {}
        self.og = {}
        self.twitter = {}
        self.robots_meta = ""
        self.canonical = None
        self.hreflangs = []
        self.has_favicon = False
        self.feeds = []

        self.jsonld_raw = []
        self.microdata_types = []
        self.rdfa_types = []
        self.microformats = []

        self.headings = []
        self.images = []
        self.links = []
        self.iframes = []
        self.scripts = {"total": 0, "external": 0, "head_blocking": 0, "inline_bytes": 0}
        self.counts = {"video": 0, "audio": 0, "canvas": 0, "svg": 0, "table": 0,
                       "picture": 0, "details": 0, "dialog": 0}
        self.forms = {"count": 0, "search": False, "inputs": 0, "labeled": 0,
                      "submits_offsite": False, "has_password": False}
        self.viewport = False
        self.noscript_len = 0
        self.aria_labels = 0
        self.has_nav = False
        self.has_breadcrumbs = False
        self.nav_links = 0
        self._nav_depth = 0

        # Citability signals (see references/evidence-base.md for why each exists)
        self.emphasis_chars = 0
        self.unit_counts = {"p": 0, "li": 0, "tr": 0, "pre": 0, "dt": 0}
        self.quote_tags = {"blockquote": 0, "q": 0, "cite": 0}
        self.paragraph_words = []
        self.sections = []          # [{heading, level, words}]
        self.intro_words = 0
        self._seen_h1 = False
        self._in_intro = False
        self._cur_section = None
        self._emph_depth = 0
        self._p_words = 0
        self._in_p = False

        # block segmentation
        self.blocks = []          # {text_len, link_text_len, boilerplate, tag}
        self._block_stack = []
        self._boiler_depth = 0
        self._skip_depth = 0
        self._in_title = False
        self._in_ld = None
        self._in_noscript = False
        self._link_depth = 0
        self._cur_link = None
        self._cur_heading = None
        self._label_for = 0
        self._text_chunks = []

    # -- helpers ------------------------------------------------------------
    def _add_text(self, data):
        stripped = data.strip()
        if not stripped:
            return
        self._text_chunks.append(stripped)
        n = len(stripped)
        if self._block_stack:
            b = self._block_stack[-1]
            b["text_len"] += n
            if self._link_depth:
                b["link_text_len"] += n

    def _open_block(self, tag):
        self._block_stack.append({"tag": tag, "text_len": 0, "link_text_len": 0,
                                  "boilerplate": self._boiler_depth > 0})

    def _close_block(self):
        if self._block_stack:
            self.blocks.append(self._block_stack.pop())

    # -- handlers -----------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TEXT_TAGS:
            self._skip_depth += 1
            if tag == "svg":
                self.counts["svg"] += 1
            if tag == "noscript":
                self._in_noscript = True

        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "base" and a.get("href"):
            self.base_href = a["href"]
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or a.get("itemprop") or "").lower()
            content = a.get("content", "")
            if name:
                if name.startswith("og:"):
                    self.og[name] = content
                elif name.startswith("twitter:"):
                    self.twitter[name] = content
                else:
                    self.meta[name] = content
                if name == "viewport":
                    self.viewport = True
                elif name == "robots":
                    self.robots_meta = content
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href", "")
            if "canonical" in rel:
                self.canonical = href
            if "alternate" in rel:
                if a.get("hreflang"):
                    self.hreflangs.append(a["hreflang"])
                if "rss" in (a.get("type") or "") or "atom" in (a.get("type") or ""):
                    self.feeds.append(href)
            if "icon" in rel:
                self.has_favicon = True
        elif tag == "script":
            stype = (a.get("type") or "").lower()
            self.scripts["total"] += 1
            if a.get("src"):
                self.scripts["external"] += 1
                if not ("async" in a or "defer" in a or stype == "module"):
                    self.scripts["head_blocking"] += 1
            if stype == "application/ld+json":
                self._in_ld = []
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self._cur_heading = [level, ""]
            if self._cur_section:
                self.sections.append(self._cur_section)
            self._cur_section = {"level": level, "heading": "", "words": 0}
            if level == 1:
                self._seen_h1 = True
                self._in_intro = True
            elif self._seen_h1 and self._in_intro:
                self._in_intro = False       # intro ends at the first sub-heading
        elif tag in ("b", "strong", "em", "i", "mark", "u"):
            self._emph_depth += 1
        elif tag == "p":
            self._in_p = True
            self._p_words = 0
            self.unit_counts["p"] += 1
        elif tag in ("li", "tr", "pre", "dt"):
            self.unit_counts[tag] = self.unit_counts.get(tag, 0) + 1
        elif tag in ("blockquote", "q", "cite"):
            self.quote_tags[tag] = self.quote_tags.get(tag, 0) + 1
        elif tag == "img":
            self.images.append({"src": a.get("src") or a.get("data-src", ""),
                                "alt": a.get("alt"), "loading": a.get("loading")})
        elif tag == "a":
            self._link_depth += 1
            if self._nav_depth:
                self.nav_links += 1
            self._cur_link = {"href": a.get("href", ""), "text": "",
                              "aria": a.get("aria-label", "")}
        elif tag == "iframe":
            self.iframes.append({"src": a.get("src", ""), "title": a.get("title")})
        elif tag in ("video", "audio", "canvas", "table", "picture", "details", "dialog"):
            self.counts[tag] = self.counts.get(tag, 0) + 1
        elif tag == "form":
            self.forms["count"] += 1
            action = a.get("action", "")
            if action.startswith("http") and urlparse(action).netloc:
                self.forms["submits_offsite"] = True
            if (a.get("role") or "").lower() == "search":
                self.forms["search"] = True
        elif tag == "input":
            itype = (a.get("type") or "text").lower()
            if itype == "password":
                self.forms["has_password"] = True
            if itype not in ("hidden", "submit", "button"):
                self.forms["inputs"] += 1
                if a.get("aria-label") or a.get("title") or a.get("placeholder"):
                    self.forms["labeled"] += 1
            if itype == "search" or "search" in (a.get("name") or "").lower() \
               or "search" in (a.get("id") or "").lower():
                self.forms["search"] = True
        elif tag == "label":
            self._label_for += 1

        if a.get("aria-label"):
            self.aria_labels += 1
        if a.get("itemtype"):
            self.microdata_types.append(a["itemtype"])
        if a.get("typeof"):
            self.rdfa_types.append(a["typeof"])
        cls = a.get("class") or ""
        for token in cls.split():
            if token.startswith(("h-", "p-", "u-", "e-", "dt-")) and len(token) > 2:
                self.microformats.append(token)

        # Track <nav> separately from the wider boilerplate set: the number of
        # top-level navigation choices is an engagement signal in its own right,
        # and header/footer/aside links are not navigation choices.
        if tag == "nav":
            self._nav_depth += 1
            self.has_nav = True
            aria = (a.get("aria-label") or "") + " " + (a.get("class") or "")
            if "breadcrumb" in aria.lower():
                self.has_breadcrumbs = True
        if tag in BOILERPLATE_TAGS:
            self._boiler_depth += 1
        if tag in BLOCK_TAGS:
            self._open_block(tag)

    def handle_endtag(self, tag):
        if tag == "nav" and self._nav_depth:
            self._nav_depth -= 1
        if tag in SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
            if tag == "noscript":
                self._in_noscript = False
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_ld is not None:
            self.jsonld_raw.append("".join(self._in_ld))
            self._in_ld = None
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._cur_heading:
            text = " ".join(self._cur_heading[1].split())
            if text:
                self.headings.append([self._cur_heading[0], text[:200]])
                if self._cur_section is not None:
                    self._cur_section["heading"] = text[:200]
            self._cur_heading = None
        if tag in ("b", "strong", "em", "i", "mark", "u") and self._emph_depth:
            self._emph_depth -= 1
        if tag == "p" and self._in_p:
            self._in_p = False
            if self._p_words:
                self.paragraph_words.append(self._p_words)
        if tag == "a":
            if self._link_depth:
                self._link_depth -= 1
            if self._cur_link is not None:
                self.links.append((self._cur_link["href"],
                                   " ".join(self._cur_link["text"].split())[:150],
                                   self._cur_link["aria"]))
                self._cur_link = None
        if tag in BLOCK_TAGS:
            self._close_block()
        if tag in BOILERPLATE_TAGS and self._boiler_depth:
            self._boiler_depth -= 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag in BLOCK_TAGS:
            self._close_block()
        if tag in BOILERPLATE_TAGS and self._boiler_depth:
            self._boiler_depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld is not None:
            self._in_ld.append(data)
            return
        if self._skip_depth:
            if self._in_noscript:
                self.noscript_len += len(data.strip())
            return
        if self._cur_heading is not None:
            self._cur_heading[1] += data
        if self._cur_link is not None:
            self._cur_link["text"] += data
        self._add_text(data)

        stripped = data.strip()
        if stripped:
            words = len(stripped.split())
            if self._emph_depth:
                self.emphasis_chars += len(stripped)
            if self._in_p:
                self._p_words += words
            if self._cur_section is not None:
                self._cur_section["words"] += words
            if self._in_intro and self._cur_heading is None:
                self.intro_words += words

    # -- derived ------------------------------------------------------------
    def finish(self):
        while self._block_stack:
            self._close_block()
        if self._cur_section:
            self.sections.append(self._cur_section)
            self._cur_section = None
        if self._in_p and self._p_words:
            self.paragraph_words.append(self._p_words)
            self._in_p = False

    @property
    def all_text(self):
        return " ".join(self._text_chunks)

    def main_text(self):
        """Content blocks only: leaf-ish blocks with low link density, outside
        nav/header/footer/aside. Mirrors the link-density heuristic that
        mainstream extractors use to drop boilerplate."""
        parts = []
        for b in self.blocks:
            if b["boilerplate"] or b["text_len"] < 25:
                continue
            density = b["link_text_len"] / b["text_len"] if b["text_len"] else 1.0
            if density <= 0.45:
                parts.append(b)
        return sum(b["text_len"] - b["link_text_len"] for b in parts)

    def boilerplate_len(self):
        return sum(b["text_len"] for b in self.blocks if b["boilerplate"])

    def link_density(self):
        total = sum(b["text_len"] for b in self.blocks)
        linked = sum(b["link_text_len"] for b in self.blocks)
        return round(linked / total, 3) if total else 0.0


def parse_html(html):
    p = DocParser()
    try:
        p.feed(html)
    except Exception:
        pass
    try:
        p.finish()
    except Exception:
        pass
    return p


def walk_jsonld_types(obj, out):
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, list):
            out.update(str(x) for x in t)
        elif t:
            out.add(str(t))
        for v in obj.values():
            walk_jsonld_types(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_jsonld_types(v, out)


def collect_jsonld(parser):
    parsed, invalid, types = [], 0, set()
    for raw in parser.jsonld_raw:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            invalid += 1
            continue
        parsed.append(obj)
        walk_jsonld_types(obj, types)
    return parsed, invalid, sorted(types)


def extract_facts(text, html, parser):
    """Pull the concrete, quotable facts an assistant would need to answer a
    question about this brand. Presence/absence of these is what the
    answerability probe reasons over."""
    emails = sorted(set(EMAIL_RE.findall(text)))[:10]
    tel_links = [h[4:] for h, _, _ in parser.links if h.lower().startswith("tel:")]
    # Every separator in PHONE_RE is optional (real numbers are formatted every
    # which way), which also lets it match an unbroken run of 9-12 digits --
    # a percentage, an order ID, a tracking number. Require at least one
    # actual separator character so a bare digit run is never read as a phone
    # number (observed live: python.org's "66.66666666666667%" stat).
    phones = sorted(set(p.strip() for p in PHONE_RE.findall(text)
                        if any(c in p for c in " .-()")))[:10]
    return {
        "emails": emails,
        "tel_links": sorted(set(tel_links))[:10],
        "phones": phones,
        "prices": sorted(set(PRICE_RE.findall(text)))[:15],
        "postal_codes": sorted(set(ZIP_RE.findall(text)))[:5],
        "hours_mentions": len(HOURS_RE.findall(text)),
        "founded_years": sorted(set(FOUNDED_RE.findall(text)))[:3],
        # findall yields (start, end) tuples; the effective year is the range
        # end where present, otherwise the start.
        "copyright_years": sorted({(e or s) for s, e in COPYRIGHT_YEAR_RE.findall(html)})[:3],
        "updated_years": sorted(set(UPDATED_YEAR_RE.findall(html)))[:3],
        "coming_soon": sorted(set(m.lower() for m in COMING_SOON_RE.findall(text)))[:5],
        "cta_matches": sorted(set(m.lower() for m in CTA_RE.findall(html)))[:10],
        "login_wall": bool(LOGIN_WALL_RE.search(text)),
        "consent_wall": bool(CONSENT_WALL_RE.search(text)),
    }


# --- Citability signals -----------------------------------------------------
# Every regex/threshold below traces to a measured finding; see
# references/evidence-base.md for the effect size and source behind each.
STAT_RES = [
    re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:%|percent|per cent)", re.I),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:x|×|-fold|bn|billion|million|thousand|k)\b", re.I),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|kg|km|mi|mph|GB|MB|TB|ms|hrs?|hours?|days?|"
               r"weeks?|months?|years?|users|customers|employees)\b", re.I),
]
ATTRIB_RE = re.compile(r"\b(said|says|according to|explains?|notes?|told|stated|writes?|"
                       r"reported by|published by)\b", re.I)
QUOTE_SPAN_RE = re.compile(r"[“\"]([^“”\"]{20,400})[”\"]")
HEDGE_RE = re.compile(r"\b(might|may|could|possibly|perhaps|arguably|somewhat|relatively|"
                      r"seems? to|appears? to|it is believed|roughly|approximately|around|"
                      r"some experts|generally|typically|often|usually)\b", re.I)
HEDGED_NUMBER_RE = re.compile(r"\b(around|about|roughly|approximately|up to|as much as)\s+\d", re.I)
COMPARISON_RE = re.compile(r"\b(vs\.?|versus|compared (?:to|with)|alternatives? to|"
                           r"better than|instead of|rather than)\b", re.I)
SPEC_PAIR_RE = re.compile(r"^\s*[A-Z][\w /()\-]{2,30}\s*:\s*\S", re.M)
AUTHORITATIVE_TLDS = (".gov", ".edu", ".ac.uk", ".org", ".int", ".mil")
STOPWORDS = {"the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with", "your",
             "our", "is", "are", "we", "you", "it", "at", "by", "from", "best", "top",
             "home", "official", "site", "website", "welcome", "page"}


def compute_citability(parser, text, page_url):
    """Score the signals that measurably separate cited from uncited pages.

    Split into TIER 1 gatekeepers (failure is near-disqualifying) and TIER 2
    structure (only pays once tier 1 passes). That ordering is not stylistic --
    it resolves a real contradiction in the literature, where a head-to-head
    study found formatting negligible while a structural study found it worth
    +17%. Formatting cannot rescue a page that fails a gatekeeper.
    """
    words = text.split()
    wc = len(words) or 1
    per100 = lambda n: round(n * 100.0 / wc, 2)

    stats = sum(len(r.findall(text)) for r in STAT_RES)

    quotes = sum(parser.quote_tags.values())
    attributed = 0
    for m in QUOTE_SPAN_RE.finditer(text):
        window = text[max(0, m.start() - 120): m.end() + 120]
        if ATTRIB_RE.search(window):
            attributed += 1

    host = urlparse(page_url).netloc.lower()
    ext_domains, authoritative = set(), set()
    for href, _, _ in parser.links:
        try:
            netloc = urlparse(href).netloc.lower()
        except ValueError:
            continue
        if netloc and netloc != host:
            ext_domains.add(netloc)
            if netloc.endswith(AUTHORITATIVE_TLDS):
                authoritative.add(netloc)

    hedges = len(HEDGE_RE.findall(text))

    # Structural ratios (targets from the structural-engineering study)
    u = parser.unit_counts
    structured_units = u.get("li", 0) + u.get("tr", 0) + u.get("pre", 0)
    total_units = structured_units + u.get("p", 0)
    f_d = round(structured_units / total_units, 3) if total_units else 0.0
    e_d = round(parser.emphasis_chars / len(text), 4) if text else 0.0

    levels = [h[0] for h in parser.headings]
    depth = max(levels) if levels else 0
    skipped = any(b - a > 1 for a, b in zip(levels, levels[1:]) if b > a)

    body_sections = [s for s in parser.sections if s["words"] > 0]
    in_band = sum(1 for s in body_sections if 150 <= s["words"] <= 300)
    oversized = sum(1 for s in body_sections if s["words"] > 300)

    # Query-term coverage: do the terms the page claims to be about (title/H1)
    # actually appear in the opening body text?
    h1 = next((h[1] for h in parser.headings if h[0] == 1), "")
    claim_terms = {w.strip(".,:;!?()").lower() for w in (parser.title + " " + h1).split()
                   if len(w) > 3}
    claim_terms -= STOPWORDS
    opening = " ".join(words[:200]).lower()
    covered = {t for t in claim_terms if t in opening}
    coverage = round(len(covered) / len(claim_terms), 2) if claim_terms else None

    # Where do the load-bearing facts sit? Facts stranded in the middle of a
    # long page perform worse than the page not being supplied at all.
    def first_pos(rx):
        m = rx.search(text)
        return round(m.start() / len(text), 3) if m and text else None

    return {
        "word_count": wc,
        "tier1": {
            "statistics_count": stats,
            "statistics_per_100w": per100(stats),
            "quote_tags": quotes,
            "attributed_quotes": attributed,
            "external_domains": len(ext_domains),
            "authoritative_domains": sorted(authoritative)[:8],
            "has_price": bool(PRICE_RE.search(text)),
            "price_position": first_pos(PRICE_RE),
            "spec_pairs": len(SPEC_PAIR_RE.findall(text)) + parser.unit_counts.get("dt", 0),
            "has_spec_table": parser.counts.get("table", 0) > 0,
            "comparison_markers": len(COMPARISON_RE.findall(text)),
            "hedges_per_100w": per100(hedges),
            "hedged_numbers": len(HEDGED_NUMBER_RE.findall(text)),
            "query_term_coverage": coverage,
            "uncovered_claim_terms": sorted(claim_terms - covered)[:10],
        },
        "tier2": {
            "heading_depth": depth,
            "heading_levels_skipped": skipped,
            "heading_count": len(levels),
            "sections": len(body_sections),
            "sections_in_150_300_band": in_band,
            "sections_over_300w": oversized,
            "median_paragraph_words": (sorted(parser.paragraph_words)[len(parser.paragraph_words) // 2]
                                       if parser.paragraph_words else 0),
            "structured_format_ratio": f_d,
            "emphasis_density": e_d,
            "intro_summary_words": parser.intro_words,
        },
    }


# --- Structured-data verdict ladder -----------------------------------------
# Reporting "no structured data" when a site uses microdata, RDFa or
# microformats instead of JSON-LD is a textbook false positive. Millions of
# WordPress themes emit classic microformats (`vcard`, `hentry`); Microdata and
# RDFa annotate the visible text directly, so their fact-parity is arguably
# BETTER than JSON-LD's. Always resolve the full ladder before concluding.
MF1_CLASSES = ("vcard", "vevent", "hcard", "hcalendar", "hreview", "hrecipe", "hproduct",
               "hresume", "hatom", "hentry", "hfeed", "adr", "geo", "hreview-aggregate")
MF1_RE = re.compile(r'class\s*=\s*["\'][^"\']*\b(' + "|".join(MF1_CLASSES) + r')\b', re.I)
MICRODATA_ANY_RE = re.compile(r"\sitem(scope|type|prop)\b", re.I)
RDFA_STRICT_RE = re.compile(r'\s(typeof|vocab)\s*=\s*["\']', re.I)
REL_ME_RE = re.compile(r'rel\s*=\s*["\'][^"\']*\bme\b', re.I)
STATE_BLOB_RE = re.compile(r"(__NEXT_DATA__|window\.__NUXT__|window\.__INITIAL_STATE__|"
                           r"window\.__APOLLO_STATE__|self\.__next_f|__remixContext)", re.I)


def structured_data_verdict(html, page, parser):
    strong = bool(page["jsonld_types"]) or bool(MICRODATA_ANY_RE.search(html)) \
        or bool(RDFA_STRICT_RE.search(html)) \
        or any(c.startswith("h-") for c in parser.microformats)
    legacy = bool(MF1_RE.search(html))
    weak = bool(parser.og) or bool(parser.twitter) or \
        any(k.startswith(("dc.", "dcterms.")) for k in parser.meta)
    adjacent = bool(REL_ME_RE.search(html)) or bool(parser.feeds) or \
        bool(STATE_BLOB_RE.search(html))

    if page["jsonld_invalid"] and not page["jsonld_types"]:
        verdict = "INVALID_STRUCTURED_DATA"   # worse than absent: present but unparseable
    elif strong:
        verdict = "STRUCTURED_DATA_PRESENT"
    elif legacy:
        verdict = "LEGACY_MICROFORMATS_ONLY"
    elif weak:
        verdict = "SOCIAL_META_ONLY"
    elif adjacent:
        verdict = "MACHINE_HINTS_ONLY"
    else:
        verdict = "NO_STRUCTURED_DATA"
    return {"verdict": verdict, "strong": strong, "legacy_microformats": legacy,
            "social_meta": weak, "machine_hints": adjacent,
            "embedded_state_blob": bool(STATE_BLOB_RE.search(html))}


# --- Extractability failure modes -------------------------------------------
# Ways a fact is plainly visible to a human yet invisible to a text extractor.
FACTLIKE_IMG_RE = re.compile(r"(price|pricing|menu|spec|table|chart|graph|infographic|"
                             r"comparison|tier|plan|rate|schedule|hours|contact)", re.I)
SVG_TEXT_RE = re.compile(r"<svg\b[^>]*>.*?<t(?:ext|span)\b", re.S | re.I)
CSS_CONTENT_RE = re.compile(r'content\s*:\s*(["\'])(.*?)\1', re.I)
MUSTACHE_RE = re.compile(r"\{\{\s*[\w.]+\s*\}\}")
BINDING_RE = re.compile(r"\s(v-(?:text|html|bind)|x-(?:text|html)|ng-(?:bind|model))\s*=", re.I)
DATA_FACT_RE = re.compile(r'\sdata-(price|amount|value|rating|count|date|cost)\s*=\s*"([^"]+)"', re.I)
FACT_PDF_RE = re.compile(r'href\s*=\s*["\']([^"\']+\.pdf)["\']', re.I)
EMBED_HOST_RE = re.compile(r"(datawrapper|flourish|tableau|docs\.google|airtable|typeform|infogram)", re.I)
CUSTOM_EL_RE = re.compile(r"<([a-z][a-z0-9]*-[a-z0-9-]+)[^>]*>", re.I)
OBFUSCATED_EMAIL_RE = re.compile(r"\[\s*at\s*\]|\(\s*at\s*\)|&#(?:64|0*x40);", re.I)
LOADMORE_RE = re.compile(r">\s*(load more|show more|view all|see all)\s*<", re.I)


def extractability_risks(html, text, parser, page):
    """Flag likely-invisible facts. Each entry is a SIGNAL, never a certainty --
    downstream skills must hedge accordingly."""
    risks = []

    fact_imgs = [i for i in parser.images
                 if FACTLIKE_IMG_RE.search(i.get("src") or "")
                 and not (i.get("alt") or "").strip()]
    if fact_imgs:
        risks.append({"mode": "fact_bearing_image_without_alt", "count": len(fact_imgs),
                      "examples": [i["src"][:120] for i in fact_imgs[:3]]})

    if len(text) < 500 and len([i for i in parser.images if i.get("src")]) >= 3:
        risks.append({"mode": "image_heavy_text_sparse", "text_chars": len(text),
                      "images": len(parser.images)})

    if SVG_TEXT_RE.search(html):
        risks.append({"mode": "text_inside_svg", "note": "most extractors drop <svg> entirely"})
    if parser.counts.get("canvas"):
        risks.append({"mode": "canvas_rendered_content", "count": parser.counts["canvas"]})

    css_text = [v for _, v in CSS_CONTENT_RE.findall(html)
                if v.strip() and re.search(r"[A-Za-z0-9]{3}", v) and "\\f" not in v]
    if css_text:
        risks.append({"mode": "css_generated_text", "count": len(css_text),
                      "examples": css_text[:3]})

    if MUSTACHE_RE.search(text) or BINDING_RE.search(html):
        risks.append({"mode": "unrendered_template_binding",
                      "note": "template syntax survived into served HTML -- value never rendered server-side"})

    data_facts = [(k, v) for k, v in DATA_FACT_RE.findall(html) if v not in text]
    if data_facts:
        risks.append({"mode": "fact_only_in_data_attribute", "count": len(data_facts),
                      "examples": [f"data-{k}={v}"[:80] for k, v in data_facts[:3]]})

    pdfs = [p for p in FACT_PDF_RE.findall(html) if FACTLIKE_IMG_RE.search(p)]
    if pdfs:
        risks.append({"mode": "facts_locked_in_pdf", "examples": pdfs[:3]})

    embeds = [f["src"] for f in parser.iframes if EMBED_HOST_RE.search(f.get("src") or "")]
    if embeds:
        risks.append({"mode": "third_party_embed_content", "examples": embeds[:3]})

    customs = {m for m in CUSTOM_EL_RE.findall(html)} - {"font-face"}
    if customs and len(text) < 1000:
        risks.append({"mode": "web_components_possible_shadow_dom",
                      "examples": sorted(customs)[:5]})

    media = parser.counts.get("video", 0) + parser.counts.get("audio", 0)
    if media and "track" not in html.lower():
        risks.append({"mode": "media_without_captions", "count": media})

    if OBFUSCATED_EMAIL_RE.search(html):
        risks.append({"mode": "obfuscated_contact_details"})
    if LOADMORE_RE.search(html):
        risks.append({"mode": "content_behind_load_more"})
    if parser.counts.get("table", 0) == 0 and re.search(r"\b(table below|see (?:the )?chart|as shown below)\b", text, re.I):
        risks.append({"mode": "referenced_table_not_in_markup"})

    return risks


def jsonld_dates(parser):
    out = {}
    blob = " ".join(parser.jsonld_raw)
    for key in ("dateModified", "datePublished", "foundingDate"):
        m = re.search(key + r'"\s*:\s*"([^"]+)"', blob)
        if m:
            out[key] = m.group(1)
    return out


def jsonld_paywalled(parser):
    """True when the page's own structured data explicitly declares itself
    inaccessible for free (schema.org isAccessibleForFree: false) -- a soft
    paywall the raw HTML can otherwise look completely normal for. This is a
    structured, self-declared signal, not a heuristic guess: a subscribe CTA
    or a mention of "subscribe" is NOT paywall evidence on its own."""
    blob = " ".join(parser.jsonld_raw)
    return bool(re.search(r'"isAccessibleForFree"\s*:\s*(false|"false")', blob, re.I))


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------
def score_link(href, text):
    low = (href + " " + text).lower()
    for i, w in enumerate(PRIORITY_WORDS):
        if w in low:
            return len(PRIORITY_WORDS) - i
    return 0


def normalize(url):
    url = url.split("#")[0]
    return url[:-1] if url.endswith("/") and urlparse(url).path != "/" else url


def crawlable(url, domain):
    p = urlparse(url)
    if p.netloc != domain or p.scheme not in ("http", "https"):
        return False
    low = url.lower()
    if low.endswith(SKIP_EXTENSIONS):
        return False
    return not any(w in low for w in SKIP_PATH_WORDS)


def build_page_record(url, resp, depth):
    html = resp["text"] or ""
    parser = parse_html(html)
    jsonld, jsonld_invalid, jsonld_types = collect_jsonld(parser)
    text = parser.all_text
    domain = urlparse(resp["final_url"] or url).netloc

    internal, external = [], []
    for href, ltext, aria in parser.links:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        full = normalize(urljoin(resp["final_url"] or url, href))
        if urlparse(full).netloc == domain:
            internal.append([full, ltext or aria])
        else:
            external.append([full, ltext or aria])

    imgs = [i for i in parser.images if i.get("src")]
    record = {
        "url": url,
        "final_url": resp["final_url"],
        "status": resp["status"],
        "error": resp["error"],
        "depth": depth,
        "elapsed_ms": resp["elapsed_ms"],
        "redirect_chain": resp.get("redirect_chain") or [],
        "html_bytes": resp["bytes"],
        "https": (urlparse(resp["final_url"] or url).scheme == "https"),
        "headers": {k: v for k, v in resp["headers"].items()
                    if k in ("content-type", "x-robots-tag", "last-modified", "etag",
                             "cache-control", "server", "content-language")},
        "title": " ".join(parser.title.split())[:300],
        "lang": parser.lang,
        "canonical": parser.canonical,
        "hreflangs": parser.hreflangs[:10],
        "robots_meta": parser.robots_meta,
        "meta_description": parser.meta.get("description", ""),
        "og": parser.og,
        "twitter": parser.twitter,
        "has_favicon": parser.has_favicon,
        "feeds": parser.feeds[:5],
        "jsonld": jsonld[:12],
        "jsonld_types": jsonld_types,
        "jsonld_invalid": jsonld_invalid,
        "jsonld_dates": jsonld_dates(parser),
        "paywalled": jsonld_paywalled(parser),
        "microdata_types": sorted(set(parser.microdata_types))[:15],
        "rdfa_types": sorted(set(parser.rdfa_types))[:15],
        "microformats": sorted(set(parser.microformats))[:15],
        "headings": parser.headings[:60],
        "text_len": len(text),
        "main_text_len": parser.main_text(),
        "boilerplate_text_len": parser.boilerplate_len(),
        "link_density": parser.link_density(),
        "text_sample": text[:2500],
        "word_count": len(text.split()),
        "links_internal": internal[:250],
        "links_external": external[:120],
        "images_total": len(imgs),
        "images_missing_alt": sum(1 for i in imgs if not (i.get("alt") or "").strip()),
        "iframes": parser.iframes[:10],
        "media_counts": parser.counts,
        "scripts": parser.scripts,
        "spa_root": bool(SPA_ROOT_RE.search(html)),
        "noscript_len": parser.noscript_len,
        "viewport": parser.viewport,
        "forms": parser.forms,
        "aria_labels": parser.aria_labels,
        "has_nav": parser.has_nav,
        "nav_links": parser.nav_links,
        "has_breadcrumbs": parser.has_breadcrumbs or "BreadcrumbList" in jsonld_types,
        "facts": extract_facts(text, html, parser),
    }
    record["citability"] = compute_citability(parser, text, resp["final_url"] or url)
    record["structured_data"] = structured_data_verdict(html, record, parser)
    record["extractability_risks"] = extractability_risks(html, text, parser, record)
    return record


def analyze_robots(entry_url):
    root = site_root(entry_url)
    res = fetch(root + "/robots.txt")
    raw = res["text"] if res["status"] == 200 else ""
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(raw.splitlines() if raw else [])

    agents = {}
    for token, (operator, category, impact) in AI_AGENTS.items():
        try:
            allowed = rp.can_fetch(token, root + "/")
        except Exception:
            allowed = True
        agents[token] = {"operator": operator, "category": category,
                         "citation_impact": impact, "allowed_root": allowed}
    try:
        star_allowed = rp.can_fetch("*", root + "/")
    except Exception:
        star_allowed = True

    # Cloudflare Content Signals Policy (search / ai-input / ai-train = yes|no)
    signals = {}
    for line in CONTENT_SIGNALS_RE.findall(raw or ""):
        for key, val in SIGNAL_PAIR_RE.findall(line):
            signals[key.lower()] = val.lower()

    sitemaps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", raw or "")
    mentioned = [t for t in AI_AGENTS
                 if re.search(r"(?im)^\s*user-agent:\s*" + re.escape(t) + r"\s*$", raw or "")]
    return rp, {
        "status": res["status"],
        "present": res["status"] == 200 and bool(raw.strip()),
        "bytes": len(raw or ""),
        "star_allowed_root": star_allowed,
        "agents": agents,
        "agents_explicitly_named": mentioned,
        "content_signals": signals,
        "declared_sitemaps": sitemaps[:10],
        "raw_excerpt": (raw or "")[:1500],
    }


def probe_user_agents(url):
    """Fetch the same URL as a browser and as declared AI crawlers.

    robots.txt is only an advisory layer. CDN/WAF bot management (Cloudflare's
    one-click "Block AI Bots", AWS WAF, Akamai) blocks at the network layer and
    OVERRIDES robots.txt -- a site can publish a perfectly permissive
    robots.txt and still be completely invisible to assistants. That failure is
    undetectable by robots.txt analysis alone; only a differential fetch finds
    it. A browser-UA 200 alongside an AI-UA 403 is the signature.
    """
    probes = {
        "browser": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
        "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; "
                  "+https://openai.com/gptbot",
        "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ClaudeBot/1.0; "
                     "+claudebot@anthropic.com",
        "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
                         "PerplexityBot/1.0; +https://perplexity.ai/perplexitybot",
    }
    out = {}
    for i, (label, ua) in enumerate(probes.items()):
        # Space these out more than a normal crawl step. Four near-simultaneous
        # requests to one origin can trip its rate limiter, and a 429 provoked by
        # our own probe would then be misread as the site blocking AI crawlers.
        if i:
            time.sleep(1.0)
        _throttle(urlparse(url).netloc)
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read(200_000)
                out[label] = {"status": resp.status, "bytes": len(body), "error": None}
        except urllib.error.HTTPError as e:
            out[label] = {"status": e.code, "bytes": 0, "error": f"HTTP {e.code}"}
        except Exception as e:
            out[label] = {"status": None, "bytes": 0, "error": f"{type(e).__name__}"}

    browser = out.get("browser", {})
    blocked = []
    if browser.get("status") and browser["status"] < 400:
        for label, r in out.items():
            if label == "browser":
                continue
            # Hard block, or a body so much smaller it's a challenge/interstitial page.
            if r["status"] in (401, 403, 429, 503) or r["status"] is None:
                blocked.append({"agent": label, "status": r["status"], "error": r["error"]})
            elif r["bytes"] and browser["bytes"] and r["bytes"] < browser["bytes"] * 0.35:
                blocked.append({"agent": label, "status": r["status"],
                                "error": f"body {r['bytes']}B vs browser {browser['bytes']}B"})
    return {"probes": out, "blocked_agents": blocked,
            "network_layer_block_suspected": bool(blocked)}


def analyze_sitemap(entry_url, declared):
    urls_seen, checked = [], []
    candidates = declared[:2] or [site_root(entry_url) + "/sitemap.xml"]
    for sm in candidates:
        res = fetch(sm)
        entry = {"url": sm, "status": res["status"], "is_index": False, "url_count": 0}
        if res["status"] == 200 and res["text"]:
            body = res["text"]
            entry["is_index"] = "<sitemapindex" in body.lower()
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body, re.I)
            entry["url_count"] = len(locs)
            urls_seen.extend(locs[:400])
        checked.append(entry)
    return {"checked": checked,
            "total_urls_found": sum(c["url_count"] for c in checked),
            "sample_urls": [normalize(u) for u in urls_seen[:200]]}


def collect(entry, max_pages, max_depth, budget_seconds):
    started = time.time()
    first = resolve_entry(entry)
    if not first or first["status"] is None:
        return {
            "schema_version": COLLECTOR_VERSION,
            "site": entry,
            "entry_reachable": False,
            "entry_error": (first or {}).get("error", "unknown"),
            "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pages": [], "robots": {}, "sitemap": {}, "wellknown": {},
            "stats": {"pages_fetched": 0, "pages_failed": 1, "elapsed_seconds": 0},
        }

    base = first["final_url"]
    domain = urlparse(base).netloc
    rp, robots_info = analyze_robots(base)
    sitemap_info = analyze_sitemap(base, robots_info.get("declared_sitemaps", []))

    root = site_root(base)
    wellknown = {}
    for name, path in (("llms_txt", "/llms.txt"), ("security_txt", "/.well-known/security.txt")):
        r = fetch(root + path)
        wellknown[name] = {"status": r["status"],
                           "present": r["status"] == 200 and bool((r["text"] or "").strip()),
                           "starts_with_h1": (r["text"] or "").lstrip().startswith("#"),
                           "bytes": len(r["text"] or "")}

    ua_probe = probe_user_agents(base)

    home = build_page_record(base, first, 0)
    pages = [home]
    visited = {normalize(base)}
    failed, robots_skipped = [], []

    # BFS with priority ordering, bounded by pages/depth/wall-clock.
    frontier = []
    for href, text in home["links_internal"]:
        if crawlable(href, domain) and normalize(href) not in visited:
            frontier.append((-score_link(href, text), 1, normalize(href)))
    frontier.sort()

    while frontier and len(pages) < max_pages:
        if time.time() - started > budget_seconds:
            break
        _, depth, url = frontier.pop(0)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        try:
            if not rp.can_fetch("*", url):
                robots_skipped.append(url)
                continue
        except Exception:
            pass
        res = fetch(url)
        if res["status"] is None or res["status"] >= 400:
            failed.append({"url": url, "status": res["status"], "error": res["error"]})
            continue
        ctype = res["headers"].get("content-type", "")
        if ctype and "html" not in ctype.lower():
            continue
        rec = build_page_record(url, res, depth)
        pages.append(rec)
        if depth < max_depth:
            added = []
            for href, text in rec["links_internal"]:
                n = normalize(href)
                if crawlable(href, domain) and n not in visited:
                    added.append((-score_link(href, text), depth + 1, n))
            frontier.extend(added)
            frontier.sort()

    link_graph = {p["url"]: [normalize(h) for h, _ in p["links_internal"]][:150] for p in pages}

    return {
        "schema_version": COLLECTOR_VERSION,
        "site": base,
        "domain": domain,
        "entry_reachable": True,
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limits": {"max_pages": max_pages, "max_depth": max_depth,
                   "budget_seconds": budget_seconds},
        "robots": robots_info,
        "ua_probe": ua_probe,
        "sitemap": sitemap_info,
        "wellknown": wellknown,
        "pages": pages,
        "link_graph": link_graph,
        "stats": {
            "pages_fetched": len(pages),
            "pages_failed": len(failed),
            "failures": failed[:25],
            "robots_skipped": robots_skipped[:25],
            "elapsed_seconds": round(time.time() - started, 1),
            "budget_exhausted": (time.time() - started) > budget_seconds,
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Collect a bounded evidence bundle for a site.")
    ap.add_argument("url")
    ap.add_argument("--out", default="evidence.json")
    ap.add_argument("--max-pages", type=int, default=15)
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--budget-seconds", type=int, default=150)
    args = ap.parse_args()

    bundle = collect(args.url, args.max_pages, args.max_depth, args.budget_seconds)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=1)
    print(args.out)


if __name__ == "__main__":
    main()
