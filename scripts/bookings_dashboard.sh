#!/usr/bin/env bash

set -euo pipefail

# Resolve symlinks first.
# This is required when invoked as ~/.local/bin/cowodlaval-bookings.
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"

cd "$PROJECT_DIR"

MODE="menu"


usage() {
    cat <<'USAGE'
Usage:
  cowodlaval-bookings
  cowodlaval-bookings --cli
  cowodlaval-bookings --gui
  cowodlaval-bookings --auto
  cowodlaval-bookings --help

Modes:
  --cli   Terminal interface.
  --gui   Graphical interface.
          Over SSH use: ssh -XY user@server
  --auto  GUI if DISPLAY is available, otherwise CLI.

Without arguments an interactive selector is shown.
USAGE
}


check_web_container() {
    local container

    container="$(docker compose ps -q web 2>/dev/null || true)"

    if [[ -z "$container" ]]; then
        echo "Error: the CowoDlaVal web container is not running." >&2
        echo >&2
        echo "Start it with:" >&2
        echo "  cd \"$PROJECT_DIR\"" >&2
        echo "  docker compose up -d" >&2
        exit 1
    fi

    if [[ "$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null)" != "true" ]]; then
        echo "Error: the CowoDlaVal web container is not running." >&2
        exit 1
    fi
}


run_cli() {
    check_web_container

    exec docker compose exec web \
        python manage.py bookings_dashboard \
        --cli \
        "$@"
}


run_gui() {
    check_web_container

    if [[ -z "${DISPLAY:-}" ]]; then
        echo "Error: DISPLAY is not set." >&2
        echo >&2
        echo "Reconnect with X11 forwarding:" >&2
        echo "  ssh -XY user@server" >&2
        echo >&2
        echo "Or use:" >&2
        echo "  cowodlaval-bookings --cli" >&2
        exit 1
    fi

    if [[ ! -x "$PROJECT_DIR/scripts/bookings_dashboard_gui.sh" ]]; then
        echo "Error: GUI launcher not found." >&2
        exit 1
    fi

    exec "$PROJECT_DIR/scripts/bookings_dashboard_gui.sh"
}


select_mode() {
    echo
    echo "Cowo d'la val - Prenotazioni"
    echo "============================"
    echo
    echo "  1) CLI - Terminal interface"

    if [[ -n "${DISPLAY:-}" ]]; then
        echo "  2) GUI - Graphical interface"
    else
        echo "  2) GUI - Graphical interface [X11 unavailable]"
    fi

    echo
    echo "  q) Exit"
    echo

    while true; do
        read -r -p "Select mode [1/2/q]: " choice

        case "$choice" in
            1)
                MODE="cli"
                return
                ;;

            2)
                MODE="gui"
                return
                ;;

            q|Q)
                exit 0
                ;;

            *)
                echo "Invalid selection."
                ;;
        esac
    done
}


if [[ $# -gt 0 ]]; then
    case "$1" in
        --cli)
            MODE="cli"
            shift
            ;;

        --gui)
            MODE="gui"
            shift
            ;;

        --auto)
            MODE="auto"
            shift
            ;;

        -h|--help)
            usage
            exit 0
            ;;

        *)
            MODE="cli"
            ;;
    esac
fi


if [[ "$MODE" == "auto" ]]; then
    if [[ -n "${DISPLAY:-}" ]]; then
        MODE="gui"
    else
        MODE="cli"
    fi
fi


if [[ "$MODE" == "menu" ]]; then
    select_mode
fi


case "$MODE" in
    cli)
        run_cli "$@"
        ;;

    gui)
        run_gui "$@"
        ;;

    *)
        echo "Error: unsupported mode '$MODE'." >&2
        exit 1
        ;;
esac
