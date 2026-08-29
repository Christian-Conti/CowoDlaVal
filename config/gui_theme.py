import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


DARK = {
    "window": "#151722",
    "surface": "#1E2230",
    "surface2": "#272C3D",
    "border": "#414860",

    "text": "#F3F3F8",
    "muted": "#B7BAC8",

    "primary": "#747CFF",
    "primary_hover": "#8B92FF",

    "success": "#55B889",
    "success_hover": "#69C99C",

    "danger": "#E9788A",
    "danger_hover": "#F08C9C",

    "neutral": "#303751",
    "neutral_hover": "#3C4665",

    "selection": "#50598A",
}


LIGHT = {
    "window": "#F4F5F8",
    "surface": "#FFFFFF",
    "surface2": "#E9EBF2",
    "border": "#C9CDDA",

    "text": "#252736",
    "muted": "#666B7B",

    "primary": "#626BF0",
    "primary_hover": "#747CFF",

    "success": "#3D9B70",
    "success_hover": "#4BAB7F",

    "danger": "#D85E73",
    "danger_hover": "#E9788A",

    "neutral": "#E0E3ED",
    "neutral_hover": "#D1D5E2",

    "selection": "#C8CDFD",
}


UTILITY_FIT = {
    "adatta colonne",
    "fit columns",
    "fit columns automatically",
}

UTILITY_THEME_PREFIXES = (
    "tema",
    "theme",
)

UTILITY_CLOSE = {
    "chiudi",
    "close",
}

HEADER_NEW = {
    "nuovo",
    "new",
    "nuovo evento",
    "new event",
}

HEADER_REFRESH = {
    "aggiorna",
    "refresh",
}


def _norm(value):
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace(":", " ")
        .split()
    )


def _palette(root):
    mode = getattr(
        root,
        "_cowodlaval_theme_mode",
        "dark",
    )

    return LIGHT if mode == "light" else DARK


def _font_size(root):
    width = max(
        root.winfo_width(),
        1,
    )

    if width < 700:
        return 9

    if width < 950:
        return 10

    if width < 1350:
        return 11

    return 12


def _semantic_button(text):
    text = _norm(text)

    danger = (
        "cancella",
        "cancel",
        "elimina",
        "delete",
        "rimuovi",
        "remove",
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
        "nuovo",
        "new",
        "aggiungi",
        "add",
        "applica",
        "apply",
    )

    if any(word in text for word in danger):
        return "Danger.TButton"

    if any(word in text for word in success):
        return "Success.TButton"

    if any(word in text for word in primary):
        return "Primary.TButton"

    return "Neutral.TButton"


def _configure_button(
    style,
    name,
    background,
    hover,
    foreground,
    disabled,
    font,
    padding,
):
    style.configure(
        name,
        background=background,
        foreground=foreground,

        bordercolor=background,
        lightcolor=background,
        darkcolor=background,

        relief="flat",
        borderwidth=0,

        padding=padding,
        font=font,
    )

    style.map(
        name,
        background=[
            ("pressed", hover),
            ("active", hover),
            ("disabled", disabled),
        ],
        foreground=[
            ("disabled", foreground),
        ],
    )


