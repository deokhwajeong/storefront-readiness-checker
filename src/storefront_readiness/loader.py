"""Load and validate the catalog, storefront config, rating schemes, and market rule packs.

Rule packs are authored by people who are not engineers (regional launch
leads, legal reviewers). Validation therefore fails loudly with the file name
and the exact key, instead of letting a typo silently disable a rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_FIELDS = {"title", "description", "screenshot_alt"}
VALID_UNITS = {"chars", "display_width"}
VALID_SEVERITIES = {"blocker", "warning"}
VALID_CONTENT_ACTIONS = {"block", "review", "min_rating"}
PRICING_KEYS = {"currency", "symbol", "position", "space", "decimal", "group", "decimals"}
PACK_KEYS = {
    "market", "name", "notes", "locales", "translation", "string_limits",
    "age_rating", "pricing", "legal", "content", "accessibility",
}  # fmt: skip


class RulePackError(ValueError):
    """Raised when a rule pack or data file is malformed."""


@dataclass
class MarketPack:
    code: str
    name: str
    required_locales: list[str]
    fallback: dict[str, str]
    required_fields: list[str]
    min_completeness: float
    string_limits: dict[str, dict[str, Any]]
    rating_scheme: str
    pricing: dict[str, Any]
    required_links: list[str]
    content: dict[str, dict[str, Any]]
    accessibility_required: bool
    accessibility_standard: str
    notes: str = ""
    source: str = ""


@dataclass
class Storefront:
    name: str
    source_locale: str
    ui_locales: list[str]
    legal_links: dict[str, dict[str, str]]
    apps: list[dict[str, Any]]
    schemes: dict[str, dict[str, Any]]
    markets: list[MarketPack] = field(default_factory=list)


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RulePackError(f"{path.name}: invalid YAML: {exc}") from exc


def _require(cond: bool, where: str, msg: str) -> None:
    if not cond:
        raise RulePackError(f"{where}: {msg}")


def parse_market_pack(raw: dict[str, Any], schemes: dict[str, Any], where: str) -> MarketPack:
    _require(isinstance(raw, dict), where, "rule pack must be a mapping")
    unknown = set(raw) - PACK_KEYS
    _require(not unknown, where, f"unknown keys {sorted(unknown)} (typo?)")
    for key in ("market", "name", "locales", "age_rating", "pricing", "legal"):
        _require(key in raw, where, f"missing required key '{key}'")

    code = str(raw["market"])
    _require(
        code.isalpha() and code.isupper() and len(code) == 2,
        where,
        f"market must be a two-letter uppercase code, got '{code}'",
    )

    locales = raw["locales"] or {}
    required = list(locales.get("required") or [])
    _require(bool(required), where, "locales.required must list at least one locale")
    fallback = dict(locales.get("fallback") or {})
    for loc in fallback:
        _require(loc in required, where, f"locales.fallback key '{loc}' is not a required locale")

    translation = raw.get("translation") or {}
    fields = list(translation.get("required_fields") or ["title", "description"])
    bad = set(fields) - VALID_FIELDS
    _require(not bad, where, f"translation.required_fields has unknown fields {sorted(bad)}")
    min_c = float(translation.get("min_completeness", 1.0))
    _require(0.0 <= min_c <= 1.0, where, "translation.min_completeness must be between 0 and 1")

    limits = raw.get("string_limits") or {}
    for fname, spec in limits.items():
        w = f"{where}: string_limits.{fname}"
        _require(
            fname in {"title", "description"}, where, f"string_limits.{fname} is not supported"
        )
        _require(
            isinstance(spec.get("max"), int) and spec["max"] > 0, w, "max must be a positive int"
        )
        spec.setdefault("unit", "chars")
        spec.setdefault("severity", "blocker")
        _require(spec["unit"] in VALID_UNITS, w, f"unit must be one of {sorted(VALID_UNITS)}")
        _require(
            spec["severity"] in VALID_SEVERITIES,
            w,
            f"severity must be one of {sorted(VALID_SEVERITIES)}",
        )

    scheme = (raw["age_rating"] or {}).get("scheme")
    _require(scheme in schemes, where, f"age_rating.scheme '{scheme}' is not defined")

    pricing = raw["pricing"] or {}
    missing = PRICING_KEYS - set(pricing)
    _require(not missing, where, f"pricing is missing {sorted(missing)}")
    _require(
        pricing["position"] in {"prefix", "suffix"},
        where,
        "pricing.position must be prefix or suffix",
    )

    links = list((raw["legal"] or {}).get("required_links") or [])
    _require(bool(links), where, "legal.required_links must not be empty")

    content = raw.get("content") or {}
    scheme_values = schemes[scheme]["values"]
    for tag, rule in content.items():
        w = f"{where}: content.{tag}"
        _require(
            isinstance(rule, dict) and rule.get("action") in VALID_CONTENT_ACTIONS,
            w,
            f"action must be one of {sorted(VALID_CONTENT_ACTIONS)}",
        )
        if rule["action"] == "min_rating":
            _require(
                str(rule.get("min")) in scheme_values,
                w,
                f"min must be a value of scheme '{scheme}': {scheme_values}",
            )
            rule["min"] = str(rule["min"])

    a11y = raw.get("accessibility") or {}
    return MarketPack(
        code=code,
        name=str(raw["name"]),
        required_locales=required,
        fallback=fallback,
        required_fields=fields,
        min_completeness=min_c,
        string_limits=limits,
        rating_scheme=scheme,
        pricing=pricing,
        required_links=links,
        content=content,
        accessibility_required=bool(a11y.get("required", False)),
        accessibility_standard=str(a11y.get("standard", "WCAG 2.0 Level AA")),
        notes=str(raw.get("notes", "")),
        source=where,
    )


def load_storefront(data_dir: Path | str) -> Storefront:
    data_dir = Path(data_dir)
    cfg = _load_yaml(data_dir / "storefront.yaml")
    catalog = _load_yaml(data_dir / "catalog.yaml")
    schemes = _load_yaml(data_dir / "rating_schemes.yaml")["schemes"]
    for sid, s in schemes.items():
        _require(bool(s.get("values")), "rating_schemes.yaml", f"scheme '{sid}' has no values")
        s["values"] = [str(v) for v in s["values"]]

    markets = []
    pack_dir = data_dir / "markets"
    for path in sorted(pack_dir.glob("*.yaml")):
        markets.append(parse_market_pack(_load_yaml(path), schemes, path.name))
    codes = [m.code for m in markets]
    dupes = {c for c in codes if codes.count(c) > 1}
    _require(not dupes, "markets/", f"duplicate market codes {sorted(dupes)}")

    apps = catalog.get("apps") or []
    ids = [a["id"] for a in apps]
    _require(len(ids) == len(set(ids)), "catalog.yaml", "duplicate app ids")

    return Storefront(
        name=cfg["name"],
        source_locale=cfg["source_locale"],
        ui_locales=list(cfg.get("ui_locales") or []),
        legal_links={k: dict(v or {}) for k, v in (cfg.get("legal_links") or {}).items()},
        apps=apps,
        schemes=schemes,
        markets=markets,
    )
