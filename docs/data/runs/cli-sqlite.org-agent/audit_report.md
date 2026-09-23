# AI Discoverability & Engagement Audit — sqlite.org

_Audited 2026-09-22T20:20:16Z · 15 pages sampled in 37.5s_

**12 findings** — 0 critical · 0 high · 2 medium · 10 low

## Readiness at a glance

| Pillar | Score |
|---|---|
| Reachable | `█████████░` 93/100 |
| Readable | `████████░░` 89/100 |
| Quotable | `█████████░` 99/100 |
| Answerable | `██████████` 100/100 |
| Current & corroborated | `█████████░` 99/100 |
| Engaging | `█████████░` 93/100 |

_Scores are this audit's own 0-100 framework (100 = no findings in that pillar), intended to show relative weakness at a glance. They are not a validated or externally comparable metric._

## Remediation roadmap

_Bucketed by impact against implementation cost, so a cheap fix is not queued behind an expensive one. Severity order is preserved within each bucket._

### Do now

- **F-001 · No usable XML sitemap found** (medium, quick effort) — Publish an XML sitemap covering all public pages and reference it from robots.txt with a Sitemap: line.
- **F-002 · Homepage has no H1** (medium, quick effort) — Make the existing description line the homepage H1, e.g. "SQLite is a C-language library that implements a small, fast, self-contained, high-reliability, full-featured SQL database engine."
- **F-003 · Training crawlers are blocked at the network layer; search and live-fetch agents are not** (low, quick effort) — No fix needed if the training-crawler block is intentional. Optionally state the policy in robots.txt so the intent is explicit and does not look like a misconfiguration to the next maintainer.
- **F-008 · No language declared on the html element** (low, quick effort) — Add a lang attribute, e.g. <html lang="en">.
- **F-009 · No llms.txt (optional, unproven -- informational only)** (low, quick effort) — Optional. Prioritise sitemap.xml, crawler access and visible on-page facts first -- all three are far better evidenced. Add llms.txt only if it is cheap and you accept it may do nothing.
- **F-012 · Form fields without accessible labels** (low, quick effort) — Give the search box an aria-label="Search sqlite.org" (or a visible label) and set a placeholder.

### Later / ongoing

- **F-004 · Images with no alt text on 3 sampled pages** (low, moderate effort) — Add short descriptive alt text to the benchmark chart on news.html and to the book-cover images on books.html (title and author); mark purely decorative images alt="".
- **F-005 · Visibly stale dates on the site** (low, moderate effort) — Review faq.html and threadsafe.html for anything that has changed since the stated dates; if something has, update it and let the date advance. If nothing has changed, no action is needed.
- **F-006 · No structured data of any kind on the sampled pages** (low, moderate effort) — Optionally add JSON-LD to the homepage (Organization or SoftwareApplication with name, url, a stable @id and sameAs links to the Wikipedia and Wikidata entries).
- **F-007 · Most pages have no meta description** (low, moderate effort) — Write a specific description (roughly 120-160 characters) for each substantive page.
- **F-010 · Long documentation pages have almost no heading structure or opening summary** (low, moderate effort) — On the few substantive explainer pages (about, cintro, threadsafe), add H2/H3 headings that name the question each section answers and open with a one- or two-sentence summary.
- **F-011 · No breadcrumbs on a site with nested content** (low, moderate effort) — Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.

## All findings

### F-001 · No usable XML sitemap found

- **Code:** `NO_SITEMAP`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** No sitemap was retrievable from robots.txt declarations or /sitemap.xml.
- **Why it matters:** A sitemap is the most reliable way for a crawler to discover pages that have few inbound internal links. It is far better evidenced than newer conventions such as llms.txt, which measurably almost nothing reads.
- **Do this (medium, quick effort):** Publish an XML sitemap covering all public pages and reference it from robots.txt with a Sitemap: line.

### F-002 · Homepage has no H1

- **Code:** `NO_H1`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** No H1 element on https://www.sqlite.org/ (its only headings are four H3s: "Common Links", "Latest Release", "Common Links", "Sponsors"). The page does carry a visible tagline in a div ("Small. Fast. Reliable. Choose any three.") and a one-sentence description in body text, but neither is marked up as the page heading, and the <title> is the generic "SQLite Home Page".
- **Affected URLs:** https://www.sqlite.org/
- **Why it matters:** The H1 is the clearest single statement of what a page is -- for a scanning visitor, for assistive technology, and for any system building a page outline.
- **Do this (medium, quick effort):** Make the existing description line the homepage H1, e.g. "SQLite is a C-language library that implements a small, fast, self-contained, high-reliability, full-featured SQL database engine."

