#!/bin/sh
# Avvia KogitechHub dalla cartella del progetto (senza pip).
#
# Prima di avviare installa, in modo idempotente, la voce nelle applicazioni
# (ricerca con il tasto Super / menu Start) usando l'icona del progetto:
#   ~/.local/share/applications/kogitechhub.desktop
#   ~/.local/share/icons/hicolor/scalable/apps/kogitechhub.svg
# Se sposti la cartella del progetto, riesegui questo script per aggiornare
# il percorso memorizzato nella voce.

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APPDIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONDIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
DESKTOP="$APPDIR/kogitechhub.desktop"
ICON_SRC="$DIR/data/kogitechhub.svg"

mkdir -p "$APPDIR" "$ICONDIR/scalable/apps" "$ICONDIR/256x256/apps"

# --- voce nelle applicazioni ------------------------------------------------
# Icon=<percorso assoluto>: funziona su Plasma, GNOME, KDE, XFCE... senza
# dipendere dalla cache del tema; l'SVG è quello mostrato nella finestra.
TMP="$DESKTOP.new"
cat > "$TMP" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=KogitechHub
GenericName=Configuratore mouse
Comment=Configura DPI, preset e frequenza di report del mouse
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

# --- avvio ------------------------------------------------------------------
cd "$DIR" && PYTHONPATH=src exec python3 -m kogitechhub "$@"
