"""Dependency-free HTML fetch + parse helpers shared by this skill's checks.

Stdlib only (urllib, html.parser, re) on purpose: every skill in this
marketplace must run on a bare `python3` install with no pip installs, so it
stays portable across agent hosts and never depends on network access to a
package index.
"""
import gzip
import time
import urllib.error
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

USER_AGENT = (
    "BrandAIReadinessAuditBot/1.0 "
    "(+read-only compliance audit; small same-domain sample; honors robots.txt)"
)
TIMEOUT = 10
MAX_BYTES = 3_000_000
REQUEST_DELAY = 0.5  # politeness delay between requests to the same host

_last_request_time = {}

# Well-known AI/assistant crawler and fetcher user-agent tokens, as of 2026.
# Kept as a flat list (not "the" canonical list -- new bots appear often) so
# checks degrade gracefully: unknown bots just fall back to the "*" rule.
AI_CRAWLERS = [
    "GPTBot", "ChatGPT-User", "OAI-SearchBot",
    "ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai",
    "PerplexityBot", "Perplexity-User",
    "Google-Extended", "Applebot-Extended",
    "CCBot", "Amazonbot", "Meta-ExternalAgent", "Bytespider", "Diffbot",
]


def _throttle(host):
    last = _last_request_time.get(host, 0)
    wait = REQUEST_DELAY - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _last_request_time[host] = time.time()


