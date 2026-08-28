from django.urls import path

from .views import EmailLoginView, signup


urlpatterns = [
    path("login/", EmailLoginView.as_view(), name="login"),
    path("signup/", signup, name="signup"),
]
