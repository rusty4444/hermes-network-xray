"""Model-facing schemas. Collection is explicit and read-only."""

TOOL_SCHEMAS = {
    "network_xray_probe": {
        "name": "network_xray_probe",
        "description": (
            "Run a bounded, direct (no proxy) DNS/TCP/verified TLS/HTTP HEAD probe from "
            "THIS Hermes backend, only for a URL the user requested or approved. "
            "No credentials, query strings, redirects or response bodies. Private/loopback "
            "targets are allowed; this is not a scanner. connect_ip is an explicit manual "
            "experiment preserving the original Host and TLS server name. Saves evidence."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "maxLength": 2048},
                "label": {"type": "string", "minLength": 1, "maxLength": 48},
                "connect_ip": {"type": "string", "maxLength": 45},
            },
            "required": ["url", "label"],
            "additionalProperties": False,
        },
    },
    "network_xray_import": {
        "name": "network_xray_import",
        "description": (
            "Import a portable Network X-ray collector JSON bundle (maximum 128 KiB). "
            "Validates its schema and content digest and saves it as an imported, "
            "unauthenticated recorded observation, never a live probe. Do not import secrets."
        ),
        "parameters": {
            "type": "object",
            "properties": {"bundle_json": {"type": "string", "maxLength": 131072}},
            "required": ["bundle_json"],
            "additionalProperties": False,
        },
    },
    "network_xray_compare": {
        "name": "network_xray_compare",
        "description": (
            "Compare two saved Network X-ray probe IDs for the same URL. Returns actual "
            "stage differences, clearly labelled hypotheses and optional manual tests. "
            "A difference is not proof of root cause; does not run suggested tests."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "left_id": {"type": "string", "maxLength": 36},
                "right_id": {"type": "string", "maxLength": 36},
            },
            "required": ["left_id", "right_id"],
            "additionalProperties": False,
        },
    },
    "network_xray_history": {
        "name": "network_xray_history",
        "description": "List the newest saved Network X-ray probes in the active profile. No network calls.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}
