"""The demo is generated from real tool output and must pass the tool's own checks."""

from __future__ import annotations

import importlib.util
import json

from storefront_readiness.checks.accessibility import audit_html

from .conftest import ROOT


def load_build():
    spec = importlib.util.spec_from_file_location("demo_build", ROOT / "demo" / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_builds_and_passes_own_accessibility_checks(tmp_path):
    out = tmp_path / "site"
    load_build().build(out)
    assert {p.name for p in out.iterdir()} == {
        "index.html", "styles.css", "app.js", "favicon.svg", "scorecard.json", "scorecard.md",
    }  # fmt: skip
    html = (out / "index.html").read_text()
    assert audit_html(html, "index.html") == []
    assert html.count('class="tile ') == 16
    # The failing element from the sample templates is shown, escaped, in the page.
    assert "&lt;img src=&quot;{{ hero.image }}&quot; class=&quot;hero-art&quot;&gt;" in html
    summary = json.loads((out / "scorecard.json").read_text())["summary"]
    assert summary["go"] == 8 and summary["blocked"] == 8
    # Static site only: every script, stylesheet, and icon is a relative path.
    assert 'src="http' not in html
    assert 'rel="stylesheet" href="styles.css"' in html
    assert "cdn" not in html.lower()
