#!/bin/sh

set -eu

ACTION="${1:-}"
HOST_HOME="${COWODLAVAL_HOST_HOME:-/host-home}"
HOST_HOME_PATH="${COWODLAVAL_HOST_HOME_PATH:-}"
HOST_PROJECT_DIR="${COWODLAVAL_HOST_PROJECT_DIR:-}"

if [ -z "$HOST_HOME_PATH" ] || [ -z "$HOST_PROJECT_DIR" ]; then
    echo "Missing COWODLAVAL_HOST_HOME_PATH or COWODLAVAL_HOST_PROJECT_DIR." >&2
    exit 1
fi

if [ ! -d "$HOST_HOME" ]; then
    echo "Mounted host home directory not found: $HOST_HOME" >&2
    exit 1
fi

OWNER="$(stat -c '%u:%g' "$HOST_HOME")"
APPLICATIONS_DIR="$HOST_HOME/.local/share/applications"
BIN_DIR="$HOST_HOME/.local/bin"

find_desktop_dir() {
    config_file="$HOST_HOME/.config/user-dirs.dirs"
    desktop_value=""

    if [ -f "$config_file" ]; then
        desktop_value="$(grep '^XDG_DESKTOP_DIR=' "$config_file" 2>/dev/null | head -n 1 | cut -d= -f2-)"
        desktop_value="${desktop_value#\"}"
        desktop_value="${desktop_value%\"}"
    fi

    case "$desktop_value" in
        '$HOME'/*)
            printf '%s/%s\n' "$HOST_HOME" "${desktop_value#\$HOME/}"
            return
            ;;
        "$HOST_HOME_PATH"/*)
            printf '%s/%s\n' "$HOST_HOME" "${desktop_value#"$HOST_HOME_PATH"/}"
            return
            ;;
    esac

    if [ -d "$HOST_HOME/Desktop" ]; then
        printf '%s\n' "$HOST_HOME/Desktop"
        return
    fi

    if [ -d "$HOST_HOME/Scrivania" ]; then
        printf '%s\n' "$HOST_HOME/Scrivania"
    fi
}

install_one() {
    launcher_name="$1"
    desktop_name="$2"
    app_name="$3"
    comment="$4"
    script_name="$5"
    icon="$6"

    launcher_path="$BIN_DIR/$launcher_name"
    application_path="$APPLICATIONS_DIR/$desktop_name"

    cat > "$launcher_path" <<EOF_LAUNCHER
#!/usr/bin/env bash
exec "$HOST_PROJECT_DIR/scripts/$script_name" "\$@"
EOF_LAUNCHER

    chmod 755 "$launcher_path"
    chown "$OWNER" "$launcher_path"

    cat > "$application_path" <<EOF_DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=$app_name
Comment=$comment
Exec="$HOST_HOME_PATH/.local/bin/$launcher_name"
Icon=$icon
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF_DESKTOP

    chmod 755 "$application_path"
    chown "$OWNER" "$application_path"

    desktop_dir="$(find_desktop_dir || true)"
    if [ -n "$desktop_dir" ] && [ -d "$desktop_dir" ]; then
        desktop_path="$desktop_dir/$desktop_name"
        rm -f "$desktop_path"
        ln -s "$HOST_HOME_PATH/.local/share/applications/$desktop_name" "$desktop_path"
        chown -h "$OWNER" "$desktop_path" 2>/dev/null || true
    fi
}

remove_one() {
    launcher_name="$1"
    desktop_name="$2"

    rm -f "$BIN_DIR/$launcher_name" "$APPLICATIONS_DIR/$desktop_name"

    for directory in "$HOST_HOME/Desktop" "$HOST_HOME/Scrivania" "$(find_desktop_dir || true)"; do
        if [ -n "$directory" ] && [ -d "$directory" ]; then
            rm -f "$directory/$desktop_name"
        fi
    done
}

install_launchers() {
    mkdir -p "$APPLICATIONS_DIR" "$BIN_DIR"
    chown "$OWNER" "$HOST_HOME/.local" "$HOST_HOME/.local/share" "$APPLICATIONS_DIR" "$BIN_DIR" 2>/dev/null || true

    rm -f \
        "$BIN_DIR/cowodlaval-db-controller" \
        "$APPLICATIONS_DIR/cowodlaval-db-controller.desktop" \
        "$APPLICATIONS_DIR/cowodlaval-bookings-gui.desktop"

    install_one \
        "cowodlaval-bookings" \
        "cowodlaval-bookings.desktop" \
        "Cowo d'la val - Prenotazioni" \
        "Gestisci le prenotazioni Cowo d'la val" \
        "bookings_dashboard_gui.sh" \
        "utilities-system-monitor"

    install_one \
        "cowodlaval-events" \
        "cowodlaval-events.desktop" \
        "Cowo d'la val - Eventi" \
        "Gestisci gli eventi Cowo d'la val" \
        "events_dashboard_gui.sh" \
        "x-office-calendar"

    echo "Cowo d'la val booking and event launchers installed."
}

uninstall_launchers() {
    remove_one "cowodlaval-bookings" "cowodlaval-bookings.desktop"
    remove_one "cowodlaval-events" "cowodlaval-events.desktop"

    rm -f \
        "$BIN_DIR/cowodlaval-db-controller" \
        "$APPLICATIONS_DIR/cowodlaval-db-controller.desktop" \
        "$APPLICATIONS_DIR/cowodlaval-bookings-gui.desktop"

    echo "Cowo d'la val desktop integration removed."
}

case "$ACTION" in
    install)
        install_launchers
        ;;
    uninstall)
        uninstall_launchers
        ;;
    *)
        echo "Usage: $0 {install|uninstall}" >&2
        exit 1
        ;;
esac
