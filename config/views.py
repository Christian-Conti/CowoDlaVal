import logging
import smtplib

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from bookings.models import Booking
from spaces.models import Space

from .forms import ContactForm

logger = logging.getLogger(__name__)


def home(request):
    selected_date = parse_date(request.GET.get("date", "")) or timezone.localdate()
    if selected_date < timezone.localdate():
        selected_date = timezone.localdate()

    spaces = list(Space.objects.filter(is_active=True).order_by("name")[:4])
    confirmed_bookings = Booking.objects.filter(
        space__in=spaces,
        status=Booking.Status.CONFIRMED,
        date=selected_date,
    ).select_related("user")
    bookings_by_space_id = {booking.space_id: booking for booking in confirmed_bookings}

    occupied_space_ids = set(bookings_by_space_id)
    for space in spaces:
        booking = bookings_by_space_id.get(space.id)
        if booking is None:
            space.booked_by_name = ""
            continue

        full_name = booking.user.get_full_name().strip()
        space.booked_by_name = full_name or booking.user.get_username()

    return render(
        request,
        "home.html",
        {
            "spaces": spaces,
            "selected_date": selected_date,
            "occupied_space_ids": occupied_space_ids,
            "today": timezone.localdate(),
            "contact_email": settings.CONTACT_EMAIL,
        },
    )


@require_http_methods(["GET", "POST"])
def contact(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {
            "name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
        }

    form = ContactForm(request.POST or None, initial=initial if request.method == "GET" else None)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["website"]:
            return redirect("contact")

        sender_name = form.cleaned_data["name"]
        sender_email = form.cleaned_data["email"]
        body = _("Information request from %(name)s (%(email)s):\n\n%(message)s") % {
            "name": sender_name,
            "email": sender_email,
            "message": form.cleaned_data["message"],
        }
        email = EmailMessage(
            subject=_("Cowo d'la val - information request"),
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_EMAIL],
            reply_to=[sender_email],
        )
        try:
            sent = email.send(fail_silently=False)
        except (OSError, smtplib.SMTPException):
            logger.exception("Unable to send contact-form email")
            sent = 0

        if sent:
            messages.success(request, _("Your message has been sent. We will reply as soon as possible."))
            return redirect("contact")

        messages.error(
            request,
            _("We could not send your message. Please try again later or contact us by email."),
        )

    return render(
        request,
        "contact/contact.html",
        {"form": form, "contact_email": settings.CONTACT_EMAIL},
    )
