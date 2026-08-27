from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from .views import contact, home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("contact/", contact, name="contact"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("accounts.urls")),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("spaces/", include("spaces.urls")),
    path("bookings/", include("bookings.urls")),
]
