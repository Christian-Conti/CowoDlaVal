import sys
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext as _

from bookings.models import Booking
from spaces.models import Space


class Command(BaseCommand):
    help = _("View bookings and payment status by date.")

    def add_arguments(self, parser):
        parser.add_argument("--date", dest="selected_date", help=_("Show YYYY-MM-DD and exit."))
        parser.add_argument("--today", action="store_true", help=_("Show today and exit."))
        parser.add_argument("--from-date", help=_("First date in a non-interactive range."))
        parser.add_argument("--to-date", help=_("Last date in a non-interactive range."))

    def handle(self, *args, **options):
        self.use_color = sys.stdout.isatty() and not options["no_color"]
        if options["from_date"] or options["to_date"]:
            if not options["from_date"] or not options["to_date"]:
                raise CommandError(_("--from-date and --to-date must be used together."))
            start = self._parse_date(options["from_date"])
            end = self._parse_date(options["to_date"])
            if end < start:
                raise CommandError(_("--to-date cannot be earlier than --from-date."))
            current = start
            while current <= end:
                self._render_date(current)
                current += timedelta(days=1)
            return

        if options["selected_date"] or options["today"] or not sys.stdin.isatty():
            selected = self._parse_date(options["selected_date"]) if options["selected_date"] else timezone.localdate()
            self._render_date(selected)
            return

        selected = timezone.localdate()
        while True:
            self._render_date(selected)
            choice = input(_("[p]revious [n]ext [j]ump [r]ange [q]uit: ")).strip().lower()
            if choice == "q":
                return
            if choice == "p":
                selected -= timedelta(days=1)
            elif choice == "n":
                selected += timedelta(days=1)
            elif choice == "j":
                selected = self._prompt_date(_("Date (YYYY-MM-DD): "), selected)
            elif choice == "r":
                start = self._prompt_date(_("From (YYYY-MM-DD): "), selected)
                end = self._prompt_date(_("To (YYYY-MM-DD): "), start)
                if end < start:
                    self.stderr.write(_("End date must not be earlier than start date."))
                    continue
                current = start
                while current <= end:
                    self._render_date(current)
                    current += timedelta(days=1)
                input(_("Press Enter to continue..."))

    def _parse_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise CommandError(_("Dates must use YYYY-MM-DD.")) from exc

    def _prompt_date(self, prompt: str, default: date) -> date:
        value = input(prompt).strip()
        if not value:
            return default
        try:
            return date.fromisoformat(value)
        except ValueError:
            self.stderr.write(_("Invalid date; keeping the current date."))
            return default

    def _style(self, value: str, code: str) -> str:
        return f"\033[{code}m{value}\033[0m" if self.use_color else value

    def _render_date(self, selected: date) -> None:
        spaces = list(Space.objects.filter(is_active=True).order_by("name"))
        bookings = Booking.objects.filter(
            date=selected,
            status=Booking.Status.CONFIRMED,
        ).select_related("space", "user")
        by_space = {booking.space_id: booking for booking in bookings}

        self.stdout.write("")
        self.stdout.write(self._style(_("Date: %(date)s") % {"date": selected.isoformat()}, "1;34"))
        self.stdout.write("=" * 36)
        for space in spaces:
            self.stdout.write(self._style(str(space), "1"))
            booking = by_space.get(space.pk)
            if booking is None:
                self.stdout.write(f"  {self._style(_('AVAILABLE'), '32')}")
                continue

            name = booking.user.get_full_name().strip() or booking.user.get_username()
            self.stdout.write(f"  {booking.booking_code}")
            self.stdout.write(f"  {name} ({booking.user.get_username()})")
            self.stdout.write(f"  {booking.get_payment_method_display()}")
            self.stdout.write(f"  €{booking.amount} {booking.currency}")
            if booking.payment_due:
                indicator = self._style(_("PAYMENT DUE"), "1;31")
            elif booking.payment_status == Booking.PaymentStatus.PAID:
                indicator = self._style(_("PAID"), "1;32")
            else:
                indicator = self._style(booking.get_payment_status_display().upper(), "1;33")
            self.stdout.write(f"  {indicator}")
