"""Installa le dipendenze mancanti di KogitechHub, chiedendo conferma (Y/N).

`run.sh` avvia questo modulo prima dell'interfaccia: su un sistema appena
installato basta `./run.sh` e l'app propone cosa manca, con il comando giusto
per la distribuzione in uso.

Non importa PySide6 né PyGObject (gli import sono verificati in un processo
separato), quindi funziona anche quando Qt non c'è ancora.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import deps

PYSIDE_IMPORT = "import PySide6.QtQuick, PySide6.QtQml"
GIO_IMPORT = ("import gi\n"
              "gi.require_version('Gio', '2.0')\n"
              "from gi.repository import Gio")
PROBE_TIMEOUT = 30          # secondi per verificare un import
VENV_NAME = ".venv"


@dataclass(frozen=True)
class Problem:
    key: str
    label: str
    blocking: bool
    detail: str = ""


# --- interrogazioni sull'ambiente ------------------------------------------

def project_root() -> Path | None:
    """Cartella del progetto (serve per il venv locale), None se non c'è."""
    env = os.environ.get("KOGITECHHUB_ROOT")
    root = Path(env) if env else Path(__file__).resolve().parents[2]
    try:
        if (root / "src" / "kogitechhub" / "__init__.py").is_file():
            return root
    except OSError:
        pass
    return None


def venv_python(root: Path | None = None) -> Path | None:
    root = root if root is not None else project_root()
    return None if root is None else root / VENV_NAME / "bin" / "python"


