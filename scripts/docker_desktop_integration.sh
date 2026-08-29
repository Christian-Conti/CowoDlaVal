#!/bin/sh

set -eu

ACTION="${1:-}"

HOST_HOME="${COWODLAVAL_HOST_HOME:-/host-home}"
HOST_HOME_PATH="${COWODLAVAL_HOST_HOME_PATH:-}"
HOST_PROJECT_DIR="${COWODLAVAL_HOST_PROJECT_DIR:-}"

APP_DIR="$HOST_HOME/.local/share/applications"
BIN_DIR="$HOST_HOME/.local/bin"

BOOKINGS_CMD="$BIN_DIR/cowodlaval-bookings"
EVENTS_CMD="$BIN_DIR/cowodlaval-events"

BOOKINGS_DESKTOP="$APP_DIR/cowodlaval-bookings.desktop"
EVENTS_DESKTOP="$APP_DIR/cowodlaval-events.desktop"

OWNER="$(stat -c '%u:%g' "$HOST_HOME")"


find_desktop_dir() {
    config_file="$HOST_HOME/.config/user-dirs.dirs"

    if [ -f "$config_file" ]; then
        value="$(
            sed -n 's/^XDG_DESKTOP_DIR="\([^"]*\)"/\1/p' "$config_file" \
                | head -n 1
        )"

        case "$value" in
            '$HOME'/*)
                candidate="$HOST_HOME/${value#\$HOME/}"

                if [ -d "$candidate" ]; then
                    printf '%s\n' "$candidate"
                    return
                fi
                ;;
        esac
    fi

    if [ -d "$HOST_HOME/Desktop" ]; then
        printf '%s\n' "$HOST_HOME/Desktop"
        return
    fi

    if [ -d "$HOST_HOME/Scrivania" ]; then
        printf '%s\n' "$HOST_HOME/Scrivania"
        return
    fi
}


install_path() {
    file="$1"

    touch "$file"

    if ! grep -Fq '# >>> cowodlaval local bin >>>' "$file" 2>/dev/null; then
        cat >> "$file" <<'PATH_EOF'

# >>> cowodlaval local bin >>>
export PATH="$HOME/.local/bin:$PATH"
# <<< cowodlaval local bin <<<
PATH_EOF
    fi

    chown "$OWNER" "$file" 2>/dev/null || true
}


remove_path() {
    file="$1"

    [ -f "$file" ] || return 0

    tmp="${file}.cowodlaval.$$"

    awk '
        $0 == "# >>> cowodlaval local bin >>>" {
            skip=1
            next
        }

        $0 == "# <<< cowodlaval local bin <<<" {
            skip=0
            next
        }

        !skip {
            print
        }
    ' "$file" > "$tmp"

    cat "$tmp" > "$file"
    rm -f "$tmp"
}


install_bookings_command() {
    cat > "$BOOKINGS_CMD" <<EOF_BOOKINGS
#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$HOST_PROJECT_DIR"
cd "\$PROJECT_DIR"

case "\${1:---gui}" in
    --gui)
        exec "\$PROJECT_DIR/scripts/bookings_dashboard_gui.sh"
        ;;

    --cli)
        exec docker compose exec web \
            python manage.py bookings_cli
        ;;

    --help|-h)
        echo "Usage:"
        echo "  cowodlaval-bookings"
        echo "  cowodlaval-bookings --gui"
        echo "  cowodlaval-bookings --cli"
        ;;

    *)
        echo "Unknown option: \$1" >&2
        exit 2
        ;;
esac
EOF_BOOKINGS

    chmod 755 "$BOOKINGS_CMD"
    chown "$OWNER" "$BOOKINGS_CMD"
}


install_events_command() {
    cat > "$EVENTS_CMD" <<EOF_EVENTS
#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$HOST_PROJECT_DIR"
cd "\$PROJECT_DIR"


get_base_url() {
    local value=""

    if [[ -f "\$PROJECT_DIR/.env" ]]; then
        value="\$(
            sed -n 's/^PUBLIC_BASE_URL=//p' "\$PROJECT_DIR/.env" \
                | tail -n 1 \
                | tr -d '\r'
        )"
    fi

    if [[ -z "\$value" ]]; then
        value="http://127.0.0.1:8000"
    fi

    printf '%s\n' "\${value%/}"
}


open_gui() {
    if [[ -x "\$PROJECT_DIR/scripts/events_dashboard_gui.sh" ]]; then
        exec "\$PROJECT_DIR/scripts/events_dashboard_gui.sh"
    fi

    if command -v xdg-open >/dev/null 2>&1; then
        exec xdg-open "\$(get_base_url)/events/"
    fi

    echo "Unable to open Events GUI." >&2
    exit 1
}


open_cli() {
    if docker compose exec -T web \
        python manage.py help events_cli \
        >/dev/null 2>&1
    then
        exec docker compose exec web \
            python manage.py events_cli
    fi

    echo "No events_dashboard management command is available."
    echo "Opening the Events web interface instead."

    open_gui
}


case "\${1:---gui}" in
    --gui)
        open_gui
        ;;

    --cli)
        open_cli
        ;;

    --help|-h)
        echo "Usage:"
        echo "  cowodlaval-events"
        echo "  cowodlaval-events --gui"
        echo "  cowodlaval-events --cli"
        ;;

    *)
        echo "Unknown option: \$1" >&2
        exit 2
        ;;
esac
EOF_EVENTS

    chmod 755 "$EVENTS_CMD"
    chown "$OWNER" "$EVENTS_CMD"
}


install_menu_entries() {
    cat > "$BOOKINGS_DESKTOP" <<EOF_BOOKINGS_DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Cowo d'la val - Prenotazioni
Comment=Gestisci le prenotazioni di Cowo d'la val
Exec=$HOST_HOME_PATH/.local/bin/cowodlaval-bookings --gui
Icon=x-office-calendar
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF_BOOKINGS_DESKTOP

    cat > "$EVENTS_DESKTOP" <<EOF_EVENTS_DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Cowo d'la val - Eventi
Comment=Gestisci gli eventi di Cowo d'la val
Exec=$HOST_HOME_PATH/.local/bin/cowodlaval-events --gui
Icon=x-office-calendar
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF_EVENTS_DESKTOP

    chmod 755 \
        "$BOOKINGS_DESKTOP" \
        "$EVENTS_DESKTOP"

    chown "$OWNER" \
        "$BOOKINGS_DESKTOP" \
        "$EVENTS_DESKTOP"
}


install_desktop_entries() {
    desktop_dir="$(find_desktop_dir || true)"

    if [ -z "$desktop_dir" ]; then
        echo "Desktop directory not present; shortcuts skipped."
        return
    fi

    rm -f \
        "$desktop_dir/cowodlaval-bookings.desktop" \
        "$desktop_dir/cowodlaval-events.desktop"

    ln -s \
        "$HOST_HOME_PATH/.local/share/applications/cowodlaval-bookings.desktop" \
        "$desktop_dir/cowodlaval-bookings.desktop"

    ln -s \
        "$HOST_HOME_PATH/.local/share/applications/cowodlaval-events.desktop" \
        "$desktop_dir/cowodlaval-events.desktop"

    chown -h "$OWNER" \
        "$desktop_dir/cowodlaval-bookings.desktop" \
        "$desktop_dir/cowodlaval-events.desktop" \
        2>/dev/null || true

    echo "Desktop shortcuts installed."
}


remove_legacy() {
    rm -f \
        "$BIN_DIR/cowodlaval-db-controller" \
        "$APP_DIR/cowodlaval-db-controller.desktop" \
        "$APP_DIR/cowodlaval-bookings-gui.desktop"

    desktop_dir="$(find_desktop_dir || true)"

    if [ -n "$desktop_dir" ]; then
        rm -f \
            "$desktop_dir/cowodlaval-db-controller.desktop" \
            "$desktop_dir/cowodlaval-bookings-gui.desktop"
    fi
}


install_all() {
    if [ -z "$HOST_HOME_PATH" ]; then
        echo "COWODLAVAL_HOST_HOME_PATH is not set." >&2
        exit 1
    fi

    if [ -z "$HOST_PROJECT_DIR" ]; then
        echo "COWODLAVAL_HOST_PROJECT_DIR is not set." >&2
        exit 1
    fi

    echo "Installing Cowo d'la val host integration..."

    mkdir -p \
        "$BIN_DIR" \
        "$APP_DIR"

    chown -R "$OWNER" "$HOST_HOME/.local"

    remove_legacy

    install_bookings_command
    install_events_command
    install_menu_entries
    install_desktop_entries

    install_path "$HOST_HOME/.zshrc"
    install_path "$HOST_HOME/.profile"

    echo
    echo "Installed commands:"
    echo "  $HOST_HOME_PATH/.local/bin/cowodlaval-bookings"
    echo "  $HOST_HOME_PATH/.local/bin/cowodlaval-events"
    echo
    echo "Installed menu entries:"
    echo "  $HOST_HOME_PATH/.local/share/applications/cowodlaval-bookings.desktop"
    echo "  $HOST_HOME_PATH/.local/share/applications/cowodlaval-events.desktop"
}


uninstall_all() {
    echo "Removing Cowo d'la val host integration..."

    desktop_dir="$(find_desktop_dir || true)"

    rm -f \
        "$BOOKINGS_CMD" \
        "$EVENTS_CMD" \
        "$BOOKINGS_DESKTOP" \
        "$EVENTS_DESKTOP"

    if [ -n "$desktop_dir" ]; then
        rm -f \
            "$desktop_dir/cowodlaval-bookings.desktop" \
            "$desktop_dir/cowodlaval-events.desktop"
    fi

    remove_legacy

    remove_path "$HOST_HOME/.zshrc"
    remove_path "$HOST_HOME/.profile"

    echo "Cowo d'la val host integration removed."
}


case "$ACTION" in
    install)
        install_all
        ;;

    uninstall)
        uninstall_all
        ;;

    *)
        echo "Usage: $0 {install|uninstall}" >&2
        exit 2
        ;;
esac