def configure_styles(root):
    colors = _palette(root)

    size = _font_size(root)

    style = ttk.Style(root)

    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    normal = (
        "TkDefaultFont",
        size,
    )

    bold = (
        "TkDefaultFont",
        size,
        "bold",
    )

    title = (
        "TkDefaultFont",
        size + 4,
        "bold",
    )

    padding = (
        max(11, size + 1),
        max(6, size - 3),
    )

    root.configure(
        background=colors["window"],
    )

    # --------------------------------------------------------
    # Frames / labels
    # --------------------------------------------------------

    style.configure(
        ".",
        background=colors["window"],
        foreground=colors["text"],
        font=normal,
    )

    style.configure(
        "TFrame",
        background=colors["window"],
    )

    style.configure(
        "TLabel",
        background=colors["window"],
        foreground=colors["text"],
        font=normal,
    )

    style.configure(
        "Title.TLabel",
        background=colors["window"],
        foreground=colors["text"],
        font=title,
    )

    style.configure(
        "Muted.TLabel",
        background=colors["window"],
        foreground=colors["muted"],
        font=normal,
    )

    # --------------------------------------------------------
    # Inputs
    # --------------------------------------------------------

    style.configure(
        "TEntry",
        fieldbackground=colors["surface"],
        foreground=colors["text"],
        insertcolor=colors["text"],
        bordercolor=colors["border"],
        padding=(8, 6),
        font=normal,
    )

    style.configure(
        "TCombobox",
        fieldbackground=colors["surface"],
        background=colors["surface"],
        foreground=colors["text"],
        arrowcolor=colors["text"],
        bordercolor=colors["border"],
        padding=(8, 6),
        font=normal,
    )

    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", colors["surface"]),
        ],
        foreground=[
            ("readonly", colors["text"]),
        ],
    )

    style.configure(
        "TCheckbutton",
        background=colors["window"],
        foreground=colors["text"],
        font=normal,
    )

    style.configure(
        "TRadiobutton",
        background=colors["window"],
        foreground=colors["text"],
        font=normal,
    )

    # --------------------------------------------------------
    # Notebook
    # --------------------------------------------------------

    style.configure(
        "TNotebook",
        background=colors["window"],
        borderwidth=0,
    )

    style.configure(
        "TNotebook.Tab",
        background=colors["neutral"],
        foreground=colors["text"],
        padding=(13, 7),
        font=bold,
    )

    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", colors["primary"]),
            ("active", colors["neutral_hover"]),
        ],
    )

    # --------------------------------------------------------
    # Treeview
    # --------------------------------------------------------

    style.configure(
        "Treeview",
        background=colors["surface"],
        fieldbackground=colors["surface"],
        foreground=colors["text"],

        bordercolor=colors["border"],
        lightcolor=colors["border"],
        darkcolor=colors["border"],

        rowheight=max(
            25,
            int(size * 2.4),
        ),

        font=normal,
    )

    style.configure(
        "Treeview.Heading",
        background=colors["surface2"],
        foreground=colors["text"],

        bordercolor=colors["border"],

        relief="flat",

        padding=(8, 6),

        font=bold,
    )

    style.map(
        "Treeview",
        background=[
            ("selected", colors["selection"]),
        ],
        foreground=[
            ("selected", colors["text"]),
        ],
    )

    style.map(
        "Treeview.Heading",
        background=[
            ("active", colors["neutral_hover"]),
        ],
    )

    # --------------------------------------------------------
    # Buttons
    # --------------------------------------------------------

    _configure_button(
        style,
        "Neutral.TButton",
        colors["neutral"],
        colors["neutral_hover"],
        colors["text"],
        colors["surface2"],
        bold,
        padding,
    )

    _configure_button(
        style,
        "TButton",
        colors["neutral"],
        colors["neutral_hover"],
        colors["text"],
        colors["surface2"],
        bold,
        padding,
    )

    _configure_button(
        style,
        "Primary.TButton",
        colors["primary"],
        colors["primary_hover"],
        "#FFFFFF",
        colors["surface2"],
        bold,
        padding,
    )

    _configure_button(
        style,
        "Success.TButton",
        colors["success"],
        colors["success_hover"],
        "#FFFFFF",
        colors["surface2"],
        bold,
        padding,
    )

    _configure_button(
        style,
        "Danger.TButton",
        colors["danger"],
        colors["danger_hover"],
        "#FFFFFF",
        colors["surface2"],
        bold,
        padding,
    )

    # Compatibility with old Bookings styles.
    _configure_button(
        style,
        "Accent.TButton",
        colors["primary"],
        colors["primary_hover"],
        "#FFFFFF",
        colors["surface2"],
        bold,
        padding,
    )

    _configure_button(
        style,
        "Secondary.TButton",
        colors["neutral"],
        colors["neutral_hover"],
        colors["text"],
        colors["surface2"],
        bold,
        padding,
    )

    # --------------------------------------------------------
    # Scrollbars
    # --------------------------------------------------------

    style.configure(
        "Vertical.TScrollbar",
        background=colors["neutral"],
        troughcolor=colors["surface"],
        bordercolor=colors["surface"],
        arrowcolor=colors["text"],
    )

    style.configure(
        "Horizontal.TScrollbar",
        background=colors["neutral"],
        troughcolor=colors["surface"],
        bordercolor=colors["surface"],
        arrowcolor=colors["text"],
    )


def _walk(widget):
    yield widget

    try:
        children = widget.winfo_children()
    except tk.TclError:
        return

    for child in children:
        yield from _walk(child)


