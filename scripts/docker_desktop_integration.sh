#!/bin/sh

set -eu

ACTION="${1:-}"
HOST_HOME="${COWODLAVAL_HOST_HOME:-/host-home}"
HOST_HOME_PATH="${COWODLAVAL_HOST_HOME_PATH:-}"
HOST_PROJECT_DIR="${COWODLAVAL_HOST_PROJECT_DIR:-}"

APP_NAME="Cowo d'la val - Prenotazioni"
DESKTOP_FILE_NAME="cowodlaval-bookings.desktop"
LAUNCHER_NAME="cowodlaval-bookings"

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
APPLICATION_PATH="$APPLICATIONS_DIR/$DESKTOP_FILE_NAME"
LAUNCHER_PATH="$BIN_DIR/$LAUNCHER_NAME"

find_desktop_dir() {
    config_file="$HOST_HOME/.config/user-dirs.dirs"
    desktop_value=""

    if [ -f "$config_file" ]; then
        desktop_value="$(
            grep '^XDG_DESKTOP_DIR=' "$config_file" 2>/dev/null \
                | head -n 1 \
                | cut -d= -f2-
        )"
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
    fi
}

remove_legacy_files() {
    rm -f \
        "$BIN_DIR/cowodlaval-db-controller" \
        "$APPLICATIONS_DIR/cowodlaval-db-controller.desktop" \
        "$APPLICATIONS_DIR/cowodlaval-bookings-gui.desktop"

    for directory in "$HOST_HOME/Desktop" "$(find_desktop_dir || true)"; do
        if [ -n "$directory" ] && [ -d "$directory" ]; then
            rm -f \
                "$directory/cowodlaval-db-controller.desktop" \
                "$directory/cowodlaval-bookings-gui.desktop"
        fi
    done
}

install_launcher() {
    remove_legacy_files

    mkdir -p "$APPLICATIONS_DIR" "$BIN_DIR"
    chown "$OWNER" "$HOST_HOME/.local" "$HOST_HOME/.local/share" "$APPLICATIONS_DIR" "$BIN_DIR" 2>/dev/null || true

    cat > "$LAUNCHER_PATH" <<EOF_LAUNCHER
#!/usr/bin/env bash
exec "$HOST_PROJECT_DIR/scripts/bookings_dashboard_gui.sh" "\$@"
EOF_LAUNCHER

    chmod 755 "$LAUNCHER_PATH"
    chown "$OWNER" "$LAUNCHER_PATH"

    cat > "$APPLICATION_PATH" <<EOF_DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Open the Cowo d'la val bookings database controller
Exec="$HOST_HOME_PATH/.local/bin/$LAUNCHER_NAME"
Icon=utilities-system-monitor
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF_DESKTOP

    chmod 755 "$APPLICATION_PATH"
    chown "$OWNER" "$APPLICATION_PATH"

    desktop_dir="$(find_desktop_dir || true)"

    if [ -n "$desktop_dir" ] && [ -d "$desktop_dir" ]; then
        desktop_path="$desktop_dir/$DESKTOP_FILE_NAME"
        host_desktop_target="$HOST_HOME_PATH/${desktop_dir#"$HOST_HOME"/}/$DESKTOP_FILE_NAME"

        rm -f "$desktop_path"
        ln -s "$HOST_HOME_PATH/.local/share/applications/$DESKTOP_FILE_NAME" "$desktop_path"
        chown -h "$OWNER" "$desktop_path" 2>/dev/null || true

        echo "Desktop shortcut installed: $host_desktop_target"
    else
        echo "Desktop directory not present; desktop shortcut skipped."
    fi

    echo "Application launcher installed: $HOST_HOME_PATH/.local/share/applications/$DESKTOP_FILE_NAME"
}

uninstall_launcher() {
    desktop_dir="$(find_desktop_dir || true)"

    rm -f "$APPLICATION_PATH" "$LAUNCHER_PATH"

    if [ -n "$desktop_dir" ] && [ -d "$desktop_dir" ]; then
        rm -f "$desktop_dir/$DESKTOP_FILE_NAME"
    fi

    if [ -d "$HOST_HOME/Desktop" ]; then
        rm -f "$HOST_HOME/Desktop/$DESKTOP_FILE_NAME"
    fi

    remove_legacy_files

    echo "Cowo d'la val desktop integration removed."
}

case "$ACTION" in
    install)
        install_launcher
        ;;
    uninstall)
        uninstall_launcher
        ;;
    *)
        echo "Usage: $0 {install|uninstall}" >&2
        exit 1
        ;;
esac
