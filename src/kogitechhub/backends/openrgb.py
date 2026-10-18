"""Backend OpenRGB: RGB di tastiere, cuffie, mouse e altro via `openrgb`.

OpenRGB è il progetto che parla con quasi tutti i controller RGB su Linux
(Logitech, Corsair, Razer, SteelSeries, ASUS, MSI, ...). KogitechHub usa la
sua CLI (`openrgb -ld` per l'elenco, `-d/-m/-c/-b/-s` per scrivere) invece
del suo server SDK: nessuna porta aperta e nessun demone da avviare a mano.

La CLI mostra nome, tipo, modalità (con quella attiva tra parentesi quadre),
zone e LED. Colori, luminosità e velocità non sono leggibili: l'ultimo valore
scritto da KogitechHub viene ricordato in `core.store` e mostrato come tale.
"""
from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import time

from ..core import store
from .base import Backend, BackendError

DEVICE_RE = re.compile(r"^(\d+):\s*(.*)$")
FIELD_RE = re.compile(r"^  ([A-Za-z ]+):\s*(.*)$")
TIMEOUT = 45
LIST_TTL = 30.0                     # secondi di cache: `openrgb -ld` è lento

KINDS = {
    "keyboard": "keyboard",
    "headset": "headset",
    "headset stand": "headset",
    "mouse": "mouse",
    "mousemat": "other",
    "motherboard": "other",
    "dram": "other",
    "gpu": "other",
    "cooler": "other",
    "led strip": "other",
    "gamepad": "other",
    "light": "other",
    "speaker": "other",
    "virtual": "other",
    "accessory": "other",
    "unknown": "other",
}

MODES_WITH_COLOR = ("direct", "static", "breathing", "spectrum cycle", "rainbow",
                    "wave", "color wave", "color shift", "color pulse", "marquee")

_cache: dict = {"at": 0.0, "devices": None}


def reset_cache() -> None:
    _cache["at"] = 0.0
    _cache["devices"] = None


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "device"


def device_id(index: int, name: str) -> str:
    return f"openrgb:{index}:{slug(name)}"


def kind_of(type_name: str) -> str:
    return KINDS.get(type_name.strip().lower(), "other")


def parse_devices(text: str) -> list[dict]:
    """Interpreta l'output di `openrgb --list-detailed` (formato della CLI)."""
    devices: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        started = DEVICE_RE.match(line)
        if started:
            current = {
                "index": int(started.group(1)),
                "name": started.group(2).strip(),
                "type": "",
                "description": "",
                "version": "",
                "location": "",
                "serial": "",
                "modes": [],
                "activeMode": "",
                "zones": [],
                "leds": [],
            }
            devices.append(current)
            continue
        if current is None:
            continue
        field = FIELD_RE.match(line)
        if not field:
            continue
        label, value = field.group(1).strip(), field.group(2).strip()
        if label == "Type":
            current["type"] = value
        elif label == "Description":
            current["description"] = value
        elif label == "Version":
            current["version"] = value
        elif label == "Location":
            current["location"] = value
        elif label == "Serial":
            current["serial"] = value
        elif label == "Modes":
            try:
                tokens = shlex.split(value)
            except ValueError:
                tokens = value.split()
            for token in tokens:
                if token.startswith("[") and token.endswith("]"):
                    active = token[1:-1]
                    current["activeMode"] = active
                    if active not in current["modes"]:
                        current["modes"].append(active)
                elif token and token not in current["modes"]:
                    current["modes"].append(token)
        elif label == "Zones":
            try:
                current["zones"] = shlex.split(value)
            except ValueError:
                current["zones"] = value.split()
        elif label == "LEDs":
            try:
                current["leds"] = shlex.split(value)
            except ValueError:
                current["leds"] = value.split()
    for dev in devices:
        dev["kind"] = kind_of(dev["type"])
        dev["id"] = device_id(dev["index"], dev["name"])
    return devices


