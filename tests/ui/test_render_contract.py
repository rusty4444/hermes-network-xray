"""Synthetic browser contract tests; these do NOT prove backend/native integration."""
import functools
import http.server
import os
from pathlib import Path
import subprocess
import tempfile
import threading

import pytest
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def browser_app():
    with tempfile.TemporaryDirectory(prefix="network-xray-ui-", dir=os.environ["TMPDIR"]) as directory:
        build = Path(directory)
        subprocess.run([str(ROOT / "node_modules/.bin/esbuild"), str(ROOT / "tests/ui/harness.js"), "--bundle", "--format=iife", f"--outfile={build / 'bundle.js'}"], check=True, cwd=ROOT)
        (build / "index.html").write_text('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Synthetic UI tests</title><body style="margin:0"><div id="root"></div><script src="/bundle.js"></script></body></html>')
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            yield browser, f"http://127.0.0.1:{server.server_port}"
            browser.close()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def page(browser_app):
    browser, url = browser_app
    page = browser.new_page(viewport={"width": 1280, "height": 1000}, color_scheme="dark")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url)
    expect(page.get_by_role("button", name="Refresh history")).to_be_enabled()
    yield page
    assert not errors
    page.close()


def compare(page):
    ids = page.evaluate("window.mock.ids")
    page.get_by_label("First perspective", exact=True).select_option(ids[0])
    page.get_by_label("Second perspective", exact=True).select_option(ids[1])
    expect(page.get_by_text("TLS verification differs between these captures", exact=True)).to_be_visible()
    return ids


def test_empty_state_never_probes_on_open(page):
    expect(page.get_by_text("Two captures. One clear comparison.")).to_be_visible()
    assert page.evaluate("mock.requests.map(x => x.path)") == ["/probes"]
    expect(page.get_by_role("button", name="Export report")).to_be_disabled()
    page.get_by_role("button", name="Run probe").click()
    expect(page.get_by_role("alert")).to_contain_text("exact HTTP(S) URL")
    assert page.evaluate("mock.requests.filter(x => x.path === '/probe').length") == 0


def test_comparison_evidence_provenance_and_literal_text(page):
    page.evaluate("mock.envelopes[mock.ids[1]].probe.stages[2].details.server_name = '<img src=x onerror=alert(1)>'")
    compare(page)
    expect(page.get_by_text("First observed difference · TLS")).to_be_visible()
    expect(page.get_by_text("Imported · unauthenticated", exact=True)).to_be_visible()
    page.get_by_role("button", name="Synthetic peer: TLS Failed; view evidence", exact=True).click()
    evidence = page.locator("#nx-evidence")
    expect(evidence).to_be_focused()
    expect(evidence).to_contain_text("certificate_sha256")
    expect(evidence).to_contain_text("<img src=x onerror=alert(1)>")
    assert evidence.locator("img").count() == 0
    page.keyboard.press("Escape")
    expect(page.get_by_role("button", name="Synthetic peer: TLS Failed; view evidence", exact=True)).to_be_focused()
    expect(page.get_by_text("HYPOTHESES · NOT PROVEN")).to_be_visible()


def test_suggested_test_requires_confirmation_preserves_target(page):
    compare(page)
    page.get_by_role("button", name="Review test").click()
    button = page.get_by_role("button", name="Run confirmed test here")
    expect(button).to_be_disabled()
    assert page.evaluate("mock.requests.filter(x => x.path === '/probe').length") == 0
    page.get_by_label("Local experiment vantage name").fill("Local follow-up")
    page.get_by_role("checkbox").check()
    button.click()
    expect(page.get_by_text('Captured “Synthetic local”. Saved to this backend’s history.')).to_be_visible()
    request = page.evaluate("mock.requests.find(x => x.path === '/probe')")
    assert request["options"]["body"] == {"url": "https://synthetic.example/", "label": "Local follow-up", "connect_ip": "192.0.2.1"}


def test_selection_race_does_not_replace_newer_capture(page):
    ids = page.evaluate("mock.ids")
    page.evaluate("mock.defer('/probes/' + mock.ids[0])")
    page.get_by_label("First perspective", exact=True).select_option(ids[0])
    expect(page.get_by_text("Loading recorded evidence…")).to_be_visible()
    page.get_by_label("First perspective", exact=True).select_option(ids[2])
    expect(page.get_by_role("heading", name="Synthetic third")).to_be_visible()
    page.evaluate("mock.pending['/probes/' + mock.ids[0]].resolve(mock.envelopes[mock.ids[0]])")
    expect(page.get_by_role("heading", name="Synthetic third")).to_be_visible()
    assert page.get_by_role("heading", name="Synthetic local", exact=True).count() == 0


def test_comparison_race_cannot_restore_old_verdict(page):
    ids = page.evaluate("mock.ids")
    page.evaluate("mock.defer('/compare')")
    page.get_by_label("First perspective", exact=True).select_option(ids[0])
    page.get_by_label("Second perspective", exact=True).select_option(ids[1])
    expect(page.get_by_text("Comparing recorded observations…")).to_be_visible()
    page.get_by_label("Second perspective", exact=True).select_option("")
    page.evaluate("mock.pending['/compare'].resolve(mock.comparison)")
    expect(page.get_by_role("button", name="Export report")).to_be_disabled()
    assert page.get_by_text("TLS verification differs between these captures", exact=True).count() == 0


