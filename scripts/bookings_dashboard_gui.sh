#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

STATE_DIR="${HOME}/.local/state/cowodlaval"
LOG_FILE="${STATE_DIR}/bookings-dashboard.log"
mkdir -p "$STATE_DIR"

log_error() {
    local message="$1"
    printf '%s\n' "$message" >&2
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$message" >> "$LOG_FILE"
}

show_error_dialog() {
    local message="$1"

    if [[ -z "${DISPLAY:-}" ]]; then
        return
    fi

    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Cowo d'la val" --text="$message" >/dev/null 2>&1 || true
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "$message" --title "Cowo d'la val" >/dev/null 2>&1 || true
    elif command -v xmessage >/dev/null 2>&1; then
        xmessage -center "$message" >/dev/null 2>&1 || true
    fi
}

fail() {
    local message="$1"
    log_error "$message"
    show_error_dialog "$message"
    exit 1
}

require_command() {
    local command="$1"

    if ! command -v "$command" >/dev/null 2>&1; then
        fail "Required command '$command' is not installed on the host."
    fi
}

if [[ -z "${DISPLAY:-}" ]]; then
    fail "DISPLAY is not set. Use the server graphical session or connect through SSH with X11 forwarding (ssh -XY <server>)."
fi

for command in docker xauth socat awk; do
    require_command "$command"
done

if ! docker compose ps --status running web 2>/dev/null | grep -q .; then
    fail "The Docker Compose web service is not running. Start it with: docker compose up -d"
fi

WEB_CONTAINER="$(docker compose ps -q web)"

if [[ -z "$WEB_CONTAINER" ]]; then
    fail "Unable to find the Docker Compose web container."
fi

DISPLAY_NUM="${DISPLAY#*:}"
DISPLAY_NUM="${DISPLAY_NUM%%.*}"

if ! [[ "$DISPLAY_NUM" =~ ^[0-9]+$ ]]; then
    fail "Unsupported DISPLAY value: $DISPLAY"
fi

DISPLAY_HOST="${DISPLAY%%:*}"

NETWORK="$(
    docker inspect "$WEB_CONTAINER" \
        --format '{{range $name, $network := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' \
        | head -n 1
)"

if [[ -z "$NETWORK" ]]; then
    fail "Unable to determine the Docker network used by the web service."
fi

GW="$(
    docker network inspect "$NETWORK" \
        --format '{{(index .IPAM.Config 0).Gateway}}'
)"

if [[ -z "$GW" ]]; then
    fail "Unable to determine the Docker network gateway."
fi

COOKIE="$(
    xauth list "$DISPLAY" 2>/dev/null \
        | awk 'NF >= 3 {print $3; exit}'
)"

if [[ -z "$COOKIE" ]]; then
    COOKIE="$(
        xauth list 2>/dev/null \
            | awk -v n="$DISPLAY_NUM" '$1 ~ (":" n "(\\.0)?$") {print $3; exit}'
    )"
fi

if [[ -z "$COOKIE" ]]; then
    fail "Unable to find the X11 authentication cookie for DISPLAY=$DISPLAY."
fi

XAUTH_HOST="$(mktemp /tmp/cowodlaval-xauth.XXXXXX)"
SOCAT_LOG="$(mktemp /tmp/cowodlaval-socat.XXXXXX.log)"
SOCAT_PID=""
PROXY_DISPLAY=""

cleanup() {
    if [[ -n "$SOCAT_PID" ]] && kill -0 "$SOCAT_PID" 2>/dev/null; then
        kill "$SOCAT_PID" 2>/dev/null || true
        wait "$SOCAT_PID" 2>/dev/null || true
    fi

    rm -f "$XAUTH_HOST" "$SOCAT_LOG"
}

trap cleanup EXIT INT TERM

if [[ "$DISPLAY_HOST" == "localhost" || "$DISPLAY_HOST" == "127.0.0.1" ]]; then
    SOURCE_DESCRIPTION="127.0.0.1:$((6000 + DISPLAY_NUM))"
    SOCAT_TARGET="TCP:127.0.0.1:$((6000 + DISPLAY_NUM))"
elif [[ -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ]]; then
    SOURCE_DESCRIPTION="/tmp/.X11-unix/X${DISPLAY_NUM}"
    SOCAT_TARGET="UNIX-CONNECT:/tmp/.X11-unix/X${DISPLAY_NUM}"
elif [[ -n "$DISPLAY_HOST" ]]; then
    SOURCE_DESCRIPTION="${DISPLAY_HOST}:$((6000 + DISPLAY_NUM))"
    SOCAT_TARGET="TCP:${DISPLAY_HOST}:$((6000 + DISPLAY_NUM))"
else
    fail "Unable to determine how to reach DISPLAY=$DISPLAY."
fi

for candidate in $(seq 90 109); do
    : > "$SOCAT_LOG"

    socat \
        TCP-LISTEN:"$((6000 + candidate))",bind="$GW",reuseaddr,fork \
        "$SOCAT_TARGET" \
        >"$SOCAT_LOG" 2>&1 &

    candidate_pid=$!
    sleep 0.15

    if kill -0 "$candidate_pid" 2>/dev/null; then
        PROXY_DISPLAY="$candidate"
        SOCAT_PID="$candidate_pid"
        break
    fi

    wait "$candidate_pid" 2>/dev/null || true
done

if [[ -z "$PROXY_DISPLAY" || -z "$SOCAT_PID" ]]; then
    log_error "Unable to start the X11 proxy."
    if [[ -s "$SOCAT_LOG" ]]; then
        cat "$SOCAT_LOG" >&2
        cat "$SOCAT_LOG" >> "$LOG_FILE"
    fi
    show_error_dialog "Unable to start the X11 proxy. See $LOG_FILE for details."
    exit 1
fi

xauth -f "$XAUTH_HOST" add \
    "$GW:${PROXY_DISPLAY}.0" \
    MIT-MAGIC-COOKIE-1 \
    "$COOKIE"

chmod 644 "$XAUTH_HOST"

docker cp \
    "$XAUTH_HOST" \
    "${WEB_CONTAINER}:/tmp/.cowodlaval-xauth" \
    >/dev/null

docker compose exec -u root web \
    chmod 644 /tmp/.cowodlaval-xauth

printf '[%s] Host DISPLAY=%s; source=%s; container DISPLAY=%s:%s.0\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" \
    "$DISPLAY" \
    "$SOURCE_DESCRIPTION" \
    "$GW" \
    "$PROXY_DISPLAY" \
    >> "$LOG_FILE"

docker compose exec \
    -e DISPLAY="${GW}:${PROXY_DISPLAY}.0" \
    -e XAUTHORITY=/tmp/.cowodlaval-xauth \
    -e XDG_CACHE_HOME=/tmp/.cache \
    web \
    sh -lc 'mkdir -p /tmp/.cache/fontconfig && python manage.py bookings_dashboard --gui' \
    || fail "The bookings dashboard GUI exited with an error. See $LOG_FILE for details."
