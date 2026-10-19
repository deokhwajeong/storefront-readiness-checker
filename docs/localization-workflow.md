# Localization workflow

How storefront and partner strings move from source to launch-ready in every required locale. The workflow has five gates. The readiness checker enforces what can be checked mechanically (presence, completeness, length, copy-paste detection); people own the rest.

```
string freeze -> translation -> linguistic QA -> legal review -> release
      |               |               |                |
  source locked   completeness    in-market        legal strings
                  tracked daily   sign-off         signed off
```

## Gate 1: String freeze

**What freezes:** storefront UI strings, legal page copy, and partner listing fields that the storefront displays (title, short description, screenshot alt text).

**Rules**
- Freeze date is published at least four weeks ahead and repeated in every partner communication.
- After freeze, a source string changes only through an exception request that names the reason, the affected locales, and who pays for the re-translation time.
- Source strings are reviewed for translatability before freeze: no concatenated fragments, no text in images, plural and gender handled with message format placeholders, and length budgets stated next to the string.

**Length budgets.** A title tile that holds 30 characters in English will not hold the German translation of a descriptive title. Set budgets per UI surface, not per language, and state the unit. For CJK markets the checker measures display width (full-width characters count as two), because that is what the tile actually renders.

**Exit:** source catalog exported; checker run on source locale shows no `missing_title` or `title_max` findings.

## Gate 2: Translation

**Who:** translation vendors for storefront strings; partners for their own listings, with vendor support offered for partners without in-house localization.

**Tracking.** Translation completeness per market is the headline number in the readiness scorecard. It is computed field by field across every app listed in the market and every required locale:

```
completeness = present required strings / total required strings
```

A market's rule pack sets the gate (`translation.min_completeness`). Below the gate the market is blocked. Above it, individual gaps are warnings with owners.

**Fallbacks** are a policy decision, not a technical convenience. A pack may allow `en-GB -> en-US`; it should almost never allow `fr-CA -> fr-FR` or `es-MX -> es-ES` without explicit sign-off from the regional lead, because customers notice.

**Copy-paste detection.** The checker flags a non-English listing whose description is identical to the source. It is a cheap heuristic that catches the most common partner shortcut. It does not detect machine translation quality; LQA does.

**Exit:** every market at or above its completeness gate; remaining gaps assigned.

## Gate 3: Linguistic QA (LQA)

**Who:** in-market reviewers (native speakers who know the product), coordinated by the localization program manager.

**Scope**
- Rendered storefront screens, not spreadsheets. Truncation, line breaks, and RTL mirroring only show up in context.
- Terminology against the market glossary (for example, consistent terms for "install", "subscription", and "parental controls").
- Locale formats: dates, numbers, currency display. The checker verifies price display strings against the pack's format; LQA verifies everything else that is rendered.
- Right-to-left markets: layout mirroring, bidirectional text with embedded Latin brand names and numbers, icon direction.

**Severity scale used in LQA reports**

| Severity | Meaning | Launch impact |
|---|---|---|
| Critical | Wrong meaning, offensive, legal or pricing error | Blocks the market |
| Major | Truncation, untranslated UI, wrong terminology on a primary flow | Blocks unless an exception is approved |
| Minor | Style, punctuation, secondary screens | Tracked, does not block |

**Exit:** signed LQA report per locale with zero open critical issues.

## Gate 4: Legal review

**Who:** regional legal counsel.

**Scope**
- Terms of service, privacy policy, and any market-specific legal pages (imprint, commerce disclosure, legal notice) in each required locale.
- Content decisions recorded in the rule pack (`content` section): which content tags require review, minimum ratings, and where an app must not be offered.
- Price presentation rules where a market requires tax-inclusive display or specific wording.

Legal sign-off is recorded against a specific commit of the rule pack and the legal page URLs listed in `data/storefront.yaml`. If either changes after sign-off, the sign-off is void for that market.

**Exit:** sign-off recorded per market; checker shows no `link_*` blockers.

## Gate 5: Release

- Final scorecard generated from the release commit and attached to the go/no-go record.
- Translation memory and glossary updated with LQA fixes so the next release starts from the corrected baseline.
- Post-launch: a short retro per market wave covering late strings, vendor turnaround, and which checks caught real issues versus noise. Adjust packs and budgets from what you learn.

## Roles

| Role | Owns |
|---|---|
| Localization program manager | Schedule, vendor management, completeness tracking, LQA coordination |
| Regional launch lead | Fallback decisions, glossary, in-market reviewers |
| Partner management | Partner listing translations and deadlines |
| Legal counsel | Legal copy and content decisions per market |
| TPM | Gate reviews, exceptions, escalation, go/no-go input |
