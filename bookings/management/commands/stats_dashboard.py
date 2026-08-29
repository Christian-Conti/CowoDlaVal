from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dashboard statistiche prenotazioni (GUI o CLI)."

    def add_arguments(self, parser):
        parser.add_argument("--gui", action="store_true", help="Apri la GUI.")
        parser.add_argument("--cli", action="store_true", help="Mostra la CLI.")
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--all", action="store_true", dest="all_time")
        parser.add_argument("--trend", action="store_true")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        if options["gui"] and options["cli"]:
            raise SystemExit("Usa solo uno tra --gui e --cli.")

        if options["gui"]:
            call_command("stats_dashboard_gui")
            return

        argv = ["--days", str(options["days"])]
        if options["all_time"]:
            argv.append("--all")
        if options["trend"]:
            argv.append("--trend")
        if options["json"]:
            argv.append("--json")
        call_command("stats_cli", *argv)
