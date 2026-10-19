# Market rule pack authoring guide

A rule pack is one YAML file per market in `data/markets/`. It states what "ready to launch" means for that market in terms the checker can evaluate. Packs are written by regional launch leads and reviewed by legal; engineers should rarely need to touch them.

> The packs in this repo are illustrative examples for a fictional storefront. They are not legal advice and do not describe any jurisdiction's actual requirements. Real packs must be reviewed by counsel for each market.

## Anatomy of a pack

```yaml
# Market rule pack: Germany.
market: DE                    # two-letter uppercase code, unique across packs
name: Germany
notes: "German strings run long; the title limit is the tile limit."

locales:
  required: [de-DE]           # every listed app needs these locales
  fallback: {}                # e.g. {en-GB: en-US}; only for required locales

translation:
  required_fields: [title, description, screenshot_alt]
  min_completeness: 0.98      # below this the market is blocked

string_limits:
  title: {max: 30, unit: chars, severity: blocker}
  description: {max: 320, unit: chars, severity: warning}

age_rating:
  scheme: numeric-5           # must exist in data/rating_schemes.yaml

pricing:
  currency: "EUR"
  symbol: "€"
  position: "suffix"          # prefix | suffix
  space: true                 # space between number and symbol
  decimal: ","
  group: "."
  decimals: 2

legal:
  required_links: [terms, privacy, imprint]   # keys looked up in storefront.yaml

content:
  loot_boxes: {action: min_rating, min: "12"}
  simulated_gambling: {action: review}

accessibility:
  required: false             # true makes automated a11y failures a blocker here
  standard: "WCAG 2.0 Level AA"
```

## Field reference

### `locales`
- `required`: locales every listed app must provide. Also checked against the storefront's `ui_locales`; a required locale the UI is not translated into is a blocker.
- `fallback`: map of required locale to the locale allowed to stand in for it. Use sparingly and only with the regional lead's sign-off. A fallback counts as present for completeness.

### `translation`
- `required_fields`: any of `title`, `description`, `screenshot_alt`. Screenshot alt text is counted once per screenshot in the source locale.
- `min_completeness`: 0 to 1. The checker computes completeness across all listed apps and required locales. A missing title is always a blocker regardless of this gate.

### `string_limits`
- Supported fields: `title`, `description`.
- `unit`: `chars` counts code points; `display_width` counts full-width and wide characters as two columns. Use `display_width` for CJK markets where the UI budget is in columns.
- `severity`: `blocker` when overflow breaks the UI (tile titles), `warning` when it only truncates gracefully.

### `age_rating`
- `scheme`: one of the schemes in `data/rating_schemes.yaml`. Each scheme lists its values from least to most restrictive; that order is what `min_rating` compares against.
- An app with no rating in the scheme, or a value not in the scheme, is a blocker.

### `pricing`
All seven keys are required. The checker formats each paid app's amount with these rules and compares it with the display string the partner supplied. Mismatches (wrong decimals, wrong separator, wrong symbol position) and currency mismatches are blockers. Free apps are skipped.

### `legal`
- `required_links`: link types that must be published for this market under `legal_links.<MARKET>` in `data/storefront.yaml`. Each must be a non-empty HTTPS URL. Common types: `terms`, `privacy`; some markets add others (`imprint`, `legal_notice`, `commerce_disclosure`). Use whatever key names legal agrees on; the checker treats them as opaque.

### `content`
Map of content tag to rule. Apps declare tags in the catalog (`content_tags`). Actions:

| Action | Effect |
|---|---|
| `block` | Blocker if a tagged app is offered in this market. Resolve by removing the market from the app's availability or recording a policy exception. |
| `review` | Warning: a regional policy reviewer must sign off before launch. Does not change status. |
| `min_rating` | Blocker if the app's rating in this market's scheme is below `min`. |

If the partner has already excluded the app from the market (`exclude_markets`), no content rule fires; the scorecard records the exclusion as information.

### `accessibility`
- `required: true` makes any automated accessibility failure in the storefront templates a blocker for this market. Advisories stay warnings.
- `required: false` still reports failures, as a warning.

## How to add a market

1. Copy the closest existing pack (same currency or rating scheme) to `data/markets/<code>.yaml`.
2. Update `market`, `name`, `locales`, and `pricing` first. These are the most common sources of launch-day defects.
3. Add the market's legal links to `data/storefront.yaml`.
4. Run `storefront-readiness check --market <CODE>`. A malformed pack fails with the file name and the exact key, for example:
   ```
   error: xx.yaml: age_rating.scheme 'numeric5' is not defined
   ```
5. Open a pull request. Changes to `legal` or `content` require approval from regional legal counsel (enforce with CODEOWNERS).

## Review checklist

- [ ] Market code unique and matches the file name.
- [ ] Fallbacks agreed with the regional lead, and none crosses a regional variant without sign-off.
- [ ] Price format verified against a rendered sample by an in-market reviewer.
- [ ] Rating scheme matches what partners are asked to supply.
- [ ] Legal links resolve and are the localized versions.
- [ ] Content rules reviewed by legal; comment in the pack states the basis for each rule.
- [ ] `accessibility.required` decision recorded with its rationale.