def _style_widgets(root):
    colors = _palette(root)

    for widget in _walk(root):

        if isinstance(widget, ttk.Button):
            try:
                widget.configure(
                    style=_semantic_button(
                        widget.cget("text")
                    )
                )
            except tk.TclError:
                pass

        elif isinstance(widget, tk.Text):
            try:
                widget.configure(
                    background=colors["surface"],
                    foreground=colors["text"],

                    insertbackground=colors["text"],

                    selectbackground=colors["selection"],
                    selectforeground=colors["text"],

                    relief="flat",
                    borderwidth=1,

                    highlightbackground=colors["border"],
                    highlightcolor=colors["primary"],
                )
            except tk.TclError:
                pass

        elif isinstance(widget, tk.Listbox):
            try:
                widget.configure(
                    background=colors["surface"],
                    foreground=colors["text"],

                    selectbackground=colors["selection"],
                    selectforeground=colors["text"],

                    relief="flat",

                    highlightbackground=colors["border"],
                    highlightcolor=colors["primary"],
                )
            except tk.TclError:
                pass

        elif isinstance(widget, tk.Button):
            style_name = _semantic_button(
                widget.cget("text")
            )

            mapping = {
                "Primary.TButton": (
                    colors["primary"],
                    colors["primary_hover"],
                ),

                "Success.TButton": (
                    colors["success"],
                    colors["success_hover"],
                ),

                "Danger.TButton": (
                    colors["danger"],
                    colors["danger_hover"],
                ),

                "Neutral.TButton": (
                    colors["neutral"],
                    colors["neutral_hover"],
                ),
            }

            bg, active = mapping[
                style_name
            ]

            try:
                widget.configure(
                    background=bg,
                    activebackground=active,

                    foreground=colors["text"],
                    activeforeground=colors["text"],

                    relief="flat",
                    borderwidth=0,

                    padx=12,
                    pady=7,
                )
            except tk.TclError:
                pass


# ============================================================
# FIT COLUMNS
# ============================================================

def _treeviews(root):
    return [
        widget
        for widget in _walk(root)
        if isinstance(widget, ttk.Treeview)
    ]


def fit_columns(root):
    """
    Same 'Adatta colonne' behaviour for Bookings and Events.
    """

    root.update_idletasks()

    for tree in _treeviews(root):
        columns = list(
            tree["columns"]
        )

        if not columns:
            continue

        font_name = tree.cget("font")

        try:
            font = tkfont.nametofont(
                font_name
            )
        except tk.TclError:
            font = tkfont.nametofont(
                "TkDefaultFont"
            )

        available = max(
            tree.winfo_width() - 20,
            300,
        )

        widths = []

        for column in columns:
            heading = str(
                tree.heading(
                    column,
                    "text",
                )
            )

            width = max(
                font.measure(heading) + 32,
                85,
            )

            for item in tree.get_children():
                value = tree.set(
                    item,
                    column,
                )

                width = max(
                    width,
                    font.measure(
                        str(value)
                    ) + 28,
                )

            widths.append(
                min(width, 320)
            )

        total = sum(widths)

        if total < available:
            extra = (
                available - total
            ) / len(widths)

            widths = [
                int(width + extra)
                for width in widths
            ]

        elif total > available:
            scale = (
                available / total
            )

            widths = [
                max(
                    85,
                    int(width * scale),
                )
                for width in widths
            ]

        for column, width in zip(
            columns,
            widths,
        ):
            tree.column(
                column,
                width=width,
                minwidth=70,
                stretch=False,
            )


# ============================================================
# THEME
# ============================================================

def toggle_theme(root):
    current = getattr(
        root,
        "_cowodlaval_theme_mode",
        "dark",
    )

    root._cowodlaval_theme_mode = (
        "light"
        if current == "dark"
        else "dark"
    )

    _refresh(root)


# ============================================================
# UTILITY TOOLBAR
# ============================================================

def _hide(widget):
    try:
        manager = widget.winfo_manager()

        if manager == "grid":
            widget.grid_remove()

        elif manager == "pack":
            widget.pack_forget()

        elif manager == "place":
            widget.place_forget()

    except tk.TclError:
        pass


def _button_y(root, widget):
    try:
        return (
            widget.winfo_rooty()
            - root.winfo_rooty()
        )
    except tk.TclError:
        return 9999


def _find_existing_controls(root):
    """
    Find existing New / Refresh / Fit / Theme / Close controls.

    Fit, Theme and Close are always moved to the standard toolbar.

    New and Refresh are moved only when they already belong to the
    upper part of the GUI.
    """

    result = {
        "new": None,
        "refresh": None,
        "fit": None,
        "theme": None,
        "close": None,
    }

    for widget in _walk(root):

        if not isinstance(
            widget,
            (
                ttk.Button,
                tk.Button,
            ),
        ):
            continue

        try:
            text = _norm(
                widget.cget("text")
            )
        except tk.TclError:
            continue

        if text in UTILITY_FIT:
            result["fit"] = widget

        elif text.startswith(
            UTILITY_THEME_PREFIXES
        ):
            result["theme"] = widget

        elif text in UTILITY_CLOSE:
            result["close"] = widget

        elif (
            text in HEADER_NEW
            and _button_y(
                root,
                widget,
            ) < 180
        ):
            result["new"] = widget

        elif (
            text in HEADER_REFRESH
            and _button_y(
                root,
                widget,
            ) < 180
        ):
            result["refresh"] = widget

    return result


