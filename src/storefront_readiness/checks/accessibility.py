"""Static accessibility checks on storefront HTML templates.

Scope, stated plainly: these checks cover a small set of WCAG 2.0 success
criteria that can be evaluated honestly from markup alone. Passing them does
NOT mean a page conforms to WCAG 2.0. Keyboard operation, focus order, screen
reader output, captions, error handling, timing, and most of the "meaningful"
judgments (is this alt text actually useful?) need manual and assistive
technology testing. See docs/accessibility-certification-plan.md.

Checks implemented:
  1.1.1  Non-text content: <img> without an alt attribute, image inputs without alt
  1.3.1  Info and relationships: form fields without a programmatic label (fail);
         skipped heading levels or missing h1 (advisory, a best practice rather
         than a strict failure)
  2.4.4  Link purpose: links with no accessible name (fail); generic link text
         such as "click here" (advisory, since context can make it acceptable)
  3.1.1  Language of page: <html> without a valid lang attribute
  4.1.2  Name, role, value: buttons with no accessible name
  1.4.3  Contrast (minimum): see contrast.py, run against declared token pairs

Severity: "fail" findings are emitted as BLOCKER and "advisory" ones as WARNING.
The scorecard downgrades fails to WARNING for markets whose pack does not make
accessibility a launch gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from ..models import Area, Finding, Severity

GENERIC_LINK_TEXT = {
    "click here", "here", "more", "read more", "learn more", "details", "link", "this",
    "go", "click", "more info",
}  # fmt: skip
LABELABLE = {"input", "select", "textarea"}
UNLABELED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}
LANG_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


@dataclass
class _NameCollector:
    tag: str
    attrs: dict[str, str | None]
    line: int
    snippet: str
    text: list[str] = field(default_factory=list)

    def name(self) -> str:
        for key in ("aria-label", "title"):
            if (self.attrs.get(key) or "").strip():
                return (self.attrs[key] or "").strip()
        if self.attrs.get("aria-labelledby"):
            return "(aria-labelledby)"
        return " ".join("".join(self.text).split())


class _TemplateAuditor(HTMLParser):
    def __init__(self, filename: str) -> None:
        super().__init__(convert_charrefs=True)
        self.filename = filename
        self.findings: list[Finding] = []
        self.html_lang: str | None = None
        self.saw_html = False
        self.html_line = 1
        self.html_snippet = "<html>"
        self.headings: list[tuple[int, int, str]] = []
        self.open_names: list[_NameCollector] = []  # a, button, label currently open
        self.hidden_depth = 0
        self.stack: list[str] = []
        self.label_for: set[str] = set()
        self.fields: list[tuple[dict, int, str, bool]] = []  # attrs, line, snippet, wrapped

    # -- helpers ------------------------------------------------------------
    def _add(self, sev: Severity, rule: str, msg: str, line: int, snippet: str) -> None:
        self.findings.append(
            Finding(
                Area.ACCESSIBILITY,
                sev,
                msg,
                rule=rule,
                location=f"{self.filename}:{line}",
                element=snippet.strip()[:160],
            )
        )

    def _inside(self, tag: str) -> bool:
        return any(c.tag == tag for c in self.open_names)

    # -- parser callbacks -----------------------------------------------------
    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        line = self.getpos()[0]
        snippet = self.get_starttag_text() or f"<{tag}>"
        void = tag in {"img", "input", "br", "hr", "meta", "link", "source", "area", "wbr"}

        if attrs.get("aria-hidden") == "true" and not void:
            self.hidden_depth += 1
            self.stack.append(f"{tag}:hidden")
            return
        if not void:
            self.stack.append(tag)

        if tag == "html":
            self.saw_html = True
            self.html_line, self.html_snippet = line, snippet
            self.html_lang = (attrs.get("lang") or "").strip()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings.append((int(tag[1]), line, snippet))
        elif tag == "img":
            self._img(attrs, line, snippet)
        elif tag in {"a", "button"} and (tag == "button" or "href" in attrs):
            self.open_names.append(_NameCollector(tag, attrs, line, snippet))
        elif tag == "label":
            if attrs.get("for"):
                self.label_for.add(attrs["for"] or "")
            self.open_names.append(_NameCollector(tag, attrs, line, snippet))
        if tag in LABELABLE:
            self._field(tag, attrs, line, snippet)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in {"img", "input", "br", "hr", "meta", "link", "source", "area", "wbr"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        # pop to the matching open tag (tolerates sloppy nesting)
        for i in range(len(self.stack) - 1, -1, -1):
            name = self.stack[i]
            if name.split(":")[0] == tag:
                for popped in self.stack[i:]:
                    if popped.endswith(":hidden"):
                        self.hidden_depth -= 1
                del self.stack[i:]
                break
        if tag in {"a", "button", "label"}:
            for i in range(len(self.open_names) - 1, -1, -1):
                if self.open_names[i].tag == tag:
                    coll = self.open_names.pop(i)
                    if tag != "label":
                        self._close_named(coll)
                    break

    def handle_data(self, data: str) -> None:
        if self.hidden_depth:
            return
        for coll in self.open_names:
            coll.text.append(data)

    # -- individual rules ---------------------------------------------------
    def _img(self, attrs: dict, line: int, snippet: str) -> None:
        decorative = (
            attrs.get("role") in {"presentation", "none"}
            or attrs.get("aria-hidden") == "true"
            or self.hidden_depth
        )
        if "alt" not in attrs and not decorative:
            self._add(Severity.BLOCKER, "1.1.1", "Image has no alt attribute", line, snippet)
        elif attrs.get("alt") and not self.hidden_depth:
            for coll in self.open_names:
                coll.text.append(f" {attrs['alt']} ")

    def _field(self, tag: str, attrs: dict, line: int, snippet: str) -> None:
        if tag == "input":
            itype = (attrs.get("type") or "text").lower()
            if itype == "image" and not (attrs.get("alt") or "").strip():
                self._add(Severity.BLOCKER, "1.1.1", "Image button has no alt text", line, snippet)
            if itype in UNLABELED_INPUT_TYPES:
                return
        self.fields.append((attrs, line, snippet, self._inside("label")))

    def _close_named(self, coll: _NameCollector) -> None:
        name = coll.name()
        if coll.tag == "a":
            if not name:
                self._add(
                    Severity.BLOCKER,
                    "2.4.4",
                    "Link has no accessible name (no text, alt, or aria-label)",
                    coll.line,
                    coll.snippet,
                )
            elif name.lower().strip(" .!>") in GENERIC_LINK_TEXT:
                self._add(
                    Severity.WARNING,
                    "2.4.4",
                    f"Generic link text '{name}' does not describe the destination",
                    coll.line,
                    coll.snippet,
                )
        elif coll.tag == "button" and not name:
            self._add(
                Severity.BLOCKER, "4.1.2", "Button has no accessible name", coll.line, coll.snippet
            )

    def finish(self) -> list[Finding]:
        self.close()
        if self.saw_html and not self.html_lang:
            self._add(
                Severity.BLOCKER,
                "3.1.1",
                "<html> element has no lang attribute",
                self.html_line,
                self.html_snippet,
            )
        elif (
            self.saw_html
            and "{{" not in (self.html_lang or "")
            and not LANG_RE.match(self.html_lang or "")
        ):
            # A template placeholder such as {{ locale }} is accepted; the rendered
            # value is the localization pipeline's responsibility.
            self._add(
                Severity.BLOCKER,
                "3.1.1",
                f"lang='{self.html_lang}' is not a valid language tag",
                self.html_line,
                self.html_snippet,
            )

        for attrs, line, snippet, wrapped in self.fields:
            labelled = (
                wrapped
                or (attrs.get("id") and attrs["id"] in self.label_for)
                or (attrs.get("aria-label") or "").strip()
                or attrs.get("aria-labelledby")
                or (attrs.get("title") or "").strip()
            )
            if not labelled:
                hint = " (placeholder is not a label)" if attrs.get("placeholder") else ""
                self._add(
                    Severity.BLOCKER,
                    "1.3.1",
                    f"Form field has no programmatic label{hint}",
                    line,
                    snippet,
                )

        if self.saw_html or self.headings:
            levels = [h[0] for h in self.headings]
            if self.headings and 1 not in levels:
                lvl, line, snip = self.headings[0]
                self._add(Severity.WARNING, "1.3.1", "Page has no h1 heading", line, snip)
            prev = 0
            for lvl, line, snip in self.headings:
                if prev and lvl > prev + 1:
                    self._add(
                        Severity.WARNING,
                        "1.3.1",
                        f"Heading level skips from h{prev} to h{lvl}",
                        line,
                        snip,
                    )
                prev = lvl
        return self.findings


def audit_html(html: str, filename: str = "<string>") -> list[Finding]:
    auditor = _TemplateAuditor(filename)
    auditor.feed(html)
    return auditor.finish()


def audit_templates(directory: Path | str) -> tuple[list[Finding], list[str]]:
    """Audit every .html file in a directory. Returns (findings, files checked)."""
    directory = Path(directory)
    files = sorted(directory.glob("*.html"))
    findings: list[Finding] = []
    for path in files:
        findings += audit_html(path.read_text(encoding="utf-8"), path.name)
    return findings, [p.name for p in files]
