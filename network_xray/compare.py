"""Deterministic evidence comparison, never an asserted absolute root cause."""

from datetime import datetime
import ipaddress
import uuid

from .bundles import overall, validate_bundle
from .collector import permitted_ip, utc_now

BASE_LIMITATIONS = [
    "Point-in-time direct-connection observations; proxies and browser trust stores may behave differently.",
    "Imported results are not authenticated; hashes detect content changes, not origin.",
    "Each probe attempts a single address; untested addresses and paths may behave differently.",
]


def _finding(kind, stage, text):
    return {"kind": kind, "stage": stage, "text": text}


def _differences(left, right):
    statuses, details = [], []
    for first, second in zip(left["stages"], right["stages"]):
        name = first["name"]
        if first["status"] != second["status"]:
            statuses.append(
                _finding(
                    "observation",
                    name,
                    f"{name.upper()} statuses differ: left {first['status']}, right {second['status']}.",
                )
            )
        one, two = first["details"], second["details"]
        key = {
            "dns": "addresses",
            "tcp": "address",
            "tls": "certificate_sha256",
            "http": "status_code",
        }[name]
        if key not in one or key not in two:
            continue
        first_value, second_value = one[key], two[key]
        if name == "dns":
            first_value, second_value = set(first_value), set(second_value)
        if first_value != second_value:
            text = {
                "dns": "Recorded DNS address sets differ; CDN or resolver variation is possible.",
                "tcp": "The selected connection addresses differ; each probe tests only one address.",
                "tls": "Recorded certificate fingerprints differ; certificate rotation or different endpoints are possible, not proof of attack.",
                "http": f"HTTP status codes differ: left {first_value}, right {second_value}.",
            }[name]
            details.append(_finding("observation", name, text))
    return statuses, details


def _limitations(left, right):
    limitations = list(BASE_LIMITATIONS)
    first = datetime.fromisoformat(left["captured_at"].replace("Z", "+00:00"))
    second = datetime.fromisoformat(right["captured_at"].replace("Z", "+00:00"))
    separation = abs((first - second).total_seconds())
    limitations.append(
        f"Capture times: left {left['captured_at']}, right {right['captured_at']}; separation {separation:.3f} seconds. Recorded results can be stale and do not establish current health."
    )
    for side, probe in (("Left", left), ("Right", right)):
        if probe["target"]["connect_ip"] is not None:
            limitations.append(
                f"{side} uses an explicit connect_ip override ({probe['target']['connect_ip']}); original Host/SNI and certificate verification are preserved. This is not normal-DNS success."
            )
        if probe["stages"][3]["details"].get("redirect"):
            limitations.append(
                f"{side} received a redirect. It was not followed; the destination remains untested."
            )
        if probe["stages"][0]["details"].get("truncated"):
            limitations.append(
                f"{side} DNS address list was truncated; unrecorded addresses cannot be compared."
            )
    return limitations


def _selected_address(probe):
    if probe["target"]["connect_ip"]:
        return probe["target"]["connect_ip"]
    details = probe["stages"][1]["details"]
    addresses = probe["stages"][0]["details"].get("addresses", [])
    return details.get("address") or (addresses[0] if addresses else None)


def _hypotheses(left, right):
    findings = []
    addresses = [_selected_address(probe) for probe in (left, right)]
    if all(address and ipaddress.ip_address(address).is_loopback for address in addresses):
        findings.append(
            _finding(
                "hypothesis",
                "tcp",
                "The recorded destinations are loopback addresses: each machine reaches itself. A service listening on one machine need not be listening on the other; check the intended service host before changing firewall or DNS settings.",
            )
        )
    for side, probe in (("A", left), ("B", right)):
        for stage in probe["stages"]:
            if stage["status"] != "error":
                continue
            code = stage["error"]["code"]
            advice = {
                "dns_failed": "Name resolution failed. Compare resolver configuration and whether this hostname exists on both networks; the service itself has not been tested from this vantage.",
                "connection_refused": "A connection was refused at the selected address and port. Check whether the intended service is listening there; an active rejection is different from a timeout.",
                "socket_timeout": "The operation timed out. Routing, filtering, an unresponsive endpoint or network delay could explain it; this capture does not distinguish them.",
                "certificate_invalid": "TCP connected but certificate verification failed. Check the certificate hostname, trust chain, validity and local clock; do not bypass verification.",
                "tls_failed": "TCP connected but TLS negotiation failed. Compare the endpoint and protocol configuration before investigating application paths.",
            }.get(code)
            status = stage["details"].get("status_code")
            if status in (401, 403):
                advice = "The server rejected an anonymous HEAD request. Authentication, access policy or method handling may differ from a signed-in browser; this collector sends no credentials."
            elif status == 405:
                advice = "The server rejects HEAD. A GET request may behave differently; this tool has not tested GET. Check the endpoint in an approved browser instead of treating this as a TCP failure."
            elif status == 404:
                advice = "The HTTP endpoint was reached but the path returned 404. Check the requested path and virtual-host routing; DNS and TCP completed for this capture."
            elif status is not None and status >= 500:
                advice = "The server returned an application or upstream error after the preceding network stages completed. Inspect service/upstream health rather than assuming DNS failed."
            if advice:
                findings.append(
                    _finding("hypothesis", stage["name"], f"Perspective {side}: {advice}")
                )
    return findings


