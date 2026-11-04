"""Adapter contract tests. Fake responses here are synthetic, not live evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xray_adapter_tests", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
PLUGIN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PLUGIN
SPEC.loader.exec_module(PLUGIN)


class Context:
    def __init__(self):
        self.tools = []
        self.commands = []
        self.skills = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_cli_command(self, **kwargs):
        self.commands.append(kwargs)

    def register_skill(self, **kwargs):
        self.skills.append(kwargs)


def test_registration_is_inert_and_declares_four_tools():
    context = Context()
    PLUGIN.register(context)
    assert {tool["name"] for tool in context.tools} == {
        "network_xray_probe", "network_xray_import", "network_xray_compare", "network_xray_history"
    }
    assert all(tool["check_fn"]() for tool in context.tools)
    assert all(tool["schema"]["parameters"]["additionalProperties"] is False for tool in context.tools)
    assert len(context.commands) == len(context.skills) == 1


def test_cli_parser_preserves_explicit_target_and_label():
    from xray_adapter_tests.cli import configure
    parser = argparse.ArgumentParser()
    configure(parser)
    args = parser.parse_args(["probe", "https://example.com/", "--label", "Peer"])
    assert args.url == "https://example.com/"
    assert args.label == "Peer"
    assert args.connect_ip is None


@pytest.mark.parametrize("args", [{"url": "https://example.com/"}, {"url": 5, "label": "Peer"}, {"url": "https://example.com/", "label": "Peer", "shell": "no"}])
def test_tool_rejects_bad_args_without_invoking_service(args):
    from xray_adapter_tests.service import handle_tool
    class MustNotRun:
        def collect(self, **kwargs):
            raise AssertionError("invalid inputs dispatched")
    result = json.loads(handle_tool("network_xray_probe", args, MustNotRun()))
    assert result["ok"] is False


def test_history_tool_returns_real_service_envelope():
    from xray_adapter_tests.service import handle_tool
    class FakeHistory:
        def list_probes(self):
            return {"probes": []}
    assert json.loads(handle_tool("network_xray_history", {}, FakeHistory())) == {
        "ok": True, "result": {"probes": []}
    }


def test_report_escapes_untrusted_strings_and_has_no_external_dependencies():
    from xray_adapter_tests.export import render_report
    malicious = '<img src=x onerror="alert(1)">'
    probe = {
        "id": "synthetic", "vantage": {"label": malicious}, "captured_at": "2026-01-01T00:00:00Z",
        "target": {"url": "https://example.com/", "connect_ip": None},
        "stages": [{"name": name, "status": "unknown", "duration_ms": 0, "summary": malicious, "details": {}, "error": None} for name in ["dns", "tcp", "tls", "http"]],
        "integrity": {"algorithm": "sha256", "digest": "0" * 64},
    }
    report = {"headline": malicious, "verdict": "inconclusive", "created_at": "2026-01-01T00:00:00Z", "left": probe, "right": probe,
              "findings": [{"kind": "limitation", "stage": "capture", "text": malicious}], "limitations": [malicious], "next_tests": []}
    page = render_report(report, {"synthetic": "imported"})
    assert '<img src=x' not in page
    assert '&lt;img' in page
    assert '<script' not in page
    assert '<link' not in page
    assert 'Imported' in page
    assert 'Content-Security-Policy' in page
