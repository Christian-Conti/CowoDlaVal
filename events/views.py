from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import EventForm
from .i18n import tr
from .models import Event, EventImage
from .services import save_uploaded_images


class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return bool(
            self.request.user.is_authenticated
            and self.request.user.is_superuser
        )

    def handle_no_permission(self):
        raise PermissionDenied


class EventListView(ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        return (
            Event.objects.filter(
                is_public=True,
                date__gte=timezone.localdate(),
            )
            .prefetch_related("images")
            .order_by("date", "time", "pk")
        )


class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        queryset = Event.objects.prefetch_related("images")

        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return queryset

        return queryset.filter(is_public=True)


class EventCreateView(SuperuserRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        save_uploaded_images(self.object, form.cleaned_data.get("images", []))
        messages.success(self.request, tr("Event created successfully."))
        return response


class EventUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        save_uploaded_images(self.object, form.cleaned_data.get("images", []))
        messages.success(self.request, tr("Event updated successfully."))
        return response


class EventDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Event
    template_name = "events/event_confirm_delete.html"
    success_url = reverse_lazy("events:list")

    def form_valid(self, form):
        messages.success(self.request, tr("Event deleted successfully."))
        return super().form_valid(form)


def event_image(request, pk):
    image = get_object_or_404(
        EventImage.objects.select_related("event"),
        pk=pk,
    )

    if not image.event.is_public:
        if not (
            request.user.is_authenticated
            and request.user.is_superuser
        ):
            raise Http404

    response = HttpResponse(bytes(image.data), content_type=image.content_type)
    safe_name = image.original_name.replace('"', "")
    response["Content-Disposition"] = f'inline; filename="{safe_name}"'
    response["Cache-Control"] = "public, max-age=3600"
    return response


@require_POST
def event_image_delete(request, pk):
    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        raise PermissionDenied

    image = get_object_or_404(
        EventImage.objects.select_related("event"),
        pk=pk,
    )
    event_pk = image.event_id
    image.delete()
    messages.success(request, tr("Image removed."))
    return redirect("events:edit", pk=event_pk)
