"""WCAG 2.0 contrast ratio for design-token color pairs (success criterion 1.4.3).

The checker does not try to infer which colors end up next to each other in a
rendered page; that requires a browser and still misses images and gradients.
Instead the design system declares the foreground/background pairs it uses,
and every declared pair is verified. Undeclared combinations are a gap that
manual review has to cover.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Area, Finding, Severity

AA_NORMAL = 4.5
AA_LARGE = 3.0  # 18pt regular or 14pt bold and larger


def _channel(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def parse_hex(color: str) -> tuple[int, int, int]:
    h = color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError(f"not a hex color: {color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(color: str) -> float:
    r, g, b = (_channel(c) for c in parse_hex(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def check_tokens(path: Path | str) -> list[Finding]:
    """Check every declared pair in a tokens JSON file.

    Format: {"colors": {"name": "#hex"}, "pairs": [{"name", "fg", "bg", "large"?}]}
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    colors = data.get("colors", {})
    out = []
    for pair in data.get("pairs", []):
        fg, bg = colors[pair["fg"]], colors[pair["bg"]]
        ratio = contrast_ratio(fg, bg)
        need = AA_LARGE if pair.get("large") else AA_NORMAL
        if ratio < need:
            size = "large text" if pair.get("large") else "normal text"
            out.append(
                Finding(
                    Area.ACCESSIBILITY,
                    Severity.BLOCKER,
                    f"Token pair '{pair['name']}' ({pair['fg']} {fg} on {pair['bg']} {bg}) has "
                    f"contrast {ratio:.2f}:1; {size} needs {need}:1",
                    rule="1.4.3",
                    location=path.name,
                    element=f"{pair['fg']} on {pair['bg']}",
                )
            )
    return out
