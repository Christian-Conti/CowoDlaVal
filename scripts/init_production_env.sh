#!/usr/bin/env bash
set -euo pipefail

# Create a production environment file with generated Django and database secrets.

if [[ $# -ne 3 ]]; then
    printf 'Usage: %s <domain> <contact-email> <from-email>\n' "$0" >&2
    exit 1
fi

domain="$1"
contact_email="$2"
from_email="$3"

[[ "${domain}" != *"://"* && "${domain}" != *"/"* ]] || {
    echo "Domain must be a hostname without scheme or path." >&2
    exit 1
}

command -v python3 >/dev/null 2>&1 || {
    echo "python3 is required." >&2
    exit 1
}

[[ ! -e .env.production ]] || {
    echo ".env.production already exists; refusing to overwrite it." >&2
    exit 1
}

umask 077

django_secret="$(python3 - <<'PY_SECRET'
import secrets
print(secrets.token_urlsafe(64))
PY_SECRET
)"

db_password="$(python3 - <<'PY_DB'
import secrets
print(secrets.token_hex(32))
PY_DB
)"

cp .env.production.example .env.production

python3 - "$domain" "$contact_email" "$from_email" "$django_secret" "$db_password" <<'PY_ENV'
from pathlib import Path
import sys

domain, contact_email, from_email, django_secret, db_password = sys.argv[1:]
path = Path(".env.production")
text = path.read_text(encoding="utf-8")

replacements = {
    "cowo.example.org": domain,
    "REPLACE_WITH_A_LONG_RANDOM_SECRET": django_secret,
    "REPLACE_WITH_DB_PASSWORD": db_password,
    "contact@example.org": contact_email,
    "no-reply@example.org": from_email,
}

for old, new in replacements.items():
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
PY_ENV

chmod 600 .env.production

echo "Created .env.production with mode 600."
echo "Review SMTP and payment-provider credentials before deployment."