### F-003 · Training crawlers are blocked at the network layer; search and live-fetch agents are not

- **Code:** `TRAINING_CRAWLERS_BLOCKED_OK`  ·  **Severity:** low  ·  **Confidence:** 80%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** GET https://www.sqlite.org/index.html returns HTTP 403 to the GPTBot and ClaudeBot user-agents and HTTP 200 to a browser UA, OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot, ChatGPT-User, Claude-User and Perplexity-User (collector probe plus a manual re-probe on 2026-09-22). robots.txt (100 bytes) disallows only /cvstrac, /src, /docsrc, /cgi and /contrib and says nothing about either blocked agent, so the 403 is applied above robots.txt.
- **Affected URLs:** https://www.sqlite.org/index.html
- **Why it matters:** GPTBot and ClaudeBot are training crawlers. Refusing them while serving the search-index and live-fetch agents is a documented, legitimate choice and does not remove the site from AI answers. The only residual point is that the policy is enforced silently rather than declared.
- **Do this (low, quick effort):** No fix needed if the training-crawler block is intentional. Optionally state the policy in robots.txt so the intent is explicit and does not look like a misconfiguration to the next maintainer.
  - _How:_ Do NOT unblock OAI-SearchBot, Claude-SearchBot, PerplexityBot or the *-User agents; they currently get 200. Re-probe them after any CDN/WAF rule change.
  - _Severity adjusted from critical by the evidence critic._

### F-004 · Images with no alt text on 3 sampled pages

- **Code:** `MISSING_ALT_TEXT`  ·  **Severity:** low  ·  **Confidence:** 80%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** From the evidence bundle: https://www.sqlite.org/books.html has 13 of 14 images with no alt attribute, https://www.sqlite.org/news.html has 1 of 2 (images/sschart20221116.jpg, a CPU-cycle benchmark chart), and https://www.sqlite.org/copyright.html has 1 of 2. The chart on news.html is introduced by body text that states the result, so no fact is stranded in the image. The other 12 sampled pages have no missing alt text.
- **Affected URLs:** https://www.sqlite.org/books.html, https://www.sqlite.org/news.html, https://www.sqlite.org/copyright.html
- **Why it matters:** Images without alt text are invisible to text extractors and to screen readers. Here the impact is small: the one fact-bearing chart is explained in adjacent text, and the rest are book covers.
- **Do this (low, moderate effort):** Add short descriptive alt text to the benchmark chart on news.html and to the book-cover images on books.html (title and author); mark purely decorative images alt="".
  - _How:_ Alt-text coverage is a prompt for review, not a verdict: decorative images legitimately use empty alt.
  - _Severity adjusted from high by the evidence critic._

### F-005 · Visibly stale dates on the site

- **Code:** `STALE_DATES`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Checked against 2026-09-22: https://www.sqlite.org/faq.html footer reads "last updated on 2024-11-26" and https://www.sqlite.org/threadsafe.html reads "last updated on 2023-12-05". That is 2 of 15 sampled pages, both stable technical reference pages. The homepage ("last updated on 2026-08-14") and news.html (newest entry 2026-07-24, release 3.53.4) are current.
- **Affected URLs:** https://www.sqlite.org/faq.html, https://www.sqlite.org/threadsafe.html
- **Why it matters:** Recency is a citation gatekeeper for time-sensitive content, and an old visible date scores worse than a recent one. On reference documentation that has not needed to change, an older "last updated" date is expected; the exposure is limited to pages whose content has actually drifted.
- **Do this (low, moderate effort):** Review faq.html and threadsafe.html for anything that has changed since the stated dates; if something has, update it and let the date advance. If nothing has changed, no action is needed.
  - _How:_ Do not bump dates without reviewing content, and do not remove dates to look evergreen: undated content measured worse than recently-dated content.
  - _Severity adjusted from high by the evidence critic._

### F-006 · No structured data of any kind on the sampled pages

