from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import signup, EmailLoginView

urlpatterns = [
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("signup/", signup, name="signup"),
]
