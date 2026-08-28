#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ -z "${DISPLAY:-}" ]]; then
    echo "Error: DISPLAY is not set."
    echo "Connect with X11 forwarding, for example: ssh -XY <server>"
    exit 1
fi

for command in docker xauth socat ss awk; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Error: required command '$command' is not installed."
        exit 1
    fi
done

if ! docker compose ps --status running web >/dev/null 2>&1; then
    echo "Error: the Docker Compose web service is not running."
    exit 1
fi

DISPLAY_NUM="${DISPLAY#*:}"
DISPLAY_NUM="${DISPLAY_NUM%%.*}"

if ! [[ "$DISPLAY_NUM" =~ ^[0-9]+$ ]]; then
    echo "Error: unsupported DISPLAY value: $DISPLAY"
    exit 1
fi

SSH_X_PORT=$((6000 + DISPLAY_NUM))
PROXY_DISPLAY=99
PROXY_PORT=$((6000 + PROXY_DISPLAY))

WEB_CONTAINER="$(docker compose ps -q web)"

if [[ -z "$WEB_CONTAINER" ]]; then
    echo "Error: unable to find the web container."
    exit 1
fi

NETWORK="$(
    docker inspect "$WEB_CONTAINER" \
        --format '{{range $name, $network := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' \
        | head -n 1
)"

if [[ -z "$NETWORK" ]]; then
    echo "Error: unable to determine the Docker network."
    exit 1
fi

GW="$(
    docker network inspect "$NETWORK" \
        --format '{{(index .IPAM.Config 0).Gateway}}'
)"

if [[ -z "$GW" ]]; then
    echo "Error: unable to determine the Docker network gateway."
    exit 1
fi

COOKIE="$(
    xauth list \
        | awk -v n="$DISPLAY_NUM" '$1 ~ (":" n "$") {print $3; exit}'
)"

if [[ -z "$COOKIE" ]]; then
    echo "Error: unable to find the X11 authentication cookie for DISPLAY=$DISPLAY."
    exit 1
fi

XAUTH_HOST="$(mktemp /tmp/cowodlaval-xauth.XXXXXX)"
SOCAT_LOG="$(mktemp /tmp/cowodlaval-socat.XXXXXX.log)"
SOCAT_PID=""

cleanup() {
    if [[ -n "$SOCAT_PID" ]] && kill -0 "$SOCAT_PID" 2>/dev/null; then
        kill "$SOCAT_PID" 2>/dev/null || true
        wait "$SOCAT_PID" 2>/dev/null || true
    fi

    rm -f "$XAUTH_HOST"
}

trap cleanup EXIT INT TERM

xauth -f "$XAUTH_HOST" add \
    "$GW:${PROXY_DISPLAY}.0" \
    MIT-MAGIC-COOKIE-1 \
    "$COOKIE"

chmod 644 "$XAUTH_HOST"

# Remove a stale proxy from a previous interrupted run.
pkill -f "socat.*TCP-LISTEN:${PROXY_PORT}.*bind=${GW}" 2>/dev/null || true

socat \
    TCP-LISTEN:"${PROXY_PORT}",bind="$GW",reuseaddr,fork \
    TCP:127.0.0.1:"${SSH_X_PORT}" \
    >"$SOCAT_LOG" 2>&1 &

SOCAT_PID=$!

sleep 0.3

if ! kill -0 "$SOCAT_PID" 2>/dev/null; then
    echo "Error: unable to start the X11 proxy."
    cat "$SOCAT_LOG"
    exit 1
fi

if ! ss -ltn | grep -q "${GW}:${PROXY_PORT}"; then
    echo "Error: the X11 proxy is not listening on ${GW}:${PROXY_PORT}."
    cat "$SOCAT_LOG"
    exit 1
fi

docker cp \
    "$XAUTH_HOST" \
    "${WEB_CONTAINER}:/tmp/.cowodlaval-xauth"

docker compose exec -u root web \
    chmod 644 /tmp/.cowodlaval-xauth

echo "SSH DISPLAY:       $DISPLAY"
echo "SSH X11 port:      $SSH_X_PORT"
echo "Docker network:    $NETWORK"
echo "Docker gateway:    $GW"
echo "Container DISPLAY: ${GW}:${PROXY_DISPLAY}.0"

docker compose exec \
    -e DISPLAY="${GW}:${PROXY_DISPLAY}.0" \
    -e XAUTHORITY=/tmp/.cowodlaval-xauth \
    -e XDG_CACHE_HOME=/tmp/.cache \
    web \
    sh -lc 'mkdir -p /tmp/.cache/fontconfig && python manage.py bookings_dashboard --gui'
