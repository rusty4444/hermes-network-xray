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
