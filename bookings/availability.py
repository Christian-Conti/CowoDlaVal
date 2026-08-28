from datetime import timedelta
from typing import List, Tuple

from django.utils import timezone
from django.utils.translation import gettext as _

from spaces.models import Space
from .models import Booking


def get_booking_date_range(start_date, duration: str) -> Tuple[timezone.datetime.date, timezone.datetime.date]:
    """
    Calculate the end date based on the start date and duration.
    Returns (start_date, end_date)
    """
    if duration == "half_day":
        return start_date, start_date
    elif duration == "full_day":
        return start_date, start_date
    elif duration == "week":
        return start_date, start_date + timedelta(days=6)  # 7 days total
    elif duration == "month":
        return start_date, start_date + timedelta(days=29)  # 30 days total
    else:
        raise ValueError(f"Invalid duration: {duration}")


def get_available_desks_for_period(
    start_date,
    end_date,
    exclude_booking_id: int | None = None,
) -> dict:
    """
    Check availability of all desks for a given period.
    Returns a dict with:
    - fully_available: list of desks available for the entire period
    - partially_available: dict of desks with their available date ranges
    """
    desks = Space.objects.filter(is_active=True)
    fully_available = []
    partially_available = {}

    for desk in desks:
        bookings = Booking.objects.filter(
            space=desk,
            date__range=[start_date, end_date],
            status=Booking.Status.CONFIRMED,
        )
        if exclude_booking_id:
            bookings = bookings.exclude(pk=exclude_booking_id)

        if not bookings.exists():
            # Desk is fully available for the entire period
            fully_available.append(desk)
        else:
            # Check for partial availability
            booked_dates = set(b.date for b in bookings)
            available_ranges = _get_available_ranges(start_date, end_date, booked_dates)
            if available_ranges:
                partially_available[desk.id] = {
                    "desk": desk,
                    "available_ranges": available_ranges,
                }

    return {
        "fully_available": fully_available,
        "partially_available": partially_available,
    }


def _get_available_ranges(start_date, end_date, booked_dates: set) -> List[Tuple]:
    """
    Get list of available date ranges within the period, excluding booked dates.
    """
    ranges = []
    current = start_date

    while current <= end_date:
        if current not in booked_dates:
            range_start = current
            while current <= end_date and current not in booked_dates:
                current += timedelta(days=1)
            ranges.append((range_start, current - timedelta(days=1)))
        else:
            current += timedelta(days=1)

    return ranges


def suggest_split_booking(start_date, end_date, requested_desk_id: int) -> dict | None:
    """
    If the requested desk is not fully available, suggest splitting the booking
    across multiple desks for different periods.

    Returns a dict with suggested split booking or None if fully available.
    """
    requested_desk = Space.objects.get(pk=requested_desk_id)
    bookings = Booking.objects.filter(
        space=requested_desk,
        date__range=[start_date, end_date],
        status=Booking.Status.CONFIRMED,
    )

    if not bookings.exists():
        return None  # Desk is fully available

    booked_dates = set(b.date for b in bookings)
    available_ranges = _get_available_ranges(start_date, end_date, booked_dates)

    if not available_ranges:
        # No availability at all
        return None

    suggestion = {
        "original_desk": requested_desk,
        "original_period": (start_date, end_date),
        "split_options": [],
    }

    # Get all available desks for the periods
    current_period_start = start_date
    used_desks = {}

    for available_start, available_end in available_ranges:
        # For this available period, find a desk
        alternative_desks = Space.objects.filter(is_active=True).exclude(pk=requested_desk_id)
        for desk in alternative_desks:
            desk_bookings = Booking.objects.filter(
                space=desk,
                date__range=[available_start, available_end],
                status=Booking.Status.CONFIRMED,
            )
            if not desk_bookings.exists():
                suggestion["split_options"].append({
                    "desk": desk,
                    "start_date": available_start,
                    "end_date": available_end,
                    "days": (available_end - available_start).days + 1,
                })
                break

    return suggestion if suggestion["split_options"] else None
