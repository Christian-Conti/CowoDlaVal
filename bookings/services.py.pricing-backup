from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from spaces.models import Space

from .models import Booking, Payment
from .availability import get_booking_date_range, get_available_desks_for_period, suggest_split_booking


DAILY_RATES = {
    Booking.TariffCategory.STANDARD: Decimal("8.00"),
    Booking.TariffCategory.DISCOUNTED: Decimal("5.00"),
}


def _send_confirmation_after_commit(booking_id: int) -> None:
    from .emails import send_booking_confirmation

    transaction.on_commit(lambda: send_booking_confirmation(booking_id))


def calculate_booking_amount(tariff_category: str, duration: str, num_days: int = 1) -> Decimal:
    """
    Calculate the total booking amount based on tariff and duration.
    """
    try:
        daily_rate = DAILY_RATES[tariff_category]
    except KeyError as exc:
        raise ValidationError(_("Select a valid rate.")) from exc

    if duration == "half_day":
        return daily_rate / 2
    elif duration == "full_day":
        return daily_rate
    else:
        return daily_rate * num_days


@transaction.atomic
def create_booking(
    *,
    user,
    space_id,
    booking_date,
    duration="full_day",
    tariff_category=Booking.TariffCategory.STANDARD,
    notes="",
    language="it",
) -> Booking:
    space = Space.objects.select_for_update().get(pk=space_id, is_active=True)
    start_date, end_date = get_booking_date_range(booking_date, duration)
    num_days = (end_date - start_date).days + 1

    # Check if the desk is available for the entire period
    bookings = Booking.objects.filter(
        space=space,
        date__range=[start_date, end_date],
        status=Booking.Status.CONFIRMED,
    )
    if bookings.exists():
        raise ValidationError(
            _("This desk is not available for the entire requested period. Please check availability or try a different desk.")
        )

    try:
        amount = calculate_booking_amount(tariff_category, duration, num_days)
    except ValidationError:
        raise

    booking = Booking(
        user=user,
        space=space,
        date=start_date,
        end_date=end_date if end_date != start_date else None,
        tariff_category=tariff_category,
        amount=amount,
        currency="EUR",
        notes=notes,
        language=language,
        status=Booking.Status.CONFIRMED,
    )
    booking.full_clean()

    try:
        with transaction.atomic():
            booking.save()
    except IntegrityError as exc:
        raise ValidationError(_("This desk is already booked for the selected date.")) from exc

    return booking


@transaction.atomic
def select_onsite_payment(*, booking: Booking, user) -> Booking:
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.user_id != user.id:
        raise ValidationError(_("You do not have permission to manage this booking."))
    if booking.status != Booking.Status.CONFIRMED:
        raise ValidationError(_("This booking is no longer active."))
    if booking.payment_status == Booking.PaymentStatus.PAID:
        raise ValidationError(_("This booking has already been paid."))
    if booking.payment_method not in {Booking.PaymentMethod.UNSELECTED, Booking.PaymentMethod.ONSITE}:
        raise ValidationError(_("The payment method cannot be changed after online checkout starts."))

    first_confirmation = booking.confirmation_sent_at is None
    booking.payment_method = Booking.PaymentMethod.ONSITE
    booking.payment_status = Booking.PaymentStatus.UNPAID
    booking.save(update_fields=["payment_method", "payment_status", "updated_at"])
    if first_confirmation:
        _send_confirmation_after_commit(booking.pk)
    return booking


@transaction.atomic
def prepare_online_payment(*, booking: Booking, user, provider: str) -> Payment:
    if provider not in Payment.Provider.values:
        raise ValidationError(_("Select a valid payment method."))

    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.user_id != user.id:
        raise ValidationError(_("You do not have permission to manage this booking."))
    if booking.status != Booking.Status.CONFIRMED:
        raise ValidationError(_("This booking is no longer active."))
    if booking.payment_status == Booking.PaymentStatus.PAID:
        raise ValidationError(_("This booking has already been paid."))
    if booking.payment_method not in {Booking.PaymentMethod.UNSELECTED, provider}:
        raise ValidationError(_("The payment method cannot be changed after online checkout starts."))

    booking.payment_method = provider
    booking.payment_status = Booking.PaymentStatus.PENDING
    booking.save(update_fields=["payment_method", "payment_status", "updated_at"])
    return Payment.objects.create(
        booking=booking,
        provider=provider,
        amount=booking.amount,
        currency=booking.currency,
    )


