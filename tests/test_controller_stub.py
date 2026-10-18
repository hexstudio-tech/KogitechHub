"""Prova la logica di Controller (debounce, scrittura, polling) con uno stub minimale di PySide6.

Non sostituisce una prova con Qt reale: verifica solo il flusso Python.
"""
import sys
import types
import unittest


def install_stubs():
    class Signal:
        def __init__(self, *a):
            self.slots = []
        def __set_name__(self, owner, name):
            self.name = name
        def __get__(self, obj, owner=None):
            if obj is None:
                return self
            bound = obj.__dict__.setdefault("_sig_" + self.name, BoundSignal())
            return bound

    class BoundSignal:
        def __init__(self):
            self.slots = []
        def connect(self, fn):
            self.slots.append(fn)
        def emit(self, *a):
            for s in list(self.slots):
                s(*a)

    def Slot(*a, **k):
        return lambda f: f

    def Property(typ, fget=None, notify=None, constant=False):
        return lambda f: property(f)

    class QObject:
        def __init__(self, *a):
            pass

    class QTimer:
        def __init__(self, parent=None):
            self.timeout = BoundSignal(); self.running = False; self.interval = 0
        def setSingleShot(self, v): pass
        def setInterval(self, v): self.interval = v
        def start(self): self.running = True
        def stop(self): self.running = False

    core = types.ModuleType("PySide6.QtCore")
    core.Property, core.QObject, core.QTimer, core.QUrl, core.Signal, core.Slot = Property, QObject, QTimer, object, Signal, Slot
    gui = types.ModuleType("PySide6.QtGui"); gui.QGuiApplication = object; gui.QIcon = object
    qml = types.ModuleType("PySide6.QtQml"); qml.QQmlApplicationEngine = object
    pkg = types.ModuleType("PySide6")
    sys.modules.update({"PySide6": pkg, "PySide6.QtCore": core, "PySide6.QtGui": gui, "PySide6.QtQml": qml})


install_stubs()
from kogitechhub.app import Controller  # noqa: E402
from kogitechhub.backends.mock import MockBackend  # noqa: E402
from kogitechhub.core.engine import Engine  # noqa: E402


def flush(c):
    c._pool.submit(lambda: None).result()


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.mock = MockBackend()
        self.c = Controller(Engine([self.mock]))
        self.c.start(); flush(self.c)

    def tearDown(self):
        self.c.shutdown()

    def test_devices_and_open(self):
        self.assertEqual([d["name"] for d in self.c.devices],
                         ["Logitech Gaming Mouse G402", "HP USB Optical Mouse"])
        self.c.openDevice("mock:g402"); flush(self.c)
        self.assertEqual(self.c.page, "device")
        self.assertEqual([p["dpi"] for p in self.c.current["presets"]], [400, 800, 1600, 3200])
        self.c.openDevice("mock:hp"); flush(self.c)
        self.assertFalse(self.c.current["configurable"])

    def test_edit_debounce_and_commit(self):
        self.c.openDevice("mock:g402"); flush(self.c)
        idx = self.c.setDpi(1, 1000)
        self.assertEqual(idx, 1)
        self.assertTrue(self.c.syncing)
        self.assertTrue(self.c._commit_timer.running)
        self.assertEqual(self.mock.commits, 0)               # ancora nessuna scrittura
        self.c.commitNow(); flush(self.c)
        self.assertEqual(self.mock.commits, 1)
        self.assertFalse(self.c.syncing)
        self.assertEqual(self.mock.slots[1]["dpi"], 1000)
        self.assertEqual([p["dpi"] for p in self.c.current["presets"]], [400, 1000, 1600, 3200])

    def test_add_remove_default_rate(self):
        self.c.openDevice("mock:g402"); flush(self.c)
        self.assertEqual(self.c.addPresetAuto(), 3)           # tra 1600 e 3200 (gap più largo)
        self.c.setDefaultPreset(0)
        self.c.setReportRate(250)
        self.assertFalse(self.c.setReportRate.__self__ is None)
        self.c.commitNow(); flush(self.c)
        cur = self.c.current
        self.assertEqual(len(cur["presets"]), 5)
        self.assertEqual([p["default"] for p in cur["presets"]], [True, False, False, False, False])
        self.assertTrue(cur["presets"][3]["active"])
        self.assertEqual(self.mock.rate, 250)
        self.assertTrue(self.c.removePreset(3))
        self.c.commitNow(); flush(self.c)
        self.assertEqual(len(self.c.current["presets"]), 4)
        self.assertEqual(sum(p["active"] for p in self.c.current["presets"]), 1)

    def test_poll_picks_up_hardware_change_when_clean(self):
        self.c.openDevice("mock:g402"); flush(self.c)
        self.mock.slots[1]["active"] = False
        self.mock.slots[2]["active"] = True                   # tasto DPI premuto sul mouse
        self.c._poll(); flush(self.c)
        self.assertTrue(self.c.current["presets"][2]["active"])

    def test_poll_does_not_clobber_pending_edit(self):
        self.c.openDevice("mock:g402"); flush(self.c)
        self.c.setDpi(0, 300)
        self.c._poll(); flush(self.c)
        self.assertEqual(self.c.current["presets"][0]["dpi"], 300)

    def test_readonly_is_not_editable(self):
        self.c.openDevice("mock:hp"); flush(self.c)
        self.assertEqual(self.c.setDpi(0, 500), 0)
        self.assertFalse(self.c.syncing)

    def test_restore_defaults(self):
        self.c.openDevice("mock:g402"); flush(self.c)
        self.c.setReportRate(125); self.c.commitNow(); flush(self.c)
        self.c.restoreDefaults(); flush(self.c)
        self.assertEqual(self.mock.rate, 1000)
        self.assertEqual(self.c.current["reportRate"], 1000)


if __name__ == "__main__":
    unittest.main()