def normalize_color(value: str) -> str | None:
    """'#ff0000' / 'FF0000' -> '#FF0000'; None se non è un colore RGB."""
    text = (value or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", text):
        return None
    return "#" + text.upper()


def apply_argv(index: int, desired: dict) -> list[str]:
    """Argomenti per `openrgb` che scrivono le impostazioni richieste."""
    argv = ["openrgb", "-d", str(index)]
    mode = (desired.get("mode") or "").strip()
    if mode:
        argv += ["-m", mode]
    color = normalize_color(desired.get("color") or "")
    if color:
        argv += ["-c", color[1:]]
    brightness = desired.get("brightness")
    if brightness is not None:
        argv += ["-b", str(max(0, min(100, int(brightness))))]
    speed = desired.get("speed")
    if speed is not None:
        argv += ["-s", str(max(0, min(100, int(speed))))]
    return argv


def _run(args: list[str], timeout: int = TIMEOUT) -> str:
    if shutil.which("openrgb") is None:
        raise BackendError("OpenRGB non è installato.")
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise BackendError("OpenRGB non ha risposto in tempo.") from exc
    except OSError as exc:
        raise BackendError(f"Impossibile eseguire OpenRGB: {exc}") from exc
    output = (done.stdout or "") + (done.stderr or "")
    errors = [line.strip() for line in output.splitlines() if line.strip().startswith("Error")]
    if done.returncode != 0 or errors:
        message = errors[0] if errors else (output.strip() or f"codice {done.returncode}")
        raise BackendError(f"OpenRGB: {message}")
    return done.stdout or ""


def devices(force: bool = False) -> list[dict]:
    now = time.monotonic()
    if (not force and _cache["devices"] is not None
            and now - _cache["at"] < LIST_TTL):
        return _cache["devices"]
    found = parse_devices(_run(["openrgb", "-ld"]))
    _cache["devices"], _cache["at"] = found, now
    return found


def _find(found: list[dict], dev_id: str) -> dict:
    for dev in found:
        if dev["id"] == dev_id:
            return dev
    raise BackendError("Dispositivo RGB non più collegato.")


def state_of(dev: dict, applied: dict | None = None) -> dict:
    key = f"openrgb:{slug(dev['name'])}"
    stored = store.get(key)
    if applied:                     # valori appena scritti: non dipendono dal disco
        stored = {**stored, **{k: v for k, v in applied.items() if v is not None}}
    led_count = len(dev["leds"])
    active = dev["activeMode"] or stored.get("mode") or (dev["modes"][0] if dev["modes"] else "")
    details = {
        "Tipo": dev["type"] or "Sconosciuto",
        "Modalità disponibili": ", ".join(dev["modes"]) or "nessuna",
        "Zone": ", ".join(dev["zones"]) or "intero dispositivo",
        "LED": str(led_count),
    }
    if dev["version"]:
        details["Firmware"] = dev["version"]
    if dev["serial"]:
        details["Seriale"] = dev["serial"]
    if dev["location"]:
        details["Posizione"] = dev["location"]
    stored_color = normalize_color(stored.get("color") or "") or "#7B6CFF"
    return {
        "id": dev["id"],
        "backend": "openrgb",
        "kind": dev["kind"],
        "name": dev["name"],
        "vendor": dev["type"] or "RGB",
        "vendorId": "",
        "productId": "",
        "subtitle": f"{dev['type'] or 'RGB'}" + (f" · {led_count} LED" if led_count else ""),
        "configurable": True,
        "lighting": True,
        "loading": False,
        "note": ("OpenRGB non comunica colori e luminosità attuali: qui vedi gli ultimi "
                 "valori applicati da KogitechHub."),
        "modes": list(dev["modes"]),
        "mode": active,
        "zones": list(dev["zones"]),
        "ledCount": led_count,
        "color": stored_color,
        "brightness": int(stored.get("brightness", 100)),
        "speed": int(stored.get("speed", 50)),
        "remembered": bool(stored),
        "details": details,
    }


class OpenRGBBackend(Backend):
    id = "openrgb"

    def available(self):
        if shutil.which("openrgb") is None:
            from .. import deps

            hint = (deps.install_hint(["openrgb"]) or ["installa il pacchetto openrgb"])[0].strip()
            return False, f"OpenRGB non è installato ({hint})."
        return True, ""

    def list(self):
        found = devices()
        out = []
        for dev in found:
            state = state_of(dev)
            out.append({
                "id": state["id"], "name": state["name"], "vendor": state["vendor"],
                "vendorId": "", "productId": "", "subtitle": state["subtitle"],
                "backend": self.id, "kind": dev["kind"], "configurable": True,
                "lighting": True, "dpi": 0, "reportRate": 0, "presetCount": 0,
                "activeMode": state["mode"], "ledCount": state["ledCount"],
                "note": state["note"],
            })
        return out

    def load(self, dev_id):
        return state_of(_find(devices(), dev_id))

    def apply(self, dev_id, desired):
        found = devices()
        dev = _find(found, dev_id)
        _run(apply_argv(dev["index"], desired))
        mode = (desired.get("mode") or "").strip()
        if mode:
            dev["activeMode"] = mode
            if mode not in dev["modes"]:
                dev["modes"].append(mode)
        color = normalize_color(desired.get("color") or "")
        store.put(f"openrgb:{slug(dev['name'])}", {
            "mode": mode or dev["activeMode"],
            "color": color,
            "brightness": desired.get("brightness"),
            "speed": desired.get("speed"),
        })
        _cache["devices"], _cache["at"] = found, time.monotonic()
        return state_of(dev, {"mode": mode or dev["activeMode"], "color": color,
                              "brightness": desired.get("brightness"),
                              "speed": desired.get("speed")})
