from django.urls import path

from .views import BookingCreateView, BookingListView, cancel_booking_view

urlpatterns = [
    path("", BookingListView.as_view(), name="booking_list"),
    path("new/", BookingCreateView.as_view(), name="booking_create"),
    path("<int:pk>/cancel/", cancel_booking_view, name="booking_cancel"),
]
