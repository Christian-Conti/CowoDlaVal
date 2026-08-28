from datetime import timedelta
from typing import List, Tuple

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from bookings.models import Booking
from spaces.models import Space


def get_booking_date_range(start_date, duration):
    """
    Return the inclusive start/end date range for a booking duration.

    Canonical duration values:
        half_day
        daily
        weekly
        monthly
    """
    duration = str(duration).strip().lower()

    if duration in {"half_day", "daily"}:
        return start_date, start_date

    if duration == "weekly":
        return start_date, start_date + timedelta(days=6)

    if duration == "monthly":
        return start_date, start_date + timedelta(days=29)

    raise ValidationError(
        _("Select a valid duration."),
    )




def get_overlapping_bookings(
    start_date,
    end_date,
    space_id=None,
    confirmed_only=True,
    exclude_booking_id=None,
):
    """
    Return bookings whose occupied interval intersects the requested interval.

    A booking with no end_date is treated as a one-day booking.
    """
    from django.db.models import Q

    bookings = Booking.objects.filter(date__lte=end_date).filter(
        Q(end_date__gte=start_date)
        | Q(
            end_date__isnull=True,
            date__gte=start_date,
        )
    )

    if space_id is not None:
        bookings = bookings.filter(space_id=space_id)

    if confirmed_only:
        bookings = bookings.filter(status=Booking.Status.CONFIRMED)

    if exclude_booking_id is not None:
        bookings = bookings.exclude(pk=exclude_booking_id)

    return bookings


def get_booked_dates(start_date, end_date, space_id):
    """
    Return every calendar day occupied by confirmed bookings for one space.
    """
    booked_dates = set()

    bookings = get_overlapping_bookings(
        start_date=start_date,
        end_date=end_date,
        space_id=space_id,
    )

    for booking in bookings:
        occupied_start = max(booking.date, start_date)
        occupied_end = min(booking.end_date or booking.date, end_date)

        current = occupied_start
        while current <= occupied_end:
            booked_dates.add(current)
            current += timedelta(days=1)

    return booked_dates


def get_available_spaces(start_date, end_date):
    """
    Return active spaces that are free for the complete requested interval.
    """
    available = []

    for space in Space.objects.filter(is_active=True).order_by("name"):
        if not get_overlapping_bookings(
            start_date=start_date,
            end_date=end_date,
            space_id=space.pk,
        ).exists():
            available.append(space)

    return available


def get_available_desks(start_date, end_date):
    """
    Backwards-compatible alias for callers that use desk terminology.
    """
    return get_available_spaces(start_date, end_date)


def find_available_desks(start_date, end_date):
    """
    Backwards-compatible alias for callers that use find_available_desks().
    """
    return get_available_spaces(start_date, end_date)


def _get_available_ranges(start_date, end_date, booked_dates: set) -> List[Tuple]:
    """
    Return contiguous free ranges inside an inclusive date interval.
    """
    ranges = []
    current = start_date

    while current <= end_date:
        if current in booked_dates:
            current += timedelta(days=1)
            continue

        available_start = current

        while current <= end_date and current not in booked_dates:
            current += timedelta(days=1)

        available_end = current - timedelta(days=1)
        ranges.append((available_start, available_end))

    return ranges


def suggest_split_booking(
    start_date,
    end_date,
    requested_desk_id: int,
) -> dict | None:
    """
    Return selectable alternatives when the requested desk cannot cover the
    complete period. This function only computes options; it never books them.
    """
    requested_space = Space.objects.filter(
        pk=requested_desk_id,
        is_active=True,
    ).first()

    if requested_space is None:
        return None

    if not get_overlapping_bookings(
        start_date=start_date,
        end_date=end_date,
        space_id=requested_desk_id,
    ).exists():
        return None

    options = []

    for space in Space.objects.filter(is_active=True).order_by("name"):
        booked_dates = get_booked_dates(
            start_date=start_date,
            end_date=end_date,
            space_id=space.pk,
        )

        for available_start, available_end in _get_available_ranges(
            start_date,
            end_date,
            booked_dates,
        ):
            days = (available_end - available_start).days + 1
            option_id = (
                f"{space.pk}:"
                f"{available_start.isoformat()}:"
                f"{available_end.isoformat()}"
            )

            options.append(
                {
                    "option_id": option_id,
                    "space": space,
                    "space_id": space.pk,
                    "desk": space,
                    "desk_id": space.pk,
                    "start_date": available_start,
                    "end_date": available_end,
                    "days": days,
                }
            )

    if not options:
        return None

    options.sort(
        key=lambda option: (
            -option["days"],
            option["space"].name,
            option["start_date"],
        )
    )

    return {
        "original_period": (start_date, end_date),
        "requested_space": requested_space,
        "requested_desk": requested_space,
        "options": options,
        "split_options": options,
    }


