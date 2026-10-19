from __future__ import annotations

import pytest

from storefront_readiness.pricing import format_price

USD = {
    "symbol": "$",
    "position": "prefix",
    "space": False,
    "decimal": ".",
    "group": ",",
    "decimals": 2,
}
EUR_DE = {
    "symbol": "€",
    "position": "suffix",
    "space": True,
    "decimal": ",",
    "group": ".",
    "decimals": 2,
}
BRL = {
    "symbol": "R$",
    "position": "prefix",
    "space": True,
    "decimal": ",",
    "group": ".",
    "decimals": 2,
}
JPY = {
    "symbol": "¥",
    "position": "prefix",
    "space": False,
    "decimal": ".",
    "group": ",",
    "decimals": 0,
}


@pytest.mark.parametrize("amount,fmt,expected", [
    (4.99, USD, "$4.99"),
    (1234.5, USD, "$1,234.50"),
    (4.99, EUR_DE, "4,99 €"),
    (1299.99, EUR_DE, "1.299,99 €"),
    (24.9, BRL, "R$ 24,90"),
    (600, JPY, "¥600"),
    (13000, JPY, "¥13,000"),
    (0.005, USD, "$0.01"),  # half-up, not banker's rounding
    (1234567, JPY, "¥1,234,567"),
])  # fmt: skip
def test_format_price(amount, fmt, expected):
    assert format_price(amount, fmt) == expected
