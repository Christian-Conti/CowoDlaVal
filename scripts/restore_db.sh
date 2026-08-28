#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    printf 'Usage: %s BACKUP.sql.gz\n' "$0" >&2
    exit 2
fi

if [ ! -f "$1" ]; then
    printf 'Backup not found: %s\n' "$1" >&2
    exit 2
fi

gunzip -c "$1" | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"'
printf 'Restore completed from %s\n' "$1"
