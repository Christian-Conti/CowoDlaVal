import base64
import hashlib
import json
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from email.utils import format_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import stripe
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse

from .models import Booking, Payment
from .services import mark_payment_failed, mark_payment_paid


class PaymentConfigurationError(Exception):
    pass


class PaymentProviderError(Exception):
    pass


def _absolute_url(path: str) -> str:
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def create_stripe_checkout(payment: Payment) -> str:
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentConfigurationError("Stripe is not configured.")

    success_url = _absolute_url(reverse("stripe_success", kwargs={"pk": payment.booking_id}))
    success_url += "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = _absolute_url(reverse("booking_payment", kwargs={"pk": payment.booking_id}))
    try:
        session = stripe.checkout.Session.create(
            api_key=settings.STRIPE_SECRET_KEY,
            mode="payment",
            payment_method_types=["card"],
            client_reference_id=payment.booking.booking_code,
            customer_email=payment.booking.user.email or None,
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": payment.currency.lower(),
                        "unit_amount": int(payment.amount * 100),
                        "product_data": {"name": f"Cowo d'la val {payment.booking.booking_code}"},
                    },
                }
            ],
            metadata={"booking_code": payment.booking.booking_code, "payment_id": str(payment.pk)},
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=str(payment.idempotency_key),
        )
    except stripe.StripeError as exc:
        mark_payment_failed(payment=payment, provider_status="checkout_error")
        raise PaymentProviderError("Stripe checkout could not be created.") from exc

    payment.checkout_id = session.id
    payment.external_id = session.id
    payment.provider_status = session.status or "open"
    payment.save(update_fields=["checkout_id", "external_id", "provider_status", "updated_at"])
    return session.url


def verify_stripe_session(session) -> Payment:
    session_id = session.get("id", "")
    payment = Payment.objects.select_related("booking").get(
        provider=Payment.Provider.STRIPE,
        checkout_id=session_id,
    )
    expected_cents = int(payment.amount * 100)
    metadata = session.get("metadata") or {}
    if (
        session.get("payment_status") != "paid"
        or session.get("amount_total") != expected_cents
        or str(session.get("currency", "")).upper() != payment.currency
        or session.get("client_reference_id") != payment.booking.booking_code
        or str(metadata.get("payment_id", "")) != str(payment.pk)
    ):
        raise ValidationError("Stripe payment verification failed.")
    return mark_payment_paid(
        payment=payment,
        provider_status=session.get("payment_status", "paid"),
        transaction_id=session.get("payment_intent") or "",
        provider_metadata={"checkout_session_id": session_id},
    )


def retrieve_stripe_session(session_id: str) -> Payment:
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentConfigurationError("Stripe is not configured.")
    try:
        session = stripe.checkout.Session.retrieve(session_id, api_key=settings.STRIPE_SECRET_KEY)
    except stripe.StripeError as exc:
        raise PaymentProviderError("Stripe payment verification failed.") from exc
    return verify_stripe_session(session)


def construct_stripe_event(payload: bytes, signature: str):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise PaymentConfigurationError("Stripe webhook verification is not configured.")
    return stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)


