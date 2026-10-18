"""Rilevamento in sola lettura dei mouse tramite /proc/bus/input/devices."""
from __future__ import annotations

import re

from ..core.vendors import vendor_name
from .base import Backend

PROC = "/proc/bus/input/devices"
SKIP = re.compile(r"virtual|touchpad|trackpad|ydotool|uinput", re.I)
BUS_NAMES = {"0003": "USB", "0005": "Bluetooth"}


def parse_proc(text: str) -> list[dict]:
    found, seen = [], set()
    for block in text.strip().split("\n\n"):
        info = {}
        for line in block.splitlines():
            if line.startswith("I:"):
                for k, v in re.findall(r"(\w+)=(\w+)", line):
                    info[k.lower()] = v
            elif line.startswith("N:"):
                m = re.search(r'Name="(.*)"', line)
                info["name"] = m.group(1) if m else ""
            elif line.startswith("H:"):
                info["handlers"] = line.split("=", 1)[1].split()
        handlers = info.get("handlers", [])
        if not any(re.fullmatch(r"mouse\d+", h) for h in handlers):
            continue
        bus = info.get("bus", "").lower()
        if bus not in BUS_NAMES or SKIP.search(info.get("name", "")):
            continue
        vid, pid = info.get("vendor", "").lower(), info.get("product", "").lower()
        if (vid, pid) in seen:
            continue
        seen.add((vid, pid))
        found.append({"name": info.get("name", "Mouse"), "vendorId": vid, "productId": pid,
                      "bus": BUS_NAMES[bus], "handlers": " ".join(handlers)})
    return found


class SysInputBackend(Backend):
    id = "sys"

    def __init__(self, path: str = PROC):
        self.path = path

    def list(self):
        try:
            with open(self.path, encoding="utf-8", errors="replace") as fh:
                items = parse_proc(fh.read())
        except OSError:
            return []
        out = []
        for it in items:
            receiver = "receiver" in it["name"].lower()
            note = ("Ricevitore wireless: i mouse collegati non sono configurabili da qui."
                    if receiver else
                    "Questo mouse non è supportato da libratbag: KogitechHub può solo mostrarlo.")
            out.append({"id": f"{self.id}:{it['vendorId']}:{it['productId']}", "name": it["name"],
                        "vendor": vendor_name(it["vendorId"]), "vendorId": it["vendorId"],
                        "productId": it["productId"], "backend": self.id, "configurable": False,
                        "dpi": 0, "reportRate": 0, "presetCount": 0, "note": note,
                        "details": {"Collegamento": it["bus"], "Gestori input": it["handlers"]}})
        return out

    def load(self, dev_id):
        for d in self.list():
            if d["id"] == dev_id:
                return d
        from .base import BackendError
        raise BackendError("Mouse non più collegato.")

    def apply(self, dev_id, desired):
        from .base import BackendError
        raise BackendError("Mouse in sola lettura.")
