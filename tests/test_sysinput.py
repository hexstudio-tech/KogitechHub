import tempfile
import unittest
from pathlib import Path

from kogitechhub.backends.sysinput import (SysInputBackend, parse_proc,
                                           parse_serial_ports)

SAMPLE = '''I: Bus=0003 Vendor=046d Product=c07e Version=0111
N: Name="Logitech Gaming Mouse G402"
H: Handlers=mouse1 event5

I: Bus=0003 Vendor=046d Product=c07e Version=0111
N: Name="Logitech Gaming Mouse G402 Keyboard"
H: Handlers=sysrq kbd event6

I: Bus=0003 Vendor=03f0 Product=094a Version=0111
N: Name="PixArt HP USB Optical Mouse"
H: Handlers=mouse2 event7

I: Bus=0019 Vendor=0000 Product=0001 Version=0000
N: Name="Power Button"
H: Handlers=kbd event0

I: Bus=0000 Vendor=0000 Product=0000 Version=0000
N: Name="Virtual mouse"
H: Handlers=mouse3 event9

I: Bus=0003 Vendor=046d Product=c534 Version=0111
N: Name="Logitech USB Receiver Mouse"
H: Handlers=mouse4 event10

I: Bus=0003 Vendor=19f7 Product=0003 Version=0110
N: Name="RODE Microphones RODE NT-USB Consumer Control"
H: Handlers=kbd event2

I: Bus=0003 Vendor=beef Product=dead Version=0111
N: Name="Mouse passthrough"
S: Sysfs=/devices/virtual/input/input27
H: Handlers=event21 mouse2
'''

KEYBOARD = '''I: Bus=0003 Vendor=258a Product=002a Version=0111
N: Name="SINO WEALTH Gaming KB "
H: Handlers=sysrq kbd leds event3

I: Bus=0003 Vendor=258a Product=002a Version=0111
N: Name="SINO WEALTH Gaming KB  System Control"
H: Handlers=kbd event4

I: Bus=0003 Vendor=258a Product=002a Version=0111
N: Name="SINO WEALTH Gaming KB  Consumer Control"
H: Handlers=kbd event5

I: Bus=0003 Vendor=258a Product=002a Version=0111
N: Name="SINO WEALTH Gaming KB  Keyboard"
H: Handlers=kbd event6

I: Bus=0003 Vendor=258a Product=002a Version=0111
N: Name="SINO WEALTH Gaming KB  Mouse"
H: Handlers=event7 mouse0
'''


class SysInputTests(unittest.TestCase):
    def test_parse_mice(self):
        found = parse_proc(SAMPLE)
        self.assertEqual([(d["vendorId"], d["productId"]) for d in found],
                         [("046d", "c07e"), ("03f0", "094a"), ("046d", "c534")])
        self.assertEqual(found[1]["name"], "PixArt HP USB Optical Mouse")
        self.assertEqual(found[0]["bus"], "USB")
        self.assertEqual([d["kind"] for d in found], ["mouse", "mouse", "mouse"])

    def test_ignore_noise_and_audio(self):
        found = parse_proc(SAMPLE)
        self.assertNotIn("RODE Microphones RODE NT-USB Consumer Control",
                         [d["name"] for d in found])
        self.assertNotIn("Power Button", [d["name"] for d in found])

    def test_virtual_passthrough_is_ignored(self):
        names = [d["name"] for d in parse_proc(SAMPLE)]
        self.assertNotIn("Mouse passthrough", names)

    def test_wired_keyboard_is_detected_once(self):
        found = parse_proc(KEYBOARD)
        self.assertEqual(len(found), 1)
        keyboard = found[0]
        self.assertEqual(keyboard["kind"], "keyboard")
        self.assertEqual(keyboard["name"], "SINO WEALTH Gaming KB")
        self.assertEqual(keyboard["bus"], "USB")
        self.assertEqual(len(keyboard["interfaces"]), 5)
        self.assertIn("mouse0", keyboard["handlers"])

    def test_multi_interface_mouse_is_not_keyboard(self):
        found = parse_proc(SAMPLE)
        self.assertEqual(found[0]["name"], "Logitech Gaming Mouse G402")
        self.assertEqual(found[0]["kind"], "mouse")

    def test_serial_ports(self):
        found = parse_serial_ports(["/dev/ttyACM0", "/dev/ttyUSB1"])
        self.assertEqual([d["name"] for d in found],
                         ["Porta seriale ttyACM0", "Porta seriale ttyUSB1"])
        self.assertEqual(found[0]["kind"], "other")

    def test_backend_lists_keyboard_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "devices"
            path.write_text(KEYBOARD, encoding="utf-8")
            backend = SysInputBackend(path=str(path), patterns=())
            devices = backend.list()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["kind"], "keyboard")
        self.assertFalse(devices[0]["configurable"])
        self.assertIn("OpenRGB", devices[0]["note"])
        self.assertEqual(devices[0]["details"]["Collegamento"], "USB")

    def test_backend_lists_serial_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "devices"
            path.write_text("", encoding="utf-8")
            port = Path(tmp) / "ttyACM0"
            port.write_text("", encoding="utf-8")
            backend = SysInputBackend(path=str(path), patterns=(str(port),))
            devices = backend.list()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["kind"], "other")
        self.assertIn("Porta seriale", devices[0]["name"])


if __name__ == "__main__":
    unittest.main()
