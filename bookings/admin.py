from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Booking, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = [
        "provider",
        "status",
        "amount",
        "currency",
        "external_id",
        "checkout_id",
        "transaction_id",
        "provider_status",
        "paid_at",
    ]
    readonly_fields = fields
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "booking_code",
        "date",
        "space",
        "username",
        "customer_name",
        "status",
        "amount",
        "payment_method",
        "payment_indicator",
        "created_at",
    ]
    list_filter = ["date", "space", "payment_method", "payment_status", "status"]
    search_fields = [
        "booking_code",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    ]
    readonly_fields = ["booking_code", "currency", "paid_at", "confirmation_sent_at", "created_at", "updated_at"]
    date_hierarchy = "date"
    list_select_related = ["space", "user"]
    inlines = [PaymentInline]

    @admin.display(description=_("Username"), ordering="user__username")
    def username(self, booking):
        return booking.user.get_username()

    @admin.display(description=_("Name"), ordering="user__last_name")
    def customer_name(self, booking):
        return booking.user.get_full_name() or "—"

    @admin.display(description=_("Payment"), ordering="payment_status")
    def payment_indicator(self, booking):
        colors = {
            Booking.PaymentStatus.PAID: "#147a42",
            Booking.PaymentStatus.PENDING: "#9a6700",
            Booking.PaymentStatus.UNPAID: "#a61302",
            Booking.PaymentStatus.FAILED: "#a61302",
            Booking.PaymentStatus.REFUNDED: "#555",
            Booking.PaymentStatus.CANCELLED: "#555",
        }
        label = _("PAYMENT DUE") if booking.payment_due else booking.get_payment_status_display().upper()
        return format_html(
            '<strong style="color:{}">{}</strong>',
            colors.get(booking.payment_status, "inherit"),
            label,
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["booking", "provider", "status", "amount", "currency", "transaction_id", "created_at", "paid_at"]
    list_filter = ["provider", "status", "currency", "created_at"]
    search_fields = ["booking__booking_code", "external_id", "checkout_id", "transaction_id"]
    readonly_fields = [
        "booking",
        "provider",
        "amount",
        "currency",
        "idempotency_key",
        "external_id",
        "checkout_id",
        "transaction_id",
        "provider_status",
        "provider_metadata",
        "created_at",
        "updated_at",
        "paid_at",
    ]
