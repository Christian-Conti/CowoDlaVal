from django import forms
from django.core.exceptions import ValidationError

from .i18n import tr
from .models import Event


ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_clean = super().clean

        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]

        return [single_clean(data, initial)]


class EventForm(forms.ModelForm):
    images = MultipleFileField(required=False)

    class Meta:
        model = Event
        fields = (
            "title_it",
            "title_en",
            "title_de",
            "title_fr",
            "short_description_it",
            "short_description_en",
            "short_description_de",
            "short_description_fr",
            "description_it",
            "description_en",
            "description_de",
            "description_fr",
            "date",
            "time",
            "location",
            "is_public",
        )
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
            "description_it": forms.Textarea(attrs={"rows": 6}),
            "description_en": forms.Textarea(attrs={"rows": 6}),
            "description_de": forms.Textarea(attrs={"rows": 6}),
            "description_fr": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "title_it": "Title (Italian)",
            "title_en": "Title (English)",
            "title_de": "Title (German)",
            "title_fr": "Title (French)",
            "short_description_it": "Short description (Italian)",
            "short_description_en": "Short description (English)",
            "short_description_de": "Short description (German)",
            "short_description_fr": "Short description (French)",
            "description_it": "Description (Italian)",
            "description_en": "Description (English)",
            "description_de": "Description (German)",
            "description_fr": "Description (French)",
            "date": "Event date",
            "time": "Time",
            "location": "Location",
            "is_public": "Public",
            "images": "Images",
        }

        for name, key in labels.items():
            self.fields[name].label = tr(key)

        self.fields["images"].help_text = tr("You can select multiple images.")

    def clean(self):
        cleaned = super().clean()

        if not any(
            cleaned.get(field)
            for field in ("title_it", "title_en", "title_de", "title_fr")
        ):
            raise ValidationError(tr("Enter the event title in at least one language."))

        return cleaned

    def clean_images(self):
        files = self.cleaned_data.get("images", [])

        for uploaded_file in files:
            if uploaded_file.size > MAX_IMAGE_SIZE:
                raise ValidationError(f"{uploaded_file.name} is larger than 10 MB.")

            if uploaded_file.content_type not in ALLOWED_IMAGE_TYPES:
                raise ValidationError(
                    f"{uploaded_file.name} is not a supported image format."
                )

        return files
