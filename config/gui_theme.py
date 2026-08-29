import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


COLORS = {
    "window": "#151722",
    "surface": "#1E2230",
    "surface_alt": "#252B40",
    "border": "#414862",

    "text": "#F1F1F7",
    "muted": "#B9B9C9",

    "primary": "#7C83FF",
    "primary_active": "#9197FF",

    "success": "#56B88A",
    "success_active": "#69C89A",

    "danger": "#EE8294",
    "danger_active": "#F29BA9",

    "neutral": "#29314D",
    "neutral_active": "#35405F",

    "selection": "#4E568A",
}


ORIGINAL_BUTTON = ttk.Button


def semantic_style(text):
    text = text.strip().lower()

    danger = (
        "cancella",
        "delete",
        "elimina",
        "remove",
        "rimuovi",
        "annulla prenotazione",
    )

    success = (
        "conferma",
        "confirm",
        "salva",
        "save",
        "pagato",
        "paid",
    )

    primary = (
        "applica",
        "apply",
        "nuovo",
        "new",
        "aggiungi",
        "add",
    )

    neutral = (
        "aggiorna",
        "refresh",
        "update",
        "chiudi",
        "close",
        "oggi",
        "today",
        "precedente",
        "previous",
        "successivo",
        "next",
        "tema",
        "theme",
        "adatta",
        "fit",
    )

    if any(word in text for word in danger):
        return "Danger.TButton"

    if any(word in text for word in success):
        return "Success.TButton"

    if any(word in text for word in primary):
        return "Primary.TButton"

    if any(word in text for word in neutral):
        return "Neutral.TButton"

    return "Neutral.TButton"


def configure_styles(root, base_size=11):
    style = ttk.Style(root)

    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(
        background=COLORS["window"],
    )

    normal_font = (
        "TkDefaultFont",
        base_size,
    )

    button_font = (
        "TkDefaultFont",
        base_size,
        "bold",
    )

    heading_font = (
        "TkDefaultFont",
        base_size,
        "bold",
    )

    style.configure(
        ".",
        background=COLORS["window"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["surface"],
        font=normal_font,
    )

    style.configure(
        "TFrame",
        background=COLORS["window"],
    )

    style.configure(
        "TLabel",
        background=COLORS["window"],
        foreground=COLORS["text"],
        font=normal_font,
    )

    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        insertcolor=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=6,
        font=normal_font,
    )

    style.configure(
        "TNotebook",
        background=COLORS["window"],
        borderwidth=0,
    )

    style.configure(
        "TNotebook.Tab",
        background=COLORS["neutral"],
        foreground=COLORS["text"],
        padding=(12, 6),
        font=normal_font,
    )

    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", COLORS["primary"]),
        ],
    )

    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        rowheight=max(26, int(base_size * 2.25)),
        font=normal_font,
    )

    style.configure(
        "Treeview.Heading",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        relief="flat",
        padding=(7, 5),
        font=heading_font,
    )

    style.map(
        "Treeview",
        background=[
            ("selected", COLORS["selection"]),
        ],
        foreground=[
            ("selected", COLORS["text"]),
        ],
    )

    configure_button(
        style,
        "Neutral.TButton",
        COLORS["neutral"],
        COLORS["neutral_active"],
        button_font,
    )

    configure_button(
        style,
        "Primary.TButton",
        COLORS["primary"],
        COLORS["primary_active"],
        button_font,
    )

    configure_button(
        style,
        "Success.TButton",
        COLORS["success"],
        COLORS["success_active"],
        button_font,
    )

    configure_button(
        style,
        "Danger.TButton",
        COLORS["danger"],
        COLORS["danger_active"],
        button_font,
    )

    # Keep generic/custom legacy button styles visually coherent.
    for name in (
        "TButton",
        "Accent.TButton",
        "Secondary.TButton",
    ):
        configure_button(
            style,
            name,
            COLORS["neutral"],
            COLORS["neutral_active"],
            button_font,
        )


def configure_button(
    style,
    name,
    background,
    active_background,
    font,
):
    style.configure(
        name,
        background=background,
        foreground=COLORS["text"],
        bordercolor=background,
        lightcolor=background,
        darkcolor=background,
        padding=(13, 8),
        relief="flat",
        font=font,
    )

    style.map(
        name,
        background=[
            ("active", active_background),
            ("pressed", active_background),
            ("disabled", COLORS["surface_alt"]),
        ],
        foreground=[
            ("disabled", COLORS["muted"]),
        ],
    )


def walk_widgets(widget):
    yield widget

    for child in widget.winfo_children():
        yield from walk_widgets(child)


def style_buttons(root):
    for widget in walk_widgets(root):
        if isinstance(widget, ORIGINAL_BUTTON):
            try:
                text = str(widget.cget("text"))
                widget.configure(
                    style=semantic_style(text)
                )
            except tk.TclError:
                pass


def responsive_button_bars(root):
    """
    Reflow frames containing only buttons.

    This intentionally ignores mixed frames containing labels, entries,
    etc., so date/navigation forms are never rearranged unexpectedly.
    """
    width = max(root.winfo_width(), 1)

    if width >= 1200:
        columns = 6
    elif width >= 900:
        columns = 4
    elif width >= 650:
        columns = 3
    else:
        columns = 2

    for parent in walk_widgets(root):
        children = [
            child
            for child in parent.winfo_children()
            if child.winfo_manager()
        ]

        if len(children) < 2:
            continue

        if not all(
            isinstance(child, ORIGINAL_BUTTON)
            for child in children
        ):
            continue

        if not all(
            child.winfo_manager() == "grid"
            for child in children
        ):
            continue

        actual_columns = min(
            columns,
            len(children),
        )

        for column in range(len(children)):
            try:
                parent.grid_columnconfigure(
                    column,
                    weight=0,
                )
            except tk.TclError:
                pass

        for column in range(actual_columns):
            parent.grid_columnconfigure(
                column,
                weight=1,
                uniform="actions",
            )

        for index, button in enumerate(children):
            button.grid_configure(
                row=index // actual_columns,
                column=index % actual_columns,
                sticky="ew",
                padx=4,
                pady=4,
            )


def responsive_update(root):
    width = max(root.winfo_width(), 1)

    if width < 700:
        size = 9
    elif width < 1000:
        size = 10
    elif width < 1400:
        size = 11
    else:
        size = 12

    configure_styles(
        root,
        base_size=size,
    )

    style_buttons(root)
    responsive_button_bars(root)


def apply_cowodlaval_theme(root):
    configure_styles(root)

    pending = {"job": None}

    def schedule_update(_event=None):
        if pending["job"] is not None:
            try:
                root.after_cancel(
                    pending["job"]
                )
            except tk.TclError:
                pass

        pending["job"] = root.after(
            80,
            lambda: responsive_update(root),
        )

    root.bind(
        "<Configure>",
        schedule_update,
        add="+",
    )

    root.after_idle(
        lambda: responsive_update(root)
    )
