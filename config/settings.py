from pathlib import Path
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost" if DEBUG else "")
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production.")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "spaces",
    "bookings",
    "events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL must point to PostgreSQL.")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "it"
LANGUAGES = [
    ("it", "Italiano"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Français"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
LOGIN_URL = "login"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

if env_bool("DJANGO_BEHIND_PROXY", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
if not PUBLIC_BASE_URL:
    raise ImproperlyConfigured("PUBLIC_BASE_URL must be set.")

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")
if not DEBUG and (not CONTACT_EMAIL or not DEFAULT_FROM_EMAIL):
    raise ImproperlyConfigured("CONTACT_EMAIL and DEFAULT_FROM_EMAIL must be set in production.")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled.")
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG and not EMAIL_HOST
    else "django.core.mail.backends.smtp.EmailBackend"
)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "")
PAYPAL_ENVIRONMENT = os.getenv("PAYPAL_ENVIRONMENT", "sandbox").lower()
if PAYPAL_ENVIRONMENT not in {"sandbox", "live"}:
    raise ImproperlyConfigured("PAYPAL_ENVIRONMENT must be sandbox or live.")
PAYPAL_API_BASE = (
    "https://api-m.sandbox.paypal.com"
    if PAYPAL_ENVIRONMENT == "sandbox"
    else "https://api-m.paypal.com"
)

SATISPAY_KEY_ID = os.getenv("SATISPAY_KEY_ID", "")
SATISPAY_PRIVATE_KEY_PATH = os.getenv("SATISPAY_PRIVATE_KEY_PATH", "")
SATISPAY_ENVIRONMENT = os.getenv("SATISPAY_ENVIRONMENT", "sandbox").lower()
if SATISPAY_ENVIRONMENT not in {"sandbox", "live"}:
    raise ImproperlyConfigured("SATISPAY_ENVIRONMENT must be sandbox or live.")
SATISPAY_API_BASE = (
    "https://staging.authservices.satispay.com"
    if SATISPAY_ENVIRONMENT == "sandbox"
    else "https://authservices.satispay.com"
)

PAYMENT_HTTP_TIMEOUT = int(os.getenv("PAYMENT_HTTP_TIMEOUT", "15"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# BEGIN COWODLAVAL SECURITY HARDENING
# Added by the production security patch. Keep this block at the end of settings.py.
from urllib.parse import urlsplit as _cowodlaval_urlsplit

CACHE_URL = os.getenv("CACHE_URL", "")
if CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "cowodlaval-security",
        }
    }

RATE_LIMITS_ENABLED = env_bool("DJANGO_RATE_LIMITS_ENABLED", not DEBUG)
BEHIND_PROXY = env_bool("DJANGO_BEHIND_PROXY", False)
if BEHIND_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

_security_headers_middleware = "config.security_middleware.SecurityHeadersMiddleware"
_rate_limit_middleware = "config.security_middleware.RateLimitMiddleware"

if _security_headers_middleware not in MIDDLEWARE:
    try:
        _security_index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1
    except ValueError:
        _security_index = 0
    MIDDLEWARE.insert(_security_index, _security_headers_middleware)

if _rate_limit_middleware not in MIDDLEWARE:
    try:
        _rate_index = MIDDLEWARE.index("django.middleware.csrf.CsrfViewMiddleware")
    except ValueError:
        _rate_index = len(MIDDLEWARE)
    MIDDLEWARE.insert(_rate_index, _rate_limit_middleware)

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
PASSWORD_RESET_TIMEOUT = int(os.getenv("DJANGO_PASSWORD_RESET_TIMEOUT", "3600"))
SESSION_COOKIE_AGE = int(os.getenv("DJANGO_SESSION_COOKIE_AGE", "43200"))
SESSION_SAVE_EVERY_REQUEST = True

if not DEBUG:
    SESSION_COOKIE_NAME = "__Host-cowodlaval_session"
    CSRF_COOKIE_NAME = "__Host-cowodlaval_csrf"
    SESSION_COOKIE_PATH = "/"
    CSRF_COOKIE_PATH = "/"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

_public_url = _cowodlaval_urlsplit(PUBLIC_BASE_URL)
if (
    not _public_url.scheme
    or not _public_url.netloc
    or _public_url.username
    or _public_url.password
    or _public_url.query
    or _public_url.fragment
    or _public_url.path not in {"", "/"}
):
    raise ImproperlyConfigured("PUBLIC_BASE_URL must be a plain site origin.")

PUBLIC_ORIGIN = f"{_public_url.scheme}://{_public_url.netloc}"
if not DEBUG and _public_url.scheme != "https":
    raise ImproperlyConfigured("PUBLIC_BASE_URL must use HTTPS in production.")
if not DEBUG and PUBLIC_ORIGIN not in CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "DJANGO_CSRF_TRUSTED_ORIGINS must include PUBLIC_BASE_URL origin."
    )
# END COWODLAVAL SECURITY HARDENING
