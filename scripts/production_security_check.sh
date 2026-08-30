#!/usr/bin/env bash
set -euo pipefail

# Validate the production Compose configuration and Django deployment settings.

[[ -f .env.production ]] || {
    echo "Missing .env.production. Run scripts/init_production_env.sh first." >&2
    exit 1
}

docker compose \
    --env-file .env.production \
    -f compose.yaml \
    -f compose.prod.yaml \
    config >/dev/null

docker compose \
    --env-file .env.production \
    -f compose.yaml \
    -f compose.prod.yaml \
    run --rm web \
    python manage.py check --deploy

docker compose \
    --env-file .env.production \
    -f compose.yaml \
    -f compose.prod.yaml \
    run --rm web \
    python manage.py test

echo "Production security checks passed."