def can_import(python: str | Path, code: str) -> bool:
    try:
        done = subprocess.run([str(python), "-c", code], capture_output=True,
                              text=True, timeout=PROBE_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def pyside_ok(python: str | Path) -> bool:
    return can_import(python, PYSIDE_IMPORT)


def gio_ok(python: str | Path) -> bool:
    return can_import(python, GIO_IMPORT)


def interpreter_has_pyside(python: str | Path) -> bool:
    """PySide6 c'è in questo interprete oppure nel venv locale del progetto."""
    if pyside_ok(python):
        return True
    vpy = venv_python()
    return vpy is not None and vpy.is_file() and pyside_ok(vpy)


def preferred_python(current: str) -> str:
    """Interprete da usare: quello attuale se ha Qt, altrimenti il venv locale."""
    if pyside_ok(current):
        return current
    vpy = venv_python()
    if vpy is not None and vpy.is_file() and pyside_ok(vpy):
        return str(vpy)
    return current


def service_state(unit: str = "ratbagd") -> str:
    """'ok' | 'disabled' | 'masked' | 'unknown' (systemd assente o unità ignota)."""
    if shutil.which("systemctl") is None:
        return "unknown"
    try:
        done = subprocess.run(["systemctl", "is-enabled", unit],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    state = done.stdout.strip()
    if state in ("enabled", "static", "alias", "indirect", "generated"):
        return "ok"
    if state == "masked":
        return "masked"
    if state in ("disabled", "linked", "linked-runtime"):
        return "disabled"
    return "unknown"


# --- dialogo con l'utente ---------------------------------------------------

class Prompter:
    """Chiede Y/N; --yes e --no-install evitano le domande."""

    def __init__(self, *, assume_yes: bool = False, assume_no: bool = False,
                 interactive: bool | None = None):
        self.assume_yes = assume_yes
        self.assume_no = assume_no
        self.interactive = sys.stdin.isatty() if interactive is None else interactive

    def ask(self, question: str, default: bool = True) -> bool | None:
        """True/False per la risposta, None se non si può chiedere."""
        if self.assume_yes:
            print(f"  {question} sì (--yes)")
            return True
        if self.assume_no:
            print(f"  {question} no (--no-install)")
            return False
        if not self.interactive:
            print(f"  {question} non chiesto: nessun terminale collegato.")
            return None
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            try:
                raw = input(f"  {question} {suffix} ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return None
            if not raw:
                return default
            if raw in ("y", "yes", "s", "si", "sì"):
                return True
            if raw in ("n", "no"):
                return False
            print("  risposta non valida: scrivi Y (sì) oppure N (no).")


def run(argv: list[str]) -> int:
    print(f"  $ {shlex.join(argv)}")
    try:
        return subprocess.call(argv)
    except OSError as exc:
        print(f"  impossibile eseguire il comando: {exc}")
        return 127


def _without_sudo(argv: list[str]) -> list[str]:
    """Chi è già root (container, live) non ha bisogno di sudo."""
    if argv[:1] == ["sudo"] and hasattr(os, "geteuid") and os.geteuid() == 0:
        return argv[1:]
    return argv


# --- installazione ----------------------------------------------------------

def _install_package(prompter: Prompter, key: str, label: str, verify,
                     distro: deps.Distro) -> bool:
    argv = deps.install_argv(key, distro)
    if not argv:
        print(f"  Non conosco il pacchetto {label} per {distro.pretty}.")
        for line in deps.install_hint([key], distro):
            print(line)
        return False
    argv = _without_sudo(argv)
    print(f"  comando: {shlex.join(argv)}")
    if prompter.ask("Installarlo adesso?") is not True:
        return False
    code = run(argv)
    if verify():
        print("  installato.")
        return True
    print(f"  installazione non riuscita (codice {code}): forse il pacchetto non")
    print("  esiste nei repository di questa distribuzione.")
    return False


def _create_venv(root: Path, vpy: Path | None) -> bool:
    if vpy is not None and vpy.is_file():
        return True
    target = root / VENV_NAME
    argv = [sys.executable, "-m", "venv", "--system-site-packages", str(target)]
    print(f"  comando: {shlex.join(argv)}")
    code = run(argv)
    if code != 0 or vpy is None or not vpy.is_file():
        print("  creazione dell'ambiente non riuscita: su Debian/Ubuntu serve")
        print("  il pacchetto python3-venv (sudo apt install python3-venv).")
        return False
    return True


def _install_pyside(prompter: Prompter, python: str, distro: deps.Distro,
                    root: Path | None) -> bool:
    if interpreter_has_pyside(python):
        return True
    if _install_package(prompter, "pyside6", deps.LABELS["pyside6"],
                        lambda: pyside_ok(python), distro):
        return True
    if prompter.assume_no:
        return False
    if root is None or not os.access(root, os.W_OK):
        hint = (deps.install_hint(["pyside6"], distro)
                or ["pip install --user PySide6"])[-1]
        print(f"  PySide6 va installato a mano: {hint.strip()}")
        return False
    vpy = venv_python(root)
    if vpy is not None and vpy.is_file() and pyside_ok(vpy):
        return True
    print(f"  Se i repository non hanno PySide6, lo installo in {root / VENV_NAME}:")
    print("  è una cartella locale del progetto, il Python di sistema resta com'è.")
    if prompter.ask("Creare l'ambiente locale e installare PySide6 con pip?") is not True:
        return False
    if not _create_venv(root, vpy):
        return False
    assert vpy is not None
    if run([str(vpy), "-m", "pip", "install", "PySide6"]) != 0:
        print("  pip non è riuscito a installare PySide6.")
        return False
    return pyside_ok(vpy)


def _enable_service(prompter: Prompter) -> bool:
    state = service_state()
    if state == "ok" or state == "unknown":
        return True
    if shutil.which("sudo") is None:
        print("  serve root per attivare il servizio: sudo systemctl enable --now ratbagd")
        return False
    if state == "masked":
        print("  il servizio ratbagd è mascherato: sudo systemctl unmask ratbagd")
        return False
    argv = _without_sudo(["sudo", "systemctl", "enable", "--now", "ratbagd"])
    question = f"Attivare il servizio ratbagd ({shlex.join(argv)})?"
    return prompter.ask(question) is True and run(argv) == 0


def _install(problem: Problem, prompter: Prompter, python: str,
             distro: deps.Distro, root: Path | None) -> bool:
    if problem.key == "pyside6":
        return _install_pyside(prompter, python, distro, root)
    if problem.key == "gobject":
        return _install_package(prompter, "gobject", problem.label,
                                lambda: gio_ok(python), distro)
    if problem.key == "ratbagd":
        if _install_package(prompter, "ratbagd", problem.label,
                            lambda: shutil.which("ratbagd") is not None, distro):
            return _enable_service(prompter)
        return False
    if problem.key == "ratbagd-service":
        return _enable_service(prompter)
    if problem.key in ("openrgb", "headsetcontrol"):
        return _install_package(prompter, problem.key, problem.label,
                                lambda: shutil.which(problem.key) is not None, distro)
    return False


# --- rilevamento ------------------------------------------------------------

def detect(python: str | None = None, *, mock: bool = False) -> list[Problem]:
    """Dipendenze mancanti, in ordine di importanza."""
    py = str(python or sys.executable)
    problems: list[Problem] = []
    if sys.version_info < (3, 10):
        problems.append(Problem("python", "Python 3.10 o successivo", True,
                                sys.version.split()[0]))
    if not interpreter_has_pyside(py):
        problems.append(Problem("pyside6", deps.LABELS["pyside6"], True))
    if not mock and not gio_ok(py):         # --mock non usa D-Bus
        problems.append(Problem("gobject", deps.LABELS["gobject"], False))
    if not mock and shutil.which("ratbagd") is None:
        problems.append(Problem("ratbagd", deps.LABELS["ratbagd"], False))
    elif not mock and service_state() == "disabled":
        problems.append(Problem("ratbagd-service", "servizio ratbagd attivo", False,
                                "libratbag è installato ma il servizio è disattivato"))
    # facoltativi: senza OpenRGB/HeadsetControl l'app funziona lo stesso
    if not mock and shutil.which("openrgb") is None:
        problems.append(Problem("openrgb", deps.LABELS["openrgb"], False))
    if not mock and shutil.which("headsetcontrol") is None:
        problems.append(Problem("headsetcontrol", deps.LABELS["headsetcontrol"], False))
    return problems


def describe(problems: list[Problem], distro: deps.Distro) -> str:
    """Riepilogo leggibile di cosa manca e come si installa."""
    lines = [f"KogitechHub: mancano {len(problems)} dipendenza/e su {distro.pretty}:"]
    for problem in problems:
        lines.append(f"  - {problem.label}" + (f" ({problem.detail})" if problem.detail else ""))
        if problem.key == "ratbagd-service":
            lines.append("    sudo systemctl enable --now ratbagd")
            continue
        for line in deps.install_hint([problem.key], distro)[:1]:
            lines.append(f"    {line.strip()}")
    if any(p.key == "gobject" for p in problems):
        lines.append(f"    per compilarlo da sorgente: {deps.gobject_build_hint(distro)}")
    return "\n".join(lines)


def ensure(*, assume_yes: bool = False, assume_no: bool = False,
           mock: bool = False, python: str | None = None) -> int:
    """Installa (con conferma) ciò che manca. 0 se l'app può partire."""
    py = str(python or sys.executable)
    distro = deps.detect_distro()
    problems = detect(py, mock=mock)
    if not problems:
        return 0

    prompter = Prompter(assume_yes=assume_yes, assume_no=assume_no)
    print("KogitechHub - controllo delle dipendenze")
    print(f"  sistema: {distro.pretty}")
    if not prompter.interactive and not (assume_yes or assume_no):
        print("  nessun terminale collegato: posso solo spiegare cosa installare.")
        print("  esegui ./run.sh da un terminale, oppure ./run.sh --yes")
    print()

    unresolved: list[Problem] = []
    for problem in problems:
        if problem.key == "python":
            unresolved.append(problem)
            continue
        print(f"- {problem.label}")
        if not _install(problem, prompter, py, distro, project_root()):
            still = [p for p in detect(py, mock=mock) if p.key == problem.key]
            if still:
                unresolved.append(still[0])
        print()

    if unresolved:
        print(describe(unresolved, distro))
        print()
        print("Puoi anche installare tutto in una volta con "
              "./run.sh --install-deps (o ./run.sh --yes --install-deps).")
        if any(p.blocking for p in unresolved):
            return 1
    else:
        print()
        print("Dipendenze a posto.")
    return 0


# --- uso diretto: python3 -m kogitechhub.installer --------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="kogitechhub-installer",
        description="Installa le dipendenze di KogitechHub chiedendo conferma (Y/N).")
    parser.add_argument("-y", "--yes", action="store_true", help="installa senza chiedere")
    parser.add_argument("--no-install", action="store_true",
                        help="mostra solo cosa manca, senza installare")
    parser.add_argument("--mock", action="store_true",
                        help="non richiede ratbagd (mouse simulati)")
    args = parser.parse_args(argv)
    return ensure(assume_yes=args.yes, assume_no=args.no_install, mock=args.mock)


if __name__ == "__main__":                                      # pragma: no cover
    raise SystemExit(main())
