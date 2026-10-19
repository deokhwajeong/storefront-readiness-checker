"""Command line entry point.

storefront-readiness check   [--data data] [--templates storefront/templates]
                             [--tokens storefront/tokens.json] [--market DE ...]
                             [--format md|json] [--out FILE] [--fail-on-blocked]
storefront-readiness a11y    FILE_OR_DIR ... [--tokens tokens.json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks.accessibility import audit_html, audit_templates
from .checks.contrast import check_tokens
from .loader import RulePackError, load_storefront
from .models import Finding, Severity
from .scorecard import A11Y_DISCLAIMER, evaluate, to_json, to_markdown


def run_accessibility(paths: list[Path], tokens: Path | None) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    checked: list[str] = []
    for p in paths:
        if p.is_dir():
            f, names = audit_templates(p)
            findings += f
            checked += names
        else:
            findings += audit_html(p.read_text(encoding="utf-8"), p.name)
            checked.append(p.name)
    if tokens:
        findings += check_tokens(tokens)
        checked.append(tokens.name)
    return findings, checked


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        sf = load_storefront(args.data)
    except (RulePackError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    a11y, checked = run_accessibility(
        [Path(args.templates)], Path(args.tokens) if args.tokens else None
    )
    report = evaluate(sf, a11y, checked, as_of=args.as_of, markets=args.market)
    text = to_json(report) if args.format == "json" else to_markdown(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"{len(report.go)} go, {len(report.blocked)} blocked -> {args.out}")
    else:
        print(text)
    return 1 if args.fail_on_blocked and report.blocked else 0


def _cmd_a11y(args: argparse.Namespace) -> int:
    findings, checked = run_accessibility(
        [Path(p) for p in args.paths], Path(args.tokens) if args.tokens else None
    )
    for f in findings:
        kind = "FAIL" if f.severity is Severity.BLOCKER else "advisory"
        print(f"{kind:8} {f.rule:6} {f.location}  {f.message}\n         {f.element}")
    fails = sum(f.severity is Severity.BLOCKER for f in findings)
    print(f"\nchecked {len(checked)} file(s): {fails} fail, {len(findings) - fails} advisory")
    print(A11Y_DISCLAIMER)
    if args.strict:
        return 1 if findings else 0
    return 1 if fails else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="storefront-readiness", description="Per-market launch readiness for a storefront."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="score every market and write a scorecard")
    c.add_argument("--data", default="data", help="directory with catalog, packs, schemes")
    c.add_argument("--templates", default="storefront/templates")
    c.add_argument("--tokens", default="storefront/tokens.json")
    c.add_argument("--market", action="append", help="limit to market code (repeatable)")
    c.add_argument("--format", choices=["md", "json"], default="md")
    c.add_argument("--out", help="write to file instead of stdout")
    c.add_argument("--as-of", help="report date (default: today)")
    c.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="exit 1 if any market is blocked (for CI gating)",
    )
    c.set_defaults(func=_cmd_check)

    a = sub.add_parser("a11y", help="run only the accessibility checks on HTML files")
    a.add_argument("paths", nargs="+")
    a.add_argument("--tokens")
    a.add_argument("--strict", action="store_true", help="advisories also fail")
    a.set_defaults(func=_cmd_a11y)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
