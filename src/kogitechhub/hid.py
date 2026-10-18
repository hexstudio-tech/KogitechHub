"""Laboratorio HID: nodi hidraw, descrittori, cattura e invio di report.

Serve per le periferiche che nessun backend conosce (per esempio tastiere
generiche con VID/PID fuori dalle liste di OpenRGB). Con questo modulo si può:

- elencare i nodi `/dev/hidraw*` con nome, VID/PID e permessi;
- leggere e interpretare il report descriptor (usage page, report ID, byte);
- catturare i report che il dispositivo invia (attenzione: una tastiera invia
  anche i tasti premuti);
- inviare un report di output o feature, cioè il canale con cui il software
  del produttore configura gli RGB.

Non indovina comandi RGB: quelli vanno ricavati dal protocollo del dispositivo
(vedi README). Il modulo non richiede Qt e non tocca il sistema senza chiedere.
"""
from __future__ import annotations

import collections
import fcntl
import os
import re
import shlex
import shutil
import select
import struct
import subprocess
import threading
import time
from pathlib import Path

SYSFS = Path("/sys/class/hidraw")
DEV = Path("/dev")
MAX_REPORT = 4096
UDEDIR = Path("/etc/udev/rules.d")
RULE_PREFIX = "70-kogitechhub-hid"

REPORT_TYPES = {0x08: "input", 0x09: "output", 0x0B: "feature"}


# --- descrittore ------------------------------------------------------------

def _items(data: bytes):
    """Itera gli item HID (breve e lungo) come (tipo, tag, valore, size)."""
    index = 0
    while index < len(data):
        prefix = data[index]
        if prefix == 0xFE:                       # long item: non usato dai descrittori comuni
            if index + 2 >= len(data):
                break
            size = data[index + 1]
            index += 3 + size
            continue
        size = (0, 1, 2, 4)[prefix & 0x03]      # 0 = item senza dati (per esempio End Collection)
        kind = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F
        raw = data[index + 1:index + 1 + size]
        if len(raw) < size:
            break
        index += 1 + size
        yield kind, tag, int.from_bytes(raw, "little"), size


def describe(descriptor: bytes) -> list[dict]:
    """Riepiloga i report dichiarati: tipo, ID, byte e usage page."""
    global_values = {"usage_page": 0, "report_id": 0, "report_size": 0, "report_count": 0}
    usages: list[tuple[int, int]] = []
    usage_range: tuple[int, int] | None = None
    reports: dict[tuple[str, int], dict] = {}
    order: list[tuple[str, int]] = []

    for kind, tag, value, size in _items(descriptor):
        if kind == 0x01:                          # global
            if tag == 0x00:
                global_values["usage_page"] = value
            elif tag == 0x07:
                global_values["report_size"] = value
            elif tag == 0x08:
                global_values["report_id"] = value
            elif tag == 0x09:
                global_values["report_count"] = value
            continue
        if kind == 0x02:                          # local
            if tag == 0x00:
                page = value >> 16 if size == 4 and value > 0xFFFF else global_values["usage_page"]
                usages.append((page, value & 0xFFFF if size == 4 and value > 0xFFFF else value))
            elif tag == 0x01:
                usage_range = (value, value)
            elif tag == 0x02 and usage_range:
                usage_range = (usage_range[0], value)
            continue
        if kind != 0x00 or tag not in REPORT_TYPES:   # main item
            continue

        rtype = REPORT_TYPES[tag]
        report_id = global_values["report_id"]
        key = (rtype, report_id)
        entry = reports.get(key)
        if entry is None:
            entry = {"type": rtype, "id": report_id, "bits": 0, "bytes": 0,
                     "pages": [], "usages": []}
            reports[key] = entry
            order.append(key)
        entry["bits"] += global_values["report_size"] * global_values["report_count"]
        entry["bytes"] = (entry["bits"] + 7) // 8
        pages = [page for page, _ in usages]
        if usage_range:
            pages.append(global_values["usage_page"])
        for page in pages:
            label = f"0x{page:04X}"
            if label not in entry["pages"]:
                entry["pages"].append(label)
        for page, usage in usages[:8]:
            label = f"0x{page:04X}:0x{usage:04X}"
            if label not in entry["usages"]:
                entry["usages"].append(label)
        usages = []
        usage_range = None

    return [reports[key] for key in order]


def _read_descriptor(sysfs_entry: Path) -> bytes:
    try:
        return (sysfs_entry / "device" / "report_descriptor").read_bytes()[:MAX_REPORT]
    except OSError:
        return b""