def test_owner_change_invalidates_pending_capture(page):
    page.evaluate("mock.defer('/probe')")
    page.get_by_label("Target URL", exact=True).fill("https://synthetic.example/")
    page.get_by_role("button", name="Run probe").click()
    expect(page.get_by_role("button", name="Waiting for capture…")).to_be_disabled()
    page.evaluate("mock.setOwner('synthetic-owner-B'); mock.pending['/probe'].resolve(mock.envelopes[mock.ids[0]])")
    expect(page.get_by_text("Backend scope: synthetic-owner-B")).to_be_visible()
    expect(page.get_by_label("First perspective", exact=True)).to_have_value("")
    expect(page.get_by_label("Target URL", exact=True)).to_have_value("")
    assert page.get_by_role("heading", name="Synthetic local", exact=True).count() == 0


def test_timeout_is_inconclusive_and_retry_is_available(page):
    page.evaluate("() => { mock.handlers['/probe'] = () => { throw new Error('request timed out'); }; }")
    page.get_by_label("Target URL", exact=True).fill("https://synthetic.example/")
    page.get_by_role("button", name="Run probe").click()
    expect(page.get_by_role("alert")).to_contain_text("not evidence of a DNS or connection failure")
    expect(page.get_by_role("button", name="Run probe")).to_be_enabled()


def test_import_size_json_errors_and_download(page):
    page.get_by_text("Add the other perspective", exact=True).click()
    upload = page.get_by_label("Import peer bundle", exact=True)
    upload.set_input_files({"name": "oversized.json", "mimeType": "application/json", "buffer": b" " * (128 * 1024 + 1)})
    expect(page.get_by_role("alert")).to_contain_text("larger than 128 KiB")
    upload.set_input_files({"name": "invalid.json", "mimeType": "application/json", "buffer": b"{not-json}"})
    expect(page.get_by_role("alert")).to_contain_text("not valid JSON")
    assert page.evaluate("mock.requests.filter(x => x.path === '/import').length") == 0
    with page.expect_download() as download:
        page.get_by_role("button", name="Download collector").click()
    assert download.value.suggested_filename == "synthetic-collector.py"


def test_unknown_stages_and_override_are_not_normal_success(page):
    page.evaluate("""() => {
      const probe = mock.envelopes[mock.ids[0]].probe;
      probe.capture.status = 'timeout'; probe.capture.duration_ms = null;
      probe.target.connect_ip = '192.0.2.3';
      probe.stages.forEach(stage => { stage.status = 'unknown'; stage.duration_ms = null; stage.details = {}; stage.summary = 'No stage evidence escaped'; });
    }""")
    page.get_by_label("First perspective", exact=True).select_option(page.evaluate("mock.ids[0]"))
    expect(page.get_by_text("inconclusive", exact=True)).to_be_visible()
    expect(page.get_by_text("Explicit connect-IP override: 192.0.2.3 · original Host/SNI retained")).to_be_visible()
    assert page.get_by_text("Unknown", exact=True).count() == 4
    assert page.locator(".nx-stage-time").filter(has_text="Not measured").count() == 4


def test_strict_mode_mount_effect_replay_remains_usable(page):
    page.goto(page.url + '?strict')
    expect(page.get_by_role("button", name="Refresh history")).to_be_enabled()
    compare(page)
    assert page.evaluate("mock.requests.filter(x => x.path === '/probe').length") == 0


def test_owner_roundtrip_does_not_revive_old_async_results(page):
    page.evaluate("mock.defer('/probe')")
    page.get_by_label("Target URL", exact=True).fill("https://synthetic.example/")
    page.get_by_role("button", name="Run probe").click()
    expect(page.get_by_role("button", name="Waiting for capture…")).to_be_disabled()
    page.evaluate("mock.setOwner('synthetic-owner-B'); mock.setOwner('synthetic-owner-A'); mock.pending['/probe'].resolve(mock.envelopes[mock.ids[0]])")
    expect(page.get_by_label("First perspective", exact=True)).to_have_value("")
    assert page.get_by_role("heading", name="Synthetic local", exact=True).count() == 0


def test_report_download_is_explicit_and_keeps_selected_ids(page):
    ids = compare(page)
    assert page.evaluate("mock.requests.filter(x => x.path.startsWith('/export/')).length") == 0
    with page.expect_download() as download:
        page.get_by_role("button", name="Export report").click()
    assert download.value.suggested_filename == "synthetic-report.html"
    assert page.evaluate("mock.requests.filter(x => x.path.startsWith('/export/')).at(-1).path") == f"/export/{ids[0]}/{ids[1]}"


def test_duplicate_keys_are_rejected_before_import_transport(page):
    page.get_by_text("Add the other perspective", exact=True).click()
    page.get_by_label("Import peer bundle", exact=True).set_input_files({"name": "duplicate.json", "mimeType": "application/json", "buffer": b'{"id":"one","id":"two"}'})
    expect(page.get_by_role("alert")).to_contain_text("duplicate keys")
    assert page.evaluate("mock.requests.filter(x => x.path === '/import').length") == 0


def test_different_target_urls_do_not_request_comparison(page):
    page.evaluate("mock.envelopes[mock.ids[1]].probe.target.url = 'https://different.example/'")
    ids = page.evaluate("mock.ids")
    page.get_by_label("First perspective", exact=True).select_option(ids[0])
    page.get_by_label("Second perspective", exact=True).select_option(ids[1])
    expect(page.get_by_role("alert")).to_contain_text("different URLs")
    assert page.evaluate("mock.requests.filter(x => x.path === '/compare').length") == 0


def test_narrow_layout_has_no_horizontal_overflow(page):
    page.set_viewport_size({"width": 390, "height": 844})
    compare(page)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.locator(".nx-root").evaluate("el => el.scrollWidth <= el.clientWidth")
    page.emulate_media(reduced_motion="reduce")
    expect(page.get_by_role("button", name="Review test")).to_be_visible()
