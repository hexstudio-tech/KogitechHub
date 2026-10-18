"""Test del punto di ingresso: scelta dell'interprete e riavvio nel venv.

Non importa `kogitechhub.app`: altri test sostituiscono PySide6 con degli stub
e un import anticipato della GUI renderebbe l'ordine dei test significativo.
"""
import unittest
from unittest import mock

from kogitechhub import cli


class Exec(Exception):
    """Sostituisce os.execvpe per fermare il test prima della GUI."""


class NotifyTests(unittest.TestCase):
    def test_avvisa_fuori_dal_terminale(self):
        with mock.patch.object(cli.sys.stdin, "isatty", return_value=False), \
                mock.patch.object(
                    cli.shutil, "which",
                    side_effect=lambda b: f"/usr/bin/{b}" if b == "notify-send" else None), \
                mock.patch.object(cli.subprocess, "call") as call_mock:
            cli._notify("mancano dipendenze")
        call_mock.assert_called_once()
        self.assertEqual(call_mock.call_args.args[0][:2], ["notify-send", "KogitechHub"])

    def test_non_avvisa_nel_terminale(self):
        with mock.patch.object(cli.sys.stdin, "isatty", return_value=True), \
                mock.patch.object(cli.subprocess, "call") as call_mock:
            cli._notify("mancano dipendenze")
        call_mock.assert_not_called()


class ReexecTests(unittest.TestCase):
    def test_usa_il_venv_locale_quando_il_sistema_non_ha_qt(self):
        args = cli.build_parser().parse_args(["--mock"])
        with mock.patch.object(cli.installer, "preferred_python",
                               return_value="/tmp/venv/bin/python"), \
                mock.patch.object(cli.sys, "executable", "/usr/bin/python3"), \
                mock.patch.object(cli.os, "execvpe", side_effect=Exec) as exec_mock, \
                mock.patch.dict(cli.os.environ, {"KOGITECHHUB_REEXEC": ""}):
            with self.assertRaises(Exec):
                cli._reexec(args, ["--platform", "offscreen"])

        command, argv, env = exec_mock.call_args.args
        self.assertEqual(command, "/tmp/venv/bin/python")
        self.assertEqual(argv, ["/tmp/venv/bin/python", "-m", "kogitechhub", "--no-deps",
                                "--mock", "--platform", "offscreen"])
        self.assertEqual(env["KOGITECHHUB_REEXEC"], "1")

    def test_non_riavvia_due_volte(self):
        args = cli.build_parser().parse_args([])
        with mock.patch.object(cli.installer, "preferred_python",
                               return_value="/tmp/venv/bin/python"), \
                mock.patch.object(cli.sys, "executable", "/usr/bin/python3"), \
                mock.patch.object(cli.os, "execvpe") as exec_mock, \
                mock.patch.dict(cli.os.environ, {"KOGITECHHUB_REEXEC": "1"}):
            self.assertIsNone(cli._reexec(args, []))
        exec_mock.assert_not_called()

    def test_non_riavvia_se_il_python_attuale_ha_qt(self):
        args = cli.build_parser().parse_args([])
        with mock.patch.object(cli.installer, "preferred_python",
                               return_value="/usr/bin/python3"), \
                mock.patch.object(cli.sys, "executable", "/usr/bin/python3"), \
                mock.patch.object(cli.os, "execvpe") as exec_mock:
            self.assertIsNone(cli._reexec(args, []))
        exec_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
