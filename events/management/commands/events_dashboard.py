from config.gui_theme import install_unified_gui
from datetime import datetime
import mimetypes
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from events.models import Event, EventImage


LANGUAGES = (
    ("it", "Italiano"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Français"),
)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class Command(BaseCommand):
    help = "List, create and manage Cowo d'la val events from CLI or GUI."

    def add_arguments(self, parser):
        parser.add_argument("--add", action="store_true", help="Interactively create an event.")
        parser.add_argument("--gui", action="store_true", help="Open the graphical event manager.")
        parser.add_argument("--delete", type=int, metavar="EVENT_ID")
        parser.add_argument("--publish", type=int, metavar="EVENT_ID")
        parser.add_argument("--unpublish", type=int, metavar="EVENT_ID")
        parser.add_argument("--add-image", nargs=2, metavar=("EVENT_ID", "IMAGE_PATH"))
        parser.add_argument("--include-past", action="store_true")

    def handle(self, *args, **options):
        if options["gui"]:
            self._run_gui()
            return
        if options["add"]:
            self._interactive_add()
            return
        if options["delete"] is not None:
            event = self._get_event(options["delete"])
            label = event.display_title
            event.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted: {label}"))
            return
        if options["publish"] is not None:
            self._set_public(options["publish"], True)
            return
        if options["unpublish"] is not None:
            self._set_public(options["unpublish"], False)
            return
        if options["add_image"]:
            event_id, image_path = options["add_image"]
            event = self._get_event(int(event_id))
            self._attach_path(event, Path(image_path).expanduser())
            self.stdout.write(self.style.SUCCESS("Image attached."))
            return
        self._list_events(options["include_past"])

    def _get_event(self, event_id):
        try:
            return Event.objects.get(pk=event_id)
        except Event.DoesNotExist as exc:
            raise CommandError(f"Event #{event_id} does not exist.") from exc

    def _set_public(self, event_id, value):
        event = self._get_event(event_id)
        event.is_public = value
        event.save(update_fields=["is_public", "updated_at"])
        state = "Published" if value else "Unpublished"
        self.stdout.write(self.style.SUCCESS(f"{state} event #{event.pk}."))

    def _list_events(self, include_past):
        queryset = Event.objects.all().order_by("date", "time", "pk")
        if not include_past:
            queryset = queryset.filter(date__gte=timezone.localdate())
        rows = list(queryset)
        if not rows:
            self.stdout.write("No events.")
            return
        self.stdout.write(f"{'ID':>4}  {'DATE':10}  {'PUBLIC':6}  {'IMAGES':6}  TITLE")
        for event in rows:
            self.stdout.write(
                f"{event.pk:>4}  {event.date.isoformat():10}  "
                f"{('yes' if event.is_public else 'no'):6}  "
                f"{event.images.count():>6}  {event.display_title}"
            )

    def _prompt(self, label, default=""):
        suffix = f" [{default}]" if default else ""
        value = input(f"{label}{suffix}: ").strip()
        return value or default

    def _prompt_bool(self, label, default=True):
        value = input(f"{label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        if not value:
            return default
        return value in {"y", "yes", "1", "true"}

    @transaction.atomic
    def _interactive_add(self):
        values = {}
        for code, label in LANGUAGES:
            self.stdout.write(f"\n{label}")
            values[f"title_{code}"] = self._prompt("  Title")
            values[f"short_description_{code}"] = self._prompt("  Short description")
            values[f"description_{code}"] = self._prompt("  Description")
        if not any(values[f"title_{code}"] for code, _ in LANGUAGES):
            raise CommandError("Enter at least one title.")
        date_text = self._prompt("Date (YYYY-MM-DD)", timezone.localdate().isoformat())
        try:
            event_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError("Date must use YYYY-MM-DD.") from exc
        time_text = self._prompt("Time (HH:MM, optional)")
        event_time = None
        if time_text:
            try:
                event_time = datetime.strptime(time_text, "%H:%M").time()
            except ValueError as exc:
                raise CommandError("Time must use HH:MM.") from exc
        event = Event.objects.create(
            **values,
            date=event_date,
            time=event_time,
            location=self._prompt("Location"),
            is_public=self._prompt_bool("Public", True),
        )
        image_text = self._prompt("Image paths, comma-separated (optional)")
        if image_text:
            for item in image_text.split(","):
                value = item.strip()
                if value:
                    self._attach_path(event, Path(value).expanduser())
        self.stdout.write(self.style.SUCCESS(f"Created event #{event.pk}: {event.display_title}"))

    def _attach_path(self, event, path):
        if not path.is_file():
            raise CommandError(f"Image not found: {path}")
        content_type, _ = mimetypes.guess_type(path.name)
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise CommandError(f"Unsupported image type: {path.name}")
        data = path.read_bytes()
        if len(data) > 10 * 1024 * 1024:
            raise CommandError(f"Image is larger than 10 MB: {path}")
        EventImage.objects.create(
            event=event,
            original_name=path.name[:255],
            content_type=content_type,
            data=data,
            position=event.images.count(),
        )

    def _run_gui(self):
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox, ttk
        except ImportError as exc:
            raise CommandError("Tkinter is not available.") from exc
        EventManagerGUI(tk, ttk, filedialog, messagebox).run()


class EventManagerGUI:
    def __init__(self, tk, ttk, filedialog, messagebox):
        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.root = tk.Tk()
        install_unified_gui(self.root)
        self.root.title("Cowo d'la val - Eventi")
        self.root.geometry("1280x850")
        self.root.minsize(900, 620)
        self.current_event_id = None
        self.pending_images = []
        self.fields = {}
        self._style()
        self._build()
        self.new_event()
        self.refresh_events()

    def _style(self):
        style = self.ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except self.tk.TclError:
            pass
        bg = "#171925"
        surface = "#202432"
        alt = "#252d48"
        text = "#f4f2f8"
        primary = "#747cff"
        self.root.configure(bg=bg)
        style.configure(".", background=bg, foreground=text, fieldbackground=surface, font=("Sans", 11))
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Title.TLabel", font=("Sans", 18, "bold"))
        style.configure("TButton", background=alt, foreground=text, padding=(10, 7))
        style.map("TButton", background=[("active", primary)])
        style.configure("Treeview", background=surface, fieldbackground=surface, foreground=text, rowheight=30)
        style.configure("Treeview.Heading", background=alt, foreground=text, font=("Sans", 11, "bold"))
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", background=alt, foreground=text, padding=(12, 7))
        style.map("TNotebook.Tab", background=[("selected", primary)])
        self.colors = {"surface": surface, "text": text, "primary": primary, "border": "#434b68"}

    def _build(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        header = self.ttk.Frame(self.root, padding=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        self.ttk.Label(header, text="Cowo d'la val · Eventi", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        controls = self.ttk.Frame(header)
        controls.grid(row=0, column=1, sticky="e")
        for label, command in (("Nuovo", self.new_event), ("Aggiorna", self.refresh_events), ("Chiudi", self.root.destroy)):
            self.ttk.Button(controls, text=label, command=command).pack(side="left", padx=4)

        paned = self.ttk.Panedwindow(self.root, orient=self.tk.VERTICAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        list_frame = self.ttk.Frame(paned)
        edit_frame = self.ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        paned.add(edit_frame, weight=3)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        columns = ("id", "date", "title_it", "title_en", "public", "images")
        self.tree = self.ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        labels = {"id": "ID", "date": "Data", "title_it": "Titolo IT", "title_en": "Titolo EN", "public": "Pubblico", "images": "Immagini"}
        widths = {"id": 55, "date": 110, "title_it": 300, "title_en": 300, "public": 90, "images": 90}
        for column in columns:
            self.tree.heading(column, text=labels[column])
            self.tree.column(column, width=widths[column], minwidth=50, stretch=column in {"title_it", "title_en"})
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        scroll = self.ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        edit_frame.columnconfigure(0, weight=1)
        edit_frame.rowconfigure(1, weight=1)
        meta = self.ttk.Frame(edit_frame, padding=(0, 10))
        meta.grid(row=0, column=0, sticky="ew")
        self.date_var = self.tk.StringVar()
        self.time_var = self.tk.StringVar()
        self.location_var = self.tk.StringVar()
        self.public_var = self.tk.BooleanVar(value=True)
        for idx in (1, 3, 5):
            meta.columnconfigure(idx, weight=1)
        widgets = (("Data", self.date_var, 0), ("Ora", self.time_var, 2), ("Luogo", self.location_var, 4))
        for label, variable, column in widgets:
            self.ttk.Label(meta, text=label).grid(row=0, column=column, sticky="w", padx=(0, 5))
            self.ttk.Entry(meta, textvariable=variable).grid(row=0, column=column + 1, sticky="ew", padx=(0, 12))
        self.ttk.Checkbutton(meta, text="Pubblico", variable=self.public_var).grid(row=0, column=6, sticky="e")

        notebook = self.ttk.Notebook(edit_frame)
        notebook.grid(row=1, column=0, sticky="nsew")
        for code, label in LANGUAGES:
            frame = self.ttk.Frame(notebook, padding=10)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(5, weight=1)
            notebook.add(frame, text=label)
            title = self.tk.StringVar()
            short = self.tk.StringVar()
            self.ttk.Label(frame, text="Titolo").grid(row=0, column=0, sticky="w")
            self.ttk.Entry(frame, textvariable=title).grid(row=1, column=0, sticky="ew", pady=(2, 8))
            self.ttk.Label(frame, text="Descrizione breve").grid(row=2, column=0, sticky="w")
            self.ttk.Entry(frame, textvariable=short).grid(row=3, column=0, sticky="ew", pady=(2, 8))
            self.ttk.Label(frame, text="Descrizione").grid(row=4, column=0, sticky="w")
            description = self.tk.Text(frame, wrap="word", height=7, background=self.colors["surface"], foreground=self.colors["text"], insertbackground=self.colors["text"], relief="flat", highlightthickness=1, highlightbackground=self.colors["border"])
            description.grid(row=5, column=0, sticky="nsew")
            self.fields[code] = (title, short, description)

        bottom = self.ttk.Frame(edit_frame, padding=(0, 10))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.image_list = self.tk.Listbox(bottom, height=4, background=self.colors["surface"], foreground=self.colors["text"], selectbackground=self.colors["primary"])
        self.image_list.grid(row=0, column=0, sticky="ew")
        image_buttons = self.ttk.Frame(bottom)
        image_buttons.grid(row=1, column=0, sticky="w", pady=(6, 8))
        self.ttk.Button(image_buttons, text="Aggiungi immagini", command=self.add_images).pack(side="left", padx=(0, 6))
        self.ttk.Button(image_buttons, text="Rimuovi immagine", command=self.remove_image).pack(side="left")
        actions = self.ttk.Frame(bottom)
        actions.grid(row=2, column=0, sticky="ew")
        self.ttk.Button(actions, text="Salva", command=self.save_event).pack(side="left", padx=(0, 6))
        self.ttk.Button(actions, text="Elimina evento", command=self.delete_event).pack(side="left")

    def run(self):
        self.root.mainloop()

    def refresh_events(self):
        selected = self.current_event_id
        for item in self.tree.get_children():
            self.tree.delete(item)
        for event in Event.objects.all().order_by("date", "time", "pk"):
            item = self.tree.insert("", "end", iid=str(event.pk), values=(event.pk, event.date.isoformat(), event.title_it, event.title_en, "Sì" if event.is_public else "No", event.images.count()))
            if selected == event.pk:
                self.tree.selection_set(item)

    def new_event(self):
        self.current_event_id = None
        self.pending_images = []
        self.date_var.set(timezone.localdate().isoformat())
        self.time_var.set("")
        self.location_var.set("")
        self.public_var.set(True)
        for title, short, description in self.fields.values():
            title.set("")
            short.set("")
            description.delete("1.0", "end")
        self._refresh_images()

    def _on_select(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.load_event(int(selected[0]))

    def load_event(self, event_id):
        event = Event.objects.get(pk=event_id)
        self.current_event_id = event.pk
        self.pending_images = []
        self.date_var.set(event.date.isoformat())
        self.time_var.set(event.time.strftime("%H:%M") if event.time else "")
        self.location_var.set(event.location)
        self.public_var.set(event.is_public)
        for code, (title, short, description) in self.fields.items():
            title.set(getattr(event, f"title_{code}"))
            short.set(getattr(event, f"short_description_{code}"))
            description.delete("1.0", "end")
            description.insert("1.0", getattr(event, f"description_{code}"))
        self._refresh_images()

    def _refresh_images(self):
        self.image_list.delete(0, "end")
        if self.current_event_id:
            for image in EventImage.objects.filter(event_id=self.current_event_id).order_by("position", "pk"):
                self.image_list.insert("end", f"db:{image.pk} {image.original_name}")
        for path in self.pending_images:
            self.image_list.insert("end", f"new:{path}")

    def add_images(self):
        paths = self.filedialog.askopenfilenames(title="Seleziona immagini", initialdir="/event_uploads" if Path("/event_uploads").is_dir() else "/app", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif"), ("All files", "*")])
        for value in paths:
            path = Path(value)
            if path not in self.pending_images:
                self.pending_images.append(path)
        self._refresh_images()

    def remove_image(self):
        selection = self.image_list.curselection()
        if not selection:
            return
        value = self.image_list.get(selection[0])
        if value.startswith("new:"):
            path = Path(value[4:])
            self.pending_images = [item for item in self.pending_images if item != path]
        elif value.startswith("db:"):
            image_id = int(value.split()[0].split(":", 1)[1])
            if self.messagebox.askyesno("Conferma", "Rimuovere questa immagine?"):
                EventImage.objects.filter(pk=image_id).delete()
        self._refresh_images()
        self.refresh_events()

    def _values(self):
        try:
            event_date = datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("La data deve usare YYYY-MM-DD.") from exc
        time_text = self.time_var.get().strip()
        event_time = None
        if time_text:
            try:
                event_time = datetime.strptime(time_text, "%H:%M").time()
            except ValueError as exc:
                raise ValueError("L'ora deve usare HH:MM.") from exc
        values = {"date": event_date, "time": event_time, "location": self.location_var.get().strip(), "is_public": self.public_var.get()}
        for code, (title, short, description) in self.fields.items():
            values[f"title_{code}"] = title.get().strip()
            values[f"short_description_{code}"] = short.get().strip()
            values[f"description_{code}"] = description.get("1.0", "end").strip()
        if not any(values[f"title_{code}"] for code, _ in LANGUAGES):
            raise ValueError("Inserire il titolo in almeno una lingua.")
        return values

    @transaction.atomic
    def save_event(self):
        try:
            values = self._values()
            if self.current_event_id:
                event = Event.objects.select_for_update().get(pk=self.current_event_id)
                for field, value in values.items():
                    setattr(event, field, value)
                event.save()
            else:
                event = Event.objects.create(**values)
                self.current_event_id = event.pk
            command = Command()
            for path in self.pending_images:
                command._attach_path(event, path)
            self.pending_images = []
            self.load_event(event.pk)
            self.refresh_events()
            self.messagebox.showinfo("Evento", "Evento salvato.")
        except Exception as exc:
            self.messagebox.showerror("Errore", str(exc))

    def delete_event(self):
        if not self.current_event_id:
            return
        if not self.messagebox.askyesno("Conferma", "Eliminare definitivamente l'evento selezionato?"):
            return
        Event.objects.filter(pk=self.current_event_id).delete()
        self.new_event()
        self.refresh_events()
