"""Backend simulato per provare l'interfaccia senza hardware (`kogitechhub --mock`)."""
from __future__ import annotations

import copy

from .base import Backend, BackendError, build_state, plan_ops


class MockBackend(Backend):
    id = "mock"

    def __init__(self):
        allowed = list(range(200, 4001, 50))
        dpis = [400, 800, 1600, 3200, 2000]
        self.slots = [{"dpi": d, "enabled": i < 4, "active": i == 1, "default": i == 1,
                       "allowed": allowed} for i, d in enumerate(dpis)]
        self.rate = 1000
        self.commits = 0

    def list(self):
        st = self.load("mock:g402")
        active = next(p["dpi"] for p in st["presets"] if p["active"])
        return [
            {"id": "mock:g402", "name": "Logitech Gaming Mouse G402", "vendor": "Logitech",
             "vendorId": "046d", "productId": "c07e", "backend": self.id, "configurable": True,
             "dpi": active, "reportRate": self.rate, "presetCount": len(st["presets"]), "note": ""},
            {"id": "mock:hp", "name": "HP USB Optical Mouse", "vendor": "HP", "vendorId": "03f0",
             "productId": "094a", "backend": self.id, "configurable": False, "dpi": 0,
             "reportRate": 0, "presetCount": 0,
             "note": "Questo mouse non è supportato da libratbag: KogitechHub può solo mostrarlo.",
             "details": {"Collegamento": "USB", "Gestori input": "mouse3 event7"}},
        ]

    def load(self, dev_id):
        if dev_id == "mock:hp":
            return next(d for d in self.list() if d["id"] == dev_id)
        if dev_id != "mock:g402":
            raise BackendError("Mouse non più collegato.")
        return build_state(dev_id=dev_id, backend=self.id, name="Logitech Gaming Mouse G402",
                           vendor_id="046d", product_id="c07e", slots=copy.deepcopy(self.slots),
                           can_disable=True, rates=[125, 250, 500, 1000], rate=self.rate,
                           details={"Modello": "usb:046d:c07e:0 (simulato)"})

    def apply(self, dev_id, desired):
        if dev_id != "mock:g402":
            raise BackendError("Mouse in sola lettura.")
        ops = plan_ops(self.slots, True, desired["presets"], desired.get("rate"), self.rate)
        for op in ops:
            if op[0] == "enable":
                self.slots[op[1]]["enabled"] = op[2]
            elif op[0] == "dpi":
                self.slots[op[1]]["dpi"] = op[2]
            elif op[0] in ("default", "active"):
                for i, s in enumerate(self.slots):
                    s[op[0]] = i == op[1]
            elif op[0] == "rate":
                self.rate = op[1]
        if ops:
            self.commits += 1
        return self.load(dev_id)
