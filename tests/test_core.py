"""Synthetic domain fixtures and real loopback-only collector tests."""

import copy
import json
import os
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from network_xray import collector
from network_xray.bundles import overall, parse_bundle, seal_bundle, validate_bundle
from network_xray.compare import compare
from network_xray.store import Store


@pytest.fixture
def synthetic():
    """Explicitly synthetic, never represented as a live receipt."""
    value = collector.empty_bundle(collector.parse_target("http://example.test/"), "Synthetic")
    value["capture"] = {"status": "complete", "duration_ms": 4, "error": None}
    value["stages"] = [
        {
            "name": "dns",
            "status": "ok",
            "duration_ms": 1,
            "summary": "Synthetic DNS",
            "details": {"addresses": ["127.0.0.1"], "truncated": False},
            "error": None,
        },
        {
            "name": "tcp",
            "status": "ok",
            "duration_ms": 1,
            "summary": "Synthetic TCP",
            "details": {"address": "127.0.0.1", "port": 80, "family": "ipv4", "selection": "dns"},
            "error": None,
        },
        {
            "name": "tls",
            "status": "skipped",
            "duration_ms": 0,
            "summary": "Not applicable: HTTP",
            "details": {},
            "error": None,
        },
        {
            "name": "http",
            "status": "ok",
            "duration_ms": 1,
            "summary": "Synthetic HTTP",
            "details": {
                "status_code": 200,
                "reason": "OK",
                "server": "fixture",
                "content_type": "text/plain",
                "redirect": False,
            },
            "error": None,
        },
    ]
    return seal_bundle(value)


def clone(bundle):
    result = copy.deepcopy(bundle)
    result["id"] = str(uuid.uuid4())
    return seal_bundle(result)


@pytest.mark.parametrize(
    "url",
    [
        "https://u:p@example.test/",
        "https://example.test/?",
        "https://example.test/#",
        " https://example.test/",
        "https://example.test/\n",
        "http://a\\b/",
        "http://%65xample.test/",
        "http://[fe80::1%25en0]/",
        "ftp://example.test/",
        "http:///",
        "http://example.test:0/",
        "http://example.test:65536/",
        "http://example.test:/",
        "http://[::1]evil/",
        "http://example.test/%zz",
        "http://example.test/a b",
        "http://169.254.169.254/",
        "http://0.0.0.0/",
        "http://224.0.0.1/",
        "http://[::]/",
        "http://[ff02::1]/",
        "http://127.1/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://bad_host/",
    ],
)
def test_rejected_urls(url):
    with pytest.raises(ValueError):
        collector.parse_target(url)


def test_target_canonicalisation_and_override():
    target = collector.parse_target("HTTPS://EXAMPLE.test:443", "127.0.0.1")
    assert target == {
        "url": "https://example.test/",
        "scheme": "https",
        "host": "example.test",
        "port": 443,
        "path": "/",
        "connect_ip": "127.0.0.1",
    }
    assert collector.parse_target("http://[::1]:8000/a%20b")["host"] == "::1"
    for ip in ("localhost", "169.254.1.2", "0.0.0.0", "224.0.0.1", "fe80::1", "::ffff:169.254.1.2"):
        with pytest.raises(ValueError):
            collector.parse_target("http://example.test/", ip)


def test_bundle_roundtrip_independent_and_digest(synthetic):
    validated = parse_bundle(json.dumps(synthetic))
    assert validated == synthetic and validated is not synthetic
    validated["vantage"]["label"] = "changed"
    with pytest.raises(ValueError):
        validate_bundle(validated)
    assert overall(synthetic) == "healthy"


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), True),
        (("extra",), "secret"),
        (("policy", "tls_verification"), False),
        (("policy", "extra"), 1),
        (("target", "port"), True),
        (("target", "host"), "different.test"),
        (("capture", "duration_ms"), float("inf")),
        (("capture", "duration_ms"), True),
        (("vantage", "extra"), "secret"),
        (("stages", 0, "details", "truncated"), 0),
        (("stages", 1, "details", "address"), "169.254.169.254"),
        (("stages", 3, "details", "status_code"), True),
        (("stages", 3, "details", "redirect"), True),
        (("stages", 3, "details", "cookie"), "secret"),
        (("stages", 3, "error"), {"code": "bad", "message": "x", "secret": "x"}),
        (("stages", 2, "details"), {"verified": False}),
        (("captured_at",), "2020-01-01"),
        (("id",), "../escape"),
    ],
)
def test_nested_tampering_rejected_even_resealed(synthetic, path, value):
    result = copy.deepcopy(synthetic)
    node = result
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(ValueError):
        validate_bundle(seal_bundle(result))


def test_duplicate_keys_and_size(synthetic):
    text = json.dumps(synthetic)
    with pytest.raises(ValueError):
        parse_bundle(
            text.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        )
    with pytest.raises(ValueError):
        parse_bundle('{"x": NaN}')
    with pytest.raises(ValueError):
        parse_bundle(" " * (128 * 1024 + 1))


