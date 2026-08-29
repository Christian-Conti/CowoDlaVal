import tkinter as tk
from tkinter import ttk


COLORS = {
    "window": "#161823",

    "surface": "#1E2230",
    "surface_alt": "#272C3E",
    "surface_hover": "#30364A",

    "border": "#414861",

    "text": "#F3F3F8",
    "muted": "#B8BAC8",

    "primary": "#747CFF",
    "primary_hover": "#8A91FF",

    "success": "#55B88A",
    "success_hover": "#69C99C",

    "danger": "#E9788B",
    "danger_hover": "#F08C9D",

    "neutral": "#303752",
    "neutral_hover": "#3B4565",

    "selection": "#50598A",
}


SEMANTIC_WORDS = {
    "Danger.TButton": (
        "cancella",
        "cancel booking",
        "delete",
        "elimina",
        "remove",
        "rimuovi",
        "abbandona",
        "abandon",
    ),

    "Success.TButton": (
        "conferma",
        "confirm",
        "salva",
        "save",
        "pagato",
        "paid",
    ),

    "Primary.TButton": (
        "applica",
        "apply",
        "nuovo",
        "new",
        "aggiungi",
        "add image",
        "add event",
    ),

    "Neutral.TButton": (
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
    ),
}


def _button_style(text):
    value = str(text or "").strip().lower()

    for style_name, words in SEMANTIC_WORDS.items():
        if any(word in value for word in words):
            return style_name

    return "Neutral.TButton"


def _button_style_config(
    style,
    name,
    background,
    hover,
    font,
    padding,
):
    style.configure(
        name,
        background=background,
        foreground=COLORS["text"],
        bordercolor=background,
        lightcolor=background,
        darkcolor=background,
        relief="flat",
        padding=padding,
        font=font,
    )

    style.map(
        name,
        background=[
            ("pressed", hover),
            ("active", hover),
            ("disabled", COLORS["surface_alt"]),
        ],
        foreground=[
            ("disabled", COLORS["muted"]),
        ],
    )


def _font_size(width):
    if width < 700:
        return 9

    if width < 950:
        return 10

    if width < 1350:
        return 11

    return 12


