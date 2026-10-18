"""Prova la logica di Controller (debounce, scrittura, polling) con uno stub minimale di PySide6.

Non sostituisce una prova con Qt reale: verifica solo il flusso Python.
"""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


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
from kogitechhub import hid  # noqa: E402
from kogitechhub.app import Controller  # noqa: E402
from kogitechhub.backends.mock import MockBackend  # noqa: E402
from kogitechhub.core.engine import Engine  # noqa: E402


def flush(c):
    c._pool.submit(lambda: None).result()
    c.lab._pool.submit(lambda: None).result()


# Due interfacce dello stesso dispositivo: quella dei tasti (input) e quella di
# configurazione, che dichiara i report feature su pagina vendor.
HID_NODES = [
    {"node": "/dev/hidraw8", "name": "Gaming KB", "vendorId": "03f0", "productId": "094a",
     "phys": "", "exists": True, "readable": True, "writable": False,
     "reports": [{"type": "input", "id": 0, "bits": 64, "bytes": 8,
                  "pages": ["0x0001", "0x0007"], "usages": []},
                 {"type": "output", "id": 0, "bits": 8, "bytes": 1,
                  "pages": ["0x0008"], "usages": []}]},
    {"node": "/dev/hidraw9", "name": "Gaming KB", "vendorId": "03f0", "productId": "094a",
     "phys": "", "exists": True, "readable": True, "writable": False,
     "reports": [{"type": "feature", "id": 5, "bits": 40, "bytes": 5,
                  "pages": ["0xFF00"], "usages": []}]},
]
CONFIG_NODE = dict(HID_NODES[1])


