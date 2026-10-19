"""Build the static readiness demo from the tool's real output.

  python demo/build.py --out demo/dist

Steps:
  1. Run the readiness checker on the sample storefront (same code path as the CLI).
  2. Render a fully static index.html: market tile grid, per-market blockers,
     translation completeness, and accessibility findings. JavaScript only
     toggles which market panel is shown; all content is in the HTML.
  3. Write scorecard.json and scorecard.md next to it.
  4. Run the tool's own accessibility checks on the generated page and the demo
     palette. Any finding, including advisories, fails the build.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from storefront_readiness.checks.accessibility import audit_html  # noqa: E402
from storefront_readiness.checks.contrast import check_tokens  # noqa: E402
from storefront_readiness.cli import run_accessibility  # noqa: E402
from storefront_readiness.loader import load_storefront  # noqa: E402
from storefront_readiness.models import Finding, MarketResult, Severity  # noqa: E402
from storefront_readiness.scorecard import (  # noqa: E402
    A11Y_DISCLAIMER,
    AREA_LABEL,
    RULES_DISCLAIMER,
    Report,
    evaluate,
    to_json,
    to_markdown,
)

DEMO = Path(__file__).resolve().parent
REPO_URL = "https://github.com/deokhwajeong/storefront-readiness-checker"
AS_OF = "2026-10-19"

# Tile grid: (column, row). A rough geographic arrangement, not a map.
GRID = {
    "CA": (1, 1), "GB": (4, 1), "NL": (5, 1),
    "US": (1, 2), "FR": (4, 2), "DE": (5, 2), "TR": (6, 2), "KR": (8, 2), "JP": (9, 2),
    "MX": (1, 3), "ES": (4, 3), "IT": (5, 3), "SA": (6, 3), "IN": (7, 3),
    "BR": (2, 4), "AU": (9, 4),
}  # fmt: skip

# Hand-written SVG glyphs, referenced with <use>. Decorative: status is always in text too.
SVG_SPRITE = """<svg xmlns="http://www.w3.org/2000/svg" class="sprite" aria-hidden="true" focusable="false">
  <symbol id="i-go" viewBox="0 0 16 16"><path d="M3 8.5l3.2 3L13 4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></symbol>
  <symbol id="i-blocked" viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></symbol>
  <symbol id="i-warn" viewBox="0 0 16 16"><path d="M8 2.5l6 11H2z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M8 6.5v3.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="11.6" r=".9" fill="currentColor"/></symbol>
  <symbol id="i-mark" viewBox="0 0 32 32"><rect x="3" y="6" width="26" height="17" rx="2.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M11 27h10M16 23v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="7" y="10" width="5" height="4" rx="1" fill="currentColor"/><rect x="13.5" y="10" width="5" height="4" rx="1" fill="currentColor" opacity=".55"/><rect x="20" y="10" width="5" height="4" rx="1" fill="currentColor" opacity=".3"/><path d="M7 18h18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity=".55"/></symbol>
</svg>"""


def icon(name: str, cls: str = "ic") -> str:
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#i-{name}"/></svg>'


def pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".0%", "%")


def who(f: Finding) -> str:
    parts = []
    if f.app_id:
        parts.append(f'<code class="tag">{escape(f.app_id)}</code>')
    if f.locale:
        parts.append(f'<span class="loc">{escape(f.locale)}</span>')
    return " ".join(parts)


def finding_li(f: Finding, kind: str) -> str:
    element = ""
    if f.element and f.area.value in {"string_length", "pricing"}:
        element = f'<span class="el">Value: <code>{escape(f.element)}</code></span>'
    return (
        f'<li class="finding {kind}"><span class="area">{escape(AREA_LABEL[f.area])}</span>'
        f'<span class="msg">{escape(f.message)}</span>{who(f)}{element}</li>'
    )


def completeness_svg(value: float, gate: float) -> str:
    """Hand-built horizontal bar with the market's gate as a tick mark."""
    w = 200
    fill = round(w * value, 1)
    gx = round(w * gate, 1)
    cls = "ok" if value >= gate else "low"
    return (
        f'<svg class="bar" viewBox="0 0 {w} 12" preserveAspectRatio="none" aria-hidden="true" '
        f'focusable="false"><rect class="track" x="0" y="2" width="{w}" height="8" rx="4"/>'
        f'<rect class="fill {cls}" x="0" y="2" width="{fill}" height="8" rx="4"/>'
        f'<rect class="gate" x="{gx - 1}" y="0" width="2" height="12"/></svg>'
    )