def configure_styles(root):
    width = max(root.winfo_width(), 800)
    size = _font_size(width)

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
        size,
    )

    bold_font = (
        "TkDefaultFont",
        size,
        "bold",
    )

    title_font = (
        "TkDefaultFont",
        size + 3,
        "bold",
    )

    button_padding = (
        max(9, size),
        max(6, size - 2),
    )

    # --------------------------------------------------------
    # Generic widgets
    # --------------------------------------------------------

    style.configure(
        ".",
        background=COLORS["window"],
        foreground=COLORS["text"],
        font=normal_font,
    )

    style.configure(
        "TFrame",
        background=COLORS["window"],
    )

    style.configure(
        "Card.TFrame",
        background=COLORS["surface"],
    )

    style.configure(
        "TLabel",
        background=COLORS["window"],
        foreground=COLORS["text"],
        font=normal_font,
    )

    style.configure(
        "Title.TLabel",
        background=COLORS["window"],
        foreground=COLORS["text"],
        font=title_font,
    )

    style.configure(
        "Muted.TLabel",
        background=COLORS["window"],
        foreground=COLORS["muted"],
        font=normal_font,
    )

    # --------------------------------------------------------
    # Entries / Combobox
    # --------------------------------------------------------

    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        insertcolor=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=(8, 6),
        font=normal_font,
    )

    style.configure(
        "TCombobox",
        fieldbackground=COLORS["surface"],
        background=COLORS["surface"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=(8, 6),
        font=normal_font,
    )

    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", COLORS["surface"]),
        ],
        foreground=[
            ("readonly", COLORS["text"]),
        ],
        selectbackground=[
            ("readonly", COLORS["selection"]),
        ],
    )

    # --------------------------------------------------------
    # Check / Radio
    # --------------------------------------------------------

    style.configure(
        "TCheckbutton",
        background=COLORS["window"],
        foreground=COLORS["text"],
        font=normal_font,
    )

    style.configure(
        "TRadiobutton",
        background=COLORS["window"],
        foreground=COLORS["text"],
        font=normal_font,
    )

    # --------------------------------------------------------
    # Notebook
    # --------------------------------------------------------

    style.configure(
        "TNotebook",
        background=COLORS["window"],
        borderwidth=0,
    )

    style.configure(
        "TNotebook.Tab",
        background=COLORS["neutral"],
        foreground=COLORS["text"],
        padding=(14, 7),
        font=bold_font,
        borderwidth=0,
    )

    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", COLORS["primary"]),
            ("active", COLORS["neutral_hover"]),
        ],
    )

    # --------------------------------------------------------
    # Treeview
    # --------------------------------------------------------

    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        rowheight=max(25, int(size * 2.45)),
        font=normal_font,
    )

    style.configure(
        "Treeview.Heading",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        relief="flat",
        padding=(8, 6),
        font=bold_font,
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

    style.map(
        "Treeview.Heading",
        background=[
            ("active", COLORS["surface_hover"]),
        ],
    )

    # --------------------------------------------------------
    # Scrollbars
    # --------------------------------------------------------

    style.configure(
        "Vertical.TScrollbar",
        background=COLORS["neutral"],
        troughcolor=COLORS["surface"],
        arrowcolor=COLORS["text"],
        bordercolor=COLORS["surface"],
    )

    style.configure(
        "Horizontal.TScrollbar",
        background=COLORS["neutral"],
        troughcolor=COLORS["surface"],
        arrowcolor=COLORS["text"],
        bordercolor=COLORS["surface"],
    )

    # --------------------------------------------------------
    # Buttons
    # --------------------------------------------------------

    _button_style_config(
        style,
        "TButton",
        COLORS["neutral"],
        COLORS["neutral_hover"],
        bold_font,
        button_padding,
    )

    _button_style_config(
        style,
        "Neutral.TButton",
        COLORS["neutral"],
        COLORS["neutral_hover"],
        bold_font,
        button_padding,
    )

    _button_style_config(
        style,
        "Primary.TButton",
        COLORS["primary"],
        COLORS["primary_hover"],
        bold_font,
        button_padding,
    )

    _button_style_config(
        style,
        "Success.TButton",
        COLORS["success"],
        COLORS["success_hover"],
        bold_font,
        button_padding,
    )

    _button_style_config(
        style,
        "Danger.TButton",
        COLORS["danger"],
        COLORS["danger_hover"],
        bold_font,
        button_padding,
    )

    # Legacy styles used by existing dashboards.
    _button_style_config(
        style,
        "Accent.TButton",
        COLORS["primary"],
        COLORS["primary_hover"],
        bold_font,
        button_padding,
    )

    _button_style_config(
        style,
        "Secondary.TButton",
        COLORS["neutral"],
        COLORS["neutral_hover"],
        bold_font,
        button_padding,
    )


def _walk(widget):
    yield widget

    try:
        children = widget.winfo_children()
    except tk.TclError:
        return

    for child in children:
        yield from _walk(child)


def _style_existing_widgets(root):
    for widget in _walk(root):

        # ----------------------------------------------------
        # ttk.Button semantic colours
        # ----------------------------------------------------

        if isinstance(widget, ttk.Button):
            try:
                widget.configure(
                    style=_button_style(
                        widget.cget("text")
                    )
                )
            except tk.TclError:
                pass

        # ----------------------------------------------------
        # Old tk.Button widgets
        # ----------------------------------------------------

        elif isinstance(widget, tk.Button):
            text = str(
                widget.cget("text")
            )

            semantic = _button_style(text)

            palette = {
                "Primary.TButton": (
                    COLORS["primary"],
                    COLORS["primary_hover"],
                ),
                "Success.TButton": (
                    COLORS["success"],
                    COLORS["success_hover"],
                ),
                "Danger.TButton": (
                    COLORS["danger"],
                    COLORS["danger_hover"],
                ),
                "Neutral.TButton": (
                    COLORS["neutral"],
                    COLORS["neutral_hover"],
                ),
            }

            bg, active = palette.get(
                semantic,
                (
                    COLORS["neutral"],
                    COLORS["neutral_hover"],
                ),
            )

            try:
                widget.configure(
                    background=bg,
                    activebackground=active,
                    foreground=COLORS["text"],
                    activeforeground=COLORS["text"],
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=0,
                    padx=12,
                    pady=7,
                )
            except tk.TclError:
                pass

        # ----------------------------------------------------
        # Text areas
        # ----------------------------------------------------

        elif isinstance(widget, tk.Text):
            try:
                widget.configure(
                    background=COLORS["surface"],
                    foreground=COLORS["text"],
                    insertbackground=COLORS["text"],
                    selectbackground=COLORS["selection"],
                    selectforeground=COLORS["text"],
                    relief="flat",
                    borderwidth=1,
                    highlightbackground=COLORS["border"],
                    highlightcolor=COLORS["primary"],
                )
            except tk.TclError:
                pass

        # ----------------------------------------------------
        # Listbox
        # ----------------------------------------------------

        elif isinstance(widget, tk.Listbox):
            try:
                widget.configure(
                    background=COLORS["surface"],
                    foreground=COLORS["text"],
                    selectbackground=COLORS["selection"],
                    selectforeground=COLORS["text"],
                    relief="flat",
                    borderwidth=1,
                    highlightbackground=COLORS["border"],
                    highlightcolor=COLORS["primary"],
                )
            except tk.TclError:
                pass


def _responsive_button_frames(root):
    """
    Reflow only frames whose visible children are ALL buttons.

    This avoids touching forms containing labels/entries while allowing
    action bars to become 1, 2 or 3 rows depending on window width.
    """

    width = max(
        root.winfo_width(),
        1,
    )

    if width >= 1450:
        max_columns = 6
    elif width >= 1100:
        max_columns = 4
    elif width >= 800:
        max_columns = 3
    else:
        max_columns = 2

    for parent in _walk(root):
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

        # Only reflow grid-based button bars.
        if not all(
            child.winfo_manager() == "grid"
            for child in children
        ):
            continue

        columns = min(
            max_columns,
            len(children),
        )

        try:
            for index in range(
                len(children)
            ):
                parent.grid_columnconfigure(
                    index,
                    weight=0,
                )

            for index in range(columns):
                parent.grid_columnconfigure(
                    index,
                    weight=1,
                    uniform="cowodlaval-actions",
                )

            for index, button in enumerate(
                children
            ):
                button.grid_configure(
                    row=index // columns,
                    column=index % columns,
                    sticky="ew",
                    padx=4,
                    pady=4,
                )

        except tk.TclError:
            pass


def _refresh(root):
    try:
        configure_styles(root)
        _style_existing_widgets(root)
        _responsive_button_frames(root)
    except tk.TclError:
        pass


def apply_cowodlaval_theme(root):
    """
    Install the shared CowoDlaVal theme on one Tk root.

    Safe to call immediately after Tk(): widgets created afterwards are
    styled on the first idle cycle and on subsequent window resizes.
    """

    root.configure(
        background=COLORS["window"],
    )

    state = {
        "job": None,
    }

    def schedule_refresh(_event=None):
        if state["job"] is not None:
            try:
                root.after_cancel(
                    state["job"]
                )
            except tk.TclError:
                pass

        try:
            state["job"] = root.after(
                80,
                lambda: _refresh(root),
            )
        except tk.TclError:
            pass

    root.bind(
        "<Configure>",
        schedule_refresh,
        add="+",
    )

    root.after_idle(
        lambda: _refresh(root)
    )


def build_standard_toolbar(
    parent,
    *,
    fit_command=None,
    theme_command=None,
    close_command=None,
):
    """
    Standard top-right toolbar shared by Bookings and Events.

    Layout:
        [Fit columns]    ...    [Theme] [Close]

    On small windows it reflows while preserving the same order.
    """

    toolbar = ttk.Frame(parent)

    buttons = []

    if fit_command is not None:
        fit = ttk.Button(
            toolbar,
            text="Adatta colonne",
            command=fit_command,
            style="Neutral.TButton",
        )
        buttons.append(fit)

    if theme_command is not None:
        theme = ttk.Button(
            toolbar,
            text="Tema",
            command=theme_command,
            style="Neutral.TButton",
        )
        buttons.append(theme)

    if close_command is not None:
        close = ttk.Button(
            toolbar,
            text="Chiudi",
            command=close_command,
            style="Neutral.TButton",
        )
        buttons.append(close)

    toolbar._cowodlaval_toolbar_buttons = buttons

    def layout(width=None):
        if width is None:
            try:
                width = parent.winfo_width()
            except tk.TclError:
                width = 1200

        for button in buttons:
            button.grid_forget()

        for column in range(6):
            toolbar.grid_columnconfigure(
                column,
                weight=0,
            )

        if width >= 900:
            # Keep Fit on the left and Theme/Close aligned to right.
            toolbar.grid_columnconfigure(
                1,
                weight=1,
            )

            index = 0

            if fit_command is not None:
                buttons[index].grid(
                    row=0,
                    column=0,
                    sticky="w",
                    padx=(0, 5),
                    pady=3,
                )
                index += 1

            if theme_command is not None:
                buttons[index].grid(
                    row=0,
                    column=2,
                    sticky="e",
                    padx=5,
                    pady=3,
                )
                index += 1

            if close_command is not None:
                buttons[index].grid(
                    row=0,
                    column=3,
                    sticky="e",
                    padx=(5, 0),
                    pady=3,
                )

        else:
            # Small windows: two rows, same semantic order.
            toolbar.grid_columnconfigure(
                0,
                weight=1,
            )
            toolbar.grid_columnconfigure(
                1,
                weight=1,
            )

            index = 0

            if fit_command is not None:
                buttons[index].grid(
                    row=0,
                    column=0,
                    columnspan=2,
                    sticky="ew",
                    padx=3,
                    pady=3,
                )
                index += 1

            if theme_command is not None:
                buttons[index].grid(
                    row=1,
                    column=0,
                    sticky="ew",
                    padx=3,
                    pady=3,
                )
                index += 1

            if close_command is not None:
                buttons[index].grid(
                    row=1,
                    column=1,
                    sticky="ew",
                    padx=3,
                    pady=3,
                )

    toolbar._cowodlaval_layout = layout

    return toolbar
