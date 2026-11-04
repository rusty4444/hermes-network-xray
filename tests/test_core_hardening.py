"""Additional adversarial, synthetic-boundary, and loopback TLS evidence."""

import copy
import importlib
import json
import os
import socket
import ssl
import subprocess
import time

import pytest

from network_xray import collector
from network_xray.bundles import parse_bundle, seal_bundle, validate_bundle
from network_xray.store import Store
import test_core
from test_core import clone, server

synthetic = test_core.synthetic


@pytest.mark.parametrize(
    "url",
    [
        "http://example.test../",
        "http://example.test/<bad>",
        "http://example.test/|bad",
        "http://example.test/`bad",
        "http://example.test/{bad}",
    ],
)
def test_rfc_hostname_and_path(url):
    with pytest.raises(ValueError):
        collector.parse_target(url)


@pytest.mark.parametrize("label", ["", "a" * 49, "line\nfeed", "tab\tlabel", 23, None])
def test_invalid_labels_never_launch(label, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Invalid request reached subprocess")

    monkeypatch.setattr(collector.subprocess, "Popen", unexpected)
    with pytest.raises(ValueError):
        collector.probe("http://127.0.0.1/", label)


def test_dns_truncation_and_single_selection(monkeypatch):
    addresses = [f"127.0.0.{index}" for index in range(1, 11)]

    def resolve(*args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 80))
            for address in addresses + addresses
        ]

    monkeypatch.setattr(collector.socket, "getaddrinfo", resolve)
    with server() as (port, requests):
        result = collector._collect(
            collector.parse_target(f"http://fixture.test:{port}/"), "Synthetic DNS"
        )
    dns = result["stages"][0]["details"]
    assert dns == {"addresses": addresses[:8], "truncated": True}
    assert result["stages"][1]["details"]["address"] == addresses[0]
    assert len(requests) == 1
    validate_bundle(result)


@pytest.mark.parametrize(
    "address", ["169.254.169.254", "0.0.0.0", "224.0.0.1", "fe80::1", "::ffff:169.254.169.254"]
)
def test_forbidden_dns_destination_never_connects(monkeypatch, address):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(
        collector.socket,
        "getaddrinfo",
        lambda *a, **k: [(family, socket.SOCK_STREAM, 6, "", (address, 80))],
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("Forbidden address reached socket")

    monkeypatch.setattr(collector.socket, "socket", unexpected)
    result = collector._collect(collector.parse_target("http://fixture.test/"), "Synthetic DNS")
    assert result["stages"][0]["status"] == "error"
    assert result["stages"][1]["status"] == "skipped"
    validate_bundle(result)


def test_real_dns_failure_numeric_no_external_query():
    # A numeric literal with an unsupported numeric family produces an actual
    # getaddrinfo error without any public DNS query. Injection is test-only.
    original = collector.socket.getaddrinfo

    def fail_numeric(*args, **kwargs):
        return original("::1", 80, socket.AF_INET, socket.SOCK_STREAM, flags=socket.AI_NUMERICHOST)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(collector.socket, "getaddrinfo", fail_numeric)
        result = collector._collect(
            collector.parse_target("http://127.0.0.1/"), "Controlled resolver fault"
        )
    assert result["stages"][0]["error"]["code"] == "dns_failed"
    assert result["stages"][1]["status"] == "skipped"
    validate_bundle(result)


def test_verified_tls_preserves_override_sni_and_host(tmp_path, monkeypatch):
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
            "/CN=fixture.test",
            "-addext",
            "subjectAltName=DNS:fixture.test",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={"PATH": os.defpath},
    )
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certificate, key)
    names = []
    server_context.set_servername_callback(lambda connection, name, context: names.append(name))
    trusted_context = ssl.create_default_context(cafile=str(certificate))
    assert trusted_context.verify_mode == ssl.CERT_REQUIRED and trusted_context.check_hostname
    monkeypatch.setattr(collector.ssl, "create_default_context", lambda: trusted_context)
    monkeypatch.setattr(
        collector.socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.2", 80))],
    )
    with server(tls_context=server_context) as (port, requests):
        result = collector._collect(
            collector.parse_target(f"https://fixture.test:{port}/secure", "127.0.0.1"),
            "Loopback trust fixture",
        )
    assert result["stages"][2]["status"] == "ok"
    assert result["stages"][2]["details"]["verified"] is True
    assert len(result["stages"][2]["details"]["certificate_sha256"]) == 64
    assert names == ["fixture.test"]
    assert f"Host: fixture.test:{port}\r\n".encode() in requests[0]
    validate_bundle(result)


