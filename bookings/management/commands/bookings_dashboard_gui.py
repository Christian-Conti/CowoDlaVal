from __future__ import annotations

from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from bookings.models import Booking
from spaces.models import Space
from config.admin_gui import UnifiedAdminWindow


COLUMNS = (
    "code",
    "space",
    "user",
    "email",
    "status",
    "payment_method",
    "payment_status",
    "amount",
)

HEADINGS = {
    "code": "Codice",
    "space": "Postazione",
    "user": "User",
    "email": "Email",
    "status": "Stato",
    "payment_method": "Metodo pagamento",
    "payment_status": "Pagamento",
    "amount": "Importo",
}


class BookingsWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.ui = UnifiedAdminWindow(
            self.root,
            "Cowo d'la val · Prenotazioni",
            "Caricamento…",
        )
        self.selected_date = tk.StringVar(value=date.today().isoformat())
        self.selected_booking = None

        self._build_toolbar()
        self._build_body()
        self._build_footer()
        self.refresh()

    def _build_toolbar(self):
        self.ui.add_toolbar_button("Aggiorna", self.refresh, "neutral")
        self.ui.add_toolbar_button("Adatta colonne", self.ui.fit_columns, "neutral")
        self.ui.add_toolbar_button("Tema", self.ui.toggle_theme, "neutral")
        self.ui.add_toolbar_button("Chiudi", self.root.destroy, "danger")

    def _build_body(self):
        body = self.ui.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        nav = ttk.Frame(body, style="Cowo.Root.TFrame")
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for col in range(6):
            nav.grid_columnconfigure(col, weight=1 if col in {0, 1, 2, 3, 4, 5} else 0)

        ttk.Button(nav, text="‹ Giorno precedente", command=self.previous_day, style="Cowo.Neutral.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Entry(nav, textvariable=self.selected_date, style="Cowo.TEntry", justify="center").grid(
            row=0, column=1, sticky="ew", padx=3
        )
        ttk.Button(nav, text="Applica data", command=self.refresh, style="Cowo.Primary.TButton").grid(
            row=0, column=2, sticky="ew", padx=3
        )
        ttk.Button(nav, text="Oggi", command=self.today, style="Cowo.Neutral.TButton").grid(
            row=0, column=3, sticky="ew", padx=3
        )
        ttk.Button(nav, text="Giorno successivo ›", command=self.next_day, style="Cowo.Neutral.TButton").grid(
            row=0, column=4, sticky="ew", padx=(3, 0)
        )

        table_frame = ttk.Frame(body, style="Cowo.Card.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=COLUMNS,
            show="headings",
            selectmode="browse",
            style="Cowo.Treeview",
        )
        for column in COLUMNS:
            self.tree.heading(column, text=HEADINGS[column])
            self.tree.column(column, width=125, minwidth=70, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.ui.register_tree(self.tree)

        notes_frame = ttk.Frame(body, style="Cowo.Root.TFrame")
        notes_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        notes_frame.grid_columnconfigure(0, weight=1)
        ttk.Label(notes_frame, text="Note della prenotazione selezionata", style="Cowo.Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.notes = tk.Text(notes_frame, height=5, wrap="word")
        self.notes.grid(row=1, column=0, sticky="ew")

    def _build_footer(self):
        self.confirm_button = self.ui.add_footer_button("Conferma", self.confirm_booking, "success")
        self.paid_button = self.ui.add_footer_button("Segna pagato", self.mark_paid, "success")
        self.save_notes_button = self.ui.add_footer_button("Salva note", self.save_notes, "success")
        self.cancel_button = self.ui.add_footer_button("Cancella prenotazione", self.cancel_booking, "danger")
        self._set_action_state(False)

    def _parse_date(self):
        try:
            return date.fromisoformat(self.selected_date.get().strip())
        except ValueError as exc:
            raise CommandError("Usa una data nel formato YYYY-MM-DD.") from exc

    def _booking_queryset(self, day):
        field_names = {field.name for field in Booking._meta.fields}
        if "end_date" in field_names:
            return Booking.objects.filter(date__lte=day).filter(
                Q(end_date__gte=day) | Q(end_date__isnull=True, date=day)
            )
        return Booking.objects.filter(date=day)

    def refresh(self):
        try:
            day = self._parse_date()
        except CommandError as exc:
            messagebox.showerror("Data non valida", str(exc), parent=self.root)
            return

        selected_code = self.selected_booking.booking_code if self.selected_booking else None
        self.tree.delete(*self.tree.get_children())
        bookings = list(
            self._booking_queryset(day)
            .select_related("space", "user")
            .order_by("space__name", "booking_code")
        )

        booked_space_ids = set()
        for booking in bookings:
            booked_space_ids.add(booking.space_id)
            full_name = booking.user.get_full_name().strip() if booking.user_id else ""
            username = getattr(booking.user, "username", "") if booking.user_id else ""
            user_text = full_name or username or "—"
            email = getattr(booking.user, "email", "") if booking.user_id else ""
            status = self._display(booking, "status")
            payment_method = self._display(booking, "payment_method")
            payment_status = self._display(booking, "payment_status")
            amount = f"€{booking.amount}" if booking.amount is not None else "—"
            item = self.tree.insert(
                "",
                "end",
                iid=str(booking.pk),
                values=(
                    booking.booking_code,
                    str(booking.space),
                    user_text,
                    email,
                    status,
                    payment_method,
                    payment_status,
                    amount,
                ),
            )
            if selected_code and booking.booking_code == selected_code:
                self.tree.selection_set(item)
                self.tree.focus(item)

        free_spaces = Space.objects.filter(is_active=True).exclude(pk__in=booked_space_ids).count()
        self.ui.set_subtitle(
            f"{len(bookings)} {'prenotazione' if len(bookings) == 1 else 'prenotazioni'} · "
            f"{free_spaces} {'postazione libera' if free_spaces == 1 else 'postazioni libere'}"
        )
        self.ui.fit_columns()
        self._on_select()

    @staticmethod
    def _display(obj, field):
        method = getattr(obj, f"get_{field}_display", None)
        if callable(method):
            try:
                return method()
            except Exception:
                pass
        return str(getattr(obj, field, "") or "—")

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            self.selected_booking = None
            self.notes.delete("1.0", "end")
            self._set_action_state(False)
            return
        try:
            self.selected_booking = Booking.objects.get(pk=int(selection[0]))
        except (Booking.DoesNotExist, ValueError):
            self.selected_booking = None
            self._set_action_state(False)
            return
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", self.selected_booking.notes or "")
        self._set_action_state(True)

    def _set_action_state(self, enabled):
        state = ["!disabled"] if enabled else ["disabled"]
        for button in (self.confirm_button, self.paid_button, self.save_notes_button, self.cancel_button):
            button.state(state)

    def _selected_code(self):
        if not self.selected_booking:
            messagebox.showwarning("Prenotazione", "Seleziona una prenotazione.", parent=self.root)
            return None
        return self.selected_booking.booking_code

    def confirm_booking(self):
        code = self._selected_code()
        if not code:
            return
        if not messagebox.askyesno("Conferma", f"Confermare la prenotazione {code}?", parent=self.root):
            return
        self._run_booking_action("--confirm-booking", code, "Prenotazione confermata.")

    def mark_paid(self):
        code = self._selected_code()
        if not code:
            return
        if not messagebox.askyesno("Pagamento", f"Segnare {code} come pagata?", parent=self.root):
            return
        self._run_booking_action("--mark-paid", code, "Prenotazione segnata come pagata.")

    def cancel_booking(self):
        code = self._selected_code()
        if not code:
            return
        if not messagebox.askyesno(
            "Cancella prenotazione",
            f"Cancellare definitivamente la prenotazione {code}?",
            icon="warning",
            parent=self.root,
        ):
            return
        self._run_booking_action("--cancel-booking", code, "Prenotazione cancellata.")

    def _run_booking_action(self, flag, code, success_text):
        try:
            call_command("bookings_dashboard", flag, code)
        except Exception as exc:
            messagebox.showerror("Operazione non riuscita", str(exc), parent=self.root)
            return
        messagebox.showinfo("Cowo d'la val", success_text, parent=self.root)
        self.selected_booking = None
        self.refresh()

    def save_notes(self):
        if not self.selected_booking:
            return
        self.selected_booking.notes = self.notes.get("1.0", "end-1c")
        fields = ["notes"]
        if any(field.name == "updated_at" for field in Booking._meta.fields):
            fields.append("updated_at")
        try:
            self.selected_booking.save(update_fields=fields)
        except Exception as exc:
            messagebox.showerror("Note", str(exc), parent=self.root)
            return
        messagebox.showinfo("Note", "Note salvate.", parent=self.root)
        self.refresh()

    def previous_day(self):
        try:
            day = self._parse_date() - timedelta(days=1)
        except CommandError:
            day = date.today() - timedelta(days=1)
        self.selected_date.set(day.isoformat())
        self.refresh()

    def next_day(self):
        try:
            day = self._parse_date() + timedelta(days=1)
        except CommandError:
            day = date.today() + timedelta(days=1)
        self.selected_date.set(day.isoformat())
        self.refresh()

    def today(self):
        self.selected_date.set(date.today().isoformat())
        self.refresh()

    def run(self):
        self.root.mainloop()


class Command(BaseCommand):
    help = "Open the unified Cowo d'la val bookings desktop dashboard."

    def handle(self, *args, **options):
        try:
            BookingsWindow().run()
        except tk.TclError as exc:
            raise CommandError(f"Impossibile avviare la GUI prenotazioni: {exc}") from exc