- **Code:** `NO_STRUCTURED_DATA`  ·  **Severity:** low  ·  **Confidence:** 60%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** All 15 sampled pages resolve to NO_STRUCTURED_DATA -- no JSON-LD, microdata, RDFa, microformats, Open Graph or Dublin Core markup was found.
- **Why it matters:** Structured data is a legitimate aid for search rich results and, more importantly here, for stating entity identity unambiguously. Note the honest scope: controlled studies do NOT show schema markup causing more AI citations -- so this is worth doing for identity and search, not as a route to being quoted. What gets a page quoted is concrete facts in visible body text. Entity confusion is not a live risk here: brief searches for "SQLite" returned results about this database engine (Wikipedia, dbdb.io, The New Stack), not an unrelated organisation.
- **Do this (low, moderate effort):** Optionally add JSON-LD to the homepage (Organization or SoftwareApplication with name, url, a stable @id and sameAs links to the Wikipedia and Wikidata entries).
  - _How:_ Keep every claim in the markup identical to the visible page text.
  - _Severity adjusted from medium by the evidence critic._

### F-007 · Most pages have no meta description

- **Code:** `NO_META_DESCRIPTION`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 15/15 sampled pages expose no meta description.
- **Why it matters:** The description is a structural field used in retrieval and as an explicit one-line statement of page purpose.
- **Do this (low, moderate effort):** Write a specific description (roughly 120-160 characters) for each substantive page.

### F-008 · No language declared on the html element

- **Code:** `NO_HTML_LANG`  ·  **Severity:** low  ·  **Confidence:** 70%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** <html> has no lang attribute on https://www.sqlite.org/.
- **Affected URLs:** https://www.sqlite.org/
- **Why it matters:** Missing language metadata weakens locale and entity matching, and degrades screen reader pronunciation.
- **Do this (low, quick effort):** Add a lang attribute, e.g. <html lang="en">.

### F-009 · No llms.txt (optional, unproven -- informational only)

- **Code:** `NO_LLMS_TXT`  ·  **Severity:** low  ·  **Confidence:** 45%  ·  **Category:** discoverability  ·  **Evidence strength:** speculative
- **What we found:** GET /llms.txt returned no usable file.
- **Why it matters:** llms.txt is an emerging convention with, as of 2026, no demonstrated citation benefit: a 137,000-domain study found 97% of published files received zero requests, a ~300,000-domain study found no significant correlation with AI citations, and Google has said it does not support it. Listed for completeness only.
- **Do this (low, quick effort):** Optional. Prioritise sitemap.xml, crawler access and visible on-page facts first -- all three are far better evidenced. Add llms.txt only if it is cheap and you accept it may do nothing.

### F-010 · Long documentation pages have almost no heading structure or opening summary

