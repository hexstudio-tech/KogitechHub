"""Backend simulato per provare l'interfaccia senza hardware (`--mock`).

Oltre ai due mouse include una tastiera RGB e una cuffia, così si possono
provare anche le pagine Illuminazione e Cuffie senza avere i dispositivi.
"""
from __future__ import annotations

import copy

from .base import Backend, BackendError, build_state, plan_ops

KEYBOARD_MODES = ["Direct", "Static", "Breathing", "Rainbow", "Spectrum Cycle", "Wave"]


class MockBackend(Backend):
    id = "mock"

    def __init__(self):
        allowed = list(range(200, 4001, 50))
        dpis = [400, 800, 1600, 3200, 2000]
        self.slots = [{"dpi": d, "enabled": i < 4, "active": i == 1, "default": i == 1,
                       "allowed": allowed} for i, d in enumerate(dpis)]
        self.rate = 1000
        self.commits = 0
        self.lighting = {
            "mode": "Static", "modeIndex": 1, "color": "#7B6CFF",
            "brightness": 80, "speed": 40, "modes": list(KEYBOARD_MODES),
            "zones": ["Keyboard", "Underglow"], "ledCount": 120,
        }
        self.headset = {
            "sidetone": 64, "lights": True, "inactive": 30,
            "battery": 42, "batteryStatus": "BATTERY_AVAILABLE", "chatmix": 48,
            "capabilities": ["sidetone", "battery", "lights", "inactive time", "chatmix"],
        }

    # --- elenco ---------------------------------------------------------------
    def list(self):
        st = self.load("mock:g402")
        active = next(p["dpi"] for p in st["presets"] if p["active"])
        return [
            {"id": "mock:g402", "name": "Logitech Gaming Mouse G402", "vendor": "Logitech",
             "vendorId": "046d", "productId": "c07e", "backend": self.id, "kind": "mouse",
             "configurable": True, "dpi": active, "reportRate": self.rate,
             "presetCount": len(st["presets"]), "note": ""},
            {"id": "mock:keyboard", "name": "Kogitech RGB Keyboard", "vendor": "Kogitech",
             "vendorId": "f00b", "productId": "a001", "backend": self.id, "kind": "keyboard",
             "configurable": True, "lighting": True, "dpi": 0, "reportRate": 0,
             "presetCount": 0, "activeMode": self.lighting["mode"],
             "ledCount": self.lighting["ledCount"],
             "subtitle": f"Keyboard · {self.lighting['ledCount']} LED", "note": ""},
            {"id": "mock:headset", "name": "Kogitech Wireless Headset", "vendor": "Kogitech",
             "vendorId": "f00b", "productId": "a002", "backend": self.id, "kind": "headset",
             "configurable": True, "headset": True, "dpi": 0, "reportRate": 0,
             "presetCount": 0, "battery": self.headset["battery"],
             "batteryStatus": self.headset["batteryStatus"],
             "subtitle": "Kogitech · cuffia", "note": ""},
            {"id": "mock:hp", "name": "HP USB Optical Mouse", "vendor": "HP", "vendorId": "03f0",
             "productId": "094a", "backend": self.id, "kind": "mouse", "configurable": False,
             "dpi": 0, "reportRate": 0, "presetCount": 0,
             "note": "Questo mouse non è supportato da libratbag: KogitechHub può solo mostrarlo.",
             "details": {"Collegamento": "USB", "Gestori input": "mouse3 event7"}},
        ]

    # --- stato ---------------------------------------------------------------
    def load(self, dev_id):
        if dev_id == "mock:hp":
            return next(d for d in self.list() if d["id"] == dev_id)
        if dev_id == "mock:keyboard":
            light = self.lighting
            return {
                "id": dev_id, "backend": self.id, "kind": "keyboard",
                "name": "Kogitech RGB Keyboard", "vendor": "Kogitech",
                "vendorId": "f00b", "productId": "a001",
                "subtitle": f"Keyboard · {light['ledCount']} LED",
                "configurable": True, "lighting": True, "loading": False,
                "note": "Dispositivo simulato.",
                "modes": list(light["modes"]), "mode": light["mode"],
                "zones": list(light["zones"]), "ledCount": light["ledCount"],
                "color": light["color"], "brightness": light["brightness"],
                "speed": light["speed"], "remembered": True,
                "details": {"Tipo": "Tastiera", "Zone": ", ".join(light["zones"]),
                            "LED": str(light["ledCount"])},
            }
        if dev_id == "mock:headset":
            headset = self.headset
            return {
                "id": dev_id, "backend": self.id, "kind": "headset",
                "name": "Kogitech Wireless Headset", "vendor": "Kogitech",
                "vendorId": "f00b", "productId": "a002",
                "subtitle": "Kogitech · cuffia", "configurable": True,
                "headset": True, "loading": False, "note": "Dispositivo simulato.",
                "capabilities": list(headset["capabilities"]),
                "battery": headset["battery"], "batteryStatus": headset["batteryStatus"],
                "chatmix": headset["chatmix"], "sidetone": headset["sidetone"],
                "sidetoneMax": 128, "lights": headset["lights"],
                "inactive": headset["inactive"],
                "inactiveChoices": [0, 10, 30, 60], "remembered": True,
                "details": {"Produttore": "Kogitech", "Modello": "Wireless Headset",
                            "Funzioni": ", ".join(headset["capabilities"])},
            }
        if dev_id != "mock:g402":
            raise BackendError("Dispositivo non più collegato.")
        state = build_state(dev_id=dev_id, backend=self.id,
                            name="Logitech Gaming Mouse G402", vendor_id="046d",
                            product_id="c07e", slots=copy.deepcopy(self.slots),
                            can_disable=True, rates=[125, 250, 500, 1000],
                            rate=self.rate,
                            details={"Modello": "usb:046d:c07e:0 (simulato)"})
        state.update(kind="mouse", subtitle="Logitech Gaming Mouse G402")
        return state

    # --- scrittura -----------------------------------------------------------
    def apply(self, dev_id, desired):
        if dev_id == "mock:keyboard":
            for key in ("mode", "color", "brightness", "speed"):
                if desired.get(key) is not None:
                    self.lighting[key] = desired[key]
            self.commits += 1
            return self.load(dev_id)
        if dev_id == "mock:headset":
            for key in ("sidetone", "lights", "inactive"):
                if desired.get(key) is not None:
                    self.headset[key] = desired[key]
            self.commits += 1
            return self.load(dev_id)
        if dev_id != "mock:g402":
            raise BackendError("Dispositivo in sola lettura.")
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
