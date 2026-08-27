from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from spaces.models import Space


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", _("Confirmed")
        CANCELLED = "cancelled", _("Cancelled")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="bookings")
    date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "space__name"]
        indexes = [
            models.Index(fields=["date", "status"], name="bookings_date_status_idx"),
            models.Index(fields=["user", "date"], name="bookings_user_date_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["space", "date"],
                condition=Q(status="confirmed"),
                name="unique_confirmed_booking_per_desk_date",
            )
        ]

    def __str__(self) -> str:
        return f"{self.space} - {self.date:%Y-%m-%d}"

    def clean(self):
        if self.date and self.date < timezone.localdate():
            raise ValidationError({"date": _("You cannot book a past date.")})
