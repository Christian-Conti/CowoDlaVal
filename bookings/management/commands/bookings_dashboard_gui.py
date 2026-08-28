from __future__ import annotations

import io
import os
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from bookings.models import Booking
from spaces.models import Space


LIGHT_FALLBACK = {
    "background": "#f4f6fb",
    "surface": "#ffffff",
    "surface_alt": "#eef1f7",
    "text": "#171a2b",
    "muted": "#687086",
    "primary": "#5b63d3",
    "primary_hover": "#4d55c2",
    "danger": "#e97891",
    "danger_hover": "#d9637e",
    "border": "#d9deea",
    "selection": "#e4e6ff",
    "selection_text": "#171a2b",
}

DARK_FALLBACK = {
    "background": "#101525",
    "surface": "#191f33",
    "surface_alt": "#222a42",
    "text": "#f4f6ff",
    "muted": "#aeb6d0",
    "primary": "#7c83ff",
    "primary_hover": "#9196ff",
    "danger": "#f08ca1",
    "danger_hover": "#f4a2b3",
    "border": "#303954",
    "selection": "#343d67",
    "selection_text": "#ffffff",
}


CSS_CANDIDATES = {
    "background": (
        "--background",
        "--background-color",
        "--page-bg",
        "--page-background",
        "--bg",
        "--color-bg",
    ),
    "surface": (
        "--surface",
        "--card-bg",
        "--card-background",
        "--panel-bg",
        "--surface-1",
    ),
    "surface_alt": (
        "--surface-alt",
        "--surface-2",
        "--muted-bg",
        "--secondary-bg",
    ),
    "text": (
        "--text",
        "--text-color",
        "--foreground",
        "--color-text",
    ),
    "muted": (
        "--muted",
        "--muted-text",
        "--text-muted",
        "--secondary-text",
    ),
    "primary": (
        "--primary",
        "--accent",
        "--brand",
        "--color-primary",
        "--accent-color",
    ),
    "danger": (
        "--danger",
        "--error",
        "--destructive",
        "--color-danger",
    ),
    "border": (
        "--border",
        "--border-color",
        "--divider",
        "--line",
    ),
}


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$")
RGB_COLOR_RE = re.compile(
    r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,[^)]*)?\)$"
)
CSS_VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}{]+)")


def _extract_balanced_block(text: str, start_index: int) -> str:
    opening = text.find("{", start_index)
    if opening < 0:
        return ""

    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index]

    return ""


def _collect_css_text() -> str:
    static_root = Path(settings.BASE_DIR) / "static"
    if not static_root.exists():
        return ""

    chunks = []
    total = 0
    for path in sorted(static_root.rglob("*.css")):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        chunks.append(content)
        total += len(content)
        if total >= 2_000_000:
            break

    return "\n".join(chunks)


def _parse_css_variables(text: str) -> dict[str, str]:
    return {name.strip(): value.strip() for name, value in CSS_VAR_RE.findall(text)}


def _resolve_css_value(value: str, variables: dict[str, str], depth: int = 0) -> str:
    if depth > 8:
        return value

    match = re.fullmatch(r"var\((--[\w-]+)(?:,\s*([^)]*))?\)", value.strip())
    if match is None:
        return value.strip()

    name, fallback = match.groups()
    resolved = variables.get(name, fallback or "")
    return _resolve_css_value(resolved, variables, depth + 1)


def _normalize_color(value: str, variables: dict[str, str]) -> str | None:
    value = _resolve_css_value(value, variables).strip()

    if HEX_COLOR_RE.fullmatch(value):
        if len(value) == 4:
            return "#" + "".join(character * 2 for character in value[1:])
        return value.lower()

    match = RGB_COLOR_RE.fullmatch(value)
    if match is not None:
        red, green, blue = (max(0, min(255, int(part))) for part in match.groups())
        return f"#{red:02x}{green:02x}{blue:02x}"

    return None


def _first_color(
    variables: dict[str, str],
    candidates: Iterable[str],
) -> str | None:
    for candidate in candidates:
        if candidate not in variables:
            continue
        color = _normalize_color(variables[candidate], variables)
        if color is not None:
            return color

    # Also accept project-specific variable names containing the semantic keyword.
    keywords = {
        candidate.removeprefix("--").replace("color-", "").replace("-color", "")
        for candidate in candidates
    }
    for name, value in variables.items():
        lowered = name.lower()
        if not any(keyword and keyword in lowered for keyword in keywords):
            continue
        color = _normalize_color(value, variables)
        if color is not None:
            return color

    return None


