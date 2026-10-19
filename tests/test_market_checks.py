from __future__ import annotations

from storefront_readiness.checks.market import (
    check_age_rating,
    check_content,
    check_legal,
    check_locales,
    check_pricing,
    check_string_length,
    check_translation,
    display_width,
)
from storefront_readiness.models import Area, Severity


def rules(findings, severity=None):
    return [f.rule for f in findings if severity is None or f.severity is severity]


def test_display_width_counts_full_width_as_two():
    assert display_width("abc") == 3
    assert display_width("映画") == 4
    assert display_width("ＡＢ") == 4  # full-width Latin
    assert display_width("오로라") == 6


def test_missing_ui_locale_is_blocker(sf, make_pack):
    mp = make_pack(locales={"required": ["xx-XX"], "fallback": {}})
    findings = check_locales(sf, mp)
    assert [f.rule for f in findings] == ["ui_locale"]
    assert findings[0].severity is Severity.BLOCKER


def test_fallback_locale_counts_as_present(sf, make_pack):
    mp = make_pack(locales={"required": ["en-GB"], "fallback": {"en-GB": "en-US"}})
    findings, ratio = check_translation(sf, mp)
    assert ratio == 1.0
    assert not findings


def test_missing_locale_without_fallback_blocks(sf, make_pack):
    mp = make_pack(locales={"required": ["en-GB"], "fallback": {}})
    findings, ratio = check_translation(sf, mp)
    assert ratio == 0.0
    assert "listing_missing" in rules(findings, Severity.BLOCKER)
    assert "completeness_gate" in rules(findings, Severity.BLOCKER)


def test_missing_title_is_always_a_blocker(sf, make_pack):
    sf.apps[0]["listings"]["en-US"]["title"] = "  "
    mp = make_pack(translation={"required_fields": ["title"], "min_completeness": 0.0})
    findings, _ = check_translation(sf, mp)
    assert rules(findings, Severity.BLOCKER) == ["missing_title"]


def test_missing_description_is_warning_above_gate(sf, make_pack):
    del sf.apps[0]["listings"]["en-US"]["description"]
    mp = make_pack(
        translation={"required_fields": ["title", "description"], "min_completeness": 0.9}
    )
    findings, ratio = check_translation(sf, mp)
    assert 0.9 < ratio < 1.0
    assert rules(findings) == ["missing_description"]
    assert findings[0].severity is Severity.WARNING


def test_screenshot_alt_slots_follow_source_locale(sf, make_pack):
    sf.apps[0]["listings"]["en-US"]["screenshots"][1]["alt"] = ""
    mp = make_pack(translation={"required_fields": ["screenshot_alt"], "min_completeness": 0.0})
    findings, ratio = check_translation(sf, mp)
    assert rules(findings) == ["missing_screenshot_alt"]
    assert ratio == (2 * len(sf.apps) - 1) / (2 * len(sf.apps))


def test_untranslated_copy_of_source_is_flagged(sf, make_pack):
    app = sf.apps[0]
    app["listings"]["de-DE"]["description"] = app["listings"]["en-US"]["description"]
    mp = make_pack(
        locales={"required": ["de-DE"], "fallback": {}},
        translation={"required_fields": ["title"], "min_completeness": 0.0},
    )
    findings, _ = check_translation(sf, mp)
    assert rules(findings, Severity.WARNING) == ["untranslated"]


def test_string_limit_uses_display_width(sf, make_pack):
    sf.apps[0]["listings"]["ja-JP"]["title"] = "映" * 16  # 16 chars, 32 columns
    chars = make_pack(
        locales={"required": ["ja-JP"], "fallback": {}},
        string_limits={"title": {"max": 30, "unit": "chars"}},
    )
    width = make_pack(
        locales={"required": ["ja-JP"], "fallback": {}},
        string_limits={"title": {"max": 30, "unit": "display_width"}},
    )
    assert check_string_length(sf, chars) == []
    found = check_string_length(sf, width)
    assert rules(found) == ["title_max"]
    assert "32 columns" in found[0].message


def test_string_limit_severity_comes_from_pack(sf, make_pack):
    sf.apps[0]["listings"]["en-US"]["description"] = "x" * 500
    mp = make_pack(string_limits={"description": {"max": 200, "severity": "warning"}})
    found = check_string_length(sf, mp)
    assert [f.severity for f in found] == [Severity.WARNING]


def test_age_rating_missing_and_invalid(sf, make_pack):
    mp = make_pack()
    del sf.apps[0]["ratings"]["numeric-5"]
    sf.apps[1]["ratings"]["numeric-5"] = "21"
    found = check_age_rating(sf, mp)
    assert sorted(rules(found)) == ["rating_invalid", "rating_missing"]
    assert all(f.severity is Severity.BLOCKER for f in found)


def test_pricing_checks_currency_display_and_presence(sf, make_pack):
    mp = make_pack(market="US")
    paid = [a for a in sf.apps if a["pricing"] != "free"]
    paid[0]["pricing"]["US"]["display"] = "USD 9.99"
    paid[1]["pricing"]["US"]["currency"] = "EUR"
    del paid[2]["pricing"]["US"]
    found = check_pricing(sf, mp)
    assert sorted(rules(found)) == ["currency_mismatch", "price_format", "price_missing"]


def test_free_apps_skip_pricing(sf, make_pack):
    for app in sf.apps:
        app["pricing"] = "free"
    assert check_pricing(sf, make_pack()) == []


def test_legal_links_missing_and_insecure(sf, make_pack):
    sf.legal_links["ZZ"] = {"terms": "http://apps.example/zz/terms"}
    found = check_legal(sf, make_pack())
    assert sorted(f.message.split("'")[1] for f in found) == ["privacy", "terms"]
    assert any("not HTTPS" in f.message for f in found)


def test_content_block_review_and_min_rating(sf, make_pack):
    mp = make_pack(
        content={
            "loot_boxes": {"action": "block"},
            "user_generated_content": {"action": "review"},
            "alcohol": {"action": "min_rating", "min": "18"},
            "simulated_gambling": {"action": "min_rating", "min": "16"},
        }
    )
    vintner = next(a for a in sf.apps if a["id"] == "vintners-table")
    vintner["ratings"]["numeric-5"] = "16"
    found = check_content(sf, mp)
    by_rule = {f.rule: f.severity for f in found if f.area is Area.CONTENT and f.app_id}
    assert by_rule["content_loot_boxes"] is Severity.BLOCKER
    assert by_rule["content_user_generated_content"] is Severity.WARNING
    assert by_rule["content_alcohol"] is Severity.BLOCKER  # rated 16, needs 18
    assert "content_simulated_gambling" not in by_rule  # rated 18, needs 16


def test_partner_exclusion_is_info_not_blocker(sf, make_pack):
    mp = make_pack(market="KR", content={"simulated_gambling": {"action": "block"}})
    found = check_content(sf, mp)
    cardhouse = [f for f in found if f.app_id == "cardhouse-poker"]
    assert [f.severity for f in cardhouse] == [Severity.INFO]