def test_impossible_progression(synthetic):
    result = copy.deepcopy(synthetic)
    result["stages"][0].update(
        status="error", details={}, error={"code": "dns_failed", "message": "Synthetic failure"}
    )
    with pytest.raises(ValueError):
        validate_bundle(seal_bundle(result))


@contextmanager
def server(
    response=b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n", delay=0, tls_context=None
):
    requests = []

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            connection = self.request
            try:
                if tls_context:
                    connection = tls_context.wrap_socket(connection, server_side=True)
                connection.settimeout(2)
                request = connection.recv(4096)
                requests.append(request)
                time.sleep(delay)
                connection.sendall(response)
            except (OSError, ssl.SSLError):
                pass
            finally:
                connection.close()

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    instance = Server(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance.server_address[1], requests
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join()


@pytest.mark.parametrize(
    "status,expected", [(200, "healthy"), (302, "healthy"), (404, "failed"), (500, "failed")]
)
def test_real_http(status, expected):
    response = f"HTTP/1.1 {status} Fixture\r\nLocation: http://127.0.0.1:1/never\r\nSet-Cookie: secret\r\n\r\n".encode()
    with server(response) as (port, requests):
        result = collector.probe(f"http://127.0.0.1:{port}/chosen", "Loopback")
    validate_bundle(result)
    assert overall(result) == expected
    assert result["stages"][3]["details"]["status_code"] == status
    assert len(requests) == 1 and requests[0].startswith(b"HEAD /chosen HTTP/1.1\r\n")
    assert b"Authorization" not in requests[0] and b"Cookie" not in requests[0]
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize(
    "response",
    [
        b"not http\r\n\r\n",
        b"HTTP/1.1 200 OK\r\n",
        b"HTTP/1.1 200 OK\r\nX: " + b"a" * 17000 + b"\r\n\r\n",
    ],
)
def test_real_invalid_or_oversized_headers(response):
    with server(response) as (port, _):
        result = collector.probe(f"http://127.0.0.1:{port}/", "Loopback")
    assert result["stages"][3]["status"] == "error"
    assert overall(validate_bundle(result)) == "failed"


def test_real_slow_headers():
    with server(delay=3.4) as (port, _):
        result = collector.probe(f"http://127.0.0.1:{port}/", "Loopback")
    assert result["stages"][3]["error"]["code"] == "socket_timeout"
    validate_bundle(result)


def test_real_tcp_refusal():
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        result = collector.probe(f"http://127.0.0.1:{port}/", "Loopback")
    assert result["stages"][1]["status"] == "error"
    assert result["stages"][3]["status"] == "skipped"
    validate_bundle(result)


def test_dns_failure_and_override(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("Synthetic resolver failure")

    monkeypatch.setattr(collector.socket, "getaddrinfo", fail)
    with server() as (port, requests):
        result = collector._collect(
            collector.parse_target(f"http://original.test:{port}/", "127.0.0.1"),
            "Synthetic resolver",
        )
    assert result["stages"][0]["status"] == "error"
    assert result["stages"][1]["details"]["selection"] == "override"
    assert result["stages"][3]["status"] == "ok"
    assert f"Host: original.test:{port}\r\n".encode() in requests[0]
    validate_bundle(result)
    no_override = collector._collect(
        collector.parse_target("http://original.test/"), "Synthetic resolver"
    )
    assert no_override["stages"][1]["status"] == "skipped"
    validate_bundle(no_override)


def test_tls_invalid_certificate(tmp_path):
    key, certificate = tmp_path / "key.pem", tmp_path / "certificate.pem"
    subprocess.run(
        [
            "/usr/bin/openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={"PATH": os.defpath},
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    with server(tls_context=context) as (port, requests):
        result = collector.probe(f"https://localhost:{port}/", "Loopback", connect_ip="127.0.0.1")
    assert result["stages"][2]["status"] == "error"
    assert result["stages"][2]["error"]["code"] == "certificate_invalid"
    assert result["stages"][3]["status"] == "skipped" and not requests
    validate_bundle(result)


def test_portable_copied_cli(tmp_path):
    script = tmp_path / "collector.py"
    shutil.copyfile(collector.__file__, script)
    with server() as (port, _):
        child = subprocess.run(
            [sys.executable, "-I", str(script), f"http://127.0.0.1:{port}/", "--label", "Copied"],
            capture_output=True,
            text=True,
            timeout=15,
            env={"PATH": os.defpath},
            cwd=tmp_path,
        )
    assert child.returncode == 0 and child.stderr == ""
    assert overall(parse_bundle(child.stdout)) == "healthy"
    assert set(tmp_path.iterdir()) == {script}


def test_whole_process_timeout_kills_reaps_and_filters_environment(monkeypatch):
    children = []
    real_popen = subprocess.Popen

    def hanging_worker(command, **kwargs):
        assert "shell" not in kwargs or kwargs["shell"] is False
        assert set(kwargs["env"]) <= {"PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR"}
        assert "-I" in command
        process = real_popen(
            [sys.executable, "-I", "-S", "-c", "import time; time.sleep(60)"], **kwargs
        )
        children.append(process)
        return process

    monkeypatch.setenv("SYNTHETIC_TOKEN", "must-not-inherit")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setattr(collector, "PROCESS_TIMEOUT", 0.2)
    monkeypatch.setattr(collector.subprocess, "Popen", hanging_worker)
    started = time.monotonic()
    result = collector.probe("http://127.0.0.1/", "Timeout fixture")
    assert time.monotonic() - started < 2
    assert children[0].returncode is not None
    with pytest.raises(ProcessLookupError):
        os.kill(children[0].pid, 0)
    assert result["capture"]["status"] == "timeout"
    assert all(stage["status"] == "unknown" for stage in result["stages"])
    assert overall(validate_bundle(result)) == "inconclusive"


def test_compare_healthy_differences_and_suggestions(synthetic):
    right = clone(synthetic)
    right["stages"][0]["details"]["addresses"] = ["127.0.0.2"]
    right["stages"][1]["details"]["address"] = "127.0.0.2"
    result = compare(synthetic, seal_bundle(right))
    assert result["verdict"] == "both_healthy" and result["first_divergence"] == "dns"
    assert all(item["requires_confirmation"] for item in result["next_tests"])
    assert all(item["url"] == synthetic["target"]["url"] for item in result["next_tests"])
    assert any("not authenticated" in text for text in result["limitations"])
    assert set(result) == {
        "schema_version",
        "kind",
        "id",
        "created_at",
        "left",
        "right",
        "verdict",
        "first_divergence",
        "headline",
        "findings",
        "next_tests",
        "limitations",
    }


def test_compare_status_before_details_and_all_verdicts(synthetic):
    failed = clone(synthetic)
    failed["stages"][0]["details"]["addresses"] = ["127.0.0.2"]
    failed["stages"][1]["details"]["address"] = "127.0.0.2"
    failed["stages"][3].update(
        status="error", error={"code": "http_status", "message": "Synthetic 500"}
    )
    failed["stages"][3]["details"]["status_code"] = 500
    failed = seal_bundle(failed)
    assert compare(synthetic, failed)["first_divergence"] == "http"
    assert compare(synthetic, failed)["verdict"] == "diverged"
    assert compare(failed, clone(failed))["verdict"] == "both_failed"
    unknown = collector.empty_bundle(synthetic["target"], "Synthetic timeout")
    unknown["capture"].update(
        status="timeout", error={"code": "deadline_exceeded", "message": "Synthetic"}
    )
    assert compare(synthetic, seal_bundle(unknown))["verdict"] == "inconclusive"
    with pytest.raises(ValueError):
        compare(synthetic, synthetic)
    different = clone(synthetic)
    different["target"] = collector.parse_target("http://other.test/")
    with pytest.raises(ValueError):
        compare(synthetic, seal_bundle(different))


def test_comparison_time_override_and_truncation_limitations(synthetic):
    right = clone(synthetic)
    right["captured_at"] = "2000-01-01T00:00:00Z"
    right["target"]["connect_ip"] = "127.0.0.1"
    right["stages"][1]["details"]["selection"] = "override"
    right["stages"][0]["details"]["truncated"] = True
    text = json.dumps(compare(synthetic, seal_bundle(right))).lower()
    for expected in ("override", "truncat", "single", "time", "host", "sni"):
        assert expected in text


def test_store_private_roundtrip_collision_and_origins(tmp_path, synthetic):
    store = Store(tmp_path / "records")
    saved = store.save_probe(synthetic, "imported")
    assert saved == {"probe": synthetic, "origin": "imported"}
    assert store.get_probe(synthetic["id"]) == saved
    assert store.save_probe(synthetic, "local") == saved
    assert len(store.list_probes()["probes"]) == 1
    changed = copy.deepcopy(synthetic)
    changed["vantage"]["label"] = "Collision"
    with pytest.raises(ValueError):
        store.save_probe(seal_bundle(changed), "imported")
    assert (tmp_path / "records").stat().st_mode & 0o777 == 0o700
    for path in (tmp_path / "records").iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
    for bad in ("../escape", "not-a-uuid", str(uuid.uuid1())):
        with pytest.raises(ValueError):
            store.get_probe(bad)


def test_store_symlink_rejection(tmp_path, synthetic):
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        Store(linked)
    store = Store(tmp_path / "records")
    (store.root / f"{synthetic['id']}.json").symlink_to(outside / "victim")
    with pytest.raises(ValueError):
        store.save_probe(synthetic, "imported")
    with pytest.raises(ValueError):
        store.get_probe(synthetic["id"])
    assert not (outside / "victim").exists()


def test_store_bounded_history_and_thread_safety(tmp_path, synthetic):
    from concurrent.futures import ThreadPoolExecutor

    store = Store(tmp_path / "records")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.save_probe(synthetic, "local"), range(12)))
    assert all(item == results[0] for item in results)
    for index in range(103):
        item = clone(synthetic)
        item["captured_at"] = (
            datetime.fromtimestamp(1_700_000_000 + index, timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        store.save_probe(seal_bundle(item), "local")
    history = store.list_probes()["probes"]
    assert len(history) == 100
    assert history == sorted(
        history, key=lambda item: (item["captured_at"], item["id"]), reverse=True
    )