def market_panel(m: MarketResult, gate: float, first: bool) -> str:
    status = "Go" if m.status == "go" else "Blocked"
    blockers = "".join(finding_li(f, "blocker") for f in m.blockers)
    market_warn = [f for f in m.warnings if not (f.rule or "").startswith("a11y_")]
    a11y_warn = [f for f in m.warnings if (f.rule or "").startswith("a11y_")]
    warnings = "".join(finding_li(f, "warning") for f in market_warn + a11y_warn)
    withheld = f"({m.apps_withheld} excluded by the partner)" if m.apps_withheld else ""
    body = []
    if m.blockers:
        body.append(
            f'<h4 class="list-h blocked-h">{icon("blocked")} Blockers ({len(m.blockers)})</h4>'
            f'<ul class="findings">{blockers}</ul>'
        )
    else:
        body.append(f'<p class="clear">{icon("go")} No blockers. This market can launch.</p>')
    if m.warnings:
        body.append(
            f'<h4 class="list-h warn-h">{icon("warn")} Warnings ({len(m.warnings)})</h4>'
            f'<ul class="findings">{warnings}</ul>'
        )
    return f"""
<article class="panel" id="m-{m.market}" data-market="{m.market}" aria-labelledby="h-{m.market}"{"" if first else ' data-hide="1"'}>
  <header class="panel-head">
    <h3 id="h-{m.market}">{escape(m.name)} <span class="code-chip">{m.market}</span></h3>
    <p class="status {m.status}">{icon("go" if m.status == "go" else "blocked")} {status}</p>
  </header>
  <dl class="facts">
    <div><dt>Translation completeness</dt><dd>{pct(m.translation_completeness)} <span class="muted">gate {pct(gate)}</span>{completeness_svg(m.translation_completeness, gate)}</dd></div>
    <div><dt>Apps listed</dt><dd>{m.apps_listed}<span class="muted">{withheld}</span></dd></div>
    <div><dt>Blockers / warnings</dt><dd>{len(m.blockers)} / {len(m.warnings)}</dd></div>
  </dl>
  {"".join(body)}
</article>"""


def tile(m: MarketResult) -> str:
    col, row = GRID[m.market]
    n = len(m.blockers)
    detail = "go" if m.status == "go" else f"blocked, {n} blocker{'s' if n != 1 else ''}"
    badge = (
        icon("go", "ic tile-ic")
        if m.status == "go"
        else f'<span class="n" aria-hidden="true">{n}</span>'
    )
    return (
        f'<li class="cell" style="grid-column:{col};grid-row:{row}">'
        f'<button type="button" class="tile {m.status}" data-market="{m.market}" '
        f'aria-controls="m-{m.market}" aria-pressed="false">'
        f'<span class="code" aria-hidden="true">{m.market}</span>{badge}'
        f'<span class="sr">{escape(m.name)}: {detail}</span></button></li>'
    )


def completeness_rows(report: Report, gates: dict[str, float]) -> str:
    rows = []
    for m in sorted(report.markets, key=lambda m: (m.translation_completeness, m.market)):
        gate = gates[m.market]
        below = m.translation_completeness < gate
        note = '<span class="below">below gate</span>' if below else ""
        rows.append(
            f'<li class="crow"><span class="cname">{m.market} <span class="muted">{escape(m.name)}</span></span>'
            f"{completeness_svg(m.translation_completeness, gate)}"
            f'<span class="cval">{pct(m.translation_completeness)} {note}</span></li>'
        )
    return "".join(rows)