def _derive_palette(base: dict[str, str], variables: dict[str, str]) -> dict[str, str]:
    palette = dict(base)

    for semantic_name, candidates in CSS_CANDIDATES.items():
        color = _first_color(variables, candidates)
        if color is not None:
            palette[semantic_name] = color

    # Keep hover/selection colors predictable even when the website only exposes core colors.
    palette.setdefault("primary_hover", base["primary_hover"])
    palette.setdefault("danger_hover", base["danger_hover"])
    palette.setdefault("selection", base["selection"])
    palette.setdefault("selection_text", base["selection_text"])
    return palette


def load_site_palettes() -> tuple[dict[str, str], dict[str, str]]:
    css = _collect_css_text()
    if not css:
        return dict(LIGHT_FALLBACK), dict(DARK_FALLBACK)

    root_variables: dict[str, str] = {}
    root_match = re.search(r":root\s*{", css, re.IGNORECASE)
    if root_match is not None:
        root_variables.update(
            _parse_css_variables(_extract_balanced_block(css, root_match.start()))
        )

    light_variables = dict(root_variables)
    dark_variables = dict(root_variables)

    dark_media = re.search(
        r"@media\s*\([^)]*prefers-color-scheme\s*:\s*dark[^)]*\)\s*{",
        css,
        re.IGNORECASE,
    )
    if dark_media is not None:
        dark_variables.update(
            _parse_css_variables(_extract_balanced_block(css, dark_media.start()))
        )

    # Support explicit theme selectors used by many responsive sites.
    for pattern in (
        r"(?:html|body)?\s*\[data-theme=[\"']dark[\"']\]\s*{",
        r"\.dark\s*{",
        r"\.theme-dark\s*{",
    ):
        for match in re.finditer(pattern, css, re.IGNORECASE):
            dark_variables.update(
                _parse_css_variables(_extract_balanced_block(css, match.start()))
            )

    return (
        _derive_palette(LIGHT_FALLBACK, light_variables),
        _derive_palette(DARK_FALLBACK, dark_variables),
    )


def _detect_theme(requested: str) -> str:
    requested = requested.strip().lower()
    if requested in {"light", "dark"}:
        return requested

    environment_theme = os.environ.get("COWO_GUI_THEME", "").strip().lower()
    if environment_theme in {"light", "dark"}:
        return environment_theme

    gtk_theme = os.environ.get("GTK_THEME", "").lower()
    if "dark" in gtk_theme:
        return "dark"

    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.5,
        )
        if "dark" in result.stdout.lower():
            return "dark"
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        pass

    # The public site is designed around a dark device theme as well; the GUI keeps
    # the same default when the container cannot inspect the host desktop setting.
    return "dark"


def _display_value(instance, field_name: str, fallback: str = "—") -> str:
    display_method = getattr(instance, f"get_{field_name}_display", None)
    if callable(display_method):
        try:
            value = display_method()
            if value not in (None, ""):
                return str(value)
        except (AttributeError, TypeError, ValueError):
            pass

    value = getattr(instance, field_name, None)
    if value in (None, ""):
        return fallback
    return str(value)


def _booking_code(booking: Booking) -> str:
    for field_name in ("code", "booking_code", "public_code"):
        value = getattr(booking, field_name, None)
        if value:
            return str(value)
    return str(booking.pk)


def _customer_name(booking: Booking) -> str:
    user = getattr(booking, "user", None)
    if user is None:
        return "—"

    full_name = ""
    get_full_name = getattr(user, "get_full_name", None)
    if callable(get_full_name):
        full_name = get_full_name().strip()

    username = getattr(user, "username", "") or ""
    if full_name and username and full_name != username:
        return f"{full_name} ({username})"
    return full_name or username or str(user)


def _customer_email(booking: Booking) -> str:
    user = getattr(booking, "user", None)
    return str(getattr(user, "email", "") or "—")


def _space_name(booking: Booking) -> str:
    space = getattr(booking, "space", None)
    if space is None:
        return "—"
    return str(getattr(space, "name", "") or space)


