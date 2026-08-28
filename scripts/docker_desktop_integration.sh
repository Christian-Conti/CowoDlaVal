#!/bin/sh

set -eu

ACTION="${1:-}"

HOST_HOME="${COWODLAVAL_HOST_HOME:-/host-home}"
HOST_HOME_PATH="${COWODLAVAL_HOST_HOME_PATH:-}"
HOST_PROJECT_DIR="${COWODLAVAL_HOST_PROJECT_DIR:-}"

APP_NAME="Cowo d'la val - Prenotazioni"
DESKTOP_FILE_NAME="cowodlaval-bookings.desktop"

APPLICATIONS_DIR="$HOST_HOME/.local/share/applications"
APPLICATION_PATH="$APPLICATIONS_DIR/$DESKTOP_FILE_NAME"


if [ -z "$HOST_HOME_PATH" ] || [ -z "$HOST_PROJECT_DIR" ]; then
    echo "Missing COWODLAVAL_HOST_HOME_PATH or COWODLAVAL_HOST_PROJECT_DIR." >&2
    exit 1
fi


if [ ! -d "$HOST_HOME" ]; then
    echo "Mounted host home directory not found: $HOST_HOME" >&2
    exit 1
fi


OWNER="$(stat -c '%u:%g' "$HOST_HOME")"


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
            printf '%s/%s\n' \
                "$HOST_HOME" \
                "${desktop_value#"$HOST_HOME_PATH"/}"
            return
            ;;
    esac

    if [ -d "$HOST_HOME/Desktop" ]; then
        printf '%s\n' "$HOST_HOME/Desktop"
        return
    fi

    if [ -d "$HOST_HOME/Scrivania" ]; then
        printf '%s\n' "$HOST_HOME/Scrivania"
        return
    fi
}


remove_legacy_files() {
    # Remove launchers used by previous versions.
    rm -f \
        "$HOST_HOME/.local/bin/cowodlaval-bookings" \
        "$HOST_HOME/.local/bin/cowodlaval-db-controller" \
        "$APPLICATIONS_DIR/cowodlaval-db-controller.desktop" \
        "$APPLICATIONS_DIR/cowodlaval-bookings-gui.desktop"

    for directory in \
        "$HOST_HOME/Desktop" \
        "$HOST_HOME/Scrivania" \
        "$(find_desktop_dir || true)"
    do
        if [ -n "$directory" ] && [ -d "$directory" ]; then
            rm -f \
                "$directory/cowodlaval-db-controller.desktop" \
                "$directory/cowodlaval-bookings-gui.desktop"
        fi
    done
}


install_launcher() {
    echo "Installing Cowo d'la val desktop integration..."

    remove_legacy_files

    mkdir -p "$APPLICATIONS_DIR"

    chown "$OWNER" \
        "$HOST_HOME/.local" \
        "$HOST_HOME/.local/share" \
        "$APPLICATIONS_DIR" \
        2>/dev/null || true

    cat > "$APPLICATION_PATH" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Open the Cowo d'la val bookings database controller
Exec="$HOST_PROJECT_DIR/scripts/bookings_dashboard_gui.sh"
Icon=utilities-system-monitor
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF

    chmod 755 "$APPLICATION_PATH"
    chown "$OWNER" "$APPLICATION_PATH"

    desktop_dir="$(find_desktop_dir || true)"

    if [ -n "$desktop_dir" ] && [ -d "$desktop_dir" ]; then
        desktop_path="$desktop_dir/$DESKTOP_FILE_NAME"

        rm -f "$desktop_path"

        ln -s \
            "$HOST_HOME_PATH/.local/share/applications/$DESKTOP_FILE_NAME" \
            "$desktop_path"

        chown -h "$OWNER" "$desktop_path" 2>/dev/null || true

        echo "Desktop shortcut installed:"
        echo "  ${desktop_path#"$HOST_HOME"}"
    else
        echo "Desktop directory not present; desktop shortcut skipped."
    fi

    echo "Application menu entry installed:"
    echo "  $HOST_HOME_PATH/.local/share/applications/$DESKTOP_FILE_NAME"
}


uninstall_launcher() {
    echo "Removing Cowo d'la val desktop integration..."

    desktop_dir="$(find_desktop_dir || true)"

    rm -f "$APPLICATION_PATH"

    if [ -n "$desktop_dir" ] && [ -d "$desktop_dir" ]; then
        rm -f "$desktop_dir/$DESKTOP_FILE_NAME"
    fi

    if [ -d "$HOST_HOME/Desktop" ]; then
        rm -f "$HOST_HOME/Desktop/$DESKTOP_FILE_NAME"
    fi

    if [ -d "$HOST_HOME/Scrivania" ]; then
        rm -f "$HOST_HOME/Scrivania/$DESKTOP_FILE_NAME"
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