def a11y_rows(findings: list[Finding]) -> str:
    rows = []
    for f in sorted(findings, key=lambda f: (f.severity is not Severity.BLOCKER, f.location or "")):
        kind = "fail" if f.severity is Severity.BLOCKER else "advisory"
        rows.append(
            f'<tr><td data-label="WCAG SC"><span class="sc">{escape(f.rule or "")}</span></td>'
            f'<td data-label="Result"><span class="res {kind}">{kind}</span></td>'
            f'<td data-label="Location"><code>{escape(f.location or "")}</code></td>'
            f'<td data-label="Finding">{escape(f.message)}</td>'
            f'<td data-label="Failing element"><code class="snippet">{escape(f.element or "")}'
            "</code></td></tr>"
        )
    return "".join(rows)


def render(report: Report, gates: dict[str, float], gated: list[str]) -> str:
    go, blocked = len(report.go), len(report.blocked)
    total = len(report.markets)
    ordered = sorted(
        report.markets, key=lambda m: (m.status != "blocked", -len(m.blockers), m.market)
    )
    first = ordered[0].market
    panels = "".join(market_panel(m, gates[m.market], m.market == first) for m in ordered)
    tiles = "".join(tile(m) for m in sorted(report.markets, key=lambda m: GRID[m.market][::-1]))
    avg = sum(m.translation_completeness for m in report.markets) / total
    fails, advis = len(report.a11y_fails), len(report.a11y_advisories)
    area_counts: dict[str, int] = {}
    for m in report.markets:
        for f in m.blockers:
            area_counts[AREA_LABEL[f.area]] = area_counts.get(AREA_LABEL[f.area], 0) + 1
    area_list = "".join(
        f'<li><span>{escape(a)}</span><span class="cnt">{n}</span></li>'
        for a, n in sorted(area_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )
    gated_txt = ", ".join(gated)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Storefront Launch Readiness</title>
<meta name="description" content="Per-market launch readiness for a fictional multi-locale app storefront, generated by storefront-readiness-checker.">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="styles.css">
</head>
<body>
{SVG_SPRITE}
<a class="skip" href="#markets">Skip to market grid</a>
<header class="top">
  <div class="wrap top-in">
    {icon("mark", "mark")}
    <div>
      <p class="eyebrow">storefront-readiness-checker</p>
      <h1>Launch readiness for {total} markets</h1>
      <p class="sub">{escape(report.storefront)}, a fictional TV app storefront. Scorecard as of {report.as_of}, generated by the tool from synthetic data with seeded defects.</p>
    </div>
  </div>
</header>
<main class="wrap">
  <section class="kpis" aria-labelledby="kpi-h">
    <h2 id="kpi-h" class="sr">Summary</h2>
    <div class="kpi"><p class="k-label">Markets go</p><p class="k-val go-t">{go}<span class="k-of"> of {total}</span></p></div>
    <div class="kpi"><p class="k-label">Markets blocked</p><p class="k-val blocked-t">{blocked}</p></div>
    <div class="kpi"><p class="k-label">Average translation completeness</p><p class="k-val">{pct(avg)}</p></div>
    <div class="kpi"><p class="k-label">Template accessibility</p><p class="k-val">{fails}<span class="k-of"> fails, {advis} advisories</span></p></div>
  </section>

  <section class="grid-sec" id="markets" aria-labelledby="markets-h">
    <div class="sec-head">
      <h2 id="markets-h">Markets</h2>
      <p class="muted">Select a market to see why it is go or blocked. Tiles are arranged roughly by geography.</p>
    </div>
    <div class="grid-layout">
      <div class="tiles-wrap">
        <ul class="tiles" aria-label="Market readiness tiles">{tiles}</ul>
        <ul class="legend" aria-label="Legend">
          <li><span class="sw go"></span>Go: no blockers</li>
          <li><span class="sw blocked"></span>Blocked: number shows blockers</li>
        </ul>
        <div class="areas">
          <h3>Blockers by area</h3>
          <ul class="area-list">{area_list}</ul>
        </div>
      </div>
      <div class="panels" id="panels">{panels}</div>
    </div>
  </section>

  <section class="comp-sec" aria-labelledby="comp-h">
    <div class="sec-head">
      <h2 id="comp-h">Translation completeness</h2>
      <p class="muted">Required strings present (title, description, screenshot alt text) across every listed app and required locale. The tick marks each market's gate; below it, the market is blocked.</p>
    </div>
    <ul class="comp">{completeness_rows(report, gates)}</ul>
  </section>

  <section class="a11y-sec" aria-labelledby="a11y-h">
    <div class="sec-head">
      <h2 id="a11y-h">Accessibility findings in storefront templates</h2>
      <p class="muted">Automated WCAG 2.0 checks on the sample templates and design tokens. Failures block launch only where the market pack makes accessibility a gate ({gated_txt}); elsewhere they are warnings.</p>
    </div>
    <p class="callout">{escape(A11Y_DISCLAIMER)}</p>
    <div class="table-scroll" role="region" aria-labelledby="a11y-h" tabindex="0">
      <table class="a11y">
        <caption class="sr">Automated accessibility findings with the failing element</caption>
        <thead><tr><th scope="col">WCAG SC</th><th scope="col">Result</th><th scope="col">Location</th><th scope="col">Finding</th><th scope="col">Failing element</th></tr></thead>
        <tbody>{a11y_rows(report.accessibility)}</tbody>
      </table>
    </div>
  </section>

  <section class="how-sec" aria-labelledby="how-h">
    <h2 id="how-h">How a market is scored</h2>
    <ol class="how">
      <li>Every market check runs against the catalog for that market: locales, translation completeness, string limits, age rating, pricing format, legal links, content rules.</li>
      <li>Accessibility checks run once on the storefront templates and design tokens.</li>
      <li>Where the market pack makes accessibility a launch gate, template failures add one blocker; otherwise one warning.</li>
      <li>Any blocker means blocked. Warnings never change status; they ship with an owner and a date.</li>
    </ol>
    <p class="downloads">Raw output from this run: <a href="scorecard.json">scorecard JSON</a> and <a href="scorecard.md">scorecard Markdown</a>. Source and rule packs: <a href="{REPO_URL}">storefront-readiness-checker on GitHub</a>.</p>
  </section>
</main>
<footer class="foot">
  <div class="wrap">
    <p>{escape(RULES_DISCLAIMER)} All apps, partners, and strings are fictional.</p>
    <p>This page passes the tool's own automated accessibility checks, which is necessary but not sufficient for conformance.</p>
  </div>
</footer>
<script src="app.js"></script>
</body>
</html>
"""


def tokens_css(tokens_path: Path) -> str:
    colors = json.loads(tokens_path.read_text())["colors"]
    lines = [f"  --{k}: {v};" for k, v in colors.items()]
    return ":root {\n" + "\n".join(lines) + "\n}\n"


def build(out: Path) -> Report:
    sf = load_storefront(ROOT / "data")
    a11y, checked = run_accessibility(
        [ROOT / "storefront" / "templates"], ROOT / "storefront" / "tokens.json"
    )
    report = evaluate(sf, a11y, checked, as_of=AS_OF)
    gates = {m.code: m.min_completeness for m in sf.markets}
    gated = [m.code for m in sf.markets if m.accessibility_required]

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    html = render(report, gates, gated)
    (out / "index.html").write_text(html, encoding="utf-8")
    css = tokens_css(DEMO / "tokens.json") + (DEMO / "static" / "styles.css").read_text()
    (out / "styles.css").write_text(css, encoding="utf-8")
    for name in ("app.js", "favicon.svg"):
        shutil.copy(DEMO / "static" / name, out / name)
    (out / "scorecard.json").write_text(to_json(report) + "\n", encoding="utf-8")
    (out / "scorecard.md").write_text(to_markdown(report), encoding="utf-8")

    # Dogfood: the demo must pass the checks it reports on, advisories included.
    own = audit_html(html, "index.html") + check_tokens(DEMO / "tokens.json")
    if own:
        for f in own:
            print(f"demo a11y: {f.rule} {f.location} {f.message} {f.element}", file=sys.stderr)
        raise SystemExit("demo page fails its own accessibility checks")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEMO / "dist"))
    args = ap.parse_args()
    out = Path(args.out).resolve()
    report = build(out)
    print(
        f"built {out}: {len(report.go)} go, {len(report.blocked)} blocked; "
        "demo passes its own accessibility checks"
    )


if __name__ == "__main__":
    main()
