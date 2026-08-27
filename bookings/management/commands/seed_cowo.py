from datetime import time

from django.core.management.base import BaseCommand

from spaces.models import Space


class Command(BaseCommand):
    help = "Create or update the four Cowo d'la val desks."

    def handle(self, *args, **options):
        for number in range(1, 5):
            Space.objects.update_or_create(
                name=f"Desk {number}",
                defaults={
                    "description": "Cowo d'la val coworking desk",
                    "opening_time": time(6, 0),
                    "closing_time": time(21, 0),
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Four coworking desks are ready."))