class FakeCapture:
    """Sostituisce hid.Capture: nessun nodo reale, report inseriti dal test."""

    def __init__(self, node):
        self.node = node
        self.error = ""
        self.queue = []
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def drain(self):
        out = self.queue
        self.queue = []
        return out


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.mock = MockBackend()
        self.c = Controller(Engine([self.mock]))
        self.c.start(); flush(self.c)

    def tearDown(self):
        self.c.shutdown()

    def test_devices_and_open(self):
        self.assertEqual([d["name"] for d in self.c.devices],
                         ["Logitech Gaming Mouse G402", "Kogitech RGB Keyboard",
                          "Kogitech Wireless Headset", "HP USB Optical Mouse"])
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

    def test_lighting_edit_and_apply(self):
        self.c.openDevice("mock:keyboard"); flush(self.c)
        self.assertEqual(self.c.current["kind"], "keyboard")
        self.assertIn("Static", self.c.current["modes"])

        self.c.setLightingMode("Rainbow")
        self.assertTrue(self.c.setLightingColor("#ff0000"))
        self.c.setLightingBrightness(55)
        self.c.setLightingSpeed(20)
        self.assertEqual(self.c.current["color"], "#FF0000")
        self.c.commitNow(); flush(self.c)

        self.assertEqual(self.mock.lighting["mode"], "Rainbow")
        self.assertEqual(self.mock.lighting["color"], "#FF0000")
        self.assertEqual(self.mock.lighting["brightness"], 55)
        self.assertEqual(self.mock.lighting["speed"], 20)

    def test_lighting_invalid_color_is_rejected(self):
        self.c.openDevice("mock:keyboard"); flush(self.c)
        self.assertFalse(self.c.setLightingColor("zzz"))
        self.assertEqual(self.c.current["color"], "#7B6CFF")

    def test_lighting_unknown_mode_is_ignored(self):
        self.c.openDevice("mock:keyboard"); flush(self.c)
        before = self.c.current["mode"]
        self.c.setLightingMode("Non esiste")
        self.assertEqual(self.c.current["mode"], before)

    def test_headset_controls(self):
        self.c.openDevice("mock:headset"); flush(self.c)
        self.assertEqual(self.c.current["kind"], "headset")
        self.assertIn("sidetone", self.c.current["capabilities"])

        self.c.setSidetone(100)
        self.c.setHeadsetLights(False)
        self.c.setInactiveTime(10)
        self.c.commitNow(); flush(self.c)

        self.assertEqual(self.mock.headset["sidetone"], 100)
        self.assertFalse(self.mock.headset["lights"])
        self.assertEqual(self.mock.headset["inactive"], 10)

    # ---- laboratorio HID -----------------------------------------------------
    def _ids(self):
        return self.c.current["vendorId"], self.c.current["productId"]
    def _sniff(self, nodes=None, **patches):
        self.c.openDevice("mock:hp")
        flush(self.c)
        with mock.patch.object(hid, "devices_for", return_value=nodes if nodes is not None else [dict(CONFIG_NODE)]) as call, \
                mock.patch.object(hid, "send_report"):
            self.c.lab.startFor(*self._ids())
            flush(self.c)
            self._devices_for = call
        return self.c

    def test_sniffer_lists_the_nodes_of_the_device(self):
        self.c.openDevice("mock:hp"); flush(self.c)
        with mock.patch.object(hid, "devices_for", return_value=[dict(n) for n in HID_NODES]) as call:
            self.c.lab.startFor(*self._ids()); flush(self.c)
        call.assert_called_once_with("03f0", "094a")
        self.c.showSniffer()                    # il clic sul bottone apre la pagina
        self.assertEqual(self.c.page, "sniff")
        self.assertEqual(len(self.c.lab.nodes), 2)
        self.assertEqual([n["node"] for n in self.c.lab.nodes],
                         ["/dev/hidraw9", "/dev/hidraw8"])   # prima l'interfaccia di configurazione
        self.assertEqual(self.c.lab.node, "/dev/hidraw9")
        self.assertEqual(self.c.lab.nodeInfo["vendorId"], "03f0")
        self.assertEqual(self.c.lab.nodeInfo["reports"][0]["type"], "feature")
        self.assertFalse(self.c.lab.capturing)

        self.c.lab.selectNode("/dev/hidraw8")
        self.assertEqual(self.c.lab.node, "/dev/hidraw8")
        self.assertEqual(self.c.lab.nodeInfo["reports"][0]["type"], "input")

    def test_capture_refuses_a_node_without_permissions(self):
        self._sniff([dict(CONFIG_NODE, readable=False)])
        self.c.lab.toggleCapture()
        self.assertFalse(self.c.lab.capturing)
        self.assertTrue(self.c.toastIsError)
        self.assertIn("Permessi", self.c.toast)

    def test_capture_and_send_reports(self):
        with mock.patch.object(hid, "devices_for", return_value=[dict(CONFIG_NODE, writable=True)]), \
                mock.patch.object(hid, "Capture", FakeCapture), \
                mock.patch.object(hid, "send_report") as sender:
            self.c.openDevice("mock:hp"); flush(self.c)
            self.c.lab.startFor(*self._ids()); flush(self.c)

            self.c.lab.toggleCapture()
            self.assertTrue(self.c.lab.capturing)
            self.c.lab._capture.queue.append({"time": "12:00:00", "stamp": 1.0,
                                              "length": 4, "id": 5, "hex": "05 01 02 03"})
            self.c.lab._drain()
            self.assertEqual(len(self.c.lab.reports), 1)
            self.assertNotIn("sent", self.c.lab.reports[0])

            self.assertTrue(self.c.lab.sendReport("05 01 02 03", "output"))
            sender.assert_called_once_with("/dev/hidraw9", b"\x05\x01\x02\x03", "output")
            self.assertEqual(len(self.c.lab.reports), 2)
            self.assertTrue(self.c.lab.reports[-1]["sent"])

            self.c.lab.toggleCapture()
            self.assertFalse(self.c.lab.capturing)
            self.assertIn("Cattura fermata", self.c.toast)

            self.c.lab.clearReports()
            self.assertEqual(self.c.lab.reports, [])

    def test_capture_error_stops_and_notifies(self):
        self._sniff([dict(CONFIG_NODE, writable=True)])
        with mock.patch.object(hid, "Capture", FakeCapture):
            self.c.lab.toggleCapture()
            self.c.lab._capture.error = "/dev/hidraw9: Permission denied"
            self.c.lab._drain()
        self.assertFalse(self.c.lab.capturing)
        self.assertIn("Cattura interrotta", self.c.toast)

    def test_read_feature_appends_a_read_row(self):
        self._sniff([dict(CONFIG_NODE, writable=True)])
        with mock.patch.object(hid, "get_feature", return_value=b"\x09\x01\x02") as reader:
            self.assertTrue(self.c.lab.readFeature(9, 3))
        reader.assert_called_once_with("/dev/hidraw9", 9, 3)
        self.assertEqual(self.c.lab.reports[-1]["read"], True)
        self.assertEqual(self.c.lab.reports[-1]["hex"], "09 01 02")
        self.assertIn("Letto il report feature 9", self.c.toast)

    def test_read_feature_errors_are_reported(self):
        self._sniff([dict(CONFIG_NODE)])
        with mock.patch.object(hid, "get_feature", side_effect=PermissionError("no")):
            self.assertFalse(self.c.lab.readFeature(9, 3))
        self.assertIn("Permessi", self.c.toast)
        with mock.patch.object(hid, "get_feature", side_effect=OSError("rotto")):
            self.assertFalse(self.c.lab.readFeature(9, 3))
        self.assertIn("Lettura non riuscita", self.c.toast)

    def test_send_rejects_invalid_payload(self):
        self._sniff()
        self.assertFalse(self.c.lab.sendReport("zz", "output"))
        self.assertTrue(self.c.toastIsError)
        self.assertIn("Report non valido", self.c.toast)

    def test_send_reports_permission_errors(self):
        self._sniff()
        with mock.patch.object(hid, "send_report", side_effect=PermissionError("no")):
            self.assertFalse(self.c.lab.sendReport("05", "output"))
        self.assertIn("Permessi", self.c.toast)

    def test_save_capture_writes_jsonl(self):
        folder = tempfile.TemporaryDirectory()
        try:
            self.c.openDevice("mock:hp"); flush(self.c)
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": folder.name}), \
                    mock.patch.object(hid, "devices_for", return_value=[dict(CONFIG_NODE)]), \
                    mock.patch.object(hid, "send_report"):
                self.c.lab.startFor(*self._ids()); flush(self.c)
                self.assertTrue(self.c.lab.sendReport("05 01", "feature"))
                path = self.c.lab.saveCapture()

            self.assertTrue(path.startswith(folder.name))
            lines = Path(path).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["product"], "094a")
            self.assertEqual(json.loads(lines[0])["captured"], 1)
            self.assertEqual(json.loads(lines[1])["hex"], "05 01")
        finally:
            folder.cleanup()

    def test_save_capture_without_reports_notifies(self):
        self._sniff()
        self.assertEqual(self.c.lab.saveCapture(), "")
        self.assertIn("Nessun report", self.c.toast)

    def test_grant_access_reports_the_outcome(self):
        self.c.openDevice("mock:hp"); flush(self.c)
        with mock.patch.object(hid, "devices_for", return_value=[dict(CONFIG_NODE, readable=False)]), \
                mock.patch.object(hid, "grant_access", return_value=(True, "regola udev installata")) as grant:
            self.c.lab.startFor(*self._ids()); flush(self.c)
            self.c.lab.grantAccess(); flush(self.c)
        grant.assert_called_once_with("03f0", "094a")
        self.assertEqual(self.c.toast, "regola udev installata")
        self.assertFalse(self.c.toastIsError)

    def test_grant_failure_is_signalled(self):
        self.c.openDevice("mock:hp"); flush(self.c)
        with mock.patch.object(hid, "devices_for", return_value=[dict(CONFIG_NODE)]), \
                mock.patch.object(hid, "grant_access", side_effect=RuntimeError("boom")):
            self.c.lab.startFor(*self._ids()); flush(self.c)
            self.c.lab.grantAccess(); flush(self.c)
        self.assertTrue(self.c.toastIsError)
        self.assertIn("boom", self.c.toast)

    def test_leaving_the_sniffer_stops_the_capture_and_the_polling(self):
        self._sniff([dict(CONFIG_NODE, writable=True)])
        with mock.patch.object(hid, "Capture", FakeCapture), \
                mock.patch.object(hid, "devices_for", return_value=[dict(CONFIG_NODE)]) as call:
            self.c.lab.toggleCapture()
            self.assertTrue(self.c.lab.capturing)
            self.c._poll()                       # sulla pagina HID il polling dei mouse è sospeso
            call.assert_not_called()
            self.c.goBack()
        self.assertFalse(self.c.lab.capturing)
        self.assertEqual(self.c.page, "dashboard")


if __name__ == "__main__":
    unittest.main()
