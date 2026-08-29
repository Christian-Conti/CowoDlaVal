from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from django.core.management.base import BaseCommand

from bookings.analytics import get_booking_statistics

try:
    from config.admin_gui import UnifiedAdminWindow
except ImportError:
    from config.stats_admin_gui import UnifiedAdminWindow


class BookingStatsDashboard:
    PERIODS = {
        "Ultimi 30 giorni": 30,
        "Ultimi 90 giorni": 90,
        "Ultimo anno": 365,
        "Tutto lo storico": None,
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.shell = UnifiedAdminWindow(
            root,
            "Cowo d'la val · Statistiche",
            "Andamento, occupazione e valore delle prenotazioni",
        )
        self.root.geometry("1320x820")
        self.root.minsize(860, 640)

        self.period_var = tk.StringVar(value="Ultimi 30 giorni")
        self.period_text = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Pronto")
        self.stats = None
        self._resize_job = None

        self._configure_stats_styles()
        self._build_toolbar()
        self._build_body()
        self.root.bind("<Configure>", self._on_resize, add="+")
        self.refresh()

    @property
    def colors(self):
        return self.shell.colors

    def _configure_stats_styles(self):
        c = self.colors
        style = self.shell.style
        style.configure(
            "Stats.Kpi.TLabel",
            background=c["surface"],
            foreground=c["text"],
            font=("TkDefaultFont", 19, "bold"),
        )
        style.configure(
            "Stats.KpiTitle.TLabel",
            background=c["surface"],
            foreground=c["muted"],
            font=("TkDefaultFont", 9, "bold"),
        )
        style.configure(
            "Stats.Small.TLabel",
            background=c["surface"],
            foreground=c["muted"],
            font=("TkDefaultFont", 9),
        )
        style.configure(
            "Stats.Combo.TCombobox",
            fieldbackground=c["surface"],
            background=c["surface"],
            foreground=c["text"],
            arrowcolor=c["text"],
            bordercolor=c["border"],
            padding=(8, 6),
        )
        style.map(
            "Stats.Combo.TCombobox",
            fieldbackground=[("readonly", c["surface"])],
            foreground=[("readonly", c["text"])],
        )
        style.configure(
            "Stats.TNotebook",
            background=c["window"],
            borderwidth=0,
        )
        style.configure(
            "Stats.TNotebook.Tab",
            background=c["neutral"],
            foreground=c["text"],
            padding=(13, 7),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "Stats.TNotebook.Tab",
            background=[("selected", c["primary"])],
            foreground=[("selected", "#FFFFFF")],
        )

    def _build_toolbar(self):
        self.shell.add_toolbar_button("Aggiorna", self.refresh, "neutral")
        self.shell.add_toolbar_button("Adatta colonne", self.fit_columns, "neutral")
        self.shell.add_toolbar_button("Tema", self.toggle_theme, "neutral")
        self.shell.add_toolbar_button("Chiudi", self.root.destroy, "danger")

    def _build_body(self):
        body = self.shell.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        self._build_filters(body)
        self._build_kpis(body)
        self._build_notebook(body)

        ttk.Label(
            body,
            textvariable=self.status_text,
            style="Cowo.Subtitle.TLabel",
        ).grid(row=3, column=0, sticky="ew", pady=(7, 0))

    def _build_filters(self, parent):
        bar = ttk.Frame(parent, style="Cowo.Root.TFrame")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        bar.grid_columnconfigure(3, weight=1)

        ttk.Label(bar, text="Periodo", style="Cowo.Section.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.period_combo = ttk.Combobox(
            bar,
            textvariable=self.period_var,
            values=list(self.PERIODS),
            state="readonly",
            width=20,
            style="Stats.Combo.TCombobox",
        )
        self.period_combo.grid(row=0, column=1, sticky="w")
        self.period_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())

        ttk.Button(
            bar,
            text="Applica",
            command=self.refresh,
            style="Cowo.Primary.TButton",
        ).grid(row=0, column=2, padx=8)

        ttk.Label(
            bar,
            textvariable=self.period_text,
            style="Cowo.Subtitle.TLabel",
        ).grid(row=0, column=3, sticky="e")

    def _kpi_card(self, parent, column, title):
        card = ttk.Frame(parent, style="Cowo.Card.TFrame", padding=12)
        card.grid(row=0, column=column, sticky="nsew", padx=4)
        parent.grid_columnconfigure(column, weight=1, uniform="stats-kpi")
        ttk.Label(card, text=title, style="Stats.KpiTitle.TLabel").pack(anchor="w")
        value = ttk.Label(card, text="—", style="Stats.Kpi.TLabel")
        value.pack(anchor="w", pady=(4, 0))
        note = ttk.Label(card, text="", style="Stats.Small.TLabel")
        note.pack(anchor="w", pady=(2, 0))
        return value, note

    def _build_kpis(self, parent):
        box = ttk.Frame(parent, style="Cowo.Root.TFrame")
        box.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.kpi_total, self.kpi_total_note = self._kpi_card(box, 0, "Prenotazioni")
        self.kpi_occupancy, self.kpi_occupancy_note = self._kpi_card(box, 1, "Occupazione")
        self.kpi_revenue, self.kpi_revenue_note = self._kpi_card(box, 2, "Incassato")
        self.kpi_users, self.kpi_users_note = self._kpi_card(box, 3, "Utenti unici")
        self.kpi_cancel, self.kpi_cancel_note = self._kpi_card(box, 4, "Cancellazioni")

    def _build_notebook(self, parent):
        self.notebook = ttk.Notebook(parent, style="Stats.TNotebook")
        self.notebook.grid(row=2, column=0, sticky="nsew")

        self.overview = ttk.Frame(self.notebook, style="Cowo.Root.TFrame")
        self.detail = ttk.Frame(self.notebook, style="Cowo.Root.TFrame")
        self.notebook.add(self.overview, text="Panoramica")
        self.notebook.add(self.detail, text="Dettaglio giornaliero")

        self._build_overview()
        self._build_detail()

    def _chart_card(self, parent, title):
        card = ttk.Frame(parent, style="Cowo.Card.TFrame", padding=10)
        ttk.Label(card, text=title, style="Cowo.Card.TLabel").pack(anchor="w", pady=(0, 6))
        canvas = tk.Canvas(card, height=240, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", lambda _event: self._schedule_redraw())
        return card, canvas

    def _build_overview(self):
        self.overview.grid_columnconfigure(0, weight=1)
        self.overview.grid_columnconfigure(1, weight=1)
        self.overview.grid_rowconfigure(0, weight=1)
        self.overview.grid_rowconfigure(1, weight=1)

        self.trend_card, self.trend_canvas = self._chart_card(
            self.overview, "Andamento giornaliero"
        )
        self.spaces_card, self.spaces_canvas = self._chart_card(
            self.overview, "Postazioni più utilizzate"
        )
        self.weekday_card, self.weekday_canvas = self._chart_card(
            self.overview, "Prenotazioni per giorno della settimana"
        )
        self.status_card, self.status_canvas = self._chart_card(
            self.overview, "Distribuzione stati"
        )
        self._reflow_overview()

    def _build_detail(self):
        self.detail.grid_columnconfigure(0, weight=1)
        self.detail.grid_rowconfigure(0, weight=1)

        columns = ("date", "bookings", "occupied")
        self.tree = ttk.Treeview(
            self.detail,
            columns=columns,
            show="headings",
            style="Cowo.Treeview",
        )
        self.tree.heading("date", text="Data")
        self.tree.heading("bookings", text="Prenotazioni")
        self.tree.heading("occupied", text="Postazioni occupate")
        self.tree.column("date", width=180, anchor="w")
        self.tree.column("bookings", width=150, anchor="center")
        self.tree.column("occupied", width=190, anchor="center")

        scroll = ttk.Scrollbar(self.detail, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.shell.register_tree(self.tree)

    def _reflow_overview(self):
        width = max(self.root.winfo_width(), 1)
        cards = [self.trend_card, self.spaces_card, self.weekday_card, self.status_card]
        for card in cards:
            card.grid_forget()

        if width >= 1050:
            self.overview.grid_columnconfigure(0, weight=1)
            self.overview.grid_columnconfigure(1, weight=1)
            for index, card in enumerate(cards):
                card.grid(
                    row=index // 2,
                    column=index % 2,
                    sticky="nsew",
                    padx=4,
                    pady=4,
                )
        else:
            self.overview.grid_columnconfigure(0, weight=1)
            self.overview.grid_columnconfigure(1, weight=0)
            for index, card in enumerate(cards):
                card.grid(row=index, column=0, sticky="nsew", padx=4, pady=4)

    def refresh(self):
        try:
            label = self.period_var.get()
            days = self.PERIODS.get(label, 30)
            self.status_text.set("Aggiornamento statistiche…")
            self.root.update_idletasks()
            self.stats = get_booking_statistics(days=days or 30, all_time=days is None)
            self._update_kpis()
            self._update_tree()
            self._redraw_charts()
            period = self.stats["period"]
            self.period_text.set(f"{period['start']} → {period['end']}")
            self.shell.set_subtitle(
                f"{self.stats['kpi']['total']} prenotazioni · "
                f"{self.stats['kpi']['space_count']} postazioni · "
                f"{period['days']} giorni"
            )
            self.status_text.set("Statistiche aggiornate")
        except Exception as exc:
            self.status_text.set("Errore durante il caricamento")
            messagebox.showerror("Statistiche", str(exc), parent=self.root)

    def _update_kpis(self):
        k = self.stats["kpi"]
        occupancy = "n/d" if k["occupancy"] is None else f"{k['occupancy']:.1f}%"

        self.kpi_total.configure(text=str(k["total"]))
        self.kpi_total_note.configure(text=f"{k['active']} attive · {k['confirmed']} confermate")

        self.kpi_occupancy.configure(text=occupancy)
        self.kpi_occupancy_note.configure(
            text=f"{k['occupied_desk_days']} desk-days su {k['space_count']} postazioni"
        )

        self.kpi_revenue.configure(text=f"€ {k['paid_revenue']:.2f}")
        self.kpi_revenue_note.configure(text=f"€ {k['expected_revenue']:.2f} valore attivo")

        self.kpi_users.configure(text=str(k["unique_users"]))
        self.kpi_users_note.configure(text=f"{k['repeat_rate']:.1f}% utenti ricorrenti")

        self.kpi_cancel.configure(text=f"{k['cancellation_rate']:.1f}%")
        self.kpi_cancel_note.configure(text=f"{k['cancelled']} cancellate")

    def _update_tree(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.stats["trend"]:
            self.tree.insert(
                "",
                "end",
                values=(item["date"], item["bookings"], item["occupied_desks"]),
            )
        self.fit_columns()

    def fit_columns(self):
        self.shell.fit_columns()

    def toggle_theme(self):
        self.shell.toggle_theme()
        self._configure_stats_styles()
        self._redraw_charts()

    def _schedule_redraw(self):
        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except tk.TclError:
                pass
        self._resize_job = self.root.after(80, self._redraw_charts)

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        self._reflow_overview()
        self._schedule_redraw()

    def _prepare_canvas(self, canvas):
        c = self.colors
        canvas.configure(background=c["surface"])
        canvas.delete("all")
        width = max(canvas.winfo_width(), 120)
        height = max(canvas.winfo_height(), 120)
        return c, width, height

    def _redraw_charts(self):
        if not self.stats:
            return
        self._draw_trend()
        self._draw_spaces()
        self._draw_weekdays()
        self._draw_statuses()

    def _draw_trend(self):
        canvas = self.trend_canvas
        c, width, height = self._prepare_canvas(canvas)
        data = self.stats["trend"]
        if not data:
            return self._draw_empty(canvas, width, height)

        left, right, top, bottom = 42, 18, 22, 32
        plot_w = max(width - left - right, 1)
        plot_h = max(height - top - bottom, 1)
        max_value = max(
            1,
            max(max(item["bookings"], item["occupied_desks"]) for item in data),
        )

        for i in range(5):
            y = top + plot_h * i / 4
            canvas.create_line(left, y, left + plot_w, y, fill=c["border"])
            value = round(max_value * (1 - i / 4))
            canvas.create_text(left - 8, y, text=str(value), fill=c["muted"], anchor="e")

        def points(key):
            result = []
            denominator = max(len(data) - 1, 1)
            for index, item in enumerate(data):
                x = left + plot_w * index / denominator
                y = top + plot_h * (1 - item[key] / max_value)
                result.extend((x, y))
            return result

        for key, color, label in (
            ("bookings", c["primary"], "Prenotazioni"),
            ("occupied_desks", c["success"], "Postazioni occupate"),
        ):
            pts = points(key)
            if len(pts) >= 4:
                canvas.create_line(*pts, fill=color, width=2.5, smooth=True)
            elif len(pts) == 2:
                canvas.create_oval(pts[0] - 2, pts[1] - 2, pts[0] + 2, pts[1] + 2, fill=color, outline="")

        if data:
            canvas.create_text(left, height - 9, text=data[0]["label"], fill=c["muted"], anchor="w")
            canvas.create_text(width - right, height - 9, text=data[-1]["label"], fill=c["muted"], anchor="e")

        x = left
        for color, label in ((c["primary"], "Prenotazioni"), (c["success"], "Postazioni occupate")):
            canvas.create_rectangle(x, 5, x + 10, 15, fill=color, outline="")
            canvas.create_text(x + 15, 10, text=label, fill=c["text"], anchor="w")
            x += 125

    def _draw_spaces(self):
        canvas = self.spaces_canvas
        c, width, height = self._prepare_canvas(canvas)
        data = self.stats["top_spaces"][:7]
        if not data:
            return self._draw_empty(canvas, width, height)

        maximum = max(item["days"] for item in data) or 1
        label_w = min(145, width * 0.38)
        usable = max(width - label_w - 42, 40)
        row_h = max((height - 16) / len(data), 22)

        for index, item in enumerate(data):
            y = 12 + index * row_h
            name = item["space"]
            if len(name) > 20:
                name = name[:19] + "…"
            canvas.create_text(8, y + row_h / 2, text=name, fill=c["text"], anchor="w")
            bar_w = usable * item["days"] / maximum
            x = label_w
            canvas.create_rectangle(x, y + 5, x + usable, y + row_h - 5, fill=c["surface_alt"], outline="")
            canvas.create_rectangle(x, y + 5, x + bar_w, y + row_h - 5, fill=c["primary"], outline="")
            canvas.create_text(x + usable + 7, y + row_h / 2, text=f"{item['days']} gg", fill=c["muted"], anchor="w")

    def _draw_weekdays(self):
        canvas = self.weekday_canvas
        c, width, height = self._prepare_canvas(canvas)
        data = self.stats["weekdays"]
        maximum = max((item["count"] for item in data), default=0) or 1

        left, right, top, bottom = 28, 12, 16, 30
        plot_w = max(width - left - right, 1)
        plot_h = max(height - top - bottom, 1)
        step = plot_w / max(len(data), 1)
        bar_w = step * 0.58

        for index, item in enumerate(data):
            x = left + index * step + (step - bar_w) / 2
            bar_h = plot_h * item["count"] / maximum
            y = top + plot_h - bar_h
            canvas.create_rectangle(x, y, x + bar_w, top + plot_h, fill=c["success"], outline="")
            canvas.create_text(x + bar_w / 2, height - 9, text=item["label"], fill=c["muted"])
            canvas.create_text(x + bar_w / 2, max(y - 9, 8), text=str(item["count"]), fill=c["text"])

    def _draw_statuses(self):
        canvas = self.status_canvas
        c, width, height = self._prepare_canvas(canvas)
        data = self.stats["statuses"][:7]
        if not data:
            return self._draw_empty(canvas, width, height)

        maximum = max(item["count"] for item in data) or 1
        label_w = min(150, width * 0.42)
        usable = max(width - label_w - 40, 40)
        row_h = max((height - 14) / len(data), 22)

        for index, item in enumerate(data):
            y = 8 + index * row_h
            label = item["label"]
            low = label.lower()
            if any(word in low for word in ("cancel", "annull", "cancell")):
                color = c["danger"]
            elif any(word in low for word in ("confirm", "conferm", "paid", "pagat", "complet")):
                color = c["success"]
            else:
                color = c["primary"]

            if len(label) > 21:
                label = label[:20] + "…"
            canvas.create_text(8, y + row_h / 2, text=label, fill=c["text"], anchor="w")
            x = label_w
            canvas.create_rectangle(x, y + 5, x + usable, y + row_h - 5, fill=c["surface_alt"], outline="")
            canvas.create_rectangle(
                x,
                y + 5,
                x + usable * item["count"] / maximum,
                y + row_h - 5,
                fill=color,
                outline="",
            )
            canvas.create_text(x + usable + 7, y + row_h / 2, text=str(item["count"]), fill=c["muted"], anchor="w")

    def _draw_empty(self, canvas, width, height):
        canvas.create_text(
            width / 2,
            height / 2,
            text="Nessun dato nel periodo selezionato",
            fill=self.colors["muted"],
        )


class Command(BaseCommand):
    help = "Apre il dashboard grafico delle statistiche prenotazioni."

    def handle(self, *args, **options):
        root = tk.Tk()
        BookingStatsDashboard(root)
        root.mainloop()
