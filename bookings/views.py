import json
import logging

import stripe
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import FormView, ListView

from .forms import BookingForm, PaymentMethodForm
from .models import Booking, Payment
from .providers import (
    PaymentConfigurationError,
    PaymentProviderError,
    apply_paypal_webhook,
    capture_paypal_order,
    construct_stripe_event,
    create_paypal_checkout,
    create_satispay_checkout,
    create_stripe_checkout,
    retrieve_satispay_payment,
    retrieve_stripe_session,
    verify_paypal_webhook,
    verify_stripe_session,
)
from .services import (
    cancel_booking,
    create_booking,
    mark_payment_failed,
    modify_booking,
    prepare_online_payment,
    select_onsite_payment,
    discard_unfinished_booking,
)
from .availability import get_booking_date_range, get_booking_alternatives
from django.views import View


logger = logging.getLogger(__name__)


def _user_booking(request, pk) -> Booking:
    queryset = Booking.objects.select_related("space", "user")
    if not request.user.is_staff:
        queryset = queryset.filter(user=request.user)
    return get_object_or_404(queryset, pk=pk)


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
        space_id = form.cleaned_data["space"].id
        booking_date = form.cleaned_data["date"]
        duration = form.cleaned_data["duration"]
        tariff_category = form.cleaned_data["tariff_category"]
        notes = form.cleaned_data["notes"]

        start_date, end_date = get_booking_date_range(booking_date, duration)

        # Check if split booking is needed
        alternative_suggestion = get_booking_alternatives(
            start_date=start_date,
            end_date=end_date,
            requested_space_id=space_id,
        )
        
        if alternative_suggestion is not None:
            alternatives = alternative_suggestion["alternatives"]
            selected_alternative_id = (
                self.request.POST.get("alternative", "").strip()
            )
        
            if not alternatives or not selected_alternative_id:
                context = self.get_context_data(form=form)
                context["alternative_suggestion"] = alternative_suggestion
                context["alternative_choice_required"] = True
                return self.render_to_response(context)
        
            selected_alternatives = [
                alternative
                for alternative in alternatives
                if alternative["alternative_id"] == selected_alternative_id
            ]
            if len(selected_alternatives) != 1:
                form.add_error(
                    None,
                    _(
                        "The selected alternative is no longer available. "
                        "Please choose again."
                    ),
                )
                context = self.get_context_data(form=form)
                context["alternative_suggestion"] = alternative_suggestion
                context["alternative_choice_required"] = True
                return self.render_to_response(context)
        
            # Only the desk changes. Preserve the original date, duration and tariff.
            space_id = selected_alternatives[0]["space_id"]
        
        try:
            booking = create_booking(
                user=self.request.user,
                space_id=space_id,
                booking_date=booking_date,
                duration=duration,
                tariff_category=tariff_category,
                notes=notes,
                language=getattr(self.request, "LANGUAGE_CODE", "it"),
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, _("Booking created. Choose how you want to pay."))
        return redirect("booking_payment", pk=booking.pk)


@login_required


@login_required
def booking_detail(request, pk):
    return render(request, "bookings/booking_detail.html", {"booking": _user_booking(request, pk)})


@login_required
def booking_payment(request, pk):
    booking = _user_booking(request, pk)
    if booking.status != Booking.Status.CONFIRMED:
        messages.error(request, _("This booking is no longer active."))
        return redirect("booking_detail", pk=booking.pk)
    if booking.payment_status == Booking.PaymentStatus.PAID:
        return redirect("booking_detail", pk=booking.pk)

    form = PaymentMethodForm(request.POST or None, initial={"payment_method": booking.payment_method})
    if request.method == "POST" and form.is_valid():
        method = form.cleaned_data["payment_method"]
        try:
            if method == Booking.PaymentMethod.ONSITE:
                select_onsite_payment(booking=booking, user=request.user)
                messages.success(request, _("Booking confirmed. Payment is due on site."))
                return redirect("booking_detail", pk=booking.pk)

            payment = prepare_online_payment(
                booking=booking,
                user=request.user,
                provider=method,
            )
            if method == Booking.PaymentMethod.STRIPE:
                checkout_url = create_stripe_checkout(payment)
            elif method == Booking.PaymentMethod.PAYPAL:
                checkout_url = create_paypal_checkout(payment)
            else:
                checkout_url = create_satispay_checkout(payment)
            return redirect(checkout_url)
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
        except (PaymentConfigurationError, PaymentProviderError):
            logger.exception("Unable to start %s checkout for %s", method, booking.booking_code)
            form.add_error(None, _("This payment method is temporarily unavailable. Please try again later."))

    return render(request, "bookings/payment_method.html", {"booking": booking, "form": form})


@login_required
def modify_booking_view(request, pk):
    booking = _user_booking(request, pk)
    if not booking.can_user_modify:
        messages.error(
            request,
            _("Online-paid bookings cannot be modified automatically. Contact the coworking staff."),
        )
        return redirect("booking_detail", pk=booking.pk)

    initial = {
        "space": booking.space_id,
        "date": booking.date,
        "tariff_category": booking.tariff_category,
        "notes": booking.notes,
    }
    form = BookingForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            modify_booking(
                booking=booking,
                user=request.user,
                space_id=form.cleaned_data["space"].id,
                booking_date=form.cleaned_data["date"],
                duration=form.cleaned_data.get("duration", "daily"),
                tariff_category=form.cleaned_data["tariff_category"],
                notes=form.cleaned_data["notes"],
            )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
        else:
            messages.success(request, _("Booking updated."))
            return redirect("booking_detail", pk=booking.pk)
    return render(request, "bookings/booking_form.html", {"form": form, "booking": booking, "is_update": True})


