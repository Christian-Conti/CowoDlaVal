from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event, EventImage


class EventImageSecurityTests(TestCase):
    def test_private_image_is_not_publicly_cacheable(self):
        User = get_user_model()
        admin = User.objects.create_superuser(
            username="security-admin",
            email="security-admin@example.org",
            password="test-password-123",
        )
        event = Event.objects.create(
            title_en="Private event",
            date=timezone.localdate(),
            is_public=False,
            created_by=admin,
        )
        image = EventImage.objects.create(
            event=event,
            original_name='private"name.png',
            content_type="image/png",
            data=b"private-image",
        )

        self.client.force_login(admin)
        response = self.client.get(reverse("events:image", args=[image.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertNotIn("\n", response["Content-Disposition"])
        self.assertNotIn("\r", response["Content-Disposition"])
