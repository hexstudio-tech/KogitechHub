"""Backend libratbag: parla con il demone `ratbagd` via D-Bus (nessun accesso HID diretto).

Supporta tutti i mouse noti a libratbag (Logitech, Razer, SteelSeries, Roccat...).
Per i test si può usare il bus di sessione con KOGITECHHUB_BUS=session.
"""
from __future__ import annotations

import os
import re

from ..core.vendors import vendor_name
from .base import Backend, BackendError, build_state, plan_ops

try:  # PyGObject è presente di serie su Fedora/Nobara
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib
    _GI_ERROR = ""
except Exception as exc:  # pragma: no cover - dipende dall'ambiente
    Gio = GLib = None
    _GI_ERROR = str(exc)

BUS = "org.freedesktop.ratbag1"
MANAGER_PATH = "/org/freedesktop/ratbag1"
I_MANAGER = BUS + ".Manager"
I_DEVICE = BUS + ".Device"
I_PROFILE = BUS + ".Profile"
I_RES = BUS + ".Resolution"
I_PROPS = "org.freedesktop.DBus.Properties"
# RATBAG_RESOLUTION_CAP_* (libratbag.h): SEPARATE_XY_RESOLUTION = 1, DISABLE = 2
CAP_DISABLE = 2


class RatbagBackend(Backend):
    id = "ratbag"

    def __init__(self):
        self._conn = None

    # --- D-Bus -----------------------------------------------------------
    def _bus(self):
        if Gio is None:
            raise BackendError("PyGObject non disponibile (installa python3-gobject).")
        if self._conn is None:
            kind = Gio.BusType.SESSION if os.environ.get("KOGITECHHUB_BUS") == "session" else Gio.BusType.SYSTEM
            try:
                self._conn = Gio.bus_get_sync(kind, None)
            except GLib.Error as exc:
                raise BackendError(f"Bus D-Bus non raggiungibile: {exc.message}") from exc
        return self._conn

    def _call(self, path, iface, method, params=None, reply=None, timeout=15000):
        try:
            return self._bus().call_sync(
                BUS, path, iface, method, params, reply,
                Gio.DBusCallFlags.NONE, timeout, None)
        except GLib.Error as exc:
            self._conn = None if "closed" in (exc.message or "").lower() else self._conn
            raise BackendError(exc.message) from exc

    def _get_all(self, path, iface) -> dict:
        res = self._call(path, I_PROPS, "GetAll", GLib.Variant("(s)", (iface,)),
                         GLib.VariantType("(a{sv})"), timeout=5000)
        return res.unpack()[0]

    def _resolution_info(self, path) -> tuple[int, bool, bool]:
        """Ritorna (dpi, xy, proprietà_di_tipo_variant) di uno slot di risoluzione.

        Le versioni recenti di ratbagd dichiarano `Resolution` come variant ('v')
        per poter contenere sia `u` sia `(uu)` (X/Y separati): in quel caso il
        valore va scritto con un variant annidato (v dentro v dentro il valore).
        """
        res = self._call(path, I_PROPS, "Get", GLib.Variant("(ss)", (I_RES, "Resolution")),
                         GLib.VariantType("(v)"), timeout=5000)
        value = res.get_child_value(0).get_variant()
        variant_prop = value.get_type_string() == "v"
        if variant_prop:
            value = value.get_variant()
        raw = value.unpack()
        xy = isinstance(raw, (tuple, list))
        return int(raw[0] if xy else raw), xy, variant_prop

    def _set(self, path, iface, name, value):
        self._call(path, I_PROPS, "Set", GLib.Variant("(ssv)", (iface, name, value)))

    # --- disponibilità ---------------------------------------------------
    def available(self):
        try:
            self._get_all(MANAGER_PATH, I_MANAGER)
            return True, ""
        except BackendError as exc:
            msg = str(exc)
            if "ServiceUnknown" in msg or "not provided" in msg or "not activatable" in msg or "NameHasNoOwner" in msg:
                msg = "Il servizio ratbagd non è attivo."
            return False, msg

    # --- lettura ---------------------------------------------------------
    def _read(self, path):
        dev = self._get_all(path, I_DEVICE)
        profile_path, profile = None, {}
        for p in dev.get("Profiles", []):
            props = self._get_all(p, I_PROFILE)
            if profile_path is None:
                profile_path, profile = p, props
            if props.get("IsActive"):
                profile_path, profile = p, props
                break
        if profile_path is None:
            raise BackendError("Il dispositivo non espone profili.")
        slots = []
        for r in profile.get("Resolutions", []):
            props = self._get_all(r, I_RES)
            dpi, xy, variant_prop = self._resolution_info(r)
            slots.append({
                "path": r,
                "index": int(props.get("Index", len(slots))),
                "dpi": dpi,
                "xy": xy,
                "variant_prop": variant_prop,
                "enabled": not props.get("IsDisabled", False),
                "active": bool(props.get("IsActive")),
                "default": bool(props.get("IsDefault")),
                "allowed": [int(v) for v in props.get("Resolutions", [])],
                "caps": list(props.get("Capabilities", [])),
            })
        slots.sort(key=lambda s: s["index"])
        if not slots:
            raise BackendError("Il profilo non ha risoluzioni configurabili.")
        can_disable = any(CAP_DISABLE in s["caps"] for s in slots)
        return dev, profile_path, profile, slots, can_disable

    @staticmethod
    def _ids(model_str):
        m = re.match(r"^\w+:([0-9a-fA-F]{4}):([0-9a-fA-F]{4})", model_str or "")
        return (m.group(1).lower(), m.group(2).lower()) if m else ("", "")

    def load(self, dev_id):
        path = dev_id.split(":", 1)[1]
        dev, profile_path, profile, slots, can_disable = self._read(path)
        vid, pid = self._ids(dev.get("Model", ""))
        details = {"Modello": dev.get("Model", ""), "Profilo attivo": str(int(profile.get("Index", 0)) + 1),
                   "Percorso D-Bus": path}
        return build_state(
            dev_id=dev_id, backend=self.id, name=dev.get("Name") or "Mouse",
            vendor_id=vid, product_id=pid, slots=slots, can_disable=can_disable,
            rates=profile.get("ReportRates", []), rate=profile.get("ReportRate", 0),
            details=details)

    def list(self):
        mgr = self._get_all(MANAGER_PATH, I_MANAGER)
        out = []
        for path in mgr.get("Devices", []):
            dev_id = f"{self.id}:{path}"
            try:
                st = self.load(dev_id)
                active = next((p["dpi"] for p in st["presets"] if p["active"]), 0)
                out.append({"id": dev_id, "name": st["name"], "vendor": st["vendor"],
                            "vendorId": st["vendorId"], "productId": st["productId"],
                            "backend": self.id, "kind": "mouse", "configurable": True,
                            "dpi": active, "reportRate": st["reportRate"],
                            "presetCount": len(st["presets"]), "note": ""})
            except BackendError as exc:
                dev = {}
                try:
                    dev = self._get_all(path, I_DEVICE)
                except BackendError:
                    pass
                vid, pid = self._ids(dev.get("Model", ""))
                out.append({"id": dev_id, "name": dev.get("Name") or "Mouse sconosciuto",
                            "vendor": vendor_name(vid), "vendorId": vid, "productId": pid,
                            "backend": self.id, "kind": "mouse", "configurable": False,
                            "dpi": 0, "reportRate": 0, "presetCount": 0, "note": str(exc)})
        return out

    # --- scrittura -------------------------------------------------------
    def apply(self, dev_id, desired):
        path = dev_id.split(":", 1)[1]
        dev, profile_path, profile, slots, can_disable = self._read(path)
        ops = plan_ops(slots, can_disable, desired["presets"], desired.get("rate"),
                       int(profile.get("ReportRate", 0)))
        for op in ops:
            kind = op[0]
            if kind == "enable":
                self._set(slots[op[1]]["path"], I_RES, "IsDisabled", GLib.Variant("b", not op[2]))
            elif kind == "dpi":
                s = slots[op[1]]
                value = GLib.Variant("(uu)", (op[2], op[2])) if s["xy"] else GLib.Variant("u", op[2])
                if s.get("variant_prop"):
                    value = GLib.Variant("v", value)
                self._set(s["path"], I_RES, "Resolution", value)
            elif kind == "default":
                self._call(slots[op[1]]["path"], I_RES, "SetDefault")
            elif kind == "active":
                self._call(slots[op[1]]["path"], I_RES, "SetActive")
            elif kind == "rate":
                self._set(profile_path, I_PROFILE, "ReportRate", GLib.Variant("u", op[1]))
        if ops:
            res = self._call(path, I_DEVICE, "Commit")
            code = res.unpack()[0] if res is not None and res.n_children() else 0
            if code:
                raise BackendError(f"Il dispositivo ha rifiutato la modifica (codice {code}).")
        return self.load(dev_id)
