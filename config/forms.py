from django import forms
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=120)
    email = forms.EmailField(label=_("Email"))
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={"rows": 7}),
    )
    website = forms.CharField(required=False, widget=forms.HiddenInput)
