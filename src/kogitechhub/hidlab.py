"""Ponte Qt/QML del laboratorio HID: nodi hidraw, cattura e invio dei report.

Sta separato dal Controller principale perché ha uno stato tutto suo (nodo
scelto, report catturati, timer di drenaggio). Comunica con il resto dell'app
solo attraverso la funzione di notifica che riceve dal Controller: così i
messaggi a comparsa restano uno solo, quello della finestra principale.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from . import hid

DRAIN_MS = 250         # frequenza con cui la pagina legge i report catturati
MAX_REPORTS = 200      # righe tenute in memoria (la cattura completa va salvata)


class HidLab(QObject):
    nodesChanged = Signal()
    nodeChanged = Signal()
    reportsChanged = Signal()
    capturingChanged = Signal()

    _nodesReady = Signal(object)
    _grantReady = Signal(bool, str)
    _toast = Signal(str, bool)

    def __init__(self, notify, parent=None):
        super().__init__(parent)
        self._notify = notify
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kogitechhub-hid")
        self._vendor = ""
        self._product = ""
        self._node = ""
        self._nodes: list = []
        self._reports: list = []
        self._capture = None
        self._timer = QTimer(self)
        self._timer.setInterval(DRAIN_MS)
        self._timer.timeout.connect(self._drain)
        self._nodesReady.connect(self._on_nodes)
        self._grantReady.connect(self._on_grant)
        self._toast.connect(self._notify)      # dal thread I/O al thread dell'interfaccia

    # ---- proprietà per QML --------------------------------------------------
    @Property("QVariantList", notify=nodesChanged)
    def nodes(self):
        return self._nodes

    @Property("QVariantList", notify=reportsChanged)
    def reports(self):
        return self._reports

    @Property(str, notify=nodeChanged)
    def node(self):
        return self._node

    @Property("QVariantMap", notify=nodeChanged)
    def nodeInfo(self):
        return self._info()

    @Property(bool, notify=capturingChanged)
    def capturing(self):
        return self._capture is not None

    # ---- avvio e aggiornamento ----------------------------------------------
    @Slot(str, str)
    def startFor(self, vendor, product):
        """Riparte da zero sul dispositivo indicato (VID/PID)."""
        self.stop()
        self._vendor, self._product = vendor or "", product or ""
        self._node = ""
        self._reports = []
        self.reportsChanged.emit()
        self.nodeChanged.emit()
        self.refresh()

    def shutdown(self) -> None:
        self.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)

    @Slot()
    def refresh(self):
        self._run(self._task_nodes)

    def _run(self, fn, *args):
        def guarded():
            try:
                fn(*args)
            except Exception as exc:                     # mai bloccare il thread I/O
                self._toast.emit(f"Errore interno: {exc}", True)
        self._pool.submit(guarded)

    def _task_nodes(self):
        vendor, product = self._vendor, self._product
        nodes = (hid.devices_for(vendor, product) if vendor and product
                 else hid.list_devices())
        self._nodesReady.emit(nodes)

    @Slot(object)
    def _on_nodes(self, nodes):
        # il nodo con report feature/output su pagina vendor è quello di
        # configurazione: va mostrato per primo ed è la scelta predefinita
        self._nodes = sorted(nodes, key=lambda n: (-hid.report_score(n), n["node"]))
        self.nodesChanged.emit()
        if not any(n["node"] == self._node for n in self._nodes):
            self._node = self._nodes[0]["node"] if self._nodes else ""
        self.nodeChanged.emit()          # aggiorna anche i permessi del nodo scelto

    def _info(self) -> dict:
        return next((n for n in self._nodes if n["node"] == self._node), {})

    # ---- nodo scelto --------------------------------------------------------
    @Slot(str)
    def selectNode(self, node):
        self.stop()
        if node != self._node:
            self._node = node
            self.nodeChanged.emit()

    # ---- cattura ------------------------------------------------------------
    @Slot()
    def toggleCapture(self):
        if self._capture is not None:
            count = len(self._reports)
            self.stop()
            self._notify(f"Cattura fermata: {count} report.")
            return
        device = self._info()
        if not device:
            self._notify("Nessun nodo hidraw selezionato.", True)
            return
        if not device["readable"]:
            self._notify("Permessi mancanti sul nodo: usa «Abilita accesso» e riprova.", True)
            return
        self._capture = hid.Capture(device["node"])
        self._capture.start()
        self._timer.start()
        self.capturingChanged.emit()
        self._notify(f"Cattura avviata su {device['node']}.")

    def stop(self) -> None:
        if self._capture is not None:
            self._capture.stop()
            self._capture = None
            self.capturingChanged.emit()
        self._timer.stop()

    def _drain(self):
        capture = self._capture
        if capture is None:
            self._timer.stop()
            return
        fresh = capture.drain()
        if capture.error:
            message = capture.error
            self.stop()
            self._notify(f"Cattura interrotta: {message}", True)
            return
        if not fresh:
            return
        self._append(fresh)

    def _append(self, entries: list) -> None:
        self._reports = (self._reports + entries)[-MAX_REPORTS:]
        self.reportsChanged.emit()

    @Slot()
    def clearReports(self):
        if self._reports:
            self._reports = []
            self.reportsChanged.emit()

    @Slot(result=str)
    def saveCapture(self):
        if not self._reports:
            self._notify("Nessun report da salvare.", True)
            return ""
        folder = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / \
            "kogitechhub" / "captures"
        name = (f"hid-{self._vendor or 'xxxx'}-{self._product or 'xxxx'}-"
                f"{time.strftime('%Y%m%d-%H%M%S')}.jsonl")
        path = folder / name
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "node": self._node, "vendor": self._vendor, "product": self._product,
                    "captured": len(self._reports)}) + "\n")
                for report in self._reports:
                    handle.write(json.dumps(report) + "\n")
        except OSError as exc:
            self._notify(f"Salvataggio non riuscito: {exc.strerror or exc}", True)
            return ""
        self._notify(f"Cattura salvata in {path}")
        return str(path)

    # ---- report: lettura e invio -------------------------------------------
    @Slot(int, int, result=bool)
    def readFeature(self, report_id, length):
        """Legge un report feature dichiarato dal dispositivo (nessuna scrittura)."""
        node = self._node
        if not node:
            self._notify("Nessun nodo hidraw selezionato.", True)
            return False
        try:
            data = hid.get_feature(node, int(report_id), int(length))
        except PermissionError:
            self._notify("Permessi mancanti sul nodo: usa «Abilita accesso» e riprova.", True)
            return False
        except (OSError, ValueError) as exc:
            self._notify(f"Lettura non riuscita: {exc}", True)
            return False
        self._append([self._entry(data, read=True)])
        self._notify(f"Letto il report feature {int(report_id)} ({len(data)} byte).")
        return True

    @Slot(str, str, result=bool)
    def sendReport(self, text, kind):
        node = self._node
        if not node:
            self._notify("Nessun nodo hidraw selezionato.", True)
            return False
        try:
            data = hid.parse_hex(text)
        except ValueError as exc:
            self._notify(f"Report non valido: {exc}.", True)
            return False
        try:
            hid.send_report(node, data, kind)
        except PermissionError:
            self._notify("Permessi mancanti sul nodo: usa «Abilita accesso» e riprova.", True)
            return False
        except (OSError, ValueError) as exc:
            self._notify(f"Invio non riuscito: {exc}", True)
            return False
        self._append([self._entry(data, sent=True)])
        self._notify(f"Report {kind} inviato a {Path(node).name}.")
        return True

    @staticmethod
    def _entry(data: bytes, sent: bool = False, read: bool = False) -> dict:
        entry = {"time": time.strftime("%H:%M:%S"), "stamp": round(time.time(), 3),
                 "length": len(data), "id": data[0], "hex": data.hex(" ")}
        if sent:
            entry["sent"] = True
        if read:
            entry["read"] = True
        return entry

    # ---- permessi (regola udev) --------------------------------------------
    @Slot()
    def grantAccess(self):
        vendor = self._vendor or self._info().get("vendorId", "")
        product = self._product or self._info().get("productId", "")
        if not vendor or not product:
            self._notify("VID/PID non disponibili per questo dispositivo.", True)
            return
        self._notify("Richiesta dei permessi: conferma nella finestra di sistema…")

        def guarded():
            try:
                ok, message = hid.grant_access(vendor, product)
            except Exception as exc:                     # mai bloccare il thread I/O
                ok, message = False, f"Errore interno: {exc}"
            self._grantReady.emit(ok, message)

        self._pool.submit(guarded)

    @Slot(bool, str)
    def _on_grant(self, ok, message):
        self._notify(message, not ok)
        if ok:
            self.refresh()      # udev ha già ricaricato le regole: rileggi i permessi
