# AI Discoverability & Engagement Audit — sqlite.org

_Audited 2026-09-23T16:25:57Z · 15 pages sampled in 29.7s_

**21 findings** — 1 critical · 6 high · 6 medium · 8 low

## Readiness at a glance

| Pillar | Score |
|---|---|
| Reachable | `█████░░░░░` 58/100 |
| Readable | `█████░░░░░` 50/100 |
| Quotable | `███████░░░` 76/100 |
| Answerable | `███████░░░` 76/100 |
| Current & corroborated | `████████░░` 88/100 |
| Engaging | `███████░░░` 75/100 |

_Scores are this audit's own 0-100 framework (100 = no findings in that pillar), intended to show relative weakness at a glance. They are not a validated or externally comparable metric._

## Remediation roadmap

_Bucketed by impact against implementation cost, so a cheap fix is not queued behind an expensive one. Severity order is preserved within each bucket._

### Do now

- **F-001 · AI crawler user-agents are blocked at the network layer** (critical, quick effort) — Check the CDN/WAF bot-management settings and allow the AI search crawlers you want citing you.
- **F-002 · Facts appear to be locked in non-text elements** (high, project effort) — Add a plain-text equivalent alongside each of these elements: real HTML text for prices and specs shown as images, an HTML summary beside PDF-only documents, and descriptive alt text on fact-bearing graphics.
- **F-003 · Pages carry visibly stale dates** (high, moderate effort) — Review and update these pages, then set an accurate visible 'last updated' date and a matching dateModified.
- **F-004 · 2 of 6 core questions about this brand cannot be answered from its own extractable content** (high, project effort) — Publish each missing fact as plain, visible text on a relevant page: What is SQLite Home Page?, What services does SQLite Home Page provide?
- **F-005 · Some missing answers may exist on the page but in a non-extractable form** (high, project effort) — Add a plain-text equivalent beside each non-textual element carrying a fact (prices in images, spec tables as graphics, PDF-only documents).
- **F-006 · Visibly stale dates on the site** (high, moderate effort) — Review these pages, update what has changed, and set an accurate current date. Auto-generate the footer copyright year.
- **F-007 · Homepage states no value proposition in extractable text** (high, moderate effort) — State in one sentence, near the top of the homepage, what the organisation does and who it is for.
- **F-009 · No usable XML sitemap found** (medium, quick effort) — Publish an XML sitemap covering all public pages and reference it from robots.txt with a Sitemap: line.
- **F-012 · Homepage has no H1** (medium, quick effort) — Add exactly one H1 stating plainly what the organisation does.
- **F-015 · No language declared on the html element** (low, quick effort) — Add a lang attribute, e.g. <html lang="en">.
- **F-016 · No llms.txt (optional, unproven -- informational only)** (low, quick effort) — Optional. Prioritise sitemap.xml, crawler access and visible on-page facts first -- all three are far better evidenced. Add llms.txt only if it is cheap and you accept it may do nothing.
- **F-020 · No link to a privacy policy or terms page** (low, quick effort) — Publish and link privacy policy from the site footer.
- **F-021 · Form fields without accessible labels** (low, quick effort) — Give every input a visible <label> (placeholders alone are not labels).

### Do next

- **F-010 · No structured data of any kind on the sampled pages** (medium, moderate effort) — Add an Organization (or LocalBusiness) JSON-LD block on the homepage with name, url, logo, a stable @id and sameAs links.
- **F-011 · Content sections run long enough to bury facts mid-passage** (medium, moderate effort) — Break long sections into 150-300 word chunks under their own descriptive subheadings, and move each section's key fact to its opening sentence.
- **F-013 · Most substantive pages offer no clear next action** (medium, moderate effort) — Give each substantive page one obvious next action appropriate to its intent.

### Later / ongoing

