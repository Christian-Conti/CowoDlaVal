from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from bookings.models import Booking
from spaces.models import Space


def get_booking_date_range(start_date, duration):
    # Return the inclusive range for one canonical booking duration.
    duration = str(duration).strip().lower()

    if duration in {"half_day", "daily"}:
        return start_date, start_date
    if duration == "weekly":
        return start_date, start_date + timedelta(days=6)
    if duration == "monthly":
        return start_date, start_date + timedelta(days=29)

    raise ValidationError(_("Select a valid duration."))


def get_overlapping_bookings(
    start_date,
    end_date,
    space_id=None,
    confirmed_only=True,
    exclude_booking_id=None,
):
    # Return bookings whose occupied interval intersects the requested range.
    bookings = Booking.objects.filter(date__lte=end_date).filter(
        Q(end_date__gte=start_date)
        | Q(end_date__isnull=True, date__gte=start_date)
    )

    if space_id is not None:
        bookings = bookings.filter(space_id=space_id)
    if confirmed_only:
        bookings = bookings.filter(status=Booking.Status.CONFIRMED)
    if exclude_booking_id is not None:
        bookings = bookings.exclude(pk=exclude_booking_id)
    return bookings


def get_available_spaces(start_date, end_date):
    # Return active spaces free for the complete requested interval.
    return [
        space
        for space in Space.objects.filter(is_active=True).order_by("name")
        if not get_overlapping_bookings(
            start_date=start_date,
            end_date=end_date,
            space_id=space.pk,
        ).exists()
    ]


def get_booking_alternatives(
    start_date,
    end_date,
    requested_space_id: int,
) -> dict | None:
    # Return only alternative desks covering the complete original interval.
    requested_space = Space.objects.filter(
        pk=requested_space_id,
        is_active=True,
    ).first()
    if requested_space is None:
        return None

    if not get_overlapping_bookings(
        start_date=start_date,
        end_date=end_date,
        space_id=requested_space_id,
    ).exists():
        return None

    alternatives = []
    for space in Space.objects.filter(is_active=True).order_by("name"):
        if space.pk == requested_space.pk:
            continue
        if get_overlapping_bookings(
            start_date=start_date,
            end_date=end_date,
            space_id=space.pk,
        ).exists():
            continue

        alternatives.append({
            "alternative_id": f"{space.pk}:{start_date.isoformat()}:{end_date.isoformat()}",
            "space": space,
            "space_id": space.pk,
            "start_date": start_date,
            "end_date": end_date,
        })

    return {
        "original_period": (start_date, end_date),
        "requested_space": requested_space,
        "alternatives": alternatives,
    }
