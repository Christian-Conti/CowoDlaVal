from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView

from .forms import BookingForm
from .models import Booking
from .services import cancel_booking, create_booking


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = "bookings/booking_list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        queryset = Booking.objects.select_related("space", "user")
        if self.request.user.is_staff:
            return queryset.all()
        return queryset.filter(user=self.request.user)


class BookingCreateView(LoginRequiredMixin, FormView):
    template_name = "bookings/booking_form.html"
    form_class = BookingForm
    success_url = reverse_lazy("booking_list")

    def get_initial(self):
        initial = super().get_initial()
        space_id = self.request.GET.get("space")
        booking_date = parse_date(self.request.GET.get("date", ""))
        if space_id:
            initial["space"] = space_id
        if booking_date:
            initial["date"] = booking_date
        return initial

    def form_valid(self, form):
        try:
            create_booking(
                user=self.request.user,
                space_id=form.cleaned_data["space"].id,
                booking_date=form.cleaned_data["date"],
                notes=form.cleaned_data["notes"],
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, _("Booking confirmed."))
        return super().form_valid(form)


@login_required
@require_POST
def cancel_booking_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    try:
        cancel_booking(booking=booking, user=request.user)
        messages.success(request, _("Booking cancelled."))
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("booking_list")