def _make_toolbar(root):
    if getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    ) is not None:
        return

    controls = _find_existing_controls(
        root
    )

    # Remove old copies so there is only ONE toolbar.
    for widget in controls.values():
        if widget is not None:
            _hide(widget)

    toolbar = ttk.Frame(
        root,
        style="TFrame",
    )

    root._cowodlaval_toolbar = toolbar

    buttons = []

    # --------------------------------------------------------
    # Existing Events-specific upper actions
    # --------------------------------------------------------

    if controls["new"] is not None:
        original = controls["new"]

        button = ttk.Button(
            toolbar,
            text=original.cget("text"),
            command=original.invoke,
            style="Primary.TButton",
        )

        buttons.append(button)

    if controls["refresh"] is not None:
        original = controls["refresh"]

        button = ttk.Button(
            toolbar,
            text=original.cget("text"),
            command=original.invoke,
            style="Neutral.TButton",
        )

        buttons.append(button)

    # --------------------------------------------------------
    # UNIVERSAL CONTROLS
    # These are present in BOTH Bookings and Events.
    # --------------------------------------------------------

    fit_button = ttk.Button(
        toolbar,
        text="Adatta colonne",
        command=lambda: fit_columns(
            root
        ),
        style="Neutral.TButton",
    )

    buttons.append(
        fit_button
    )

    theme_button = ttk.Button(
        toolbar,
        text="Tema",
        command=lambda: toggle_theme(
            root
        ),
        style="Neutral.TButton",
    )

    buttons.append(
        theme_button
    )

    close_button = ttk.Button(
        toolbar,
        text="Chiudi",
        command=root.destroy,
        style="Neutral.TButton",
    )

    buttons.append(
        close_button
    )

    toolbar._cowodlaval_buttons = buttons

    _layout_toolbar(root)


def _layout_toolbar(root):
    toolbar = getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    )

    if toolbar is None:
        return

    buttons = toolbar._cowodlaval_buttons

    width = max(
        root.winfo_width(),
        1,
    )

    for button in buttons:
        button.grid_forget()

    for column in range(10):
        toolbar.grid_columnconfigure(
            column,
            weight=0,
        )

    if width >= 1050:
        columns = len(buttons)

    elif width >= 720:
        columns = 3

    else:
        columns = 2

    columns = min(
        columns,
        len(buttons),
    )

    for column in range(columns):
        toolbar.grid_columnconfigure(
            column,
            weight=1,
            uniform="utility",
        )

    for index, button in enumerate(
        buttons
    ):
        button.grid(
            row=index // columns,
            column=index % columns,

            sticky="ew",

            padx=3,
            pady=3,
        )

    # Always top-right, in exactly the same place.
    toolbar.place(
        relx=1.0,
        x=-14,
        y=12,
        anchor="ne",
    )

    toolbar.lift()


# ============================================================
# NORMAL ACTION BUTTON GROUPS
# ============================================================

def _responsive_action_bars(root):
    """
    Standardize groups containing only buttons.

    This does NOT touch forms/date controls.
    """

    width = max(
        root.winfo_width(),
        1,
    )

    if width >= 1400:
        max_columns = 6

    elif width >= 1050:
        max_columns = 4

    elif width >= 760:
        max_columns = 3

    else:
        max_columns = 2

    toolbar = getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    )

    for parent in _walk(root):

        if parent is toolbar:
            continue

        try:
            children = [
                child
                for child in parent.winfo_children()
                if child.winfo_manager()
            ]
        except tk.TclError:
            continue

        if len(children) < 2:
            continue

        if not all(
            isinstance(
                child,
                (
                    ttk.Button,
                    tk.Button,
                ),
            )
            for child in children
        ):
            continue

        if not all(
            child.winfo_manager()
            == "grid"
            for child in children
        ):
            continue

        columns = min(
            max_columns,
            len(children),
        )

        try:
            for column in range(
                len(children)
            ):
                parent.grid_columnconfigure(
                    column,
                    weight=0,
                )

            for column in range(
                columns
            ):
                parent.grid_columnconfigure(
                    column,
                    weight=1,
                    uniform="actions",
                )

            for index, child in enumerate(
                children
            ):
                child.grid_configure(
                    row=index // columns,
                    column=index % columns,

                    sticky="ew",

                    padx=4,
                    pady=4,
                )

        except tk.TclError:
            pass


