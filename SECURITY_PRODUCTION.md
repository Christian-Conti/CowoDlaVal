# CowoDlaVal production security

This hardening keeps the public booking username visible but no longer exposes
the user's full name on the public availability page.

## Included hardening

- Shared Compose base with a small production override and Caddy automatic HTTPS.
- Gunicorn is not published directly in production.
- PostgreSQL and Redis are reachable only on an internal Docker network.
- Redis-backed rate limiting for login, signup, password reset, contact form,
  admin login, and payment callbacks.
- Request-size limits on sensitive endpoints.
- Content Security Policy and additional browser security headers.
- Secure `__Host-` session and CSRF cookies in production.
- One-hour password-reset tokens and a 12-hour sliding session timeout.
- Strict validation of the production public HTTPS origin.
- Case-insensitive unique email enforcement at PostgreSQL level.
- Login timing equalisation for unknown email addresses.
- Private event images are marked `private, no-store`.
- Safer `Content-Disposition` generation for event images.
- Development port binds to localhost by default.
- Desktop integration has no container network access.
- Production web container drops Linux capabilities and forbids privilege gain.
- Dependabot and a weekly `pip-audit` workflow.

## Apply the patch

Run from a clean repository checkout:

```bash
bash apply_security_patch_v3.sh
```

The script creates a backup branch before changing tracked files. Review the
result with:

```bash
git diff
git status
```

## Create the production environment

```bash
./scripts/init_production_env.sh \
    cowo.example.org \
    contact@cowo.example.org \
    no-reply@cowo.example.org
```

Then edit `.env.production` and configure SMTP and the payment providers you
actually use. Keep the file mode at `600`.

Before starting Caddy, the public DNS A/AAAA record must point to the server and
TCP ports 80 and 443 must reach the server. UDP 443 is used for HTTP/3.

## Validate before deployment

```bash
./scripts/production_security_check.sh
```

The email migration intentionally aborts if duplicate case-insensitive email
addresses already exist. Resolve those duplicates manually and rerun the
migration.

## Start production

```bash
docker compose \
    --env-file .env.production \
    -f compose.prod.yaml \
    up --build -d
```

Check:

```bash
docker compose \
    --env-file .env.production \
    -f compose.prod.yaml \
    ps

docker compose \
    --env-file .env.production \
    -f compose.prod.yaml \
    logs -f caddy web
```

Do not publish port 8000 on the production server. Only Caddy publishes
80/443.

## HSTS rollout

Start with:

```text
DJANGO_SECURE_HSTS_SECONDS=3600
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
DJANGO_SECURE_HSTS_PRELOAD=False
```

After HTTPS has worked correctly for a suitable validation period, increase the
HSTS lifetime. Enable subdomains or preload only if every relevant subdomain is
permanently HTTPS.

## Host-level items that cannot be safely automated by this patch

The repository cannot safely decide your SSH/firewall policy or backup
destination. Before Internet exposure, configure the host so that:

- only required inbound ports are open, normally SSH plus 80/443;
- SSH uses keys and root/password login is disabled where appropriate;
- the OS and Docker receive security updates;
- PostgreSQL backups are encrypted, stored off-host, and restore-tested;
- production secrets are backed up separately and never committed.

Multi-factor authentication for Django Admin is intentionally not enabled
automatically because doing so requires enrolling an administrator and an
out-of-band recovery procedure. Add MFA before exposing high-value
administrative accounts if the deployment requires it.
