#!/bin/sh

set -eu

ACTION="${1:-}"

HOST_HOME="${COWODLAVAL_HOST_HOME:-/host-home}"
HOST_HOME_PATH="${COWODLAVAL_HOST_HOME_PATH:-}"
HOST_PROJECT_DIR="${COWODLAVAL_HOST_PROJECT_DIR:-}"

APP_NAME="Cowo d'la val - Prenotazioni"

DESKTOP_FILE_NAME="cowodlaval-bookings.desktop"
COMMAND_NAME="cowodlaval-bookings"

LOCAL_DIR="$HOST_HOME/.local"
BIN_DIR="$LOCAL_DIR/bin"
APPLICATIONS_DIR="$LOCAL_DIR/share/applications"

COMMAND_PATH="$BIN_DIR/$COMMAND_NAME"
APPLICATION_PATH="$APPLICATIONS_DIR/$DESKTOP_FILE_NAME"


if [ -z "$HOST_HOME_PATH" ] || [ -z "$HOST_PROJECT_DIR" ]; then
    echo "Missing host path configuration." >&2
    exit 1
fi


if [ ! -d "$HOST_HOME" ]; then
    echo "Host home directory not mounted: $HOST_HOME" >&2
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
            printf '%s/%s\n' \
                "$HOST_HOME" \
                "${desktop_value#\$HOME/}"
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
    rm -f \
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


install_integration() {
    echo "Installing Cowo d'la val host integration..."

    remove_legacy_files

    mkdir -p \
        "$BIN_DIR" \
        "$APPLICATIONS_DIR"

    # --------------------------------------------------------
    # CLI / GUI host command
    # --------------------------------------------------------

    rm -f "$COMMAND_PATH"

    ln -s \
        "$HOST_PROJECT_DIR/scripts/bookings_dashboard.sh" \
        "$COMMAND_PATH"

    chown -h "$OWNER" "$COMMAND_PATH" 2>/dev/null || true

    # --------------------------------------------------------
    # Application menu entry
    # --------------------------------------------------------

    cat > "$APPLICATION_PATH" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Open the Cowo d'la val bookings manager
Exec=$HOST_HOME_PATH/.local/bin/$COMMAND_NAME --gui
Icon=utilities-system-monitor
Terminal=false
Categories=Office;Utility;
StartupNotify=true
DESKTOP

    chmod 755 "$APPLICATION_PATH"
    chown "$OWNER" "$APPLICATION_PATH"

    # --------------------------------------------------------
    # Desktop shortcut, if a desktop directory exists
    # --------------------------------------------------------

    desktop_dir="$(find_desktop_dir || true)"

    if [ -n "$desktop_dir" ] && [ -d "$desktop_dir" ]; then
        desktop_path="$desktop_dir/$DESKTOP_FILE_NAME"

        rm -f "$desktop_path"

        ln -s \
            "$HOST_HOME_PATH/.local/share/applications/$DESKTOP_FILE_NAME" \
            "$desktop_path"

        chown -h "$OWNER" "$desktop_path" 2>/dev/null || true

        echo "Desktop shortcut installed."
    fi

    echo "Host command installed:"
    echo "  $HOST_HOME_PATH/.local/bin/$COMMAND_NAME"

    echo "Application menu entry installed:"
    echo "  $HOST_HOME_PATH/.local/share/applications/$DESKTOP_FILE_NAME"
}


uninstall_integration() {
    echo "Removing Cowo d'la val host integration..."

    desktop_dir="$(find_desktop_dir || true)"

    rm -f \
        "$COMMAND_PATH" \
        "$APPLICATION_PATH"

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

    echo "Cowo d'la val host integration removed."
}


case "$ACTION" in
    install)
        install_integration
        ;;

    uninstall)
        uninstall_integration
        ;;

    *)
        echo "Usage: $0 {install|uninstall}" >&2
        exit 1
        ;;
esac
