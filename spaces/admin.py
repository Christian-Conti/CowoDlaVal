from django.contrib import admin

from .models import Space


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ["name", "opening_time", "closing_time", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
