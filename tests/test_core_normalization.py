"""Regression for IDNA mappings that reveal ambiguous or forbidden numeric hosts."""

import subprocess

import pytest

from network_xray import collector
from network_xray.bundles import validate_bundle


@pytest.mark.parametrize(
    "url",
    [
        "http://１２７．１/",
        "http://０ｘ７ｆ０００００１/",
        "http://０．０．０．０/",
        "http://１６９．２５４．１６９．２５４/",
        "http://２２４．０．０．１/",
        "http://２１３０７０６４３３/",
        "http://０１７７．０．０．１/",
    ],
)
def test_idna_numeric_policy_rejects_before_worker_launch(monkeypatch, url):
    def must_not_launch(*args, **kwargs):
        raise AssertionError("Invalid normalised target reached worker launch")

    monkeypatch.setattr(collector.subprocess, "Popen", must_not_launch)
    with pytest.raises(ValueError):
        collector.probe(url, "Rejected Unicode host")


@pytest.mark.parametrize(
    "url",
    [
        "https://bücher.example/",
        "https://ＥＸＡＭＰＬＥ．ＣＯＭ/",
        "http://１２７．０．０．１/",
        "http://127.0.0.1/",
        "http://[::1]:8000/path",
        "HTTPS://EXAMPLE.COM:443/",
    ],
)
def test_accepted_normalised_targets_are_idempotent_and_timeout_bundles_validate(monkeypatch, url):
    target = collector.parse_target(url)
    assert collector.parse_target(target["url"]) == target

    def timeout_without_observations(*args, **kwargs):
        raise subprocess.TimeoutExpired("controlled test worker", 12)

    monkeypatch.setattr(collector, "_run_worker", timeout_without_observations)
    result = collector.probe(url, "Synthetic deadline case")
    assert result["capture"]["status"] == "timeout"
    assert validate_bundle(result) == result
    assert result["target"] == target
