"""Explicitly synthetic, schema-valid examples for diagnostic explanation rules."""

from network_xray.collector import empty_bundle, parse_target
from network_xray.bundles import seal_bundle
from network_xray.compare import compare


def record(address="192.0.2.10", status=200, refused=False):
    probe = empty_bundle(parse_target("http://service.example.test/"), "Synthetic guidance case")
    probe["capture"] = {"status": "complete", "duration_ms": 3, "error": None}
    probe["stages"][0].update(
        status="ok",
        duration_ms=1,
        summary="Synthetic DNS",
        details={"addresses": [address], "truncated": False},
    )
    if refused:
        probe["stages"][1].update(
            status="error",
            duration_ms=1,
            summary="Synthetic refusal",
            error={"code": "connection_refused", "message": "Connection refused"},
        )
        probe["stages"][3].update(status="skipped", summary="Not attempted after earlier failure")
    else:
        probe["stages"][1].update(
            status="ok",
            duration_ms=1,
            summary="Synthetic connection",
            details={"address": address, "port": 80, "family": "ipv4", "selection": "dns"},
        )
        probe["stages"][3].update(
            status="ok" if status < 400 else "error",
            duration_ms=1,
            summary=f"HTTP {status}",
            details={
                "status_code": status,
                "reason": "",
                "server": "",
                "content_type": "",
                "redirect": 300 <= status <= 399,
            },
            error=None
            if status < 400
            else {"code": "http_status", "message": "HTTP application error status"},
        )
    probe["stages"][2].update(status="skipped", summary="Not applicable: HTTP")
    return seal_bundle(probe)


def guidance(report):
    return " ".join(
        item["text"] for item in report["findings"] if item["kind"] == "hypothesis"
    ).lower()


def test_loopback_failure_explains_machine_local_destination():
    result = compare(record("127.0.0.1"), record("127.0.0.1", refused=True))
    assert "loopback" in guidance(result)
    assert "each machine" in guidance(result)
    assert "refused" in result["headline"].lower()
    assert result["next_tests"] == []


def test_same_selected_peer_ip_does_not_offer_redundant_override():
    assert compare(record(), record(refused=True))["next_tests"] == []


def test_distinct_healthy_peer_ip_offers_discriminating_manual_test():
    result = compare(record("192.0.2.10"), record("192.0.2.20", refused=True))
    assert len(result["next_tests"]) == 1
    assert result["next_tests"][0]["connect_ip"] == "192.0.2.10"
    assert result["next_tests"][0]["requires_confirmation"] is True


def test_auth_status_explains_anonymous_head_limit():
    assert "authentication" in guidance(compare(record(), record(status=401)))


def test_method_rejection_explains_head_without_claiming_get_failed():
    text = guidance(compare(record(), record(status=405)))
    assert "head" in text and "get" in text


def test_server_error_points_beyond_completed_network_layers():
    text = guidance(compare(record(), record(status=503)))
    assert "application" in text or "upstream" in text


def test_redirect_marks_destination_as_untested():
    result = compare(record(), record(status=302))
    assert "not followed" in " ".join(result["limitations"]).lower()
