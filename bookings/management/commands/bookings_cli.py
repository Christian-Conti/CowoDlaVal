from django.core.management import call_command
from django.core.management.base import BaseCommand

from config.cli_ui import CLI


class Command(BaseCommand):
    help = "Interactive Cowo d'la val bookings CLI."

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            nargs="?",
            choices=[
                "list",
                "confirm",
                "paid",
                "cancel",
            ],
        )

        parser.add_argument(
            "code",
            nargs="?",
        )

    def handle(self, *args, **options):
        self.ui = CLI()

        action = options.get("action")
        code = options.get("code")

        if action:
            self.run_action(
                action,
                code,
            )
            return

        self.menu()

    def menu(self):
        while True:
            self.ui.header(
                "Bookings · CLI"
            )

            self.ui.option(
                "1",
                "List bookings",
            )

            self.ui.option(
                "2",
                "Confirm booking",
                "primary",
            )

            self.ui.option(
                "3",
                "Mark booking as paid",
                "success",
            )

            self.ui.option(
                "4",
                "Cancel booking",
                "danger",
            )

            self.ui.option(
                "0",
                "Exit",
            )

            self.ui.write()

            choice = self.ui.prompt(
                "Select an option"
            )

            actions = {
                "1": "list",
                "2": "confirm",
                "3": "paid",
                "4": "cancel",
            }

            if choice in {
                "0",
                "q",
                "quit",
                "exit",
                "",
            }:
                return

            action = actions.get(
                choice
            )

            if not action:
                self.ui.warning(
                    "Invalid selection."
                )
                self.ui.pause()
                continue

            self.run_action(
                action,
                None,
            )

            self.ui.pause()

    def get_code(self, supplied=None):
        if supplied:
            return supplied

        return self.ui.prompt(
            "Booking code"
        )

    def run_action(self, action, code):
        if action == "list":
            self.ui.section(
                "Bookings"
            )

            try:
                call_command(
                    "bookings_dashboard",
                )
            except Exception as exc:
                self.ui.error(
                    str(exc)
                )

            return

        code = self.get_code(code)

        if not code:
            self.ui.warning(
                "No booking code supplied."
            )
            return

        if action == "confirm":
            self.confirm_booking(code)
            return

        if action == "paid":
            self.mark_paid(code)
            return

        if action == "cancel":
            self.cancel_booking(code)
            return

    def confirm_booking(self, code):
        if not self.ui.confirm(
            f"Confirm booking {code}?"
        ):
            self.ui.info(
                "Operation cancelled."
            )
            return

        try:
            call_command(
                "bookings_dashboard",
                "--confirm-booking",
                code,
            )

            self.ui.success(
                f"Booking {code} confirmed."
            )

        except Exception as exc:
            self.ui.error(
                str(exc)
            )

    def mark_paid(self, code):
        if not self.ui.confirm(
            f"Mark booking {code} as paid?"
        ):
            self.ui.info(
                "Operation cancelled."
            )
            return

        try:
            call_command(
                "bookings_dashboard",
                "--mark-paid",
                code,
            )

            self.ui.success(
                f"Booking {code} marked as paid."
            )

        except Exception as exc:
            self.ui.error(
                str(exc)
            )

    def cancel_booking(self, code):
        self.ui.warning(
            "This operation cancels the booking."
        )

        if not self.ui.confirm(
            f"Cancel booking {code}?"
        ):
            self.ui.info(
                "Operation cancelled."
            )
            return

        try:
            call_command(
                "bookings_dashboard",
                "--cancel-booking",
                code,
            )

            self.ui.success(
                f"Booking {code} cancelled."
            )

        except Exception as exc:
            self.ui.error(
                str(exc)
            )
