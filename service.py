"""Application service shared by tools, CLI and the HTTP adapter."""

import json
from pathlib import Path

VERSION = "0.1.0"


class Service:
    def __init__(self, root: Path | None = None):
        self.root = root

    def _store(self):
        from .network_xray.store import Store

        if self.root is not None:
            return Store(self.root)
        from plugins.plugin_storage import plugin_data_dir

        return Store(plugin_data_dir("network-xray"))

    def collect(self, url, label, connect_ip=None):
        from .network_xray.collector import probe

        return self._store().save_probe(probe(url, label, connect_ip=connect_ip), "local")

    def import_probe(self, bundle):
        from .network_xray.bundles import parse_bundle, validate_bundle

        checked = parse_bundle(bundle) if isinstance(bundle, str) else validate_bundle(bundle)
        return self._store().save_probe(checked, "imported")

    def list_probes(self):
        return self._store().list_probes()

    def get_probe(self, probe_id):
        return self._store().get_probe(probe_id)

    def compare_probes(self, left_id, right_id):
        from .network_xray.compare import compare

        left = self.get_probe(left_id)
        right = self.get_probe(right_id)
        return compare(left["probe"], right["probe"])

    def collector_source(self):
        return (Path(__file__).parent / "network_xray" / "collector.py").read_text(encoding="utf-8")

    def export_report(self, left_id, right_id):
        from .export import render_report

        comparison = self.compare_probes(left_id, right_id)
        origins = {
            left_id: self.get_probe(left_id)["origin"],
            right_id: self.get_probe(right_id)["origin"],
        }
        return render_report(comparison, origins)


def _validate_args(name, args):
    from .schemas import TOOL_SCHEMAS

    if name not in TOOL_SCHEMAS or not isinstance(args, dict):
        raise ValueError("Unknown tool or invalid arguments")
    schema = TOOL_SCHEMAS[name]["parameters"]
    if set(args) - set(schema["properties"]) or set(schema.get("required", [])) - set(args):
        raise ValueError("Missing or unexpected arguments")
    for key, value in args.items():
        spec = schema["properties"][key]
        if (
            not isinstance(value, str)
            or not spec.get("minLength", 0) <= len(value) <= spec["maxLength"]
        ):
            raise ValueError("Invalid argument type or length")


def handle_tool(name, args, service=None):
    try:
        _validate_args(name, args)
        service = service or Service()
        if name == "network_xray_probe":
            result = service.collect(**args)
        elif name == "network_xray_import":
            result = service.import_probe(args["bundle_json"])
        elif name == "network_xray_compare":
            result = service.compare_probes(args["left_id"], args["right_id"])
        else:
            result = service.list_probes()
        return json.dumps({"ok": True, "result": result}, allow_nan=False)
    except (ValueError, TypeError):
        return json.dumps(
            {
                "ok": False,
                "error": "Invalid input: check the URL, fields, bundle schema/digest, or matching probe targets.",
            }
        )
    except (FileNotFoundError, KeyError):
        return json.dumps(
            {
                "ok": False,
                "error": "Probe not found in this profile. List history and use its exact IDs.",
            }
        )
    except (OSError, RuntimeError):
        return json.dumps(
            {
                "ok": False,
                "error": "Network X-ray could not complete the operation. Check local storage and retry; no success is implied.",
            }
        )