def fetch(url, timeout=TIMEOUT, extra_headers=None):
    """GET a URL. Never raises -- returns a dict with an 'error' key instead."""
    host = urlparse(url).netloc
    _throttle(host)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml,*/*"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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
            return {"url": resp.geturl(), "status": resp.status,
                    "headers": dict(resp.headers.items()), "text": text, "error": None}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(MAX_BYTES).decode("utf-8", errors="replace")
        except Exception:
            pass
        return {"url": url, "status": e.code,
                "headers": dict(e.headers.items()) if e.headers else {}, "text": body, "error": str(e)}
    except Exception as e:
        return {"url": url, "status": None, "headers": {}, "text": "", "error": str(e)}


def resolve_base_url(raw):
    """Accept 'example.com' or a full URL; try https then http."""
    candidates = [raw] if "://" in raw else [f"https://{raw}", f"http://{raw}"]
    last = None
    for c in candidates:
        r = fetch(c)
        last = r
        if r["status"] and r["status"] < 400:
            return c, r
    return candidates[0], last


def site_root(url):
    """scheme://netloc with no path -- the correct base for well-known root
    files (robots.txt, sitemap.xml, llms.txt) regardless of what path the
    *audited* URL itself points at (e.g. https://example.com/products/widget
    must still resolve sitemap.xml to https://example.com/sitemap.xml, not
    .../products/widget/sitemap.xml)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def robots_check(base_url):
    """Fetch robots.txt once. Returns (RobotFileParser, raw_text, status)."""
    robots_url = site_root(base_url) + "/robots.txt"
    result = fetch(robots_url)
    rp = urllib.robotparser.RobotFileParser()
    if result["status"] == 200 and result["text"]:
        rp.parse(result["text"].splitlines())
    else:
        rp.parse([])
    return rp, (result["text"] if result["status"] == 200 else ""), result["status"]


def allowed(rp, url, user_agent="*"):
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


class PageParser(HTMLParser):
    """Single-pass, best-effort structural extractor. Not a full HTML5 parser
    -- good enough for the text/metadata/link/schema signals these audits need."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.lang = ""
        self.meta = []
        self.canonical = None
        self.hreflangs = []
        self.ld_json_raw = []
        self.scripts = []
        self.headings = []
        self.images = []
        self.links = []
        self.forms_search = False
        self.viewport = False
        self.robots_meta = ""
        self.noscript_text_len = 0
        self.body_text_parts = []
        self.has_nav = False

        self._in_head = False
        self._in_body = False
        self._skip_stack = []
        self._current_ld = None
        self._current_heading = None
        self._current_noscript = False
        self._current_a = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "head":
            self._in_head = True
        elif tag == "body":
            self._in_body = True
        elif tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "nav":
            self.has_nav = True
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            content = a.get("content", "")
            if name:
                self.meta.append({"name": name, "content": content})
            if name == "viewport":
                self.viewport = True
            if name == "robots":
                self.robots_meta = content
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if rel == "canonical":
                self.canonical = a.get("href")
            if rel == "alternate" and a.get("hreflang"):
                self.hreflangs.append(a.get("hreflang"))
            if rel in ("icon", "shortcut icon"):
                self.meta.append({"name": "_has_favicon", "content": "1"})
        elif tag == "script":
            stype = (a.get("type") or "").lower()
            if stype == "application/ld+json":
                self._current_ld = []
            self.scripts.append({"src": a.get("src"), "head": self._in_head,
                                  "async_defer": ("async" in a) or ("defer" in a), "type": stype})
            self._skip_stack.append("script")
        elif tag == "style":
            self._skip_stack.append("style")
        elif tag == "noscript":
            self._current_noscript = True
            self._skip_stack.append("noscript")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._current_heading = [int(tag[1]), ""]
        elif tag == "img":
            self.images.append({"src": a.get("src", ""), "alt": a.get("alt")})
        elif tag == "a":
            self._current_a = {"href": a.get("href", ""), "text": ""}
        elif tag == "input":
            itype = (a.get("type") or "").lower()
            role = (a.get("role") or "").lower()
            nm = (a.get("name") or "").lower()
            if itype == "search" or role == "search" or "search" in nm:
                self.forms_search = True

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
        if tag == "title":
            self._in_title = False
        if tag in ("script", "style", "noscript") and self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
        if tag == "script" and self._current_ld is not None:
            self.ld_json_raw.append("".join(self._current_ld))
            self._current_ld = None
        if tag == "noscript":
            self._current_noscript = False
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._current_heading:
            self.headings.append(tuple(self._current_heading))
            self._current_heading = None
        if tag == "a" and self._current_a is not None:
            self.links.append((self._current_a["href"], self._current_a["text"].strip()))
            self._current_a = None

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in ("script", "style", "noscript") and self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._current_ld is not None:
            self._current_ld.append(data)
            return
        if self._skip_stack:
            if self._current_noscript:
                self.noscript_text_len += len(data.strip())
            return
        if self._current_heading is not None:
            self._current_heading[1] += data
        if self._current_a is not None:
            self._current_a["text"] += data
        if self._in_body:
            stripped = data.strip()
            if stripped:
                self.body_text_parts.append(stripped)

    @property
    def body_text(self):
        return " ".join(self.body_text_parts)

    @property
    def has_favicon(self):
        return any(m["name"] == "_has_favicon" for m in self.meta)


def parse(html):
    p = PageParser()
    try:
        p.feed(html)
    except Exception:
        pass
    return p


# Paths that are either authenticated-area-adjacent (no value auditing them
# read-only, and staying well clear of anything account/session-specific)
# or simply never a content page worth sampling -- both waste crawl budget
# without teaching the audit anything.
_SKIP_PATH_WORDS = ("login", "signin", "sign-in", "signup", "sign-up", "logout",
                     "cart", "checkout", "account", "wp-admin", "admin")
_SKIP_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
                     ".zip", ".css", ".js", ".mp4", ".mp3", ".woff", ".woff2", ".xml")


def same_domain_links(base_url, links, limit=6):
    """Pick a small, useful sample of same-domain internal links to sample,
    biased toward pages likely to be representative (about/product/contact/blog)."""
    domain = urlparse(base_url).netloc
    seen = set()
    priority_words = ["about", "product", "pricing", "contact", "blog", "news", "shop"]
    scored = []
    for href, text in links:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(base_url, href).split("#")[0]
        parsed = urlparse(full)
        if parsed.netloc != domain or full == base_url or full in seen:
            continue
        low_full = full.lower()
        if low_full.endswith(_SKIP_EXTENSIONS):
            continue
        if any(w in low_full for w in _SKIP_PATH_WORDS):
            continue
        seen.add(full)
        score = 0
        low = (href + " " + text).lower()
        for i, w in enumerate(priority_words):
            if w in low:
                score = len(priority_words) - i
                break
        scored.append((score, full))
    scored.sort(key=lambda t: -t[0])
    return [u for _, u in scored[:limit]]