def test_real_worker_sees_only_clean_environment(tmp_path, monkeypatch):
    script = tmp_path / "env_worker.py"
    script.write_text(
        "import json, os, sys\nprint(json.dumps({'environment_keys': list(os.environ), 'isolated': sys.flags.isolated, 'no_site': sys.flags.no_site}))\n"
    )
    monkeypatch.setattr(collector, "__file__", str(script))
    for key in (
        "SYNTHETIC_TOKEN",
        "AWS_SECRET_ACCESS_KEY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "SSL_CERT_FILE",
        "PYTHONPATH",
    ):
        monkeypatch.setenv(key, "synthetic-never-inherit")
    result = collector._run_worker(collector.parse_target("http://127.0.0.1/"), "Clean env fixture")
    # macOS/CPython may inject locale metadata after exec, not credentials.
    assert set(result["environment_keys"]) <= {
        "PATH",
        "LANG",
        "LC_CTYPE",
        "SYSTEMROOT",
        "WINDIR",
        "__CF_USER_TEXT_ENCODING",
    }
    assert result["isolated"] == 1 and result["no_site"] == 1
    assert "synthetic-never-inherit" not in json.dumps(result)


def test_real_copied_worker_dns_hang_is_killed(tmp_path, monkeypatch):
    script = tmp_path / "dns_hang.py"
    script.write_text(
        "import socket, time\nsocket.getaddrinfo = lambda *a, **k: time.sleep(60)\nsocket.getaddrinfo('localhost', 80)\n"
    )
    monkeypatch.setattr(collector, "__file__", str(script))
    monkeypatch.setattr(collector, "PROCESS_TIMEOUT", 0.2)
    processes = []
    real_popen = subprocess.Popen

    def record(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        processes.append(child)
        return child

    monkeypatch.setattr(collector.subprocess, "Popen", record)
    started = time.monotonic()
    result = collector.probe("http://127.0.0.1/", "Controlled DNS hang")
    assert time.monotonic() - started < 2
    assert processes[0].returncode is not None
    with pytest.raises(ChildProcessError):
        os.waitpid(processes[0].pid, os.WNOHANG)
    assert result["capture"]["status"] == "timeout"
    assert all(stage["status"] == "unknown" for stage in result["stages"])
    validate_bundle(result)


def test_worker_oversized_output_is_bounded_and_reaped(tmp_path, monkeypatch):
    script = tmp_path / "oversized_worker.py"
    script.write_text("import sys\nsys.stdout.write('x' * 500000)\nsys.stdout.flush()\n")
    monkeypatch.setattr(collector, "__file__", str(script))
    monkeypatch.setattr(collector, "PROCESS_TIMEOUT", 0.2)
    result = collector.probe("http://127.0.0.1/", "Oversized worker fixture")
    assert result["capture"]["status"] in ("failed", "timeout")
    validate_bundle(result)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b["stages"].reverse(),
        lambda b: b["stages"][0]["details"].update(addresses=["127.0.0.1"] * 9),
        lambda b: b["stages"][0]["details"].update(addresses=["127.0.0.1"] * 2),
        lambda b: b["stages"][1]["details"].update(selection="override"),
        lambda b: b["stages"][1]["details"].update(family="ipv6"),
        lambda b: b["stages"][1]["details"].update(port=81),
        lambda b: b["capture"].update(duration_ms=-1),
        lambda b: b["capture"].update(duration_ms=60001),
        lambda b: b["capture"].update(status="timeout"),
        lambda b: b["stages"][3].update(status="unknown"),
        lambda b: b["stages"][3]["details"].update(status_code=199),
        lambda b: b["stages"][3]["details"].update(reason="x" * 241),
    ],
)
def test_more_invalid_bundles(synthetic, mutate):
    value = copy.deepcopy(synthetic)
    mutate(value)
    with pytest.raises(ValueError):
        validate_bundle(seal_bundle(value))


