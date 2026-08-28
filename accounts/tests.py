from django.test import TestCase
from django.urls import reverse


class LoginTemplateTests(TestCase):
    def test_registration_button_is_shown_after_failed_login(self):
        login_url = reverse("login")

        response = self.client.get(login_url)
        self.assertContains(response, 'class="mobile-menu"')
        self.assertNotContains(response, "login-register")

        response = self.client.post(
            login_url,
            {"username": "missing-user", "password": "invalid-password"},
        )
        self.assertContains(response, "login-register")
