from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from spaces.models import Space

from .models import Booking
from .services import cancel_booking, create_booking


class BookingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="password12345")
        self.other_user = User.objects.create_user(username="other", password="password12345")
        self.space = Space.objects.create(name="Desk 1")
        self.tomorrow = timezone.localdate() + timedelta(days=1)

    def test_prevent_duplicate_booking_for_same_desk_and_date(self):
        create_booking(
            user=self.user,
            space_id=self.space.id,
            booking_date=self.tomorrow,
        )

        with self.assertRaises(ValidationError):
            create_booking(
                user=self.other_user,
                space_id=self.space.id,
                booking_date=self.tomorrow,
            )

    def test_allow_same_date_on_different_desk(self):
        second_space = Space.objects.create(name="Desk 2")
        create_booking(
            user=self.user,
            space_id=self.space.id,
            booking_date=self.tomorrow,
        )
        second = create_booking(
            user=self.other_user,
            space_id=second_space.id,
            booking_date=self.tomorrow,
        )

        self.assertEqual(second.space_id, second_space.id)

    def test_cancelled_booking_releases_desk(self):
        booking = create_booking(
            user=self.user,
            space_id=self.space.id,
            booking_date=self.tomorrow,
        )
        cancel_booking(booking=booking, user=self.user)
        replacement = create_booking(
            user=self.other_user,
            space_id=self.space.id,
            booking_date=self.tomorrow,
        )

        self.assertEqual(replacement.status, Booking.Status.CONFIRMED)
