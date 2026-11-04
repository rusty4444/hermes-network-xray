"""Strict untrusted bundle boundary. A digest proves content, never provenance."""

import copy
from datetime import datetime
import hmac
import json
import math
import re
import uuid

from .collector import (
    MAX_BUNDLE_BYTES,
    POLICY,
    STAGE_NAMES,
    parse_target,
    permitted_ip,
    seal_bundle,
    validate_label,
)

TOP_KEYS = {
    "schema_version",
    "kind",
    "id",
    "captured_at",
    "vantage",
    "target",
    "policy",
    "capture",
    "stages",
    "integrity",
}
DETAIL_KEYS = {
    "dns": {"addresses", "truncated"},
    "tcp": {"address", "port", "family", "selection"},
    "tls": {"protocol", "cipher", "certificate_sha256", "expires_at", "server_name", "verified"},
    "http": {"status_code", "reason", "server", "content_type", "redirect"},
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, keys, name):
    _require(type(value) is dict and set(value) == set(keys), f"Invalid {name} fields")


def _text(value, maximum, minimum=0):
    _require(
        type(value) is str
        and minimum <= len(value) <= maximum
        and (not value or value.isprintable()),
        "Invalid bounded text",
    )


def _number(value):
    _require(
        type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 60000,
        "Invalid duration",
    )


def _integer(value, minimum, maximum):
    _require(type(value) is int and minimum <= value <= maximum, "Invalid integer")


def _boolean(value):
    _require(type(value) is bool, "Invalid boolean")


def valid_id(value):
    _text(value, 36, 36)
    try:
        identifier = uuid.UUID(value)
    except ValueError:
        raise ValueError("Invalid UUID4") from None
    _require(identifier.version == 4 and str(identifier) == value, "Invalid UUID4")
    return value


def _date(value):
    _text(value, 40, 20)
    _require(
        re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value),
        "Invalid UTC timestamp",
    )
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValueError("Invalid UTC timestamp") from None


def _error(value):
    if value is None:
        return
    _keys(value, {"code", "message"}, "error")
    _text(value["code"], 64, 1)
    _require(re.fullmatch(r"[a-zA-Z0-9_.-]+", value["code"]), "Invalid error code")
    _text(value["message"], 400)


def _fingerprint(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "Invalid SHA256")


def _ip(value):
    _require(type(value) is str and permitted_ip(value) == value, "Noncanonical IP")


def _dns_details(details, ok):
    if "addresses" in details:
        addresses = details["addresses"]
        _require(
            type(addresses) is list and (1 if ok else 0) <= len(addresses) <= 8,
            "Invalid DNS addresses",
        )
        for address in addresses:
            _ip(address)
        _require(len(set(addresses)) == len(addresses), "Duplicate DNS address")
    if "truncated" in details:
        _boolean(details["truncated"])


def _tcp_details(details, target, dns):
    if "address" in details:
        _ip(details["address"])
    if "port" in details:
        _integer(details["port"], 1, 65535)
        _require(details["port"] == target["port"], "TCP target port mismatch")
    if "family" in details:
        _require(details["family"] in ("ipv4", "ipv6"), "Invalid IP family")
        if "address" in details:
            _require(
                details["family"] == ("ipv6" if ":" in details["address"] else "ipv4"),
                "IP family mismatch",
            )
    if "selection" in details:
        selection = "override" if target["connect_ip"] is not None else "dns"
        _require(details["selection"] == selection, "TCP selection mismatch")
    if "address" in details:
        permitted = (
            [target["connect_ip"]] if target["connect_ip"] else dns["details"].get("addresses", [])
        )
        _require(details["address"] in permitted, "TCP address not selected from target/DNS")


def _tls_details(details, target, ok):
    for name in ("protocol", "cipher"):
        if name in details:
            _text(details[name], 240, 1)
    if "certificate_sha256" in details:
        _fingerprint(details["certificate_sha256"])
    if details.get("expires_at") is not None:
        _date(details["expires_at"])
    if "server_name" in details:
        _require(details["server_name"] == target["host"], "TLS server name mismatch")
    if "verified" in details:
        _boolean(details["verified"])
        _require(not ok or details["verified"] is True, "Successful TLS must be verified")


def _http_details(details, ok):
    for name in ("reason", "server", "content_type"):
        if name in details:
            _text(details[name], 240)
    if "redirect" in details:
        _boolean(details["redirect"])
    if "status_code" in details:
        status = details["status_code"]
        _integer(status, 200, 599)
        _require((status < 400) == ok, "HTTP status and outcome mismatch")
        if "redirect" in details:
            _require(details["redirect"] == (300 <= status <= 399), "HTTP redirect mismatch")


def _stage(stage, name, target, dns):
    _keys(stage, {"name", "status", "duration_ms", "summary", "details", "error"}, "stage")
    _require(stage["name"] == name, "Invalid stage order")
    status = stage["status"]
    _require(status in ("ok", "error", "skipped", "unknown"), "Invalid stage status")
    _number(stage["duration_ms"])
    _text(stage["summary"], 240)
    _error(stage["error"])
    _require((status == "error") == (stage["error"] is not None), "Stage error/status mismatch")
    details = stage["details"]
    _require(type(details) is dict, "Invalid stage details")
    if status in ("skipped", "unknown"):
        _require(not details, "Unobserved stage cannot contain details")
        return
    _require(set(details) <= DETAIL_KEYS[name], "Unexpected stage detail")
    ok = status == "ok"
    if ok:
        _require(set(details) == DETAIL_KEYS[name], "Missing successful stage details")
    if name == "dns":
        _dns_details(details, ok)
    elif name == "tcp":
        _tcp_details(details, target, dns)
    elif name == "tls":
        _tls_details(details, target, ok)
    else:
        _http_details(details, ok)


