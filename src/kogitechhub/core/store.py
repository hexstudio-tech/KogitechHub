"""Ultime impostazioni applicate a luci e cuffie, salvate su disco.

OpenRGB (CLI) sa dire quali modalità esistono e quale è attiva, ma non i
colori, la luminosità o la velocità correnti; HeadsetControl non sa leggere
sidetone e luci. Qui ricordiamo l'ultimo valore scritto da KogitechHub, così
l'interfaccia può mostrarlo (etichettato come "impostato da KogitechHub").

Formato del file (indipendente dall'indice del dispositivo, che cambia quando
si scollega qualcosa)::

    {"openrgb:Foo Keyboard": {"mode": "Static", "color": "#7B6CFF", ...}}
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "kogitechhub" / "settings.json"


def load(path: Path | None = None) -> dict:
    file = Path(path) if path else config_path()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def get(key: str, path: Path | None = None) -> dict:
    values = load(path).get(key)
    return values if isinstance(values, dict) else {}


def put(key: str, values: dict, path: Path | None = None) -> None:
    """Salva i valori di un dispositivo; errori di scrittura non bloccano l'app."""
    file = Path(path) if path else config_path()
    data = load(file)
    merged = dict(data.get(key) or {})
    merged.update({k: v for k, v in values.items() if v is not None})
    data[key] = merged
    tmp = None
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".settings-", dir=str(file.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, file)
    except OSError:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
