"""Turn findings into a per-market go / blocked call and render it.

Scoring rule (also drawn in the README):
  1. Run every market check against the catalog for that market.
  2. Run accessibility checks once on the storefront templates and design tokens.
  3. If the market pack makes accessibility a launch gate, template failures add
     one blocker to that market; otherwise they add one warning.
  4. A market is "blocked" if it has at least one blocker, else "go".
Warnings never change status; they are carried as owned follow-ups.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from .checks.market import MARKET_CHECKS, apps_for_market, check_translation
from .loader import MarketPack, Storefront
from .models import Area, Finding, MarketResult, Severity

A11Y_DISCLAIMER = (
    "Automated checks cover only a subset of WCAG 2.0 success criteria (1.1.1, 1.3.1, "
    "1.4.3, 2.4.4, 3.1.1, 4.1.2) and only what is visible in static markup and declared "
    "design tokens. Passing them does not establish conformance. Manual review with "
    "keyboard and assistive technology testing is required before any certification claim."
)
RULES_DISCLAIMER = (
    "Market rule packs are illustrative examples for a fictional storefront. They are not "
    "legal advice and do not describe any jurisdiction's actual requirements."
)
AREA_LABEL = {
    Area.LOCALES: "Locales",
    Area.TRANSLATION: "Translation",
    Area.STRING_LENGTH: "String length",
    Area.AGE_RATING: "Age rating",
    Area.PRICING: "Pricing",
    Area.LEGAL: "Legal links",
    Area.CONTENT: "Content rules",
    Area.ACCESSIBILITY: "Accessibility",
}


@dataclass
class Report:
    storefront: str
    as_of: str
    markets: list[MarketResult]
    accessibility: list[Finding] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)

    @property
    def go(self) -> list[MarketResult]:
        return [m for m in self.markets if m.status == "go"]

    @property
    def blocked(self) -> list[MarketResult]:
        return [m for m in self.markets if m.status == "blocked"]

    @property
    def a11y_fails(self) -> list[Finding]:
        return [f for f in self.accessibility if f.severity is Severity.BLOCKER]

    @property
    def a11y_advisories(self) -> list[Finding]:
        return [f for f in self.accessibility if f.severity is not Severity.BLOCKER]


def _a11y_gate(mp: MarketPack, fails: list[Finding], advisories: list[Finding]) -> list[Finding]:
    out = []
    if fails:
        criteria = ", ".join(sorted({f.rule or "" for f in fails}))
        if mp.accessibility_required:
            out.append(
                Finding(
                    Area.ACCESSIBILITY,
                    Severity.BLOCKER,
                    f"{len(fails)} automated {mp.accessibility_standard} failures in "
                    f"storefront templates ({criteria}); accessibility is a launch "
                    "gate here",
                    market=mp.code,
                    rule="a11y_gate",
                )
            )
        else:
            out.append(
                Finding(
                    Area.ACCESSIBILITY,
                    Severity.WARNING,
                    f"{len(fails)} automated accessibility failures in storefront "
                    f"templates ({criteria}); not a launch gate in this market",
                    market=mp.code,
                    rule="a11y_gate",
                )
            )
    if advisories:
        out.append(
            Finding(
                Area.ACCESSIBILITY,
                Severity.WARNING,
                f"{len(advisories)} accessibility advisories to review",
                market=mp.code,
                rule="a11y_advisory",
            )
        )
    return out


def evaluate_market(sf: Storefront, mp: MarketPack, a11y: list[Finding]) -> MarketResult:
    findings: list[Finding] = []
    translation, completeness = check_translation(sf, mp)
    findings += translation
    for check in MARKET_CHECKS:
        findings += check(sf, mp)
    fails = [f for f in a11y if f.severity is Severity.BLOCKER]
    advisories = [f for f in a11y if f.severity is not Severity.BLOCKER]
    findings += _a11y_gate(mp, fails, advisories)

    listed, withheld = apps_for_market(sf, mp)
    status = "blocked" if any(f.severity is Severity.BLOCKER for f in findings) else "go"
    return MarketResult(
        market=mp.code,
        name=mp.name,
        status=status,
        findings=findings,
        translation_completeness=round(completeness, 4),
        apps_listed=len(listed),
        apps_withheld=len(withheld),
    )


def evaluate(
    sf: Storefront,
    a11y: list[Finding] | None = None,
    templates: list[str] | None = None,
    as_of: str | None = None,
    markets: list[str] | None = None,
) -> Report:
    a11y = a11y or []
    packs = [m for m in sf.markets if not markets or m.code in markets]
    results = [evaluate_market(sf, mp, a11y) for mp in packs]
    return Report(
        storefront=sf.name,
        as_of=as_of or date.today().isoformat(),
        markets=results,
        accessibility=a11y,
        templates=templates or [],
    )


# --------------------------------------------------------------------------- JSON


def to_json(report: Report) -> str:
    def market(m: MarketResult) -> dict:
        by_area = Counter(str(f.area) for f in m.blockers)
        return {
            "market": m.market,
            "name": m.name,
            "status": m.status,
            "translation_completeness": m.translation_completeness,
            "apps_listed": m.apps_listed,
            "apps_withheld": m.apps_withheld,
            "blocker_count": len(m.blockers),
            "warning_count": len(m.warnings),
            "blockers_by_area": dict(sorted(by_area.items())),
            "blockers": [f.to_dict() for f in m.blockers],
            "warnings": [f.to_dict() for f in m.warnings],
        }

    payload = {
        "storefront": report.storefront,
        "as_of": report.as_of,
        "summary": {
            "markets": len(report.markets),
            "go": len(report.go),
            "blocked": len(report.blocked),
            "accessibility_failures": len(report.a11y_fails),
            "accessibility_advisories": len(report.a11y_advisories),
        },
        "markets": [market(m) for m in report.markets],
        "accessibility": {
            "templates_checked": report.templates,
            "criteria_checked": ["1.1.1", "1.3.1", "1.4.3", "2.4.4", "3.1.1", "4.1.2"],
            "findings": [f.to_dict() for f in report.accessibility],
            "disclaimer": A11Y_DISCLAIMER,
        },
        "disclaimer": RULES_DISCLAIMER,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- Markdown


def _cell(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _finding_line(f: Finding) -> str:
    who = " ".join(x for x in (f"`{f.app_id}`" if f.app_id else "", f.locale or "") if x)
    return f"- **{AREA_LABEL[f.area]}**: {f.message}" + (f" ({who})" if who else "")


def to_markdown(report: Report) -> str:
    lines = [
        f"# Launch readiness: {report.storefront}",
        "",
        f"As of {report.as_of}. **{len(report.go)} of {len(report.markets)} markets are go**, "
        f"{len(report.blocked)} blocked.",
        "",
        "| Market | Status | Blockers | Warnings | Translation | Apps listed |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for m in report.markets:
        status = "GO" if m.status == "go" else "BLOCKED"
        lines.append(
            f"| {m.market} {m.name} | {status} | {len(m.blockers)} | "
            f"{len(m.warnings)} | {m.translation_completeness:.1%} | {m.apps_listed} |"
        )

    if report.blocked:
        lines += ["", "## Blocked markets", ""]
        for m in report.blocked:
            lines += [f"### {m.market} {m.name}", ""]
            lines += [_finding_line(f) for f in m.blockers]
            lines.append("")

    # Storefront-wide accessibility warnings repeat in every market; list them once below.
    def market_specific(m: MarketResult) -> list[Finding]:
        return [f for f in m.warnings if not (f.rule or "").startswith("a11y_")]

    warn_markets = [m for m in report.markets if market_specific(m)]
    if warn_markets:
        lines += [
            "## Open warnings (do not block launch)",
            "",
            "Market-specific only; storefront-wide accessibility findings are listed once "
            "in the next section.",
            "",
        ]
        for m in warn_markets:
            lines += [f"### {m.market} {m.name}", ""]
            lines += [_finding_line(f) for f in market_specific(m)]
            lines.append("")

    lines += [
        "## Accessibility: storefront templates",
        "",
        f"Templates checked: {', '.join(report.templates) or 'none'}.",
        "",
        f"> {A11Y_DISCLAIMER}",
        "",
    ]
    if report.accessibility:
        lines += ["| WCAG SC | Result | Location | Finding | Element |", "|---|---|---|---|---|"]
        for f in report.accessibility:
            kind = "fail" if f.severity is Severity.BLOCKER else "advisory"
            lines.append(
                f"| {f.rule} | {kind} | {_cell(f.location)} | {_cell(f.message)} | "
                f"`{_cell(f.element)}` |"
            )
    else:
        lines.append("No automated findings.")
    lines += ["", f"_{RULES_DISCLAIMER}_", ""]
    return "\n".join(lines)
