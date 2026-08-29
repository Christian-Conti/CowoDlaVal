from __future__ import annotations

from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from django.apps import apps
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import models

from config.admin_gui import UnifiedAdminWindow


LANGUAGES = (
    ("it", "Italiano"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Français"),
)


class EventsWindow:
    def __init__(self):
        self.Event = apps.get_model("events", "Event")
        self.root = tk.Tk()
        self.ui = UnifiedAdminWindow(
            self.root,
            "Cowo d'la val · Eventi",
            "Caricamento…",
        )
        self.current_event = None
        self.image_items = []

        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.time_var = tk.StringVar()
        self.location_var = tk.StringVar()
        self.public_var = tk.BooleanVar(value=True)
        self.lang_vars = {
            lang: {
                "title": tk.StringVar(),
                "short": tk.StringVar(),
            }
            for lang, _label in LANGUAGES
        }
        self.description_widgets = {}

        self._build_toolbar()
        self._build_body()
        self._build_footer()
        self.refresh()
        self.new_event()

    def _build_toolbar(self):
        self.ui.add_toolbar_button("Aggiorna", self.refresh, "neutral")
        self.ui.add_toolbar_button("Adatta colonne", self.ui.fit_columns, "neutral")
        self.ui.add_toolbar_button("Tema", self.ui.toggle_theme, "neutral")
        self.ui.add_toolbar_button("Chiudi", self.root.destroy, "danger")

    def _build_body(self):
        body = self.ui.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=2)

        table_frame = ttk.Frame(body, style="Cowo.Card.TFrame")
        table_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        columns = ("id", "date", "title_it", "title_en", "public", "images")
        headings = {
            "id": "ID",
            "date": "Data",
            "title_it": "Titolo IT",
            "title_en": "Titolo EN",
            "public": "Pubblico",
            "images": "Immagini",
        }
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Cowo.Treeview",
        )
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=130, minwidth=65, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.ui.register_tree(self.tree)

        form = ttk.Frame(body, style="Cowo.Root.TFrame")
        form.grid(row=1, column=0, sticky="nsew")
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        form.grid_columnconfigure(5, weight=1)
        form.grid_rowconfigure(2, weight=1)

        ttk.Label(form, text="Data", style="Cowo.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=3)
        ttk.Entry(form, textvariable=self.date_var, style="Cowo.TEntry").grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=3)
        ttk.Label(form, text="Ora", style="Cowo.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 5), pady=3)
        ttk.Entry(form, textvariable=self.time_var, style="Cowo.TEntry").grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=3)
        ttk.Label(form, text="Luogo", style="Cowo.TLabel").grid(row=0, column=4, sticky="w", padx=(0, 5), pady=3)
        ttk.Entry(form, textvariable=self.location_var, style="Cowo.TEntry").grid(row=0, column=5, sticky="ew", padx=(0, 10), pady=3)
        ttk.Checkbutton(form, text="Pubblico", variable=self.public_var, style="Cowo.TCheckbutton").grid(row=0, column=6, sticky="w", pady=3)

        self.notebook = ttk.Notebook(form, style="Cowo.TNotebook")
        self.notebook.grid(row=1, column=0, columnspan=7, sticky="nsew", pady=(6, 6))

        for lang, label in LANGUAGES:
            tab = ttk.Frame(self.notebook, style="Cowo.Root.TFrame")
            tab.grid_columnconfigure(1, weight=1)
            tab.grid_rowconfigure(2, weight=1)
            self.notebook.add(tab, text=label)
            ttk.Label(tab, text="Titolo", style="Cowo.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
            ttk.Entry(tab, textvariable=self.lang_vars[lang]["title"], style="Cowo.TEntry").grid(row=0, column=1, sticky="ew", pady=4)
            ttk.Label(tab, text="Descrizione breve", style="Cowo.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
            ttk.Entry(tab, textvariable=self.lang_vars[lang]["short"], style="Cowo.TEntry").grid(row=1, column=1, sticky="ew", pady=4)
            ttk.Label(tab, text="Descrizione", style="Cowo.TLabel").grid(row=2, column=0, sticky="nw", padx=(0, 6), pady=4)
            text = tk.Text(tab, height=8, wrap="word")
            text.grid(row=2, column=1, sticky="nsew", pady=4)
            self.description_widgets[lang] = text

        images_frame = ttk.Frame(form, style="Cowo.Root.TFrame")
        images_frame.grid(row=2, column=0, columnspan=7, sticky="nsew", pady=(2, 0))
        images_frame.grid_columnconfigure(0, weight=1)
        images_frame.grid_rowconfigure(1, weight=1)
        ttk.Label(images_frame, text="Immagini dell'evento", style="Cowo.Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.images_list = tk.Listbox(images_frame, height=4, exportselection=False)
        self.images_list.grid(row=1, column=0, sticky="nsew")

    def _build_footer(self):
        self.ui.add_footer_button("Nuovo evento", self.new_event, "primary")
        self.save_button = self.ui.add_footer_button("Salva evento", self.save_event, "success")
        self.ui.add_footer_button("Aggiungi immagini", self.add_images, "primary")
        self.remove_image_button = self.ui.add_footer_button("Rimuovi immagine", self.remove_image, "danger")
        self.delete_button = self.ui.add_footer_button("Elimina evento", self.delete_event, "danger")
        self._sync_action_state()

    def _field_names(self):
        return {field.name for field in self.Event._meta.fields}

    def _first_field(self, *names):
        available = self._field_names()
        return next((name for name in names if name in available), None)

    def _get(self, event, *names, default=""):
        for name in names:
            if hasattr(event, name):
                value = getattr(event, name)
                if value is not None:
                    return value
        return default

    def _set_if_present(self, event, value, *names):
        field = self._first_field(*names)
        if field:
            setattr(event, field, value)

    def refresh(self):
        current_pk = self.current_event.pk if self.current_event and self.current_event.pk else None
        self.tree.delete(*self.tree.get_children())
        date_field = self._first_field("date", "event_date", "start_date")
        time_field = self._first_field("time", "event_time", "start_time")
        ordering = [field for field in (date_field, time_field, "pk") if field]
        events = list(self.Event.objects.all().order_by(*ordering))
        for event in events:
            title_it = self._get(event, "title_it", "title", "name", default="")
            title_en = self._get(event, "title_en", default="")
            event_date = self._get(event, "date", "event_date", "start_date", default="")
            public = bool(self._get(event, "is_public", "public", "published", default=False))
            images = self._images_manager(event)
            count = images.count() if images is not None else 0
            item = self.tree.insert(
                "",
                "end",
                iid=str(event.pk),
                values=(event.pk, event_date, title_it, title_en, "Sì" if public else "No", count),
            )
            if current_pk == event.pk:
                self.tree.selection_set(item)
                self.tree.focus(item)
        self.ui.set_subtitle(f"{len(events)} {'evento' if len(events) == 1 else 'eventi'}")
        self.ui.fit_columns()
        self._sync_action_state()

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        try:
            self.current_event = self.Event.objects.get(pk=int(selection[0]))
        except (self.Event.DoesNotExist, ValueError):
            return
        self._load_event(self.current_event)
        self._sync_action_state()

    def _load_event(self, event):
        self.date_var.set(str(self._get(event, "date", "event_date", "start_date", default="") or ""))
        time_value = self._get(event, "time", "event_time", "start_time", default="")
        self.time_var.set(str(time_value or ""))
        self.location_var.set(str(self._get(event, "location", "place", "venue", default="") or ""))
        self.public_var.set(bool(self._get(event, "is_public", "public", "published", default=False)))
        for lang, _label in LANGUAGES:
            self.lang_vars[lang]["title"].set(str(self._get(event, f"title_{lang}", "title" if lang == "it" else "__missing__", default="") or ""))
            self.lang_vars[lang]["short"].set(str(self._get(event, f"short_description_{lang}", f"subtitle_{lang}", default="") or ""))
            text = self.description_widgets[lang]
            text.delete("1.0", "end")
            text.insert("1.0", str(self._get(event, f"description_{lang}", "description" if lang == "it" else "__missing__", default="") or ""))
        self._refresh_images()

    def new_event(self):
        self.current_event = None
        self.tree.selection_remove(self.tree.selection())
        self.date_var.set(date.today().isoformat())
        self.time_var.set("")
        self.location_var.set("")
        self.public_var.set(True)
        for lang, _label in LANGUAGES:
            self.lang_vars[lang]["title"].set("")
            self.lang_vars[lang]["short"].set("")
            self.description_widgets[lang].delete("1.0", "end")
        self.images_list.delete(0, "end")
        self.image_items = []
        self._sync_action_state()

    def save_event(self):
        event = self.current_event or self.Event()
        try:
            self._set_if_present(event, self._convert_field("date", "event_date", "start_date", raw=self.date_var.get()), "date", "event_date", "start_date")
            self._set_if_present(event, self._convert_field("time", "event_time", "start_time", raw=self.time_var.get(), allow_blank=True), "time", "event_time", "start_time")
            self._set_if_present(event, self.location_var.get().strip(), "location", "place", "venue")
            self._set_if_present(event, bool(self.public_var.get()), "is_public", "public", "published")

            for lang, _label in LANGUAGES:
                title = self.lang_vars[lang]["title"].get().strip()
                short = self.lang_vars[lang]["short"].get().strip()
                description = self.description_widgets[lang].get("1.0", "end-1c").strip()
                self._set_if_present(event, title, f"title_{lang}", *(('title',) if lang == 'it' else ()))
                self._set_if_present(event, short, f"short_description_{lang}", f"subtitle_{lang}")
                self._set_if_present(event, description, f"description_{lang}", *(('description',) if lang == 'it' else ()))

            event.full_clean()
            event.save()
        except Exception as exc:
            messagebox.showerror("Evento non salvato", str(exc), parent=self.root)
            return

        self.current_event = event
        messagebox.showinfo("Evento", "Evento salvato.", parent=self.root)
        self.refresh()
        self._load_event(event)

    def _convert_field(self, *names, raw, allow_blank=False):
        field_name = self._first_field(*names)
        if not field_name:
            return None
        raw = raw.strip()
        field = self.Event._meta.get_field(field_name)
        if not raw and allow_blank:
            return None if field.null else ""
        return field.to_python(raw)

    def delete_event(self):
        if not self.current_event or not self.current_event.pk:
            return
        title = self._get(self.current_event, "title_it", "title", "name", default=f"#{self.current_event.pk}")
        if not messagebox.askyesno(
            "Elimina evento",
            f"Eliminare definitivamente l'evento “{title}”?",
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            self.current_event.delete()
        except Exception as exc:
            messagebox.showerror("Eliminazione", str(exc), parent=self.root)
            return
        self.new_event()
        self.refresh()

    def _images_manager(self, event):
        manager = getattr(event, "images", None)
        return manager if hasattr(manager, "all") else None

    def _image_relation_info(self):
        relation = next(
            (
                field
                for field in self.Event._meta.get_fields()
                if field.name == "images" and getattr(field, "related_model", None) is not None
            ),
            None,
        )
        if relation is None:
            return None
        image_model = relation.related_model
        fk_field = next(
            (
                field
                for field in image_model._meta.fields
                if isinstance(field, models.ForeignKey) and field.remote_field.model == self.Event
            ),
            None,
        )
        file_field = next(
            (field for field in image_model._meta.fields if isinstance(field, (models.ImageField, models.FileField))),
            None,
        )
        return image_model, fk_field, file_field

    def _refresh_images(self):
        self.images_list.delete(0, "end")
        self.image_items = []
        if not self.current_event or not self.current_event.pk:
            return
        manager = self._images_manager(self.current_event)
        if manager is None:
            return
        for image in manager.all():
            file_value = next(
                (
                    getattr(image, field.name)
                    for field in image._meta.fields
                    if isinstance(field, (models.ImageField, models.FileField))
                ),
                None,
            )
            name = Path(getattr(file_value, "name", "") or str(image)).name
            self.images_list.insert("end", name or f"Immagine #{image.pk}")
            self.image_items.append(image)

    def add_images(self):
        if not self.current_event or not self.current_event.pk:
            messagebox.showwarning("Immagini", "Salva prima l'evento.", parent=self.root)
            return
        info = self._image_relation_info()
        if info is None:
            messagebox.showerror("Immagini", "Il modello Event non espone una relazione immagini compatibile.", parent=self.root)
            return
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title="Aggiungi immagini",
            filetypes=[("Immagini", "*.png *.jpg *.jpeg *.webp *.gif"), ("Tutti i file", "*")],
        )
        if not paths:
            return
        image_model, fk_field, file_field = info
        if fk_field is None or file_field is None:
            messagebox.showerror("Immagini", "Impossibile individuare i campi del modello immagini.", parent=self.root)
            return
        try:
            for path in paths:
                obj = image_model(**{fk_field.name: self.current_event})
                with open(path, "rb") as handle:
                    getattr(obj, file_field.name).save(Path(path).name, File(handle), save=False)
                obj.full_clean()
                obj.save()
        except Exception as exc:
            messagebox.showerror("Immagini", str(exc), parent=self.root)
            return
        self._refresh_images()
        self.refresh()

    def remove_image(self):
        selection = self.images_list.curselection()
        if not selection:
            messagebox.showwarning("Immagini", "Seleziona un'immagine.", parent=self.root)
            return
        image = self.image_items[selection[0]]
        if not messagebox.askyesno("Rimuovi immagine", "Rimuovere l'immagine selezionata?", parent=self.root):
            return
        try:
            image.delete()
        except Exception as exc:
            messagebox.showerror("Immagini", str(exc), parent=self.root)
            return
        self._refresh_images()
        self.refresh()

    def _sync_action_state(self):
        exists = bool(self.current_event and self.current_event.pk)
        if hasattr(self, "delete_button"):
            self.delete_button.state(["!disabled"] if exists else ["disabled"])
            self.remove_image_button.state(["!disabled"] if exists else ["disabled"])

    def run(self):
        self.root.mainloop()


class Command(BaseCommand):
    help = "Open the unified Cowo d'la val events desktop dashboard."

    def handle(self, *args, **options):
        try:
            EventsWindow().run()
        except tk.TclError as exc:
            raise CommandError(f"Impossibile avviare la GUI eventi: {exc}") from exc
