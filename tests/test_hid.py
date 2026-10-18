import fcntl
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from kogitechhub import hid

# Descrittore di una tastiera con un report di output a 5 byte su pagina vendor:
# è la forma tipica con cui il software del produttore configura gli RGB.
KEYBOARD_DESCRIPTOR = bytes([
    0x05, 0x01,              # Usage Page (Generic Desktop)
    0x09, 0x06,              # Usage (Keyboard)
    0xA1, 0x01,              # Collection (Application)
    0x05, 0x07,              #   Usage Page (Keyboard)
    0x19, 0xE0, 0x29, 0xE7,  #   Usage Minimum/Maximum (224..231)
    0x15, 0x00, 0x25, 0x01,  #   Logical Minimum/Maximum
    0x75, 0x01, 0x95, 0x08,  #   Report Size 1, Count 8
    0x81, 0x02,              #   Input (variabili)
    0x75, 0x08, 0x95, 0x06,  #   Report Size 8, Count 6
    0x81, 0x01,              #   Input (costanti)
    0x05, 0x07, 0x19, 0x00, 0x2A, 0xFF, 0x00,
    0x15, 0x00, 0x25, 0xFF, 0x75, 0x08, 0x95, 0x06,
    0x81, 0x00,              #   Input (tasti)
    0x85, 0x05,              #   Report ID (5)
    0x06, 0x00, 0xFF,        #   Usage Page (Vendor 0xFF00)
    0x09, 0x01,              #   Usage (1)
    0x15, 0x00, 0x26, 0xFF, 0x00,
    0x75, 0x08, 0x95, 0x05,  #   Report Size 8, Count 5
    0x91, 0x02,              #   Output (variabili) -> 5 byte, id 5
    0xC0,                    # End Collection
])

UEVENT = ("DRIVER=hid-generic\n"
          "HID_ID=0003:0000258A:0000002A\n"
          "HID_NAME=Gaming KB\n"
          "HID_PHYS=usb-0000:00:14.0-1/input0\n"
          "HID_UNIQ=\n")


class DescribeTests(unittest.TestCase):
    def test_input_and_output_reports(self):
        reports = hid.describe(KEYBOARD_DESCRIPTOR)
        self.assertEqual([(r["type"], r["id"]) for r in reports], [("input", 0), ("output", 5)])

        keyboard, lights = reports
        self.assertEqual(keyboard["bytes"], 13)          # 8 + 48 + 48 bit
        self.assertIn("0x0007", keyboard["pages"])
        self.assertEqual(lights["bytes"], 5)
        self.assertEqual(lights["pages"], ["0xFF00"])

    def test_empty_descriptor(self):
        self.assertEqual(hid.describe(b""), [])


class ParseHexTests(unittest.TestCase):
    def test_accepted_forms(self):
        self.assertEqual(hid.parse_hex("05 ff"), b"\x05\xff")
        self.assertEqual(hid.parse_hex("0x05,0xFF"), b"\x05\xff")
        self.assertEqual(hid.parse_hex("05ff00"), b"\x05\xff\x00")

    def test_rejected_forms(self):
        for bad in ("", "   ", "05f", "zz", "05 ff zz"):
            with self.assertRaises(ValueError):
                hid.parse_hex(bad)


class ListDevicesTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sysfs = self.root / "sys" / "class" / "hidraw"
        self.dev = self.root / "dev"
        self.dev.mkdir(parents=True)
        entry = self.sysfs / "hidraw2" / "device"
        entry.mkdir(parents=True)
        (entry / "uevent").write_text(UEVENT, encoding="utf-8")
        (entry / "report_descriptor").write_bytes(KEYBOARD_DESCRIPTOR)

    def tearDown(self):
        self.tmp.cleanup()

    def test_metadata_and_permissions(self):
        node = self.dev / "hidraw2"
        found = hid.list_devices(self.sysfs, self.dev)
        self.assertEqual(len(found), 1)
        device = found[0]
        self.assertEqual(device["node"], str(node))
        self.assertEqual((device["vendorId"], device["productId"]), ("258a", "002a"))
        self.assertEqual(device["name"], "Gaming KB")
        self.assertFalse(device["exists"])
        self.assertFalse(device["readable"])
        self.assertFalse(device["writable"])
        self.assertEqual([r["type"] for r in device["reports"]], ["input", "output"])

        node.write_bytes(b"")
        os.chmod(node, 0o600)
        device = hid.list_devices(self.sysfs, self.dev)[0]
        self.assertTrue(device["exists"])
        self.assertTrue(device["readable"])
        self.assertTrue(device["writable"])

    def test_devices_for_filters_by_usb_id(self):
        self.assertEqual(hid.devices_for("258a", "002a", sysfs=self.sysfs, dev=self.dev),
                         hid.list_devices(self.sysfs, self.dev))
        self.assertEqual(hid.devices_for("258a", "9999", sysfs=self.sysfs, dev=self.dev), [])


class ReportScoreTests(unittest.TestCase):
    def test_vendor_feature_interface_wins(self):
        boot = {"reports": [{"type": "input", "pages": ["0x0001", "0x0007"], "bytes": 8},
                            {"type": "output", "pages": ["0x0008"], "bytes": 1}]}
        config = {"reports": [{"type": "input", "pages": ["0x0001"], "bytes": 1},
                              {"type": "feature", "pages": ["0xFF00"], "bytes": 5}]}
        self.assertEqual(hid.report_score(boot), 0)
        self.assertGreater(hid.report_score(config), hid.report_score(boot))


class UdevTests(unittest.TestCase):
    def test_rule_matches_the_device(self):
        rule = hid.udev_rule("258A", "002A")
        self.assertIn('ATTRS{idVendor}=="258a"', rule)
        self.assertIn('ATTRS{idProduct}=="002a"', rule)
        self.assertIn('TAG+="uaccess"', rule)

    def test_invalid_ids_are_rejected(self):
        for bad in ("258", "258a1", "", "zzzz"):
            with self.assertRaises(ValueError):
                hid.udev_rule(bad, "002a")

    def test_grant_script_is_idempotent_and_reloads_udev(self):
        script = hid.grant_script("258a", "002a")
        self.assertIn(str(hid.rule_path("258a", "002a")), script)
        self.assertIn("udevadm control --reload-rules", script)
        self.assertIn("udevadm trigger --subsystem-match=hidraw", script)


class SendReportTests(unittest.TestCase):
    def test_arguments_are_validated_before_touching_the_device(self):
        with self.assertRaises(ValueError):
            hid.send_report("/dev/null", b"")
        with self.assertRaises(ValueError):
            hid.send_report("/dev/null", b"\x05", "input")


class GetFeatureTests(unittest.TestCase):
    def test_reads_through_ioctl(self):
        with mock.patch.object(fcntl, "ioctl") as ioctl:
            data = hid.get_feature("/dev/null", 9, 4)
        ioctl.assert_called_once()
        self.assertEqual(data, b"\x09\x00\x00\x00")          # primo byte = ID richiesto
        self.assertEqual(ioctl.call_args[0][1], hid.hid_ioc(0x07, 4))   # HIDIOCGFEATURE

    def test_arguments_are_validated(self):
        for report, length in ((256, 4), (-1, 4), (9, 0), (9, hid.MAX_REPORT + 1)):
            with self.assertRaises(ValueError):
                hid.get_feature("/dev/null", report, length)


class CaptureTests(unittest.TestCase):
    def test_missing_node_sets_an_error(self):
        capture = hid.Capture(str(Path(tempfile.gettempdir()) / "kogitechhub-non-esiste"))
        capture.start()
        deadline = time.monotonic() + 2
        while capture.error == "" and time.monotonic() < deadline:
            time.sleep(0.02)
        capture.stop()
        self.assertIn("kogitechhub-non-esiste", capture.error)
        self.assertFalse(capture.running)
        self.assertEqual(capture.drain(), [])


if __name__ == "__main__":
    unittest.main()
