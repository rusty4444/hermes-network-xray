"""HTTP boundary tests use an explicitly synthetic service, not network evidence."""

import importlib.util
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client():
    path = Path(__file__).resolve().parents[1] / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("xray_http_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class FakeService:
        def list_probes(self):
            return {"probes": []}

        def collect(self, url, label, connect_ip=None):
            return {"synthetic_test_echo": {"url": url, "label": label, "connect_ip": connect_ip}}

        def import_probe(self, bundle):
            raise ValueError("synthetic invalid bundle")

        def get_probe(self, probe_id):
            raise FileNotFoundError()

        def collector_source(self):
            return "# synthetic test source\n"

    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/network-xray")
    app.dependency_overrides[module.get_service] = lambda: FakeService()
    with TestClient(app) as test_client:
        yield test_client


def test_history_and_health_are_non_mutating(client):
    assert client.get("/api/plugins/network-xray/health").json()["ok"] is True
    assert client.get("/api/plugins/network-xray/probes").json() == {"probes": []}


def test_probe_dispatches_explicit_fields(client):
    result = client.post(
        "/api/plugins/network-xray/probe", json={"url": "https://example.com/", "label": "Peer"}
    )
    assert result.status_code == 200
    assert result.json()["synthetic_test_echo"]["label"] == "Peer"


@pytest.mark.parametrize(
    "body",
    [
        '{"url":"https://example.com/","url":"https://evil.example/","label":"Peer"}',
        '{"url":"https://example.com/","label":"Peer","command":"not allowed"}',
        '{"url":5,"label":"Peer"}',
        "[]",
        '{"url":"https://example.com/","label":NaN}',
    ],
)
def test_bad_json_or_shape_rejected(client, body):
    response = client.post(
        "/api/plugins/network-xray/probe",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert "evil.example" not in response.text
    assert "not allowed" not in response.text


def test_cross_origin_probe_rejected(client):
    response = client.post(
        "/api/plugins/network-xray/probe",
        json={"url": "https://example.com/", "label": "Peer"},
        headers={"origin": "https://attacker.example"},
    )
    assert response.status_code == 403


def test_simple_form_post_rejected(client):
    response = client.post(
        "/api/plugins/network-xray/probe", content="{}", headers={"content-type": "text/plain"}
    )
    assert response.status_code == 415


def test_oversized_body_rejected(client):
    response = client.post(
        "/api/plugins/network-xray/import",
        content=b" " * 262145,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_invalid_bundle_is_safe_400(client):
    response = client.post(
        "/api/plugins/network-xray/import",
        json={"bundle_json": '{"secret":"TEST-CANARY-NOT-A-REAL-SECRET"}'},
    )
    assert response.status_code == 400
    assert "TEST-CANARY" not in response.text


def test_path_identifier_rejected_before_store(client):
    assert client.get("/api/plugins/network-xray/probes/not-a-uuid").status_code == 400


def test_collector_is_downloadable_source(client):
    response = client.get("/api/plugins/network-xray/collector")
    assert response.json()["filename"] == "network-xray-collector.py"
    assert response.json()["source"] == "# synthetic test source\n"
    response = client.get("/api/plugins/network-xray/collector.py")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
