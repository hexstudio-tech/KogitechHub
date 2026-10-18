"""Backend cuffie: batteria, sidetone, luci e spegnimento via `headsetcontrol`.

HeadsetControl supporta le cuffie USB da gaming di Logitech, SteelSeries,
Corsair, HyperX, Audeze, Jabra, Sony... e sa leggere batteria/chatmix; sidetone
e stato delle luci non sono leggibili, quindi si mostra l'ultimo valore
impostato da KogitechHub (`core.store`).

Gli RGB delle cuffie che espongono un controller RGB passano da OpenRGB, che
le elenca come dispositivi separati.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time

from ..core import store
from .base import Backend, BackendError

TIMEOUT = 15
CACHE_TTL = 12.0
_cache: dict = {"at": 0.0, "devices": None}

SIDETONE_MAX = 128
INACTIVE_CHOICES = (0, 10, 30, 60)


def reset_cache() -> None:
    _cache["at"] = 0.0
    _cache["devices"] = None


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "headset"


def device_id(dev: dict) -> str:
    vendor = str(dev.get("id_vendor") or "").strip()
    product = str(dev.get("id_product") or "").strip()
    if vendor and product:
        return f"headset:{vendor}:{product}"
    return f"headset:{slug(str(dev.get('device') or 'headset'))}"


def parse_output(text: str) -> list[dict]:
    """Interpreta `headsetcontrol -o json` (un array di dispositivi)."""
    try:
        payload = json.loads(text)
    except ValueError:
        return []
    if isinstance(payload, dict):
        devices = payload.get("devices", [])
    else:
        devices = payload
    out = []
    for dev in devices if isinstance(devices, list) else []:
        if not isinstance(dev, dict):
            continue
        caps = [str(c) for c in dev.get("capabilities_str") or []]
        battery = dev.get("battery") or {}
        out.append({
            "id": device_id(dev),
            "name": str(dev.get("device") or "Cuffia"),
            "vendor": str(dev.get("vendor") or ""),
            "product": str(dev.get("product") or ""),
            "vendorId": str(dev.get("id_vendor") or ""),
            "productId": str(dev.get("id_product") or ""),
            "status": str(dev.get("status") or ""),
            "capabilities": caps,
            "battery": {
                "level": battery.get("level"),
                "status": str(battery.get("status") or ""),
            },
            "chatmix": dev.get("chatmix"),
        })
    return out


def _run(args: list[str], timeout: int = TIMEOUT) -> str:
    if shutil.which("headsetcontrol") is None:
        raise BackendError("HeadsetControl non è installato.")
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise BackendError("HeadsetControl non ha risposto in tempo.") from exc
    except OSError as exc:
        raise BackendError(f"Impossibile eseguire HeadsetControl: {exc}") from exc
    if done.returncode != 0:
        message = (done.stderr or done.stdout or "").strip().splitlines()
        raise BackendError("HeadsetControl: " + (message[0] if message else
                                                f"codice {done.returncode}"))
    return done.stdout or ""


def _run_listing() -> str:
    """JSON dell'elenco cuffie.

    HeadsetControl esce con codice 1 anche quando non c'è nessuna cuffia
    collegata, ma stampa un JSON valido con `device_count: 0`: quello non è
    un errore.
    """
    if shutil.which("headsetcontrol") is None:
        raise BackendError("HeadsetControl non è installato.")
    try:
        done = subprocess.run(["headsetcontrol", "-o", "json"], capture_output=True,
                              text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise BackendError("HeadsetControl non ha risposto in tempo.") from exc
    except OSError as exc:
        raise BackendError(f"Impossibile eseguire HeadsetControl: {exc}") from exc
    text = (done.stdout or "").strip()
    if text.startswith("{"):
        return text
    message = (done.stderr or text).strip().splitlines()
    raise BackendError("HeadsetControl: " + (message[0] if message else
                                            f"codice {done.returncode}"))


def devices(force: bool = False) -> list[dict]:
    now = time.monotonic()
    if not force and _cache["devices"] is not None and now - _cache["at"] < CACHE_TTL:
        return _cache["devices"]
    found = parse_output(_run_listing())
    _cache["devices"], _cache["at"] = found, now
    return found


def _find(found: list[dict], dev_id: str) -> dict:
    for dev in found:
        if dev["id"] == dev_id:
            return dev
    raise BackendError("Cuffia non più collegata.")


def available_features(dev: dict) -> list[str]:
    return [c for c in dev["capabilities"] if c in
            ("sidetone", "battery", "lights", "inactive time", "chatmix")]


def apply_argv(dev_id: str, desired: dict) -> list[list[str]]:
    """Comandi HeadsetControl per le sole impostazioni presenti in `desired`."""
    commands: list[list[str]] = []
    sidetone = desired.get("sidetone")
    if sidetone is not None:
        commands.append(["headsetcontrol", "-s", str(max(0, min(SIDETONE_MAX, int(sidetone))))])
    lights = desired.get("lights")
    if lights is not None:
        commands.append(["headsetcontrol", "-l", "1" if lights else "0"])
    inactive = desired.get("inactive")
    if inactive is not None:
        commands.append(["headsetcontrol", "-i", str(max(0, int(inactive)))])
    return commands


def state_of(dev: dict, applied: dict | None = None) -> dict:
    key = f"headset:{slug(dev['name'])}"
    stored = store.get(key)
    if applied:                     # valori appena scritti: non dipendono dal disco
        stored = {**stored, **{k: v for k, v in applied.items() if v is not None}}
    battery = dev["battery"]
    level = battery.get("level")
    status = battery.get("status") or "BATTERY_UNAVAILABLE"
    details = {
        "Produttore": dev["vendor"] or "sconosciuto",
        "Modello": dev["product"] or dev["name"],
        "ID USB": f"{dev['vendorId']}:{dev['productId']}".strip(":"),
        "Funzioni": ", ".join(available_features(dev)) or "nessuna",
    }
    if dev["status"] and dev["status"] != "success":
        details["Stato"] = dev["status"]
    return {
        "id": dev["id"],
        "backend": "headset",
        "kind": "headset",
        "name": dev["name"],
        "vendor": dev["vendor"],
        "vendorId": dev["vendorId"],
        "productId": dev["productId"],
        "subtitle": " · ".join(x for x in (dev["vendor"], "cuffia") if x),
        "configurable": True,
        "headset": True,
        "loading": False,
        "note": ("HeadsetControl non legge sidetone, luci e timer attuali: qui vedi gli "
                 "ultimi valori impostati da KogitechHub."),
        "capabilities": available_features(dev),
        "battery": level,
        "batteryStatus": status,
        "chatmix": dev["chatmix"],
        "sidetone": int(stored.get("sidetone", 0)),
        "sidetoneMax": SIDETONE_MAX,
        "lights": bool(stored.get("lights", True)),
        "inactive": int(stored.get("inactive", 0)),
        "inactiveChoices": list(INACTIVE_CHOICES),
        "remembered": bool(stored),
        "details": details,
    }


class HeadsetBackend(Backend):
    id = "headset"

    def available(self):
        if shutil.which("headsetcontrol") is None:
            from .. import deps

            hint = (deps.install_hint(["headsetcontrol"]) or
                    ["installa il pacchetto headsetcontrol"])[0].strip()
            return False, f"HeadsetControl non è installato ({hint})."
        return True, ""

    def list(self):
        out = []
        for dev in devices():
            state = state_of(dev)
            out.append({
                "id": state["id"], "name": state["name"], "vendor": state["vendor"],
                "vendorId": state["vendorId"], "productId": state["productId"],
                "subtitle": state["subtitle"], "backend": self.id, "kind": "headset",
                "configurable": True, "headset": True, "dpi": 0, "reportRate": 0,
                "presetCount": 0, "battery": state["battery"],
                "batteryStatus": state["batteryStatus"],
                "note": state["note"],
            })
        return out

    def load(self, dev_id):
        return state_of(_find(devices(), dev_id))

    def apply(self, dev_id, desired):
        found = devices()
        dev = _find(found, dev_id)
        key = f"headset:{slug(dev['name'])}"
        saved = store.get(key)
        changed = {k: v for k, v in desired.items()
                   if v is not None and saved.get(k) != v}
        commands = apply_argv(dev_id, changed)
        if not commands:
            return state_of(dev, desired)
        for argv in commands:
            _run(argv)
        store.put(key, changed)
        _cache["devices"], _cache["at"] = found, time.monotonic()
        return state_of(dev, desired)