- **F-008 · Substantive pages contain no quotable evidence** (medium, project effort) — Add specific, verifiable figures and attributed statements to the body copy of these pages -- concrete numbers with units and dates, named sources for claims.
- **F-014 · Most pages have no meta description** (low, moderate effort) — Write a specific description (roughly 120-160 characters) for each substantive page.
- **F-017 · Long pages have almost no heading structure** (low, moderate effort) — Add a descriptive heading hierarchy (H2/H3) that names the questions each section answers.
- **F-018 · Pages open without a summary paragraph** (low, moderate effort) — Open each substantive page with a 40-120 word summary that directly answers the question the page exists to answer.
- **F-019 · No breadcrumbs on a site with nested content** (low, moderate effort) — Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.

## All findings

### F-001 · AI crawler user-agents are blocked at the network layer

- **Code:** `NETWORK_LAYER_BLOCK`  ·  **Severity:** critical  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** The same URL returned a normal response to a browser user-agent but an explicit refusal to declared AI crawlers -- GPTBot: HTTP 403; ClaudeBot: HTTP 403. robots.txt does not disallow these agents, so the block is happening above it.
- **Why it matters:** CDN and WAF bot management (Cloudflare's AI-bot blocking, AWS WAF, Akamai) filters by user-agent and IP before robots.txt is ever consulted, and overrides it. A site can publish a perfectly permissive robots.txt and still be completely invisible to assistants. This failure is undetectable from robots.txt alone.
- **Do this (critical, quick effort):** Check the CDN/WAF bot-management settings and allow the AI search crawlers you want citing you.
  - _How:_ In Cloudflare this is the 'Block AI Bots' / bot-management rule set, not robots.txt. Note that some plans block AI crawlers by default.

### F-002 · Facts appear to be locked in non-text elements

- **Code:** `FACTS_IN_NON_TEXT`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Detected: fact_bearing_image_without_alt on 1 page(s) (e.g. https://sqlite.org/news.html).
- **Affected URLs:** https://sqlite.org/news.html
- **Why it matters:** A fact carried only by an image, a PDF, a canvas, a third-party embed or an unrendered template is invisible to text extraction. The information already exists -- it just cannot be read -- which makes this among the cheapest gaps to close.
- **Do this (high, project effort):** Add a plain-text equivalent alongside each of these elements: real HTML text for prices and specs shown as images, an HTML summary beside PDF-only documents, and descriptive alt text on fact-bearing graphics.

### F-003 · Pages carry visibly stale dates

- **Code:** `STALE_DATES`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 1 sampled page(s) show a most-recent date 3+ years old. Examples: https://sqlite.org/threadsafe.html -> 2023.
- **Affected URLs:** https://sqlite.org/threadsafe.html
- **Why it matters:** Recency is a unanimous citation gatekeeper (recent vs old measured OR above 10,000). Critically, an OLD date scored WORSE than showing no date at all -- but a RECENT date beats both. So the fix is to genuinely refresh and re-date, never to delete dates.
- **Do this (high, moderate effort):** Review and update these pages, then set an accurate visible 'last updated' date and a matching dateModified.
  - _How:_ Do NOT strip dates to look evergreen -- undated measured worse than recently-dated.

### F-004 · 2 of 6 core questions about this brand cannot be answered from its own extractable content

- **Code:** `UNANSWERABLE_QUESTIONS`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Entity type inferred as 'generic_org' (no strong type signal; treated as a generic organisation). Sampled 15 page(s). Unanswerable: What is SQLite Home Page? -> homepage has no meta description, no H1 and no Organization schema; What services does SQLite Home Page provide? -> no services information found in extractable text.
- **Why it matters:** An assistant answering a question about a brand builds the answer from what it can reach, read and quote at that moment. Where the answer is not present as extractable text, the assistant either omits the brand entirely or fills the gap from a third-party source it does not control -- which is how brands get described inaccurately. Each gap below is a specific question your site currently cannot answer.
- **Do this (high, project effort):** Publish each missing fact as plain, visible text on a relevant page: What is SQLite Home Page?, What services does SQLite Home Page provide?
  - _How:_ Put the answer in body text, not only in an image, a PDF, a form, or a JS-rendered widget. Stating it once, plainly, is enough.

### F-005 · Some missing answers may exist on the page but in a non-extractable form

- **Code:** `ANSWERS_NOT_EXTRACTABLE`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Detected extractability risks across sampled pages: css_generated_text, fact_bearing_image_without_alt. These co-occur with 2 unanswerable question(s).
- **Why it matters:** A fact rendered inside an image, canvas, PDF, third-party embed or client-side template is visible to a human but absent for a text extractor. This is the most recoverable class of gap -- the content already exists and only needs a text equivalent.
- **Do this (high, project effort):** Add a plain-text equivalent beside each non-textual element carrying a fact (prices in images, spec tables as graphics, PDF-only documents).
  - _How:_ A short HTML table or paragraph next to the visual is sufficient; the visual can stay.

### F-006 · Visibly stale dates on the site

- **Code:** `STALE_DATES`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 2 page(s) show a most-recent year at least 2 years old (checked against 2026-09-23): https://sqlite.org/faq.html -> 2024; https://sqlite.org/threadsafe.html -> 2023.
- **Affected URLs:** https://sqlite.org/faq.html, https://sqlite.org/threadsafe.html
- **Why it matters:** Recency measured as a citation gatekeeper -- recent content beat old content by odds ratios above 10,000 across models. A visibly stale year also tells a human visitor the site may no longer be maintained.
- **Do this (high, moderate effort):** Review these pages, update what has changed, and set an accurate current date. Auto-generate the footer copyright year.
  - _How:_ Do not simply bump the date without reviewing content -- and do not delete dates to look evergreen, since undated content measured worse than recently-dated.

### F-007 · Homepage states no value proposition in extractable text

- **Code:** `NO_VALUE_PROP`  ·  **Severity:** high  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** https://sqlite.org/ has neither an H1 nor a meta description, and exposes 235 words of extracted text.
- **Affected URLs:** https://sqlite.org/
- **Why it matters:** A first-time visitor has nothing telling them what this is or whether they are in the right place, and neither does any machine reading the page.
- **Do this (high, moderate effort):** State in one sentence, near the top of the homepage, what the organisation does and who it is for.

### F-008 · Substantive pages contain no quotable evidence

- **Code:** `NO_QUOTABLE_EVIDENCE`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 3/15 pages over 250 words contain zero statistics, zero attributed quotes and zero outbound links to any external domain. Examples: https://sqlite.org/threadsafe.html, https://sqlite.org/c3ref/funclist.html, https://sqlite.org/cintro.html.
- **Affected URLs:** https://sqlite.org/threadsafe.html, https://sqlite.org/c3ref/funclist.html, https://sqlite.org/cintro.html
- **Why it matters:** Adding statistics measured the largest single content lift in the original GEO study (+30.6% visibility; up to +37% subjective impression on a live engine), and quotations the largest overall (+41%). Claims backed by evidence beat unbacked claims by odds ratios from 2.1 up to >10,000. Answer engines quote body text -- give them something concrete and attributable to lift.
- **Do this (high, project effort):** Add specific, verifiable figures and attributed statements to the body copy of these pages -- concrete numbers with units and dates, named sources for claims.
  - _How:_ One real statistic per ~100 words of substantive copy is a reasonable target; attribute each to a named, linkable source.

### F-009 · No usable XML sitemap found

- **Code:** `NO_SITEMAP`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** No sitemap was retrievable from robots.txt declarations or /sitemap.xml.
- **Why it matters:** A sitemap is the most reliable way for a crawler to discover pages that have few inbound internal links. It is far better evidenced than newer conventions such as llms.txt, which measurably almost nothing reads.
- **Do this (medium, quick effort):** Publish an XML sitemap covering all public pages and reference it from robots.txt with a Sitemap: line.

### F-010 · No structured data of any kind on the sampled pages

- **Code:** `NO_STRUCTURED_DATA`  ·  **Severity:** medium  ·  **Confidence:** 70%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** All 15 sampled pages resolve to NO_STRUCTURED_DATA -- no JSON-LD, microdata, RDFa, microformats, Open Graph or Dublin Core markup was found.
- **Why it matters:** Structured data is a legitimate aid for search rich results and, more importantly here, for stating entity identity unambiguously. Note the honest scope: controlled studies do NOT show schema markup causing more AI citations -- so this is worth doing for identity and search, not as a route to being quoted. What gets a page quoted is concrete facts in visible body text.
- **Do this (medium, moderate effort):** Add an Organization (or LocalBusiness) JSON-LD block on the homepage with name, url, logo, a stable @id and sameAs links.
  - _How:_ Keep the markup's claims identical to the visible page text -- asserting facts in markup that the page does not show is its own failure mode.

### F-011 · Content sections run long enough to bury facts mid-passage

- **Code:** `LONG_SECTIONS`  ·  **Severity:** medium  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 2 page(s) have 2+ sections over 300 words (e.g. https://sqlite.org/oldnews.html: 6 long sections, 14 in the 150-300 band).
- **Affected URLs:** https://sqlite.org/oldnews.html, https://sqlite.org/oldnews.html:
- **Why it matters:** Information in the middle of a long passage is retrieved markedly worse than information at its start or end -- and in controlled testing, a fact in the middle position scored BELOW the baseline of not supplying the document at all. The trough deepens as the passage grows. Fix the tier-1 gatekeeper findings first -- structural work measured negligible benefit on pages that still fail a gatekeeper.
- **Do this (medium, moderate effort):** Break long sections into 150-300 word chunks under their own descriptive subheadings, and move each section's key fact to its opening sentence.

### F-012 · Homepage has no H1

- **Code:** `NO_H1`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** No H1 element found on https://sqlite.org/.
- **Affected URLs:** https://sqlite.org/
- **Why it matters:** The H1 is the clearest single statement of what a page is -- for a scanning visitor, for assistive technology, and for any system building a page outline.
- **Do this (medium, quick effort):** Add exactly one H1 stating plainly what the organisation does.

### F-013 · Most substantive pages offer no clear next action

- **Code:** `NO_CTA`  ·  **Severity:** medium  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** 14/15 sampled pages with over 150 words contain no call-to-action phrasing.
- **Why it matters:** A page that informs but does not offer a next step leaves the visitor to invent one, which most will not do. This is where discoverability gains leak away.
- **Do this (medium, moderate effort):** Give each substantive page one obvious next action appropriate to its intent.

### F-014 · Most pages have no meta description

- **Code:** `NO_META_DESCRIPTION`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 15/15 sampled pages expose no meta description.
- **Why it matters:** The description is a structural field used in retrieval and as an explicit one-line statement of page purpose.
- **Do this (low, moderate effort):** Write a specific description (roughly 120-160 characters) for each substantive page.

### F-015 · No language declared on the html element

- **Code:** `NO_HTML_LANG`  ·  **Severity:** low  ·  **Confidence:** 70%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** <html> has no lang attribute on https://sqlite.org/.
- **Affected URLs:** https://sqlite.org/
- **Why it matters:** Missing language metadata weakens locale and entity matching, and degrades screen reader pronunciation.
- **Do this (low, quick effort):** Add a lang attribute, e.g. <html lang="en">.

### F-016 · No llms.txt (optional, unproven -- informational only)

- **Code:** `NO_LLMS_TXT`  ·  **Severity:** low  ·  **Confidence:** 45%  ·  **Category:** discoverability  ·  **Evidence strength:** speculative
- **What we found:** GET /llms.txt returned no usable file.
- **Why it matters:** llms.txt is an emerging convention with, as of 2026, no demonstrated citation benefit: a 137,000-domain study found 97% of published files received zero requests, a ~300,000-domain study found no significant correlation with AI citations, and Google has said it does not support it. Listed for completeness only.
- **Do this (low, quick effort):** Optional. Prioritise sitemap.xml, crawler access and visible on-page facts first -- all three are far better evidenced. Add llms.txt only if it is cheap and you accept it may do nothing.

### F-017 · Long pages have almost no heading structure

- **Code:** `WEAK_HEADINGS`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 3 page(s) exceed 400 words with heading depth below 2. Examples: https://sqlite.org/threadsafe.html, https://sqlite.org/chronology.html, https://sqlite.org/cintro.html.
- **Affected URLs:** https://sqlite.org/threadsafe.html, https://sqlite.org/chronology.html, https://sqlite.org/cintro.html
- **Why it matters:** Structural fields (title, headings, meta description) measured a ~+22% retrieval hit-rate improvement -- they help a document get FOUND. They do not make it quoted; body-text evidence does that. Fix the tier-1 gatekeeper findings first -- structural work measured negligible benefit on pages that still fail a gatekeeper.
- **Do this (low, moderate effort):** Add a descriptive heading hierarchy (H2/H3) that names the questions each section answers.

### F-018 · Pages open without a summary paragraph

- **Code:** `NO_INTRO_SUMMARY`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 8 page(s) over 300 words have under 25 words between the H1 and the first subheading. Examples: https://sqlite.org/about.html, https://sqlite.org/docs.html, https://sqlite.org/books.html.
- **Affected URLs:** https://sqlite.org/about.html, https://sqlite.org/docs.html, https://sqlite.org/books.html
- **Why it matters:** Retrieval favours content that answers early, and the opening position is the strongest slot in a passage. Some engine architectures weight the opening especially heavily when judging a batch of retrieved documents. Fix the tier-1 gatekeeper findings first -- structural work measured negligible benefit on pages that still fail a gatekeeper.
- **Do this (low, moderate effort):** Open each substantive page with a 40-120 word summary that directly answers the question the page exists to answer.

### F-019 · No breadcrumbs on a site with nested content

- **Code:** `NO_BREADCRUMBS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** 4 sampled page(s) sit two or more clicks deep and no breadcrumb navigation (BreadcrumbList markup or a breadcrumb nav landmark) was found.
- **Why it matters:** Someone arriving on a deep page from a search result or an assistant's citation has no way to tell where they are in the site or how to go up a level. Breadcrumbs also state the site's hierarchy explicitly for machines.
- **Do this (low, moderate effort):** Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.

### F-020 · No link to a privacy policy or terms page

- **Code:** `NO_PRIVACY_OR_TERMS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** Across 15 sampled page(s), no link was found to: privacy policy.
- **Why it matters:** These pages are a baseline trust signal for visitors deciding whether to transact, and their absence is conspicuous on any site that collects data. They are also commonly expected by platforms and reviewers.
- **Do this (low, quick effort):** Publish and link privacy policy from the site footer.

### F-021 · Form fields without accessible labels

- **Code:** `UNLABELLED_FORM_FIELDS`  ·  **Severity:** low  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** 16 input field(s) across sampled pages have no label, aria-label, title or placeholder.
- **Why it matters:** Unlabelled fields are ambiguous for every visitor and unusable with a screen reader, and forms are usually the last step before a conversion.
- **Do this (low, quick effort):** Give every input a visible <label> (placeholders alone are not labels).

## Not assessed

Checks that do not apply to this kind of site, or areas that could not be observed (blocked, gated, or unreachable). Listed so the report is honest about its own coverage — these are **not** defects and are not scored:

- **N-001 · Visitor-goal checks not applicable: pricing, offering** (not applicable) — No pricing, offering destination was found, but this site shows no commercial signals (prices, purchase CTAs, Product/Offer structured data, or a pricing/shop URL), so these goals do not apply to it.
