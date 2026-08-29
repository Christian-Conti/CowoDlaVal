from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Events dashboard compatibility command."

    def add_arguments(self, parser):
        parser.add_argument("--gui", action="store_true", help="Open the desktop GUI.")
        parser.add_argument("action", nargs="?", choices=["list", "add"])

    def handle(self, *args, **options):
        if options.get("gui"):
            return call_command("events_dashboard_gui")

        action = options.get("action")
        if action:
            return call_command("events_cli", action)

        return call_command("events_cli")
