"""Portable, stdlib-only HEAD collector. Copy this file unchanged to a peer.

Direct sockets deliberately ignore proxies. A supervised isolated child bounds OS
DNS hangs; no partial observations are asserted when that child misses its deadline.
"""

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
import platform
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import uuid

SOCKET_TIMEOUT = 3.0
PROCESS_TIMEOUT = 12.0
MAX_BUNDLE_BYTES = 128 * 1024
MAX_HEADER_BYTES = 16 * 1024
STAGE_NAMES = ("dns", "tcp", "tls", "http")
POLICY = {
    "method": "HEAD",
    "redirects": "not_followed",
    "tls_verification": True,
    "proxy": "direct",
    "body_capture": False,
}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def permitted_ip(value):
    """Return canonical numeric IP; reject scoped/special-use destinations."""
    if not isinstance(value, str) or "%" in value:
        raise ValueError("An unscoped numeric IP is required")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise ValueError("An unscoped numeric IP is required") from None
    effective = getattr(address, "ipv4_mapped", None) or address
    if effective.is_link_local or effective.is_multicast or effective.is_unspecified:
        raise ValueError("Link-local, multicast and unspecified destinations are forbidden")
    return str(address)


def _hostname(raw):
    if "%" in raw:
        raise ValueError("Percent escapes and IPv6 zones are forbidden in hosts")
    try:
        ipaddress.ip_address(raw)
    except ValueError:
        pass
    else:
        return permitted_ip(raw)
    # Avoid platform-specific legacy IPv4 parsing (127.1, octal, hex, integers).
    if re.fullmatch(r"[0-9.]+", raw) or re.fullmatch(
        r"(?i)(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*", raw
    ):
        raise ValueError("Ambiguous numeric host")
    try:
        host = raw.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise ValueError("Invalid hostname") from None
    labels = host.rstrip(".").split(".")
    if len(host) > 253 or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", item) for item in labels
    ):
        raise ValueError("Invalid hostname")
    return host


def parse_target(url, connect_ip=None):
    """Validate and canonicalise only scheme/host/default port/empty path."""
    if not isinstance(url, str) or not 1 <= len(url) <= 2048:
        raise ValueError("URL must contain 1..2048 characters")
    if any(ord(char) <= 32 or ord(char) == 127 for char in url) or any(
        char in url for char in "\\?#"
    ):
        raise ValueError("URL whitespace, controls, backslashes, query and fragment are forbidden")
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc or "@" in parts.netloc:
            raise ValueError("Explicit HTTP(S) URL without credentials required")
        authority = parts.netloc
        if authority.startswith("["):
            match = re.fullmatch(r"\[([^]]+)\](?::([0-9]+))?", authority)
            if not match or ":" not in match[1]:
                raise ValueError("Invalid bracketed host")
        else:
            match = re.fullmatch(r"([^:]+)(?::([0-9]+))?", authority)
            if not match:
                raise ValueError("Invalid host or port")
        host = _hostname(match[1])
        default_port = 443 if parts.scheme == "https" else 80
        port = int(match[2]) if match[2] is not None else default_port
        if not 1 <= port <= 65535:
            raise ValueError("Port must be 1..65535")
        path = parts.path or "/"
        if not re.fullmatch(r"/[A-Za-z0-9._~!$&'()*+,;=:@/%-]*", path) or re.search(
            r"%(?![0-9a-fA-F]{2})", path
        ):
            raise ValueError(
                "Path must contain URI path characters with well-formed percent escapes"
            )
        override = permitted_ip(connect_ip) if connect_ip is not None else None
    except (UnicodeError, OverflowError, ValueError) as error:
        raise ValueError(str(error)) from None
    authority = f"[{host}]" if ":" in host else host
    if port != default_port:
        authority += f":{port}"
    canonical = f"{parts.scheme}://{authority}{path}"
    if len(canonical) > 2048:
        raise ValueError("Canonical URL exceeds limit")
    return {
        "url": canonical,
        "scheme": parts.scheme,
        "host": host,
        "port": port,
        "path": path,
        "connect_ip": override,
    }


def validate_label(label):
    if not isinstance(label, str) or not 1 <= len(label) <= 48 or not label.isprintable():
        raise ValueError("Label must contain 1..48 printable characters")
    return label


