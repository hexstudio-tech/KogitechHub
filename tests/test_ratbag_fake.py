"""Prova il backend ratbag reale contro un finto ratbagd su un bus di sessione.

Esecuzione:  dbus-run-session -- python3 -m unittest tests.test_ratbag_fake
"""
import os
import subprocess
import sys
import unittest

os.environ["KOGITECHHUB_BUS"] = "session"

from kogitechhub.backends.ratbag import RatbagBackend
from kogitechhub.core import model
from kogitechhub.core.engine import Engine
from kogitechhub.backends.sysinput import SysInputBackend

HERE = os.path.dirname(__file__)


class RatbagFakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_ratbagd.py")],
                                    stdout=subprocess.PIPE, text=True)
        assert cls.proc.stdout.readline().strip() == "READY"
        cls.backend = RatbagBackend()

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait()

    def test_01_available_and_list(self):
        self.assertEqual(self.backend.available(), (True, ""))
        devs = self.backend.list()
        self.assertEqual(len(devs), 1)
        d = devs[0]
        self.assertEqual((d["name"], d["vendorId"], d["productId"]), ("Logitech Gaming Mouse G402", "046d", "c07e"))
        self.assertTrue(d["configurable"])
        self.assertEqual((d["dpi"], d["reportRate"], d["presetCount"]), (800, 1000, 4))

    def test_02_load_state(self):
        st = self.backend.load(self.backend.list()[0]["id"])
        self.assertEqual([p["dpi"] for p in st["presets"]], [400, 800, 1600, 3200])
        self.assertEqual(st["maxPresets"], 5)
        self.assertTrue(st["canResize"])
        self.assertEqual(st["reportRates"], [125, 250, 500, 1000])
        self.assertEqual((st["dpiMin"], st["dpiMax"]), (200, 4000))

    def test_03_apply_roundtrip(self):
        dev_id = self.backend.list()[0]["id"]
        st = self.backend.load(dev_id)
        idx = model.add_preset(st, 2000)               # nuovo preset attivo, in slot 4 abilitato
        model.set_default(st, idx)
        model.set_rate(st, 500)
        model.set_dpi(st, 0, 300)
        out = self.backend.apply(dev_id, model.desired(st))
        self.assertEqual([p["dpi"] for p in out["presets"]], [300, 800, 1600, 2000, 3200])
        self.assertEqual([p["active"] for p in out["presets"]], [False, False, False, True, False])
        self.assertEqual([p["default"] for p in out["presets"]], [False, False, False, True, False])
        self.assertEqual(out["reportRate"], 500)

    def test_04_remove_and_noop(self):
        dev_id = self.backend.list()[0]["id"]
        st = self.backend.load(dev_id)
        model.remove_preset(st, 4)
        model.remove_preset(st, 0)
        out = self.backend.apply(dev_id, model.desired(st))
        self.assertEqual(len(out["presets"]), 3)
        self.assertEqual(sum(p["active"] for p in out["presets"]), 1)
        self.assertEqual(sum(p["default"] for p in out["presets"]), 1)
        again = self.backend.apply(dev_id, model.desired(out))     # nessuna differenza
        self.assertEqual(again["presets"], out["presets"])

    def test_05_engine_merges_readonly(self):
        sysb = SysInputBackend(path=os.path.join(HERE, "proc_sample.txt"))
        eng = Engine([self.backend, sysb])
        devices, status = eng.devices()
        names = [d["name"] for d in devices]
        self.assertEqual(names[0], "Logitech Gaming Mouse G402")       # configurabile prima
        self.assertEqual(sum(1 for d in devices if d["vendorId"] == "046d" and d["productId"] == "c07e"), 1)
        self.assertIn("PixArt HP USB Optical Mouse", names)
        self.assertTrue(all(s["ok"] for s in status))


if __name__ == "__main__":
    unittest.main()