def _parse_uevent(path: Path) -> dict:
    fields = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return fields
    for line in text.splitlines():
        key, _, value = line.partition("=")
        fields[key] = value
    return fields


def list_devices(sysfs: Path | str = SYSFS, dev: Path | str = DEV) -> list[dict]:
    """Nodi hidraw presenti, con VID/PID, permessi e report dichiarati."""
    sysfs, dev = Path(sysfs), Path(dev)
    found = []
    for entry in sorted(sysfs.glob("hidraw*"), key=lambda p: p.name):
        uevent = _parse_uevent(entry / "device" / "uevent")
        hid_id = uevent.get("HID_ID", "")
        parts = hid_id.split(":")
        vendor = parts[1][-4:].lower() if len(parts) >= 3 else ""
        product = parts[2][-4:].lower() if len(parts) >= 3 else ""
        node = dev / entry.name
        try:
            exists = node.exists()
        except OSError:
            exists = False
        found.append({
            "node": str(node),
            "name": uevent.get("HID_NAME", entry.name).strip(),
            "vendorId": vendor,
            "productId": product,
            "phys": uevent.get("HID_PHYS", ""),
            "exists": exists,
            "readable": bool(exists and os.access(node, os.R_OK)),
            "writable": bool(exists and os.access(node, os.W_OK)),
            "reports": describe(_read_descriptor(entry)),
        })
    return found


def report_score(device: dict) -> int:
    """Quanto un nodo somiglia all'interfaccia di configurazione.

    Un dispositivo espone più nodi hidraw: quello dei tasti (input) e quello
    che scambia comandi, che dichiara report feature/output su una pagina
    vendor (0xFF00 e simili). Il punteggio serve a proporre per primo il nodo
    giusto, quello su cui cercare il protocollo RGB.
    """
    score = 0
    for report in device.get("reports", []):
        vendor_page = any(str(page).upper().startswith("0xFF") for page in report.get("pages", []))
        if report.get("type") == "feature":
            score += 2
        if report.get("type") in ("feature", "output") and vendor_page:
            score += 3 + min(int(report.get("bytes", 0)), 8)
    return score


def devices_for(vendor: str, product: str, **kwargs) -> list[dict]:
    vendor, product = (vendor or "").lower(), (product or "").lower()
    return [d for d in list_devices(**kwargs)
            if d["vendorId"] == vendor and d["productId"] == product]


# --- cattura ----------------------------------------------------------------

class Capture:
    """Legge i report da un nodo hidraw in un thread separato."""

    def __init__(self, node: str, max_reports: int = 400):
        self.node = node
        self.reports: collections.deque = collections.deque(maxlen=max_reports)
        self.error = ""
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self.error = ""
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="hid-capture", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        try:
            fd = os.open(self.node, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as exc:
            self.error = f"{self.node}: {exc.strerror or exc}"
            return
        try:
            while not self._stop.is_set():
                ready, _, _ = select.select([fd], [], [], 0.2)
                if not ready:
                    continue
                try:
                    data = os.read(fd, MAX_REPORT)
                except BlockingIOError:
                    continue
                if not data:
                    continue
                self.reports.append({
                    "time": time.strftime("%H:%M:%S"),
                    "stamp": round(time.time(), 3),
                    "length": len(data),
                    "id": data[0],
                    "hex": data.hex(" "),
                })
        except OSError as exc:
            self.error = f"{self.node}: {exc.strerror or exc}"
        finally:
            os.close(fd)

    def drain(self) -> list[dict]:
        out = []
        while self.reports:
            out.append(self.reports.popleft())
        return out

    def stop(self, timeout: float = 1.5) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)
            self._thread = None


# --- invio report -----------------------------------------------------------

def parse_hex(text: str) -> bytes:
    """'05 FF 00' / '05ff00' / '0x05,0xFF' -> bytes; ValueError se non valido."""
    cleaned = re.sub(r"0x|[\s,;:_-]+", "", (text or "").lower())
    if not cleaned:
        raise ValueError("nessun byte da inviare")
    if not re.fullmatch(r"[0-9a-f]+", cleaned):
        raise ValueError("caratteri non esadecimali")
    if len(cleaned) % 2:
        raise ValueError("numero di cifre dispari: ogni byte ha due cifre")
    data = bytes.fromhex(cleaned)
    if len(data) > MAX_REPORT:
        raise ValueError(f"report troppo lungo (massimo {MAX_REPORT} byte)")
    return data


