import hashlib
import ipaddress
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


logger = logging.getLogger(__name__)

_KIB = 1024
_MIB = 1024 * _KIB

_BODY_LIMITS = {
    ("POST", "/accounts/login/"): 64 * _KIB,
    ("POST", "/accounts/signup/"): 128 * _KIB,
    ("POST", "/accounts/password_reset/"): 64 * _KIB,
    ("POST", "/admin/login/"): 64 * _KIB,
    ("POST", "/contact/"): 256 * _KIB,
    ("POST", "/bookings/webhooks/stripe/"): 1 * _MIB,
    ("POST", "/bookings/webhooks/paypal/"): 1 * _MIB,
}

_RATE_RULES = {
    ("POST", "/accounts/login/"): (
        ("ip", 12, 300, None),
        ("identity", 30, 300, "username"),
    ),
    ("POST", "/accounts/signup/"): (
        ("ip", 8, 3600, None),
        ("identity", 12, 3600, "email"),
    ),
    ("POST", "/accounts/password_reset/"): (
        ("ip", 6, 3600, None),
        ("identity", 10, 3600, "email"),
    ),
    ("POST", "/admin/login/"): (
        ("ip", 10, 600, None),
        ("identity", 20, 600, "username"),
    ),
    ("POST", "/contact/"): (
        ("ip", 10, 3600, None),
    ),
    ("POST", "/bookings/webhooks/stripe/"): (
        ("ip", 300, 60, None),
    ),
    ("POST", "/bookings/webhooks/paypal/"): (
        ("ip", 300, 60, None),
    ),
    ("GET", "/bookings/webhooks/satispay/"): (
        ("ip", 300, 60, None),
    ),
}


def _normalise_ip(value):
    if not value:
        return ""
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return ""


def _client_ip(request):
    if settings.BEHIND_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            address = _normalise_ip(forwarded.split(",", 1)[0])
            if address:
                return address

    return _normalise_ip(request.META.get("REMOTE_ADDR", "")) or "unknown"


def _hashed_identifier(value):
    value = (value or "").strip().lower()[:512]
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _counter_value(key, timeout):
    try:
        if cache.add(key, 1, timeout=timeout):
            return 1
        try:
            return cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=timeout)
            return 1
    except Exception:
        # A cache outage must not make the whole site unavailable.
        logger.exception("Rate-limit cache is unavailable")
        return 0


def _too_many_requests(timeout):
    response = HttpResponse("Too many requests. Please try again later.", status=429)
    response["Retry-After"] = str(timeout)
    response["Cache-Control"] = "no-store"
    return response


def _request_too_large():
    response = HttpResponse("Request body is too large.", status=413)
    response["Cache-Control"] = "no-store"
    return response


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rule_key = (request.method, request.path)

        max_body = _BODY_LIMITS.get(rule_key)
        if max_body is not None:
            content_length = request.META.get("CONTENT_LENGTH", "")
            if content_length:
                try:
                    if int(content_length) > max_body:
                        return _request_too_large()
                except ValueError:
                    return _request_too_large()

        if not settings.RATE_LIMITS_ENABLED:
            return self.get_response(request)

        rules = _RATE_RULES.get(rule_key, ())
        for scope, limit, window, field in rules:
            if scope == "ip":
                identifier = _client_ip(request)
            else:
                identifier = _hashed_identifier(request.POST.get(field, ""))

            cache_key = (
                "cowodlaval:ratelimit:"
                f"{request.method}:{request.path}:{scope}:"
                f"{_hashed_identifier(identifier)}"
            )
            if _counter_value(cache_key, window) > limit:
                return _too_many_requests(window)

        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if "Content-Security-Policy" not in response:
            script_source = "'self'"
            if request.path.startswith("/admin/"):
                # Django Admin can require inline script in some views.
                script_source = "'self' 'unsafe-inline'"
            frame_source = (
                "https://www.google.com" if request.path == "/contact/" else "'none'"
            )

            directives = [
                "default-src 'self'",
                "base-uri 'self'",
                "object-src 'none'",
                "frame-ancestors 'none'",
                f"frame-src {frame_source}",
                "img-src 'self' data:",
                "font-src 'self' data:",
                "style-src 'self' 'unsafe-inline'",
                f"script-src {script_source}",
                "connect-src 'self'",
                "form-action 'self'",
                "manifest-src 'self'",
            ]
            if not settings.DEBUG:
                directives.append("upgrade-insecure-requests")

            response["Content-Security-Policy"] = "; ".join(directives)

        if "Permissions-Policy" not in response:
            response["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=(), usb=()"
            )

        if "X-Permitted-Cross-Domain-Policies" not in response:
            response["X-Permitted-Cross-Domain-Policies"] = "none"

        return response