# ============================================================
# REFRESH
# ============================================================

def _refresh(root):
    try:
        configure_styles(root)

        _style_widgets(root)

        if getattr(
            root,
            "_cowodlaval_toolbar",
            None,
        ) is None:
            _make_toolbar(root)

        _layout_toolbar(root)

        _responsive_action_bars(
            root
        )

    except tk.TclError:
        pass


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def install_unified_gui(root):
    """
    Install the exact same visual system in Bookings and Events.
    """

    if getattr(
        root,
        "_cowodlaval_unified_gui",
        False,
    ):
        return

    root._cowodlaval_unified_gui = True

    if not hasattr(
        root,
        "_cowodlaval_theme_mode",
    ):
        root._cowodlaval_theme_mode = "dark"

    pending = {
        "job": None,
    }

    def schedule(_event=None):
        job = pending["job"]

        if job is not None:
            try:
                root.after_cancel(
                    job
                )
            except tk.TclError:
                pass

        try:
            pending["job"] = root.after(
                90,
                lambda: _refresh(
                    root
                ),
            )
        except tk.TclError:
            pass

    root.bind(
        "<Configure>",
        schedule,
        add="+",
    )

    # Run after widgets have been created.
    root.after_idle(
        lambda: _refresh(root)
    )

    root.after(
        300,
        lambda: _refresh(root),
    )


# ============================================================
# COMPATIBILITY WITH PREVIOUS PATCHES
# ============================================================

def apply_cowodlaval_theme(root):
    install_unified_gui(root)


def build_standard_toolbar(
    parent,
    *,
    fit_command=None,
    theme_command=None,
    close_command=None,
):
    """
    Compatibility helper for any code generated by previous patches.
    """

    toolbar = ttk.Frame(parent)

    if fit_command is not None:
        ttk.Button(
            toolbar,
            text="Adatta colonne",
            command=fit_command,
            style="Neutral.TButton",
        ).pack(
            side="left",
            padx=3,
        )

    if theme_command is not None:
        ttk.Button(
            toolbar,
            text="Tema",
            command=theme_command,
            style="Neutral.TButton",
        ).pack(
            side="left",
            padx=3,
        )

    if close_command is not None:
        ttk.Button(
            toolbar,
            text="Chiudi",
            command=close_command,
            style="Neutral.TButton",
        ).pack(
            side="left",
            padx=3,
        )

    return toolbar

# >>> cowodlaval-final-layout-v4 >>>

# ============================================================
# FINAL SHARED DESKTOP LAYOUT
# ============================================================

def _is_descendant(widget, parent):
    if parent is None:
        return False

    current = widget

    while current is not None:
        if current is parent:
            return True

        current = getattr(
            current,
            "master",
            None,
        )

    return False


def _widget_y(root, widget):
    try:
        return (
            widget.winfo_rooty()
            - root.winfo_rooty()
        )
    except tk.TclError:
        return 0


def _window_kind(root):
    title = str(
        root.title()
    ).lower()

    if "event" in title:
        return "events"

    return "bookings"


def _window_title(root):
    if _window_kind(root) == "events":
        return "Cowo d'la val · Eventi"

    return "Cowo d'la val · Prenotazioni"


# ============================================================
# STANDARD NAMES
# ============================================================

ACTION_SPECS = {
    "bookings": [
        {
            "label": "Conferma",
            "aliases": {
                "conferma",
                "confirm",
            },
            "style": "Success.TButton",
            "prefer": "bottom",
        },
        {
            "label": "Segna pagato",
            "aliases": {
                "segna come pagato",
                "segna come pagato in loco",
                "segna pagato",
                "mark paid",
                "mark as paid",
                "mark as paid onsite",
            },
            "style": "Success.TButton",
            "prefer": "bottom",
        },
        {
            "label": "Salva note",
            "aliases": {
                "salva note",
                "save notes",
                "save note",
            },
            "style": "Success.TButton",
            "prefer": "bottom",
        },
        {
            "label": "Aggiorna",
            "aliases": {
                "aggiorna",
                "refresh",
                "update",
            },
            "style": "Neutral.TButton",
            "prefer": "bottom",
        },
        {
            "label": "Cancella prenotazione",
            "aliases": {
                "cancella prenotazione",
                "cancel booking",
                "annulla prenotazione",
            },
            "style": "Danger.TButton",
            "prefer": "bottom",
        },
    ],

    "events": [
        {
            "label": "Nuovo evento",
            "aliases": {
                "nuovo",
                "new",
                "nuovo evento",
                "new event",
            },
            "style": "Primary.TButton",
            "prefer": "top",
        },
        {
            "label": "Aggiorna",
            "aliases": {
                "aggiorna",
                "refresh",
                "update",
            },
            "style": "Neutral.TButton",
            "prefer": "top",
        },
        {
            "label": "Salva evento",
            "aliases": {
                "salva",
                "save",
                "salva evento",
                "save event",
            },
            "style": "Success.TButton",
            "prefer": "bottom",
        },
        {
            "label": "Aggiungi immagini",
            "aliases": {
                "aggiungi immagini",
                "add images",
                "add image",
            },
            "style": "Primary.TButton",
            "prefer": "bottom",
        },
        {
            "label": "Rimuovi immagine",
            "aliases": {
                "rimuovi immagine",
                "rimuovi immagini",
                "remove image",
                "remove images",
            },
            "style": "Danger.TButton",
            "prefer": "bottom",
        },
        {
            "label": "Elimina evento",
            "aliases": {
                "elimina evento",
                "delete event",
            },
            "style": "Danger.TButton",
            "prefer": "bottom",
        },
    ],
}


