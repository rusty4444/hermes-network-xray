"""Self-contained, script-free evidence reports; untrusted text is always escaped."""

from html import escape
import json

CSS = """
:root{color-scheme:light dark;font-family:system-ui,sans-serif;background:#0b111b;color:#e5edf7}
body{max-width:1100px;margin:0 auto;padding:40px 24px;line-height:1.6}
h1{font-size:32px;letter-spacing:-.03em;line-height:1.15}h2{font-size:19px}h3{font-size:16px}
small,.muted{color:#a4b3c6}.eyebrow{color:#6bdbe1;font-size:12px;letter-spacing:.14em;text-transform:uppercase}
.banner,article,details{border:1px solid #283548;border-radius:12px;padding:20px;background:#111b29;margin:16px 0}
.lanes{display:grid;grid-template-columns:1fr 1fr;gap:20px}article{min-width:0}
.stage{border-top:1px solid #283548;padding:14px 0}.stage strong{display:inline-block;min-width:48px}
.status{font-size:12px;text-transform:uppercase;letter-spacing:.06em}.ok{color:#7de1b8}.error{color:#ffaaa8}.unknown,.skipped{color:#b4c0d0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.5;color:#c4d3e5}code{overflow-wrap:anywhere}
summary{cursor:pointer;font-weight:600}li{margin:8px 0}.finding-kind{font-weight:600;text-transform:capitalize}
@media(max-width:700px){.lanes{grid-template-columns:1fr}body{padding:20px 14px}}
@media print{:root{color-scheme:light;background:white;color:#102030}body{padding:0}article,.banner,details{background:white;color:#102030}pre,.muted,small{color:#405060}}
"""


def _text(value):
    return escape(str(value), quote=True)


def _stage(stage):
    state = (
        stage["status"] if stage["status"] in {"ok", "error", "skipped", "unknown"} else "unknown"
    )
    details = {"details": stage["details"], "error": stage["error"]}
    return (
        f'<div class="stage"><strong>{_text(stage["name"].upper())}</strong> '
        f'<span class="status {state}">{_text(state)}</span> '
        f"<small>{_text(stage['duration_ms'])} ms</small>"
        f"<p>{_text(stage['summary'])}</p>"
        f"<pre>{_text(json.dumps(details, indent=2, ensure_ascii=False, allow_nan=False))}</pre></div>"
    )


def _lane(probe, origin):
    override = probe["target"].get("connect_ip")
    extra = (
        f"<p>Explicit connection override: <code>{_text(override)}</code></p>" if override else ""
    )
    origin_label = (
        "Imported — recorded, origin not authenticated" if origin == "imported" else "Local capture"
    )
    return (
        f"<article><h2>{_text(probe['vantage']['label'])}</h2>"
        f'<p class="muted">{origin_label}<br>{_text(probe["captured_at"])}</p>'
        f"<p><code>{_text(probe['target']['url'])}</code></p>{extra}"
        + "".join(_stage(stage) for stage in probe["stages"])
        + f"<p><small>Content SHA-256: <code>{_text(probe['integrity']['digest'])}</code></small></p></article>"
    )


def render_report(comparison, origins=None):
    origins = origins or {}
    lanes = "".join(
        _lane(comparison[side], origins.get(comparison[side]["id"], "imported"))
        for side in ("left", "right")
    )
    findings = "".join(
        f'<li><span class="finding-kind">{_text(item["kind"])}</span> · {_text(item["stage"])}: {_text(item["text"])}</li>'
        for item in comparison["findings"]
    )
    limitations = "".join(f"<li>{_text(item)}</li>" for item in comparison["limitations"])
    tests = "".join(
        f"<li><strong>{_text(item['title'])}</strong> — {_text(item['reason'])} "
        "<em>Not executed. Requires a separate explicit action.</em></li>"
        for item in comparison["next_tests"]
    )
    evidence = _text(
        json.dumps(
            {"comparison": comparison, "origins": origins},
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Network X-ray — evidence report</title><style>{CSS}</style></head>
<body><p class="eyebrow">Network X-ray / evidence report</p><h1>{_text(comparison["headline"])}</h1>
<p class="muted">Generated {_text(comparison["created_at"])} · {_text(comparison["verdict"].replace("_", " "))}</p>
<div class="banner">Point-in-time observations, not a live monitor or proof of root cause.
Direct connections only: proxies ignored, redirects not followed, TLS verification retained, no response bodies.
This report may contain private network details. Review it before sharing. Content hashes do not authenticate the source.</div>
<div class="lanes">{lanes}</div><section><h2>What the evidence says</h2><ul>{findings}</ul></section>
<section><h2>Possible next tests</h2><ul>{tests or "<li>No additional automatic recommendation.</li>"}</ul></section>
<section><h2>Limits of this comparison</h2><ul>{limitations}</ul></section>
<details><summary>Full recorded evidence</summary><pre>{evidence}</pre></details>
<footer><small>Network X-ray · Local, read-only diagnostics for Hermes Agent · No external assets or scripts.</small></footer>
</body></html>"""
