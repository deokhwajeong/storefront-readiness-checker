from __future__ import annotations

import json
from pathlib import Path

import pytest

from storefront_readiness.checks.accessibility import audit_html, audit_templates
from storefront_readiness.checks.contrast import check_tokens, contrast_ratio
from storefront_readiness.models import Severity

ROOT = Path(__file__).resolve().parents[1]


def page(body: str, lang: str = ' lang="en"') -> str:
    return f"<!DOCTYPE html><html{lang}><head><title>t</title></head><body>{body}</body></html>"


def fails(html: str) -> list[str]:
    return [f.rule for f in audit_html(html) if f.severity is Severity.BLOCKER]


def advisories(html: str) -> list[str]:
    return [f.rule for f in audit_html(html) if f.severity is Severity.WARNING]


def test_clean_page_has_no_findings():
    assert audit_html(page("<main><h1>Store</h1><a href='/a'>Aurora Cinema</a></main>")) == []


@pytest.mark.parametrize("img,expected", [
    ('<img src="a.png">', ["1.1.1"]),
    ('<img src="a.png" alt="">', []),
    ('<img src="a.png" alt="Store logo">', []),
    ('<img src="a.png" role="presentation">', []),
    ('<img src="a.png" aria-hidden="true">', []),
    ('<span aria-hidden="true"><img src="a.png"></span>', []),
])  # fmt: skip
def test_alt_text(img, expected):
    assert fails(page(f"<h1>x</h1>{img}")) == expected


def test_missing_and_invalid_lang():
    assert fails(page("<h1>x</h1>", lang="")) == ["3.1.1"]
    assert fails(page("<h1>x</h1>", lang=' lang="english language"')) == ["3.1.1"]
    assert fails(page("<h1>x</h1>", lang=' lang="pt-BR"')) == []
    assert fails(page("<h1>x</h1>", lang=' lang="{{ locale }}"')) == []


@pytest.mark.parametrize("form,expected", [
    ('<input type="text" name="q">', ["1.3.1"]),
    ('<input type="text" name="q" placeholder="Search">', ["1.3.1"]),
    ('<label for="q">Search</label><input id="q" type="text">', []),
    ('<label>Search <input type="text"></label>', []),
    ('<input type="text" aria-label="Search">', []),
    ('<input type="text" aria-labelledby="h">', []),
    ('<input type="hidden" name="csrf">', []),
    ('<input type="submit" value="Go">', []),
    ('<input type="image" src="go.png">', ["1.1.1"]),
    ('<select name="c"><option>A</option></select>', ["1.3.1"]),
    ('<textarea name="m"></textarea>', ["1.3.1"]),
])  # fmt: skip
def test_form_labels(form, expected):
    assert fails(page(f"<h1>x</h1><form>{form}</form>")) == expected


def test_placeholder_hint_in_message():
    f = audit_html(page('<h1>x</h1><input name="q" placeholder="Search">'))
    assert "placeholder is not a label" in f[0].message


def test_heading_order_is_advisory():
    html = page("<h1>a</h1><h2>b</h2><h4>c</h4><h2>d</h2><h3>e</h3>")
    assert fails(html) == []
    assert advisories(html) == ["1.3.1"]
    assert advisories(page("<h2>a</h2>")) == ["1.3.1"]  # no h1


@pytest.mark.parametrize("link,fail,adv", [
    ('<a href="/x"></a>', ["2.4.4"], []),
    ('<a href="/x"><svg><path d="M0 0"/></svg></a>', ["2.4.4"], []),
    ('<a href="/x"><span aria-hidden="true">icon</span></a>', ["2.4.4"], []),
    ('<a href="/x"><img src="i.png" alt="Wishlist"></a>', [], []),
    ('<a href="/x" aria-label="Add to wishlist"><svg></svg></a>', [], []),
    ('<a href="/x">Click here</a>', [], ["2.4.4"]),
    ('<a href="/x">Read more.</a>', [], ["2.4.4"]),
    ('<a href="/x">Read more about Aurora Cinema</a>', [], []),
    ('<a name="anchor"></a>', [], []),
])  # fmt: skip
def test_link_text(link, fail, adv):
    html = page(f"<h1>x</h1>{link}")
    assert fails(html) == fail
    assert advisories(html) == adv


def test_button_name():
    assert fails(page('<h1>x</h1><button type="button"></button>')) == ["4.1.2"]
    assert fails(page('<h1>x</h1><button aria-label="Share"><svg></svg></button>')) == []
    assert fails(page("<h1>x</h1><button>Install</button>")) == []


def test_findings_carry_location_and_element():
    html = "<!DOCTYPE html>\n<html lang='en'>\n<body>\n<h1>x</h1>\n<img src='hero.png'>\n"
    (f,) = audit_html(html, "home.html")
    assert f.location == "home.html:5"
    assert f.element == "<img src='hero.png'>"


def test_contrast_ratio_reference_values():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0)
    assert contrast_ratio("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)
    assert contrast_ratio("#fff", "#000") == contrast_ratio("#000000", "#ffffff")


def test_token_pairs_respect_large_text_threshold(tmp_path):
    tokens = {
        "colors": {"bg": "#ffffff", "mid": "#888888"},  # 3.54:1
        "pairs": [
            {"name": "small", "fg": "mid", "bg": "bg"},
            {"name": "big", "fg": "mid", "bg": "bg", "large": True},
        ],
    }
    path = tmp_path / "tokens.json"
    path.write_text(json.dumps(tokens))
    found = check_tokens(path)
    assert len(found) == 1 and "'small'" in found[0].message and found[0].rule == "1.4.3"


def test_sample_templates_report_seeded_issues():
    findings, files = audit_templates(ROOT / "storefront" / "templates")
    assert files == ["account.html", "app-detail.html", "home.html", "search.html"]
    got = {(f.location.split(":")[0], f.rule, f.severity) for f in findings}
    B, W = Severity.BLOCKER, Severity.WARNING
    assert got == {
        ("home.html", "1.1.1", B),
        ("home.html", "2.4.4", W),
        ("app-detail.html", "2.4.4", B),
        ("app-detail.html", "4.1.2", B),
        ("app-detail.html", "1.3.1", W),
        ("search.html", "3.1.1", B),
        ("search.html", "1.3.1", B),
        ("search.html", "2.4.4", W),
    }
    assert not [f for f in findings if f.location.startswith("account.html")]


def test_sample_tokens_have_two_failing_pairs():
    found = check_tokens(ROOT / "storefront" / "tokens.json")
    assert sorted(f.element for f in found) == ["on-badge on badge", "price-muted on surface"]
