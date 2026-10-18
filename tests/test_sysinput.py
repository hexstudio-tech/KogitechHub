import unittest

from kogitechhub.backends.sysinput import parse_proc

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
'''


class SysInputTests(unittest.TestCase):
    def test_parse(self):
        found = parse_proc(SAMPLE)
        self.assertEqual([(d["vendorId"], d["productId"]) for d in found],
                         [("046d", "c07e"), ("03f0", "094a"), ("046d", "c534")])
        self.assertEqual(found[1]["name"], "PixArt HP USB Optical Mouse")
        self.assertEqual(found[0]["bus"], "USB")


if __name__ == "__main__":
    unittest.main()
