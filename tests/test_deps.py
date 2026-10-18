"""Test del rilevamento della distribuzione e dei comandi di installazione."""
import tempfile
import unittest
from pathlib import Path

from kogitechhub import deps


def os_release(text: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".os-release", delete=False)
    handle.write(text)
    handle.close()
    return Path(handle.name)


class DepsTests(unittest.TestCase):
    def check(self, text, family, package_command):
        path = os_release(text)
        try:
            d = deps.detect_distro(path)
            self.assertEqual(d.family, family)
            self.assertEqual(d.package_command, package_command)
            return d
        finally:
            path.unlink()

    def test_detect_fedora(self):
        self.check('ID=fedora\nID_LIKE=rhel fedora\nPRETTY_NAME="Fedora Linux 44"\n',
                   "rpm", "sudo dnf install")

    def test_detect_debian_family(self):
        for text in ('ID=debian\nPRETTY_NAME="Debian GNU/Linux 13"\n',
                     'ID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 24.04"\n',
                     'ID=linuxmint\nID_LIKE="ubuntu debian"\nPRETTY_NAME="Mint 22"\n',
                     'ID=mobian\nID_LIKE=debian\nPRETTY_NAME="Mobian"\n'):
            with self.subTest(text=text.splitlines()[0]):
                self.check(text, "deb", "sudo apt install")

    def test_detect_arch_and_opensuse(self):
        self.check('ID=arch\nPRETTY_NAME="Arch Linux"\n', "pacman", "sudo pacman -S")
        self.check('ID="opensuse-tumbleweed"\nID_LIKE="opensuse suse"\n', "zypper",
                   "sudo zypper install")

    def test_detect_unknown(self):
        path = os_release("ID=weirdos\n")
        try:
            d = deps.detect_distro(path)
            self.assertEqual(d.family, "unknown")
            self.assertFalse(d.known)
        finally:
            path.unlink()

    def test_install_commands_per_distro(self):
        deb = deps.Distro("debian", "Debian", "deb", "sudo apt install")
        self.assertEqual(deps.install_command("ratbagd", deb), "sudo apt install ratbagd")
        self.assertEqual(deps.install_command("gobject", deb), "sudo apt install python3-gi")
        self.assertEqual(deps.install_command("pyside6", deb), "sudo apt install python3-pyside6")

        rpm = deps.Distro("fedora", "Fedora", "rpm", "sudo dnf install")
        self.assertEqual(deps.install_command("ratbagd", rpm), "sudo dnf install libratbag-ratbagd")
        self.assertEqual(deps.install_command("gobject", rpm), "sudo dnf install python3-gobject")

        pacman = deps.Distro("arch", "Arch", "pacman", "sudo pacman -S")
        self.assertEqual(deps.install_command("ratbagd", pacman), "sudo pacman -S ratbagd")

    def test_hint_combines_packages_and_offers_pip(self):
        deb = deps.Distro("debian", "Debian", "deb", "sudo apt install")
        lines = deps.install_hint(["pyside6", "gobject", "ratbagd"], deb)
        self.assertEqual(lines[0].strip(), "sudo apt install python3-pyside6 python3-gi ratbagd")
        self.assertTrue(any("pip install --user PySide6" in line for line in lines))

    def test_ratbagd_hint_mentions_systemctl(self):
        deb = deps.Distro("debian", "Debian", "deb", "sudo apt install")
        hint = deps.ratbagd_hint("servizio non raggiungibile", deb)
        self.assertIn("apt install ratbagd", hint)
        self.assertIn("systemctl enable --now ratbagd", hint)
        self.assertIn("servizio non raggiungibile", hint)


if __name__ == "__main__":
    unittest.main()
