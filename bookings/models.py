from datetime import datetime, timedelta
import secrets
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from spaces.models import Space


def generate_booking_code() -> str:
    return f"COWO-{timezone.localdate().year}-{secrets.token_hex(6).upper()}"


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", _("Confirmed")
        CANCELLED = "cancelled", _("Cancelled")

    class TariffCategory(models.TextChoices):
        STANDARD = "standard", _("Standard")
        DISCOUNTED = "discounted", _("Student / resident")

    class PaymentMethod(models.TextChoices):
        UNSELECTED = "", _("Not selected")
        ONSITE = "onsite", _("Pay in person")
        SATISPAY = "satispay", _("Satispay")
        PAYPAL = "paypal", _("PayPal")
        STRIPE = "stripe", _("Credit/debit card")

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", _("Unpaid")
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")
        CANCELLED = "cancelled", _("Cancelled")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="bookings")
    booking_code = models.CharField(max_length=32, unique=True, default=generate_booking_code, editable=False)
    date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # For multi-day bookings
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    tariff_category = models.CharField(
        max_length=20,
        choices=TariffCategory.choices,
        default=TariffCategory.STANDARD,
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR", editable=False)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    language = models.CharField(max_length=10, default="it")
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    confirmation_sent_at = models.DateTimeField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "space__name"]
        indexes = [
            models.Index(fields=["date", "status"], name="bookings_date_status_idx"),
            models.Index(fields=["user", "date"], name="bookings_user_date_idx"),
            models.Index(fields=["payment_method", "payment_status"], name="bookings_payment_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["space", "date"],
                condition=Q(status="confirmed"),
                name="unique_confirmed_booking_per_desk_date",
            ),
            models.CheckConstraint(condition=Q(amount__gte=0), name="booking_amount_nonnegative"),
        ]

    def __str__(self) -> str:
        if self.end_date and self.end_date != self.date:
            return f"{self.booking_code} - {self.space} - {self.date:%Y-%m-%d} to {self.end_date:%Y-%m-%d}"
        return f"{self.booking_code} - {self.space} - {self.date:%Y-%m-%d}"

    def clean(self):
        if self.date and self.date < timezone.localdate():
            raise ValidationError({"date": _("You cannot book a past date.")})
        if self.end_date and self.end_date < self.date:
            raise ValidationError({"end_date": _("End date must be after or equal to start date.")})


    @property
    def can_user_modify(self) -> bool:
        return self.can_user_cancel

    @property
    def payment_due(self) -> bool:
        return self.payment_method == self.PaymentMethod.ONSITE and self.payment_status == self.PaymentStatus.UNPAID

    @property
    def payment_reference(self) -> str:
        payment = self.payments.filter(status=Payment.Status.PAID).order_by("-paid_at").first()
        if payment is None:
            return ""
        return payment.transaction_id or payment.external_id or payment.checkout_id


    @property
    def cancellation_deadline(self):
        """
        Return the deadline for autonomous cancellation.

        Onsite bookings can be cancelled autonomously until
        12 hours before the desk opening time.
        """
        booking_start = datetime.combine(
            self.date,
            self.space.opening_time,
        )

        booking_start = timezone.make_aware(
            booking_start,
            timezone.get_current_timezone(),
        )

        return booking_start - timedelta(hours=12)

    @property
    def can_user_cancel(self):
        """
        Return whether the customer can autonomously cancel the booking.
        """
        if self.status != self.Status.CONFIRMED:
            return False

        if self.payment_method != self.PaymentMethod.ONSITE:
            return False

        return timezone.now() < self.cancellation_deadline

    @property
    def cancellation_penalty_applies(self):
        """
        Return whether the autonomous cancellation window has closed.
        """
        if self.status != self.Status.CONFIRMED:
            return False

        if self.payment_method != self.PaymentMethod.ONSITE:
            return False

        return timezone.now() >= self.cancellation_deadline

    @property
    def cancellation_penalty_amount(self):
        """
        Return the 50 percent late-cancellation charge.
        """
        return self.amount / 2


class Payment(models.Model):
    class Provider(models.TextChoices):
        SATISPAY = "satispay", _("Satispay")
        PAYPAL = "paypal", _("PayPal")
        STRIPE = "stripe", _("Credit/debit card")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")
        CANCELLED = "cancelled", _("Cancelled")

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    external_id = models.CharField(max_length=255, blank=True)
    checkout_id = models.CharField(max_length=255, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)
    provider_status = models.CharField(max_length=64, blank=True)
    provider_metadata = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                condition=~Q(external_id=""),
                name="unique_provider_external_payment",
            ),
            models.UniqueConstraint(
                fields=["provider", "checkout_id"],
                condition=~Q(checkout_id=""),
                name="unique_provider_checkout",
            ),
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.booking.booking_code} - {self.get_provider_display()} - {self.get_status_display()}"
