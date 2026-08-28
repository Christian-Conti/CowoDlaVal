from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from .forms import EmailAuthenticationForm, SignUpForm


class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            try:
                user = form.save()
            except IntegrityError:
                form.add_error(
                    "username",
                    _("A user with that username already exists."),
                )
            else:
                login(request, user)
                messages.success(
                    request,
                    _("Account created successfully."),
                )
                return redirect("home")
    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/signup.html",
        {"form": form},
    )