UTILITY_ALIASES = {
    "adatta colonne",
    "fit columns",
    "tema",
    "tema chiaro",
    "tema scuro",
    "theme",
    "light theme",
    "dark theme",
    "chiudi",
    "close",
}


def _widget_text(widget):
    try:
        return _norm(
            widget.cget("text")
        )
    except tk.TclError:
        return ""


# ============================================================
# FIND ORIGINAL ACTION BUTTONS
# ============================================================

def _find_action_source(
    root,
    aliases,
    prefer,
):
    header = getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    )

    bottom = getattr(
        root,
        "_cowodlaval_bottom_bar",
        None,
    )

    candidates = []

    for widget in _walk(root):

        if not isinstance(
            widget,
            (
                ttk.Button,
                tk.Button,
            ),
        ):
            continue

        if _is_descendant(
            widget,
            header,
        ):
            continue

        if _is_descendant(
            widget,
            bottom,
        ):
            continue

        text = _widget_text(
            widget
        )

        if text not in aliases:
            continue

        candidates.append(
            (
                _widget_y(
                    root,
                    widget,
                ),
                widget,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda value: value[0]
    )

    if prefer == "top":
        return candidates[0][1]

    return candidates[-1][1]


def _collect_action_sources(root):
    kind = _window_kind(
        root
    )

    result = []

    for spec in ACTION_SPECS[kind]:

        source = _find_action_source(
            root,
            spec["aliases"],
            spec["prefer"],
        )

        if source is None:
            continue

        result.append(
            (
                spec,
                source,
            )
        )

    return result


# ============================================================
# HEADER
#
# SAME EXACT STRUCTURE FOR EVENTS AND BOOKINGS
# ============================================================

def _booking_summary(root):
    for widget in _walk(root):

        if not isinstance(
            widget,
            (
                ttk.Label,
                tk.Label,
            ),
        ):
            continue

        if _is_descendant(
            widget,
            getattr(
                root,
                "_cowodlaval_toolbar",
                None,
            ),
        ):
            continue

        text = str(
            widget.cget("text")
        ).strip()

        lower = text.lower()

        if (
            "prenotazioni" in lower
            and "postazioni" in lower
        ):
            return text

    count = len(
        _treeviews(root)[0].get_children()
    ) if _treeviews(root) else 0

    return (
        f"{count} "
        f"{'prenotazione' if count == 1 else 'prenotazioni'}"
    )


def _events_summary(root):
    count = 0

    trees = _treeviews(
        root
    )

    if trees:
        count = len(
            trees[0].get_children()
        )

    return (
        f"{count} "
        f"{'evento' if count == 1 else 'eventi'}"
    )


def _header_summary(root):
    if _window_kind(root) == "events":
        return _events_summary(
            root
        )

    return _booking_summary(
        root
    )


def _hide_original_headers(root):
    header = getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    )

    for widget in _walk(root):

        if _is_descendant(
            widget,
            header,
        ):
            continue

        # ----------------------------------------------------
        # Old duplicated titles
        # ----------------------------------------------------

        if isinstance(
            widget,
            (
                ttk.Label,
                tk.Label,
            ),
        ):
            text = _widget_text(
                widget
            )

            if text.startswith(
                "cowo d'la val"
            ):
                _hide(
                    widget
                )

            continue

        # ----------------------------------------------------
        # Old utility buttons
        # ----------------------------------------------------

        if not isinstance(
            widget,
            (
                ttk.Button,
                tk.Button,
            ),
        ):
            continue

        text = _widget_text(
            widget
        )

        if text in UTILITY_ALIASES:
            _hide(
                widget
            )


