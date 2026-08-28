from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from spaces.models import Space

from .models import Booking, Payment
from .services import (
    cancel_booking,
    create_booking,
    mark_payment_failed,
    mark_payment_paid,
    prepare_online_payment,
    select_onsite_payment,
)


class BookingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", email="user@example.org")
        self.other_user = User.objects.create_user(username="other", email="other@example.org")
        self.space = Space.objects.create(name="Desk 1")
        self.tomorrow = timezone.localdate() + timedelta(days=1)

    def create(self, user=None):
        return create_booking(
            user=user or self.user,
            space_id=self.space.id,
            booking_date=self.tomorrow,
        )

    def test_booking_code_is_human_readable_and_unique(self):
        first = self.create()
        second_space = Space.objects.create(name="Desk 2")
        second = create_booking(
            user=self.other_user,
            space_id=second_space.id,
            booking_date=self.tomorrow,
        )

        self.assertRegex(first.booking_code, r"^COWO-\d{4}-[0-9A-F]{12}$")
        self.assertNotEqual(first.booking_code, second.booking_code)

    def test_prevent_duplicate_booking_for_same_desk_and_date(self):
        self.create()
        with self.assertRaises(ValidationError):
            self.create(self.other_user)

    def test_database_constraint_prevents_double_booking(self):
        self.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(
                user=self.other_user,
                space=self.space,
                date=self.tomorrow,
                amount="8.00",
            )

    def test_allow_same_date_on_different_desk(self):
        second_space = Space.objects.create(name="Desk 2")
        self.create()
        second = create_booking(
            user=self.other_user,
            space_id=second_space.id,
            booking_date=self.tomorrow,
        )
        self.assertEqual(second.space_id, second_space.id)

    def test_onsite_booking_can_be_cancelled(self):
        booking = self.create()
        with self.captureOnCommitCallbacks(execute=True):
            select_onsite_payment(booking=booking, user=self.user)
        cancel_booking(booking=booking, user=self.user)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_cancelled_booking_releases_desk(self):
        booking = self.create()
        with self.captureOnCommitCallbacks(execute=True):
            select_onsite_payment(booking=booking, user=self.user)
        cancel_booking(booking=booking, user=self.user)
        replacement = self.create(self.other_user)
        self.assertEqual(replacement.status, Booking.Status.CONFIRMED)

    def test_paid_online_booking_cannot_be_cancelled(self):
        booking = self.create()
        payment = prepare_online_payment(booking=booking, user=self.user, provider=Payment.Provider.STRIPE)
        with self.captureOnCommitCallbacks(execute=True):
            mark_payment_paid(payment=payment, provider_status="paid", transaction_id="transaction-reference")
        booking.refresh_from_db()

        with self.assertRaises(ValidationError):
            cancel_booking(booking=booking, user=self.user)

    def test_cancellation_url_rejects_online_booking(self):
        booking = self.create()
        prepare_online_payment(booking=booking, user=self.user, provider=Payment.Provider.PAYPAL)
        self.client.force_login(self.user)
        response = self.client.post(reverse("booking_cancel", kwargs={"pk": booking.pk}))
        booking.refresh_from_db()

        self.assertRedirects(response, reverse("booking_detail", kwargs={"pk": booking.pk}))
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)


class PaymentAndEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payer",
            email="payer@example.org",
            first_name="Test",
            last_name="User",
        )
        self.space = Space.objects.create(name="Desk 1")
        self.booking = create_booking(
            user=self.user,
            space_id=self.space.pk,
            booking_date=timezone.localdate() + timedelta(days=1),
            language="en",
        )

    def test_onsite_selection_sends_confirmation_and_leaves_payment_due(self):
        with self.captureOnCommitCallbacks(execute=True):
            select_onsite_payment(booking=self.booking, user=self.user)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.payment_status, Booking.PaymentStatus.UNPAID)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.booking.booking_code, mail.outbox[0].body)
        self.assertIn(reverse("booking_detail", kwargs={"pk": self.booking.pk}), mail.outbox[0].body)

    def test_unpaid_online_booking_does_not_send_final_receipt(self):
        prepare_online_payment(booking=self.booking, user=self.user, provider=Payment.Provider.PAYPAL)
        self.assertEqual(mail.outbox, [])

    def test_verified_online_payment_transitions_once_and_sends_receipt(self):
        payment = prepare_online_payment(
            booking=self.booking,
            user=self.user,
            provider=Payment.Provider.STRIPE,
        )
        with self.captureOnCommitCallbacks(execute=True):
            paid = mark_payment_paid(
                payment=payment,
                provider_status="paid",
                transaction_id="transaction-reference",
            )
        with self.captureOnCommitCallbacks(execute=True):
            repeated = mark_payment_paid(
                payment=payment,
                provider_status="paid",
                transaction_id="transaction-reference",
            )
        self.booking.refresh_from_db()

        self.assertEqual(paid.status, Payment.Status.PAID)
        self.assertEqual(repeated.pk, paid.pk)
        self.assertEqual(self.booking.payment_status, Booking.PaymentStatus.PAID)
        self.assertEqual(len(mail.outbox), 1)

    def test_paid_payment_cannot_be_downgraded_by_late_failure(self):
        payment = prepare_online_payment(
            booking=self.booking,
            user=self.user,
            provider=Payment.Provider.SATISPAY,
        )
        with self.captureOnCommitCallbacks(execute=True):
            mark_payment_paid(payment=payment, provider_status="ACCEPTED")
        mark_payment_failed(payment=payment, provider_status="CANCELED")
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)

    def test_verified_amount_must_match_booking_snapshot(self):
        payment = prepare_online_payment(
            booking=self.booking,
            user=self.user,
            provider=Payment.Provider.PAYPAL,
        )
        Payment.objects.filter(pk=payment.pk).update(amount="7.00")
        payment.refresh_from_db()
        with self.assertRaises(ValidationError):
            mark_payment_paid(payment=payment, provider_status="COMPLETED")

    def test_terminal_dashboard_non_interactive_output(self):
        output = StringIO()
        call_command(
            "bookings_dashboard",
            selected_date=self.booking.date.isoformat(),
            no_color=True,
            stdout=output,
        )
        self.assertIn(self.booking.booking_code, output.getvalue())
        self.assertIn(str(self.space), output.getvalue())

    def test_dashboard_manages_onsite_payment_and_booking_state(self):
        select_onsite_payment(booking=self.booking, user=self.user)
        call_command("bookings_dashboard", mark_paid=self.booking.booking_code, stdout=StringIO())
        call_command("bookings_dashboard", cancel_booking=self.booking.booking_code, stdout=StringIO())
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.payment_status, Booking.PaymentStatus.PAID)
        self.assertIsNotNone(self.booking.paid_at)
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_dashboard_prevents_conflicting_confirmation(self):
        call_command("bookings_dashboard", cancel_booking=self.booking.booking_code, stdout=StringIO())
        create_booking(
            user=self.user,
            space_id=self.space.pk,
            booking_date=self.booking.date,
        )

        with self.assertRaises(CommandError):
            call_command("bookings_dashboard", confirm_booking=self.booking.booking_code)

    def test_booking_detail_and_payment_pages_render(self):
        self.client.force_login(self.user)
        detail = self.client.get(reverse("booking_detail", kwargs={"pk": self.booking.pk}))
        payment = self.client.get(reverse("booking_payment", kwargs={"pk": self.booking.pk}))
        booking_list = self.client.get(reverse("booking_list"))

        self.assertContains(detail, self.booking.booking_code)
        self.assertContains(payment, self.booking.booking_code)
        self.assertContains(payment, "payment-option-paypal")
        self.assertContains(payment, "payment-option-stripe")
        self.assertContains(booking_list, 'data-label="')

    def test_booking_admin_changelist_loads(self):
        admin_user = User.objects.create_superuser(username="admin", email="admin@example.org")
        self.client.force_login(admin_user)
        response = self.client.get(reverse("admin:bookings_booking_changelist"))
        self.assertContains(response, self.booking.booking_code)