@transaction.atomic
def mark_payment_paid(
    *,
    payment: Payment,
    provider_status: str,
    transaction_id: str = "",
    provider_metadata: dict | None = None,
) -> Payment:
    payment = Payment.objects.select_for_update().select_related("booking").get(pk=payment.pk)
    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)

    if payment.status == Payment.Status.PAID:
        return payment
    if payment.amount != booking.amount or payment.currency != booking.currency:
        raise ValidationError(_("The verified payment amount does not match the booking."))
    if booking.payment_method != payment.provider:
        raise ValidationError(_("The verified payment provider does not match the booking."))

    paid_at = timezone.now()
    payment.status = Payment.Status.PAID
    payment.provider_status = provider_status[:64]
    payment.transaction_id = transaction_id[:255]
    payment.provider_metadata = provider_metadata or {}
    payment.paid_at = paid_at
    payment.save(
        update_fields=[
            "status",
            "provider_status",
            "transaction_id",
            "provider_metadata",
            "paid_at",
            "updated_at",
        ]
    )
    booking.payment_status = Booking.PaymentStatus.PAID
    booking.paid_at = paid_at
    booking.save(update_fields=["payment_status", "paid_at", "updated_at"])
    if booking.confirmation_sent_at is None:
        _send_confirmation_after_commit(booking.pk)
    return payment


@transaction.atomic
def mark_payment_failed(*, payment: Payment, provider_status: str) -> Payment:
    payment = Payment.objects.select_for_update().select_related("booking").get(pk=payment.pk)
    if payment.status == Payment.Status.PAID:
        return payment

    payment.status = Payment.Status.FAILED
    payment.provider_status = provider_status[:64]
    payment.save(update_fields=["status", "provider_status", "updated_at"])
    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
    if booking.payment_status != Booking.PaymentStatus.PAID:
        booking.payment_status = Booking.PaymentStatus.FAILED
        booking.save(update_fields=["payment_status", "updated_at"])
    return payment


@transaction.atomic
def cancel_booking(*, booking: Booking, user) -> Booking:
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if not user.is_staff and booking.user_id != user.id:
        raise ValidationError(_("You do not have permission to cancel this booking."))
    if booking.status != Booking.Status.CONFIRMED:
        raise ValidationError(_("This booking is no longer active."))
    if not user.is_staff and not booking.can_user_cancel:
        raise ValidationError(
            _("Only bookings with payment in person can be cancelled online. Contact the coworking staff.")
        )

    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status", "updated_at"])
    return booking


@transaction.atomic
def modify_booking(
    *,
    booking: Booking,
    user,
    space_id,
    booking_date,
    duration="full_day",
    tariff_category,
    notes=""
) -> Booking:
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.user_id != user.id:
        raise ValidationError(_("You do not have permission to manage this booking."))
    if not booking.can_user_modify:
        raise ValidationError(
            _("Online-paid bookings cannot be modified automatically. Contact the coworking staff.")
        )

    space = Space.objects.select_for_update().get(pk=space_id, is_active=True)
    start_date, end_date = get_booking_date_range(booking_date, duration)
    num_days = (end_date - start_date).days + 1

    bookings = Booking.objects.filter(
        space=space,
        date__range=[start_date, end_date],
        status=Booking.Status.CONFIRMED,
    ).exclude(pk=booking.pk)
    if bookings.exists():
        raise ValidationError(_("This desk is already booked for the selected dates."))

    try:
        amount = calculate_booking_amount(tariff_category, duration, num_days)
    except ValidationError:
        raise

    booking.space = space
    booking.date = start_date
    booking.end_date = end_date if end_date != start_date else None
    booking.tariff_category = tariff_category
    booking.amount = amount
    booking.notes = notes
    booking.full_clean()
    try:
        with transaction.atomic():
            booking.save()
    except IntegrityError as exc:
        raise ValidationError(_("This desk is already booked for the selected dates.")) from exc
    return booking
