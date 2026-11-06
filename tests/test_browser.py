"""Browser end-to-end flow against the real HTTP adapter and real loopback collector."""

import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.request import urlopen
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.sync_api import sync_playwright, expect

from network_xray import collector
from network_xray.bundles import parse_bundle, seal_bundle

ROOT = Path(__file__).resolve().parents[1]


class FixtureHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        pass


@pytest.fixture
def workbench(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with (tmp_path / "workbench.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-E",
                str(ROOT / "scripts/serve.py"),
                "--data",
                str(tmp_path / "records"),
                "--port",
                str(port),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError((tmp_path / "workbench.log").read_text())
                try:
                    with urlopen(base + "/api/plugins/network-xray/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.05)
            else:
                raise AssertionError("Workbench did not start")
            yield base
        finally:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_real_probe_import_compare_evidence_and_download(workbench, tmp_path):
    service = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    target = f"http://127.0.0.1:{service.server_port}/health"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(workbench)
            expect(page.get_by_role("button", name="Run probe")).to_be_enabled()
            page.get_by_label("Target URL", exact=True).fill(target)
            page.get_by_label("Name this backend’s vantage", exact=True).fill(
                "Local fixture running"
            )
            page.get_by_role("button", name="Run probe").click()
            expect(
                page.get_by_text(
                    "Captured “Local fixture running”. Saved to this backend’s history."
                )
            ).to_be_visible(timeout=20000)
            with urlopen(workbench + "/api/plugins/network-xray/probes") as response:
                history = json.load(response)["probes"]
            left_id = history[0]["id"]
            service.shutdown()
            service.server_close()
            thread.join(timeout=3)
            copied_collector = tmp_path / "portable.py"
            copied_collector.write_bytes((ROOT / "network_xray/collector.py").read_bytes())
            peer = subprocess.run(
                [
                    sys.executable,
                    "-E",
                    str(copied_collector),
                    target,
                    "--label",
                    "Recorded local failure",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            # A failed network stage is still a valid collected observation.
            bundle = json.loads(peer.stdout)
            assert bundle["stages"][1]["status"] == "error"
            bundle_file = tmp_path / "peer.json"
            bundle_file.write_text(peer.stdout)
            page.get_by_text("Add the other perspective", exact=True).click()
            page.get_by_label("Import peer bundle", exact=True).set_input_files(bundle_file)
            expect(
                page.get_by_label("Second perspective", exact=True).locator(
                    f'option[value="{bundle["id"]}"]'
                )
            ).to_be_attached(timeout=10000)
            page.get_by_label("First perspective", exact=True).select_option(left_id)
            page.get_by_label("Second perspective", exact=True).select_option(bundle["id"])
            expect(page.get_by_text("First observed difference · TCP")).to_be_visible(timeout=10000)
            expect(page.get_by_text("Imported · unauthenticated", exact=True)).to_be_visible()
            page.get_by_role(
                "button", name="Recorded local failure: TCP Failed; view evidence", exact=True
            ).click()
            expect(page.locator("#nx-evidence")).to_contain_text("error")
            with page.expect_download() as download:
                page.get_by_role("button", name="Export report").click()
            report_path = tmp_path / "report.html"
            download.value.save_as(report_path)
            report = report_path.read_text()
            assert "Recorded local failure" in report
            assert "<script" not in report
            assert bundle["integrity"]["digest"] in report
            assert not errors
            browser.close()
    finally:
        service.shutdown()
        service.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("adapter", ["standalone", "native_adapter_contract"])
@pytest.mark.parametrize("number_form", ["integral_float", "exponent", "negative_zero"])
def test_import_numeric_forms_through_actual_ui_and_router(
    workbench, tmp_path, adapter, number_form
):
    """Synthetic sealed inputs; real shared UI, adapter, router and storage."""
    bundle = collector.empty_bundle(
        collector.parse_target("https://example.test/"), "Synthetic float import"
    )
    bundle["capture"] = {
        "status": "timeout",
        "duration_ms": 12000.0,
        "error": {"code": "deadline_exceeded", "message": "Synthetic timeout"},
    }
    if number_form == "negative_zero":
        bundle["stages"][0]["duration_ms"] = -0.0
    bundle = seal_bundle(bundle)
    raw = json.dumps(bundle, separators=(",", ":"))
    if number_form == "exponent":
        raw = raw.replace('"duration_ms":12000.0', '"duration_ms":1.2e4')
    assert parse_bundle(raw) == bundle
    native_bundle = tmp_path / "native-harness.js"
    if adapter == "native_adapter_contract":
        subprocess.run(
            [
                str(ROOT / "node_modules/.bin/esbuild"),
                str(ROOT / "tests/ui/native-transport-harness.js"),
                "--bundle",
                "--format=esm",
                f"--outfile={native_bundle}",
                f"--alias:@hermes/plugin-sdk={ROOT / 'tests/ui/sdk-test-shim.js'}",
            ],
            check=True,
            cwd=ROOT,
        )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            if adapter == "native_adapter_contract":
                page.route(
                    "**/app.js",
                    lambda route: route.fulfill(
                        path=str(native_bundle), content_type="text/javascript"
                    ),
                )
            page.goto(workbench)
            page.get_by_text("Add the other perspective", exact=True).click()
            with page.expect_response("**/api/plugins/network-xray/import") as imported:
                page.get_by_label("Import peer bundle", exact=True).set_input_files(
                    {
                        "name": "synthetic.json",
                        "mimeType": "application/json",
                        "buffer": raw.encode(),
                    }
                )
            response = imported.value
            assert response.request.post_data_json == {"bundle_json": raw}
            assert response.status == 200, response.text()
            expect(
                page.get_by_label("First perspective", exact=True).locator(
                    f'option[value="{bundle["id"]}"]'
                )
            ).to_be_attached()
            with urlopen(workbench + "/api/plugins/network-xray/probes/" + bundle["id"]) as saved:
                result = json.load(saved)
            assert result["origin"] == "imported"
            assert result["probe"]["id"] == bundle["id"]
            assert parse_bundle(json.dumps(result["probe"]))["integrity"] == bundle["integrity"]
        finally:
            browser.close()


def _native_harness(tmp_path):
    """The native adapter bundled with a ctx.rest that rejects as Hermes Desktop does."""
    native_bundle = tmp_path / "native-harness.js"
    subprocess.run(
        [
            str(ROOT / "node_modules/.bin/esbuild"),
            str(ROOT / "tests/ui/native-transport-harness.js"),
            "--bundle",
            "--format=esm",
            f"--outfile={native_bundle}",
            f"--alias:@hermes/plugin-sdk={ROOT / 'tests/ui/sdk-test-shim.js'}",
        ],
        check=True,
        cwd=ROOT,
    )
    return native_bundle


@pytest.mark.parametrize("adapter", ["standalone", "native_adapter_contract"])
def test_a_rejected_import_shows_the_backend_detail_in_both_adapters(workbench, tmp_path, adapter):
    """A real 400 from the real router reads the same in both adapters, without the IPC wrapper."""
    native_bundle = _native_harness(tmp_path) if adapter == "native_adapter_contract" else None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            if native_bundle:
                page.route(
                    "**/app.js",
                    lambda route: route.fulfill(path=str(native_bundle), content_type="text/javascript"),
                )
            page.goto(workbench)
            page.get_by_text("Add the other perspective", exact=True).click()
            with page.expect_response("**/api/plugins/network-xray/import") as imported:
                page.get_by_label("Import peer bundle", exact=True).set_input_files(
                    {
                        "name": "not-a-bundle.json",
                        "mimeType": "application/json",
                        "buffer": b'{"kind": "not a probe bundle"}',
                    }
                )
            assert imported.value.status == 400
            expect(
                page.get_by_text(
                    "Invalid input: check URL, fields, bundle schema/digest, and matching targets",
                    exact=True,
                )
            ).to_be_visible()
            assert "Error invoking" not in page.locator("body").inner_text()
            assert "hermes:api" not in page.locator("body").inner_text()
        finally:
            browser.close()


def _open(playwright, workbench, native_bundle):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    if native_bundle:
        page.route("**/app.js", lambda route: route.fulfill(path=str(native_bundle), content_type="text/javascript"))
    page.goto(workbench)
    page.get_by_text("Add the other perspective", exact=True).click()
    return browser, page


@pytest.mark.parametrize("adapter", ["standalone", "native_adapter_contract"])
def test_a_bad_file_is_never_reported_as_a_backend_failure(workbench, tmp_path, adapter):
    """The browser's JSON.parse message quotes the file, which must not trip the connection heuristics."""
    native_bundle = _native_harness(tmp_path) if adapter == "native_adapter_contract" else None
    with sync_playwright() as playwright:
        browser, page = _open(playwright, workbench, native_bundle)
        try:
            requests = []
            page.on("request", lambda request: requests.append(request.url) if "/import" in request.url else None)
            page.get_by_label("Import peer bundle", exact=True).set_input_files(
                # Short enough that V8 quotes all of it in the JSON.parse message.
                {"name": "notes.json", "mimeType": "application/json", "buffer": b"Network error"}
            )
            expect(page.get_by_text("This file is not valid JSON", exact=False)).to_be_visible()
            assert "Could not reach" not in page.locator("body").inner_text()
            assert requests == []
        finally:
            browser.close()


@pytest.mark.parametrize("adapter", ["standalone", "native_adapter_contract"])
def test_a_proxy_error_page_reads_as_a_backend_failure_without_markup(workbench, tmp_path, adapter):
    native_bundle = _native_harness(tmp_path) if adapter == "native_adapter_contract" else None
    with sync_playwright() as playwright:
        browser, page = _open(playwright, workbench, native_bundle)
        try:
            page.route(
                "**/api/plugins/network-xray/import",
                lambda route: route.fulfill(status=502, content_type="text/html", body="<html><h1>Bad Gateway</h1></html>"),
            )
            page.get_by_label("Import peer bundle", exact=True).set_input_files(
                {"name": "peer.json", "mimeType": "application/json", "buffer": b'{"kind": "probe"}'}
            )
            expect(page.get_by_text("The Network X-ray backend failed (HTTP 502).", exact=False)).to_be_visible()
            body = page.locator("body").inner_text()
            assert "Bad Gateway" not in body and "<html" not in body and "Check the URL" not in body
        finally:
            browser.close()
