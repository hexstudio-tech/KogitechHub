"""Test del backend OpenRGB: parsing della CLI e comandi di scrittura."""
import unittest
from pathlib import Path
from unittest import mock

from kogitechhub.backends import openrgb

SAMPLE = """0: Corsair K70 RGB MK.2
  Type:           Keyboard
  Description:    Mechanical keyboard
  Version:        1.0
  Location:       /dev/hidraw3
  Modes: Direct [Static] Breathing 'Spectrum Cycle'
  Zones: 'Keyboard Zone' Logo
  LEDs: 'Key 1' 'Key 2' 'Key 3'

1: Logitech G733
  Type:           Headset
  Modes: [Direct]
  Zones: Main
  LEDs: 'LED 1' 'LED 2'
"""


class ParseTests(unittest.TestCase):
    def test_parse_detailed_list(self):
        found = openrgb.parse_devices(SAMPLE)
        self.assertEqual([d["name"] for d in found],
                         ["Corsair K70 RGB MK.2", "Logitech G733"])

        keyboard = found[0]
        self.assertEqual(keyboard["index"], 0)
        self.assertEqual(keyboard["type"], "Keyboard")
        self.assertEqual(keyboard["kind"], "keyboard")
        self.assertEqual(keyboard["activeMode"], "Static")
        self.assertIn("Spectrum Cycle", keyboard["modes"])
        self.assertEqual(keyboard["zones"], ["Keyboard Zone", "Logo"])
        self.assertEqual(len(keyboard["leds"]), 3)
        self.assertEqual(keyboard["version"], "1.0")
        self.assertEqual(keyboard["location"], "/dev/hidraw3")

        headset = found[1]
        self.assertEqual(headset["kind"], "headset")
        self.assertEqual(headset["modes"], ["Direct"])

    def test_id_is_stable_and_readable(self):
        self.assertEqual(openrgb.device_id(0, "Corsair K70 RGB MK.2"),
                         "openrgb:0:corsair-k70-rgb-mk-2")

    def test_kind_mapping(self):
        self.assertEqual(openrgb.kind_of("Keyboard"), "keyboard")
        self.assertEqual(openrgb.kind_of("Headset Stand"), "headset")
        self.assertEqual(openrgb.kind_of("Motherboard"), "other")

    def test_empty_output(self):
        self.assertEqual(openrgb.parse_devices(""), [])

    def test_normalize_color(self):
        self.assertEqual(openrgb.normalize_color("#ff0000"), "#FF0000")
        self.assertEqual(openrgb.normalize_color("00aa55"), "#00AA55")
        self.assertIsNone(openrgb.normalize_color("#f00"))
        self.assertIsNone(openrgb.normalize_color(""))
        self.assertIsNone(openrgb.normalize_color("rosso"))


class CommandTests(unittest.TestCase):
    def test_apply_argv(self):
        argv = openrgb.apply_argv(2, {"mode": "Static", "color": "#ff0000",
                                      "brightness": 80, "speed": 40})
        self.assertEqual(argv, ["openrgb", "-d", "2", "-m", "Static", "-c", "FF0000",
                                "-b", "80", "-s", "40"])

    def test_apply_argv_clamps_and_skips_invalid(self):
        argv = openrgb.apply_argv(0, {"mode": "", "color": "boh",
                                      "brightness": 300, "speed": -5})
        self.assertEqual(argv, ["openrgb", "-d", "0", "-b", "100", "-s", "0"])

    def test_modes_with_spaces_are_passed_as_one_argument(self):
        argv = openrgb.apply_argv(1, {"mode": "Spectrum Cycle", "color": None,
                                      "brightness": None, "speed": None})
        self.assertEqual(argv, ["openrgb", "-d", "1", "-m", "Spectrum Cycle"])


class StateTests(unittest.TestCase):
    def test_defaults_without_saved_values(self):
        dev = openrgb.parse_devices(SAMPLE)[0]
        with mock.patch.object(openrgb.store, "get", return_value={}):
            state = openrgb.state_of(dev)
        self.assertEqual(state["kind"], "keyboard")
        self.assertTrue(state["lighting"])
        self.assertEqual(state["mode"], "Static")
        self.assertEqual(state["color"], "#7B6CFF")
        self.assertEqual(state["brightness"], 100)
        self.assertEqual(state["ledCount"], 3)

    def test_saved_values_are_used(self):
        dev = openrgb.parse_devices(SAMPLE)[0]
        saved = {"mode": "Static", "color": "#00ff00", "brightness": 33, "speed": 12}
        with mock.patch.object(openrgb.store, "get", return_value=saved):
            state = openrgb.state_of(dev)
        self.assertEqual(state["color"], "#00FF00")
        self.assertEqual(state["brightness"], 33)
        self.assertEqual(state["speed"], 12)
        self.assertTrue(state["remembered"])


class BackendTests(unittest.TestCase):
    def test_available_reports_missing_tool(self):
        with mock.patch.object(openrgb.shutil, "which", return_value=None):
            ok, message = openrgb.OpenRGBBackend().available()
        self.assertFalse(ok)
        self.assertIn("OpenRGB", message)

    def test_apply_runs_command_and_saves(self):
        found = openrgb.parse_devices(SAMPLE)
        backend = openrgb.OpenRGBBackend()
        with mock.patch.object(openrgb, "devices", return_value=found), \
                mock.patch.object(openrgb, "_run", return_value="") as run_mock, \
                mock.patch.object(openrgb.store, "put") as put_mock, \
                mock.patch.object(openrgb.store, "get", return_value={}):
            state = backend.apply(found[0]["id"], {"mode": "Breathing",
                                                   "color": "#123456",
                                                   "brightness": 60, "speed": 30})

        run_mock.assert_called_once_with(["openrgb", "-d", "0", "-m", "Breathing",
                                          "-c", "123456", "-b", "60", "-s", "30"])
        put_mock.assert_called_once()
        self.assertEqual(put_mock.call_args.args[0], "openrgb:corsair-k70-rgb-mk-2")
        self.assertEqual(state["mode"], "Breathing")
        self.assertEqual(state["color"], "#123456")

    def test_load_unknown_device(self):
        with mock.patch.object(openrgb, "devices", return_value=[]):
            with self.assertRaises(Exception):
                openrgb.OpenRGBBackend().load("openrgb:9:nope")


class StoreTests(unittest.TestCase):
    def test_roundtrip(self):
        from tempfile import TemporaryDirectory

        from kogitechhub.core import store

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            self.assertEqual(store.get("k", path), {})
            store.put("k", {"color": "#111111", "brightness": 10}, path)
            store.put("k", {"brightness": 20}, path)
            self.assertEqual(store.get("k", path),
                             {"color": "#111111", "brightness": 20})
            self.assertEqual(store.get("altro", path), {})


if __name__ == "__main__":
    unittest.main()
