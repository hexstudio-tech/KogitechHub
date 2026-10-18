"""Test dell'installer delle dipendenze: prompt Y/N, comandi, interprete."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kogitechhub import deps, installer

DEB = deps.Distro("debian", "Debian 13", "deb", "sudo apt install")
APT_PYSIDE = ["sudo", "apt", "install", "-y", "python3-pyside6"]


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


class PromptTests(unittest.TestCase):
    def ask_with(self, answers, prompter=None):
        prompter = prompter or installer.Prompter(interactive=True)
        with mock.patch("builtins.input", side_effect=answers):
            return prompter.ask("Installare?")

    def test_invio_vuoto_significa_si(self):
        self.assertIs(self.ask_with([""]), True)

    def test_risposte_accettate(self):
        for answer in ("y", "Y", "yes", "s", "sì"):
            with self.subTest(answer=answer):
                self.assertIs(self.ask_with([answer]), True)
        for answer in ("n", "N", "no", "NO"):
            with self.subTest(answer=answer):
                self.assertIs(self.ask_with([answer]), False)

    def test_richiede_finche_la_risposta_non_e_valida(self):
        with quiet():
            self.assertIs(self.ask_with(["boh", "n"]), False)

    def test_flag_yes_no_e_terminale_assente(self):
        with quiet():
            self.assertIs(installer.Prompter(assume_yes=True, interactive=False).ask("?"), True)
            self.assertIs(installer.Prompter(assume_no=True, interactive=False).ask("?"), False)
            self.assertIsNone(installer.Prompter(interactive=False).ask("?"))

    def test_eof_non_blocca(self):
        with quiet():
            self.assertIsNone(self.ask_with([EOFError]))


class DetectTests(unittest.TestCase):
    def test_mock_salta_ratbagd(self):
        with mock.patch.object(installer, "interpreter_has_pyside", return_value=True), \
                mock.patch.object(installer, "gio_ok", return_value=False), \
                mock.patch.object(installer.shutil, "which", return_value=None):
            self.assertEqual(installer.detect(mock=True), [])
            keys = [p.key for p in installer.detect(mock=False)]
        self.assertIn("ratbagd", keys)

    def test_strumenti_rgb_e_cuffie_sono_facoltativi(self):
        def which(binary):
            return "/usr/bin/ratbagd" if binary == "ratbagd" else None

        with mock.patch.object(installer, "interpreter_has_pyside", return_value=True), \
                mock.patch.object(installer, "gio_ok", return_value=True), \
                mock.patch.object(installer.shutil, "which", side_effect=which), \
                mock.patch.object(installer, "service_state", return_value="ok"):
            problems = installer.detect()
        self.assertEqual([p.key for p in problems], ["openrgb", "headsetcontrol"])
        self.assertFalse(any(p.blocking for p in problems))

    def test_pyside_e_obbligatorio(self):
        with mock.patch.object(installer, "interpreter_has_pyside", return_value=False), \
                mock.patch.object(installer, "gio_ok", return_value=True), \
                mock.patch.object(installer.shutil, "which", return_value="/usr/bin/ratbagd"), \
                mock.patch.object(installer, "service_state", return_value="ok"):
            problems = installer.detect()
        self.assertEqual([p.key for p in problems], ["pyside6"])
        self.assertTrue(problems[0].blocking)

    def test_servizio_disattivato(self):
        with mock.patch.object(installer, "interpreter_has_pyside", return_value=True), \
                mock.patch.object(installer, "gio_ok", return_value=True), \
                mock.patch.object(installer.shutil, "which", return_value="/usr/bin/ratbagd"), \
                mock.patch.object(installer, "service_state", return_value="disabled"):
            problems = installer.detect()
        self.assertEqual([p.key for p in problems], ["ratbagd-service"])


class EnsureTests(unittest.TestCase):
    def test_tutto_presente_non_stampa_nulla(self):
        out = io.StringIO()
        with mock.patch.object(installer, "detect", return_value=[]), \
                contextlib.redirect_stdout(out):
            self.assertEqual(installer.ensure(assume_no=True), 0)
        self.assertEqual(out.getvalue(), "")

    def test_rifiuto_blocca_solo_il_necessario(self):
        problem = installer.Problem("pyside6", "PySide6", True)
        out = io.StringIO()
        with mock.patch.object(installer, "detect", return_value=[problem]), \
                mock.patch.object(installer, "interpreter_has_pyside", return_value=False), \
                mock.patch.object(deps, "install_argv", return_value=APT_PYSIDE), \
                contextlib.redirect_stdout(out):
            code = installer.ensure(assume_no=True)
        self.assertEqual(code, 1)
        self.assertIn("python3-pyside6", out.getvalue())

    def test_dipendenza_opzionale_rifiutata_non_blocca(self):
        problem = installer.Problem("gobject", "PyGObject", False)
        with mock.patch.object(installer, "detect", return_value=[problem]), \
                mock.patch.object(deps, "install_argv",
                                  return_value=["sudo", "apt", "install", "-y", "python3-gi"]), \
                quiet():
            self.assertEqual(installer.ensure(assume_no=True), 0)

    def test_installa_dopo_il_si(self):
        state = {"ok": False}

        def fake_detect(python=None, *, mock=False):
            return [] if state["ok"] else [installer.Problem("pyside6", "PySide6", True)]

        def fake_run(argv):
            state["ok"] = True
            return 0

        with mock.patch.object(installer, "detect", fake_detect), \
                mock.patch.object(installer, "run", side_effect=fake_run) as run_mock, \
                mock.patch.object(installer, "interpreter_has_pyside", return_value=False), \
                mock.patch.object(installer, "pyside_ok", return_value=True), \
                mock.patch.object(deps, "install_argv", return_value=APT_PYSIDE), \
                quiet():
            code = installer.ensure(assume_yes=True)
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(APT_PYSIDE)

    def test_python_vecchio_blocca(self):
        problem = installer.Problem("python", "Python 3.10 o successivo", True, "3.9.0")
        with mock.patch.object(installer, "detect", return_value=[problem]), quiet():
            self.assertEqual(installer.ensure(assume_no=True), 1)

    def test_root_non_usa_sudo(self):
        with mock.patch.object(installer.os, "geteuid", return_value=0), \
                mock.patch.object(installer, "run") as run_mock, \
                mock.patch.object(deps, "install_argv",
                                  return_value=["sudo", "apt", "install", "-y", "python3-gi"]), \
                quiet():
            installer._install_package(
                installer.Prompter(assume_yes=True, interactive=False),
                "gobject", "PyGObject", lambda: True, DEB)
        run_mock.assert_called_once_with(["apt", "install", "-y", "python3-gi"])

    def test_nessun_terminale_non_installa(self):
        problem = installer.Problem("pyside6", "PySide6", True)
        with mock.patch.object(installer, "detect", return_value=[problem]), \
                mock.patch.object(installer, "run") as run_mock, \
                mock.patch.object(installer, "interpreter_has_pyside", return_value=False), \
                mock.patch.object(installer.sys.stdin, "isatty", return_value=False), \
                quiet():
            code = installer.ensure()
        self.assertEqual(code, 1)
        run_mock.assert_not_called()


class VenvTests(unittest.TestCase):
    def make_venv(self, root):
        vpy = root / installer.VENV_NAME / "bin" / "python"
        vpy.parent.mkdir(parents=True)
        vpy.write_text("#!/bin/sh\n")
        vpy.chmod(0o755)
        return vpy

    def test_ripiega_su_venv_se_il_pacchetto_non_c_e(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vpy = self.make_venv(root)
            state = {"pip": False}

            def fake_pyside(python):
                return state["pip"] and str(python) == str(vpy)

            def fake_run(argv):
                if "pip" in argv:
                    state["pip"] = True
                    return 0
                return 1

            with mock.patch.object(installer, "pyside_ok", side_effect=fake_pyside), \
                    mock.patch.object(installer, "run", side_effect=fake_run), \
                    mock.patch.object(installer, "project_root", return_value=root), \
                    mock.patch.object(deps, "install_argv", return_value=APT_PYSIDE), \
                    quiet():
                ok = installer._install_pyside(
                    installer.Prompter(assume_yes=True, interactive=False),
                    "/usr/bin/python3", DEB, root)
        self.assertTrue(ok)

    def test_interprete_preferito(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vpy = self.make_venv(root)

            def only_venv(python):
                return str(python) == str(vpy)

            with mock.patch.object(installer, "project_root", return_value=root), \
                    mock.patch.object(installer, "pyside_ok", side_effect=only_venv):
                self.assertEqual(installer.preferred_python("/usr/bin/python3"), str(vpy))

        with mock.patch.object(installer, "pyside_ok", return_value=True):
            self.assertEqual(installer.preferred_python("/usr/bin/python3"),
                             "/usr/bin/python3")


class DescribeTests(unittest.TestCase):
    def test_riepilogo_con_comandi(self):
        text = installer.describe([installer.Problem("gobject", "PyGObject", False)], DEB)
        self.assertIn("PyGObject", text)
        self.assertIn("sudo apt install python3-gi", text)
        self.assertIn("libgirepository1.0-dev", text)

    def test_servizio_disattivato_mostra_systemctl(self):
        problem = installer.Problem("ratbagd-service", "servizio ratbagd attivo", False)
        text = installer.describe([problem], DEB)
        self.assertIn("sudo systemctl enable --now ratbagd", text)
        self.assertNotIn("apt install ratbagd", text)


if __name__ == "__main__":
    unittest.main()
