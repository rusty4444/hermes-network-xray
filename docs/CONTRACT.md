# Network X-ray v1 contract

Status: implementation contract, not observed evidence. All examples/fixtures are synthetic unless an evidence manifest says otherwise.

## Product boundary

Read-only, user-requested HTTP(S) diagnostics: compare one exact URL from two chosen vantage points. DNS, TCP, verified TLS, HTTP HEAD. Observe differences, distinguish hypotheses, export evidence. No scans, credentials, proxies, body downloads, automatic redirects, arbitrary commands, TLS bypass, firewall/DNS edits, telemetry, continuous daemon or automatic remote execution. Direct connections ignore proxy environment variables and say so prominently.

Python core has no Hermes or web-framework imports. Python 3.10+ core; standalone collector Python 3.10+; stdlib only. Adapters depend inward. Native Hermes 0.22.5 is the compatibility target, subject to real validation. Data survives plugin upgrades under profile-local plugin_data_dir('network-xray').

## Request

`probe(url: str, label: str, *, connect_ip: str | None = None) -> dict`

- URL: <=2048 chars; explicit http or https; hostname/IP; optional port 1..65535; optional path. Reject credentials, query strings, fragments, control characters, surrounding whitespace, backslashes, percent escapes in hostname, IPv6 zones. Never silently fix malformed input. ASCII/IDNA hostname validation, reject empty host. Query strings excluded because diagnostic URLs often carry secrets. Paths percent-encoded by the user must have well-formed escapes; no CR/LF on the wire.
- Label: 1..48 printable characters; no host discovery. User controls a neutral vantage name; do not capture local username, hostname or interface inventory.
- Explicit private/loopback targets are allowed (this is a LAN diagnostic). Reject link-local, multicast, unspecified addresses including cloud metadata endpoints. Validate actual resolved/override IP before every connect. At most one connection target per probe; list at most 8 unique resolved addresses with truncation disclosed.
- `connect_ip`: optional numeric IPv4/IPv6 only. A deliberate follow-up experiment, not a hidden DNS replacement. Resolve original hostname too; record it even if it fails, then connect to the explicitly supplied IP with original Host/SNI and full certificate validation. Never treat this as a normal-DNS success.
- Network limits: <=3 s per socket operation, <=12 s whole collector process. DNS can block in OS: parent subprocess deadline must kill and reap the owned child. Worker runs isolated Python with a credential-free environment, no shell. Bounded request/result JSON, bounded HTTP header read (16 KiB max), no response body, no cookies/auth headers, no redirects.
- A timeout is inconclusive capture, not fabricated proof that DNS failed. When no stage result escaped, all stages are unknown and the parent reports collector deadline exceeded.

## Probe bundle (wire and disk)

Exactly these top-level keys:

```
{
  "schema_version": 1,
  "kind": "network_xray.probe",
  "id": "<UUID4 string>",
  "captured_at": "<UTC ISO8601 ending Z>",
  "vantage": {"label": "Workstation", "platform": "darwin", "python": "3.12.13"},
  "target": {"url": "https://example.com/", "scheme": "https", "host": "example.com", "port": 443, "path": "/", "connect_ip": null},
  "policy": {"method": "HEAD", "redirects": "not_followed", "tls_verification": true, "proxy": "direct", "body_capture": false},
  "capture": {"status": "complete", "duration_ms": 123.4, "error": null},
  "stages": [
    {"name": "dns", "status": "ok", "duration_ms": 1.2, "summary": "Resolved 1 address", "details": {"addresses": ["93.184.216.34"], "truncated": false}, "error": null},
    {"name": "tcp", "status": "ok", "duration_ms": 42.1, "summary": "Connected", "details": {"address": "93.184.216.34", "port": 443, "family": "ipv4", "selection": "dns"}, "error": null},
    {"name": "tls", "status": "ok", "duration_ms": 64.1, "summary": "Certificate verified", "details": {"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384", "certificate_sha256": "<64 lowercase hex>", "expires_at": "<UTC ISO8601 or null>", "server_name": "example.com", "verified": true}, "error": null},
    {"name": "http", "status": "ok", "duration_ms": 14.0, "summary": "HTTP 200", "details": {"status_code": 200, "reason": "OK", "server": "", "content_type": "text/html", "redirect": false}, "error": null}
  ],
  "integrity": {"algorithm": "sha256", "digest": "<64 lowercase hex>"}
}
```

