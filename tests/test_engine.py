"""Test del motore: ordine dei tipi e rimozione dei duplicati."""
import unittest

from kogitechhub.backends.base import Backend
from kogitechhub.core.engine import Engine


class FakeBackend(Backend):
    def __init__(self, bid, devices):
        self.id = bid
        self._devices = devices

    def list(self):
        return [dict(d) for d in self._devices]

    def load(self, dev_id):
        return {}

    def apply(self, dev_id, desired):
        return {}


def device(name, kind, configurable=True, vid="", pid=""):
    return {"id": f"{kind}:{name}", "name": name, "kind": kind,
            "configurable": configurable, "vendorId": vid, "productId": pid}


class EngineTests(unittest.TestCase):
    def test_order_by_kind(self):
        backend = FakeBackend("x", [
            device("Cuffia", "headset"),
            device("Tastiera", "keyboard"),
            device("Mouse", "mouse"),
            device("Lettore", "other"),
        ])
        devices, _ = Engine([backend]).devices()
        self.assertEqual([d["kind"] for d in devices],
                         ["mouse", "keyboard", "headset", "other"])

    def test_read_only_duplicate_by_usb_id_is_hidden(self):
        ratbag = FakeBackend("ratbag", [device("Mouse G402", "mouse", vid="046d",
                                               pid="c07e")])
        system = FakeBackend("sys", [device("Mouse G402", "mouse", configurable=False,
                                            vid="046d", pid="c07e")])
        devices, _ = Engine([ratbag, system]).devices()
        self.assertEqual(len(devices), 1)

    def test_read_only_duplicate_by_name_is_hidden(self):
        # OpenRGB non espone VID/PID: il confronto per nome evita doppioni
        openrgb = FakeBackend("openrgb", [device("SINO WEALTH Gaming KB", "keyboard")])
        system = FakeBackend("sys", [device("SINO WEALTH Gaming KB", "keyboard",
                                            configurable=False, vid="258a", pid="002a")])
        devices, _ = Engine([openrgb, system]).devices()
        self.assertEqual(len(devices), 1)
        self.assertTrue(devices[0]["configurable"])

    def test_unknown_backend_is_not_hidden(self):
        system = FakeBackend("sys", [device("Tastiera", "keyboard", configurable=False)])
        devices, _ = Engine([system]).devices()
        self.assertEqual(len(devices), 1)


if __name__ == "__main__":
    unittest.main()
