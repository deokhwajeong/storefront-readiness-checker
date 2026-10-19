"""Core data types shared by every check.

A check never decides launch status on its own. It emits Findings; the
scorecard turns findings into a go / blocked call per market. Keeping that
separation means a policy change ("contrast is a blocker in market X") is a
rule pack edit, not a code change.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    BLOCKER = "blocker"  # market cannot launch until fixed
    WARNING = "warning"  # ship-able, but owned and tracked
    INFO = "info"  # context for reviewers, never affects status


class Area(StrEnum):
    LOCALES = "locales"
    TRANSLATION = "translation"
    STRING_LENGTH = "string_length"
    AGE_RATING = "age_rating"
    PRICING = "pricing"
    LEGAL = "legal"
    CONTENT = "content"
    ACCESSIBILITY = "accessibility"


@dataclass(frozen=True)
class Finding:
    area: Area
    severity: Severity
    message: str
    market: str | None = None  # None = storefront-wide
    app_id: str | None = None
    locale: str | None = None
    rule: str | None = None  # rule id or WCAG success criterion, e.g. "1.1.1"
    location: str | None = None  # file:line for template findings
    element: str | None = None  # offending markup snippet

    def to_dict(self) -> dict:
        return {k: (str(v) if isinstance(v, StrEnum) else v) for k, v in asdict(self).items()}


@dataclass
class MarketResult:
    market: str
    name: str
    status: str  # "go" | "blocked"
    findings: list[Finding] = field(default_factory=list)
    translation_completeness: float = 1.0  # 0..1 across required locales and fields
    apps_listed: int = 0
    apps_withheld: int = 0  # apps excluded from this market by content rules

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.BLOCKER]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]