Enums: stage names fixed ordered `dns,tcp,tls,http`; status `ok,error,skipped,unknown`; capture status `complete,timeout,failed`; error `null` or `{code:<1..64 machine-safe chars>, message:<bounded plain text>}`. Skipped/unknown details `{}`; failed stage details may contain safe facts from the same stage or `{}`. Strings bounded (summary 240, error message 400, any collected header/reason 240). Timing finite nonnegative <=60000; bool is not number. No arbitrary extra nested fields/imported secrets. HTTP 200..399 => ok (redirects reported, not followed); 400..599 => error with actual status; malformed/incomplete response => error, not reachability success. HTTP URL TLS stage skipped with summary `Not applicable: HTTP` and downstream HTTP may run. Downstream stages skipped after earlier failure, except explicit connect_ip may proceed after DNS failure. A failed certificate never proceeds to HTTP.

Canonical digest: sha256(json.dumps(bundle_without_integrity, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')). Digest verifies content integrity only, NOT origin/authenticity. Imported bundles remain untrusted recorded observations. Strict decoder rejects duplicate JSON keys, NaN/Infinity, wrong types/shape, inconsistent stage order/state, bad IDs/date/digest, impossible policy or target fields. Max encoded bundle size 128 KiB. Validate exact nested schemas, not just outer envelope. Treat displayed text as data, never HTML.

`validate_bundle(value: dict) -> dict` validates and returns an independent normalised copy without changing meaning; raises `ValueError` safely. `parse_bundle(text: str) -> dict` validates duplicate-key-safe JSON. `seal_bundle(value: dict) -> dict` computes integrity for locally created bundles. `overall(bundle) -> 'healthy'|'failed'|'inconclusive'`: healthy only complete + HTTP ok; failed only complete + an error stage; otherwise inconclusive. Never accept stored/imported overall assertions.

## Comparison

`compare(left: dict, right: dict) -> dict` validates both, requires identical target.url (normalised canonical URL defined by parser) but allows different connect_ip experiments. Reject same id as both sides. Does not claim live current health or identify an absolute root cause.

```
{
 "schema_version":1, "kind":"network_xray.comparison", "id":"<uuid4>", "created_at":"<UTC Z>",
 "left":<probe>, "right":<probe>,
 "verdict":"diverged|both_healthy|both_failed|inconclusive",
 "first_divergence":"dns|tcp|tls|http|null",
 "headline":"plain text",
 "findings":[{"kind":"observation|hypothesis|limitation", "stage":"dns|tcp|tls|http|capture", "text":"bounded plain text"}],
 "next_tests":[{"title":"plain text", "reason":"plain text", "url":"exact target url", "connect_ip":"numeric ip or null", "requires_confirmation":true}],
 "limitations":["Point-in-time direct-connection observations; proxies and browser trust stores may behave differently.", "Imported results are not authenticated; hashes detect content changes, not origin."]
}
```

Deterministic comparison rules (timestamps/IDs aside): Prefer earliest stage STATUS divergence for first_divergence, ignoring TLS HTTP-not-applicable when same URL. Otherwise DNS address-set difference, TCP selected-address difference, TLS certificate fingerprint difference, HTTP status difference are observable differences. An address/certificate difference alone is NOT proof of failure or attack. Both healthy => verdict both_healthy even if details differ; inconclusive if capture not complete or unknown; diverged if outcomes/statuses differ; both_failed if both failed, describe differing failures without claiming common cause. Always note connect_ip override, age/time separation, truncated address lists and single-address probe limits. Suggest peer-IP follow-up only with a validated permissible observed IP, same target URL and clear original Host/SNI preserved; manual confirmation, never autoexecute. Empty next_tests is valid.

## Storage/service boundary

`Store(root: Path)` owns root, creates private directory. Atomic JSON files with random IDs, no user-derived filenames. Concurrency safe enough for threads; no global active-profile path captured at import. Read lists bounded to newest 100 records; writes reject after a reasonable 1000-record storage cap rather than delete user data. Validate before persist, no symlink escape. Imported colliding id with different bytes refuses; identical content can reuse same record. Store origin separately as `local|imported` and do not trust origin supplied inside imported data.

Service API (parent/adapters own):
- `collect(url,label,connect_ip=None) -> {"probe":<bundle>,"origin":"local"}`
- `import_probe(bundle) -> {"probe":<bundle>,"origin":"imported"}`
- `list_probes() -> {"probes":[{"id", "label", "url", "captured_at", "overall", "origin"}]}`
- `get_probe(id) -> {"probe":<bundle>,"origin":...}`
- `compare_probes(left_id,right_id) -> <comparison>`

Native tools planned: `network_xray_probe(url,label,connect_ip?)`, `network_xray_import(bundle_json)`, `network_xray_compare(left_id,right_id)`, `network_xray_history()`; all JSON strings returned. Tool output should expose IDs plus results sufficient for agent interpretation. No background collector, no LLM hooks, no override/middleware.

REST planned own namespace only, final registration per SDK preflight:
- GET /health -> {"ok":true,"version":"0.1.1"}
- GET /probes -> list_probes()
- POST /probe JSON {url,label,connect_ip?} -> collect()
- POST /import JSON {bundle_json:<original JSON text>} -> import_probe(); reject object transport so JavaScript cannot change float encodings before the digest check
- GET /probes/{id} -> get_probe()
- POST /compare JSON {left_id,right_id} -> compare_probes()
- GET /collector -> {"filename":"network-xray-collector.py","source":<exact source text>} for SDK JSON transport
- GET /collector.py -> exact source collector (attachment, ordinary browser/CLI clients)
- GET /export/{left_id}/{right_id} -> {"filename":"network-xray-report.html","html":<self-contained escaped HTML evidence report>} for SDK JSON transport; no network resources

UI adapter: `createApp(React, api)` exports a React component. `api.request(path,options={})` returns decoded JSON; options `{method,body,timeoutMs}` (body object, never pre-stringified in SDK). `api.ownerKey()` returns current connection/profile identity; `api.subscribeOwner(callback)` returns unsubscribe. Native adapter must use documented SDK state where available; the browser harness owner is a fixed isolated demo instance. On owner change reset selections/results, invalidate in-flight generations and refresh history. UI file import checks JSON syntax and duplicate keys locally but submits the original text in `{bundle_json}` without reserialising its values; the server performs authoritative strict parsing and digest validation. Integral floats, exponent spellings and signed zero must preserve the original ID and digest. Imports must never be silently resealed. Download exported source/HTML with Blob URLs created only after explicit user click, then revoke them.

Cap HTTP request bodies before reading/parsing at 256 KiB. Pydantic fields strict/extra forbidden; errors safe. No arbitrary filename upload/read. Explicit user action required to run probes from UI; page load only reads history. If same shared backend serves browser contexts, enforce application-authenticated SDK route boundary and reject cross-origin unsafe methods through host or plugin guard. Standalone demo/dev server loopback-only with origin protections and no credentials.

## Desktop experience

A plugin-owned page: crisp dark/light-aware header, target URL + vantage label + Probe button; portable collector instructions/download; JSON import; saved-result selectors left/right; four-stage parallel ladders; failure/first-divergence banner; evidence drawer with actual IP/certificate/status/timing; origin/time badges; clearly marked suggested experiments with explicit Run action; export. Keyboard operable, labelled controls, reduced-motion support, colour plus text/icons. No fake active animations after the operation completes. No production synthetic 'demo data' button. Real recorded fixtures may be imported and labelled as recordings.

Native desktop and standalone local demonstration use the SAME rendering/components and backend engine, not a mockup. Design with module factory `createApp(React, api)` reusable by the SDK adapter and browser dev harness; any build bundle must remain readable source and pass scanner. No external CDN dependencies in distributable app/export.

## Acceptance

1. Real local HTTP fixture success, 404/500, redirect not followed, malformed/slow response, DNS failure, TCP refusal, TLS invalid certificate; no HTTP after TLS failure.
2. Actual whole-process deadline tested; process reaped. No inherited tokens/proxy vars to collector; no shell.
3. URL rejection table, IP policy, import tampering/duplicate keys/nested types/oversized JSON/path traversal; output/report XSS checks.
4. Comparison tests for all verdicts, differing healthy CDN IPs, stale/imported evidence, override distinction, same-target requirement.
5. Hermes real plugin doctor/validate, declared capability equality, isolated profile persistence, tool dispatch, real REST and browser end-to-end interactions (not only snapshots).
6. Real second machine runs the portable collector. Retain original bundles privately, export only explicitly reviewed non-sensitive observations.
7. Capture real UI in video <90 seconds; controlled fault labelled as such; no synthesised results or passing animations standing in for actual operations.
8. Independent SPEC then QUALITY review of frozen revision, local tests, source-only release, exact-commit catalog PR, X video readback and Typeform confirmation. Never claim maintainer acceptance when only submitted.
