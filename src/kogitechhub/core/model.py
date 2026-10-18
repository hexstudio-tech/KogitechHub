"""Operazioni pure sullo stato di un mouse configurabile.

Nessun I/O e nessuna dipendenza da Qt: l'interfaccia lavora su una copia
"desiderata" dello stato (preset DPI ordinati in modo crescente, uno attivo e
uno di avvio) e il motore la scrive poi sul dispositivo.

Schema dello stato (dict compatibile con QML):
    presets      [{dpi, active, default}]  solo preset abilitati, DPI crescenti
    maxPresets   numero di slot hardware
    minPresets   minimo di preset da mantenere
    canResize    True se si possono aggiungere/rimuovere preset
    dpiMin/dpiMax/dpiList   valori DPI supportati
    reportRate / reportRates
"""
from __future__ import annotations

import bisect

DEFAULT_PRESETS = (400, 800, 1600, 3200)
DEFAULT_START = 800


def snap(state: dict, dpi: int) -> int:
    """Riporta un valore DPI al valore supportato più vicino."""
    lo, hi = state["dpiMin"], state["dpiMax"]
    dpi = max(lo, min(hi, int(dpi)))
    values = state.get("dpiList") or []
    if not values:
        return dpi
    i = bisect.bisect_left(values, dpi)
    if i == 0:
        return values[0]
    if i == len(values):
        return values[-1]
    before, after = values[i - 1], values[i]
    return before if dpi - before <= after - dpi else after


def normalize(state: dict) -> dict:
    """Ordina i preset per DPI e garantisce un solo attivo e un solo default."""
    presets = state["presets"]
    presets.sort(key=lambda p: p["dpi"])
    for flag in ("active", "default"):
        marked = [i for i, p in enumerate(presets) if p[flag]]
        keep = marked[0] if marked else 0
        for i, p in enumerate(presets):
            p[flag] = i == keep
    return state


def _insert_sorted(presets: list, preset: dict) -> int:
    pos = sum(1 for q in presets if q["dpi"] < preset["dpi"])
    presets.insert(pos, preset)
    return pos


def select(state: dict, idx: int) -> None:
    presets = state["presets"]
    if 0 <= idx < len(presets):
        for i, p in enumerate(presets):
            p["active"] = i == idx


def set_default(state: dict, idx: int) -> None:
    presets = state["presets"]
    if 0 <= idx < len(presets):
        for i, p in enumerate(presets):
            p["default"] = i == idx


def set_dpi(state: dict, idx: int, dpi: int, exact: bool = False) -> int:
    """Cambia il DPI di un preset. Restituisce il suo nuovo indice.

    exact=True scrive il valore così com'è (limitato all'intervallo del
    dispositivo): serve quando l'utente digita un valore, che va rispettato.
    Altrimenti il valore viene agganciato alla lista dei valori supportati,
    comodo durante il trascinamento.
    """
    presets = state["presets"]
    if not 0 <= idx < len(presets):
        return idx
    if exact:
        new = max(state["dpiMin"], min(state["dpiMax"], int(dpi)))
    else:
        new = snap(state, dpi)
    if new == presets[idx]["dpi"]:
        return idx
    if any(i != idx and p["dpi"] == new for i, p in enumerate(presets)):
        return idx
    preset = presets.pop(idx)
    preset["dpi"] = new
    return _insert_sorted(presets, preset)


def can_add(state: dict) -> bool:
    return bool(state.get("canResize")) and len(state["presets"]) < state.get("maxPresets", 0)


def can_remove(state: dict) -> bool:
    return bool(state.get("canResize")) and len(state["presets"]) > state.get("minPresets", 1)


def add_preset(state: dict, dpi: int) -> int:
    """Aggiunge un preset (e lo rende attivo). Restituisce l'indice o -1."""
    if not can_add(state):
        return -1
    new = snap(state, dpi)
    if any(p["dpi"] == new for p in state["presets"]):
        return -1
    pos = _insert_sorted(state["presets"], {"dpi": new, "active": False, "default": False})
    select(state, pos)
    return pos


def remove_preset(state: dict, idx: int) -> bool:
    presets = state["presets"]
    if not can_remove(state) or not 0 <= idx < len(presets):
        return False
    was_active, was_default = presets[idx]["active"], presets[idx]["default"]
    del presets[idx]
    fallback = idx - 1 if idx > 0 else 0
    if was_active:
        select(state, fallback)
    if was_default:
        set_default(state, fallback)
    return True


def set_rate(state: dict, hz: int) -> bool:
    if hz in state.get("reportRates", []):
        state["reportRate"] = hz
        return True
    return False


def nudge(state: dict, delta: int) -> int:
    """Sposta il preset attivo di `delta` valori supportati."""
    presets = state["presets"]
    idx = next((i for i, p in enumerate(presets) if p["active"]), -1)
    if idx < 0:
        return -1
    values = state.get("dpiList") or []
    cur = presets[idx]["dpi"]
    if values:
        pos = bisect.bisect_left(values, cur)
        target = values[max(0, min(len(values) - 1, pos + delta))]
    else:
        target = cur + 50 * delta
    return set_dpi(state, idx, target)


def restore_defaults(state: dict) -> None:
    """Preset di fabbrica: 400/800/1600/3200 DPI, avvio a 800, massima frequenza.

    I valori di fabbrica vengono scritti così come sono: niente aggancio alla
    griglia, che sui mouse Logitech finirebbe per scrivere 402/802/1602/3202
    invece di 400/800/1600/3200.
    """
    presets = state["presets"]
    if state.get("canResize"):
        count = max(1, min(state.get("maxPresets", 4), len(DEFAULT_PRESETS)))
    else:
        count = len(presets)
    values = state.get("dpiList") or []
    wanted: list[int] = []
    for v in DEFAULT_PRESETS:
        if len(wanted) == count:
            break
        if v not in wanted and state["dpiMin"] <= v <= state["dpiMax"]:
            wanted.append(v)
    spread = values[:: max(1, len(values) // max(count, 1))] if values else []
    for v in spread:                      # eventuali slot in più: punto più "vuoto"
        if len(wanted) == count:
            break
        s = snap(state, v)
        if s not in wanted:
            wanted.append(s)
    start = DEFAULT_START if DEFAULT_START in wanted else snap(state, DEFAULT_START)
    if start not in wanted:
        start = wanted[min(1, len(wanted) - 1)]
    state["presets"] = [{"dpi": v, "active": v == start, "default": v == start} for v in wanted]
    normalize(state)
    if state.get("reportRates"):
        state["reportRate"] = max(state["reportRates"])


def desired(state: dict) -> dict:
    """Parte dello stato da scrivere sul dispositivo."""
    return {
        "presets": [dict(dpi=p["dpi"], active=p["active"], default=p["default"]) for p in state["presets"]],
        "rate": state.get("reportRate"),
    }


def suggest_dpi(state: dict) -> int:
    """Valore DPI nel punto più "vuoto" dell'intervallo, per aggiungere un preset."""
    pts = [state["dpiMin"]] + [p["dpi"] for p in state["presets"]] + [state["dpiMax"]]
    best = max(range(len(pts) - 1), key=lambda i: pts[i + 1] - pts[i])
    return snap(state, (pts[best] + pts[best + 1]) // 2)
