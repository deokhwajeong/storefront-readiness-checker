from __future__ import annotations

import copy
from pathlib import Path

import pytest

from storefront_readiness.loader import Storefront, load_storefront, parse_market_pack

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def sample() -> Storefront:
    return load_storefront(ROOT / "data")


@pytest.fixture
def sf(sample: Storefront) -> Storefront:
    """A deep copy that individual tests may mutate."""
    return copy.deepcopy(sample)


@pytest.fixture
def schemes(sample: Storefront) -> dict:
    return sample.schemes


def minimal_pack(**overrides) -> dict:
    pack = {
        "market": "ZZ",
        "name": "Testland",
        "locales": {"required": ["en-US"], "fallback": {}},
        "translation": {"required_fields": ["title", "description"], "min_completeness": 1.0},
        "string_limits": {"title": {"max": 30}},
        "age_rating": {"scheme": "numeric-5"},
        "pricing": {
            "currency": "USD",
            "symbol": "$",
            "position": "prefix",
            "space": False,
            "decimal": ".",
            "group": ",",
            "decimals": 2,
        },
        "legal": {"required_links": ["terms", "privacy"]},
        "content": {},
        "accessibility": {"required": False},
    }
    pack.update(overrides)
    return pack


@pytest.fixture
def make_pack(schemes):
    def _make(**overrides):
        return parse_market_pack(minimal_pack(**overrides), schemes, "test.yaml")

    return _make
