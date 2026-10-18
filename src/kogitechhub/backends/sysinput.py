"""Rilevamento in sola lettura delle periferiche cablate del sistema.

Legge `/proc/bus/input/devices` (USB e Bluetooth) e le porte seriali
(`/dev/ttyACM*`, `/dev/ttyUSB*`). Serve a mostrare anche i dispositivi che
libratbag/OpenRGB/HeadsetControl non conoscono: una tastiera cablata generica,
per esempio, compare comunque nella dashboard (in sola lettura, con la
spiegazione del perché l'RGB non è controllabile).

Le interfacce multiple dello stesso dispositivo (una tastiera espone spesso
"Keyboard", "Consumer Control" e "Mouse") vengono unite in una sola scheda.
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

from ..core.vendors import vendor_name
from .base import Backend, BackendError

PROC = "/proc/bus/input/devices"
SERIAL_PATTERNS = ("/dev/ttyACM*", "/dev/ttyUSB*")
BUS_NAMES = {"0003": "USB", "0005": "Bluetooth"}

SKIP = re.compile(r"virtual|touchpad|trackpad|ydotool|uinput|power button|video bus|"
                  r"pc speaker|hd-audio|hdmi|microphone|webcam|camera|audio device", re.I)
MOUSE_NAME = re.compile(r"mouse|trackball", re.I)
KEYBOARD_NAME = re.compile(r"keyboard|\bkb\b|\bkbd\b", re.I)
MOUSE_HANDLER = re.compile(r"mouse\d+")
SUFFIX = re.compile(r"\s+(Keyboard|Mouse|Consumer Control|System Control|"
                    r"Touchpad|Trackpad)$", re.I)


def _blocks(text: str):
    for block in text.strip().split("\n\n"):
        info = {}
        for line in block.splitlines():
            if line.startswith("I:"):
                for key, value in re.findall(r"(\w+)=(\w+)", line):
                    info[key.lower()] = value
            elif line.startswith("N:"):
                match = re.search(r'Name="(.*)"', line)
                info["name"] = match.group(1) if match else ""
            elif line.startswith("H:"):
                info["handlers"] = line.split("=", 1)[1].split()
            elif line.startswith("S:"):
                match = re.search(r"Sysfs=(\S+)", line)
                info["sysfs"] = match.group(1) if match else ""
        if info.get("name"):
            yield info


def classify(names: list[str], handlers: list[str]) -> str:
    """Tipo di periferica dal nome base e dagli handler del kernel."""
    bases = [SUFFIX.sub("", name).strip() for name in names]
    base = min(bases, key=len) if bases else ""
    if MOUSE_NAME.search(base):
        return "mouse"
    if KEYBOARD_NAME.search(base):
        return "keyboard"
    if any(MOUSE_HANDLER.fullmatch(h) for h in handlers):
        return "mouse"
    if any(h in ("kbd", "sysrq") for h in handlers):
        return "keyboard"
    return "other"


def parse_proc(text: str) -> list[dict]:
    """Dispositivi USB/Bluetooth con handler di input, una voce per VID/PID."""
    groups: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for info in _blocks(text):
        bus = info.get("bus", "").lower()
        name = info.get("name", "")
        if bus not in BUS_NAMES or SKIP.search(name):
            continue
        if info.get("sysfs", "").startswith("/devices/virtual/"):
            continue                # passthrough, uinput, dispositivi finti
        handlers = info.get("handlers", [])
        relevant = [h for h in handlers
                    if MOUSE_HANDLER.fullmatch(h) or h in ("kbd", "sysrq")]
        if not relevant:
            continue
        key = (info.get("vendor", "").lower(), info.get("product", "").lower())
        entry = groups.get(key)
        if entry is None:
            entry = {"names": [], "handlers": [], "vendorId": key[0], "productId": key[1],
                     "bus": BUS_NAMES[bus]}
            groups[key] = entry
            order.append(key)
        entry["names"].append(name)
        entry["handlers"] += [h for h in handlers if h not in entry["handlers"]]

    found = []
    for key in order:
        entry = groups[key]
        display = min((n.strip() for n in entry["names"]), key=len)
        found.append({
            "name": display or entry["names"][0],
            "vendorId": entry["vendorId"],
            "productId": entry["productId"],
            "bus": entry["bus"],
            "handlers": " ".join(entry["handlers"]),
            "interfaces": entry["names"],
            "kind": classify(entry["names"], entry["handlers"]),
        })
    return found


def parse_serial_ports(paths: list[str]) -> list[dict]:
    """Voci per le porte seriali collegate (non HID: nessun controllo RGB)."""
    found = []
    for path in paths:
        port = Path(path).name
        found.append({"name": f"Porta seriale {port}", "vendorId": "", "productId": "",
                      "bus": "Seriale", "handlers": "", "interfaces": [], "kind": "other",
                      "port": str(path)})
    return found


def find_serial_ports(patterns=SERIAL_PATTERNS) -> list[dict]:
    paths: list[str] = []
    for pattern in patterns:
        paths.extend(sorted(glob.glob(pattern)))
    return parse_serial_ports(paths)


class SysInputBackend(Backend):
    id = "sys"

    def __init__(self, path: str = PROC, patterns=SERIAL_PATTERNS):
        self.path = path
        self.patterns = patterns

    def list(self):
        try:
            with open(self.path, encoding="utf-8", errors="replace") as handle:
                items = parse_proc(handle.read())
        except OSError:
            items = []
        items += find_serial_ports(self.patterns)

        out = []
        for it in items:
            kind = it["kind"]
            receiver = "receiver" in it["name"].lower()
            if kind == "keyboard":
                note = ("Tastiera cablata rilevata tramite USB. OpenRGB non la riconosce: "
                        "KogitechHub può mostrarla ma non cambiarne colori e pattern.")
            elif receiver:
                note = "Ricevitore wireless: i mouse collegati non sono configurabili da qui."
            elif kind == "mouse":
                note = ("Questo mouse non è supportato da libratbag: KogitechHub può "
                        "solo mostrarlo.")
            elif kind == "other" and it.get("port"):
                note = ("Porta seriale collegata. Se è una periferica di input, il controllo "
                        "dipende dal produttore: nessun backend la gestisce.")
            else:
                note = "Periferica di input rilevata dal sistema in sola lettura."
            dev_id = (f"{self.id}:serial:{it['name'].rsplit(' ', 1)[-1]}"
                      if it.get("port") else f"{self.id}:{it['vendorId']}:{it['productId']}")
            details = {"Collegamento": it["bus"]}
            if it["handlers"]:
                details["Gestori input"] = it["handlers"]
            if it["interfaces"] and len(it["interfaces"]) > 1:
                details["Interfacce"] = ", ".join(it["interfaces"])
            if it.get("port"):
                details["Porta"] = it["port"]
            out.append({
                "id": dev_id, "name": it["name"],
                "vendor": vendor_name(it["vendorId"]) if it["vendorId"] else "",
                "vendorId": it["vendorId"], "productId": it["productId"],
                "backend": self.id, "kind": kind, "configurable": False,
                "subtitle": it["bus"], "dpi": 0, "reportRate": 0, "presetCount": 0,
                "note": note, "details": details,
            })
        return out

    def load(self, dev_id):
        for dev in self.list():
            if dev["id"] == dev_id:
                return dev
        raise BackendError("Dispositivo non più collegato.")

    def apply(self, dev_id, desired):
        raise BackendError("Dispositivo in sola lettura.")
