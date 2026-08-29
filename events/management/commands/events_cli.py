import sys

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import models

from config.cli_ui import CLI


class Command(BaseCommand):
    help = "Interactive Cowo d'la val events CLI."

    SKIP = object()

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            nargs="?",
            choices=[
                "list",
                "add",
            ],
        )

    def handle(self, *args, **options):
        self.Event = apps.get_model(
            "events",
            "Event",
        )

        self.ui = CLI()

        action = options.get(
            "action"
        )

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
            self.ui.header(
                "Events · CLI"
            )

            self.ui.option(
                "1",
                "List events",
            )

            self.ui.option(
                "2",
                "Add event",
                "success",
            )

            self.ui.option(
                "0",
                "Exit",
            )

            self.ui.write()

            choice = self.ui.prompt(
                "Select an option"
            )

            if choice == "1":
                self.list_events()
                self.ui.pause()

            elif choice == "2":
                self.add_event()
                self.ui.pause()

            elif choice in {
                "0",
                "q",
                "quit",
                "exit",
                "",
            }:
                return

            else:
                self.ui.warning(
                    "Invalid selection."
                )
                self.ui.pause()

    def list_events(self):
        events = self.Event.objects.all()

        date_field = self.find_field(
            "date",
            "event_date",
            "start_date",
        )

        time_field = self.find_field(
            "time",
            "event_time",
            "start_time",
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
            ordering.append(
                date_field.name
            )

        if time_field:
            ordering.append(
                time_field.name
            )

        if ordering:
            events = events.order_by(
                *ordering
            )

        self.ui.section(
            "Events"
        )

        if not events.exists():
            self.ui.empty(
                "No events."
            )
            return

        for event in events:
            title = (
                getattr(
                    event,
                    title_field.name,
                    "",
                )
                if title_field
                else str(event)
            )

            self.ui.write(
                self.ui.paint(
                    f"  #{event.pk}  {title}",
                    self.ui.BOLD,
                )
            )

            details = []

            if date_field:
                value = getattr(
                    event,
                    date_field.name,
                    None,
                )

                if value:
                    details.append(
                        str(value)
                    )

            if time_field:
                value = getattr(
                    event,
                    time_field.name,
                    None,
                )

                if value:
                    details.append(
                        str(value)
                    )

            if location_field:
                value = getattr(
                    event,
                    location_field.name,
                    None,
                )

                if value:
                    details.append(
                        str(value)
                    )

            if details:
                self.ui.write(
                    self.ui.paint(
                        "       "
                        + " · ".join(details),
                        self.ui.MUTED,
                    )
                )

            if public_field:
                public = bool(
                    getattr(
                        event,
                        public_field.name,
                        False,
                    )
                )

                if public:
                    status = self.ui.paint(
                        "PUBLIC",
                        self.ui.GREEN,
                    )
                else:
                    status = self.ui.paint(
                        "PRIVATE",
                        self.ui.YELLOW,
                    )

                self.ui.write(
                    f"       {status}"
                )

            self.ui.write()

    def add_event(self):
        self.ui.header(
            "Events · Add"
        )

        event = self.Event()

        fields = self.editable_fields()

        if not fields:
            self.ui.error(
                "No editable Event fields found."
            )
            return

        for field in fields:
            value = self.prompt_field(
                field
            )

            if value is self.SKIP:
                continue

            setattr(
                event,
                field.name,
                value,
            )

        self.ui.write()

        if not self.ui.confirm(
            "Save this event?"
        ):
            self.ui.info(
                "Event not saved."
            )
            return

        try:
            event.full_clean()
            event.save()

        except ValidationError as exc:
            self.ui.error(
                "The event is not valid."
            )

            if hasattr(
                exc,
                "message_dict",
            ):
                for field, messages in (
                    exc.message_dict.items()
                ):
                    for message in messages:
                        self.ui.write(
                            f"  {field}: {message}"
                        )
            else:
                for message in exc.messages:
                    self.ui.write(
                        f"  {message}"
                    )

            return

        self.ui.success(
            f"Event #{event.pk} created."
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

            fields.append(
                field
            )

        priority = [
            "date",
            "event_date",
            "start_date",
            "time",
            "event_time",
            "start_time",
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
            for index, name
            in enumerate(priority)
        }

        fields.sort(
            key=lambda field: (
                order.get(
                    field.name,
                    1000,
                ),
                field.name,
            )
        )

        return fields

    def prompt_field(
        self,
        field,
    ):
        label = str(
            field.verbose_name
        )

        default = self.field_default(
            field
        )

        required = (
            not field.blank
            and not field.null
            and default is self.SKIP
        )

        while True:
            if default is not self.SKIP:
                suffix = (
                    f" [{default}]"
                )
            elif required:
                suffix = " *"
            else:
                suffix = " [optional]"

            raw = self.ui.prompt(
                f"{label}{suffix}"
            )

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

                self.ui.warning(
                    "This field is required."
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
                self.ui.warning(
                    f"Invalid value: {exc}"
                )

    def convert_value(
        self,
        field,
        raw,
    ):
        if isinstance(
            field,
            models.BooleanField,
        ):
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

            raise ValueError(
                "Use yes/no."
            )

        if isinstance(
            field,
            models.ForeignKey,
        ):
            model = (
                field.remote_field.model
            )

            try:
                return model.objects.get(
                    pk=raw
                )

            except model.DoesNotExist as exc:
                raise ValueError(
                    f"{model.__name__} "
                    f"ID {raw} does not exist."
                ) from exc

        return field.to_python(
            raw
        )

    def field_default(
        self,
        field,
    ):
        if not field.has_default():
            return self.SKIP

        value = field.get_default()

        if value is None:
            return self.SKIP

        return value

    def find_field(
        self,
        *names,
    ):
        fields = {
            field.name: field
            for field
            in self.Event._meta.fields
        }

        for name in names:
            if name in fields:
                return fields[name]

        return None
