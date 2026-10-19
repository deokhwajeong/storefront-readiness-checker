"""Reference price formatter driven by a market pack's pricing block.

Deliberately simple: one symbol, prefix or suffix, fixed decimals, a single
grouping separator every three digits. Real storefronts should use CLDR data;
this formatter exists so a rule pack can state the expected display shape and
the checker can compare partner-supplied strings against it.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def format_price(amount: float | int | str, fmt: dict[str, Any]) -> str:
    decimals = int(fmt["decimals"])
    q = Decimal(1).scaleb(-decimals) if decimals else Decimal(1)
    value = Decimal(str(amount)).quantize(q, rounding=ROUND_HALF_UP)
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):f}".partition(".")

    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    number = fmt["group"].join(groups)
    if decimals:
        number += fmt["decimal"] + frac.ljust(decimals, "0")

    gap = " " if fmt.get("space") else ""
    if fmt["position"] == "prefix":
        return f"{sign}{fmt['symbol']}{gap}{number}"
    return f"{sign}{number}{gap}{fmt['symbol']}"
