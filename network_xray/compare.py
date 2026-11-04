"""Deterministic evidence comparison, never an asserted absolute root cause."""

from datetime import datetime
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
        if probe["stages"][0]["details"].get("truncated"):
            limitations.append(
                f"{side} DNS address list was truncated; unrecorded addresses cannot be compared."
            )
    return limitations


def _next_tests(left, right):
    suggestions = []
    seen = set()
    for side, peer in (("left", right), ("right", left)):
        address = peer["stages"][1]["details"].get("address")
        if address is None or address in seen:
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
    if statuses and verdict != "both_healthy":
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
        "next_tests": _next_tests(left, right) if observations else [],
        "limitations": limitations,
    }
