from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import translation


SUPPORTED_EVENT_LANGUAGES = ("it", "en", "de", "fr")


class Event(models.Model):
    title_it = models.CharField(max_length=180, blank=True)
    title_en = models.CharField(max_length=180, blank=True)
    title_de = models.CharField(max_length=180, blank=True)
    title_fr = models.CharField(max_length=180, blank=True)

    short_description_it = models.CharField(max_length=320, blank=True)
    short_description_en = models.CharField(max_length=320, blank=True)
    short_description_de = models.CharField(max_length=320, blank=True)
    short_description_fr = models.CharField(max_length=320, blank=True)

    description_it = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    description_de = models.TextField(blank=True)
    description_fr = models.TextField(blank=True)

    date = models.DateField(db_index=True)
    time = models.TimeField(blank=True, null=True)
    location = models.CharField(max_length=220, blank=True)
    is_public = models.BooleanField(default=True, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("date", "time", "pk")

    def __str__(self):
        return self.display_title or f"Event #{self.pk}"

    def get_absolute_url(self):
        return reverse("events:detail", kwargs={"pk": self.pk})

    def _localized_value(self, prefix):
        language = (translation.get_language() or "en").split("-", 1)[0]
        if language not in SUPPORTED_EVENT_LANGUAGES:
            language = "en"

        values = {
            code: getattr(self, f"{prefix}_{code}", "")
            for code in SUPPORTED_EVENT_LANGUAGES
        }

        return (
            values.get(language)
            or values.get("en")
            or values.get("it")
            or values.get("de")
            or values.get("fr")
            or ""
        )

    @property
    def display_title(self):
        return self._localized_value("title")

    @property
    def display_short_description(self):
        return self._localized_value("short_description")

    @property
    def display_description(self):
        return self._localized_value("description")

    @property
    def cover_image(self):
        return self.images.order_by("position", "pk").first()


class EventImage(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="images",
    )
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    data = models.BinaryField(editable=False)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position", "pk")

    def __str__(self):
        return f"{self.event}: {self.original_name}"
