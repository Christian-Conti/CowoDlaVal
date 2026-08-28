from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse


class LoginTemplateTests(TestCase):
    def test_registration_button_is_shown_after_failed_login(self):
        login_url = reverse("login")

        response = self.client.get(login_url)
        self.assertContains(response, 'class="mobile-menu"')
        self.assertContains(response, reverse("password_reset"))
        self.assertNotContains(response, "login-register")

        response = self.client.post(
            login_url,
            {"username": "missing-user", "password": "invalid-password"},
        )
        self.assertContains(response, "login-register")


class PasswordManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="password-user",
            email="password@example.org",
            password="old-password-123",
        )

    def test_authenticated_user_can_change_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "old-password-123",
                "new_password1": "new-password-456",
                "new_password2": "new-password-456",
            },
        )

        self.assertRedirects(response, reverse("password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password-456"))

    def test_password_reset_sends_email(self):
        response = self.client.post(reverse("password_reset"), {"email": self.user.email})

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)
