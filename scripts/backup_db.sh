#!/bin/sh
set -eu

backup_file=${1:-"cowodlaval-$(date +%Y%m%d-%H%M%S).sql.gz"}

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$backup_file"
printf 'Backup written to %s\n' "$backup_file"
