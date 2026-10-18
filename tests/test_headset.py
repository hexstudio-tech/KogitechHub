"""Test del backend cuffie: parsing del JSON e comandi HeadsetControl."""
import json
import unittest
from unittest import mock

from kogitechhub.backends import headset

SAMPLE = json.dumps({
    "name": "HeadsetControl",
    "version": "3.0.0",
    "device_count": 1,
    "devices": [{
        "status": "success",
        "device": "Logitech G733",
        "vendor": "Logitech",
        "product": "G733",
        "id_vendor": "0x046d",
        "id_product": "0x0ab5",
        "capabilities_str": ["sidetone", "battery", "lights", "inactive time",
                             "chatmix"],
        "battery": {"status": "BATTERY_AVAILABLE", "level": 42},
        "chatmix": 48,
    }],
})


class ParseTests(unittest.TestCase):
    def test_parse_json(self):
        found = headset.parse_output(SAMPLE)
        self.assertEqual(len(found), 1)
        dev = found[0]
        self.assertEqual(dev["name"], "Logitech G733")
        self.assertEqual(dev["id"], "headset:0x046d:0x0ab5")
        self.assertEqual(dev["battery"]["level"], 42)
        self.assertEqual(dev["chatmix"], 48)
        self.assertIn("sidetone", dev["capabilities"])

    def test_broken_or_empty_output(self):
        self.assertEqual(headset.parse_output(""), [])
        self.assertEqual(headset.parse_output("non json"), [])
        self.assertEqual(headset.parse_output('{"devices": []}'), [])

    def test_id_falls_back_to_name(self):
        dev = {"device": "Cuffia USB", "id_vendor": "", "id_product": ""}
        self.assertEqual(headset.device_id(dev), "headset:cuffia-usb")


EMPTY = json.dumps({"name": "HeadsetControl", "device_count": 0, "devices": []})


class ListingTests(unittest.TestCase):
    def test_nessuna_cuffia_non_e_un_errore(self):
        done = mock.Mock(returncode=1, stdout=EMPTY, stderr="")
        headset.reset_cache()
        with mock.patch.object(headset.subprocess, "run", return_value=done), \
                mock.patch.object(headset.shutil, "which", return_value="/usr/bin/headsetcontrol"):
            self.assertEqual(headset.devices(), [])
        headset.reset_cache()

    def test_output_non_json_e_un_errore(self):
        done = mock.Mock(returncode=1, stdout="", stderr="No device found")
        headset.reset_cache()
        with mock.patch.object(headset.subprocess, "run", return_value=done), \
                mock.patch.object(headset.shutil, "which", return_value="/usr/bin/headsetcontrol"):
            with self.assertRaises(headset.BackendError):
                headset.devices()
        headset.reset_cache()


class CommandTests(unittest.TestCase):
    def test_apply_argv_only_requested(self):
        self.assertEqual(headset.apply_argv("x", {"sidetone": 64, "lights": True,
                                                  "inactive": 30}),
                         [["headsetcontrol", "-s", "64"],
                          ["headsetcontrol", "-l", "1"],
                          ["headsetcontrol", "-i", "30"]])

    def test_apply_argv_lights_off_and_clamp(self):
        self.assertEqual(headset.apply_argv("x", {"sidetone": 999, "lights": False}),
                         [["headsetcontrol", "-s", "128"],
                          ["headsetcontrol", "-l", "0"]])

    def test_apply_argv_nothing_to_do(self):
        self.assertEqual(headset.apply_argv("x", {}), [])


class StateTests(unittest.TestCase):
    def test_defaults_without_saved_values(self):
        dev = headset.parse_output(SAMPLE)[0]
        with mock.patch.object(headset.store, "get", return_value={}):
            state = headset.state_of(dev)
        self.assertEqual(state["kind"], "headset")
        self.assertTrue(state["headset"])
        self.assertEqual(state["battery"], 42)
        self.assertEqual(state["sidetone"], 0)
        self.assertTrue(state["lights"])
        self.assertIn("sidetone", state["capabilities"])
        self.assertEqual(state["inactiveChoices"], [0, 10, 30, 60])

    def test_saved_values_are_used(self):
        dev = headset.parse_output(SAMPLE)[0]
        with mock.patch.object(headset.store, "get",
                               return_value={"sidetone": 96, "lights": False,
                                             "inactive": 10}):
            state = headset.state_of(dev)
        self.assertEqual(state["sidetone"], 96)
        self.assertFalse(state["lights"])
        self.assertEqual(state["inactive"], 10)


class BackendTests(unittest.TestCase):
    def test_available_reports_missing_tool(self):
        with mock.patch.object(headset.shutil, "which", return_value=None):
            ok, message = headset.HeadsetBackend().available()
        self.assertFalse(ok)
        self.assertIn("HeadsetControl", message)

    def test_apply_runs_commands_and_saves(self):
        found = headset.parse_output(SAMPLE)
        backend = headset.HeadsetBackend()
        with mock.patch.object(headset, "devices", return_value=found), \
                mock.patch.object(headset, "_run", return_value="") as run_mock, \
                mock.patch.object(headset.store, "put") as put_mock, \
                mock.patch.object(headset.store, "get", return_value={}):
            state = backend.apply(found[0]["id"], {"sidetone": 80, "lights": True,
                                                   "inactive": 30})

        self.assertEqual([c.args[0] for c in run_mock.call_args_list],
                         [["headsetcontrol", "-s", "80"],
                          ["headsetcontrol", "-l", "1"],
                          ["headsetcontrol", "-i", "30"]])
        put_mock.assert_called_once()
        self.assertEqual(state["sidetone"], 80)

    def test_load_unknown_device(self):
        with mock.patch.object(headset, "devices", return_value=[]):
            with self.assertRaises(Exception):
                headset.HeadsetBackend().load("headset:0x1:0x2")


if __name__ == "__main__":
    unittest.main()
