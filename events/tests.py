from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event, EventImage


class EventWebTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def _event(self, title, date, public=True):
        return Event.objects.create(
            title_en=title,
            date=date,
            is_public=public,
        )

    def test_list_contains_today_and_future_public_events_only(self):
        self._event("Today", self.today)
        self._event("Future", self.today + timedelta(days=1))
        self._event("Past", self.today - timedelta(days=1))
        self._event("Private", self.today, public=False)

        response = self.client.get(reverse("events:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today")
        self.assertContains(response, "Future")
        self.assertNotContains(response, "Past")
        self.assertNotContains(response, "Private")

    def test_only_superuser_can_open_create_page(self):
        User = get_user_model()
        normal = User.objects.create_user(
            username="normal",
            password="test-password",
        )
        superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.test",
            password="test-password",
        )

        self.client.force_login(normal)
        response = self.client.get(reverse("events:add"))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(superuser)
        response = self.client.get(reverse("events:add"))
        self.assertEqual(response.status_code, 200)

    def test_public_image_is_served(self):
        event = self._event("Image event", self.today)
        image = EventImage.objects.create(
            event=event,
            original_name="test.png",
            content_type="image/png",
            data=b"fake-image-data",
        )

        response = self.client.get(reverse("events:image", args=[image.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"fake-image-data")
        self.assertEqual(response["Content-Type"], "image/png")
