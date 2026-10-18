#!/bin/sh
# Avvia KogitechHub dalla cartella del progetto (senza installazione).
#
# Prima di avviare:
#  - installa la voce nelle applicazioni (ricerca con il tasto Super / menu
#    Start) con l'icona del progetto, in modo idempotente;
#  - controlla le dipendenze (Python 3, PySide6/Qt 6, PyGObject, ratbagd) e,
#    se ne manca qualcuna, propone di installarla chiedendo Y/N con il gestore
#    di pacchetti di questa distro. Se PySide6 non è nei repository viene
#    installato in una cartella locale (.venv) con pip.
#
# Uso:
#   ./run.sh                 avvia l'app (installa ciò che manca, chiedendo)
#   ./run.sh --mock          avvia con mouse simulati (nessun hardware)
#   ./run.sh --check         verifica l'ambiente e le dipendenze, poi esce
#   ./run.sh --install-deps  installa solo le dipendenze, poi esce
#   ./run.sh --yes           risponde sì a tutte le domande
#   ./run.sh --no-install    non installa nulla, spiega solo cosa manca

set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APPDIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONDIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
DESKTOP="$APPDIR/kogitechhub.desktop"
ICON_SRC="$DIR/data/kogitechhub.svg"
PYTHON=${KOGITECHHUB_PYTHON:-python3}

# --- Python 3: unica dipendenza che run.sh deve installare da solo ----------
# (tutto il resto è gestito da kogitechhub.installer, che non ha bisogno di Qt)
install_python3() {
    if command -v apt-get >/dev/null 2>&1; then
        cmd="sudo apt-get install -y python3 python3-pip python3-venv"
    elif command -v dnf >/dev/null 2>&1; then
        cmd="sudo dnf install -y python3 python3-pip"
    elif command -v pacman >/dev/null 2>&1; then
        cmd="sudo pacman -S --needed --noconfirm python python-pip"
    elif command -v zypper >/dev/null 2>&1; then
        cmd="sudo zypper install -y python3 python3-pip"
    elif command -v apk >/dev/null 2>&1; then
        cmd="sudo apk add python3 py3-pip"
    elif command -v xbps-install >/dev/null 2>&1; then
        cmd="sudo xbps-install -Sy python3 python3-pip"
    elif command -v emerge >/dev/null 2>&1; then
        cmd="sudo emerge dev-lang/python"
    else
        echo "Gestore di pacchetti non riconosciuto: installa python3 a mano." >&2
        return 1
    fi

    printf 'Installare Python 3 adesso? [Y/n] ' >&2
    answer=""
    read -r answer || answer=""
    case "$answer" in
        n|N|no|NO) echo "  nessuna installazione: esco." >&2; return 1 ;;
    esac
    echo "  \$ $cmd" >&2
    sh -c "$cmd" || { echo "  installazione di Python 3 non riuscita." >&2; return 1; }
}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "Python 3 non è installato (o non è nel PATH): KogitechHub ne ha bisogno." >&2
    if [ -t 0 ]; then
        install_python3 || exit 1
    else
        echo "Esegui ./run.sh da un terminale per installarlo." >&2
        exit 1
    fi
    if ! command -v "$PYTHON" >/dev/null 2>&1; then
        echo "Python 3 continua a mancare: installalo e riprova." >&2
        exit 1
    fi
fi

# --- voce nelle applicazioni ------------------------------------------------
# Icon=<percorso assoluto>: funziona su Plasma, GNOME, KDE, XFCE... senza
# dipendere dalla cache del tema; l'SVG è quello mostrato nella finestra.
mkdir -p "$APPDIR" "$ICONDIR/scalable/apps" "$ICONDIR/256x256/apps"
TMP="$DESKTOP.new"
cat > "$TMP" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=KogitechHub
GenericName=Configuratore dispositivi
Comment=Configura mouse, illuminazione RGB di tastiere e cuffie, controlli delle cuffie
Exec=$DIR/run.sh %U
TryExec=$DIR/run.sh
Icon=$ICON_SRC
Categories=Settings;HardwareSettings;
Keywords=DPI;mouse;RAT;Logitech;gaming;preset;report rate;
Terminal=false
StartupNotify=true
StartupWMClass=kogitechhub
EOF

if [ ! -f "$DESKTOP" ] || ! cmp -s "$TMP" "$DESKTOP"; then
    mv "$TMP" "$DESKTOP"
    chmod 644 "$DESKTOP"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPDIR" >/dev/null 2>&1
fi
rm -f "$TMP"

# --- icona anche nel tema hicolor (per chi cerca l'app per nome) ------------
ICONS_CHANGED=0
for pair in "scalable/apps/kogitechhub.svg:$ICON_SRC" \
            "256x256/apps/kogitechhub.png:$DIR/data/kogitechhub.png"; do
    dest="${pair%%:*}"; src="${pair#*:}"
    [ -f "$src" ] || continue
    if [ ! -f "$ICONDIR/$dest" ] || ! cmp -s "$src" "$ICONDIR/$dest"; then
        cp "$src" "$ICONDIR/$dest"
        chmod 644 "$ICONDIR/$dest"
        ICONS_CHANGED=1
    fi
done
if [ "$ICONS_CHANGED" = 1 ]; then
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -f -t "$ICONDIR" >/dev/null 2>&1
fi

# --- dipendenze + avvio -----------------------------------------------------
# kogitechhub.cli controlla PySide6/PyGObject/ratbagd e, se mancano, chiede
# Y/N prima di installarle; poi passa la mano all'interfaccia.
cd "$DIR" || exit 1
PYTHONPATH="$DIR/src${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m kogitechhub "$@"
