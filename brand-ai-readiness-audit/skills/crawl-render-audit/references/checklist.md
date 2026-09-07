# Crawl & Render — checks and thresholds

## Access

| Check | Severity | Threshold |
|---|---|---|
| `Disallow: /` for `*` | critical | robots.txt blocks the root for all agents |
| Search-index crawler disallowed | critical | any of OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot, Bingbot, Applebot, DuckAssistBot |
| Training crawler disallowed | **low, informational** | GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot — no citation impact |
| Live user-fetch agent disallowed | low | ChatGPT-User, Claude-User, Perplexity-User — advisory only |
| Content Signals directives present | low/medium | `search=no` raises it to medium |
| Network-layer block detected | critical | browser UA succeeds, AI UA gets 401/403/429/503 or a body under 35% the size |
| `noindex` (meta or `X-Robots-Tag`) | critical on homepage, else high | any sampled page |
| No usable sitemap | medium | no `<loc>` entries from robots.txt declarations or `/sitemap.xml` |
| Broken internal links | medium | any 4xx/5xx in the sampled crawl |

### The crawler taxonomy, which is the whole point

`citation_impact` is what decides severity, not the mere presence of a
`Disallow`:

- **`removes`** — search-index agents. Blocking genuinely costs visibility.
- **`none`** — training and opt-out tokens. Google states blocking
  Google-Extended does not affect Google Search inclusion; OpenAI states
  disallowing GPTBot only opts out of training. Refusing training while
  allowing search is the documented way to keep citations without contributing
  training data. **Never report this as a defect.**
- **`intent`** — user-triggered fetchers. Operators say robots.txt may not
  apply, so a `Disallow` is a statement of intent, not an effective block.

## Readability

| Check | Severity | Threshold |
|---|---|---|
| JavaScript render gap | critical if ≥ half the sample, else high | under 120 words extractable **and** (SPA root element **or** ≥6 script tags) |
| Facts locked in non-text | high | fact-bearing image without alt, PDF-only doc, canvas, third-party embed, unrendered template binding, or a fact only in a `data-` attribute |
| Content only in a state blob | medium | render gap co-occurring with `__NEXT_DATA__` / `__NUXT__` / `__INITIAL_STATE__` |

### Render-gap heuristic limits

It never executes JavaScript, by design — the collector is standard-library
only so it runs anywhere. So:

- **False positives**: a deliberately minimal, image-led landing page.
- **False negatives**: partial server-side rendering where the hero renders but
  the substance loads client-side afterwards.

Confirm either way with `curl -A GPTBot <url> | head -c 2000`. If the facts are
not in that output, no non-rendering crawler can see them.

## Extractability failure modes detected

Fact-bearing images without alt text; image-heavy pages with sparse text; text
inside SVG; canvas-rendered content; CSS-generated text; unrendered template
bindings and surviving mustaches; facts only in `data-` attributes; PDF-only
documents; third-party embeds (Datawrapper, Flourish, Tableau, Google Docs,
Airtable, Typeform); custom elements suggesting shadow DOM; media without
captions; obfuscated contact details; content behind "load more"; and prose
referencing a table that does not exist in markup.

Each is reported as a **signal**, never a certainty.

## Crawl budget and politeness

Homepage plus a prioritized same-domain sample, default 15 pages, depth 2, with
a 150-second wall-clock budget and roughly 0.4s between requests to the same
host. Every URL beyond the entry page is checked against robots.txt first.
Login, signup, cart, checkout, account and admin paths are skipped outright, as
are non-HTML assets. GET only — never a form submission, never authentication.
