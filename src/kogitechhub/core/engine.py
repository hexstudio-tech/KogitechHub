"""Motore: unisce i backend, elenca i mouse e applica le modifiche."""
from __future__ import annotations

from ..backends.base import Backend, BackendError


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
        """Restituisce (mouse, stato dei backend). Un mouse noto a un backend
        configurabile non compare di nuovo come sola lettura."""
        devices, status, claimed = [], [], set()
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
            for d in found:
                key = (d.get("vendorId"), d.get("productId"))
                if not d["configurable"] and key in claimed:
                    continue
                devices.append(d)
            claimed |= {(d.get("vendorId"), d.get("productId")) for d in found if d["configurable"]}
        devices.sort(key=lambda d: (not d["configurable"], d["name"].lower()))
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
