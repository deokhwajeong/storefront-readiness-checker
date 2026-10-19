"""Catalog checks evaluated per market.

Each function takes the storefront and one market pack and returns findings.
They are intentionally independent so a launch lead can read one function and
know exactly what "translation complete" or "pricing ready" means.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from ..loader import MarketPack, Storefront
from ..models import Area, Finding, Severity
from ..pricing import format_price

B, W, INFO = Severity.BLOCKER, Severity.WARNING, Severity.INFO


def apps_for_market(sf: Storefront, mp: MarketPack) -> tuple[list[dict], list[dict]]:
    """Split the catalog into apps targeted at this market and apps the partner excluded."""
    listed, withheld = [], []
    for app in sf.apps:
        (withheld if mp.code in (app.get("exclude_markets") or []) else listed).append(app)
    return listed, withheld


def resolve_listing(app: dict, locale: str, mp: MarketPack) -> tuple[dict | None, str | None]:
    """Return (listing, locale actually used), honoring the pack's fallback map."""
    listings = app.get("listings") or {}
    if locale in listings:
        return listings[locale], locale
    fb = mp.fallback.get(locale)
    if fb and fb in listings:
        return listings[fb], fb
    return None, None


def display_width(text: str) -> int:
    """Columns a string occupies on a TV tile: wide and full-width characters count as two."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def measure(text: str, unit: str) -> int:
    return display_width(text) if unit == "display_width" else len(text)


# --------------------------------------------------------------------------- locales


def check_locales(sf: Storefront, mp: MarketPack) -> list[Finding]:
    out = []
    for loc in mp.required_locales:
        if loc not in sf.ui_locales:
            out.append(
                Finding(
                    Area.LOCALES,
                    B,
                    f"Storefront UI is not translated into {loc}",
                    market=mp.code,
                    locale=loc,
                    rule="ui_locale",
                )
            )
    return out


# --------------------------------------------------------------------------- translation


@dataclass
class Completeness:
    present: int = 0
    required: int = 0

    @property
    def ratio(self) -> float:
        return 1.0 if self.required == 0 else self.present / self.required


def check_translation(sf: Storefront, mp: MarketPack) -> tuple[list[Finding], float]:
    """Field-level completeness across every listed app and required locale.

    A missing title is always a blocker (an app cannot be listed without one).
    Other gaps are warnings individually, and become a single blocker when the
    market's completeness drops below the pack's gate.
    """
    out: list[Finding] = []
    comp = Completeness()
    listed, _ = apps_for_market(sf, mp)
    src_lang = sf.source_locale.split("-")[0]

    for app in listed:
        source = (app.get("listings") or {}).get(sf.source_locale) or {}
        n_shots = len(source.get("screenshots") or [])
        for loc in mp.required_locales:
            listing, used = resolve_listing(app, loc, mp)
            fields_required = _field_slots(mp.required_fields, n_shots)
            comp.required += len(fields_required)
            if listing is None:
                out.append(
                    Finding(
                        Area.TRANSLATION,
                        B,
                        f"No {loc} listing (and no allowed fallback)",
                        market=mp.code,
                        app_id=app["id"],
                        locale=loc,
                        rule="listing_missing",
                    )
                )
                continue
            for slot in fields_required:
                value = _slot_value(listing, slot)
                if value:
                    comp.present += 1
                    continue
                sev = B if slot == "title" else W
                out.append(
                    Finding(
                        Area.TRANSLATION,
                        sev,
                        f"Missing {slot} in {used}",
                        market=mp.code,
                        app_id=app["id"],
                        locale=loc,
                        rule=f"missing_{slot.split('[')[0]}",
                    )
                )
            # Copy-paste fallback: identical to the source string in a different language.
            if (
                used == loc
                and loc.split("-")[0] != src_lang
                and listing.get("description")
                and listing.get("description") == source.get("description")
            ):
                out.append(
                    Finding(
                        Area.TRANSLATION,
                        W,
                        f"{loc} description is identical to {sf.source_locale}; "
                        "likely untranslated",
                        market=mp.code,
                        app_id=app["id"],
                        locale=loc,
                        rule="untranslated",
                    )
                )

    if comp.ratio < mp.min_completeness:
        out.append(
            Finding(
                Area.TRANSLATION,
                B,
                f"Translation completeness {comp.ratio:.1%} is below the "
                f"{mp.min_completeness:.0%} gate ({comp.required - comp.present} "
                f"of {comp.required} required strings missing)",
                market=mp.code,
                rule="completeness_gate",
            )
        )
    return out, comp.ratio


def _field_slots(fields: list[str], n_shots: int) -> list[str]:
    slots = []
    for f in fields:
        if f == "screenshot_alt":
            slots += [f"screenshot_alt[{i}]" for i in range(n_shots)]
        else:
            slots.append(f)
    return slots


def _slot_value(listing: dict, slot: str) -> str:
    if slot.startswith("screenshot_alt["):
        idx = int(slot[len("screenshot_alt[") : -1])
        shots = listing.get("screenshots") or []
        return (shots[idx].get("alt") or "").strip() if idx < len(shots) else ""
    return (listing.get(slot) or "").strip()


# --------------------------------------------------------------------------- string length


def check_string_length(sf: Storefront, mp: MarketPack) -> list[Finding]:
    out = []
    listed, _ = apps_for_market(sf, mp)
    for app in listed:
        for loc in mp.required_locales:
            listing, used = resolve_listing(app, loc, mp)
            if not listing:
                continue
            for fname, spec in mp.string_limits.items():
                text = listing.get(fname) or ""
                n = measure(text, spec["unit"])
                if n > spec["max"]:
                    unit = "columns" if spec["unit"] == "display_width" else "characters"
                    out.append(
                        Finding(
                            Area.STRING_LENGTH,
                            Severity(spec["severity"]),
                            f"{fname} is {n} {unit} in {used}; limit is {spec['max']}",
                            market=mp.code,
                            app_id=app["id"],
                            locale=loc,
                            rule=f"{fname}_max",
                            element=text[:80],
                        )
                    )
    return out


# --------------------------------------------------------------------------- age rating


def check_age_rating(sf: Storefront, mp: MarketPack) -> list[Finding]:
    out = []
    scheme = sf.schemes[mp.rating_scheme]
    listed, _ = apps_for_market(sf, mp)
    for app in listed:
        value = (app.get("ratings") or {}).get(mp.rating_scheme)
        if value is None:
            out.append(
                Finding(
                    Area.AGE_RATING,
                    B,
                    f"No rating in the market's scheme ({mp.rating_scheme})",
                    market=mp.code,
                    app_id=app["id"],
                    rule="rating_missing",
                )
            )
        elif str(value) not in scheme["values"]:
            out.append(
                Finding(
                    Area.AGE_RATING,
                    B,
                    f"Rating '{value}' is not a valid {mp.rating_scheme} value",
                    market=mp.code,
                    app_id=app["id"],
                    rule="rating_invalid",
                )
            )
    return out


# --------------------------------------------------------------------------- pricing


def check_pricing(sf: Storefront, mp: MarketPack) -> list[Finding]:
    out = []
    fmt = mp.pricing
    listed, _ = apps_for_market(sf, mp)
    for app in listed:
        pricing = app.get("pricing", "free")
        if pricing == "free":
            continue
        price: dict[str, Any] | None = pricing.get(mp.code)
        if not price:
            out.append(
                Finding(
                    Area.PRICING,
                    B,
                    "Paid app has no price for this market",
                    market=mp.code,
                    app_id=app["id"],
                    rule="price_missing",
                )
            )
            continue
        if price.get("currency") != fmt["currency"]:
            out.append(
                Finding(
                    Area.PRICING,
                    B,
                    f"Currency {price.get('currency')} does not match "
                    f"market currency {fmt['currency']}",
                    market=mp.code,
                    app_id=app["id"],
                    rule="currency_mismatch",
                )
            )
            continue
        expected = format_price(price["amount"], fmt)
        if price.get("display") != expected:
            out.append(
                Finding(
                    Area.PRICING,
                    B,
                    f"Price display '{price.get('display')}' should be '{expected}'",
                    market=mp.code,
                    app_id=app["id"],
                    rule="price_format",
                    element=str(price.get("display")),
                )
            )
    return out


# --------------------------------------------------------------------------- legal links


def check_legal(sf: Storefront, mp: MarketPack) -> list[Finding]:
    out = []
    links = sf.legal_links.get(mp.code, {})
    for kind in mp.required_links:
        url = (links.get(kind) or "").strip()
        if not url:
            out.append(
                Finding(
                    Area.LEGAL,
                    B,
                    f"Required legal link '{kind}' is not published",
                    market=mp.code,
                    rule=f"link_{kind}",
                )
            )
        elif not url.startswith("https://"):
            out.append(
                Finding(
                    Area.LEGAL,
                    B,
                    f"Legal link '{kind}' is not HTTPS: {url}",
                    market=mp.code,
                    rule=f"link_{kind}",
                    element=url,
                )
            )
    return out


# --------------------------------------------------------------------------- content rules


def check_content(sf: Storefront, mp: MarketPack) -> list[Finding]:
    out = []
    order = sf.schemes[mp.rating_scheme]["values"]
    listed, withheld = apps_for_market(sf, mp)
    for app in listed:
        for tag in app.get("content_tags") or []:
            rule = mp.content.get(tag)
            if not rule:
                continue
            action = rule["action"]
            if action == "block":
                out.append(
                    Finding(
                        Area.CONTENT,
                        B,
                        f"Content tag '{tag}' is restricted in this market; remove "
                        "the app from availability or record a policy exception",
                        market=mp.code,
                        app_id=app["id"],
                        rule=f"content_{tag}",
                    )
                )
            elif action == "review":
                out.append(
                    Finding(
                        Area.CONTENT,
                        W,
                        f"Content tag '{tag}' requires regional policy review before launch",
                        market=mp.code,
                        app_id=app["id"],
                        rule=f"content_{tag}",
                    )
                )
            elif action == "min_rating":
                value = str((app.get("ratings") or {}).get(mp.rating_scheme, ""))
                if value in order and order.index(value) < order.index(rule["min"]):
                    out.append(
                        Finding(
                            Area.CONTENT,
                            B,
                            f"Content tag '{tag}' requires rating {rule['min']} or "
                            f"higher; app is rated {value}",
                            market=mp.code,
                            app_id=app["id"],
                            rule=f"content_{tag}",
                        )
                    )
    for app in withheld:
        out.append(
            Finding(
                Area.CONTENT,
                INFO,
                "Partner excluded this app from the market",
                market=mp.code,
                app_id=app["id"],
                rule="partner_exclusion",
            )
        )
    return out


MARKET_CHECKS = (
    check_locales,
    check_string_length,
    check_age_rating,
    check_pricing,
    check_legal,
    check_content,
)
