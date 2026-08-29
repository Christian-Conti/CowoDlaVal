from config.gui_theme import install_unified_gui
import os
import sys
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from bookings.models import Booking
from spaces.models import Space


class BookingWindow:
    def __init__(self, command, tk, ttk, messagebox, selected_date):
        self.command = command
        self.messagebox = messagebox
        self.bookings = {}

        self.root = tk.Tk()
        install_unified_gui(self.root)
        self.root.title(_("Cowo d'la val - Bookings"))
        self.root.geometry("1400x700")
        self.root.minsize(1000, 560)

        # Normalize Tk rendering when the GUI is forwarded through X11.
        self.root.tk.call("tk", "scaling", 1.0)
        self.root.tk.call("font", "configure", "TkDefaultFont", "-size", 10)
        self.root.tk.call("font", "configure", "TkTextFont", "-size", 10)
        self.root.tk.call(
            "font",
            "configure",
            "TkHeadingFont",
            "-size",
            10,
            "-weight",
            "bold",
        )

        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=28)
        style.configure("Treeview.Heading", padding=(4, 5))

        toolbar = ttk.Frame(self.root, padding=12)
        toolbar.pack(fill="x")

        ttk.Button(
            toolbar,
            text=_("Previous day"),
            command=lambda: self.move_date(-1),
        ).pack(side="left")

        self.date_value = tk.StringVar(value=selected_date.isoformat())

        ttk.Entry(
            toolbar,
            textvariable=self.date_value,
            width=12,
        ).pack(side="left", padx=6)

        ttk.Button(
            toolbar,
            text=_("Apply date"),
            command=self.refresh,
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text=_("Next day"),
            command=lambda: self.move_date(1),
        ).pack(side="left", padx=6)

        self.summary = ttk.Label(toolbar)
        self.summary.pack(side="right", padx=(12, 0))

        table_frame = ttk.Frame(self.root, padding=(12, 0, 12, 0))
        table_frame.pack(fill="both", expand=True)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = (
            "code",
            "desk",
            "user",
            "email",
            "booking",
            "method",
            "payment",
            "amount",
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "code": (_("Booking code"), 190),
            "desk": (_("Desk"), 120),
            "user": (_("Customer"), 220),
            "email": (_("Email"), 270),
            "booking": (_("Booking"), 120),
            "method": (_("Payment method"), 150),
            "payment": (_("Payment"), 160),
            "amount": (_("Amount"), 90),
        }

        for column, (label, width) in headings.items():
            self.table.heading(column, text=label)
            self.table.column(
                column,
                width=width,
                minwidth=70,
                stretch=False,
                anchor="e" if column == "amount" else "w",
            )

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.table.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.table.xview,
        )

        self.table.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.table.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        self.table.bind("<<TreeviewSelect>>", self.load_notes)

        notes_frame = ttk.LabelFrame(
            self.root,
            text=_("Selected booking notes"),
            padding=8,
        )
        notes_frame.pack(fill="x", padx=12, pady=12)

        self.notes = tk.Text(notes_frame, height=4, wrap="word")
        self.notes.pack(fill="x")

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        actions.pack(fill="x")

        ttk.Button(
            actions,
            text=_("Confirm"),
            command=lambda: self.change_status(Booking.Status.CONFIRMED),
        ).pack(side="left")

        ttk.Button(
            actions,
            text=_("Cancel booking"),
            command=lambda: self.change_status(Booking.Status.CANCELLED),
        ).pack(side="left", padx=6)

        ttk.Button(
            actions,
            text=_("Mark paid on site"),
            command=self.mark_paid,
        ).pack(side="left")

        ttk.Button(
            actions,
            text=_("Save notes"),
            command=self.save_notes,
        ).pack(side="left", padx=6)

        ttk.Button(
            actions,
            text=_("Refresh"),
            command=self.refresh,
        ).pack(side="left")

        ttk.Button(
            actions,
            text=_("Close"),
            command=self.root.destroy,
        ).pack(side="right")

        self.refresh()

    def run(self):
        self.root.mainloop()

    def selected_code(self, warn=True):
        selection = self.table.selection()

        if not selection:
            if warn:
                self.messagebox.showinfo(
                    _("Bookings"),
                    _("Select a booking first."),
                )
            return None

        return selection[0]

    def selected_date(self):
        return self.command._parse_date(self.date_value.get())

    def move_date(self, days):
        try:
            selected = self.selected_date() + timedelta(days=days)
        except CommandError as exc:
            self.messagebox.showerror(_("Bookings"), str(exc))
            return

        self.date_value.set(selected.isoformat())
        self.refresh()

    def refresh(self):
        try:
            selected = self.selected_date()
        except CommandError as exc:
            self.messagebox.showerror(_("Bookings"), str(exc))
            return

        bookings = list(self.command._bookings_for_date(selected))

        confirmed_space_ids = {
            booking.space_id
            for booking in bookings
            if booking.status == Booking.Status.CONFIRMED
            and booking.space.is_active
        }

        active_spaces = Space.objects.filter(is_active=True).count()

        self.table.delete(*self.table.get_children())

        self.bookings = {
            booking.booking_code: booking
            for booking in bookings
        }

        for booking in bookings:
            self.table.insert(
                "",
                "end",
                iid=booking.booking_code,
                values=(
                    booking.booking_code,
                    str(booking.space),
                    self.command._user_label(booking),
                    self.command._user_email(booking),
                    booking.get_status_display(),
                    booking.get_payment_method_display(),
                    self.command._payment_label(booking),
                    f"€{booking.amount}",
                ),
            )

        self.notes.delete("1.0", "end")

        self.summary.configure(
            text=_("%(count)s bookings · %(available)s desks available")
            % {
                "count": len(bookings),
                "available": max(
                    active_spaces - len(confirmed_space_ids),
                    0,
                ),
            }
        )

    def load_notes(self, _event=None):
        code = self.selected_code(warn=False)

        if code is None:
            return

        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", self.bookings[code].notes)

    def change_status(self, status):
        code = self.selected_code()

        if code is None or not self.messagebox.askyesno(
            _("Bookings"),
            _("Set %(code)s to %(status)s?")
            % {
                "code": code,
                "status": str(Booking.Status(status).label).lower(),
            },
        ):
            return

        self._run_change(
            lambda: self.command._set_booking_status(code, status)
        )

    def mark_paid(self):
        code = self.selected_code()

        if code is None or not self.messagebox.askyesno(
            _("Bookings"),
            _("Record the on-site payment for %(code)s?")
            % {"code": code},
        ):
            return

        self._run_change(
            lambda: self.command._mark_onsite_paid(code)
        )

    def save_notes(self):
        code = self.selected_code()

        if code is None:
            return

        self._run_change(
            lambda: self.command._set_notes(
                code,
                self.notes.get("1.0", "end-1c"),
            )
        )

    def _run_change(self, change):
        try:
            change()
        except CommandError as exc:
            self.messagebox.showerror(_("Bookings"), str(exc))
            return

        self.refresh()


