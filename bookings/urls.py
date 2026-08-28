from django.urls import path

from .views import (
    BookingCreateView,
    BookingListView,
    booking_detail,
    booking_payment,
    cancel_booking_view,
    modify_booking_view,
    paypal_return,
    paypal_webhook,
    satispay_callback,
    satispay_return,
    stripe_success,
    stripe_webhook,
)

urlpatterns = [
    path("", BookingListView.as_view(), name="booking_list"),
    path("new/", BookingCreateView.as_view(), name="booking_create"),
    path("<int:pk>/", booking_detail, name="booking_detail"),
    path("<int:pk>/payment/", booking_payment, name="booking_payment"),
    path("<int:pk>/modify/", modify_booking_view, name="booking_modify"),
    path("<int:pk>/cancel/", cancel_booking_view, name="booking_cancel"),
    path("<int:pk>/payments/stripe/success/", stripe_success, name="stripe_success"),
    path("<int:pk>/payments/paypal/return/", paypal_return, name="paypal_return"),
    path("<int:pk>/payments/satispay/return/", satispay_return, name="satispay_return"),
    path("webhooks/stripe/", stripe_webhook, name="stripe_webhook"),
    path("webhooks/paypal/", paypal_webhook, name="paypal_webhook"),
    path("webhooks/satispay/", satispay_callback, name="satispay_callback"),
]
