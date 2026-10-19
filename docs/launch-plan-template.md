# Multi-market launch plan (template)

Use this for any storefront launch or relaunch that ships to more than one market at once. Copy it, fill in the bracketed fields, and keep it as the single source of truth for scope, owners, and exit criteria. The readiness scorecard from this repo is the evidence for most exit criteria; the plan says who acts on it.

## 1. Launch summary

| Field | Value |
|---|---|
| Launch | [storefront relaunch, new market wave, major feature] |
| Markets in wave | [list of market codes] |
| Target launch date | [date, and the timezone the date is anchored to] |
| Accountable TPM | [name] |
| Decision forum | [weekly launch review; go/no-go meeting at T-5 business days] |
| Rollback owner | [name] |

**What success looks like:** [two or three measurable outcomes, for example "all wave 1 markets live with zero blocker findings; crash-free sessions at or above current baseline; partner catalog coverage at 95% or better per market"].

**Out of scope:** [state it explicitly; most launch slips come from scope that was assumed in, never agreed].

## 2. Market waves

Do not launch every market on the same day unless the risk is genuinely uniform. Group markets into waves by shared risk, not by geography.

| Wave | Markets | Why grouped | Target date |
|---|---|---|---|
| 0 (pilot) | [one market with a strong local team and low regulatory variance] | Validate the pipeline end to end | [date] |
| 1 | [markets sharing a currency, rating scheme, or legal template] | Same legal review and pricing rules | [date] |
| 2 | [markets with new locales, RTL scripts, or market-specific legal links] | Need extra linguistic QA and legal sign-off | [date] |

A market moves to a later wave rather than holding the whole wave when it is blocked on something only it needs (a local legal link, a rating certificate, a translation vendor gap).

## 3. Phases, owners, and exit criteria

Each phase ends with an explicit exit review. A phase is not "mostly done"; it either meets its exit criteria or it carries a named exception with an owner and a date.

### Phase 1: Scope and requirements (T-16 to T-12 weeks)

| Workstream | Owner | Output |
|---|---|---|
| Market requirements | Regional launch leads | Draft market rule pack per market (see [authoring guide](rule-pack-authoring.md)) |
| Legal and policy | Legal counsel per region | Required legal links, content restrictions, rating schemes confirmed |
| Accessibility | Accessibility lead | Target standard and certification path ([plan](accessibility-certification-plan.md)) |
| Partner readiness | Partner management | Partner list, catalog metadata deadlines communicated |

**Exit criteria**
- Every market in scope has a rule pack that loads without validation errors.
- Legal has reviewed each pack's `legal` and `content` sections and recorded sign-off in the pack's change history.
- Wave assignment agreed in the decision forum.

### Phase 2: Build and content intake (T-12 to T-6 weeks)

| Workstream | Owner | Output |
|---|---|---|
| Storefront templates | Web and TV client engineering | Templates pass automated accessibility checks |
| Catalog intake | Partner management | Partner metadata, ratings, and prices loaded |
| Localization | Localization program manager | String freeze, translation in progress ([workflow](localization-workflow.md)) |
| Pricing | Commerce | Price tiers and display formats per market |

**Exit criteria**
- Readiness scorecard runs nightly in CI and is posted to the launch channel.
- Template accessibility failures trend to zero; any remaining fail has a remediation ticket with a date before Phase 3 exit.
- String freeze declared and communicated to partners and translators.

### Phase 3: Verification (T-6 to T-2 weeks)

| Workstream | Owner | Output |
|---|---|---|
| Linguistic QA | Localization program manager and in-market reviewers | Signed-off LQA report per locale |
| Accessibility audit | Accessibility lead and external auditor | Manual audit report; remediation verified |
| Legal review | Legal counsel | Final review of rendered legal pages and content decisions |
| Functional QA | QA lead | Regression pass on target devices per market |

**Exit criteria**
- Scorecard shows zero blockers for every market in the wave, or the market is moved to a later wave.
- Each open warning has an owner and a due date in the tracker. Warnings are allowed at launch; unowned warnings are not.
- Manual accessibility audit complete for markets where accessibility is a launch gate.

### Phase 4: Go/no-go and launch (T-1 week to T+0)

**Go/no-go inputs** (all required in the meeting, no verbal updates):
1. Current scorecard (JSON and Markdown) with commit hash.
2. Open warnings list with owners.
3. LQA and accessibility sign-offs.
4. Rollback plan tested in staging.

**Decision rule:** a market is go when it has zero blockers and every required sign-off is recorded. The meeting decides per market, not per wave.

### Phase 5: Hypercare (T+0 to T+4 weeks)

| Signal | Owner | Threshold that triggers action |
|---|---|---|
| Storefront errors and crash-free sessions | Engineering on call | Regression versus pre-launch baseline |
| Partner escalations | Partner management | Any listing shown with wrong price, rating, or locale |
| Accessibility reports | Accessibility lead | Any report from users or advocacy groups gets a response within 5 business days |
| Regulatory inquiries | Legal | Same-day triage |

**Exit criteria:** two consecutive weeks within thresholds; warnings from launch either closed or rescheduled with the owning team's agreement.

## 4. RACI

| Activity | TPM | Regional lead | Legal | Localization | Engineering | Accessibility |
|---|---|---|---|---|---|---|
| Rule pack authoring | A | R | C | C | I | C |
| Rule pack legal sign-off | I | C | A/R | I | I | I |
| String freeze | A | I | I | R | C | I |
| Template remediation | A | I | I | I | R | C |
| Go/no-go call per market | A | R | C | C | C | C |

R = responsible, A = accountable, C = consulted, I = informed.

## 5. Risks to track from day one

| Risk | Early signal | Mitigation |
|---|---|---|
| Late partner metadata | Translation completeness flat for two weeks | Escalate through partner management; allow listing in fallback locale only where the pack permits it |
| Legal link not ready in one market | `link_*` blocker persists after Phase 2 | Move that market to the next wave instead of slipping the wave |
| Long strings in compounding languages | `title_max` blockers in de-DE, fi-FI, nl-NL | Agree on a short title field with partners before string freeze |
| Accessibility remediation underestimated | Fail count not falling week over week | Prioritize shared components (header, tiles, search) over page-specific fixes |
| Rule pack drift from legal advice | Pack edited without sign-off | Require legal approval in code review for `legal` and `content` sections |
