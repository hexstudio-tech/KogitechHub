"""Finto ratbagd (dbus-python) con la stessa interfaccia D-Bus del demone reale."""
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

BUS = "org.freedesktop.ratbag1"
PROPS = "org.freedesktop.DBus.Properties"


class Obj(dbus.service.Object):
    def __init__(self, bus, path, iface, props, writable=()):
        super().__init__(bus, path)
        self.iface, self.props, self.writable = iface, props, set(writable)

    @dbus.service.method(PROPS, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return dbus.Dictionary(self.props, signature="sv") if iface == self.iface else {}

    @dbus.service.method(PROPS, in_signature="s" "s", out_signature="v")
    def Get(self, iface, name):
        return self.props[name]

    @dbus.service.method(PROPS, in_signature="ssv", out_signature="")
    def Set(self, iface, name, value):
        if name not in self.writable:
            raise dbus.exceptions.DBusException("read only", name="org.freedesktop.DBus.Error.PropertyReadOnly")
        self.props[name] = value


class Device(Obj):
    @dbus.service.method(BUS + ".Device", in_signature="", out_signature="u")
    def Commit(self):
        print("COMMIT", flush=True)
        return dbus.UInt32(0)


class Resolution(Obj):
    siblings = []

    @dbus.service.method(BUS + ".Resolution", in_signature="", out_signature="")
    def SetActive(self):
        for r in Resolution.siblings:
            r.props["IsActive"] = dbus.Boolean(r is self)

    @dbus.service.method(BUS + ".Resolution", in_signature="", out_signature="")
    def SetDefault(self):
        for r in Resolution.siblings:
            r.props["IsDefault"] = dbus.Boolean(r is self)


def main():
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    _name = dbus.service.BusName(BUS, bus)
    allowed = dbus.Array([dbus.UInt32(v) for v in range(200, 4001, 50)], signature="u")
    base = "/org/freedesktop/ratbag1"
    res_paths = []
    for i, d in enumerate([400, 800, 1600, 3200, 2000]):
        path = f"{base}/resolution/0/p0/r{i}"
        res_paths.append(dbus.ObjectPath(path))
        Resolution.siblings.append(Resolution(bus, path, BUS + ".Resolution", {
            "Index": dbus.UInt32(i),
            "Capabilities": dbus.Array([dbus.UInt32(2)], signature="u"),
            "IsActive": dbus.Boolean(i == 1), "IsDefault": dbus.Boolean(i == 1),
            "IsDisabled": dbus.Boolean(i >= 4),
            "Resolution": dbus.UInt32(d), "Resolutions": allowed},
            writable=("IsDisabled", "Resolution")))
    prof_path = f"{base}/profile/0/p0"
    Obj(bus, prof_path, BUS + ".Profile", {
        "Index": dbus.UInt32(0), "IsActive": dbus.Boolean(True),
        "Resolutions": dbus.Array(res_paths, signature="o"),
        "ReportRate": dbus.UInt32(1000),
        "ReportRates": dbus.Array([dbus.UInt32(v) for v in (125, 250, 500, 1000)], signature="u")},
        writable=("ReportRate",))
    dev_path = f"{base}/device/0"
    Device(bus, dev_path, BUS + ".Device", {
        "Id": "cheering-viscacha", "Model": "usb:046d:c07e:0",
        "Name": "Logitech Gaming Mouse G402",
        "Profiles": dbus.Array([dbus.ObjectPath(prof_path)], signature="o")})
    Obj(bus, base, BUS + ".Manager", {
        "APIVersion": dbus.Int32(1),
        "Devices": dbus.Array([dbus.ObjectPath(dev_path)], signature="o")})
    print("READY", flush=True)
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
