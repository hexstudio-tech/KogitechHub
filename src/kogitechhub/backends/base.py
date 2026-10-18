"""Interfaccia comune dei backend e funzioni condivise (pure, testabili)."""
from __future__ import annotations

from ..core import model
from ..core.vendors import vendor_name

FALLBACK_DPI = list(range(200, 8001, 50))


class BackendError(Exception):
    """Errore leggibile dall'utente, proveniente da un backend."""


class Backend:
    id = "base"

    def available(self) -> tuple[bool, str]:
        return True, ""

    def list(self) -> list[dict]:
        """Riepiloghi dei dispositivi: id, name, vendorId, productId, configurable, ..."""
        raise NotImplementedError

    def load(self, dev_id: str) -> dict:
        raise NotImplementedError

    def apply(self, dev_id: str, desired: dict) -> dict:
        raise NotImplementedError


def build_state(*, dev_id, backend, name, vendor_id, product_id, slots, can_disable,
                rates, rate, details=None, note="") -> dict:
    """Costruisce lo stato per l'interfaccia a partire dagli slot hardware.

    slots: [{dpi, enabled, active, default, allowed:[...]}] in ordine di indice.
    """
    enabled = [s for s in slots if s["enabled"]] or list(slots)
    allowed = sorted({v for s in slots for v in s.get("allowed", []) if v > 0})
    if not allowed:
        allowed = [v for v in FALLBACK_DPI]
        note = note or "Valori DPI supportati non comunicati dal dispositivo: uso un intervallo generico."
    cur = [s["dpi"] for s in slots if s["dpi"]]
    if cur and (min(cur) < allowed[0] or max(cur) > allowed[-1]):
        allowed = sorted(set(allowed) | set(cur))
    state = {
        "id": dev_id,
        "backend": backend,
        "name": name,
        "vendorId": vendor_id,
        "productId": product_id,
        "vendor": vendor_name(vendor_id),
        "configurable": True,
        "note": note,
        "presets": [{"dpi": s["dpi"], "active": bool(s["active"]), "default": bool(s["default"])}
                    for s in enabled],
        "maxPresets": len(slots),
        "minPresets": 1,
        "canResize": bool(can_disable) and len(slots) > 1,
        "dpiMin": allowed[0],
        "dpiMax": allowed[-1],
        "dpiList": allowed,
        "reportRate": int(rate or 0),
        "reportRates": sorted(int(r) for r in rates if r),
        "details": details or {},
    }
    return model.normalize(state)


def plan_ops(slots, can_disable, presets, rate, cur_rate) -> list[tuple]:
    """Operazioni minime per portare gli slot hardware nello stato desiderato.

    I preset desiderati occupano gli slot 0..n-1 (abilitati); gli altri slot
    vengono disabilitati solo dopo aver spostato attivo/default.
    """
    n = len(presets)
    if n < 1:
        raise BackendError("Serve almeno un preset DPI.")
    if n > len(slots):
        raise BackendError("Troppi preset per questo mouse.")
    if not can_disable and n != len(slots):
        raise BackendError("Questo mouse ha un numero fisso di preset.")
    ops: list[tuple] = []
    for i, p in enumerate(presets):
        if can_disable and not slots[i]["enabled"]:
            ops.append(("enable", i, True))
        if slots[i]["dpi"] != p["dpi"]:
            ops.append(("dpi", i, int(p["dpi"])))
    default = next((i for i, p in enumerate(presets) if p.get("default")), 0)
    active = next((i for i, p in enumerate(presets) if p.get("active")), 0)
    if not slots[default]["default"]:
        ops.append(("default", default))
    if not slots[active]["active"]:
        ops.append(("active", active))
    if can_disable:
        for i in range(n, len(slots)):
            if slots[i]["enabled"]:
                ops.append(("enable", i, False))
    if rate and rate != cur_rate:
        ops.append(("rate", int(rate)))
    return ops