def test_nested_duplicate_key(synthetic):
    text = json.dumps(synthetic).replace(
        '"label": "Synthetic"', '"label": "Synthetic", "label": "Synthetic"'
    )
    with pytest.raises(ValueError):
        parse_bundle(text)


def test_store_cap_does_not_delete_existing_records(tmp_path, synthetic, monkeypatch):
    module = importlib.import_module("network_xray.store")
    monkeypatch.setattr(module, "MAX_RECORDS", 2)
    store = Store(tmp_path / "records")
    first = store.save_probe(synthetic, "local")
    store.save_probe(clone(synthetic), "imported")
    with pytest.raises(ValueError, match="limit"):
        store.save_probe(clone(synthetic), "local")
    assert store.get_probe(synthetic["id"]) == first
    assert len(store.list_probes()["probes"]) == 2
    assert store.save_probe(synthetic, "imported") == first


def test_store_replaced_root_symlink_and_ancestor_rejected(tmp_path, synthetic):
    root = tmp_path / "records"
    store = Store(root)
    root.rename(tmp_path / "original")
    outside = tmp_path / "outside"
    outside.mkdir()
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        store.save_probe(synthetic, "local")
    with pytest.raises(ValueError):
        Store(root / "nested")
    assert not list(outside.iterdir())


def test_store_read_tampering_fails_closed(tmp_path, synthetic):
    store = Store(tmp_path / "records")
    store.save_probe(synthetic, "local")
    path = store.root / f"{synthetic['id']}.json"
    raw = json.loads(path.read_text())
    raw["probe"]["vantage"]["label"] = "Tampered"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        store.get_probe(synthetic["id"])
    with pytest.raises(ValueError):
        store.list_probes()


@pytest.mark.parametrize("label", ["--worker", "-h", "Vantage Ω", "two words"])
def test_valid_option_like_labels_are_data(label):
    with server() as (port, _):
        result = collector.probe(f"http://127.0.0.1:{port}/", label)
    assert result["vantage"]["label"] == label
    assert result["stages"][3]["status"] == "ok"
    validate_bundle(result)


def test_comparison_describes_different_failures_without_common_cause(synthetic):
    from network_xray.compare import compare

    left = copy.deepcopy(synthetic)
    left["stages"][1].update(
        status="error",
        details={},
        error={"code": "connection_refused", "message": "Controlled refusal"},
    )
    left["stages"][3].update(status="skipped", details={}, error=None)
    left = seal_bundle(left)
    right = clone(left)
    right["stages"][1]["error"] = {"code": "socket_timeout", "message": "Controlled timeout"}
    result = compare(left, seal_bundle(right))
    assert result["verdict"] == "both_failed"
    text = json.dumps(result["findings"])
    assert "connection_refused" in text and "socket_timeout" in text
    assert "does not establish a common cause" in result["headline"]


def test_comparison_output_deterministic_except_identifiers(synthetic):
    from network_xray.compare import compare

    right = clone(synthetic)
    first, second = compare(synthetic, right), compare(synthetic, right)
    for result in (first, second):
        result.pop("id")
        result.pop("created_at")
    assert first == second