class Command(BaseCommand):
    help = _("View and manage bookings and payment status.")

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            "--cli",
            action="store_true",
            help=_("Force the terminal interface."),
        )
        mode.add_argument(
            "--gui",
            action="store_true",
            help=_("Force the desktop interface."),
        )

        parser.add_argument(
            "--date",
            dest="selected_date",
            help=_("Show YYYY-MM-DD and exit."),
        )
        parser.add_argument(
            "--today",
            action="store_true",
            help=_("Show today and exit."),
        )
        parser.add_argument(
            "--from-date",
            help=_("First date in a non-interactive range."),
        )
        parser.add_argument(
            "--to-date",
            help=_("Last date in a non-interactive range."),
        )

        actions = parser.add_mutually_exclusive_group()
        actions.add_argument(
            "--cancel-booking",
            metavar="CODE",
            help=_("Cancel a booking and exit."),
        )
        actions.add_argument(
            "--confirm-booking",
            metavar="CODE",
            help=_("Confirm a booking and exit."),
        )
        actions.add_argument(
            "--mark-paid",
            metavar="CODE",
            help=_("Record an on-site payment and exit."),
        )
        actions.add_argument(
            "--set-notes",
            nargs=2,
            metavar=("CODE", "TEXT"),
            help=_("Replace notes and exit."),
        )

    def handle(self, *args, **options):
        self.use_color = (
            sys.stdout.isatty()
            and not options["no_color"]
        )

        if self._handle_action(options):
            return

        if options["from_date"] or options["to_date"]:
            if options["gui"]:
                raise CommandError(
                    _("Date ranges are only available in the terminal interface.")
                )

            if not options["from_date"] or not options["to_date"]:
                raise CommandError(
                    _("--from-date and --to-date must be used together.")
                )

            start = self._parse_date(options["from_date"])
            end = self._parse_date(options["to_date"])

            if end < start:
                raise CommandError(
                    _("--to-date cannot be earlier than --from-date.")
                )

            current = start
            while current <= end:
                self._render_date(current)
                current += timedelta(days=1)

            return

        selected = (
            self._parse_date(options["selected_date"])
            if options["selected_date"]
            else timezone.localdate()
        )

        if options["gui"]:
            self._run_gui(selected, fallback=False)
            return

        requested_output = bool(
            options["selected_date"]
            or options["today"]
        )

        if (
            not options["cli"]
            and not requested_output
            and self._desktop_available()
        ):
            if self._run_gui(selected, fallback=True):
                return

        if requested_output or not sys.stdin.isatty():
            self._render_date(selected)
            return

        self._run_cli(selected)

    def _handle_action(self, options):
        if options["cancel_booking"]:
            booking = self._set_booking_status(
                options["cancel_booking"],
                Booking.Status.CANCELLED,
            )
        elif options["confirm_booking"]:
            booking = self._set_booking_status(
                options["confirm_booking"],
                Booking.Status.CONFIRMED,
            )
        elif options["mark_paid"]:
            booking = self._mark_onsite_paid(
                options["mark_paid"]
            )
        elif options["set_notes"]:
            booking = self._set_notes(
                *options["set_notes"]
            )
        else:
            return False

        self.stdout.write(
            self.style.SUCCESS(
                _("Updated %(code)s.")
                % {"code": booking.booking_code}
            )
        )
        return True

    def _desktop_available(self):
        if (
            os.environ.get("SSH_CONNECTION")
            or os.environ.get("SSH_TTY")
        ):
            return False

        return bool(
            os.environ.get("DISPLAY")
            or os.environ.get("WAYLAND_DISPLAY")
            or sys.platform in {"darwin", "win32"}
        )

    def _run_gui(self, selected, fallback):
        try:
            import tkinter as tk
            from tkinter import messagebox, ttk
        except ImportError as exc:
            return self._gui_error(exc, fallback)

        try:
            window = BookingWindow(
                self,
                tk,
                ttk,
                messagebox,
                selected,
            )
        except tk.TclError as exc:
            return self._gui_error(exc, fallback)

        window.run()
        return True

    def _gui_error(self, error, fallback):
        message = _(
            "The desktop interface could not start: %(error)s"
        ) % {"error": error}

        if not fallback:
            raise CommandError(message)

        self.stderr.write(
            self.style.WARNING(message)
        )
        return False

    def _run_cli(self, selected):
        while True:
            self._render_date(selected)

            try:
                choice = input(
                    _(
                        "[p]revious [n]ext [j]ump [r]ange "
                        "[c]ancel con[f]irm [m]ark paid "
                        "[e]dit notes [q]uit: "
                    )
                ).strip().lower()

                if choice == "q":
                    return

                if choice == "p":
                    selected -= timedelta(days=1)
                elif choice == "n":
                    selected += timedelta(days=1)
                elif choice == "j":
                    selected = self._prompt_date(
                        _("Date (YYYY-MM-DD): "),
                        selected,
                    )
                elif choice == "r":
                    self._render_range(selected)
                elif choice in {"c", "f", "m", "e"}:
                    self._interactive_change(choice)

            except EOFError:
                return
            except KeyboardInterrupt:
                self.stdout.write("")
                return

    def _render_range(self, selected):
        start = self._prompt_date(
            _("From (YYYY-MM-DD): "),
            selected,
        )
        end = self._prompt_date(
            _("To (YYYY-MM-DD): "),
            start,
        )

        if end < start:
            self.stderr.write(
                _("End date must not be earlier than start date.")
            )
            return

        current = start
        while current <= end:
            self._render_date(current)
            current += timedelta(days=1)

        input(_("Press Enter to continue..."))

    def _interactive_change(self, choice):
        code = input(_("Booking code: ")).strip()

        try:
            if choice == "c":
                booking = self._set_booking_status(
                    code,
                    Booking.Status.CANCELLED,
                )
            elif choice == "f":
                booking = self._set_booking_status(
                    code,
                    Booking.Status.CONFIRMED,
                )
            elif choice == "m":
                booking = self._mark_onsite_paid(code)
            else:
                booking = self._set_notes(
                    code,
                    input(
                        _("New notes (empty clears them): ")
                    ),
                )
        except CommandError as exc:
            self.stderr.write(
                self.style.ERROR(str(exc))
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                _("Updated %(code)s.")
                % {"code": booking.booking_code}
            )
        )

    def _parse_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise CommandError(
                _("Dates must use YYYY-MM-DD.")
            ) from exc

    def _prompt_date(self, prompt: str, default: date) -> date:
        value = input(prompt).strip()

        if not value:
            return default

        try:
            return date.fromisoformat(value)
        except ValueError:
            self.stderr.write(
                _("Invalid date; keeping the current date.")
            )
            return default

    def _style(self, value: str, code: str) -> str:
        if not self.use_color:
            return value

        return f"\033[{code}m{value}\033[0m"

    def _bookings_for_date(self, selected):
        return Booking.objects.filter(
            date__lte=selected,
        ).filter(
            Q(end_date__gte=selected)
            | Q(
                end_date__isnull=True,
                date=selected,
            )
        ).select_related(
            "space",
            "user",
        ).order_by(
            "space__name",
            "status",
        )

    def _render_date(self, selected: date) -> None:
        spaces = list(
            Space.objects.filter(
                is_active=True
            ).order_by("name")
        )

        bookings = list(
            self._bookings_for_date(selected)
        )

        confirmed = {
            booking.space_id: booking
            for booking in bookings
            if booking.status == Booking.Status.CONFIRMED
        }

        self.stdout.write("")
        self.stdout.write(
            self._style(
                _("Date: %(date)s")
                % {"date": selected.isoformat()},
                "1;34",
            )
        )
        self.stdout.write("=" * 50)

        for space in spaces:
            self.stdout.write(
                self._style(str(space), "1")
            )

            booking = confirmed.get(space.pk)

            if booking is None:
                self.stdout.write(
                    f"  {self._style(_('AVAILABLE'), '32')}"
                )
            else:
                self._render_booking(booking)

        cancelled = [
            booking
            for booking in bookings
            if booking.status == Booking.Status.CANCELLED
        ]

        if cancelled:
            self.stdout.write(
                self._style(
                    _("Cancelled bookings"),
                    "1",
                )
            )

            for booking in cancelled:
                self.stdout.write(
                    f"  {booking.space}"
                )
                self._render_booking(
                    booking,
                    indent="    ",
                )

    def _render_booking(self, booking, indent="  "):
        self.stdout.write(
            f"{indent}{booking.booking_code}"
        )
        self.stdout.write(
            f"{indent}{self._user_label(booking)}"
        )
        self.stdout.write(
            f"{indent}{_('Email')}: {self._user_email(booking)}"
        )
        self.stdout.write(
            f"{indent}{booking.get_status_display()}"
        )
        self.stdout.write(
            f"{indent}{booking.get_payment_method_display()}"
        )
        self.stdout.write(
            f"{indent}€{booking.amount} {booking.currency}"
        )

        indicator = self._payment_label(booking)

        if booking.payment_due:
            indicator = self._style(
                indicator,
                "1;31",
            )
        elif (
            booking.payment_status
            == Booking.PaymentStatus.PAID
        ):
            indicator = self._style(
                indicator,
                "1;32",
            )
        else:
            indicator = self._style(
                indicator,
                "1;33",
            )

        self.stdout.write(
            f"{indent}{indicator}"
        )

        if booking.notes:
            self.stdout.write(
                f"{indent}{_('Notes')}: "
                f"{' '.join(booking.notes.split())}"
            )

    def _user_label(self, booking):
        name = (
            booking.user.get_full_name().strip()
            or booking.user.get_username()
        )

        return (
            f"{name} "
            f"({booking.user.get_username()})"
        )

    def _user_email(self, booking):
        return booking.user.email.strip() or "-"

    def _payment_label(self, booking):
        if booking.payment_due:
            return str(_("PAYMENT DUE")).upper()

        return str(
            booking.get_payment_status_display()
        ).upper()

    @transaction.atomic
    def _set_booking_status(self, code, status):
        booking = self._locked_booking(code)

        if status == Booking.Status.CONFIRMED:
            booking_end = (
                booking.end_date
                or booking.date
            )

            conflict = Booking.objects.filter(
                space_id=booking.space_id,
                status=Booking.Status.CONFIRMED,
                date__lte=booking_end,
            ).filter(
                Q(end_date__gte=booking.date)
                | Q(
                    end_date__isnull=True,
                    date__gte=booking.date,
                )
            ).exclude(
                pk=booking.pk
            ).exists()

            if conflict:
                raise CommandError(
                    _(
                        "%(space)s already has a confirmed booking "
                        "overlapping %(start)s - %(end)s."
                    )
                    % {
                        "space": booking.space,
                        "start": booking.date.isoformat(),
                        "end": booking_end.isoformat(),
                    }
                )

        booking.status = status

        try:
            booking.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )
        except IntegrityError as exc:
            raise CommandError(
                _(
                    "The booking conflicts with another "
                    "confirmed booking."
                )
            ) from exc

        return booking

    @transaction.atomic
    def _mark_onsite_paid(self, code):
        booking = self._locked_booking(code)

        if booking.status != Booking.Status.CONFIRMED:
            raise CommandError(
                _(
                    "Only confirmed bookings can be marked paid."
                )
            )

        if (
            booking.payment_method
            != Booking.PaymentMethod.ONSITE
        ):
            raise CommandError(
                _(
                    "Only payments made on site can be "
                    "recorded manually."
                )
            )

        if (
            booking.payment_status
            == Booking.PaymentStatus.PAID
        ):
            return booking

        booking.payment_status = (
            Booking.PaymentStatus.PAID
        )
        booking.paid_at = timezone.now()

        booking.save(
            update_fields=[
                "payment_status",
                "paid_at",
                "updated_at",
            ]
        )

        return booking

    def _set_notes(self, code, notes):
        try:
            booking = Booking.objects.get(
                booking_code=code
            )
        except Booking.DoesNotExist as exc:
            raise CommandError(
                _("Booking %(code)s does not exist.")
                % {"code": code}
            ) from exc

        booking.notes = notes
        booking.save(
            update_fields=[
                "notes",
                "updated_at",
            ]
        )

        return booking

    def _locked_booking(self, code):
        try:
            return (
                Booking.objects
                .select_for_update()
                .select_related("space")
                .get(booking_code=code)
            )
        except Booking.DoesNotExist as exc:
            raise CommandError(
                _("Booking %(code)s does not exist.")
                % {"code": code}
            ) from exc
