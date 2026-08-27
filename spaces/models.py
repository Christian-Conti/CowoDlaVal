from datetime import time

from django.db import models
from django.utils.translation import gettext as _


class Space(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    opening_time = models.TimeField(default=time(6, 0))
    closing_time = models.TimeField(default=time(21, 0))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        if self.name.startswith("Desk "):
            number = self.name.removeprefix("Desk ")
            if number.isdigit():
                return _("Desk %(number)s") % {"number": number}
        return self.name
