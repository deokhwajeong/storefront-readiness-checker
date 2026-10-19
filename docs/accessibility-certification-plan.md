# Accessibility certification plan

Plan for taking a storefront from "we think it is accessible" to an audited, documented conformance claim against WCAG 2.0 Level AA. The structure is audit, remediate, re-test, then certify and maintain.

## What automation does and does not cover

The checker in this repo evaluates six success criteria from static markup and declared design tokens:

| SC | Name | What is checked | What is not |
|---|---|---|---|
| 1.1.1 | Non-text content | `<img>` has an `alt` attribute; image inputs have alt text | Whether the alt text is accurate or useful |
| 1.3.1 | Info and relationships | Form fields have a programmatic label; heading levels do not skip (advisory) | Tables, lists, reading order, visual grouping |
| 1.4.3 | Contrast (minimum) | Every declared foreground/background token pair meets 4.5:1 (3:1 for large text) | Text over images or gradients, undeclared combinations, focus states |
| 2.4.4 | Link purpose | Links have an accessible name; generic text flagged (advisory) | Whether surrounding context makes a link clear |
| 3.1.1 | Language of page | `<html lang>` present and well formed | Language of parts (3.1.2), whether the value matches the content |
| 4.1.2 | Name, role, value | Buttons have an accessible name | Custom widgets, state changes, ARIA correctness |

WCAG 2.0 Level AA has 38 success criteria. Automated checks of any kind typically find only a minority of real issues. **Passing the checker is an entry condition for the manual audit, never a substitute for it.** On a TV storefront, the highest-impact issues are usually focus management with a remote control, screen reader (text-to-speech) output, and timing, none of which static checks can see.

## Phase 1: Baseline audit (2 to 3 weeks)

1. **Inventory.** List every template and shared component. Prioritize by traffic and by flow criticality: browse, search, app detail, install or purchase, account and parental controls, legal pages.
2. **Automated pass.** Run `storefront-readiness a11y storefront/templates --tokens storefront/tokens.json`. Fix the mechanical failures first so auditors spend their time on judgment calls.
3. **Manual audit.** An internal accessibility lead plus an external auditor review each prioritized flow against all applicable WCAG 2.0 A and AA criteria:
   - Keyboard and remote control only: every action reachable, focus always visible, focus order logical, no traps.
   - Screen reader: platform text-to-speech on the target devices, plus a desktop screen reader for the web storefront.
   - Zoom and text resize to 200%, high contrast modes where the platform offers them.
   - Media: captions and audio description for any promotional video.
4. **Report.** Each finding gets: success criterion, flow, component, severity, reproduction steps, and suggested fix.

**Exit:** audit report accepted; findings loaded into the tracker with owners.

## Phase 2: Remediation (4 to 8 weeks, depends on findings)

**Fix order**
1. Shared components first (header, navigation, tiles, search, dialogs). One fix there clears findings across every template.
2. Blockers on critical flows: anything that prevents a user from finding, installing, or paying for an app.
3. Design tokens: adjust failing color pairs in the token file so every consumer inherits the fix. Re-run contrast checks on all declared pairs.
4. Content: alt text guidelines for partners' screenshots, and the `screenshot_alt` field made a required translation field in market packs.

**Guardrails during remediation**
- The CI accessibility check runs on every pull request; new failures fail the build.
- Advisories (heading order, generic link text) are reviewed weekly; they are often real issues in context.
- Design review includes a contrast and focus-state check before visual changes merge.

**Exit:** zero automated failures; all critical and major manual findings fixed or with an approved exception.

## Phase 3: Re-test (1 to 2 weeks)

- Auditor re-tests every fixed finding and spot-checks unaffected flows for regressions.
- Users with disabilities test the critical flows on target devices. Their findings are weighted at least as heavily as the auditor's.
- Any new finding goes back through Phase 2 at its severity.

**Exit:** auditor confirms conformance for the scoped flows; remaining minor issues documented.

## Phase 4: Certification and documentation

- Obtain the auditor's conformance statement for the scoped pages and flows, listing the standard (WCAG 2.0 Level AA), the date, the devices and assistive technologies tested, and any exceptions.
- Publish an accessibility statement in the storefront with a contact channel for accessibility issues and a response commitment.
- Record which markets treat accessibility as a launch gate in their rule packs (`accessibility.required: true`) so the readiness scorecard blocks those markets on any automated failure.

## Phase 5: Maintain

Conformance decays with every release. Keep it:
- CI check stays on; the scorecard shows accessibility status for every market every night.
- New templates and components go through a lightweight manual review before release.
- Re-audit annually and after any major redesign.
- Track accessibility reports from users with the same response targets as other customer-impacting defects.

## Roles

| Role | Owns |
|---|---|
| Accessibility lead | Standard, audit scope, triage, sign-off |
| External auditor | Independent audit and re-test, conformance statement |
| Engineering leads | Remediation per component |
| Design system owner | Token contrast, focus styles, component patterns |
| Partner management | Partner guidance on screenshot alt text and metadata |
| TPM | Plan, schedule, exception process, launch gating |
