"""Ponte Qt/QML: espone lo stato dei mouse all'interfaccia e serializza l'I/O su un thread."""
from __future__ import annotations

import argparse
import copy
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from . import __version__
from .backends import openrgb
from .backends.base import BackendError
from .backends.headset import HeadsetBackend
from .backends.mock import MockBackend
from .backends.openrgb import OpenRGBBackend
from .backends.ratbag import RatbagBackend
from .backends.sysinput import SysInputBackend
from .core import model
from .core.engine import Engine
from .deps import ratbagd_hint
from .hidlab import HidLab
from .theme import THEME, resolve_font_family

QML_DIR = Path(__file__).parent / "qml"
ICON = Path(__file__).parent / "qml" / "kogitechhub.svg"
COMMIT_DELAY_MS = 350      # attesa dopo l'ultima modifica prima di scrivere sul mouse
COMMIT_MAX_WAIT = 0.6      # durante un trascinamento scrive comunque ogni ~0,6 s
POLL_MS = 2000


class Controller(QObject):
    devicesChanged = Signal()
    currentChanged = Signal()
    pageChanged = Signal()
    toastChanged = Signal()
    syncingChanged = Signal()
    hintChanged = Signal()
    backendsChanged = Signal()

    _devicesReady = Signal(object)
    _stateReady = Signal(object, int)
    _applied = Signal(object, str, int)
    _failed = Signal(str)

    def __init__(self, engine: Engine):
        super().__init__()
        self._engine = engine
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kogitechhub-io")
        self._devices: list = []
        self._backends: list = []
        self._current: dict = {}
        self._page = "dashboard"
        self._toast = ""
        self._toast_error = False
        self._hint = ""
        self._dirty = False
        self._applying = False
        self._first_dirty = 0.0
        self._gen = 0
        self._open_id = ""
        self.lab = HidLab(self._notify)     # laboratorio HID (pagina di sniffing)

        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(COMMIT_DELAY_MS)
        self._commit_timer.timeout.connect(self._do_commit)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(POLL_MS)
        self._poll_timer.timeout.connect(self._poll)

        self._devicesReady.connect(self._on_devices)
        self._stateReady.connect(self._on_state)
        self._applied.connect(self._on_applied)
        self._failed.connect(self._on_failed)

    # ---- proprietà per QML ------------------------------------------------
    @Property("QVariantList", notify=devicesChanged)
    def devices(self):
        return self._devices

    @Property("QVariantList", notify=backendsChanged)
    def backends(self):
        return self._backends

    @Property("QVariantMap", notify=currentChanged)
    def current(self):
        return self._current

    @Property(str, notify=pageChanged)
    def page(self):
        return self._page

    @Property(str, notify=toastChanged)
    def toast(self):
        return self._toast

    @Property(bool, notify=toastChanged)
    def toastIsError(self):
        return self._toast_error

    @Property(str, notify=hintChanged)
    def hint(self):
        return self._hint

    @Property(bool, notify=syncingChanged)
    def syncing(self):
        return self._dirty or self._applying

    @Property(str, constant=True)
    def version(self):
        return __version__

    # ---- avvio e polling ----------------------------------------------------
    def start(self):
        self.refresh()
        self._poll_timer.start()

    def shutdown(self):
        self._poll_timer.stop()
        self.lab.shutdown()
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _run(self, fn, *args):
        def guarded():
            try:
                fn(*args)
            except BackendError as exc:
                self._failed.emit(str(exc))
            except Exception as exc:  # errori imprevisti: mai bloccare il thread I/O
                self._failed.emit(f"Errore interno: {exc}")
        self._pool.submit(guarded)

    @Slot()
    def refresh(self):
        self._run(self._task_devices)

    def _poll(self):
        if self._applying or self._dirty or self._page == "sniff":
            return
        if self._page == "device" and self._open_id:
            self._run(self._task_load, self._open_id, self._gen)
        else:
            self._run(self._task_devices)

    # ---- compiti sul thread I/O ---------------------------------------------
    def _task_devices(self):
        devices, status = self._engine.devices()
        self._devicesReady.emit({"devices": devices, "status": status})

    def _task_load(self, dev_id, gen):
        self._stateReady.emit(self._engine.load(dev_id), gen)

    def _task_apply(self, dev_id, desired, gen):
        try:
            state = self._engine.apply(dev_id, desired)
        except BackendError as exc:
            self._applied.emit({}, str(exc), gen)
            return
        self._applied.emit(state, "", gen)

    # ---- risultati sul thread principale ------------------------------------
    @Slot(object)
    def _on_devices(self, payload):
        devices, status = payload["devices"], payload["status"]
        if devices != self._devices:
            self._devices = devices
            self.devicesChanged.emit()
        if status != self._backends:
            self._backends = status
            self.backendsChanged.emit()
        bad = next((s for s in status if s["id"] == "ratbag" and not s["ok"]), None)
        hint = ratbagd_hint(bad["message"]) if bad else ""
        if hint != self._hint:
            self._hint = hint
            self.hintChanged.emit()

    @Slot(object, int)
    def _on_state(self, state, gen):
        if gen != self._gen or self._dirty or self._applying:
            return
        self._set_current(state)

    @Slot(object, str, int)
    def _on_applied(self, state, error, gen):
        self._applying = False
        self.syncingChanged.emit()
        if gen != self._gen:
            return
        if error:
            self._notify(error, True)
            self._dirty = False
            self._run(self._task_load, self._open_id, self._gen)
            return
        if not self._dirty:
            self._set_current(state)

    @Slot(str)
    def _on_failed(self, message):
        self._notify(message, True)

    def _set_current(self, state):
        if state != self._current:
            self._current = state
            self.currentChanged.emit()

    def _notify(self, message, error=False):
        self._toast, self._toast_error = message, error
        self.toastChanged.emit()

    @Slot()
    def clearToast(self):
        self._toast = ""
        self.toastChanged.emit()

    # ---- navigazione ----------------------------------------------------------
    def _set_page(self, page):
        if page != self._page:
            self._page = page
            self.pageChanged.emit()

    @Slot(str)
    def openDevice(self, dev_id):
        self.lab.stop()
        self._gen += 1
        self._open_id = dev_id
        self._dirty = False
        self._commit_timer.stop()
        summary = next((d for d in self._devices if d["id"] == dev_id), {})
        self._current = {"id": dev_id, "name": summary.get("name", ""), "vendor": summary.get("vendor", ""),
                         "vendorId": summary.get("vendorId", ""), "productId": summary.get("productId", ""),
                         "kind": summary.get("kind", "other"),
                         "lighting": bool(summary.get("lighting")),
                         "headset": bool(summary.get("headset")),
                         "subtitle": summary.get("subtitle", ""),
                         "configurable": summary.get("configurable", False), "loading": True,
                         "presets": [], "reportRates": [], "details": {}, "note": ""}
        self.currentChanged.emit()
        self._set_page("device")
        self._run(self._task_load, dev_id, self._gen)

    @Slot()
    def goBack(self):
        self.lab.stop()
        self._flush_before_leaving()
        self._set_page("dashboard")
        self.refresh()

    @Slot()
    def showDevice(self):
        self.lab.stop()
        if self._open_id:
            self._set_page("device")

    @Slot()
    def showSniffer(self):
        """Apre la pagina del laboratorio HID (i nodi li carica `sniffer`)."""
        self._set_page("sniff")

    @Slot()
    def showAbout(self):
        self._flush_before_leaving()
        self._set_page("about")
        self.refresh()

    def _flush_before_leaving(self):
        if self._dirty:
            self._do_commit()

    # ---- modifiche dell'utente ---------------------------------------------
    def _editable(self):
        return bool(self._current.get("configurable")) and not self._current.get("loading")

    def _desired(self) -> dict:
        """Parte dello stato da scrivere sul dispositivo (mouse, luci o cuffia)."""
        state = self._current
        if state.get("kind") == "mouse" or state.get("presets"):
            return model.desired(state)
        if state.get("lighting"):
            return {key: state.get(key) for key in ("mode", "color", "brightness", "speed")}
        if state.get("headset"):
            return {key: state.get(key) for key in ("sidetone", "lights", "inactive")}
        return {}

    def _edit(self, fn, default=None):
        if not self._editable():
            return default
        before = copy.deepcopy(self._desired())
        result = fn(self._current)
        if before != self._desired():
            self._touch()
        return result

    def _touch(self):
        if not self._dirty:
            self._dirty = True
            self._first_dirty = time.monotonic()
            self.syncingChanged.emit()
        self.currentChanged.emit()
        if not self._applying and time.monotonic() - self._first_dirty > COMMIT_MAX_WAIT:
            self._do_commit()
        else:
            self._commit_timer.start()

    @Slot()
    def commitNow(self):
        if self._dirty:
            self._do_commit()

    def _do_commit(self):
        self._commit_timer.stop()
        if not self._dirty or not self._editable():
            return
        if self._applying:                       # una scrittura è già in corso: riprova dopo
            self._commit_timer.start()
            return
        self._dirty = False
        self._applying = True
        self.syncingChanged.emit()
        self._run(self._task_apply, self._open_id, self._desired(), self._gen)

    @Slot(int)
    def selectPreset(self, idx):
        self._edit(lambda s: model.select(s, idx))

    @Slot(int)
    def setDefaultPreset(self, idx):
        self._edit(lambda s: model.set_default(s, idx))

    @Slot(int, int, result=int)
    def setDpi(self, idx, dpi):
        return self._edit(lambda s: model.set_dpi(s, idx, dpi), idx)

    @Slot(int, int)
    def setDpiTyped(self, idx, dpi):
        """Valore digitato dall'utente.

        Viene scritto così com'è solo se il dispositivo lo supporta: molti mouse
        (Logitech G402 e simili) hanno una griglia di valori e ignorano in
        silenzio qualsiasi altro numero, quindi in quel caso si scrive il valore
        supportato più vicino e si avvisa.
        """
        wanted = int(dpi)
        new_idx = self._edit(lambda s: model.set_dpi(s, idx, wanted, exact=True), idx)
        presets = self._current.get("presets", [])
        if 0 <= new_idx < len(presets):
            written = presets[new_idx]["dpi"]
            if written != wanted:
                self._notify(f"{wanted} DPI non sono supportati da questo mouse: "
                             f"impostati {written}.")

    @Slot(int, result=int)
    def addPresetAt(self, dpi):
        return self._edit(lambda s: model.add_preset(s, dpi), -1)

    @Slot(result=int)
    def addPresetAuto(self):
        return self._edit(lambda s: model.add_preset(s, model.suggest_dpi(s)), -1)

    @Slot(int, result=bool)
    def removePreset(self, idx):
        return self._edit(lambda s: model.remove_preset(s, idx), False)

    @Slot(int)
    def setReportRate(self, hz):
        self._edit(lambda s: model.set_rate(s, hz))

    # ---- illuminazione (OpenRGB) --------------------------------------------
    @Slot(str)
    def setLightingMode(self, name):
        if name not in self._current.get("modes", []):
            return
        self._edit(lambda s: s.update(mode=name))

    @Slot(str, result=bool)
    def setLightingColor(self, value):
        color = openrgb.normalize_color(value)
        if not color:
            self._notify("Colore non valido: usa un esadecimale come #7B6CFF.", True)
            return False
        self._edit(lambda s: s.update(color=color))
        return True

    @Slot(int)
    def setLightingBrightness(self, value):
        self._edit(lambda s: s.update(brightness=max(0, min(100, int(value)))))

    @Slot(int)
    def setLightingSpeed(self, value):
        self._edit(lambda s: s.update(speed=max(0, min(100, int(value)))))

    # ---- cuffie (HeadsetControl) --------------------------------------------
    @Slot(int)
    def setSidetone(self, value):
        limit = int(self._current.get("sidetoneMax", 128))
        self._edit(lambda s: s.update(sidetone=max(0, min(limit, int(value)))))

    @Slot(bool)
    def setHeadsetLights(self, on):
        self._edit(lambda s: s.update(lights=bool(on)))

    @Slot(int)
    def setInactiveTime(self, minutes):
        choices = self._current.get("inactiveChoices") or [0, 10, 30, 60]
        if int(minutes) not in choices:
            return
        self._edit(lambda s: s.update(inactive=int(minutes)))

    @Slot(int)
    def nudge(self, delta):
        self._edit(lambda s: model.nudge(s, delta))

    @Slot()
    def restoreDefaults(self):
        before = [p["dpi"] for p in self._current.get("presets", [])]
        self._edit(lambda s: model.restore_defaults(s))
        if self._dirty:
            after = [p["dpi"] for p in self._current.get("presets", [])]
            if before != after:
                self._notify("Preset predefiniti ripristinati: "
                             + "/".join(str(d) for d in after) + " DPI.")
            else:
                self._notify("Preset predefiniti ripristinati.")
            self._do_commit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="kogitechhub",
                                     description="Configuratore per mouse su Linux")
    parser.add_argument("--mock", action="store_true", help="usa mouse simulati (senza hardware)")
    parser.add_argument("--check", action="store_true",
                        help="verifica dipendenze e servizi, poi esce")
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    if args.check:
        from .doctor import report

        text, code = report()
        print(text)
        return code

    app = QGuiApplication([sys.argv[0], *qt_args])
    app.setApplicationName("KogitechHub")
    app.setDesktopFileName("kogitechhub")
    if ICON.exists():
        app.setWindowIcon(QIcon(str(ICON)))

    backends = ([MockBackend()] if args.mock else
                [RatbagBackend(), OpenRGBBackend(), HeadsetBackend(), SysInputBackend()])
    controller = Controller(Engine(backends))

    qml = QQmlApplicationEngine()
    qml.rootContext().setContextProperty("app", controller)
    qml.rootContext().setContextProperty("sniffer", controller.lab)
    qml.rootContext().setContextProperty("theme", {**THEME, "fontFamily": resolve_font_family()})
    qml.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not qml.rootObjects():
        return 1
    controller.start()
    code = app.exec()
    controller.shutdown()
    return code
