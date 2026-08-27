from django.urls import path

from .views import SpaceListView

urlpatterns = [
    path("", SpaceListView.as_view(), name="space_list"),
]
