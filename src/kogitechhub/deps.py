"""Rilevamento della distribuzione e istruzioni per installare le dipendenze.

Serve a due cose:
- far funzionare KogitechHub su qualunque distro (non solo Fedora/Nobara),
  suggerendo il comando giusto invece di `dnf` a chiunque;
- spiegare in italiano cosa manca e come si installa, con il gestore di
  pacchetti di quella distro (`apt`, `dnf`, `pacman`, `zypper`, `apk`, ...).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OS_RELEASE = Path("/etc/os-release")

# chiave -> pacchetto per famiglia di distro
PACKAGES = {
    "pyside6": {
        "rpm": "python3-pyside6",
        "deb": "python3-pyside6",        # non in tutte le versioni: si offre anche pip
        "pacman": "python-pyside6",
        "zypper": "python3-pyside6",
        "apk": "py3-pyside6",
        "pip": "pip install --user PySide6",
    },
    "gobject": {
        "rpm": "python3-gobject",
        "deb": "python3-gi",
        "pacman": "python-gobject",
        "zypper": "python3-gobject",
        "apk": "py3-gobject",
        "pip": "pip install --user PyGObject",
    },
    "ratbagd": {
        "rpm": "libratbag-ratbagd",
        "deb": "ratbagd",
        "pacman": "ratbagd",
        "zypper": "ratbagd",
        "apk": "ratbagd",
        "pip": "pip install --user PySide6",   # non usato: ratbagd è un servizio di sistema
    },
}

# famiglie riconosciute dagli identificativi di /etc/os-release
FAMILIES = (
    (("fedora", "rhel", "centos", "nobara", "ol"), "rpm"),
    (("debian", "ubuntu", "mint", "pop", "raspbian", "kali", "neon"), "deb"),
    (("arch", "manjaro", "endeavouros", "garuda", "cachyos"), "pacman"),
    (("opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles", "suse"), "zypper"),
    (("alpine",), "apk"),
    (("gentoo",), "emerge"),
    (("void",), "xbps"),
)

COMMANDS = {
    "rpm": "sudo dnf install",
    "deb": "sudo apt install",
    "pacman": "sudo pacman -S",
    "zypper": "sudo zypper install",
    "apk": "sudo apk add",
    "emerge": "sudo emerge",
    "xbps": "sudo xbps-install -S",
}

LABELS = {
    "pyside6": "PySide6 / Qt 6 (interfaccia grafica)",
    "gobject": "PyGObject (collegamento D-Bus a ratbagd)",
    "ratbagd": "ratbagd (servizio che parla con il mouse)",
}


@dataclass(frozen=True)
class Distro:
    id: str
    pretty: str
    family: str
    package_command: str

    @property
    def known(self) -> bool:
        return self.family != "unknown"


def read_os_release(path: Path | None = None) -> dict[str, str]:
    fields: dict[str, str] = {}
    file = Path(path) if path else OS_RELEASE
    try:
        text = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return fields
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        fields[key.strip()] = value.strip().strip('"')
    return fields


def detect_distro(path: Path | None = None) -> Distro:
    fields = read_os_release(path)
    ids = {fields.get("ID", "").lower()}
    ids |= {i.lower() for i in fields.get("ID_LIKE", "").split()}
    family = "unknown"
    for keys, name in FAMILIES:
        if ids & set(keys):
            family = name
            break
    return Distro(
        id=fields.get("ID", "") or "linux",
        pretty=fields.get("PRETTY_NAME", "") or "Linux",
        family=family,
        package_command=COMMANDS.get(family, ""),
    )


def install_command(key: str, distro: Distro | None = None) -> str:
    """Comando per installare una dipendenza su questa distro ('' se ignota)."""
    d = distro or detect_distro()
    entry = PACKAGES.get(key) or {}
    if d.family in entry and d.package_command:
        return f"{d.package_command} {entry[d.family]}"
    return entry.get("pip", "")


def install_hint(keys: list[str], distro: Distro | None = None) -> list[str]:
    """Righe di istruzioni pronte da mostrare all'utente."""
    d = distro or detect_distro()
    lines: list[str] = []
    packages = []
    for key in keys:
        entry = PACKAGES.get(key) or {}
        if d.family in entry and d.package_command:
            packages.append(entry[d.family])
    if packages and d.package_command:
        lines.append(f"    {d.package_command} {' '.join(packages)}")
    for key in keys:                       # alternativa pip (PySide6 manca spesso nei repo)
        entry = PACKAGES.get(key) or {}
        pip = entry.get("pip")
        if pip and key != "ratbagd" and pip not in lines:
            lines.append(f"    oppure: {pip}")
    return lines


def ratbagd_hint(message: str = "", distro: Distro | None = None) -> str:
    """Testo mostrato nell'app quando ratbagd non è raggiungibile."""
    d = distro or detect_distro()
    install = install_command("ratbagd", d) or "installa il pacchetto ratbagd"
    first = f"KogitechHub non riesce a parlare con libratbag"
    if message:
        first += f" ({message})"
    return (f"{first}.\n"
            f"Installa e avvia il servizio:\n"
            f"    {install}\n"
            f"    sudo systemctl enable --now ratbagd")
