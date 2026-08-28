import logging
import smtplib
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import Booking


logger = logging.getLogger(__name__)


def send_booking_confirmation(booking_id: int) -> bool:
    booking = Booking.objects.select_related("space", "user").get(pk=booking_id)
    if booking.confirmation_sent_at is not None or not booking.user.email:
        return False
    if booking.payment_method == Booking.PaymentMethod.ONSITE:
        if booking.payment_status != Booking.PaymentStatus.UNPAID:
            return False
    elif booking.payment_status != Booking.PaymentStatus.PAID:
        return False

    manage_path = reverse("booking_detail", kwargs={"pk": booking.pk})
    manage_url = urljoin(f"{settings.PUBLIC_BASE_URL.rstrip('/')}/", manage_path.lstrip("/"))
    with translation.override(booking.language):
        subject = _("Cowo d'la val booking %(code)s") % {"code": booking.booking_code}
        body = render_to_string(
            "bookings/email/confirmation.txt",
            {"booking": booking, "manage_url": manage_url},
        )

    try:
        EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.user.email],
        ).send(fail_silently=False)
    except (OSError, smtplib.SMTPException):
        logger.exception("Unable to send booking confirmation for %s", booking.booking_code)
        return False

    Booking.objects.filter(pk=booking.pk, confirmation_sent_at__isnull=True).update(
        confirmation_sent_at=timezone.now()
    )
    return True
