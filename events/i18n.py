from django.utils import translation


TRANSLATIONS = {
    "Events": {
        "it": "Eventi",
        "en": "Events",
        "de": "Veranstaltungen",
        "fr": "Événements",
    },
    "Upcoming public events": {
        "it": "Prossimi eventi pubblici",
        "en": "Upcoming public events",
        "de": "Kommende öffentliche Veranstaltungen",
        "fr": "Prochains événements publics",
    },
    "Add event": {
        "it": "Aggiungi evento",
        "en": "Add event",
        "de": "Veranstaltung hinzufügen",
        "fr": "Ajouter un événement",
    },
    "Edit event": {
        "it": "Modifica evento",
        "en": "Edit event",
        "de": "Veranstaltung bearbeiten",
        "fr": "Modifier l’événement",
    },
    "Delete event": {
        "it": "Elimina evento",
        "en": "Delete event",
        "de": "Veranstaltung löschen",
        "fr": "Supprimer l’événement",
    },
    "View event": {
        "it": "Vedi evento",
        "en": "View event",
        "de": "Veranstaltung ansehen",
        "fr": "Voir l’événement",
    },
    "Edit": {
        "it": "Modifica",
        "en": "Edit",
        "de": "Bearbeiten",
        "fr": "Modifier",
    },
    "Save": {
        "it": "Salva",
        "en": "Save",
        "de": "Speichern",
        "fr": "Enregistrer",
    },
    "Cancel": {
        "it": "Annulla",
        "en": "Cancel",
        "de": "Abbrechen",
        "fr": "Annuler",
    },
    "Current images": {
        "it": "Immagini attuali",
        "en": "Current images",
        "de": "Aktuelle Bilder",
        "fr": "Images actuelles",
    },
    "Remove image": {
        "it": "Rimuovi immagine",
        "en": "Remove image",
        "de": "Bild entfernen",
        "fr": "Supprimer l’image",
    },
    "Images": {
        "it": "Immagini",
        "en": "Images",
        "de": "Bilder",
        "fr": "Images",
    },
    "You can select multiple images.": {
        "it": "Puoi selezionare più immagini.",
        "en": "You can select multiple images.",
        "de": "Sie können mehrere Bilder auswählen.",
        "fr": "Vous pouvez sélectionner plusieurs images.",
    },
    "There are no upcoming public events.": {
        "it": "Non ci sono eventi pubblici in programma.",
        "en": "There are no upcoming public events.",
        "de": "Es gibt keine bevorstehenden öffentlichen Veranstaltungen.",
        "fr": "Il n’y a aucun événement public à venir.",
    },
    "Event date": {
        "it": "Data evento",
        "en": "Event date",
        "de": "Veranstaltungsdatum",
        "fr": "Date de l’événement",
    },
    "Time": {
        "it": "Ora",
        "en": "Time",
        "de": "Uhrzeit",
        "fr": "Heure",
    },
    "Location": {
        "it": "Luogo",
        "en": "Location",
        "de": "Ort",
        "fr": "Lieu",
    },
    "Public": {
        "it": "Pubblico",
        "en": "Public",
        "de": "Öffentlich",
        "fr": "Public",
    },
    "Title (Italian)": {
        "it": "Titolo (Italiano)",
        "en": "Title (Italian)",
        "de": "Titel (Italienisch)",
        "fr": "Titre (Italien)",
    },
    "Title (English)": {
        "it": "Titolo (Inglese)",
        "en": "Title (English)",
        "de": "Titel (Englisch)",
        "fr": "Titre (Anglais)",
    },
    "Title (German)": {
        "it": "Titolo (Tedesco)",
        "en": "Title (German)",
        "de": "Titel (Deutsch)",
        "fr": "Titre (Allemand)",
    },
    "Title (French)": {
        "it": "Titolo (Francese)",
        "en": "Title (French)",
        "de": "Titel (Französisch)",
        "fr": "Titre (Français)",
    },
    "Short description (Italian)": {
        "it": "Descrizione breve (Italiano)",
        "en": "Short description (Italian)",
        "de": "Kurzbeschreibung (Italienisch)",
        "fr": "Description courte (Italien)",
    },
    "Short description (English)": {
        "it": "Descrizione breve (Inglese)",
        "en": "Short description (English)",
        "de": "Kurzbeschreibung (Englisch)",
        "fr": "Description courte (Anglais)",
    },
    "Short description (German)": {
        "it": "Descrizione breve (Tedesco)",
        "en": "Short description (German)",
        "de": "Kurzbeschreibung (Deutsch)",
        "fr": "Description courte (Allemand)",
    },
    "Short description (French)": {
        "it": "Descrizione breve (Francese)",
        "en": "Short description (French)",
        "de": "Kurzbeschreibung (Französisch)",
        "fr": "Description courte (Français)",
    },
    "Description (Italian)": {
        "it": "Descrizione (Italiano)",
        "en": "Description (Italian)",
        "de": "Beschreibung (Italienisch)",
        "fr": "Description (Italien)",
    },
    "Description (English)": {
        "it": "Descrizione (Inglese)",
        "en": "Description (English)",
        "de": "Beschreibung (Englisch)",
        "fr": "Description (Anglais)",
    },
    "Description (German)": {
        "it": "Descrizione (Tedesco)",
        "en": "Description (German)",
        "de": "Beschreibung (Deutsch)",
        "fr": "Description (Allemand)",
    },
    "Description (French)": {
        "it": "Descrizione (Francese)",
        "en": "Description (French)",
        "de": "Beschreibung (Französisch)",
        "fr": "Description (Français)",
    },
    "Enter the event title in at least one language.": {
        "it": "Inserisci il titolo dell’evento in almeno una lingua.",
        "en": "Enter the event title in at least one language.",
        "de": "Geben Sie den Veranstaltungstitel in mindestens einer Sprache ein.",
        "fr": "Saisissez le titre de l’événement dans au moins une langue.",
    },
    "Event created successfully.": {
        "it": "Evento creato correttamente.",
        "en": "Event created successfully.",
        "de": "Veranstaltung wurde erstellt.",
        "fr": "Événement créé avec succès.",
    },
    "Event updated successfully.": {
        "it": "Evento aggiornato correttamente.",
        "en": "Event updated successfully.",
        "de": "Veranstaltung wurde aktualisiert.",
        "fr": "Événement mis à jour avec succès.",
    },
    "Event deleted successfully.": {
        "it": "Evento eliminato correttamente.",
        "en": "Event deleted successfully.",
        "de": "Veranstaltung wurde gelöscht.",
        "fr": "Événement supprimé avec succès.",
    },
    "Image removed.": {
        "it": "Immagine rimossa.",
        "en": "Image removed.",
        "de": "Bild entfernt.",
        "fr": "Image supprimée.",
    },
    "Are you sure you want to delete this event?": {
        "it": "Sei sicuro di voler eliminare questo evento?",
        "en": "Are you sure you want to delete this event?",
        "de": "Möchten Sie diese Veranstaltung wirklich löschen?",
        "fr": "Voulez-vous vraiment supprimer cet événement ?",
    },
}


def tr(key, language=None):
    language = (language or translation.get_language() or "en").split("-", 1)[0]
    values = TRANSLATIONS.get(key)

    if values is None:
        return key

    return values.get(language) or values.get("en") or key