def _make_toolbar(root):
    if getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    ) is not None:
        return

    root.title(
        _window_title(
            root
        )
    )

    try:
        root.minsize(
            760,
            560,
        )
    except tk.TclError:
        pass

    header = ttk.Frame(
        root,
        style="TFrame",
    )

    root._cowodlaval_toolbar = header

    # --------------------------------------------------------
    # TITLE AREA
    # --------------------------------------------------------

    title_box = ttk.Frame(
        header,
        style="TFrame",
    )

    title_box.grid(
        row=0,
        column=0,
        sticky="w",
        padx=(10, 8),
        pady=(5, 4),
    )

    title = ttk.Label(
        title_box,
        text=_window_title(
            root
        ),
        style="Title.TLabel",
    )

    title.pack(
        anchor="w",
    )

    subtitle = ttk.Label(
        title_box,
        text=_header_summary(
            root
        ),
        style="Muted.TLabel",
    )

    subtitle.pack(
        anchor="w",
        pady=(1, 0),
    )

    root._cowodlaval_header_subtitle = (
        subtitle
    )

    # --------------------------------------------------------
    # UNIVERSAL CONTROLS
    # EXACT SAME POSITION IN BOTH APPS
    # --------------------------------------------------------

    controls = ttk.Frame(
        header,
        style="TFrame",
    )

    controls.grid(
        row=0,
        column=1,
        sticky="e",
        padx=(8, 8),
        pady=6,
    )

    fit_button = ttk.Button(
        controls,
        text="Adatta colonne",
        command=lambda: fit_columns(
            root
        ),
        style="Neutral.TButton",
    )

    theme_button = ttk.Button(
        controls,
        text="Tema",
        command=lambda: toggle_theme(
            root
        ),
        style="Neutral.TButton",
    )

    close_button = ttk.Button(
        controls,
        text="Chiudi",
        command=root.destroy,
        style="Neutral.TButton",
    )

    fit_button.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=2,
    )

    theme_button.grid(
        row=0,
        column=1,
        sticky="ew",
        padx=2,
    )

    close_button.grid(
        row=0,
        column=2,
        sticky="ew",
        padx=2,
    )

    header.grid_columnconfigure(
        0,
        weight=1,
    )

    header.grid_columnconfigure(
        1,
        weight=0,
    )

    root._cowodlaval_header_buttons = [
        fit_button,
        theme_button,
        close_button,
    ]

    _hide_original_headers(
        root
    )


def _layout_toolbar(root):
    header = getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    )

    if header is None:
        return

    # Same 72px header in BOTH applications.
    header.place(
        x=0,
        y=0,
        relwidth=1.0,
        height=72,
    )

    header.lift()

    subtitle = getattr(
        root,
        "_cowodlaval_header_subtitle",
        None,
    )

    if subtitle is not None:
        try:
            subtitle.configure(
                text=_header_summary(
                    root
                )
            )
        except tk.TclError:
            pass


# ============================================================
# STANDARD BOTTOM ACTION BAR
# ============================================================

def _destroy_bottom_bar(root):
    bottom = getattr(
        root,
        "_cowodlaval_bottom_bar",
        None,
    )

    if bottom is not None:
        try:
            bottom.destroy()
        except tk.TclError:
            pass

    root._cowodlaval_bottom_bar = None
    root._cowodlaval_bottom_pairs = []
    root._cowodlaval_bottom_signature = None


def _make_bottom_bar(root):
    sources = _collect_action_sources(
        root
    )

    signature = tuple(
        (
            spec["label"],
            str(source),
        )
        for spec, source in sources
    )

    if (
        getattr(
            root,
            "_cowodlaval_bottom_signature",
            None,
        )
        == signature
        and getattr(
            root,
            "_cowodlaval_bottom_bar",
            None,
        )
        is not None
    ):
        return

    old = getattr(
        root,
        "_cowodlaval_bottom_bar",
        None,
    )

    if old is not None:
        try:
            old.destroy()
        except tk.TclError:
            pass

    if not sources:
        return

    bar = ttk.Frame(
        root,
        style="TFrame",
    )

    root._cowodlaval_bottom_bar = bar
    root._cowodlaval_bottom_signature = signature

    separator = ttk.Separator(
        bar,
        orient="horizontal",
    )

    separator.grid(
        row=0,
        column=0,
        columnspan=12,
        sticky="ew",
        pady=(0, 4),
    )

    pairs = []

    for spec, source in sources:

        # Hide the original control.
        _hide(
            source
        )

        button = ttk.Button(
            bar,
            text=spec["label"],
            command=lambda w=source: w.invoke(),
            style=spec["style"],
        )

        pairs.append(
            (
                button,
                source,
                spec,
            )
        )

    root._cowodlaval_bottom_pairs = (
        pairs
    )

    _layout_bottom_bar(
        root
    )


