# AI Discoverability & Engagement Audit — www.lua.org

_Audited 2026-09-23T16:30:45Z · 15 pages sampled in 23.2s_

**17 findings** — 0 critical · 3 high · 8 medium · 6 low

## Readiness at a glance

| Pillar | Score |
|---|---|
| Reachable | `████████░░` 83/100 |
| Readable | `████████░░` 80/100 |
| Quotable | `████████░░` 89/100 |
| Answerable | `████████░░` 83/100 |
| Current & corroborated | `█████████░` 95/100 |
| Engaging | `███████░░░` 71/100 |

_Scores are this audit's own 0-100 framework (100 = no findings in that pillar), intended to show relative weakness at a glance. They are not a validated or externally comparable metric._

## Remediation roadmap

_Bucketed by impact against implementation cost, so a cheap fix is not queued behind an expensive one. Severity order is preserved within each bucket._

### Do now

- **F-001 · Facts appear to be locked in non-text elements** (high, project effort) — Add a plain-text equivalent alongside each of these elements: real HTML text for prices and specs shown as images, an HTML summary beside PDF-only documents, and descriptive alt text on fact-bearing graphics.
- **F-002 · Some missing answers may exist on the page but in a non-extractable form** (high, project effort) — Add a plain-text equivalent beside each non-textual element carrying a fact (prices in images, spec tables as graphics, PDF-only documents).
- **F-003 · No mobile viewport declaration** (high, quick effort) — Add <meta name="viewport" content="width=device-width, initial-scale=1"> to every page.
- **F-004 · No usable XML sitemap found** (medium, quick effort) — Publish an XML sitemap covering all public pages and reference it from robots.txt with a Sitemap: line.
- **F-008 · Multiple distinct phone numbers published across the site** (medium, quick effort) — Confirm each phone number is intentional and current. If any is a stale duplicate of another, consolidate to one canonical phone number served from a single template include so it cannot drift again.
- **F-009 · Homepage has no H1** (medium, quick effort) — Add exactly one H1 stating plainly what the organisation does.
- **F-013 · No language declared on the html element** (low, quick effort) — Add a lang attribute, e.g. <html lang="en">.
- **F-014 · No llms.txt (optional, unproven -- informational only)** (low, quick effort) — Optional. Prioritise sitemap.xml, crawler access and visible on-page facts first -- all three are far better evidenced. Add llms.txt only if it is cheap and you accept it may do nothing.
- **F-017 · No link to a privacy policy or terms page** (low, quick effort) — Publish and link privacy policy, terms / legal from the site footer.

### Do next

- **F-005 · Most pages publish no date at all** (medium, moderate effort) — Add an accurate, visible published/updated date to substantive pages, mirrored in dateModified.
- **F-006 · Content sections run long enough to bury facts mid-passage** (medium, moderate effort) — Break long sections into 150-300 word chunks under their own descriptive subheadings, and move each section's key fact to its opening sentence.
- **F-010 · Most substantive pages offer no clear next action** (medium, moderate effort) — Give each substantive page one obvious next action appropriate to its intent.
- **F-011 · Most images have no alt text** (medium, moderate effort) — Add descriptive alt text to images that carry meaning; keep alt="" for purely decorative ones.

### Later / ongoing

- **F-007 · 1 of 7 core questions about this brand cannot be answered from its own extractable content** (medium, project effort) — Publish each missing fact as plain, visible text on a relevant page: What does The Programming Language Lua do / offer?
- **F-012 · Most pages have no meta description** (low, moderate effort) — Write a specific description (roughly 120-160 characters) for each substantive page.
- **F-015 · Pages open without a summary paragraph** (low, moderate effort) — Open each substantive page with a 40-120 word summary that directly answers the question the page exists to answer.
- **F-016 · No breadcrumbs on a site with nested content** (low, moderate effort) — Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.

## All findings

### F-001 · Facts appear to be locked in non-text elements