@login_required
@require_POST
def cancel_booking_view(request, pk):
    booking = _user_booking(request, pk)
    try:
        cancel_booking(booking=booking, user=request.user)
        messages.success(request, _("Booking cancelled."))
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("booking_detail", pk=booking.pk)


@login_required
@require_GET
def stripe_success(request, pk):
    booking = _user_booking(request, pk)
    session_id = request.GET.get("session_id", "")
    payment = get_object_or_404(
        Payment,
        booking=booking,
        provider=Payment.Provider.STRIPE,
        checkout_id=session_id,
    )
    try:
        if payment.status != Payment.Status.PAID:
            retrieve_stripe_session(session_id)
    except (PaymentConfigurationError, PaymentProviderError, ValidationError):
        logger.exception("Unable to verify Stripe return for %s", booking.booking_code)
        messages.info(request, _("Payment is still being verified. Refresh this page shortly."))
    else:
        messages.success(request, _("Payment confirmed."))
    return redirect("booking_detail", pk=booking.pk)


@login_required
@require_GET
def paypal_return(request, pk):
    booking = _user_booking(request, pk)
    order_id = request.GET.get("token", "")
    payment = get_object_or_404(
        Payment.objects.select_related("booking"),
        booking=booking,
        provider=Payment.Provider.PAYPAL,
        external_id=order_id,
    )
    try:
        if payment.status != Payment.Status.PAID:
            capture_paypal_order(payment, order_id)
    except (PaymentConfigurationError, PaymentProviderError, ValidationError):
        logger.exception("Unable to verify PayPal return for %s", booking.booking_code)
        messages.info(request, _("Payment is still being verified. Refresh this page shortly."))
    else:
        messages.success(request, _("Payment confirmed."))
    return redirect("booking_detail", pk=booking.pk)


@login_required
@require_GET
def satispay_return(request, pk):
    booking = _user_booking(request, pk)
    payment = get_object_or_404(
        Payment.objects.select_related("booking").order_by("-created_at"),
        booking=booking,
        provider=Payment.Provider.SATISPAY,
    )
    try:
        retrieve_satispay_payment(payment.external_id)
    except (PaymentConfigurationError, PaymentProviderError, ValidationError):
        logger.exception("Unable to verify Satispay return for %s", booking.booking_code)
        messages.info(request, _("Payment is still being verified. Refresh this page shortly."))
    else:
        messages.success(request, _("Payment status updated."))
    return redirect("booking_detail", pk=booking.pk)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    try:
        event = construct_stripe_event(request.body, request.headers.get("Stripe-Signature", ""))
        if event["type"] in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            verify_stripe_session(event["data"]["object"])
        elif event["type"] == "checkout.session.async_payment_failed":
            session = event["data"]["object"]
            payment = Payment.objects.get(provider=Payment.Provider.STRIPE, checkout_id=session["id"])
            mark_payment_failed(payment=payment, provider_status="failed")
    except (ValueError, KeyError, Payment.DoesNotExist, ValidationError, stripe.SignatureVerificationError):
        logger.warning("Rejected Stripe webhook", exc_info=True)
        return HttpResponseBadRequest()
    except (PaymentConfigurationError, PaymentProviderError):
        logger.exception("Stripe webhook processing failed")
        return HttpResponse(status=503)
    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def paypal_webhook(request):
    try:
        event = json.loads(request.body)
        if not verify_paypal_webhook(request.headers, event):
            logger.warning("Rejected PayPal webhook signature")
            return HttpResponse(status=401)
        apply_paypal_webhook(event)
    except (ValueError, KeyError, Payment.DoesNotExist, ValidationError):
        logger.warning("Rejected PayPal webhook", exc_info=True)
        return HttpResponseBadRequest()
    except (PaymentConfigurationError, PaymentProviderError):
        logger.exception("PayPal webhook processing failed")
        return HttpResponse(status=503)
    return HttpResponse(status=200)


@require_GET
def satispay_callback(request):
    payment_id = request.GET.get("payment_id", "")
    if not payment_id:
        return HttpResponseBadRequest()
    try:
        retrieve_satispay_payment(payment_id)
    except (Payment.DoesNotExist, ValidationError):
        logger.warning("Rejected Satispay callback", exc_info=True)
        return HttpResponseBadRequest()
    except (PaymentConfigurationError, PaymentProviderError):
        logger.exception("Satispay callback verification failed")
        return HttpResponse(status=503)
    return HttpResponse(status=200)


class BookingAbandonView(LoginRequiredMixin, View):
    # Permanently discard an unfinished checkout before payment starts.
    def post(self, request, booking_code):
        booking = Booking.objects.filter(
            booking_code=booking_code,
            user=request.user,
        ).first()
        if booking is None:
            messages.error(
                request,
                _("You do not have permission to manage this booking."),
            )
            return redirect("/")

        try:
            discard_unfinished_booking(
                booking=booking,
                user=request.user,
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect(request.META.get("HTTP_REFERER") or "/")

        messages.success(
            request,
            _("This unfinished booking was discarded."),
        )
        return redirect("/")