- **Code:** `WEAK_HEADINGS`  ·  **Severity:** low  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 3 pages over 400 words have heading depth below 2 (https://www.sqlite.org/threadsafe.html, https://www.sqlite.org/chronology.html, https://www.sqlite.org/cintro.html), and 8 pages over 300 words have under 25 words between the H1 and the first subheading (e.g. https://www.sqlite.org/about.html, https://www.sqlite.org/docs.html, https://www.sqlite.org/books.html). Separately, https://www.sqlite.org/oldnews.html is a 13,602-word release-note archive with 6 sections over 300 words.
- **Affected URLs:** https://www.sqlite.org/threadsafe.html, https://www.sqlite.org/chronology.html, https://www.sqlite.org/cintro.html, https://www.sqlite.org/about.html, https://www.sqlite.org/docs.html (+2 more)
- **Why it matters:** Structural fields (title, headings, meta description) measured a ~+22% retrieval hit-rate improvement -- they help a document get FOUND. They do not make it quoted; body-text evidence does that. Fix the tier-1 gatekeeper findings first -- structural work measured negligible benefit on pages that still fail a gatekeeper.
- **Do this (low, moderate effort):** On the few substantive explainer pages (about, cintro, threadsafe), add H2/H3 headings that name the question each section answers and open with a one- or two-sentence summary.
  - _How:_ Leave function lists, changelogs and the oldnews archive as they are; chunking a release-note archive would not help a reader or a retriever.

### F-011 · No breadcrumbs on a site with nested content

- **Code:** `NO_BREADCRUMBS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** 4 sampled page(s) sit two or more clicks deep and no breadcrumb navigation (BreadcrumbList markup or a breadcrumb nav landmark) was found.
- **Why it matters:** Someone arriving on a deep page from a search result or an assistant's citation has no way to tell where they are in the site or how to go up a level. Breadcrumbs also state the site's hierarchy explicitly for machines.
- **Do this (low, moderate effort):** Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.

### F-012 · Form fields without accessible labels

- **Code:** `UNLABELLED_FORM_FIELDS`  ·  **Severity:** low  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** 16 input fields across the 15 sampled pages have no label, aria-label, title or placeholder. On the homepage this is the site search box: <input type="text" name="q" id="searchbox" value=""> followed by <input type="submit" value="Go">. The same one-field search form is on every sampled page; docs.html and copyright.html carry a second form.
- **Why it matters:** Unlabelled fields are ambiguous for every visitor and unusable with a screen reader, and forms are usually the last step before a conversion.
- **Do this (low, quick effort):** Give the search box an aria-label="Search sqlite.org" (or a visible label) and set a placeholder.
  - _How:_ A one-line template change in the shared page header fixes all pages.

## Not assessed

Checks that do not apply to this kind of site, or areas that could not be observed (blocked, gated, or unreachable). Listed so the report is honest about its own coverage — these are **not** defects and are not scored:

- **N-001 · Visitor-goal checks not applicable: pricing, offering** (not applicable) — No pricing, offering destination was found, but this site shows no commercial signals (prices, purchase CTAs, Product/Offer structured data, or a pricing/shop URL), so these goals do not apply to it.

## Suppressed by the evidence critic

Candidate findings that did not survive verification — listed so the audit's reasoning is auditable:

- ~~Pages carry visibly stale dates~~ — Duplicate of "Visibly stale dates on the site" (same threadsafe.html date, found by a different skill); merged and recorded as corroboration.
- ~~Pages open without a summary paragraph~~ — Merged into the heading-structure finding: same skill, same tier-2 structural family, same fix, and the evidence overlaps (about.html, docs.html).
- ~~Content sections run long enough to bury facts mid-passage~~ — Merged into the heading-structure finding. The only strong example is oldnews.html, a 13,602-word changelog archive where re-chunking is not an appropriate fix.
- ~~Homepage states no value proposition in extractable text~~ — Contradicted by the evidence. The homepage text_sample contains "Small. Fast. Reliable. Choose any three." and "SQLite is a C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine. SQLite is the most used database engine in the world." The three orientation questions pass: what it is (stated), who it is for (implicit: developers embedding a C/SQL engine), next action ("Download", "Getting Started", "Try it live!"). The genuine gap, a missing H1 and meta description, is reported separately.
- ~~2 of 6 core questions about this brand cannot be answered from its own extractable content~~ — Heuristic misfire. The entity name was taken from the <title> "SQLite Home Page", and the "services" question was generated for a generic organisation, whereas SQLite is a public-domain library. The "what is it" answer is on the page; its only root cause (no H1 or meta description) is already reported.
- ~~Some missing answers may exist on the page but in a non-extractable form~~ — Heuristic misfire. The evidence is one benchmark JPEG on news.html and three decorative CSS glyphs on chronology.html (\2666, \2191, \2193); neither carries the facts behind the two flagged questions.
- ~~Substantive pages contain no quotable evidence~~ — Heuristic misfire. The two pages are the C API function list (c3ref/funclist.html) and a threading-mode explainer, where adding statistics or attributed quotes would be artificial. 2 of 15 pages, neither the homepage.
- ~~Most substantive pages offer no clear next action~~ — CTA detection is a fixed phrase list and this is a documentation site whose pages are reference material. The homepage does offer "Download", "Getting Started" and "Try it live!".
- ~~No link to a privacy policy or terms page~~ — No evidence that this site collects personal data (no accounts, no password fields; the only forms are site search and a licence purchase form). The finding's own premise, a site that collects data, is not shown.

## Audit notes

- **Date:** the machine clock stamped 2026-09-21T20:20:16Z; the user-stated real date, 2026-09-22, was used for staleness checks and for `audited_at`.
- **Scope:** 15 pages sampled to depth 2; page-level findings are a sample, not a census.
- **Homepage orientation (judged by hand):** what it is: pass; who it is for: implicit; what next: pass. No finding raised.
- **Off-site corroboration:** 2 web searches. Wikipedia, Database of Databases and The New Stack results agree with the site on the core facts (C-language public-domain SQL engine, created by D. Richard Hipp, 2000). No contradiction or name collision seen. A brief sample, not proof.
- **Crawler access:** GPTBot and ClaudeBot get 403; OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot, ChatGPT-User, Claude-User and Perplexity-User get 200. The probes vary the user-agent string only, not the source IP.
