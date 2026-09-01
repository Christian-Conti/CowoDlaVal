from urllib.parse import urlencode

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse


class ContactLocationTests(TestCase):
    @override_settings(LOCATION_ADDRESS="Test place & road 1")
    def test_contact_page_uses_configured_location(self):
        response = self.client.get(reverse("contact"))

        self.assertContains(response, "Test place &amp; road 1")
        self.assertEqual(
            response.context["map_embed_url"],
            "https://www.google.com/maps?"
            + urlencode(
                {
                    "q": "Test place & road 1",
                    "output": "embed",
                    "hl": "it",
                }
            ),
        )
        self.assertIn(
            "frame-src https://www.google.com",
            response.headers["Content-Security-Policy"],
        )

    @override_settings(LOCATION_ADDRESS="")
    def test_contact_page_hides_map_without_location(self):
        response = self.client.get(reverse("contact"))

        self.assertNotContains(response, 'class="location-map"')

    @override_settings(LOCATION_ADDRESS="Frazione Veglio")
    def test_location_section_uses_selected_language(self):
        headings = {
            "it": "Dove trovarci",
            "en": "Where to find us",
            "de": "So findest du uns",
            "fr": "Où nous trouver",
        }

        for language, heading in headings.items():
            with self.subTest(language=language):
                self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
                response = self.client.get(reverse("contact"))

                self.assertContains(response, heading)
                self.assertIn(f"hl={language}", response.context["map_embed_url"])
