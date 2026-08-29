from django.contrib import admin

from .models import Event, EventImage


class EventImageInline(admin.TabularInline):
    model = EventImage
    extra = 0
    fields = ("original_name", "content_type", "position", "created_at")
    readonly_fields = ("original_name", "content_type", "created_at")
    can_delete = True


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "time",
        "title_it",
        "title_en",
        "location",
        "is_public",
        "updated_at",
    )
    list_filter = ("is_public", "date")
    search_fields = (
        "title_it",
        "title_en",
        "title_de",
        "title_fr",
        "location",
    )
    date_hierarchy = "date"
    inlines = (EventImageInline,)


@admin.register(EventImage)
class EventImageAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "original_name",
        "content_type",
        "position",
        "created_at",
    )
    search_fields = ("event__title_it", "event__title_en", "original_name")
