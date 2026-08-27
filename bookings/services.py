from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from spaces.models import Space

from .models import Booking


@transaction.atomic
def create_booking(*, user, space_id, booking_date, notes="") -> Booking:
    # Lock the desk row so concurrent requests are serialized before availability is checked.
    space = Space.objects.select_for_update().get(pk=space_id, is_active=True)

    if Booking.objects.filter(
        space=space,
        date=booking_date,
        status=Booking.Status.CONFIRMED,
    ).exists():
        raise ValidationError(_("This desk is already booked for the selected date."))

    booking = Booking(
        user=user,
        space=space,
        date=booking_date,
        notes=notes,
        status=Booking.Status.CONFIRMED,
    )
    booking.full_clean()

    try:
        booking.save()
    except IntegrityError as exc:
        raise ValidationError(_("This desk is already booked for the selected date.")) from exc

    return booking


@transaction.atomic
def cancel_booking(*, booking: Booking, user) -> Booking:
    if not user.is_staff and booking.user_id != user.id:
        raise ValidationError(_("You do not have permission to cancel this booking."))

    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status", "updated_at"])
    return booking
