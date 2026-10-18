"""Motore: unisce i backend, elenca i dispositivi e applica le modifiche.

I backend coprono famiglie diverse: mouse (libratbag), RGB di tastiere/cuffie
(OpenRGB), cuffie USB (HeadsetControl). Un dispositivo non configurabile viene
nascosto se lo stesso ID USB è già gestito da un backend configurabile.
"""
from __future__ import annotations

import re

from ..backends.base import Backend, BackendError

KIND_ORDER = {"mouse": 0, "keyboard": 1, "headset": 2, "other": 3}


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


class Engine:
    def __init__(self, backends: list[Backend]):
        self.backends = {b.id: b for b in backends}
        self.order = [b.id for b in backends]

    def status(self) -> list[dict]:
        out = []
        for bid in self.order:
            ok, msg = self.backends[bid].available()
            out.append({"id": bid, "ok": ok, "message": msg})
        return out

    def devices(self) -> tuple[list[dict], list[dict]]:
        """Restituisce (dispositivi, stato dei backend), ordinati per tipo."""
        devices, status, claimed, claimed_names = [], [], set(), set()
        for bid in self.order:
            backend = self.backends[bid]
            ok, msg = backend.available()
            status.append({"id": bid, "ok": ok, "message": msg})
            if not ok:
                continue
            try:
                found = backend.list()
            except BackendError as exc:
                status[-1] = {"id": bid, "ok": False, "message": str(exc)}
                continue
            for dev in found:
                dev.setdefault("kind", "other")
                vendor_id, product_id = dev.get("vendorId"), dev.get("productId")
                key = (vendor_id, product_id) if vendor_id and product_id else None
                name = _name_key(dev.get("name", ""))
                if not dev["configurable"] and (key in claimed or (name and name in claimed_names)):
                    continue          # stesso dispositivo già gestito da un backend configurabile
                devices.append(dev)
            claimed |= {(d.get("vendorId"), d.get("productId")) for d in found
                        if d["configurable"] and d.get("vendorId") and d.get("productId")}
            claimed_names |= {_name_key(d.get("name", "")) for d in found if d["configurable"]}
        devices.sort(key=lambda d: (not d["configurable"],
                                    KIND_ORDER.get(d.get("kind"), 9),
                                    d["name"].lower()))
        return devices, status

    def _backend(self, dev_id: str) -> Backend:
        bid = dev_id.split(":", 1)[0]
        if bid not in self.backends:
            raise BackendError("Backend sconosciuto.")
        return self.backends[bid]

    def load(self, dev_id: str) -> dict:
        return self._backend(dev_id).load(dev_id)

    def apply(self, dev_id: str, desired: dict) -> dict:
        return self._backend(dev_id).apply(dev_id, desired)
