#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${PROJECT_DIR}/scripts/bookings_dashboard_gui.sh"

APP_NAME="Cowo d'la Val - DB Controller"
DESKTOP_FILE_NAME="cowodlaval-db-controller.desktop"

USER_APPLICATIONS_DIR="${HOME}/.local/share/applications"
USER_BIN_DIR="${HOME}/.local/bin"

LAUNCHER_PATH="${USER_BIN_DIR}/cowodlaval-db-controller"
APPLICATION_PATH="${USER_APPLICATIONS_DIR}/${DESKTOP_FILE_NAME}"


install_launcher() {
    echo "Installing Cowo d'la Val DB Controller launcher..."

    mkdir -p "$USER_APPLICATIONS_DIR"
    mkdir -p "$USER_BIN_DIR"

    # Create a stable launcher pointing to this project.
    cat >"$LAUNCHER_PATH" <<EOF
#!/usr/bin/env bash
exec "${SCRIPT_PATH}" "\$@"
EOF

    chmod +x "$LAUNCHER_PATH"

    # Create the application menu entry.
    cat >"$APPLICATION_PATH" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_NAME}
Comment=Open the Cowo d'la Val bookings database controller
Exec=${LAUNCHER_PATH}
Icon=utilities-system-monitor
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF

    chmod +x "$APPLICATION_PATH"

    # Install a desktop shortcut if the user has a desktop directory.
    if command -v xdg-user-dir >/dev/null 2>&1; then
        DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
    else
        DESKTOP_DIR="${HOME}/Desktop"
    fi

    if [[ -n "${DESKTOP_DIR:-}" && -d "$DESKTOP_DIR" ]]; then
        DESKTOP_PATH="${DESKTOP_DIR}/${DESKTOP_FILE_NAME}"

        cp "$APPLICATION_PATH" "$DESKTOP_PATH"
        chmod +x "$DESKTOP_PATH"

        # Mark the desktop launcher as trusted when supported.
        if command -v gio >/dev/null 2>&1; then
            gio set "$DESKTOP_PATH" metadata::trusted true \
                >/dev/null 2>&1 || true
        fi

        echo "Desktop shortcut installed:"
        echo "  $DESKTOP_PATH"
    else
        echo "Desktop directory not found; desktop shortcut skipped."
    fi

    # Refresh desktop application database when available.
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$USER_APPLICATIONS_DIR" \
            >/dev/null 2>&1 || true
    fi

    echo
    echo "Application menu entry installed:"
    echo "  $APPLICATION_PATH"
    echo
    echo "Launcher installed:"
    echo "  $LAUNCHER_PATH"
}


uninstall_launcher() {
    echo "Removing Cowo d'la Val DB Controller launcher..."

    rm -f "$APPLICATION_PATH"
    rm -f "$LAUNCHER_PATH"

    if command -v xdg-user-dir >/dev/null 2>&1; then
        DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
    else
        DESKTOP_DIR="${HOME}/Desktop"
    fi

    if [[ -n "${DESKTOP_DIR:-}" ]]; then
        rm -f "${DESKTOP_DIR}/${DESKTOP_FILE_NAME}"
    fi

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$USER_APPLICATIONS_DIR" \
            >/dev/null 2>&1 || true
    fi

    echo "Launcher removed."
}


case "${1:-}" in
    --install)
        install_launcher
        exit 0
        ;;

    --uninstall)
        uninstall_launcher
        exit 0
        ;;

    --help|-h)
        echo "Usage:"
        echo "  $0             Open the bookings DB controller GUI"
        echo "  $0 --install   Install application-menu and desktop launchers"
        echo "  $0 --uninstall Remove installed launchers"
        exit 0
        ;;
esac


cd "$PROJECT_DIR"


if [[ -z "${DISPLAY:-}" ]]; then
    echo "Error: DISPLAY is not set."
    echo
    echo "When using SSH, connect with X11 forwarding:"
    echo "  ssh -XY <server>"
    echo
    echo "When using the server locally, run this command from its graphical session."
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
    rm -f "$SOCAT_LOG"
}

trap cleanup EXIT INT TERM


xauth -f "$XAUTH_HOST" add \
    "$GW:${PROXY_DISPLAY}.0" \
    MIT-MAGIC-COOKIE-1 \
    "$COOKIE"

chmod 644 "$XAUTH_HOST"


# Remove a stale proxy from a previous interrupted run.
pkill -f "socat.*TCP-LISTEN:${PROXY_PORT}.*bind=${GW}" \
    2>/dev/null || true


# SSH X11 forwarding normally exposes the display over TCP.
if [[ "$DISPLAY" == localhost:* || "$DISPLAY" == 127.0.0.1:* ]]; then
    SOURCE_PORT=$((6000 + DISPLAY_NUM))

    socat \
        TCP-LISTEN:"${PROXY_PORT}",bind="$GW",reuseaddr,fork \
        TCP:127.0.0.1:"${SOURCE_PORT}" \
        >"$SOCAT_LOG" 2>&1 &

    DISPLAY_SOURCE="127.0.0.1:${SOURCE_PORT}"

# A local graphical session normally exposes an X11 Unix socket.
elif [[ -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ]]; then
    socat \
        TCP-LISTEN:"${PROXY_PORT}",bind="$GW",reuseaddr,fork \
        UNIX-CONNECT:"/tmp/.X11-unix/X${DISPLAY_NUM}" \
        >"$SOCAT_LOG" 2>&1 &

    DISPLAY_SOURCE="/tmp/.X11-unix/X${DISPLAY_NUM}"

else
    echo "Error: unable to determine how to reach DISPLAY=$DISPLAY."
    echo "Expected either an SSH forwarded display or a local X11 socket."
    exit 1
fi


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


echo "Host DISPLAY:      $DISPLAY"
echo "Display source:    $DISPLAY_SOURCE"
echo "Docker network:    $NETWORK"
echo "Docker gateway:    $GW"
echo "Container DISPLAY: ${GW}:${PROXY_DISPLAY}.0"


docker compose exec \
    -e DISPLAY="${GW}:${PROXY_DISPLAY}.0" \
    -e XAUTHORITY=/tmp/.cowodlaval-xauth \
    -e XDG_CACHE_HOME=/tmp/.cache \
    web \
    sh -lc '
        mkdir -p /tmp/.cache/fontconfig
        python manage.py bookings_dashboard --gui
    '
