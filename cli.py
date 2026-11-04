"""Operator-invoked CLI; no remote execution or authentication helpers."""

import json
from pathlib import Path
import sys


def configure(parser):
    commands = parser.add_subparsers(dest="xray_command", required=True)
    collect = commands.add_parser("probe", help="Probe one explicit HTTP(S) URL")
    collect.add_argument("url")
    collect.add_argument("--label", required=True)
    collect.add_argument("--connect-ip")
    imported = commands.add_parser("import", help="Import one portable collector JSON file")
    imported.add_argument("file")
    compared = commands.add_parser("compare", help="Compare two saved IDs for the same URL")
    compared.add_argument("left_id")
    compared.add_argument("right_id")
    compared.add_argument(
        "--html", action="store_true", help="Print an escaped standalone HTML report"
    )
    commands.add_parser("history", help="List saved probes in this profile")
    commands.add_parser("collector", help="Print the portable collector source to stdout")


def run(args):
    from .service import Service

    service = Service()
    try:
        if args.xray_command == "probe":
            result = service.collect(args.url, args.label, args.connect_ip)
        elif args.xray_command == "import":
            with Path(args.file).open("rb") as source:
                raw = source.read(131073)
            if len(raw) > 131072:
                raise ValueError("Bundle exceeds 128 KiB")
            result = service.import_probe(raw.decode("utf-8"))
        elif args.xray_command == "compare":
            if args.html:
                print(service.export_report(args.left_id, args.right_id))
                return 0
            result = service.compare_probes(args.left_id, args.right_id)
        elif args.xray_command == "collector":
            print(service.collector_source(), end="")
            return 0
        else:
            result = service.list_probes()
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        print(
            "Network X-ray failed: check your input, saved IDs and local storage. No success is implied.",
            file=sys.stderr,
        )
        return 1
