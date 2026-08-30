from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse


class PublicSecurityTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_security_headers_are_present(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(
            response["X-Permitted-Cross-Domain-Policies"],
            "none",
        )

    @override_settings(RATE_LIMITS_ENABLED=True, BEHIND_PROXY=False)
    def test_login_is_rate_limited(self):
        url = reverse("login")
        for _ in range(12):
            response = self.client.post(
                url,
                {
                    "username": "missing@example.org",
                    "password": "invalid-password",
                },
                REMOTE_ADDR="203.0.113.15",
            )
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post(
            url,
            {
                "username": "missing@example.org",
                "password": "invalid-password",
            },
            REMOTE_ADDR="203.0.113.15",
        )
        self.assertEqual(response.status_code, 429)


class EmailDatabaseConstraintTests(TransactionTestCase):
    reset_sequences = True

    def test_email_is_unique_case_insensitively(self):
        User.objects.create_user(
            username="first-user",
            email="person@example.org",
            password="test-password-123",
        )

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="second-user",
                email="PERSON@example.org",
                password="test-password-123",
            )
