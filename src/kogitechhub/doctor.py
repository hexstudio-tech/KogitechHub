"""`kogitechhub --check`: dice se l'app può girare qui e cosa installare.

Non crea interfaccia grafica, quindi funziona anche su server, container e
dentro ssh: utile per capire subito perché qualcosa non parte.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from . import deps

DESKTOP_NAME = "kogitechhub.desktop"
ICON_NAME = "kogitechhub.svg"


def _ok(label: str, ok: bool, detail: str = "") -> str:
    return f"  [{'OK ' if ok else '-- '}] {label}{(': ' + detail) if detail else ''}"


def _desktop_paths() -> tuple[Path, Path]:
    base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    return base / "applications" / DESKTOP_NAME, base / "icons/hicolor/scalable/apps" / ICON_NAME


def _check_display() -> tuple[bool, str]:
    if sys.platform != "linux":
        return True, ""
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"):
        return True, "Wayland" if os.environ.get("WAYLAND_DISPLAY") else "X11"
    return False, "nessun display (DISPLAY/WAYLAND_DISPLAY non impostati)"


def report() -> tuple[str, int]:
    """Restituisce (testo, codice di uscita: 0 se l'app può girare)."""
    d = deps.detect_distro()
    lines: list[str] = []
    problems = 0

    lines.append("KogitechHub - verifica dell'ambiente")
    lines.append("")
    lines.append(f"  Distribuzione: {d.pretty} (id={d.id}, famiglia={d.family})")
    if not d.known:
        lines.append("    famiglia non riconosciuta: i comandi qui sotto sono generici")
    lines.append(f"  Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        problems += 1
        lines.append(_ok("versione Python >= 3.10", False, sys.version.split()[0]))
    else:
        lines.append(_ok("versione Python >= 3.10", True))
    lines.append("")

    # --- Qt / interfaccia --------------------------------------------------
    lines.append("Interfaccia grafica")
    try:
        import PySide6
        from PySide6.QtCore import qVersion

        lines.append(_ok("PySide6", True, f"{PySide6.__version__} (Qt {qVersion()})"))
    except Exception as exc:                                   # pragma: no cover
        problems += 1
        lines.append(_ok("PySide6", False, str(exc)))
        lines.extend(f"    {cmd}" for cmd in deps.install_hint(["pyside6"], d))
    display_ok, display_info = _check_display()
    lines.append(_ok("sessione grafica", display_ok, display_info))
    if not display_ok:
        problems += 1
        lines.append("    da terminale remoto serve inoltrare X11 o Wayland")
    lines.append("")

    # --- collegamento a ratbagd -------------------------------------------
    lines.append("Mouse (libratbag / ratbagd)")
    try:
        from .backends.ratbag import RatbagBackend

        backend = RatbagBackend()
        available, message = backend.available()
        lines.append(_ok("ratbagd raggiungibile via D-Bus", available, message))
        if not available:
            problems += 1
            lines.extend(f"    {cmd}" for cmd in deps.install_hint(["ratbagd"], d))
            lines.append("    sudo systemctl enable --now ratbagd")
        else:
            try:
                devices = backend.list()
            except Exception as exc:                            # pragma: no cover
                devices = []
                lines.append(_ok("mouse elencati", False, str(exc)))
            for dev in devices:
                kind = "configurabile" if dev.get("configurable") else "sola lettura"
                lines.append(f"    - {dev.get('name', '?')}: {kind}")
            if not devices:
                lines.append("    nessun mouse configurabile trovato")
    except Exception as exc:                                    # pragma: no cover
        problems += 1
        lines.append(_ok("backend ratbag", False, str(exc)))
        lines.extend(f"    {cmd}" for cmd in deps.install_hint(["gobject", "ratbagd"], d))
    lines.append("")

    # --- PyGObject ---------------------------------------------------------
    lines.append("Dipendenze Python")
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio  # noqa: F401

        lines.append(_ok("PyGObject (Gio)", True, f"vers {getattr(gi, '__version__', '?')}"))
    except Exception as exc:
        problems += 1
        lines.append(_ok("PyGObject (Gio)", False, str(exc)))
        lines.extend(f"    {cmd}" for cmd in deps.install_hint(["gobject"], d))
    lines.append("")

    # --- voce nel menu -----------------------------------------------------
    desktop, icon = _desktop_paths()
    lines.append("Voce nelle applicazioni")
    if desktop.exists():
        lines.append(_ok("desktop entry", True, str(desktop)))
    else:
        lines.append(_ok("desktop entry", False, f"non installata ({desktop})"))
        lines.append("    si installa automaticamente al prossimo ./run.sh")
    lines.append(_ok("icona", icon.exists(), str(icon)))
    lines.append("")

    if problems:
        lines.append(f"ESITO: {problems} problema/i da risolvere prima di avviare l'app.")
    else:
        lines.append("ESITO: tutto pronto, puoi avviare KogitechHub con ./run.sh")
    return "\n".join(lines), (1 if problems else 0)
