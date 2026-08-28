import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.translation import gettext_lazy as _


PRICE_ENV_VARS = {
    "standard": {
        "half_day": "BOOKING_PRICE_STANDARD_HALF_DAY",
        "daily": "BOOKING_PRICE_STANDARD_DAILY",
        "weekly": "BOOKING_PRICE_STANDARD_WEEKLY",
        "monthly": "BOOKING_PRICE_STANDARD_MONTHLY",
    },
    "discounted": {
        "half_day": "BOOKING_PRICE_DISCOUNTED_HALF_DAY",
        "daily": "BOOKING_PRICE_DISCOUNTED_DAILY",
        "weekly": "BOOKING_PRICE_DISCOUNTED_WEEKLY",
        "monthly": "BOOKING_PRICE_DISCOUNTED_MONTHLY",
    },
}

DEFAULT_PRICES = {
    "standard": {
        "half_day": Decimal("5.00"),
        "daily": Decimal("8.00"),
        "weekly": Decimal("35.00"),
        "monthly": Decimal("100.00"),
    },
    "discounted": {
        "half_day": Decimal("3.00"),
        "daily": Decimal("5.00"),
        "weekly": Decimal("20.00"),
        "monthly": Decimal("50.00"),
    },
}

DURATION_ALIASES = {
    "half_day": "half_day",
    "half-day": "half_day",
    "halfday": "half_day",
    "daily": "daily",
    "day": "daily",
    "full_day": "daily",
    "full-day": "daily",
    "weekly": "weekly",
    "week": "weekly",
    "monthly": "monthly",
    "month": "monthly",
}

TWOPLACES = Decimal("0.01")


def _decimal_from_env(name: str, default: Decimal) -> Decimal:
    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = Decimal(raw_value.strip())
    except InvalidOperation as exc:
        raise ImproperlyConfigured(
            f"{name} must contain a valid decimal monetary value."
        ) from exc

    if value < 0:
        raise ImproperlyConfigured(f"{name} cannot be negative.")

    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def get_booking_prices() -> dict[str, dict[str, Decimal]]:
    prices = {}

    for tariff_category, duration_vars in PRICE_ENV_VARS.items():
        prices[tariff_category] = {}

        for duration, env_name in duration_vars.items():
            prices[tariff_category][duration] = _decimal_from_env(
                env_name,
                DEFAULT_PRICES[tariff_category][duration],
            )

    return prices


def calculate_booking_amount(
    tariff_category: str,
    duration: str,
    num_days: int = 1,
) -> Decimal:
    tariff_key = str(tariff_category)
    duration_key = DURATION_ALIASES.get(str(duration))

    prices = get_booking_prices()

    if tariff_key not in prices:
        raise ValidationError(_("Select a valid rate."))

    if duration_key is not None:
        return prices[tariff_key][duration_key]

    # Preserve compatibility with any custom multi-day duration already used
    # by the application: it is charged using the configured daily rate.
    if num_days < 1:
        raise ValidationError(_("The booking duration must be at least one day."))

    return (
        prices[tariff_key]["daily"] * Decimal(num_days)
    ).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
