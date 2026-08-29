from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


DARK = {
    "window": "#141722",
    "surface": "#1D2230",
    "surface_alt": "#252C3D",
    "border": "#414A63",
    "text": "#F3F4F8",
    "muted": "#AEB4C6",
    "primary": "#747CFF",
    "primary_hover": "#8C93FF",
    "success": "#4EAE7D",
    "success_hover": "#64BE91",
    "danger": "#D96678",
    "danger_hover": "#E97D8D",
    "neutral": "#303951",
    "neutral_hover": "#3B4662",
    "selection": "#4E5988",
}

LIGHT = {
    "window": "#F5F6FA",
    "surface": "#FFFFFF",
    "surface_alt": "#E9ECF3",
    "border": "#C8CEDA",
    "text": "#282B38",
    "muted": "#697084",
    "primary": "#626BF0",
    "primary_hover": "#747CFF",
    "success": "#3E996D",
    "success_hover": "#52AB7F",
    "danger": "#C95668",
    "danger_hover": "#DA6B7C",
    "neutral": "#DFE3EC",
    "neutral_hover": "#CFD5E1",
    "selection": "#CCD1FA",
}


class UnifiedAdminWindow:
    """Common desktop shell used by both Bookings and Events."""

    def __init__(self, root: tk.Tk, title: str, subtitle: str = ""):
        self.root = root
        self.title_text = title
        self.subtitle_var = tk.StringVar(value=subtitle)
        self.theme_mode = "dark"
        self.toolbar_buttons: list[ttk.Button] = []
        self.footer_buttons: list[ttk.Button] = []
        self.trees: list[ttk.Treeview] = []

        self.root.title(title)
        self.root.geometry("1280x760")
        self.root.minsize(760, 560)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.container = ttk.Frame(root, style="Cowo.Root.TFrame")
        self.container.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self.header = ttk.Frame(self.container, style="Cowo.Root.TFrame")
        self.header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        self.header.grid_columnconfigure(0, weight=1)

        self.title_box = ttk.Frame(self.header, style="Cowo.Root.TFrame")
        self.title_box.grid(row=0, column=0, sticky="w")
        self.title_label = ttk.Label(
            self.title_box,
            text=title,
            style="Cowo.Title.TLabel",
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(
            self.title_box,
            textvariable=self.subtitle_var,
            style="Cowo.Subtitle.TLabel",
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.toolbar = ttk.Frame(self.header, style="Cowo.Root.TFrame")
        self.toolbar.grid(row=0, column=1, rowspan=2, sticky="e")

        self.body = ttk.Frame(self.container, style="Cowo.Root.TFrame")
        self.body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))
        self.container.grid_rowconfigure(1, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.footer = ttk.Frame(self.container, style="Cowo.Root.TFrame")
        self.footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 10))

        self.root.bind("<Configure>", self._on_resize, add="+")
        self.apply_theme()

    @property
    def colors(self):
        return LIGHT if self.theme_mode == "light" else DARK

    def set_subtitle(self, text: str):
        self.subtitle_var.set(text)

    def add_toolbar_button(self, text, command, role="neutral"):
        button = ttk.Button(
            self.toolbar,
            text=text,
            command=command,
            style=self.button_style(role),
        )
        self.toolbar_buttons.append(button)
        self._layout_toolbar()
        return button

    def add_footer_button(self, text, command, role="neutral"):
        button = ttk.Button(
            self.footer,
            text=text,
            command=command,
            style=self.button_style(role),
        )
        self.footer_buttons.append(button)
        self._layout_footer()
        return button

    @staticmethod
    def button_style(role: str):
        return {
            "primary": "Cowo.Primary.TButton",
            "success": "Cowo.Success.TButton",
            "danger": "Cowo.Danger.TButton",
            "neutral": "Cowo.Neutral.TButton",
        }.get(role, "Cowo.Neutral.TButton")

    def register_tree(self, tree: ttk.Treeview):
        self.trees.append(tree)
        tree.configure(style="Cowo.Treeview")

    def toggle_theme(self):
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        self.apply_theme()

    def apply_theme(self):
        c = self.colors
        width = max(self.root.winfo_width(), 900)
        base = 10 if width < 900 else 11 if width < 1350 else 12
        normal = ("TkDefaultFont", base)
        bold = ("TkDefaultFont", base, "bold")
        title = ("TkDefaultFont", base + 4, "bold")

        self.root.configure(background=c["window"])

        self.style.configure("Cowo.Root.TFrame", background=c["window"])
        self.style.configure(
            "Cowo.Card.TFrame",
            background=c["surface"],
            bordercolor=c["border"],
            relief="solid",
            borderwidth=1,
        )
        self.style.configure(
            "Cowo.Title.TLabel",
            background=c["window"],
            foreground=c["text"],
            font=title,
        )
        self.style.configure(
            "Cowo.Subtitle.TLabel",
            background=c["window"],
            foreground=c["muted"],
            font=bold,
        )
        self.style.configure(
            "Cowo.TLabel",
            background=c["window"],
            foreground=c["text"],
            font=normal,
        )
        self.style.configure(
            "Cowo.Card.TLabel",
            background=c["surface"],
            foreground=c["text"],
            font=normal,
        )
        self.style.configure(
            "Cowo.Section.TLabel",
            background=c["window"],
            foreground=c["text"],
            font=bold,
        )
        self.style.configure(
            "Cowo.TEntry",
            fieldbackground=c["surface"],
            foreground=c["text"],
            insertcolor=c["text"],
            bordercolor=c["border"],
            padding=(8, 6),
            font=normal,
        )
        self.style.configure(
            "Cowo.TCheckbutton",
            background=c["window"],
            foreground=c["text"],
            font=normal,
        )
        self.style.map(
            "Cowo.TCheckbutton",
            background=[("active", c["window"])],
            foreground=[("active", c["text"])],
        )
        self.style.configure(
            "Cowo.TNotebook",
            background=c["window"],
            borderwidth=0,
        )
        self.style.configure(
            "Cowo.TNotebook.Tab",
            background=c["neutral"],
            foreground=c["text"],
            padding=(12, 6),
            font=bold,
        )
        self.style.map(
            "Cowo.TNotebook.Tab",
            background=[("selected", c["primary"]), ("active", c["neutral_hover"])],
            foreground=[("selected", "#FFFFFF")],
        )
        self.style.configure(
            "Cowo.Treeview",
            background=c["surface"],
            fieldbackground=c["surface"],
            foreground=c["text"],
            bordercolor=c["border"],
            rowheight=max(26, int(base * 2.35)),
            font=normal,
        )
        self.style.configure(
            "Cowo.Treeview.Heading",
            background=c["surface_alt"],
            foreground=c["text"],
            bordercolor=c["border"],
            relief="flat",
            padding=(7, 5),
            font=bold,
        )
        self.style.map(
            "Cowo.Treeview",
            background=[("selected", c["selection"])],
            foreground=[("selected", c["text"])],
        )

        self._configure_button_style("Cowo.Primary.TButton", c["primary"], c["primary_hover"], "#FFFFFF", bold)
        self._configure_button_style("Cowo.Success.TButton", c["success"], c["success_hover"], "#FFFFFF", bold)
        self._configure_button_style("Cowo.Danger.TButton", c["danger"], c["danger_hover"], "#FFFFFF", bold)
        self._configure_button_style("Cowo.Neutral.TButton", c["neutral"], c["neutral_hover"], c["text"], bold)

        for widget in self._walk(self.root):
            if isinstance(widget, tk.Text):
                try:
                    widget.configure(
                        background=c["surface"],
                        foreground=c["text"],
                        insertbackground=c["text"],
                        selectbackground=c["selection"],
                        selectforeground=c["text"],
                        highlightbackground=c["border"],
                        highlightcolor=c["primary"],
                        relief="flat",
                        borderwidth=1,
                        font=normal,
                    )
                except tk.TclError:
                    pass
            elif isinstance(widget, tk.Listbox):
                try:
                    widget.configure(
                        background=c["surface"],
                        foreground=c["text"],
                        selectbackground=c["selection"],
                        selectforeground=c["text"],
                        highlightbackground=c["border"],
                        highlightcolor=c["primary"],
                        relief="flat",
                        borderwidth=1,
                        font=normal,
                    )
                except tk.TclError:
                    pass

        self._layout_toolbar()
        self._layout_footer()

    def _configure_button_style(self, name, bg, active, fg, font):
        c = self.colors
        self.style.configure(
            name,
            background=bg,
            foreground=fg,
            bordercolor=bg,
            lightcolor=bg,
            darkcolor=bg,
            relief="flat",
            borderwidth=0,
            padding=(13, 8),
            font=font,
        )
        self.style.map(
            name,
            background=[
                ("active", active),
                ("pressed", active),
                ("disabled", c["surface_alt"]),
            ],
            foreground=[("disabled", c["muted"])],
        )

    def fit_columns(self):
        self.root.update_idletasks()
        for tree in self.trees:
            columns = list(tree["columns"])
            if not columns:
                continue
            try:
                font = tkfont.nametofont(tree.cget("font"))
            except tk.TclError:
                font = tkfont.nametofont("TkDefaultFont")
            widths = []
            for column in columns:
                header = str(tree.heading(column, "text"))
                width = max(85, font.measure(header) + 30)
                for item in tree.get_children():
                    width = max(width, font.measure(str(tree.set(item, column))) + 26)
                widths.append(min(width, 360))
            available = max(tree.winfo_width() - 18, 320)
            total = sum(widths)
            if total < available:
                extra = int((available - total) / len(widths))
                widths = [w + extra for w in widths]
            for column, width in zip(columns, widths):
                tree.column(column, width=width, minwidth=70, stretch=False)

    def _layout_toolbar(self):
        width = max(self.root.winfo_width(), 900)
        for button in self.toolbar_buttons:
            button.grid_forget()
        if not self.toolbar_buttons:
            return
        columns = len(self.toolbar_buttons) if width >= 1000 else min(2, len(self.toolbar_buttons))
        for col in range(len(self.toolbar_buttons)):
            self.toolbar.grid_columnconfigure(col, weight=0)
        for col in range(columns):
            self.toolbar.grid_columnconfigure(col, weight=1, uniform="toolbar")
        for idx, button in enumerate(self.toolbar_buttons):
            button.grid(row=idx // columns, column=idx % columns, sticky="ew", padx=3, pady=3)

    def _layout_footer(self):
        width = max(self.root.winfo_width(), 900)
        for button in self.footer_buttons:
            button.grid_forget()
        if not self.footer_buttons:
            return
        if width >= 1200:
            columns = len(self.footer_buttons)
        elif width >= 760:
            columns = min(3, len(self.footer_buttons))
        else:
            columns = min(2, len(self.footer_buttons))
        for col in range(len(self.footer_buttons)):
            self.footer.grid_columnconfigure(col, weight=0)
        for col in range(columns):
            self.footer.grid_columnconfigure(col, weight=1, uniform="footer")
        for idx, button in enumerate(self.footer_buttons):
            button.grid(row=idx // columns, column=idx % columns, sticky="ew", padx=3, pady=3)

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        self._layout_toolbar()
        self._layout_footer()

    @staticmethod
    def _walk(widget):
        yield widget
        try:
            children = widget.winfo_children()
        except tk.TclError:
            return
        for child in children:
            yield from UnifiedAdminWindow._walk(child)


def make_labeled_entry(parent, label_text, variable, row, column, *, colspan=1):
    ttk.Label(parent, text=label_text, style="Cowo.TLabel").grid(
        row=row, column=column, sticky="w", padx=(0, 6), pady=4
    )
    entry = ttk.Entry(parent, textvariable=variable, style="Cowo.TEntry")
    entry.grid(row=row, column=column + 1, columnspan=colspan, sticky="ew", pady=4)
    return entry