def _layout_bottom_bar(root):
    bar = getattr(
        root,
        "_cowodlaval_bottom_bar",
        None,
    )

    if bar is None:
        return

    pairs = getattr(
        root,
        "_cowodlaval_bottom_pairs",
        [],
    )

    if not pairs:
        return

    width = max(
        root.winfo_width(),
        1,
    )

    buttons = [
        pair[0]
        for pair in pairs
    ]

    for button in buttons:
        button.grid_forget()

    for column in range(12):
        bar.grid_columnconfigure(
            column,
            weight=0,
        )

    # --------------------------------------------------------
    # Same responsive layout in both GUIs
    # --------------------------------------------------------

    if width >= 1100:
        columns = len(
            buttons
        )

    elif width >= 650:
        columns = min(
            3,
            len(buttons),
        )

    else:
        columns = min(
            2,
            len(buttons),
        )

    for column in range(columns):
        bar.grid_columnconfigure(
            column,
            weight=1,
            uniform="bottom-actions",
        )

    for index, button in enumerate(
        buttons
    ):
        button.grid(
            row=1 + (
                index // columns
            ),
            column=index % columns,
            sticky="ew",
            padx=3,
            pady=2,
        )

    rows = (
        len(buttons)
        + columns
        - 1
    ) // columns

    height = (
        42
        if rows == 1
        else 72
        if rows == 2
        else 102
    )

    bar.place(
        x=0,
        rely=1.0,
        y=-height,
        relwidth=1.0,
        height=height,
    )

    bar.lift()


# ============================================================
# MIRROR ORIGINAL BUTTON STATE
# ============================================================

def _sync_bottom_states(root):
    pairs = getattr(
        root,
        "_cowodlaval_bottom_pairs",
        [],
    )

    for button, source, spec in pairs:

        try:
            if isinstance(
                source,
                ttk.Button,
            ):
                disabled = (
                    source.instate(
                        ["disabled"]
                    )
                )

            else:
                disabled = (
                    str(
                        source.cget(
                            "state"
                        )
                    )
                    == "disabled"
                )

            if disabled:
                button.state(
                    ["disabled"]
                )
            else:
                button.state(
                    ["!disabled"]
                )

            # Reapply semantic style explicitly.
            button.configure(
                style=spec["style"]
            )

        except tk.TclError:
            pass


# ============================================================
# REMOVE ALL OLD DUPLICATED CONTROLS
# ============================================================

def _cleanup_old_controls(root):
    header = getattr(
        root,
        "_cowodlaval_toolbar",
        None,
    )

    bottom = getattr(
        root,
        "_cowodlaval_bottom_bar",
        None,
    )

    kind = _window_kind(
        root
    )

    all_action_aliases = set()

    for spec in ACTION_SPECS[kind]:
        all_action_aliases.update(
            spec["aliases"]
        )

    for widget in _walk(root):

        if _is_descendant(
            widget,
            header,
        ):
            continue

        if _is_descendant(
            widget,
            bottom,
        ):
            continue

        # Old title
        if isinstance(
            widget,
            (
                ttk.Label,
                tk.Label,
            ),
        ):
            text = _widget_text(
                widget
            )

            if text.startswith(
                "cowo d'la val"
            ):
                _hide(
                    widget
                )

            continue

        if not isinstance(
            widget,
            (
                ttk.Button,
                tk.Button,
            ),
        ):
            continue

        text = _widget_text(
            widget
        )

        # Universal duplicates
        if text in UTILITY_ALIASES:
            _hide(
                widget
            )
            continue

        # Operational buttons have already been copied into
        # the standard bottom bar.
        if (
            getattr(
                root,
                "_cowodlaval_bottom_bar",
                None,
            )
            is not None
            and text in all_action_aliases
        ):
            _hide(
                widget
            )


# ============================================================
# FINAL REFRESH
# ============================================================

def _refresh(root):
    try:
        configure_styles(
            root
        )

        _style_widgets(
            root
        )

        if getattr(
            root,
            "_cowodlaval_toolbar",
            None,
        ) is None:
            _make_toolbar(
                root
            )

        _make_bottom_bar(
            root
        )

        _cleanup_old_controls(
            root
        )

        _layout_toolbar(
            root
        )

        _layout_bottom_bar(
            root
        )

        _sync_bottom_states(
            root
        )

    except tk.TclError:
        pass


# <<< cowodlaval-final-layout-v4 <<<