def _json_request(url: str, *, method="GET", body=None, headers=None) -> dict:
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    request = Request(url, data=data, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=settings.PAYMENT_HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise PaymentProviderError("Payment provider request failed.") from exc


def _paypal_access_token() -> str:
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        raise PaymentConfigurationError("PayPal is not configured.")
    credentials = base64.b64encode(
        f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}".encode()
    ).decode()
    request = Request(
        f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
        data=urlencode({"grant_type": "client_credentials"}).encode(),
        method="POST",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlopen(request, timeout=settings.PAYMENT_HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode())["access_token"]
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        raise PaymentProviderError("PayPal authentication failed.") from exc


def _paypal_request(path: str, *, method="GET", body=None, request_id="") -> dict:
    headers = {
        "Authorization": f"Bearer {_paypal_access_token()}",
        "Content-Type": "application/json",
    }
    if request_id:
        headers["PayPal-Request-Id"] = request_id[:38]
    return _json_request(
        f"{settings.PAYPAL_API_BASE}{path}",
        method=method,
        body=body,
        headers=headers,
    )


def create_paypal_checkout(payment: Payment) -> str:
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": str(payment.pk),
                "custom_id": payment.booking.booking_code,
                "description": f"Cowo d'la val {payment.booking.booking_code}",
                "amount": {"currency_code": payment.currency, "value": str(payment.amount)},
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "return_url": _absolute_url(reverse("paypal_return", kwargs={"pk": payment.booking_id})),
                    "cancel_url": _absolute_url(reverse("booking_payment", kwargs={"pk": payment.booking_id})),
                    "user_action": "PAY_NOW",
                }
            }
        },
    }
    try:
        order = _paypal_request(
            "/v2/checkout/orders",
            method="POST",
            body=payload,
            request_id=str(payment.idempotency_key),
        )
        approval_url = next(link["href"] for link in order["links"] if link["rel"] in {"payer-action", "approve"})
    except (PaymentProviderError, KeyError, StopIteration) as exc:
        mark_payment_failed(payment=payment, provider_status="checkout_error")
        raise PaymentProviderError("PayPal checkout could not be created.") from exc

    payment.external_id = order["id"]
    payment.checkout_id = order["id"]
    payment.provider_status = order.get("status", "CREATED")
    payment.save(update_fields=["external_id", "checkout_id", "provider_status", "updated_at"])
    return approval_url


def _verify_paypal_capture(payment: Payment, capture: dict, order_id: str) -> Payment:
    amount = capture.get("amount") or {}
    try:
        verified_amount = Decimal(amount.get("value", "-1"))
    except InvalidOperation as exc:
        raise ValidationError("PayPal payment verification failed.") from exc
    if (
        payment.external_id != order_id
        or capture.get("status") != "COMPLETED"
        or verified_amount != payment.amount
        or amount.get("currency_code") != payment.currency
    ):
        raise ValidationError("PayPal payment verification failed.")
    return mark_payment_paid(
        payment=payment,
        provider_status=capture["status"],
        transaction_id=capture.get("id", ""),
        provider_metadata={"order_id": order_id, "capture_id": capture.get("id", "")},
    )


def capture_paypal_order(payment: Payment, order_id: str) -> Payment:
    if payment.external_id != order_id:
        raise ValidationError("PayPal order does not match this booking.")
    order = _paypal_request(
        f"/v2/checkout/orders/{order_id}/capture",
        method="POST",
        body={},
        request_id=str(payment.idempotency_key),
    )
    try:
        capture = order["purchase_units"][0]["payments"]["captures"][0]
    except (KeyError, IndexError) as exc:
        raise PaymentProviderError("PayPal did not return a completed capture.") from exc
    return _verify_paypal_capture(payment, capture, order["id"])


def verify_paypal_webhook(headers, event: dict) -> bool:
    if not settings.PAYPAL_WEBHOOK_ID:
        raise PaymentConfigurationError("PayPal webhook verification is not configured.")
    verification = _paypal_request(
        "/v1/notifications/verify-webhook-signature",
        method="POST",
        body={
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO", ""),
            "cert_url": headers.get("PAYPAL-CERT-URL", ""),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID", ""),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG", ""),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME", ""),
            "webhook_id": settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": event,
        },
    )
    return verification.get("verification_status") == "SUCCESS"


def apply_paypal_webhook(event: dict) -> Payment | None:
    if event.get("event_type") != "PAYMENT.CAPTURE.COMPLETED":
        return None
    capture = event.get("resource") or {}
    order_id = ((capture.get("supplementary_data") or {}).get("related_ids") or {}).get("order_id", "")
    payment = Payment.objects.select_related("booking").get(
        provider=Payment.Provider.PAYPAL,
        external_id=order_id,
    )
    return _verify_paypal_capture(payment, capture, order_id)


