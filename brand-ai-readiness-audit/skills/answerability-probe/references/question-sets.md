# Canonical question sets by organisation type

The probe asks the questions people actually ask an assistant about a given
kind of organisation, then checks whether the answer exists in extractable
text. Type is **inferred from evidence**, never from a list of known sites, so
the approach generalises to sites never seen before.

## Type inference, in priority order

| Type | Inferred from |
|---|---|
| `education` | education schema types, or `/admission`, `/academics`, `/courses` paths |
| `publisher` | news/blog schema types, or 3+ article-shaped URLs |
| `saas` | `SoftwareApplication`/`WebApplication` schema, or a pricing path plus API/integration/docs vocabulary |
| `ecommerce` | a genuine cart CTA, or Product/Offer schema **plus** shipping or availability vocabulary |
| `local_business` | local-business schema, or opening hours **together with** a postal address |
| `professional_services` | services vocabulary plus credentials/accreditation vocabulary |
| `generic_org` | no strong signal |

**Ordering matters.** SaaS is tested before ecommerce because software vendors
commonly emit Product schema too, and reading one as a shop leads to asking it
about shipping and returns. Local business requires a physical-presence signal,
not merely hours-like text — during development a bare "open" matched "open
government" and "open data" and briefly misread a government site as a shop.

## Slots

**Universal** — identity, what it does, contact, location.

| Type | Additional slots |
|---|---|
| `ecommerce` | price, product specs, shipping and returns, availability |
| `saas` | price, product specs, integrations or docs, trial or signup |
| `local_business` | hours, phone, services, booking |
| `education` | programs, admissions, fees, deadlines |
| `publisher` | authorship, publish dates, topics |
| `professional_services` | services, credentials, case evidence |
| `generic_org` | services, about depth |

## What counts as an answer

Only what a non-JavaScript crawler would see: extracted body text plus
structured data. Specifically:

- **contact** needs a published email or `tel:` link. A contact form is not an
  answer — it is an invitation to ask, which an extractor cannot accept.
- **location** needs a postal code in text or a `PostalAddress` node.
- **price** needs an actual currency figure. "Contact us for pricing" reads as
  "no price exists".
- **hours** needs a real day/time pattern or `OpeningHoursSpecification`.
- **specs** needs 3+ attribute:value pairs or a table.

## Scoring

| Coverage | Severity |
|---|---|
| under 0.50 | critical |
| 0.50 – 0.74 | high |
| 0.75 and above | medium |

Coverage is answered slots over total slots for the inferred type.

## The second finding

Where unanswerable questions co-occur with extractability risks, the probe
raises a separate high-severity finding: the answer may exist on the page but
in a form nothing can read. That distinction matters because it is by far the
cheaper fix — the content is already written.

## Reading it critically

Check the inferred type in the finding's evidence line first. If the type is
wrong the question set is wrong and the findings are noise. Then weight the
named gaps by how likely a real customer is to ask that question of this
particular organisation — the probe treats all slots for a type equally, and
you should not.
