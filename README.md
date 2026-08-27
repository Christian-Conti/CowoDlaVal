# Cowo d'la val - Coworking booking site

A booking site for managing daily reservations of four coworking stations at **Cowo d'la val**.

## What has been integrated

- PostgreSQL instead of SQLite.
- Interface and content rebuilt from the "coworking space" source material.
- Four bookable workstations by date, with double-booking prevention controls both at the application and database levels.
- User registration, login, booking cancellation, and Django admin panel.
- Languages: Italian, English, German, and French.
- Automatic light/dark theme based on operating system/browser preference.
- Contact form to `cowodlaval@inventati.org`, configurable via environment variables.
- Rates, services, shared rules, and original informational PDF available from the site.
- WhiteNoise for static assets, Gunicorn, and parameterized security settings for production.
- Dockerfile and Docker Compose with PostgreSQL.

## Important security note

The PDF `New Services - MAIL.pdf` from the source material contains real access credentials. For this reason, **it is not distributed on the site or in the final package**. The old HTML prototype also contained Supabase configuration and an admin password directly in JavaScript. That logic has been completely removed: database and administration now pass through secure environment variables and Django's built-in security mechanisms.

## Getting started with Docker Compose

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Modify at least:

```text
DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS
DJANGO_CSRF_TRUSTED_ORIGINS
POSTGRES_PASSWORD
DATABASE_URL
```

For Docker Compose, the `DATABASE_URL` value must use `db` as the hostname, for example:

```text
DATABASE_URL=postgresql://coworking:A_STRONG_PASSWORD@db:5432/coworking
```

3. Start the containers:

```bash
docker compose up --build -d
```

Migrations, `collectstatic`, and the creation/update of the four workstations run automatically when the web container starts.

4. Create the Django administrator:

```bash
docker compose exec web python manage.py createsuperuser
```

5. In local development, the site will be available at:

```text
http://127.0.0.1:8000/
```

## Deploy without Docker

Requires Python 3.12+ and an accessible PostgreSQL instance.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_cowo
python manage.py createsuperuser
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

In production, Gunicorn should run behind an HTTPS reverse proxy, such as Nginx, Caddy, or your provider's proxy.

## Email configuration

The **Contact** form sends requests to the address defined by:

```text
CONTACT_EMAIL=cowodlaval@inventati.org
```

For actual email delivery, SMTP settings must also be configured in `.env`:

```text
EMAIL_HOST
EMAIL_PORT
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
EMAIL_USE_TLS
EMAIL_USE_SSL
DEFAULT_FROM_EMAIL
```

SMTP credentials must not be committed to the repository.

## HTTPS and security

When the final domain is active behind HTTPS:

```text
DJANGO_DEBUG=False
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_BEHIND_PROXY=True
```

Set `DJANGO_CSRF_TRUSTED_ORIGINS` with the HTTPS schema, for example:

```text
DJANGO_CSRF_TRUSTED_ORIGINS=https://cowodlaval.example.org
```

`DJANGO_SECURE_HSTS_SECONDS` is left at `0` in the example file. After verifying that the site functions exclusively over HTTPS, it can be increased gradually.

Before final deployment, run:

```bash
python manage.py check --deploy
```

Before opening to the public, it's also recommended to verify backups, password recovery, SMTP address, final domain, and applicable privacy policy for the service. The site does not include analytics or third-party tracking by default.

## Tests

Tests use separate settings with SQLite in memory, to keep the automated test suite independent of the production database:

```bash
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
```

The normal application does not use SQLite.

## Main structure

```text
accounts/                 user registration
bookings/                 reservations, constraints, and transaction logic
config/                   settings, home, and contact form
locale/                   translations for IT/DE/FR; English as source language
spaces/                   four coworking workstations
templates/                HTML interface
static/css/               responsive light/dark theme
static/img/               provided logos
static/docs/              provided rates/rules PDF
Dockerfile                web image
docker-compose.yml        web stack + PostgreSQL
```

## Backup

The PostgreSQL volume contains reservation data. In production, it is recommended to use managed PostgreSQL or set up periodic backups with `pg_dump`, stored outside the application server.
