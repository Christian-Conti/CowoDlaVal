#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -z "${DISPLAY:-}" ]]; then
    echo "ERROR: DISPLAY is not set."
    echo "Connect using: ssh -XY user@host"
    exit 1
fi

for cmd in docker xauth socat; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: '$cmd' is required."
        exit 1
    fi
done

WEB_CONTAINER="$(docker compose ps -q web)"

if [[ -z "$WEB_CONTAINER" ]]; then
    echo "ERROR: web container is not running."
    exit 1
fi

DISPLAY_NUM="${DISPLAY#*:}"
DISPLAY_NUM="${DISPLAY_NUM%%.*}"

if ! [[ "$DISPLAY_NUM" =~ ^[0-9]+$ ]]; then
    echo "ERROR: invalid DISPLAY: $DISPLAY"
    exit 1
fi

SSH_X_PORT=$((6000 + DISPLAY_NUM))

GW="$(
    docker inspect "$WEB_CONTAINER" \
        --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{"\n"}}{{end}}' \
        | head -n 1
)"

if [[ -z "$GW" ]]; then
    echo "ERROR: could not determine Docker gateway."
    exit 1
fi

COOKIE="$(
    xauth list "$DISPLAY" 2>/dev/null \
        | awk 'NR == 1 {print $3}'
)"

if [[ -z "$COOKIE" ]]; then
    COOKIE="$(
        xauth list \
            | awk -v n="$DISPLAY_NUM" '$1 ~ (":" n "($|\\.)") {print $3; exit}'
    )"
fi

if [[ -z "$COOKIE" ]]; then
    echo "ERROR: could not find X11 authentication cookie."
    echo "DISPLAY=$DISPLAY"
    exit 1
fi

PROXY_DISPLAY=99
PROXY_PORT=6099

XAUTH_FILE="$(mktemp /tmp/cowodlaval-xauth.XXXXXX)"
SOCAT_LOG="$(mktemp /tmp/cowodlaval-socat.XXXXXX)"

SOCAT_PID=""

cleanup() {
    if [[ -n "$SOCAT_PID" ]]; then
        kill "$SOCAT_PID" 2>/dev/null || true
    fi

    rm -f "$XAUTH_FILE" "$SOCAT_LOG"
}

trap cleanup EXIT INT TERM

touch "$XAUTH_FILE"

xauth -f "$XAUTH_FILE" add \
    "$GW:${PROXY_DISPLAY}.0" \
    MIT-MAGIC-COOKIE-1 \
    "$COOKIE"

chmod 644 "$XAUTH_FILE"

pkill -f "socat.*TCP-LISTEN:${PROXY_PORT}" 2>/dev/null || true

socat \
    TCP-LISTEN:${PROXY_PORT},bind="$GW",reuseaddr,fork \
    TCP:127.0.0.1:${SSH_X_PORT} \
    >"$SOCAT_LOG" 2>&1 &

SOCAT_PID=$!

sleep 0.5

if ! kill -0 "$SOCAT_PID" 2>/dev/null; then
    echo "ERROR: socat failed:"
    cat "$SOCAT_LOG"
    exit 1
fi

docker cp \
    "$XAUTH_FILE" \
    "$WEB_CONTAINER:/tmp/.docker.xauth"

docker compose exec -u root web \
    chmod 644 /tmp/.docker.xauth

echo
echo "SSH DISPLAY:       $DISPLAY"
echo "SSH X11 port:      $SSH_X_PORT"
echo "Docker gateway:    $GW"
echo "Container DISPLAY: $GW:${PROXY_DISPLAY}.0"
echo

docker compose exec \
    -e DISPLAY="$GW:${PROXY_DISPLAY}.0" \
    -e XAUTHORITY=/tmp/.docker.xauth \
    -e XDG_CACHE_HOME=/tmp/.cache \
    web \
    sh -lc '
        mkdir -p /tmp/.cache/fontconfig
        python manage.py bookings_dashboard --gui
    '
