from django.urls import path

from .views import (
    EventCreateView,
    EventDeleteView,
    EventDetailView,
    EventListView,
    EventUpdateView,
    event_image,
    event_image_delete,
)


app_name = "events"

urlpatterns = [
    path("", EventListView.as_view(), name="list"),
    path("add/", EventCreateView.as_view(), name="add"),
    path("images/<int:pk>/", event_image, name="image"),
    path("images/<int:pk>/delete/", event_image_delete, name="image_delete"),
    path("<int:pk>/", EventDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", EventUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", EventDeleteView.as_view(), name="delete"),
]
