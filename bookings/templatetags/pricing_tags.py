from django import template

from bookings.pricing import get_booking_prices


register = template.Library()


@register.simple_tag
def booking_price(tariff_category, duration):
    prices = get_booking_prices()
    amount = prices[str(tariff_category)][str(duration)]
    return f"{amount:.2f}".rstrip("0").rstrip(".")