def _satispay_request(path: str, *, method="GET", body=None, idempotency_key="") -> dict:
    if not settings.SATISPAY_KEY_ID or not settings.SATISPAY_PRIVATE_KEY_PATH:
        raise PaymentConfigurationError("Satispay is not configured.")
    key_path = Path(settings.SATISPAY_PRIVATE_KEY_PATH)
    try:
        private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except (OSError, ValueError) as exc:
        raise PaymentConfigurationError("The Satispay private key could not be loaded.") from exc

    encoded_body = b"" if body is None else json.dumps(body, separators=(",", ":")).encode()
    digest = "SHA-256=" + base64.b64encode(hashlib.sha256(encoded_body).digest()).decode()
    request_date = format_datetime(datetime.now(datetime_timezone.utc), usegmt=True)
    host = urlparse(settings.SATISPAY_API_BASE).netloc
    message = "\n".join(
        [
            f"(request-target): {method.lower()} {path}",
            f"host: {host}",
            f"date: {request_date}",
            f"digest: {digest}",
        ]
    )
    signature = base64.b64encode(
        private_key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
    ).decode()
    authorization = (
        f'Signature keyId="{settings.SATISPAY_KEY_ID}", algorithm="rsa-sha256", '
        f'headers="(request-target) host date digest", signature="{signature}"'
    )
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json",
        "Date": request_date,
        "Digest": digest,
        "Host": host,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(
        f"{settings.SATISPAY_API_BASE}{path}",
        data=encoded_body if method != "GET" else None,
        method=method,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=settings.PAYMENT_HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise PaymentProviderError("Satispay request failed.") from exc


def create_satispay_checkout(payment: Payment) -> str:
    callback_url = _absolute_url(reverse("satispay_callback")) + "?payment_id={uuid}"
    redirect_url = _absolute_url(reverse("satispay_return", kwargs={"pk": payment.booking_id}))
    try:
        result = _satispay_request(
            "/g_business/v1/payments",
            method="POST",
            body={
                "flow": "MATCH_CODE",
                "amount_unit": int(payment.amount * 100),
                "currency": payment.currency,
                "external_code": payment.booking.booking_code,
                "callback_url": callback_url,
                "redirect_url": redirect_url,
                "metadata": {"payment_id": str(payment.pk)},
            },
            idempotency_key=str(payment.idempotency_key),
        )
        checkout_url = result["redirect_url"]
    except (PaymentProviderError, KeyError) as exc:
        mark_payment_failed(payment=payment, provider_status="checkout_error")
        raise PaymentProviderError("Satispay checkout could not be created.") from exc

    payment.external_id = result["id"]
    payment.checkout_id = result["id"]
    payment.provider_status = result.get("status", "PENDING")
    payment.save(update_fields=["external_id", "checkout_id", "provider_status", "updated_at"])
    return checkout_url


def retrieve_satispay_payment(payment_id: str) -> Payment:
    payment = Payment.objects.select_related("booking").get(
        provider=Payment.Provider.SATISPAY,
        external_id=payment_id,
    )
    result = _satispay_request(f"/g_business/v1/payments/{payment_id}")
    metadata = result.get("metadata") or {}
    if (
        result.get("id") != payment.external_id
        or result.get("external_code") != payment.booking.booking_code
        or result.get("amount_unit") != int(payment.amount * 100)
        or result.get("currency") != payment.currency
        or str(metadata.get("payment_id", "")) != str(payment.pk)
    ):
        raise ValidationError("Satispay payment verification failed.")
    if result.get("status") == "ACCEPTED":
        return mark_payment_paid(
            payment=payment,
            provider_status="ACCEPTED",
            transaction_id=result["id"],
            provider_metadata={"payment_id": result["id"]},
        )
    if result.get("status") == "CANCELED":
        return mark_payment_failed(payment=payment, provider_status="CANCELED")
    payment.provider_status = result.get("status", "PENDING")[:64]
    payment.save(update_fields=["provider_status", "updated_at"])
    return payment
