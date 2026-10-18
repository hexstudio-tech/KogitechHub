"""Punto di ingresso: controlla/installa le dipendenze e poi apre l'interfaccia.

Sta qui (e non in `app.py`) perché `app.py` importa PySide6: se Qt non è
ancora installato, il controllo delle dipendenze deve avvenire prima.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from . import installer

# Avvisi per chi ha lanciato l'app dal menu (dove non c'è un terminale).
NOTIFIERS = (
    ("notify-send", lambda msg: ["notify-send", "KogitechHub", msg]),
    ("zenity", lambda msg: ["zenity", "--warning", "--text", msg]),
    ("kdialog", lambda msg: ["kdialog", "--title", "KogitechHub", "--sorry", msg]),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kogitechhub",
        description="Configuratore di mouse (DPI, preset, report rate) per Linux")
    parser.add_argument("--mock", action="store_true",
                        help="usa mouse simulati (senza hardware)")
    parser.add_argument("--check", "-c", action="store_true",
                        help="verifica l'ambiente e le dipendenze, poi esce")
    parser.add_argument("--install-deps", action="store_true",
                        help="installa le dipendenze mancanti (chiede Y/N), poi esce")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="risponde sì a tutte le domande di installazione")
    parser.add_argument("--no-install", action="store_true",
                        help="non installa nulla: spiega solo cosa manca")
    parser.add_argument("--no-deps", action="store_true", help=argparse.SUPPRESS)
    return parser


def _notify(message: str) -> None:
    if sys.stdin.isatty():                  # chi è nel terminale ha già letto l'errore
        return
    for binary, build in NOTIFIERS:
        if shutil.which(binary):
            try:
                subprocess.call(build(message), timeout=10)
            except (OSError, subprocess.SubprocessError):
                pass
            return


def _reexec(args: argparse.Namespace, rest: list[str]) -> None:
    """Riparte col Python del venv locale quando PySide6 sta solo lì."""
    target = installer.preferred_python(sys.executable)
    if (os.path.realpath(target) == os.path.realpath(sys.executable)
            or os.environ.get("KOGITECHHUB_REEXEC") == "1"):
        return
    argv = [target, "-m", "kogitechhub", "--no-deps"]
    if args.mock:
        argv.append("--mock")
    os.execvpe(target, argv + rest, dict(os.environ, KOGITECHHUB_REEXEC="1"))


def _launch(args: argparse.Namespace, rest: list[str]) -> int:
    _reexec(args, rest)

    from .app import main as app_main

    return app_main((["--mock"] if args.mock else []) + rest)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args, rest = build_parser().parse_known_args(argv)

    if args.check:
        from .doctor import report

        text, code = report()
        print(text)
        return code

    if not args.no_deps:
        code = installer.ensure(assume_yes=args.yes, assume_no=args.no_install,
                                mock=args.mock, python=sys.executable)
        if code != 0:
            message = "Mancano dipendenze: apri un terminale ed esegui ./run.sh"
            print()
            print("KogitechHub non può partire: mancano dipendenze obbligatorie.")
            print(message)
            _notify(message)
            return code

    if args.install_deps:
        print("Controllo delle dipendenze completato: KogitechHub può partire.")
        return 0
    return _launch(args, rest)
