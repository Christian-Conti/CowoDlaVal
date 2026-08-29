import sys

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import models


class Command(BaseCommand):
    help = "List and create Cowo d'la val events."

    SKIP = object()

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            nargs="?",
            choices=["list", "add"],
            help="List events or create a new event.",
        )

    def handle(self, *args, **options):
        self.Event = apps.get_model("events", "Event")

        action = options["action"]

        if action == "list":
            self.list_events()
            return

        if action == "add":
            self.add_event()
            return

        if sys.stdin.isatty():
            self.menu()
        else:
            self.list_events()

    def menu(self):
        while True:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "Cowo d'la val - Events CLI"
                )
            )
            self.stdout.write("")
            self.stdout.write("  1. List events")
            self.stdout.write("  2. Add event")
            self.stdout.write("  0. Exit")
            self.stdout.write("")

            choice = input("Select an option: ").strip().lower()

            if choice == "1":
                self.list_events()

            elif choice == "2":
                self.add_event()

            elif choice in {"0", "q", "quit", "exit"}:
                return

            else:
                self.stdout.write(
                    self.style.WARNING("Invalid selection.")
                )

    def list_events(self):
        events = self.Event.objects.all()

        date_field = self.find_field(
            "date",
            "event_date",
            "start_date",
        )

        title_field = self.find_field(
            "title_it",
            "title",
            "name",
        )

        location_field = self.find_field(
            "location",
            "place",
            "venue",
        )

        public_field = self.find_field(
            "is_public",
            "public",
            "published",
        )

        ordering = []

        if date_field:
            ordering.append(date_field.name)

        if ordering:
            events = events.order_by(*ordering)

        if not events.exists():
            self.stdout.write("No events.")
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("Events")
        )

        for event in events:
            data = [f"ID {event.pk}"]

            if date_field:
                data.append(
                    str(getattr(event, date_field.name, ""))
                )

            if title_field:
                data.append(
                    str(getattr(event, title_field.name, ""))
                )

            if location_field:
                location = getattr(
                    event,
                    location_field.name,
                    "",
                )

                if location:
                    data.append(str(location))

            if public_field:
                public = getattr(
                    event,
                    public_field.name,
                    False,
                )

                data.append(
                    "public" if public else "private"
                )

            self.stdout.write(" | ".join(data))

    def add_event(self):
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("Add event")
        )
        self.stdout.write("")

        event = self.Event()

        for field in self.editable_fields():
            value = self.prompt_field(field)

            if value is self.SKIP:
                continue

            setattr(event, field.name, value)

        try:
            event.full_clean()

        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for name, messages in exc.message_dict.items():
                    for message in messages:
                        self.stderr.write(
                            f"{name}: {message}"
                        )
            else:
                for message in exc.messages:
                    self.stderr.write(message)

            raise CommandError(
                "Event was not saved."
            ) from exc

        event.save()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Event {event.pk} created successfully."
            )
        )

    def editable_fields(self):
        fields = []

        for field in self.Event._meta.fields:
            if field.primary_key:
                continue

            if not field.editable:
                continue

            if isinstance(
                field,
                (
                    models.FileField,
                    models.ImageField,
                ),
            ):
                continue

            fields.append(field)

        priority = [
            "date",
            "event_date",
            "start_date",
            "time",
            "event_time",
            "location",
            "place",
            "venue",
            "is_public",
            "public",
            "published",
            "title_it",
            "title_en",
            "title_de",
            "title_fr",
            "title",
            "short_description_it",
            "short_description_en",
            "short_description_de",
            "short_description_fr",
            "description_it",
            "description_en",
            "description_de",
            "description_fr",
        ]

        order = {
            name: index
            for index, name in enumerate(priority)
        }

        fields.sort(
            key=lambda field: (
                order.get(field.name, 1000),
                field.name,
            )
        )

        return fields

    def prompt_field(self, field):
        label = str(field.verbose_name)

        default = self.field_default(field)

        required = (
            not field.blank
            and not field.null
            and default is self.SKIP
        )

        while True:
            suffix = ""

            if default is not self.SKIP:
                suffix = f" [{default}]"

            elif not required:
                suffix = " [optional]"

            raw = input(
                f"{label} ({field.name}){suffix}: "
            ).strip()

            if not raw:
                if default is not self.SKIP:
                    return default

                if not required:
                    if field.null:
                        return None

                    if isinstance(
                        field,
                        (
                            models.CharField,
                            models.TextField,
                        ),
                    ):
                        return ""

                    return self.SKIP

                self.stdout.write(
                    self.style.WARNING(
                        "This field is required."
                    )
                )
                continue

            try:
                return self.convert_value(
                    field,
                    raw,
                )

            except (
                ValidationError,
                ValueError,
                TypeError,
            ) as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"Invalid value: {exc}"
                    )
                )

    def convert_value(self, field, raw):
        if isinstance(field, models.BooleanField):
            value = raw.lower()

            if value in {
                "1",
                "true",
                "yes",
                "y",
                "si",
                "sì",
                "s",
            }:
                return True

            if value in {
                "0",
                "false",
                "no",
                "n",
            }:
                return False

            raise ValueError("Use yes/no.")

        if isinstance(field, models.ForeignKey):
            model = field.remote_field.model

            try:
                return model.objects.get(pk=raw)

            except model.DoesNotExist as exc:
                raise ValueError(
                    f"{model.__name__} ID {raw} does not exist."
                ) from exc

        return field.to_python(raw)

    def field_default(self, field):
        if not field.has_default():
            return self.SKIP

        value = field.get_default()

        if value is None:
            return self.SKIP

        return value

    def find_field(self, *names):
        fields = {
            field.name: field
            for field in self.Event._meta.fields
        }

        for name in names:
            if name in fields:
                return fields[name]

        return None
