# AI Discoverability & Engagement Audit — www.adobe.com

_Audited 2026-09-23T15:58:47Z · 15 pages sampled in 52.8s_

**20 findings** — 0 critical · 4 high · 8 medium · 8 low

## Readiness at a glance

| Pillar | Score |
|---|---|
| Reachable | `████████░░` 88/100 |
| Readable | `████████░░` 86/100 |
| Quotable | `██████░░░░` 67/100 |
| Answerable | `███████░░░` 76/100 |
| Current & corroborated | `█████████░` 93/100 |
| Engaging | `████████░░` 82/100 |

_Scores are this audit's own 0-100 framework (100 = no findings in that pillar), intended to show relative weakness at a glance. They are not a validated or externally comparable metric._

## Remediation roadmap

_Bucketed by impact against implementation cost, so a cheap fix is not queued behind an expensive one. Severity order is preserved within each bucket._

### Do now

- **F-001 · Facts appear to be locked in non-text elements** (high, project effort) — Add a plain-text equivalent alongside each of these elements: real HTML text for prices and specs shown as images, an HTML summary beside PDF-only documents, and descriptive alt text on fact-bearing graphics.
- **F-002 · Commercial pages state no explicit price in extractable text** (high, moderate effort) — Publish a real figure, a starting-from figure, or an explicit range as plain text on each commercial page.
- **F-003 · 3 of 8 core questions about this brand cannot be answered from its own extractable content** (high, project effort) — Publish each missing fact as plain, visible text on a relevant page: How do I contact Adobe?, How much does Adobe cost?, What are the specifications / what's included?
- **F-004 · Some missing answers may exist on the page but in a non-extractable form** (high, project effort) — Add a plain-text equivalent beside each non-textual element carrying a fact (prices in images, spec tables as graphics, PDF-only documents).
- **F-014 · No language declared on the html element** (low, quick effort) — Add a lang attribute, e.g. <html lang="en">.
- **F-019 · No link to a privacy policy or terms page** (low, quick effort) — Publish and link privacy policy, terms / legal from the site footer.

### Do next

- **F-005 · Most pages publish no date at all** (medium, moderate effort) — Add an accurate, visible published/updated date to substantive pages, mirrored in dateModified.
- **F-006 · Product pages lack structured specifications** (medium, moderate effort) — Add a specification table or definition list of concrete attributes and values to each product/service page.
- **F-011 · Most images have no alt text** (medium, moderate effort) — Add descriptive alt text to images that carry meaning; keep alt="" for purely decorative ones.
- **F-012 · Homepage extractable text is unrendered CMS template bindings, not a value proposition** (medium, unknown effort) — Server-render the homepage hero and product-card copy (headline, one-line description, audience, primary CTA) so it appears as real HTML text.

### Later / ongoing

- **F-007 · No comparison against alternatives anywhere in the sampled pages** (medium, project effort) — Publish an honest comparison page covering how you differ from named alternatives, including where you are not the right fit.
- **F-008 · Most sampled pages are very thin** (medium, project effort) — Expand the substantive pages with concrete detail, or consolidate thin pages into fewer, richer ones.
- **F-009 · No third-party corroboration signals anywhere on the site** (medium, project effort) — Build and then reference independent presence: a Wikidata item, an accurate LinkedIn and Crunchbase profile, listings on the review platforms your category uses, and coverage in real publications.
- **F-010 · Common visitor goals have no reachable page** (medium, project effort) — Add clear, crawlable navigation links to each missing destination, using plain labels ('Contact', 'Pricing') rather than icons or JavaScript-only menus.
- **F-013 · Only weak or legacy structured data is present** (low, moderate effort) — Add an Organization JSON-LD block alongside the existing markup rather than replacing it.
- **F-015 · Pages open without a summary paragraph** (low, moderate effort) — Open each substantive page with a 40-120 word summary that directly answers the question the page exists to answer.
- **F-016 · Priority claims to verify against independent sources** (low, project effort) — For each claim above, search independent sources working DOWN this ladder and stop at the first tier that settles it: P0 Government / regulatory registries; P1 Structured knowledge bases; P2 Established independent news; P3 User & review platforms; P4 Other websites. Count a claim corroborated only when a source that is NOT the brand, NOT a press-release wire, and NOT an aggregator copying one origin agrees with it. Record CONTRADICTED / CONFIRMED / UNCORROBORATED per claim (uncorroborated is not the same as false).
- **F-017 · Off-site corroboration of core identity claims confirmed** (low, unknown effort) — No action needed; optionally add sameAs links (Wikidata, LinkedIn) to the Organization JSON-LD.
- **F-018 · No breadcrumbs on a site with nested content** (low, moderate effort) — Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.
- **F-020 · Many links use uninformative anchor text** (low, moderate effort) — Rewrite these links so the anchor text names the destination -- 'read the pricing guide' rather than 'click here'.