def _progression(bundle):
    dns, tcp, tls, http = bundle["stages"]
    target = bundle["target"]
    complete = bundle["capture"]["status"] == "complete"
    if complete:
        _require(
            all(stage["status"] != "unknown" for stage in bundle["stages"]),
            "Complete capture has unknown stages",
        )
        _require(dns["status"] in ("ok", "error"), "Complete capture must observe DNS")
    allowed_tcp = dns["status"] == "ok" or (
        dns["status"] == "error" and target["connect_ip"] is not None
    )
    _require(tcp["status"] not in ("ok", "error") or allowed_tcp, "TCP ran without DNS/override")
    if complete and allowed_tcp:
        _require(tcp["status"] in ("ok", "error"), "Missing TCP observation")
    if target["scheme"] == "http":
        _require(tls["status"] in ("skipped", "unknown"), "TLS cannot run for HTTP")
        if tls["status"] == "skipped":
            _require(tls["summary"] == "Not applicable: HTTP", "Incorrect HTTP TLS skip")
        allowed_http = tcp["status"] == "ok"
    else:
        _require(
            tls["status"] not in ("ok", "error") or tcp["status"] == "ok", "TLS ran without TCP"
        )
        if complete and tcp["status"] == "ok":
            _require(tls["status"] in ("ok", "error"), "Missing TLS observation")
        allowed_http = tls["status"] == "ok"
    _require(http["status"] not in ("ok", "error") or allowed_http, "HTTP ran without transport")
    if complete and allowed_http:
        _require(http["status"] in ("ok", "error"), "Missing HTTP observation")
    if complete and target["scheme"] == "http":
        _require(tls["status"] == "skipped", "HTTP TLS must be skipped")


def _validate(value):
    _keys(value, TOP_KEYS, "bundle")
    _require(
        type(value["schema_version"]) is int and value["schema_version"] == 1, "Unknown schema"
    )
    _require(value["kind"] == "network_xray.probe", "Unknown bundle kind")
    valid_id(value["id"])
    _date(value["captured_at"])
    vantage = value["vantage"]
    _keys(vantage, {"label", "platform", "python"}, "vantage")
    validate_label(vantage["label"])
    _text(vantage["platform"], 64, 1)
    _text(vantage["python"], 64, 1)
    target = value["target"]
    _keys(target, {"url", "scheme", "host", "port", "path", "connect_ip"}, "target")
    _integer(target["port"], 1, 65535)
    _require(parse_target(target["url"], target["connect_ip"]) == target, "Inconsistent target")
    _keys(value["policy"], POLICY, "policy")
    for key, expected in POLICY.items():
        _require(
            type(value["policy"][key]) is type(expected) and value["policy"][key] == expected,
            "Impossible collection policy",
        )
    capture = value["capture"]
    _keys(capture, {"status", "duration_ms", "error"}, "capture")
    _require(capture["status"] in ("complete", "timeout", "failed"), "Invalid capture status")
    _number(capture["duration_ms"])
    _error(capture["error"])
    _require(
        (capture["status"] == "complete") == (capture["error"] is None),
        "Capture error/status mismatch",
    )
    stages = value["stages"]
    _require(type(stages) is list and len(stages) == 4, "Four stages required")
    for name, stage in zip(STAGE_NAMES, stages):
        _stage(stage, name, target, stages[0])
    _progression(value)
    integrity = value["integrity"]
    _keys(integrity, {"algorithm", "digest"}, "integrity")
    _require(integrity["algorithm"] == "sha256", "Unknown digest algorithm")
    _fingerprint(integrity["digest"])
    expected = seal_bundle(value)["integrity"]["digest"]
    _require(hmac.compare_digest(expected, integrity["digest"]), "Bundle digest mismatch")


def validate_bundle(value):
    """Validate exact JSON schemas and return a detached copy; raise ValueError."""
    try:
        encoded = json.dumps(value, ensure_ascii=True, allow_nan=False)
        _require(len(encoded.encode("utf-8")) <= MAX_BUNDLE_BYTES, "Bundle exceeds 128 KiB")
        _validate(value)
        return copy.deepcopy(value)
    except (TypeError, KeyError, OverflowError, RecursionError, AttributeError):
        raise ValueError("Invalid bundle data") from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Nonfinite JSON number")


def parse_bundle(text):
    if type(text) is not str:
        raise ValueError("Bundle JSON must be text")
    try:
        _require(len(text.encode("utf-8")) <= MAX_BUNDLE_BYTES, "Bundle exceeds 128 KiB")
        result = json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
    except (RecursionError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Invalid bundle JSON") from None
    return validate_bundle(result)


def overall(bundle):
    value = validate_bundle(bundle)
    if value["capture"]["status"] != "complete":
        return "inconclusive"
    if value["stages"][3]["status"] == "ok":
        return "healthy"
    if any(stage["status"] == "error" for stage in value["stages"]):
        return "failed"
    return "inconclusive"