def _next_tests(left, right):
    suggestions = []
    seen = set()
    for side, current, peer in (("left", left, right), ("right", right, left)):
        address = peer["stages"][1]["details"].get("address")
        if (
            peer["stages"][1]["status"] != "ok"
            or address is None
            or address == _selected_address(current)
            or address in seen
        ):
            continue
        permitted_ip(address)
        seen.add(address)
        suggestions.append(
            {
                "title": f"Manually test peer IP from the {side} vantage",
                "reason": "A confirmed follow-up can distinguish address selection from vantage effects. Preserve the original Host/SNI and full certificate verification; this is an explicit override, not normal DNS.",
                "url": left["target"]["url"],
                "connect_ip": address,
                "requires_confirmation": True,
            }
        )
    return suggestions


def compare(left, right):
    left, right = validate_bundle(left), validate_bundle(right)
    if left["id"] == right["id"]:
        raise ValueError("Choose two different probe IDs")
    if left["target"]["url"] != right["target"]["url"]:
        raise ValueError("Comparison requires the same canonical target URL")
    statuses, differences = _differences(left, right)
    observations = statuses + differences
    first_divergence = observations[0]["stage"] if observations else None
    outcomes = (overall(left), overall(right))
    if "inconclusive" in outcomes:
        verdict = "inconclusive"
    elif outcomes == ("healthy", "healthy"):
        verdict = "both_healthy"
    elif outcomes == ("failed", "failed"):
        verdict = "both_failed"
    else:
        verdict = "diverged"
    headline = {
        "both_healthy": "Both recorded HEAD probes succeeded; observed differences are not failures.",
        "both_failed": "Both recorded probes failed; this does not establish a common cause.",
        "diverged": "The recorded outcomes differ between these vantage observations.",
        "inconclusive": "Incomplete capture prevents a conclusive outcome comparison.",
    }[verdict]
    if verdict == "diverged":
        for failed_side, failed, other_side, other in (
            ("A", left, "B", right),
            ("B", right, "A", left),
        ):
            failure = failed["stages"][1]["error"]
            if (
                failure
                and failure["code"] == "connection_refused"
                and other["stages"][1]["status"] == "ok"
            ):
                headline = (
                    f"TCP connects from {other_side}; {failed_side} records a refused connection."
                )
    limitations = _limitations(left, right)
    failure_findings = []
    for side, probe in (("Left", left), ("Right", right)):
        for stage in probe["stages"]:
            if stage["status"] == "error":
                error = stage["error"]
                failure_findings.append(
                    _finding(
                        "observation",
                        stage["name"],
                        f"{side} {stage['name'].upper()} recorded {error['code']}: {error['message']}",
                    )
                )
    findings = (
        observations
        + failure_findings
        + [_finding("limitation", "capture", text) for text in limitations]
    )
    if verdict in ("diverged", "both_failed"):
        findings.extend(_hypotheses(left, right))
    if (
        statuses
        and verdict != "both_healthy"
        and not any(item["kind"] == "hypothesis" for item in findings)
    ):
        findings.append(
            _finding(
                "hypothesis",
                statuses[0]["stage"],
                "The earliest status difference narrows a follow-up test, but does not identify an absolute root cause.",
            )
        )
    return {
        "schema_version": 1,
        "kind": "network_xray.comparison",
        "id": str(uuid.uuid4()),
        "created_at": utc_now(),
        "left": left,
        "right": right,
        "verdict": verdict,
        "first_divergence": first_divergence,
        "headline": headline,
        "findings": findings,
        "next_tests": _next_tests(left, right)
        if observations and verdict != "inconclusive"
        else [],
        "limitations": limitations,
    }
