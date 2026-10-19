"""End-to-end: the sample storefront produces the expected go / blocked calls."""

from __future__ import annotations

import json

import pytest

from storefront_readiness.cli import main, run_accessibility
from storefront_readiness.models import Severity
from storefront_readiness.scorecard import evaluate, to_json, to_markdown

from .conftest import ROOT

EXPECTED_BLOCKED = {"CA", "DE", "GB", "JP", "KR", "NL", "SA", "US"}


@pytest.fixture(scope="module")
def report(sample):
    a11y, files = run_accessibility(
        [ROOT / "storefront" / "templates"], ROOT / "storefront" / "tokens.json"
    )
    return evaluate(sample, a11y, files, as_of="2026-10-19")


def blockers(report, code):
    m = next(m for m in report.markets if m.market == code)
    return {f.rule for f in m.blockers}


def test_go_and_blocked_split(report):
    assert {m.market for m in report.blocked} == EXPECTED_BLOCKED
    assert len(report.go) == 8


@pytest.mark.parametrize("code,rule", [
    ("CA", "completeness_gate"),
    ("DE", "title_max"),
    ("DE", "link_imprint"),
    ("JP", "price_format"),
    ("KR", "rating_missing"),
    ("NL", "content_loot_boxes"),
    ("SA", "listing_missing"),
    ("SA", "content_alcohol"),
    ("US", "a11y_gate"),
    ("GB", "a11y_gate"),
])  # fmt: skip
def test_seeded_blockers_are_caught(report, code, rule):
    assert rule in blockers(report, code)


def test_accessibility_gate_only_blocks_where_required(report):
    for m in report.markets:
        gate = [f for f in m.findings if f.rule == "a11y_gate"]
        assert len(gate) == 1
        expected = Severity.BLOCKER if m.market in {"US", "CA", "GB", "NL"} else Severity.WARNING
        assert gate[0].severity is expected, m.market


def test_warnings_do_not_block(report):
    br = next(m for m in report.markets if m.market == "BR")
    assert br.status == "go"
    assert any(f.rule == "content_simulated_gambling" for f in br.warnings)
    fr = next(m for m in report.markets if m.market == "FR")
    assert fr.status == "go" and any(f.rule == "description_max" for f in fr.warnings)


def test_translation_completeness_values(report):
    by = {m.market: m.translation_completeness for m in report.markets}
    assert by["CA"] == 0.95
    assert by["SA"] == pytest.approx(2 / 3, abs=1e-4)
    assert by["IN"] == 0.975  # below 100% but above the 97% gate
    assert by["US"] == 1.0


def test_json_shape(report):
    data = json.loads(to_json(report))
    assert data["summary"] == {
        "markets": 16,
        "go": 8,
        "blocked": 8,
        "accessibility_failures": 7,
        "accessibility_advisories": 3,
    }
    jp = next(m for m in data["markets"] if m["market"] == "JP")
    assert jp["status"] == "blocked"
    assert jp["blockers_by_area"] == {"pricing": 1}
    assert "manual review" in data["accessibility"]["disclaimer"].lower()


def test_markdown_lists_reasons_and_disclaimers(report):
    md = to_markdown(report)
    assert "**8 of 16 markets are go**" in md
    assert "Price display '¥600.00' should be '¥600'" in md
    assert "Manual review" in md and "not legal advice" in md
    assert chr(0x2014) not in md and chr(0x2013) not in md  # no em or en dashes


def test_cli_writes_json_and_gates(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    out = tmp_path / "s.json"
    assert main(["check", "--format", "json", "--out", str(out), "--as-of", "2026-10-19"]) == 0
    assert json.loads(out.read_text())["as_of"] == "2026-10-19"
    assert main(["check", "--out", str(tmp_path / "s.md"), "--fail-on-blocked"]) == 1
    assert (
        main(["check", "--market", "MX", "--out", str(tmp_path / "mx.md"), "--fail-on-blocked"])
        == 0
    )


def test_cli_a11y_subcommand(capsys):
    assert main(["a11y", str(ROOT / "storefront/templates/account.html")]) == 0
    assert main(["a11y", str(ROOT / "storefront/templates/search.html")]) == 1
    assert "manual review" in capsys.readouterr().out.lower()


def test_cli_reports_bad_pack(tmp_path, capsys):
    import shutil

    shutil.copytree(ROOT / "data", tmp_path / "data")
    (tmp_path / "data/markets/zz.yaml").write_text("market: zz\n")
    assert main(["check", "--data", str(tmp_path / "data")]) == 2
    assert "zz.yaml" in capsys.readouterr().err
