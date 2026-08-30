from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
            }
        ),
    )

    error_messages = {
        "invalid_login": _(
            "Please enter a correct email address and password."
        ),
        "inactive": _("This account is inactive."),
    }

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            UserModel = get_user_model()

            try:
                user = UserModel._default_manager.get(
                    email__iexact=email.strip()
                )
            except (
                UserModel.DoesNotExist,
                UserModel.MultipleObjectsReturned,
            ):
                # Run one password hash to reduce account-enumeration timing differences.
                UserModel().set_password(password)
                raise self.get_invalid_login_error()
            if not user.check_password(password):
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(user)
            self.user_cache = user

        return self.cleaned_data


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("Email"))

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_username(self):
        username = self.cleaned_data.get("username")

        if username and User.objects.filter(
            username__iexact=username
        ).exists():
            raise ValidationError(
                _("A user with that username already exists."),
                code="unique",
            )

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                _("An account with this email address already exists."),
                code="unique",
            )

        return email
