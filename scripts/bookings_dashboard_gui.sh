#!/bin/sh
set -eu

SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
PROJECT_DIR=$(dirname "$SCRIPT_DIR")

show_error() {
    message=$1
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Cowo d'la val" --text="$message"
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --title "Cowo d'la val" --error "$message"
    elif command -v xmessage >/dev/null 2>&1; then
        xmessage -center "$message"
    else
        printf '%s\n' "$message" >&2
    fi
}

install_launcher() {
    bin_dir=${COWO_BIN_DIR:-"$HOME/.local/bin"}
    applications_dir=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
    bin_link="$bin_dir/cowodlaval-bookings"
    desktop_file="$applications_dir/cowodlaval-bookings.desktop"

    mkdir -p "$bin_dir" "$applications_dir"
    if [ -e "$bin_link" ] && [ ! -L "$bin_link" ]; then
        printf 'Cannot replace existing file: %s\n' "$bin_link" >&2
        exit 1
    fi
    ln -sfn "$SCRIPT_PATH" "$bin_link"

    cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Cowo d'la val - Bookings
Name[it]=Cowo d'la val - Prenotazioni
Comment=Manage coworking bookings and payments
Comment[it]=Gestisci prenotazioni e pagamenti del coworking
Exec="$bin_link"
TryExec=$bin_link
Icon=$PROJECT_DIR/static/img/project-logo.png
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF
    chmod +x "$desktop_file"

    if [ -n "${COWO_DESKTOP_DIR:-}" ]; then
        desktop_dir=$COWO_DESKTOP_DIR
        mkdir -p "$desktop_dir"
    elif command -v xdg-user-dir >/dev/null 2>&1; then
        desktop_dir=$(xdg-user-dir DESKTOP)
    else
        desktop_dir="$HOME/Desktop"
    fi

    if [ -d "$desktop_dir" ] && [ "$desktop_dir" != "$HOME" ]; then
        desktop_link="$desktop_dir/Cowo d'la val - Prenotazioni.desktop"
        if [ -e "$desktop_link" ] && [ ! -L "$desktop_link" ]; then
            printf 'Desktop file already exists; application-menu entry was still installed: %s\n' "$desktop_link" >&2
        else
            ln -sfn "$desktop_file" "$desktop_link"
            command -v gio >/dev/null 2>&1 && gio set "$desktop_link" metadata::trusted true >/dev/null 2>&1 || true
        fi
    fi

    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$applications_dir" >/dev/null 2>&1 || true
    printf 'Dashboard launcher installed. Open "Cowo d'\''la val - Prenotazioni" from the application menu or desktop.\n'
}

if [ "${1:-}" = "--install" ]; then
    install_launcher
    exit 0
fi

if [ "$#" -ne 0 ]; then
    printf 'Usage: %s [--install]\n' "$0" >&2
    exit 2
fi

if [ -n "${COWO_PYTHON:-}" ]; then
    python_bin=$COWO_PYTHON
elif [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    python_bin="$PROJECT_DIR/.venv/bin/python"
elif [ -x "$PROJECT_DIR/venv/bin/python" ]; then
    python_bin="$PROJECT_DIR/venv/bin/python"
else
    python_bin=$(command -v python3 || true)
fi

if [ -z "$python_bin" ] || [ ! -x "$python_bin" ]; then
    show_error "Python non è disponibile. Crea .venv oppure imposta COWO_PYTHON."
    exit 1
fi

state_dir=${XDG_STATE_HOME:-"$HOME/.local/state"}/cowodlaval
log_file="$state_dir/bookings-dashboard.log"
mkdir -p "$state_dir"
: > "$log_file"

if ! (cd "$PROJECT_DIR" && "$python_bin" manage.py bookings_dashboard --gui) >> "$log_file" 2>&1; then
    show_error "Impossibile avviare la dashboard. Dettagli: $log_file"
    exit 1
fi