def hid_ioc(request_type: int, length: int) -> int:
    """HIDIOCSFEATURE(length) / HIDIOCGFEATURE(length) su Linux."""
    return (0xC0000000 | (length << 16) | (ord("H") << 8) | request_type)


def send_report(node: str, data: bytes, kind: str = "output") -> None:
    """Scrive un report di output (write) o feature (ioctl) sul nodo hidraw."""
    if not data:
        raise ValueError("report vuoto")
    if kind not in ("output", "feature"):
        raise ValueError("tipo di report non valido")
    try:
        fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
    except PermissionError as exc:
        raise PermissionError("permessi insufficienti sul nodo hidraw") from exc
    except OSError as exc:
        raise OSError(f"impossibile aprire {node}: {exc.strerror or exc}") from exc
    try:
        if kind == "feature":
            buffer = bytearray(data)
            fcntl.ioctl(fd, hid_ioc(0x06, len(buffer)), buffer, True)
        else:
            os.write(fd, data)
    finally:
        os.close(fd)


def get_feature(node: str, report_id: int, length: int) -> bytes:
    """Legge un report feature (HIDIOCGFEATURE) dal nodo hidraw.

    È la parte in sola lettura del protocollo di configurazione: leggere i
    report feature di una tastiera mostra lo stato corrente (colori, effetti)
    senza rischiare di scriverci sopra.
    """
    if not 0 <= int(report_id) <= 0xFF:
        raise ValueError("ID del report fuori intervallo (0-255)")
    if not 0 < int(length) <= MAX_REPORT:
        raise ValueError(f"lunghezza non valida (1-{MAX_REPORT} byte)")
    try:
        fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
    except PermissionError as exc:
        raise PermissionError("permessi insufficienti sul nodo hidraw") from exc
    except OSError as exc:
        raise OSError(f"impossibile aprire {node}: {exc.strerror or exc}") from exc
    try:
        buffer = bytearray(int(length))
        buffer[0] = int(report_id)
        fcntl.ioctl(fd, hid_ioc(0x07, len(buffer)), buffer, True)      # HIDIOCGFEATURE
        return bytes(buffer)
    finally:
        os.close(fd)


# --- permessi (regola udev) -------------------------------------------------

def udev_rule(vendor: str, product: str) -> str:
    vendor, product = (vendor or "").lower(), (product or "").lower()
    if not re.fullmatch(r"[0-9a-f]{4}", vendor) or not re.fullmatch(r"[0-9a-f]{4}", product):
        raise ValueError("VID/PID non validi")
    return (f'# KogitechHub: accesso HID a {vendor}:{product}\n'
            f'SUBSYSTEM=="hidraw", ATTRS{{idVendor}}=="{vendor}", '
            f'ATTRS{{idProduct}}=="{product}", TAG+="uaccess"\n')


def rule_path(vendor: str, product: str) -> Path:
    return UDEDIR / f"{RULE_PREFIX}-{vendor}-{product}.rules"


def grant_script(vendor: str, product: str) -> str:
    """Script root (idempotente) per installare la regola e ricaricare udev."""
    rule = udev_rule(vendor, product)
    destination = rule_path(vendor, product)
    return ("set -e\n"
            f"cat > {shlex.quote(str(destination))} <<'KOGITECHHUB_RULE'\n{rule}KOGITECHHUB_RULE\n"
            "udevadm control --reload-rules\n"
            "udevadm trigger --subsystem-match=hidraw --action=add\n")


def grant_command(vendor: str, product: str) -> str:
    """Comando da copiare in un terminale se pkexec non è disponibile."""
    script = grant_script(vendor, product)
    return f"sudo sh -c {shlex.quote(script)}"


def grant_access(vendor: str, product: str, timeout: int = 180) -> tuple[bool, str]:
    """Installa la regola udev chiedendo la password con pkexec (o sudo)."""
    script = grant_script(vendor, product)
    if shutil.which("pkexec"):
        argv = ["pkexec", "/bin/sh", "-c", script]
    elif shutil.which("sudo"):
        argv = ["sudo", "/bin/sh", "-c", script]
    else:
        return False, "pkexec/sudo non disponibili: " + grant_command(vendor, product)
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "autorizzazione scaduta: riprova"
    except OSError as exc:
        return False, f"impossibile chiedere i permessi: {exc}"
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip().splitlines()
        hint = detail[-1] if detail else f"codice {done.returncode}"
        return False, f"permessi non concessi ({hint})"
    return True, "regola udev installata"
