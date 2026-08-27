from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["space", "user", "date", "status"]
    list_filter = ["status", "space"]
    search_fields = ["user__username", "user__email", "space__name"]
    date_hierarchy = "date"
