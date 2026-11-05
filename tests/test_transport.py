"""Cross-language raw-JSON transport regressions; all probe fixtures are synthetic."""

import importlib.util
import json
from pathlib import Path
import sys
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from network_xray import collector
from network_xray.bundles import parse_bundle, seal_bundle

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def api(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "xray_transport_api", ROOT / "dashboard/plugin_api.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/network-xray")
    app.dependency_overrides[module.get_service] = lambda: module._service_module.Service(
        tmp_path / "records"
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def synthetic_raw(kind):
    value = collector.empty_bundle(
        collector.parse_target("https://example.test/"), "Synthetic numeric import"
    )
    value["capture"] = {
        "status": "timeout",
        "duration_ms": 12000.0,
        "error": {"code": "deadline_exceeded", "message": "Synthetic timeout fixture"},
    }
    if kind == "negative_zero":
        value["stages"][0]["duration_ms"] = -0.0
    value = seal_bundle(value)
    text = json.dumps(value, separators=(",", ":"))
    if kind == "exponent":
        text = text.replace('"duration_ms":12000.0', '"duration_ms":1.2e4')
    assert parse_bundle(text) == value
    return text, value


@pytest.mark.parametrize("kind", ["integral_float", "exponent", "negative_zero"])
def test_raw_text_import_preserves_original_id_and_digest(api, kind):
    raw, original = synthetic_raw(kind)
    response = api.post("/api/plugins/network-xray/import", json={"bundle_json": raw})
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["origin"] == "imported"
    assert saved["probe"]["id"] == original["id"]
    assert saved["probe"]["integrity"] == original["integrity"]
    readback = api.get("/api/plugins/network-xray/probes/" + original["id"]).json()["probe"]
    assert parse_bundle(json.dumps(readback))["integrity"] == original["integrity"]


def test_raw_text_import_does_not_reseal_tampering(api):
    raw, _ = synthetic_raw("integral_float")
    response = api.post(
        "/api/plugins/network-xray/import",
        json={"bundle_json": raw.replace("Synthetic numeric import", "Tampered label")},
    )
    assert response.status_code == 400
    assert api.get("/api/plugins/network-xray/probes").json() == {"probes": []}


@pytest.mark.parametrize("identifier", [None, 1, True, [], {}])
def test_invalid_comparison_identifiers_are_controlled_400(api, identifier):
    response = api.post(
        "/api/plugins/network-xray/compare",
        json={"left_id": identifier, "right_id": str(uuid.uuid4())},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "origin",
    ["http://[", "http://[::1", "null", "http://attacker.example", "http://testserver/path"],
)
def test_malformed_or_nonorigin_headers_are_controlled_403(api, origin):
    response = api.post(
        "/api/plugins/network-xray/import", json={"bundle_json": "{}"}, headers={"origin": origin}
    )
    assert response.status_code == 403
    assert api.get("/api/plugins/network-xray/probes").json() == {"probes": []}


def test_object_import_is_rejected_instead_of_silently_recanonicalized(api):
    _, value = synthetic_raw("integral_float")
    assert api.post("/api/plugins/network-xray/import", json={"bundle": value}).status_code == 400