- **Code:** `FACTS_IN_NON_TEXT`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Detected: fact_bearing_image_without_alt on 1 page(s) (e.g. https://www.lua.org/news.html); facts_locked_in_pdf on 1 page(s) (e.g. https://www.lua.org/wshop11.html).
- **Affected URLs:** https://www.lua.org/news.html, https://www.lua.org/wshop11.html
- **Why it matters:** A fact carried only by an image, a PDF, a canvas, a third-party embed or an unrendered template is invisible to text extraction. The information already exists -- it just cannot be read -- which makes this among the cheapest gaps to close.
- **Do this (high, project effort):** Add a plain-text equivalent alongside each of these elements: real HTML text for prices and specs shown as images, an HTML summary beside PDF-only documents, and descriptive alt text on fact-bearing graphics.

### F-002 · Some missing answers may exist on the page but in a non-extractable form

- **Code:** `ANSWERS_NOT_EXTRACTABLE`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Detected extractability risks across sampled pages: fact_bearing_image_without_alt, facts_locked_in_pdf. These co-occur with 1 unanswerable question(s).
- **Why it matters:** A fact rendered inside an image, canvas, PDF, third-party embed or client-side template is visible to a human but absent for a text extractor. This is the most recoverable class of gap -- the content already exists and only needs a text equivalent.
- **Do this (high, project effort):** Add a plain-text equivalent beside each non-textual element carrying a fact (prices in images, spec tables as graphics, PDF-only documents).
  - _How:_ A short HTML table or paragraph next to the visual is sufficient; the visual can stay.

### F-003 · No mobile viewport declaration

- **Code:** `NO_VIEWPORT`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** 15/15 sampled pages have no viewport meta tag (e.g. https://www.lua.org/).
- **Affected URLs:** https://www.lua.org/
- **Why it matters:** Without it, mobile browsers render the desktop layout scaled down, so text is unreadable without pinch-zoom. On mobile traffic this reliably drives immediate bounces before any content is read.
- **Do this (high, quick effort):** Add <meta name="viewport" content="width=device-width, initial-scale=1"> to every page.

### F-004 · No usable XML sitemap found

- **Code:** `NO_SITEMAP`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** No sitemap was retrievable from robots.txt declarations or /sitemap.xml.
- **Why it matters:** A sitemap is the most reliable way for a crawler to discover pages that have few inbound internal links. It is far better evidenced than newer conventions such as llms.txt, which measurably almost nothing reads.
- **Do this (medium, quick effort):** Publish an XML sitemap covering all public pages and reference it from robots.txt with a Sitemap: line.

### F-005 · Most pages publish no date at all

- **Code:** `UNDATED_CONTENT`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 15/15 sampled pages expose no visible updated/copyright year and no JSON-LD date field.
- **Why it matters:** A recent timestamp measured a clear citation advantage over no timestamp in every model tested. Undated content forces an answer engine to guess at currency, and it guesses conservatively.
- **Do this (medium, moderate effort):** Add an accurate, visible published/updated date to substantive pages, mirrored in dateModified.

### F-006 · Content sections run long enough to bury facts mid-passage

- **Code:** `LONG_SECTIONS`  ·  **Severity:** medium  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 4 page(s) have 2+ sections over 300 words (e.g. https://www.lua.org/docs.html: 2 long sections, 1 in the 150-300 band).
- **Affected URLs:** https://www.lua.org/docs.html, https://www.lua.org/docs.html:
- **Why it matters:** Information in the middle of a long passage is retrieved markedly worse than information at its start or end -- and in controlled testing, a fact in the middle position scored BELOW the baseline of not supplying the document at all. The trough deepens as the passage grows.
- **Do this (medium, moderate effort):** Break long sections into 150-300 word chunks under their own descriptive subheadings, and move each section's key fact to its opening sentence.

### F-007 · 1 of 7 core questions about this brand cannot be answered from its own extractable content

- **Code:** `UNANSWERABLE_QUESTIONS`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Entity type inferred as 'professional_services' (services plus credentials/accreditation vocabulary). Sampled 15 page(s). Unanswerable: What does The Programming Language Lua do / offer? -> homepage exposes only 18 words of extractable text.
- **Why it matters:** An assistant answering a question about a brand builds the answer from what it can reach, read and quote at that moment. Where the answer is not present as extractable text, the assistant either omits the brand entirely or fills the gap from a third-party source it does not control -- which is how brands get described inaccurately. Each gap below is a specific question your site currently cannot answer.
- **Do this (medium, project effort):** Publish each missing fact as plain, visible text on a relevant page: What does The Programming Language Lua do / offer?
  - _How:_ Put the answer in body text, not only in an image, a PDF, a form, or a JS-rendered widget. Stating it once, plainly, is enough.

### F-008 · Multiple distinct phone numbers published across the site

- **Code:** `MULTIPLE_PHONE_NUMBERS`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 9 distinct phone numbers found across 15 sampled pages: 83 (2025) 101326 on 1 page(s); (408) 282-8800 on 1 page(s); (408) 280-1300 on 1 page(s); (408) 998-1900 on 1 page(s). This may be legitimate (separate departments or locations) or may be stale duplicates -- the audit cannot tell which, so this is a verification prompt.
- **Why it matters:** Internal consistency measured a citation advantage (OR 1.7-4.1). Where two values genuinely compete for the same role, neither a visitor nor a machine can tell which is current, so the fact becomes unusable and the source less trustworthy. Where they belong to different departments, this is fine and no action is needed.
- **Do this (medium, quick effort):** Confirm each phone number is intentional and current. If any is a stale duplicate of another, consolidate to one canonical phone number served from a single template include so it cannot drift again.

### F-009 · Homepage has no H1

- **Code:** `NO_H1`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** No H1 element found on https://www.lua.org/.
- **Affected URLs:** https://www.lua.org/
- **Why it matters:** The H1 is the clearest single statement of what a page is -- for a scanning visitor, for assistive technology, and for any system building a page outline.
- **Do this (medium, quick effort):** Add exactly one H1 stating plainly what the organisation does.

### F-010 · Most substantive pages offer no clear next action

- **Code:** `NO_CTA`  ·  **Severity:** medium  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** 10/15 sampled pages with over 150 words contain no call-to-action phrasing.
- **Why it matters:** A page that informs but does not offer a next step leaves the visitor to invent one, which most will not do. This is where discoverability gains leak away.
- **Do this (medium, moderate effort):** Give each substantive page one obvious next action appropriate to its intent.

### F-011 · Most images have no alt text

- **Code:** `MISSING_ALT_TEXT`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** 96/127 images across sampled pages have empty or missing alt attributes.
- **Why it matters:** Alt text is the text stand-in for an image. Without it, any information carried visually is unavailable to screen-reader users and to text extraction alike. Note that purely decorative icons legitimately use empty alt, so treat this as a prompt to review rather than proof that every instance is wrong.
- **Do this (medium, moderate effort):** Add descriptive alt text to images that carry meaning; keep alt="" for purely decorative ones.

### F-012 · Most pages have no meta description

- **Code:** `NO_META_DESCRIPTION`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 14/15 sampled pages expose no meta description.
- **Why it matters:** The description is a structural field used in retrieval and as an explicit one-line statement of page purpose.
- **Do this (low, moderate effort):** Write a specific description (roughly 120-160 characters) for each substantive page.

### F-013 · No language declared on the html element

- **Code:** `NO_HTML_LANG`  ·  **Severity:** low  ·  **Confidence:** 70%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** <html> has no lang attribute on https://www.lua.org/.
- **Affected URLs:** https://www.lua.org/
- **Why it matters:** Missing language metadata weakens locale and entity matching, and degrades screen reader pronunciation.
- **Do this (low, quick effort):** Add a lang attribute, e.g. <html lang="en">.

### F-014 · No llms.txt (optional, unproven -- informational only)

- **Code:** `NO_LLMS_TXT`  ·  **Severity:** low  ·  **Confidence:** 45%  ·  **Category:** discoverability  ·  **Evidence strength:** speculative
- **What we found:** GET /llms.txt returned no usable file.
- **Why it matters:** llms.txt is an emerging convention with, as of 2026, no demonstrated citation benefit: a 137,000-domain study found 97% of published files received zero requests, a ~300,000-domain study found no significant correlation with AI citations, and Google has said it does not support it. Listed for completeness only.
- **Do this (low, quick effort):** Optional. Prioritise sitemap.xml, crawler access and visible on-page facts first -- all three are far better evidenced. Add llms.txt only if it is cheap and you accept it may do nothing.

### F-015 · Pages open without a summary paragraph

- **Code:** `NO_INTRO_SUMMARY`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 3 page(s) over 300 words have under 25 words between the H1 and the first subheading. Examples: https://www.lua.org/about.html, https://www.lua.org/docs.html, https://www.lua.org/community.html.
- **Affected URLs:** https://www.lua.org/about.html, https://www.lua.org/docs.html, https://www.lua.org/community.html
- **Why it matters:** Retrieval favours content that answers early, and the opening position is the strongest slot in a passage. Some engine architectures weight the opening especially heavily when judging a batch of retrieved documents.
- **Do this (low, moderate effort):** Open each substantive page with a 40-120 word summary that directly answers the question the page exists to answer.

### F-016 · No breadcrumbs on a site with nested content

- **Code:** `NO_BREADCRUMBS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** 12 sampled page(s) sit two or more clicks deep and no breadcrumb navigation (BreadcrumbList markup or a breadcrumb nav landmark) was found.
- **Why it matters:** Someone arriving on a deep page from a search result or an assistant's citation has no way to tell where they are in the site or how to go up a level. Breadcrumbs also state the site's hierarchy explicitly for machines.
- **Do this (low, moderate effort):** Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.

### F-017 · No link to a privacy policy or terms page

- **Code:** `NO_PRIVACY_OR_TERMS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** Across 15 sampled page(s), no link was found to: privacy policy, terms / legal.
- **Why it matters:** These pages are a baseline trust signal for visitors deciding whether to transact, and their absence is conspicuous on any site that collects data. They are also commonly expected by platforms and reviewers.
- **Do this (low, quick effort):** Publish and link privacy policy, terms / legal from the site footer.

## Not assessed

Checks that do not apply to this kind of site, or areas that could not be observed (blocked, gated, or unreachable). Listed so the report is honest about its own coverage — these are **not** defects and are not scored:

- **N-001 · Visitor-goal checks not applicable: pricing, offering** (not applicable) — No pricing, offering destination was found, but this site shows no commercial signals (prices, purchase CTAs, Product/Offer structured data, or a pricing/shop URL), so these goals do not apply to it.