## All findings

### F-001 · Facts appear to be locked in non-text elements

- **Code:** `FACTS_IN_NON_TEXT`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Detected: unrendered_template_binding on 8 page(s) (e.g. https://www.adobe.com/homepage/fragments/loggedout/redesign/default/all-products-card/all-products-card). Reviewer note: the 8 pages include CMS fragment endpoints; the same template-binding evidence also appears on the homepage.
- **Affected URLs:** https://www.adobe.com/homepage/fragments/loggedout/redesign/default/all-products-card/all-products-card
- **Why it matters:** A fact carried only by an image, a PDF, a canvas, a third-party embed or an unrendered template is invisible to text extraction. The information already exists -- it just cannot be read -- which makes this among the cheapest gaps to close.
- **Do this (high, project effort):** Add a plain-text equivalent alongside each of these elements: real HTML text for prices and specs shown as images, an HTML summary beside PDF-only documents, and descriptive alt text on fact-bearing graphics.

### F-002 · Commercial pages state no explicit price in extractable text

- **Code:** `NO_PRICE`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 9/9 pricing/product-like pages contain no currency figure in the extracted text. Examples: https://www.adobe.com/, https://www.adobe.com/products/catalog.html, https://www.adobe.com/products/firefly.html.
- **Affected URLs:** https://www.adobe.com/, https://www.adobe.com/products/catalog.html, https://www.adobe.com/products/firefly.html
- **Why it matters:** A visible price is a citation gatekeeper: its absence measured an OR above 100 against being cited, unanimously across all 6 models tested -- missing price alone can eliminate citation odds regardless of other content strengths. 'Contact us for pricing' reads to an answer engine as 'no price exists'.
- **Do this (high, moderate effort):** Publish a real figure, a starting-from figure, or an explicit range as plain text on each commercial page.
  - _How:_ Even 'from $49/month' or 'typical projects run $5,000-$15,000' is extractable; 'request a quote' is not.

### F-003 · 3 of 8 core questions about this brand cannot be answered from its own extractable content

- **Code:** `UNANSWERABLE_QUESTIONS`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Entity type inferred as 'saas' (SoftwareApplication schema, or a pricing/plans path plus API/integration/docs vocabulary). Sampled 15 page(s). Unanswerable: How do I contact Adobe? -> no email or tel: link in extractable text; How much does Adobe cost? -> no currency figure anywhere in the extracted text of the sampled pages; What are the specifications / what's included? -> no spec table and at most 1 attribute:value pairs on any page.
- **Why it matters:** An assistant answering a question about a brand builds the answer from what it can reach, read and quote at that moment. Where the answer is not present as extractable text, the assistant either omits the brand entirely or fills the gap from a third-party source it does not control -- which is how brands get described inaccurately. Each gap below is a specific question your site currently cannot answer.
- **Do this (high, project effort):** Publish each missing fact as plain, visible text on a relevant page: How do I contact Adobe?, How much does Adobe cost?, What are the specifications / what's included?
  - _How:_ Put the answer in body text, not only in an image, a PDF, a form, or a JS-rendered widget. Stating it once, plainly, is enough.

### F-004 · Some missing answers may exist on the page but in a non-extractable form

- **Code:** `ANSWERS_NOT_EXTRACTABLE`  ·  **Severity:** high  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** Detected extractability risks across sampled pages: unrendered_template_binding. These co-occur with 3 unanswerable question(s).
- **Why it matters:** A fact rendered inside an image, canvas, PDF, third-party embed or client-side template is visible to a human but absent for a text extractor. This is the most recoverable class of gap -- the content already exists and only needs a text equivalent.
- **Do this (high, project effort):** Add a plain-text equivalent beside each non-textual element carrying a fact (prices in images, spec tables as graphics, PDF-only documents).
  - _How:_ A short HTML table or paragraph next to the visual is sufficient; the visual can stay.

### F-005 · Most pages publish no date at all

- **Code:** `UNDATED_CONTENT`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 15/15 sampled pages expose no visible updated/copyright year and no JSON-LD date field.
- **Why it matters:** A recent timestamp measured a clear citation advantage over no timestamp in every model tested. Undated content forces an answer engine to guess at currency, and it guesses conservatively.
- **Do this (medium, moderate effort):** Add an accurate, visible published/updated date to substantive pages, mirrored in dateModified.

### F-006 · Product pages lack structured specifications

- **Code:** `NO_SPECS`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 9/9 commercial pages expose fewer than 3 attribute:value spec pairs and no spec table. Examples: https://www.adobe.com/, https://www.adobe.com/products/catalog.html, https://www.adobe.com/products/firefly.html.
- **Affected URLs:** https://www.adobe.com/, https://www.adobe.com/products/catalog.html, https://www.adobe.com/products/firefly.html
- **Why it matters:** Presence of technical specifications measured OR 8.6-243 for citation across models -- it is one of the strongest completeness differentiators, because it gives the engine discrete attributes it can match against a specific question.
- **Do this (medium, moderate effort):** Add a specification table or definition list of concrete attributes and values to each product/service page.

### F-007 · No comparison against alternatives anywhere in the sampled pages

- **Code:** `NO_COMPARISON`  ·  **Severity:** medium  ·  **Confidence:** 75%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** None of the 9 commercial pages contain comparison language (vs / compared to / alternative to / instead of).
- **Why it matters:** Pages that compare against alternatives measured OR 1.6-7.5 for citation. Separately, ranked comparison and 'best-of' content accounts for the single largest share of content citations in AI answers (~36%) -- far more than any brand's own marketing pages.
- **Do this (medium, project effort):** Publish an honest comparison page covering how you differ from named alternatives, including where you are not the right fit.
  - _How:_ Omitting genuine limitations is classed as a manipulation pattern and is increasingly detected -- state trade-offs honestly.

### F-008 · Most sampled pages are very thin

- **Code:** `THIN_PAGES`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 11/15 sampled pages contain under 150 words of extracted text.
- **Why it matters:** Depth of coverage measured OR 4-10,000+ for citation. Thin pages rarely contain enough quotable substance to be selected as a source, and they also suggest the real content may not be reaching the extractor at all -- cross-check the crawl-render findings for a rendering gap before treating this as purely editorial.
- **Do this (medium, project effort):** Expand the substantive pages with concrete detail, or consolidate thin pages into fewer, richer ones.

### F-009 · No third-party corroboration signals anywhere on the site

- **Code:** `NO_CORROBORATION`  ·  **Severity:** medium  ·  **Confidence:** 75%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** Across 15 sampled pages there are no outbound links to independent reference or review sources (g2.com, trustpilot.com, capterra.com, wikipedia.org, wikidata.org, linkedin.com...) and no press-mention language.
- **Why it matters:** Only a small share of AI citations point at a brand's own domain -- the large majority point at third-party pages discussing it. A brand whose claims appear nowhere but its own site has nothing for an assistant to corroborate against, and self-assertion alone is weak evidence.
- **Do this (medium, project effort):** Build and then reference independent presence: a Wikidata item, an accurate LinkedIn and Crunchbase profile, listings on the review platforms your category uses, and coverage in real publications.
  - _How:_ Getting included in credible third-party comparison and 'best of' roundups is unusually high-leverage: ranked listicles account for the single largest share of content citations in AI answers.

### F-010 · Common visitor goals have no reachable page

- **Code:** `GOALS_UNREACHABLE`  ·  **Severity:** medium  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** No page or homepage link matching these goals was found in the crawl: contact, about. Crawl reached 135 internal URL(s) from the homepage. Reviewer note: a bounded 15-page sample dominated by CMS fragments and a client-rendered nav; Adobe's real contact/about pages very likely exist, so this is most likely a crawlable-link gap rather than absence.
- **Why it matters:** These are the destinations visitors arrive looking for. If a goal has no discoverable path from the homepage, the visitor must guess a URL or leave -- and an assistant browsing on their behalf will simply report that it could not find the information.
- **Do this (medium, project effort):** Add clear, crawlable navigation links to each missing destination, using plain labels ('Contact', 'Pricing') rather than icons or JavaScript-only menus.
  - _How:_ If these pages do exist, the problem is that they are not linked in crawlable HTML -- check whether the navigation is rendered client-side.

### F-011 · Most images have no alt text

- **Code:** `MISSING_ALT_TEXT`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** 40/67 images across sampled pages have empty or missing alt attributes.
- **Why it matters:** Alt text is the text stand-in for an image. Without it, any information carried visually is unavailable to screen-reader users and to text extraction alike. Note that purely decorative icons legitimately use empty alt, so treat this as a prompt to review rather than proof that every instance is wrong.
- **Do this (medium, moderate effort):** Add descriptive alt text to images that carry meaning; keep alt="" for purely decorative ones.

### F-012 · Homepage extractable text is unrendered CMS template bindings, not a value proposition

- **Code:** `HOMEPAGE_EXTRACTABLE_TEXT_IS_UNRENDERED`  ·  **Severity:** medium  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** Homepage text_sample in evidence.json begins with the title 'Adobe: Creative, marketing and document management solutions' followed by repeated 'mas-field: ACOM / Headless / Individual / com / Creative Cloud Individual -> Title/Subtitle/Product description' placeholders and CTA labels such as 'Free trial - segmentation - modal' and 'Create with Firefly'. Only 'Adobe for Business' reads as audience copy. What it is: only the <title>. Who for: implied (individual vs business). Next action: CTA labels present but embedded in placeholder strings.
- **Why it matters:** A non-rendering extractor sees template field names instead of prose, so it cannot state what Adobe is, who it serves, or what to do next from body text. Human visitors likely see rendered content; this is a text-extraction orientation gap.
- **Do this (medium, unknown effort):** Server-render the homepage hero and product-card copy (headline, one-line description, audience, primary CTA) so it appears as real HTML text.

### F-013 · Only weak or legacy structured data is present

- **Code:** `WEAK_STRUCTURED_DATA`  ·  **Severity:** low  ·  **Confidence:** 70%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** Verdicts across sampled pages: ['SOCIAL_META_ONLY', 'STRUCTURED_DATA_PRESENT']. 0 page(s) carry only classic microformats, 14 only social meta tags.
- **Why it matters:** These formats are read by fewer consumers than JSON-LD and typically carry less entity detail, but they ARE structured data -- this is a gap in richness, not an absence of markup.
- **Do this (low, moderate effort):** Add an Organization JSON-LD block alongside the existing markup rather than replacing it.

### F-014 · No language declared on the html element

- **Code:** `NO_HTML_LANG`  ·  **Severity:** low  ·  **Confidence:** 70%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** <html> has no lang attribute on https://www.adobe.com/.
- **Affected URLs:** https://www.adobe.com/
- **Why it matters:** Missing language metadata weakens locale and entity matching, and degrades screen reader pronunciation.
- **Do this (low, quick effort):** Add a lang attribute, e.g. <html lang="en">.

### F-015 · Pages open without a summary paragraph

- **Code:** `NO_INTRO_SUMMARY`  ·  **Severity:** low  ·  **Confidence:** 85%  ·  **Category:** discoverability  ·  **Evidence strength:** measured
- **What we found:** 2 page(s) over 300 words have under 25 words between the H1 and the first subheading. Examples: https://www.adobe.com/, https://www.adobe.com/creativecloud/plans/merch-shared/fragments/faqs/catalog.
- **Affected URLs:** https://www.adobe.com/, https://www.adobe.com/creativecloud/plans/merch-shared/fragments/faqs/catalog
- **Why it matters:** Retrieval favours content that answers early, and the opening position is the strongest slot in a passage. Some engine architectures weight the opening especially heavily when judging a batch of retrieved documents. Fix the tier-1 gatekeeper findings first -- structural work measured negligible benefit on pages that still fail a gatekeeper.
- **Do this (low, moderate effort):** Open each substantive page with a 40-120 word summary that directly answers the question the page exists to answer.

### F-016 · Priority claims to verify against independent sources

- **Code:** `PRIORITY_CLAIMS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** Inferred site type: saas. The claims most worth spending the bounded off-site query budget on (Part B):
1. [identity] Adobe (from JSON-LD, on 1 page)
2. [identity] Adobe Inc. (from JSON-LD, on 1 page)
3. [location] 345 Park Avenue, San Jose, CA, 95110, US (from JSON-LD, on 1 page)
- **Why it matters:** Off-site corroboration is where most of the citation surface is -- assistants trust a fact more when independent sources agree, and a claim that lives only on the brand's own site has nothing to check it against. Verifying the highest-value claims first, and weighting sources by authority, spends a small query budget where it matters.
- **Do this (low, project effort):** For each claim above, search independent sources working DOWN this ladder and stop at the first tier that settles it: P0 Government / regulatory registries; P1 Structured knowledge bases; P2 Established independent news; P3 User & review platforms; P4 Other websites. Count a claim corroborated only when a source that is NOT the brand, NOT a press-release wire, and NOT an aggregator copying one origin agrees with it. Record CONTRADICTED / CONFIRMED / UNCORROBORATED per claim (uncorroborated is not the same as false).
  - _How:_ P0/P1 (registries, Wikidata/Crunchbase) settle identity, founding year and location cheaply. Reserve P2 news for disputed or reputational claims. P3 review sites only for reputation, weighted low.

### F-017 · Off-site corroboration of core identity claims confirmed

- **Code:** `OFF_SITE_CORROBORATION_OF_CORE`  ·  **Severity:** low  ·  **Confidence:** 70%  ·  **Category:** discoverability  ·  **Evidence strength:** correlational
- **What we found:** Web search on 2026-09-23 returned independent sources agreeing with the site's JSON-LD: Wikipedia 'Adobe Inc.' and Britannica (San Jose HQ, founded 1982), Wikipedia 'Adobe World Headquarters' (345 Park Avenue, San Jose, CA 95110), and an SEC EDGAR filing (CIK 796343). Claims CONFIRMED, no contradictions. Only one bounded query was run; sameAs links to Wikidata/LinkedIn were not verified.
- **Why it matters:** Independent agreement raises trust in the brand's own claims. Recorded as a pass.
- **Do this (low, unknown effort):** No action needed; optionally add sameAs links (Wikidata, LinkedIn) to the Organization JSON-LD.

### F-018 · No breadcrumbs on a site with nested content

- **Code:** `NO_BREADCRUMBS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** 8 sampled page(s) sit two or more clicks deep and no breadcrumb navigation (BreadcrumbList markup or a breadcrumb nav landmark) was found.
- **Why it matters:** Someone arriving on a deep page from a search result or an assistant's citation has no way to tell where they are in the site or how to go up a level. Breadcrumbs also state the site's hierarchy explicitly for machines.
- **Do this (low, moderate effort):** Add breadcrumb navigation to nested pages, marked up with BreadcrumbList.

### F-019 · No link to a privacy policy or terms page

- **Code:** `NO_PRIVACY_OR_TERMS`  ·  **Severity:** low  ·  **Confidence:** 75%  ·  **Category:** engagement  ·  **Evidence strength:** correlational
- **What we found:** Across 15 sampled page(s), no link was found to: privacy policy, terms / legal. Reviewer note: sample dominated by fragment URLs with no footer; likely not sitewide.
- **Why it matters:** These pages are a baseline trust signal for visitors deciding whether to transact, and their absence is conspicuous on any site that collects data. They are also commonly expected by platforms and reviewers.
- **Do this (low, quick effort):** Publish and link privacy policy, terms / legal from the site footer.

### F-020 · Many links use uninformative anchor text

- **Code:** `VAGUE_ANCHOR_TEXT`  ·  **Severity:** low  ·  **Confidence:** 90%  ·  **Category:** engagement  ·  **Evidence strength:** measured
- **What we found:** 9 link(s) across sampled pages use generic anchor text such as link.
- **Why it matters:** Anchor text is how both a screen-reader user scanning links and a machine building a link graph work out what is on the other end. 'Click here' describes nothing, so the destination's topic is lost.
- **Do this (low, moderate effort):** Rewrite these links so the anchor text names the destination -- 'read the pricing guide' rather than 'click here'.
