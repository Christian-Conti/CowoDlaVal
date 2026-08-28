from django.contrib import admin
from django.urls import include, path

from .views import contact, home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("contact/", contact, name="contact"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("spaces/", include("spaces.urls")),
    path("bookings/", include("bookings.urls")),
]