def _amount_text(booking: Booking) -> str:
    amount = getattr(booking, "amount", None)
    if amount is None:
        return "—"

    currency = str(getattr(booking, "currency", "EUR") or "EUR").upper()
    try:
        numeric = f"{amount:.2f}"
    except (TypeError, ValueError):
        numeric = str(amount)

    if currency == "EUR":
        return f"€ {numeric}"
    return f"{numeric} {currency}"


def _booking_queryset_for_date(selected_date: date):
    queryset = Booking.objects.select_related("space", "user")
    field_names = {field.name for field in Booking._meta.get_fields()}

    if "end_date" in field_names:
        queryset = queryset.filter(date__lte=selected_date).filter(
            Q(end_date__gte=selected_date)
            | Q(end_date__isnull=True, date=selected_date)
        )
    else:
        queryset = queryset.filter(date=selected_date)

    ordering = []
    if "space" in field_names:
        ordering.append("space__name")
    if "created_at" in field_names:
        ordering.append("created_at")
    else:
        ordering.append("pk")

    return queryset.order_by(*ordering)


def _is_cancelled(booking: Booking) -> bool:
    return str(getattr(booking, "status", "")).strip().lower() in {
        "cancelled",
        "canceled",
    }


class DashboardWindow:
    COLUMNS = (
        "code",
        "space",
        "customer",
        "email",
        "status",
        "payment_method",
        "payment_status",
        "amount",
    )

    HEADINGS = {
        "code": "Codice prenotazione",
        "space": "Postazione",
        "customer": "Cliente",
        "email": "Email",
        "status": "Prenotazione",
        "payment_method": "Metodo di pagamento",
        "payment_status": "Pagamento",
        "amount": "Importo",
    }

    COLUMN_RATIOS = {
        "code": 0.14,
        "space": 0.10,
        "customer": 0.15,
        "email": 0.19,
        "status": 0.11,
        "payment_method": 0.13,
        "payment_status": 0.11,
        "amount": 0.07,
    }

    COLUMN_MIN_WIDTHS = {
        "code": 125,
        "space": 95,
        "customer": 125,
        "email": 165,
        "status": 105,
        "payment_method": 125,
        "payment_status": 115,
        "amount": 90,
    }

    def __init__(self, root, tk, ttk, messagebox, selected_date: date, theme: str):
        self.root = root
        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.selected_date = selected_date
        self.light_palette, self.dark_palette = load_site_palettes()
        self.theme_name = _detect_theme(theme)
        self.palette = self._palette_for_theme(self.theme_name)
        self.selected_booking_id: int | None = None
        self._resize_job = None
        self._button_layout = None
        self._last_font_size = None

        self.date_var = tk.StringVar(value=self.selected_date.isoformat())
        self.summary_var = tk.StringVar(value="")
        self.theme_button_var = tk.StringVar(value="Tema chiaro" if self.theme_name == "dark" else "Tema scuro")

        self.root.title("Cowo d'la val - Prenotazioni")
        self.root.geometry("1360x780")
        self.root.minsize(900, 580)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self._build_layout()
        self._apply_theme()
        self._bind_events()
        self.refresh()
        self.root.after_idle(self._handle_resize)

    def _palette_for_theme(self, theme_name: str) -> dict[str, str]:
        if theme_name == "light":
            return dict(self.light_palette)
        return dict(self.dark_palette)

    def _build_layout(self) -> None:
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.header = self.ttk.Frame(self.root, style="App.TFrame", padding=(24, 18, 24, 12))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        self.title_label = self.ttk.Label(
            self.header,
            text="Cowo d'la val · Prenotazioni",
            style="Title.TLabel",
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.summary_label = self.ttk.Label(
            self.header,
            textvariable=self.summary_var,
            style="Summary.TLabel",
        )
        self.summary_label.grid(row=0, column=1, padx=(18, 12), sticky="e")

        self.theme_button = self.ttk.Button(
            self.header,
            textvariable=self.theme_button_var,
            style="Ghost.TButton",
            command=self.toggle_theme,
        )
        self.theme_button.grid(row=0, column=2, sticky="e")

        self.content = self.ttk.Frame(self.root, style="App.TFrame", padding=(24, 0, 24, 18))
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        self.toolbar = self.ttk.Frame(self.content, style="Toolbar.TFrame", padding=12)
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.toolbar.grid_columnconfigure(5, weight=1)

        self.previous_button = self.ttk.Button(
            self.toolbar,
            text="‹ Giorno precedente",
            style="Secondary.TButton",
            command=lambda: self.change_date(-1),
        )
        self.previous_button.grid(row=0, column=0, padx=(0, 8))

        self.date_entry = self.ttk.Entry(
            self.toolbar,
            textvariable=self.date_var,
            style="App.TEntry",
            width=14,
            justify="center",
        )
        self.date_entry.grid(row=0, column=1, padx=4)

        self.apply_date_button = self.ttk.Button(
            self.toolbar,
            text="Applica data",
            style="Primary.TButton",
            command=self.apply_date,
        )
        self.apply_date_button.grid(row=0, column=2, padx=4)

        self.today_button = self.ttk.Button(
            self.toolbar,
            text="Oggi",
            style="Secondary.TButton",
            command=self.go_today,
        )
        self.today_button.grid(row=0, column=3, padx=4)

        self.next_button = self.ttk.Button(
            self.toolbar,
            text="Giorno successivo ›",
            style="Secondary.TButton",
            command=lambda: self.change_date(1),
        )
        self.next_button.grid(row=0, column=4, padx=(8, 0))

        self.table_card = self.ttk.Frame(self.content, style="Card.TFrame", padding=1)
        self.table_card.grid(row=1, column=0, sticky="nsew")
        self.table_card.grid_rowconfigure(0, weight=1)
        self.table_card.grid_columnconfigure(0, weight=1)

        self.tree = self.ttk.Treeview(
            self.table_card,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
            style="App.Treeview",
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        for column in self.COLUMNS:
            self.tree.heading(column, text=self.HEADINGS[column], anchor="w")
            anchor = "e" if column == "amount" else "w"
            self.tree.column(
                column,
                anchor=anchor,
                minwidth=self.COLUMN_MIN_WIDTHS[column],
                stretch=True,
            )

        self.vertical_scrollbar = self.ttk.Scrollbar(
            self.table_card,
            orient="vertical",
            command=self.tree.yview,
        )
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")

        self.horizontal_scrollbar = self.ttk.Scrollbar(
            self.table_card,
            orient="horizontal",
            command=self.tree.xview,
        )
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        self.tree.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set,
        )

        self.notes_card = self.ttk.Frame(
            self.content,
            style="Card.TFrame",
            padding=(14, 10, 14, 14),
        )
        self.notes_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.notes_card.grid_columnconfigure(0, weight=1)

        self.notes_label = self.ttk.Label(
            self.notes_card,
            text="Note della prenotazione selezionata",
            style="Section.TLabel",
        )
        self.notes_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.notes_text = self.tk.Text(
            self.notes_card,
            height=4,
            wrap="word",
            undo=True,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            padx=10,
            pady=8,
        )
        self.notes_text.grid(row=1, column=0, sticky="ew")

        self.actions = self.ttk.Frame(self.content, style="App.TFrame")
        self.actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        self.confirm_button = self.ttk.Button(
            self.actions,
            text="Conferma",
            style="Primary.TButton",
            command=lambda: self.run_action("confirm"),
        )
        self.cancel_button = self.ttk.Button(
            self.actions,
            text="Cancella prenotazione",
            style="Danger.TButton",
            command=lambda: self.run_action("cancel"),
        )
        self.paid_button = self.ttk.Button(
            self.actions,
            text="Segna come pagato in loco",
            style="Secondary.TButton",
            command=lambda: self.run_action("paid"),
        )
        self.save_notes_button = self.ttk.Button(
            self.actions,
            text="Salva note",
            style="Secondary.TButton",
            command=self.save_notes,
        )
        self.refresh_button = self.ttk.Button(
            self.actions,
            text="Aggiorna",
            style="Secondary.TButton",
            command=self.refresh,
        )
        self.close_button = self.ttk.Button(
            self.actions,
            text="Chiudi",
            style="Ghost.TButton",
            command=self.root.destroy,
        )

        self._layout_action_buttons(compact=False)

    def _bind_events(self) -> None:
        self.root.bind("<Configure>", self._queue_resize)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())
        self.root.bind("<F5>", lambda _event: self.refresh())
        self.root.bind("<Alt-Left>", lambda _event: self.change_date(-1))
        self.root.bind("<Alt-Right>", lambda _event: self.change_date(1))
        self.date_entry.bind("<Return>", lambda _event: self.apply_date())
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda _event: self.notes_text.focus_set())

    def _queue_resize(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return

        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(70, self._handle_resize)

    def _handle_resize(self) -> None:
        self._resize_job = None
        width = max(self.root.winfo_width(), 900)
        height = max(self.root.winfo_height(), 580)

        scale = min(max(min(width / 1360, height / 780), 0.88), 1.28)
        font_size = max(10, min(15, round(11 * scale)))
        self._configure_fonts(font_size)

        tree_width = max(self.tree.winfo_width(), width - 70)
        minimum_total = sum(self.COLUMN_MIN_WIDTHS.values())
        available = max(tree_width - 4, minimum_total)

        for column in self.COLUMNS:
            target = int(available * self.COLUMN_RATIOS[column])
            self.tree.column(
                column,
                width=max(self.COLUMN_MIN_WIDTHS[column], target),
            )

        self._layout_action_buttons(compact=width < 1120)

    def _configure_fonts(self, font_size: int) -> None:
        if self._last_font_size == font_size:
            return
        self._last_font_size = font_size

        title_size = max(font_size + 5, 16)
        heading_size = max(font_size, 10)
        row_height = max(30, int(font_size * 2.65))
        button_padding_y = max(7, int(font_size * 0.7))

        self.style.configure("Title.TLabel", font=("TkDefaultFont", title_size, "bold"))
        self.style.configure("Summary.TLabel", font=("TkDefaultFont", font_size, "bold"))
        self.style.configure("Section.TLabel", font=("TkDefaultFont", font_size + 1, "bold"))
        self.style.configure("App.Treeview", font=("TkDefaultFont", font_size), rowheight=row_height)
        self.style.configure("App.Treeview.Heading", font=("TkDefaultFont", heading_size, "bold"))

        for style_name in (
            "Primary.TButton",
            "Secondary.TButton",
            "Danger.TButton",
            "Ghost.TButton",
        ):
            self.style.configure(
                style_name,
                font=("TkDefaultFont", font_size, "bold"),
                padding=(12, button_padding_y),
            )

        self.style.configure("App.TEntry", font=("TkDefaultFont", font_size))
        self.notes_text.configure(font=("TkDefaultFont", font_size))

    def _layout_action_buttons(self, compact: bool) -> None:
        layout_name = "compact" if compact else "wide"
        if self._button_layout == layout_name:
            return
        self._button_layout = layout_name

        buttons = (
            self.confirm_button,
            self.cancel_button,
            self.paid_button,
            self.save_notes_button,
            self.refresh_button,
            self.close_button,
        )
        for button in buttons:
            button.grid_forget()

        for column in range(6):
            self.actions.grid_columnconfigure(column, weight=0)

        if compact:
            self.actions.grid_columnconfigure(0, weight=1)
            self.actions.grid_columnconfigure(1, weight=1)
            self.actions.grid_columnconfigure(2, weight=1)

            self.confirm_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 6))
            self.paid_button.grid(row=0, column=1, sticky="ew", padx=4, pady=(0, 6))
            self.save_notes_button.grid(row=0, column=2, sticky="ew", padx=(4, 0), pady=(0, 6))
            self.cancel_button.grid(row=1, column=0, sticky="ew", padx=(0, 4))
            self.refresh_button.grid(row=1, column=1, sticky="ew", padx=4)
            self.close_button.grid(row=1, column=2, sticky="ew", padx=(4, 0))
            return

        self.actions.grid_columnconfigure(5, weight=1)
        self.confirm_button.grid(row=0, column=0, padx=(0, 6))
        self.paid_button.grid(row=0, column=1, padx=6)
        self.save_notes_button.grid(row=0, column=2, padx=6)
        self.refresh_button.grid(row=0, column=3, padx=6)
        self.cancel_button.grid(row=0, column=4, padx=6)
        self.close_button.grid(row=0, column=6, padx=(18, 0), sticky="e")

    def _apply_theme(self) -> None:
        palette = self.palette
        self.root.configure(background=palette["background"])

        self.style.configure("App.TFrame", background=palette["background"])
        self.style.configure("Toolbar.TFrame", background=palette["surface"])
        self.style.configure("Card.TFrame", background=palette["border"])

        self.style.configure(
            "Title.TLabel",
            background=palette["background"],
            foreground=palette["text"],
        )
        self.style.configure(
            "Summary.TLabel",
            background=palette["background"],
            foreground=palette["muted"],
        )
        self.style.configure(
            "Section.TLabel",
            background=palette["surface"],
            foreground=palette["text"],
        )

        self.style.configure(
            "App.Treeview",
            background=palette["surface"],
            fieldbackground=palette["surface"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
        )
        self.style.map(
            "App.Treeview",
            background=[("selected", palette["selection"])],
            foreground=[("selected", palette["selection_text"])],
        )
        self.style.configure(
            "App.Treeview.Heading",
            background=palette["surface_alt"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            relief="flat",
        )
        self.style.map(
            "App.Treeview.Heading",
            background=[("active", palette["surface_alt"])],
        )

        self.style.configure(
            "App.TEntry",
            fieldbackground=palette["surface_alt"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            insertcolor=palette["text"],
            padding=8,
        )

        self._configure_button_style(
            "Primary.TButton",
            palette["primary"],
            "#ffffff",
            palette["primary_hover"],
        )
        self._configure_button_style(
            "Danger.TButton",
            palette["danger"],
            "#ffffff",
            palette["danger_hover"],
        )
        self._configure_button_style(
            "Secondary.TButton",
            palette["surface_alt"],
            palette["text"],
            palette["border"],
        )
        self._configure_button_style(
            "Ghost.TButton",
            palette["background"],
            palette["muted"],
            palette["surface_alt"],
        )

        self.notes_text.configure(
            background=palette["surface"],
            foreground=palette["text"],
            insertbackground=palette["text"],
            selectbackground=palette["selection"],
            selectforeground=palette["selection_text"],
            highlightbackground=palette["border"],
            highlightcolor=palette["primary"],
        )

        self.theme_button_var.set(
            "Tema chiaro" if self.theme_name == "dark" else "Tema scuro"
        )

    def _configure_button_style(
        self,
        style_name: str,
        background: str,
        foreground: str,
        active_background: str,
    ) -> None:
        self.style.configure(
            style_name,
            background=background,
            foreground=foreground,
            bordercolor=background,
            lightcolor=background,
            darkcolor=background,
            relief="flat",
        )
        self.style.map(
            style_name,
            background=[
                ("active", active_background),
                ("pressed", active_background),
                ("disabled", self.palette["surface_alt"]),
            ],
            foreground=[("disabled", self.palette["muted"])],
        )

    def toggle_theme(self) -> None:
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.palette = self._palette_for_theme(self.theme_name)
        self._apply_theme()

    def change_date(self, days: int) -> None:
        self.selected_date += timedelta(days=days)
        self.date_var.set(self.selected_date.isoformat())
        self.refresh()

    def go_today(self) -> None:
        self.selected_date = date.today()
        self.date_var.set(self.selected_date.isoformat())
        self.refresh()

    def apply_date(self) -> None:
        try:
            self.selected_date = date.fromisoformat(self.date_var.get().strip())
        except ValueError:
            self.messagebox.showerror(
                "Data non valida",
                "Inserisci la data nel formato YYYY-MM-DD.",
                parent=self.root,
            )
            return

        self.date_var.set(self.selected_date.isoformat())
        self.refresh()

    def refresh(self) -> None:
        previous_selection = self.selected_booking_id
        bookings = list(_booking_queryset_for_date(self.selected_date))

        for item in self.tree.get_children():
            self.tree.delete(item)

        for booking in bookings:
            values = (
                _booking_code(booking),
                _space_name(booking),
                _customer_name(booking),
                _customer_email(booking),
                _display_value(booking, "status"),
                _display_value(booking, "payment_method"),
                _display_value(booking, "payment_status"),
                _amount_text(booking),
            )
            self.tree.insert("", "end", iid=str(booking.pk), values=values)

        active_spaces = Space.objects.filter(is_active=True)
        total_spaces = active_spaces.count()
        occupied_space_ids = {
            getattr(booking, "space_id", None)
            for booking in bookings
            if not _is_cancelled(booking)
        }
        occupied_space_ids.discard(None)
        available_spaces = max(0, total_spaces - len(occupied_space_ids))

        booking_label = "prenotazione" if len(bookings) == 1 else "prenotazioni"
        space_label = "postazione libera" if available_spaces == 1 else "postazioni libere"
        self.summary_var.set(
            f"{len(bookings)} {booking_label} · {available_spaces} {space_label}"
        )

        if previous_selection is not None and self.tree.exists(str(previous_selection)):
            self.tree.selection_set(str(previous_selection))
            self.tree.focus(str(previous_selection))
            self.tree.see(str(previous_selection))
            self.on_select()
        else:
            self.selected_booking_id = None
            self.notes_text.delete("1.0", "end")
            self._update_action_state()

    def on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_booking_id = None
            self.notes_text.delete("1.0", "end")
            self._update_action_state()
            return

        try:
            booking_id = int(selection[0])
            booking = Booking.objects.get(pk=booking_id)
        except (ValueError, Booking.DoesNotExist):
            self.selected_booking_id = None
            self._update_action_state()
            return

        self.selected_booking_id = booking.pk
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", str(getattr(booking, "notes", "") or ""))
        self._update_action_state(booking)

    def _selected_booking(self) -> Booking | None:
        if self.selected_booking_id is None:
            return None
        try:
            return Booking.objects.get(pk=self.selected_booking_id)
        except Booking.DoesNotExist:
            return None

    def _update_action_state(self, booking: Booking | None = None) -> None:
        has_selection = booking is not None or self.selected_booking_id is not None
        state = "normal" if has_selection else "disabled"

        for button in (
            self.confirm_button,
            self.cancel_button,
            self.paid_button,
            self.save_notes_button,
        ):
            button.configure(state=state)

    def run_action(self, action: str) -> None:
        booking = self._selected_booking()
        if booking is None:
            self.messagebox.showinfo(
                "Nessuna prenotazione",
                "Seleziona prima una prenotazione.",
                parent=self.root,
            )
            return

        code = _booking_code(booking)
        option_by_action = {
            "confirm": "--confirm-booking",
            "cancel": "--cancel-booking",
            "paid": "--mark-paid",
        }

        if action == "cancel":
            confirmed = self.messagebox.askyesno(
                "Cancella prenotazione",
                f"Vuoi cancellare la prenotazione {code}?",
                parent=self.root,
            )
            if not confirmed:
                return

        option = option_by_action[action]
        output = io.StringIO()
        try:
            call_command(
                "bookings_dashboard",
                option,
                code,
                no_color=True,
                stdout=output,
                stderr=output,
            )
        except Exception as exc:
            self.messagebox.showerror(
                "Operazione non riuscita",
                str(exc),
                parent=self.root,
            )
            return

        message = output.getvalue().strip()
        if message:
            self.messagebox.showinfo("Operazione completata", message, parent=self.root)
        self.refresh()

    def save_notes(self) -> None:
        booking = self._selected_booking()
        if booking is None:
            self.messagebox.showinfo(
                "Nessuna prenotazione",
                "Seleziona prima una prenotazione.",
                parent=self.root,
            )
            return

        if not hasattr(booking, "notes"):
            self.messagebox.showerror(
                "Note non disponibili",
                "Il modello Booking non contiene un campo note.",
                parent=self.root,
            )
            return

        booking.notes = self.notes_text.get("1.0", "end-1c")
        update_fields = ["notes"]
        if hasattr(booking, "updated_at"):
            update_fields.append("updated_at")
        booking.save(update_fields=update_fields)
        self.messagebox.showinfo(
            "Note salvate",
            "Le note della prenotazione sono state salvate.",
            parent=self.root,
        )
        self.refresh()


class Command(BaseCommand):
    help = "Open the responsive Cowo d'la val desktop booking dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="dashboard_date",
            help="Initial dashboard date in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--theme",
            choices=("auto", "light", "dark"),
            default="auto",
            help="Desktop theme. Auto follows the host when detectable.",
        )

    def handle(self, *args, **options):
        try:
            import tkinter as tk
            from tkinter import messagebox, ttk
        except ImportError as exc:
            raise CommandError(
                "Tkinter is required for the graphical booking dashboard."
            ) from exc

        dashboard_date = options.get("dashboard_date")
        if dashboard_date:
            try:
                selected_date = date.fromisoformat(dashboard_date)
            except ValueError as exc:
                raise CommandError("--date must use YYYY-MM-DD format.") from exc
        else:
            selected_date = date.today()

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            raise CommandError(
                "Unable to open the graphical display. Check DISPLAY/X11 forwarding."
            ) from exc

        DashboardWindow(
            root=root,
            tk=tk,
            ttk=ttk,
            messagebox=messagebox,
            selected_date=selected_date,
            theme=options["theme"],
        )
        root.mainloop()