def seal_bundle(value):
    """Content checksum, not authentication. Domain validation lives in bundles.py."""
    try:
        result = copy.deepcopy(value)
        result.pop("integrity", None)
        encoded = json.dumps(
            result, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
        result["integrity"] = {"algorithm": "sha256", "digest": hashlib.sha256(encoded).hexdigest()}
        if len(json.dumps(result, ensure_ascii=True).encode("utf-8")) > MAX_BUNDLE_BYTES:
            raise ValueError("Bundle exceeds 128 KiB")
        return result
    except (TypeError, OverflowError, RecursionError, AttributeError):
        raise ValueError("Bundle is not bounded JSON data") from None


def empty_bundle(target, label):
    return {
        "schema_version": 1,
        "kind": "network_xray.probe",
        "id": str(uuid.uuid4()),
        "captured_at": utc_now(),
        "vantage": {
            "label": validate_label(label),
            "platform": sys.platform,
            "python": platform.python_version(),
        },
        "target": copy.deepcopy(target),
        "policy": dict(POLICY),
        "capture": {"status": "failed", "duration_ms": 0, "error": None},
        "stages": [
            {
                "name": name,
                "status": "unknown",
                "duration_ms": 0,
                "summary": "No observation received",
                "details": {},
                "error": None,
            }
            for name in STAGE_NAMES
        ],
    }


def _elapsed(start):
    return round(min(60000, max(0, (time.monotonic() - start) * 1000)), 3)


def _safe_text(value, limit=240):
    return "".join(char if char.isprintable() else " " for char in str(value))[:limit]


def _error(error):
    if isinstance(error, ssl.SSLCertVerificationError):
        code, message = "certificate_invalid", "Certificate verification failed"
    elif isinstance(error, (TimeoutError, socket.timeout)):
        code, message = "socket_timeout", "Socket operation exceeded its deadline"
    elif isinstance(error, socket.gaierror):
        code, message = "dns_failed", "Name resolution failed"
    elif isinstance(error, ConnectionRefusedError):
        code, message = "connection_refused", "Connection refused"
    elif isinstance(error, ValueError):
        code, message = "invalid_response_or_address", _safe_text(error, 400)
    elif isinstance(error, ssl.SSLError):
        code, message = "tls_failed", "TLS negotiation failed"
    else:
        code, message = "network_error", "Network operation failed"
    return {"code": code, "message": message}


def _stage(bundle, index, action):
    started = time.monotonic()
    stage = bundle["stages"][index]
    try:
        summary, details = action()
        stage.update(status="ok", summary=summary, details=details)
    except (OSError, ValueError) as error:
        stage.update(
            status="error",
            summary=f"{stage['name'].upper()} failed",
            details={},
            error=_error(error),
        )
    stage["duration_ms"] = _elapsed(started)
    return stage["status"] == "ok"


def _resolve(target):
    records = socket.getaddrinfo(target["host"], target["port"], type=socket.SOCK_STREAM)
    addresses = []
    truncated = False
    for family, _, _, _, address in records:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        ip = permitted_ip(address[0])
        if ip not in addresses:
            if len(addresses) < 8:
                addresses.append(ip)
            else:
                truncated = True
    if not addresses:
        raise ValueError("Resolver returned no usable addresses")
    return f"Resolved {len(addresses)} recorded addresses", {
        "addresses": addresses,
        "truncated": truncated,
    }


def _connect(target, address, connections):
    address = permitted_ip(address)
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    connection = socket.socket(family, socket.SOCK_STREAM)
    connections.append(connection)
    connection.settimeout(SOCKET_TIMEOUT)
    connection.connect((address, target["port"]))
    return "Connected", {
        "address": address,
        "port": target["port"],
        "family": "ipv6" if family == socket.AF_INET6 else "ipv4",
        "selection": "override" if target["connect_ip"] else "dns",
    }


def _tls(target, connections):
    context = ssl.create_default_context()
    wrapped = context.wrap_socket(connections[-1], server_hostname=target["host"])
    connections.append(wrapped)
    certificate = wrapped.getpeercert()
    expiry = certificate.get("notAfter")
    expires_at = (
        datetime.fromtimestamp(ssl.cert_time_to_seconds(expiry), timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
        if expiry
        else None
    )
    return "Certificate verified", {
        "protocol": wrapped.version(),
        "cipher": wrapped.cipher()[0],
        "certificate_sha256": hashlib.sha256(wrapped.getpeercert(binary_form=True)).hexdigest(),
        "expires_at": expires_at,
        "server_name": target["host"],
        "verified": True,
    }


def _read_headers(connection):
    # Read one byte at a time: never receive response body bytes past CRLFCRLF.
    data = bytearray()
    deadline = time.monotonic() + SOCKET_TIMEOUT
    while len(data) < MAX_HEADER_BYTES:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        connection.settimeout(min(SOCKET_TIMEOUT, remaining))
        chunk = connection.recv(1)
        if not chunk:
            raise ValueError("Incomplete HTTP headers")
        data.extend(chunk)
        if data.endswith(b"\r\n\r\n"):
            return data.decode("iso-8859-1")
    raise ValueError("HTTP headers exceed 16 KiB")


def _http(target, connection):
    host = f"[{target['host']}]" if ":" in target["host"] else target["host"]
    if target["port"] != (443 if target["scheme"] == "https" else 80):
        host += f":{target['port']}"
    request = f"HEAD {target['path']} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: Network-Xray/1\r\nConnection: close\r\n\r\n"
    connection.settimeout(SOCKET_TIMEOUT)
    connection.sendall(request.encode("ascii"))
    lines = _read_headers(connection).split("\r\n")
    match = re.fullmatch(r"HTTP/1\.[01] ([2-5][0-9]{2})(?: ([\x20-\x7e\x80-\xff]*))?", lines[0])
    if not match:
        raise ValueError("Malformed or unsupported HTTP status line")
    headers = {}
    for line in lines[1:-2]:
        key, separator, value = line.partition(":")
        if (
            not separator
            or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key)
            or any(ord(char) < 32 and char != "\t" or ord(char) == 127 for char in value)
        ):
            raise ValueError("Malformed HTTP header")
        if key.lower() in ("server", "content-type"):
            headers[key.lower()] = _safe_text(value.strip())
    status = int(match[1])
    return f"HTTP {status}", {
        "status_code": status,
        "reason": _safe_text(match[2] or ""),
        "server": headers.get("server", ""),
        "content_type": headers.get("content-type", ""),
        "redirect": 300 <= status <= 399,
    }


def _collect(target, label):
    bundle = empty_bundle(target, label)
    started = time.monotonic()
    connections = []
    dns_ok = _stage(bundle, 0, lambda: _resolve(target))
    proceed = dns_ok or target["connect_ip"] is not None
    try:
        if proceed:
            address = target["connect_ip"] or bundle["stages"][0]["details"]["addresses"][0]
            proceed = _stage(bundle, 1, lambda: _connect(target, address, connections))
        if target["scheme"] == "http":
            bundle["stages"][2].update(status="skipped", summary="Not applicable: HTTP")
        elif proceed:
            proceed = _stage(bundle, 2, lambda: _tls(target, connections))
        if proceed:
            _stage(bundle, 3, lambda: _http(target, connections[-1]))
            stage = bundle["stages"][3]
            if stage["status"] == "ok" and stage["details"]["status_code"] >= 400:
                stage.update(
                    status="error",
                    error={"code": "http_status", "message": "HTTP application error status"},
                )
        for stage in bundle["stages"]:
            if stage["status"] == "unknown":
                stage.update(status="skipped", summary="Not attempted after earlier failure")
    finally:
        for connection in reversed(connections):
            connection.close()
    bundle["capture"] = {"status": "complete", "duration_ms": _elapsed(started), "error": None}
    return seal_bundle(bundle)


def _worker_environment():
    # Never inherit tokens, proxy variables, Python hooks or custom trust-store vars.
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8"}
    if os.name == "nt":
        for key in ("SYSTEMROOT", "WINDIR"):
            if key in os.environ:
                environment[key] = os.environ[key]
    return environment


def _run_worker(target, label):
    command = [
        sys.executable,
        "-I",
        "-S",
        os.path.abspath(__file__),
        target["url"],
        f"--label={label}",
        "--worker",
    ]
    if target["connect_ip"] is not None:
        command.extend(["--connect-ip", target["connect_ip"]])
    deadline = time.monotonic() + PROCESS_TIMEOUT
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=_worker_environment(),
        shell=False,
        close_fds=True,
    )
    output = []

    def read_bounded():
        output.append(process.stdout.read(MAX_BUNDLE_BYTES + 1))
        if len(output[0]) > MAX_BUNDLE_BYTES:
            try:
                process.kill()
            except ProcessLookupError:
                pass

    reader = threading.Thread(target=read_bounded, daemon=True)
    reader.start()
    try:
        process.wait(timeout=max(0, deadline - time.monotonic()))
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        reader.join(timeout=1)
        process.stdout.close()
    if process.returncode != 0 or not output or len(output[0]) > MAX_BUNDLE_BYTES:
        raise ValueError("Collector child returned no valid bounded result")
    return json.loads(output[0])


def probe(url, label, *, connect_ip=None):
    target = parse_target(url, connect_ip)
    validate_label(label)
    started = time.monotonic()
    try:
        return _run_worker(target, label)
    except subprocess.TimeoutExpired:
        status, code, message = (
            "timeout",
            "deadline_exceeded",
            "Collector deadline exceeded; no stage observations received",
        )
    except (OSError, ValueError):
        status, code, message = (
            "failed",
            "collector_failed",
            "Collector process failed; no stage observations received",
        )
    bundle = empty_bundle(target, label)
    bundle["capture"] = {
        "status": status,
        "duration_ms": _elapsed(started),
        "error": {"code": code, "message": message},
    }
    return seal_bundle(bundle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--label", required=True)
    parser.add_argument("--connect-ip")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        target = parse_target(args.url, args.connect_ip)
        validate_label(args.label)
        result = (
            _collect(target, args.label)
            if args.worker
            else probe(args.url, args.label, connect_ip=args.connect_ip)
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=True, allow_nan=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
