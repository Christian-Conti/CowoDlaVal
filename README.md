# Cowo d'la val

A multilingual Django website for viewing availability, booking one of four coworking desks, and paying on site or through hosted online checkout.

![Cowo d'la val](static/img/hero-coworking.png)

## Overview

The application keeps the existing Cowo d'la val public site and adds authenticated booking management, human-readable booking codes, frozen daily prices, confirmation email, payment tracking, password recovery, Django Admin tools, and a server booking manager with terminal and desktop interfaces. Italian is the default language; English, German, and French are also available. The responsive light/dark theme follows the device preference.

## Features

- Four desk availability and database-level double-booking protection.
- Booking codes such as `COWO-2026-A1B2C3D4`.
- Standard daily rate (€8) and student/resident daily rate (€5), frozen on each booking.
- Responsive payment cards with icons for payment on site, Satispay Web Redirect, PayPal Orders v2, and Stripe Checkout.
- Verified, idempotent payment state updates; no card data enters Django or PostgreSQL.
- Localised confirmation email and authenticated manage link.
- Booking history, mobile booking cards, payment/status badges, admin filters, and terminal/desktop dashboard.
- Account registration, password change, and email-based password reset.
- PostgreSQL, Docker Compose, persistent database volume, Gunicorn, WhiteNoise, and automatic migrations.

## Architecture

- `config/`: Django settings and top-level URLs.
- `accounts/`: registration and authentication forms/views.
- `spaces/`: coworking desk model and availability.
- `bookings/`: booking/payment models, services, provider clients, email, webhooks, admin, tests, and management commands.
- `templates/`: server-rendered Django templates.
- `static/`: source CSS, JavaScript, images, and public documents.
- `locale/`: Italian, German, and French gettext catalogues; English source strings are the fallback.
- `scripts/`: PostgreSQL backup and restore helpers.

`Booking` stores the historical price, payment summary, language, and public booking code. `Payment` stores non-sensitive provider attempts and references. Provider callbacks call one locked payment transition, so repeated notifications do not create duplicate payments or duplicate receipts.

## Requirements

- Docker Engine with the Compose plugin (recommended), or Python 3.13 and PostgreSQL 16.
- A public HTTPS URL for production payment callbacks.
- Provider sandbox accounts for any online payment methods enabled.

## Quick start with Docker Compose

```sh
cp .env.example .env
```

Edit `.env`; at minimum replace `DJANGO_SECRET_KEY`, all database password placeholders, contact addresses, and `PUBLIC_BASE_URL`. Then run:

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f web
```

The entrypoint runs migrations, collects static files, creates/updates the four desks, and starts Gunicorn. Create the first administrator separately:

```sh
docker compose exec web python manage.py createsuperuser
```

Open `http://127.0.0.1:8000` for local testing.

## Local development

Create PostgreSQL and an environment file first. Then:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_cowo
python manage.py runserver 0.0.0.0:8000
```

The application intentionally has no checked-in database or secret defaults. `DJANGO_SECRET_KEY`, `DATABASE_URL`, and `PUBLIC_BASE_URL` must exist even in development.

## Environment configuration

Start from `.env.example`. `.env`, private keys, credentials directories, and database dumps are ignored by Git.

Core variables:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Long random Django signing key. |
| `DJANGO_DEBUG` | `True` only in development. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames/IP addresses. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins when required. |
| `PUBLIC_BASE_URL` | External origin used in email and provider return/callback URLs. |
| `DATABASE_URL` | PostgreSQL connection URL. |
| `CONTACT_EMAIL` | Destination for the contact form. |
| `DEFAULT_FROM_EMAIL` | Sender for application email. |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS in production. |

Use `DJANGO_BEHIND_PROXY=True` only behind a trusted proxy that sets `X-Forwarded-Proto`. Do not commit `.env`.

## PostgreSQL setup

Docker Compose reads `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` and stores data in the named `postgres_data` volume. `DATABASE_URL` must use hostname `db` inside Compose, for example:

```dotenv
DATABASE_URL=postgresql://coworking:change-me@db:5432/coworking
```

For a host-installed PostgreSQL instance, use its actual host/port and create the role/database before migrations.

## Docker Compose operation

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f web
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py bookings_dashboard
docker compose down
```

`restart: unless-stopped` is configured for both services. To start Docker after a server reboot:

```sh
sudo systemctl enable --now docker
```

The PostgreSQL named volume survives `docker compose down` and container rebuilds.

> Do **not** run `docker compose down -v` unless you intentionally want to destroy the PostgreSQL volume and all database data.

## Database migrations

After every model change:

```sh
python manage.py makemigrations
python manage.py migrate
python manage.py makemigrations --check
```

In Docker, prefix the commands with `docker compose exec web`.

## Creating a superuser

```sh
docker compose exec web python manage.py createsuperuser
```

No administrator username or password is stored in source control.

## Testing from a LAN

Set the server IP in `DJANGO_ALLOWED_HOSTS`, keep `PUBLIC_BASE_URL` consistent, and use:

```dotenv
DJANGO_SECURE_SSL_REDIRECT=False
PUBLIC_BASE_URL=http://SERVER_LAN_IP:8000
```

Then browse to:

```text
http://SERVER_LAN_IP:8000
```

Plain HTTP is for trusted local testing only. Re-enable HTTPS redirect before public deployment.

## Admin interface

Open `/admin/` as a superuser. The booking list shows code, date, desk, account/name, status, frozen amount, payment method/status, and creation time. Filters cover date, desk, booking status, payment method, and payment status. Search supports booking code and Django user identity fields. Payment records expose only non-sensitive provider/order references and metadata.

## Server booking manager

The terminal dashboard remains available inside the web container:

    docker compose exec web python manage.py bookings_dashboard

The graphical dashboard is launched on the host through `scripts/bookings_dashboard_gui.sh`. It supports both a local graphical session and SSH X11 forwarding. The web application itself remains inside Docker.

### Automatic desktop integration

Docker Compose automatically manages the graphical launcher through the `desktop-integration` helper service. `docker compose up` installs/refreshes the application-menu entry and adds the same launcher to the configured XDG desktop directory when that directory already exists. `docker compose down` removes both entries through a `pre_stop` lifecycle hook.

    docker compose up --build -d
    docker compose down

No separate `--install` or `--uninstall` command is required. Docker Compose 2.30.0 or newer is required because the integration uses `post_start` and `pre_stop` lifecycle hooks.

The helper container has no network access and is the only service that receives a host-home bind mount. It uses that mount exclusively to manage the launcher files. The Django `web` container does not receive access to the host home directory.

To open the GUI from an SSH session, connect with X11 forwarding (`ssh -XY <server>`) and launch `scripts/bookings_dashboard_gui.sh`. The host needs `xauth` and `socat`; desktop-launched errors are recorded in `~/.local/state/cowodlaval/bookings-dashboard.log` and shown with Zenity, KDialog, or XMessage when available.

Non-interactive SSH/automation examples:

```sh
docker compose exec web python manage.py bookings_dashboard --today
docker compose exec web python manage.py bookings_dashboard --date 2026-08-28
docker compose exec web python manage.py bookings_dashboard --from-date 2026-08-28 --to-date 2026-08-31
docker compose exec web python manage.py bookings_dashboard --cancel-booking COWO-2026-ABC123DEF456
docker compose exec web python manage.py bookings_dashboard --confirm-booking COWO-2026-ABC123DEF456
docker compose exec web python manage.py bookings_dashboard --mark-paid COWO-2026-ABC123DEF456
docker compose exec web python manage.py bookings_dashboard --set-notes COWO-2026-ABC123DEF456 "Needs a monitor"
```

When attached to a terminal it uses ANSI colours; add `--no-color` for plain output.

## Email setup

All mail settings come from environment variables:

```dotenv
CONTACT_EMAIL=contact@example.org
DEFAULT_FROM_EMAIL=no-reply@example.org
EMAIL_HOST=smtp.example.org
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

TLS and SSL cannot both be enabled. With `DJANGO_DEBUG=True` and an empty `EMAIL_HOST`, Django uses the console backend. Onsite confirmations are sent after selecting payment on site. Online confirmations/receipts are sent only after verified payment success.

Password reset uses the same SMTP settings. Users can request a reset from the “Forgot your password?” link on `/accounts/login/`; Django sends a time-limited link to the email stored on the account. Logged-in users can change their password from the main menu. In production, `PUBLIC_BASE_URL`, proxy HTTPS settings, and the public hostname must be consistent so reset links point to the correct site.

## Payment providers

All online methods redirect away from this application. Provider secrets stay in `.env` or mounted secret files; raw card numbers, expiry dates, CVV, and payment instruments are never accepted or stored.

### Stripe

Set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`. Hosted Checkout does not require a publishable key. Register the Stripe endpoint for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, and `checkout.session.async_payment_failed`.

Official setup: <https://docs.stripe.com/payments/checkout>.

### PayPal

Set `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, and `PAYPAL_ENVIRONMENT=sandbox` or `live`. The server creates and captures Orders v2 and asks PayPal's verification API to authenticate each webhook. Subscribe to `PAYMENT.CAPTURE.COMPLETED`.

Official setup: <https://developer.paypal.com/api/rest/integration/orders-api/>.

### Satispay

Set `SATISPAY_KEY_ID`, `SATISPAY_PRIVATE_KEY_PATH`, and `SATISPAY_ENVIRONMENT=sandbox` or `live`. Place the private PEM at `secrets/satispay-private.pem`; Compose mounts that ignored directory read-only at `/run/secrets`. The integration uses the official `MATCH_CODE` Web Redirect flow and cryptographically signed API requests. A callback never supplies trusted payment state: Django fetches payment details from Satispay and validates ID, booking code, amount, currency, and status.

Official setup: <https://developers.satispay.com/docs/web-redirect-pay>.

## Sandbox/test payment setup

1. Keep `PAYPAL_ENVIRONMENT=sandbox` and use sandbox REST app credentials.
2. Use Stripe test keys and forward test events with the Stripe CLI to the configured webhook path.
3. Create a Satispay sandbox account/key ID and set `SATISPAY_ENVIRONMENT=sandbox`.
4. Expose local callbacks through an HTTPS development tunnel and set `PUBLIC_BASE_URL` to that exact origin.
5. Never copy sandbox secrets into Git, screenshots, logs, or documentation.

Automated tests mock/avoid external network calls and test the shared verified-state transitions directly.

## Webhooks and callbacks

Register these URLs against the public HTTPS origin:

- Stripe: `/bookings/webhooks/stripe/`
- PayPal: `/bookings/webhooks/paypal/`
- Satispay callback: `/bookings/webhooks/satispay/` (the create request supplies `payment_id={uuid}`)

Stripe raw-body signatures and PayPal's verification API authenticate their webhooks. Satispay notifications trigger a separately signed payment-details request. Processing is transaction-locked and idempotent, and amount/currency/booking references are checked before marking anything paid.

## Production configuration

- Set `DJANGO_DEBUG=False`, a unique long secret key, exact allowed hosts/origins, and the final HTTPS `PUBLIC_BASE_URL`.
- Set `DJANGO_SECURE_SSL_REDIRECT=True`; enable HSTS only after HTTPS is known to work.
- Use strong unique PostgreSQL and provider credentials, restrictive file permissions, and an unprivileged deployment account.
- Configure SMTP, provider webhooks, logging/monitoring, regular backups, and restore tests.
- Run `python manage.py check --deploy` before release.

## HTTPS and reverse proxy

Terminate TLS in a maintained reverse proxy such as Nginx or Caddy, proxy to port 8000, preserve the `Host` header, and set `X-Forwarded-Proto`. Then set `DJANGO_BEHIND_PROXY=True`. Do not expose PostgreSQL publicly. Restrict inbound traffic to SSH and HTTP/HTTPS as appropriate.

## Backups

Create a compressed PostgreSQL dump without placing credentials on the command line:

```sh
./scripts/backup_db.sh
./scripts/backup_db.sh /secure/path/cowodlaval.sql.gz
```

The script reads database credentials inside the database container. Store backups encrypted, off-host, and test restores regularly.

Equivalent command:

```sh
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > backup.sql.gz
```

## Restore procedure

Stop writes, take a fresh safety backup, and restore into an empty database that matches the backup's PostgreSQL version:

```sh
./scripts/restore_db.sh /secure/path/cowodlaval.sql.gz
docker compose exec web python manage.py migrate
```

Equivalent command:

```sh
gunzip -c backup.sql.gz | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

Restoring into a populated database can conflict with existing objects. Validate the restored booking count and dashboard before reopening traffic.

## Updating the application

```sh
git pull --ff-only
docker compose build --pull web
docker compose up -d
docker compose exec web python manage.py migrate
docker compose ps
docker compose logs --tail=200 web
```

Take a database backup before upgrades. Keep the previous image/revision available for application rollback; database migrations may require a separate tested rollback plan.

## Testing

```sh
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py check
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py makemigrations --check
python manage.py compilemessages
docker compose config
```

Production settings intentionally require environment values, while `config.settings_test` provides isolated SQLite/email test configuration.

## Troubleshooting

- **Startup says an environment variable is missing:** compare `.env` with `.env.example` and rebuild/restart the web service.
- **Database is unavailable:** run `docker compose ps`, inspect `docker compose logs db`, and confirm the `db` hostname in `DATABASE_URL`.
- **Static files are missing:** run `docker compose exec web python manage.py collectstatic --noinput`.
- **Mail appears only in logs:** an empty `EMAIL_HOST` with debug enabled intentionally selects the console backend.
- **Payment remains pending:** inspect provider dashboard events, HTTPS reachability, webhook secret/ID, registered URL, amount/currency, and web logs. Do not mark it paid manually without provider evidence.
- **Redirect loop on LAN:** set `DJANGO_SECURE_SSL_REDIRECT=False` only for local HTTP.
- **Satispay authentication fails:** check environment selection, key ID, PEM path/permissions, and server clock.

## Security notes

- No production secret, personal credential, or payment credential belongs in Git.
- The application never handles or stores raw card details.
- Webhooks are CSRF-exempt only where required and reject unverified data.
- Payment transitions use database locks, verify frozen amount/currency/reference, and are safe to repeat.
- The active desk/date uniqueness constraint remains enforced by PostgreSQL.
- Keep dependencies, Docker, PostgreSQL, the reverse proxy, and the host patched.

## Booking cancellation policy

Only bookings with **payment in person** can be cancelled or modified autonomously. For cancellations less than 12 hours before the booking, a 50% expense reimbursement is requested. Online-paid bookings cannot be changed or cancelled through the website; the user must contact coworking staff for assistance or a possible refund. This rule is enforced server-side as well as in the interface.

## Data and privacy considerations

The database contains Django account identity/contact data, booking dates/desks/notes, historical prices, and non-sensitive provider transaction references. It does not contain card numbers, CVV, expiry dates, or provider credentials. Define retention, account deletion, access control, incident response, and privacy notices appropriate to the operator's jurisdiction. Avoid placing sensitive personal information in booking notes or logs.
