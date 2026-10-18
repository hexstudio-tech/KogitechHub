#!/usr/bin/env python3
"""Sniffer HID per KogitechHub: elenca, cattura e invia report hidraw.

Uso:
    scripts/hid_sniff.py list
    scripts/hid_sniff.py info /dev/hidraw2
    scripts/hid_sniff.py capture /dev/hidraw2 --seconds 30 --out prova.jsonl
    scripts/hid_sniff.py read /dev/hidraw2 --report 9 --length 504
    scripts/hid_sniff.py send /dev/hidraw2 "05 01 FF 00 00" --type output
    scripts/hid_sniff.py grant 258a 002a

Serve a studiare le periferiche che nessun backend conosce (per esempio una
tastiera generica con RGB). La lettura di un nodo hidraw richiede permessi:
`grant` installa la regola udev che li concede all'utente collegato.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kogitechhub import hid  # noqa: E402


def report_line(report: dict) -> str:
    return (f"{report['type']:7} id={report['id']:#04x} "
            f"{report['bytes']:3}B  pagine {', '.join(report['pages']) or '-'}")


def cmd_list(_args) -> int:
    devices = hid.list_devices()
    if not devices:
        print("Nessun nodo /dev/hidraw presente.")
        return 1
    for dev in devices:
        access = "letto/scrittura" if dev["writable"] else (
            "solo lettura" if dev["readable"] else "nessun accesso")
        print(f"{dev['node']}  {dev['vendorId']}:{dev['productId']}  {dev['name']}")
        print(f"  permessi: {access}")
        for report in dev["reports"]:
            print("  " + report_line(report))
    return 0


def cmd_info(args) -> int:
    for dev in hid.list_devices():
        if dev["node"] == args.node:
            print(f"{dev['node']}  {dev['vendorId']}:{dev['productId']}  {dev['name']}")
            for report in dev["reports"]:
                print(report_line(report))
            descriptor = Path(f"/sys/class/hidraw/{Path(dev['node']).name}/device/report_descriptor")
            try:
                print("\ndescrittore:")
                print(descriptor.read_bytes()[:1024].hex(" "))
            except OSError as exc:
                print(f"descrittore non leggibile: {exc}")
            return 0
    print(f"{args.node} non trovato.", file=sys.stderr)
    return 1


def cmd_capture(args) -> int:
    device = next((d for d in hid.list_devices() if d["node"] == args.node), None)
    if device is None:
        print(f"{args.node} non trovato.", file=sys.stderr)
        return 1
    if not device["readable"]:
        print("Permessi mancanti per leggere il nodo hidraw.", file=sys.stderr)
        print("Esegui: scripts/hid_sniff.py grant "
              f"{device['vendorId']} {device['productId']}", file=sys.stderr)
        return 2

    capture = hid.Capture(args.node)
    capture.start()
    print(f"cattura da {args.node} per {args.seconds}s (Ctrl+C per fermare).")
    print("Attenzione: una tastiera invia anche i tasti premuti.", file=sys.stderr)
    started = time.monotonic()
    lines = []
    try:
        while time.monotonic() - started < args.seconds:
            time.sleep(0.2)
            for report in capture.drain():
                lines.append(report)
                print(f"{report['time']} id={report['id']:#04x} {report['length']:3}B  {report['hex']}")
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop()
        for report in capture.drain():
            print(f"{report['time']} id={report['id']:#04x} {report['length']:3}B  {report['hex']}")
            lines.append(report)
    if capture.error:
        print(capture.error, file=sys.stderr)

    if args.out:
        out = Path(args.out)
        with out.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps({"device": device["node"], "vendor": device["vendorId"],
                                     "product": device["productId"], "name": device["name"],
                                     "captured": len(lines)}) + "\n")
            for report in lines:
                handle.write(json.dumps(report) + "\n")
        print(f"salvati {len(lines)} report in {out}")
    return 0 if not capture.error else 1


def _permission_hint(node: str) -> None:
    device = next((d for d in hid.list_devices() if d["node"] == node), {})
    print("Permessi mancanti sul nodo hidraw.", file=sys.stderr)
    print(f"  scripts/hid_sniff.py grant {device.get('vendorId', '<vid>')} "
          f"{device.get('productId', '<pid>')}", file=sys.stderr)


def cmd_read(args) -> int:
    try:
        data = hid.get_feature(args.node, args.report, args.length)
    except ValueError as exc:
        print(f"argomenti non validi: {exc}", file=sys.stderr)
        return 1
    except PermissionError:
        _permission_hint(args.node)
        return 2
    except OSError as exc:
        print(f"lettura non riuscita: {exc}", file=sys.stderr)
        return 1
    print(f"{args.node} report {args.report}: {data.hex(' ')}")
    return 0


def cmd_send(args) -> int:
    try:
        data = hid.parse_hex(args.hex)
    except ValueError as exc:
        print(f"payload non valido: {exc}", file=sys.stderr)
        return 1
    print(f"invio {len(data)} byte a {args.node} come report {args.type}: {data.hex(' ')}")
    if not args.yes:
        try:
            answer = input("Confermi? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer not in ("y", "s", "si", "sì"):
            print("annullato.")
            return 1
    try:
        hid.send_report(args.node, data, args.type)
    except PermissionError:
        _permission_hint(args.node)
        return 2
    except (OSError, ValueError) as exc:
        print(f"invio non riuscito: {exc}", file=sys.stderr)
        return 1
    print("report inviato.")
    return 0


def cmd_grant(args) -> int:
    ok, message = hid.grant_access(args.vendor, args.product)
    print(message)
    if not ok:
        print("Comando equivalente:", hid.grant_command(args.vendor, args.product))
        return 1
    print("Ricollega la periferica se i permessi non compaiono subito.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sniffer HID per KogitechHub")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="elenca i nodi hidraw")

    info = sub.add_parser("info", help="descrittore e report di un nodo")
    info.add_argument("node")

    capture = sub.add_parser("capture", help="cattura i report in arrivo")
    capture.add_argument("node")
    capture.add_argument("--seconds", type=float, default=20)
    capture.add_argument("--out", help="file JSONL di destinazione")

    read = sub.add_parser("read", help="legge un report feature (solo lettura)")
    read.add_argument("node")
    read.add_argument("--report", type=int, default=0, help="ID del report")
    read.add_argument("--length", type=int, default=64, help="byte da leggere")

    send = sub.add_parser("send", help="invia un report (output o feature)")
    send.add_argument("node")
    send.add_argument("hex", help="byte esadecimali, incluso l'ID del report")
    send.add_argument("--type", choices=("output", "feature"), default="output")
    send.add_argument("--yes", action="store_true", help="non chiedere conferma")

    grant = sub.add_parser("grant", help="installa la regola udev per l'accesso")
    grant.add_argument("vendor")
    grant.add_argument("product")

    args = parser.parse_args(argv)
    return {"list": cmd_list, "info": cmd_info, "capture": cmd_capture,
            "read": cmd_read, "send": cmd_send, "grant": cmd_grant}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
