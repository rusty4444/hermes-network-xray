"""Integration tests use real loopback sockets and the real collector/store/router."""

import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


class FixtureHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


def load_api(root):
    spec = importlib.util.spec_from_file_location(
        "xray_real_api_test", ROOT / "dashboard" / "plugin_api.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/network-xray")
    app.dependency_overrides[module.get_service] = lambda: module._service_module.Service(root)
    return app, module


def test_real_collection_comparison_export_and_reopen(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/health"
    app, module = load_api(tmp_path / "records")
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/plugins/network-xray/probe",
                json={"url": url, "label": "Local service running"},
            )
            assert response.status_code == 200, response.text
            left = response.json()["probe"]
            assert left["stages"][3]["details"]["status_code"] == 200
            assert left["stages"][2]["status"] == "skipped"
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            response = client.post(
                "/api/plugins/network-xray/probe",
                json={"url": url, "label": "Local service stopped"},
            )
            assert response.status_code == 200, response.text
            right = response.json()["probe"]
            assert right["stages"][1]["status"] == "error"
            response = client.post(
                "/api/plugins/network-xray/compare",
                json={"left_id": left["id"], "right_id": right["id"]},
            )
            assert response.status_code == 200, response.text
            comparison = response.json()
            assert comparison["verdict"] == "diverged"
            assert comparison["first_divergence"] == "tcp"
            report = client.get(
                f"/api/plugins/network-xray/export/{left['id']}/{right['id']}"
            ).json()
            assert "Local service running" in report["html"]
            assert left["integrity"]["digest"] in report["html"]
            assert "<script" not in report["html"]
            source = client.get("/api/plugins/network-xray/collector").json()["source"]
            assert source == (ROOT / "network_xray" / "collector.py").read_text()
        reopened = module._service_module.Service(tmp_path / "records")
        assert len(reopened.list_probes()["probes"]) == 2
        assert reopened.get_probe(left["id"])["probe"] == left
        imported = module._service_module.Service(tmp_path / "imported")
        result = imported.import_probe(json.dumps(right))
        assert result["origin"] == "imported"
        assert result["probe"] == right
        result = json.loads(
            module._service_module.handle_tool("network_xray_history", {}, imported)
        )
        assert result["ok"] is True
        assert result["result"]["probes"][0]["origin"] == "imported"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_real_api_refuses_credentials_and_nonmatching_comparison(tmp_path):
    app, _ = load_api(tmp_path / "records")
    with TestClient(app) as client:
        response = client.post(
            "/api/plugins/network-xray/probe",
            json={"url": "https://user:TEST-CANARY@example.com/", "label": "Denied input"},
        )
        assert response.status_code == 400
        assert "TEST-CANARY" not in response.text
        assert client.get("/api/plugins/network-xray/probes").json() == {"probes": []}
