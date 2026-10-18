import unittest

from kogitechhub.core import model
from kogitechhub.backends.base import build_state, plan_ops, BackendError


def make_state():
    allowed = list(range(200, 4001, 50))
    slots = [{"dpi": d, "enabled": i < 4, "active": i == 1, "default": i == 1, "allowed": allowed}
             for i, d in enumerate([400, 800, 1600, 3200, 2000])]
    return build_state(dev_id="mock:g402", backend="mock", name="G402", vendor_id="046d",
                       product_id="c07e", slots=slots, can_disable=True,
                       rates=[125, 250, 500, 1000], rate=1000)


class ModelTests(unittest.TestCase):
    def test_build_state(self):
        st = make_state()
        self.assertEqual([p["dpi"] for p in st["presets"]], [400, 800, 1600, 3200])
        self.assertEqual(st["maxPresets"], 5)
        self.assertTrue(st["canResize"])
        self.assertEqual((st["dpiMin"], st["dpiMax"]), (200, 4000))
        self.assertEqual(st["vendor"], "Logitech")

    def test_snap(self):
        st = make_state()
        self.assertEqual(model.snap(st, 1234), 1250)
        self.assertEqual(model.snap(st, 10), 200)
        self.assertEqual(model.snap(st, 99999), 4000)

    def test_set_dpi_reorders_and_keeps_flags(self):
        st = make_state()                       # 800 attivo e di avvio (indice 1)
        new = model.set_dpi(st, 1, 2000)        # sorpassa 1600
        self.assertEqual(new, 2)
        self.assertEqual([p["dpi"] for p in st["presets"]], [400, 1600, 2000, 3200])
        self.assertTrue(st["presets"][2]["active"] and st["presets"][2]["default"])

    def test_set_dpi_collision_is_ignored(self):
        st = make_state()
        self.assertEqual(model.set_dpi(st, 1, 1600), 1)
        self.assertEqual(st["presets"][1]["dpi"], 800)

    def test_set_dpi_typed_uses_device_supported_value(self):
        st = make_state()                       # griglia del mock: multipli di 50
        model.set_dpi(st, 1, 1234, exact=True)  # 1234 non esiste sul dispositivo
        self.assertEqual(st["presets"][1]["dpi"], 1250)
        model.set_dpi(st, 1, 1250, exact=True)  # questo esiste: scritto come digitato
        self.assertEqual(st["presets"][1]["dpi"], 1250)

    def test_set_dpi_typed_on_logitech_grid(self):
        """Il G402 supporta solo 252/302/... : digitare 1600 deve scrivere 1602,
        altrimenti il mouse ignora la scrittura e torna al valore precedente."""
        st = make_state()
        st["dpiList"] = [252 + 50 * i for i in range(12)] + [1602, 3202]
        st["dpiMin"], st["dpiMax"] = st["dpiList"][0], st["dpiList"][-1]
        st["presets"] = [{"dpi": 402, "active": True, "default": True},
                         {"dpi": 1602, "active": False, "default": False}]
        model.set_dpi(st, 0, 1600, exact=True)
        self.assertIn(1602, [p["dpi"] for p in st["presets"]])
        model.set_dpi(st, 1, 1602, exact=True)
        self.assertIn(1602, [p["dpi"] for p in st["presets"]])

    def test_set_dpi_typed_without_device_list(self):
        st = make_state()
        st["dpiList"] = []                        # il dispositivo non elenca valori
        model.set_dpi(st, 0, 1234, exact=True)
        self.assertIn(1234, [p["dpi"] for p in st["presets"]])

    def test_add_and_remove(self):
        st = make_state()
        idx = model.add_preset(st, 2000)
        self.assertEqual(idx, 3)
        self.assertTrue(st["presets"][3]["active"])
        self.assertEqual(sum(p["active"] for p in st["presets"]), 1)
        self.assertEqual(model.add_preset(st, 2500), -1)        # slot esauriti (5)
        self.assertTrue(model.remove_preset(st, 3))
        self.assertTrue(st["presets"][2]["active"])             # ripiega sul precedente
        self.assertEqual(len(st["presets"]), 4)

    def test_remove_default_reassigns(self):
        st = make_state()
        model.remove_preset(st, 1)
        self.assertEqual(sum(p["default"] for p in st["presets"]), 1)
        self.assertEqual(sum(p["active"] for p in st["presets"]), 1)

    def test_cannot_remove_last(self):
        st = make_state()
        while model.remove_preset(st, 0):
            pass
        self.assertEqual(len(st["presets"]), 1)

    def test_fixed_slots_cannot_resize(self):
        st = make_state()
        st["canResize"] = False
        self.assertEqual(model.add_preset(st, 2500), -1)
        self.assertFalse(model.remove_preset(st, 0))

    def test_rate_and_nudge_and_default(self):
        st = make_state()
        self.assertTrue(model.set_rate(st, 500))
        self.assertFalse(model.set_rate(st, 333))
        self.assertEqual(st["reportRate"], 500)
        model.nudge(st, 1)
        self.assertEqual(st["presets"][1]["dpi"], 850)
        model.set_default(st, 3)
        self.assertEqual([p["default"] for p in st["presets"]], [False, False, False, True])

    def test_restore_defaults(self):
        st = make_state()
        model.set_rate(st, 125)
        model.restore_defaults(st)
        self.assertEqual([p["dpi"] for p in st["presets"]], [400, 800, 1600, 3200])
        self.assertEqual([p["default"] for p in st["presets"]], [False, True, False, False])
        self.assertEqual(st["reportRate"], 1000)

    def test_restore_defaults_on_logitech_grid(self):
        """Su una griglia Logitech i valori di fabbrica vengono adattati:
        scrivere 400/1600 su un G402 sarebbe ignorato dal mouse."""
        st = make_state()
        st["dpiList"] = [252 + 50 * i for i in range(76)]   # 252 ... 4002
        st["dpiMin"], st["dpiMax"] = st["dpiList"][0], st["dpiList"][-1]
        model.restore_defaults(st)
        self.assertEqual([p["dpi"] for p in st["presets"]], [402, 802, 1602, 3202])

    def test_restore_defaults_fixed_slots(self):
        st = make_state()
        st["canResize"] = False
        st["presets"].append({"dpi": 2000, "active": False, "default": False})
        model.restore_defaults(st)
        self.assertEqual(len(st["presets"]), 5)
        self.assertEqual(len({p["dpi"] for p in st["presets"]}), 5)

    def test_plan_ops(self):
        st = make_state()
        slots = [{"dpi": d, "enabled": i < 4, "active": i == 1, "default": i == 1}
                 for i, d in enumerate([400, 800, 1600, 3200, 2000])]
        # nessuna modifica -> nessuna operazione
        self.assertEqual(plan_ops(slots, True, model.desired(st)["presets"], 1000, 1000), [])
        model.remove_preset(st, 3)               # 3200 rimosso
        model.select(st, 2)
        ops = plan_ops(slots, True, model.desired(st)["presets"], 500, 1000)
        self.assertEqual(ops, [("active", 2), ("enable", 3, False), ("rate", 500)])
        with self.assertRaises(BackendError):
            plan_ops(slots, False, model.desired(st)["presets"], 500, 1000)


if __name__ == "__main__":
    unittest.main()
