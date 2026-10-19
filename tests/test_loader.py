from __future__ import annotations

import pytest

from storefront_readiness.loader import RulePackError, load_storefront, parse_market_pack

from .conftest import ROOT, minimal_pack


def test_sample_data_loads(sample):
    assert len(sample.markets) == 16
    assert len(sample.apps) == 10
    assert {m.code for m in sample.markets} >= {"US", "DE", "JP", "SA", "KR", "BR"}


def test_every_pack_states_it_is_illustrative():
    for path in (ROOT / "data" / "markets").glob("*.yaml"):
        assert "Illustrative" in path.read_text(), path.name


def test_defaults_applied(schemes):
    mp = parse_market_pack(minimal_pack(), schemes, "t.yaml")
    assert mp.string_limits["title"] == {"max": 30, "unit": "chars", "severity": "blocker"}
    assert mp.accessibility_required is False


@pytest.mark.parametrize("override,message", [
    ({"locals": {}}, "unknown keys"),
    ({"market": "germany"}, "two-letter uppercase"),
    ({"age_rating": {"scheme": "nope"}}, "not defined"),
    ({"locales": {"required": []}}, "at least one locale"),
    ({"locales": {"required": ["en-US"], "fallback": {"fr-CA": "fr-FR"}}}, "not a required"),
    ({"translation": {"required_fields": ["subtitle"]}}, "unknown fields"),
    ({"translation": {"min_completeness": 1.5}}, "between 0 and 1"),
    ({"string_limits": {"title": {"max": 0}}}, "positive int"),
    ({"string_limits": {"title": {"max": 30, "unit": "bytes"}}}, "unit must be"),
    ({"string_limits": {"subtitle": {"max": 30}}}, "not supported"),
    ({"pricing": {"currency": "USD"}}, "pricing is missing"),
    ({"legal": {"required_links": []}}, "must not be empty"),
    ({"content": {"alcohol": {"action": "ban"}}}, "action must be"),
    ({"content": {"alcohol": {"action": "min_rating", "min": "21"}}}, "min must be"),
])  # fmt: skip
def test_invalid_packs_fail_loudly(schemes, override, message):
    with pytest.raises(RulePackError, match=message):
        parse_market_pack(minimal_pack(**override), schemes, "bad.yaml")


def test_error_names_the_file(schemes):
    with pytest.raises(RulePackError, match=r"^de\.yaml:"):
        parse_market_pack(minimal_pack(market="de"), schemes, "de.yaml")


def test_duplicate_market_codes_rejected(tmp_path):
    import shutil

    shutil.copytree(ROOT / "data", tmp_path / "data")
    shutil.copy(tmp_path / "data/markets/de.yaml", tmp_path / "data/markets/de-copy.yaml")
    with pytest.raises(RulePackError, match="duplicate market codes"):
        load_storefront(tmp_path / "data")
