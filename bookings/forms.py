from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from spaces.models import Space

from .models import Booking


class BookingForm(forms.Form):
    space = forms.ModelChoiceField(
        queryset=Space.objects.filter(is_active=True),
        label=_("Desk"),
    )
    date = forms.DateField(
        label=_("Date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    tariff_category = forms.ChoiceField(
        label=_("Rate"),
        choices=Booking.TariffCategory.choices,
    )
    notes = forms.CharField(
        label=_("Requests or notes"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": _("For example: extra monitor, projector, wood stove assistance..."),
            }
        ),
    )

    def clean_date(self):
        booking_date = self.cleaned_data["date"]
        if booking_date < timezone.localdate():
            raise ValidationError(_("You cannot book a past date."))
        return booking_date


class PaymentMethodForm(forms.Form):
    payment_method = forms.ChoiceField(
        label=_("Payment method"),
        choices=[choice for choice in Booking.PaymentMethod.choices if choice[0]],
        widget=forms.RadioSelect,
    )
