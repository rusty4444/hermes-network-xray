# Network X-ray

**Same URL. Two perspectives. Find the first difference.**

A local-first [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin for the question every IT team eventually asks:

> “Why does this work on my machine, but not on that one?”

Network X-ray collects bounded **DNS → TCP → verified TLS → HTTP HEAD** observations, compares results from two machines and shows the evidence behind each difference. It offers possible next tests, not an invented root cause.

No service account, API key, hosted backend or model call is required by the plugin. Hermes can operate the same engine through four native tools; a Desktop workbench makes the result visual.

## What you get

- **Two diagnostic ladders:** inspect each stage's status, actual duration and recorded details.
- **A portable collector:** copy one Python source file to another machine; no Hermes installation or third-party Python packages needed there.
- **Evidence, not guesses:** distinguish observations, hypotheses and limitations. Two different healthy CDN addresses are not a network failure.
- **Explicit experiments:** optionally connect to a chosen numeric IP while preserving the original URL's Host header, TLS server name and certificate verification.
- **Local history:** saved probes stay in the active Hermes profile, with imported observations labelled separately.
- **Shareable reports:** export a self-contained, script-free HTML evidence report. Review private network details before sharing.

## Install in Hermes

Requires **Hermes Agent 0.22.5 or later** and Python 3.10 or later on **macOS or Linux**. The collector uses the Python standard library; the native HTTP adapter uses FastAPI supplied by Hermes. The evidence store uses POSIX no-follow directory operations, so this release does not support Windows.

```sh
hermes plugins install rusty4444/hermes-network-xray --no-enable
hermes plugins enable network-xray
```

Restart the relevant Hermes session/backend if prompted. In Hermes Desktop, enable the plugin's Desktop contribution and open **Network X-ray** in the sidebar. The backend plugin must also be enabled; enabling the renderer alone is insufficient.

Until the catalog entry is accepted, install from the repository above rather than assuming the catalog short name is available. Catalog acceptance and hackathon submission are separate processes.

## First comparison

1. Choose **one exact HTTP(S) URL** you own or are authorised to diagnose. Use a neutral label such as `Workstation`.
2. Run a probe from the workbench or ask Hermes to use `network_xray_probe`.
3. Download the portable collector from the workbench. Run it on the second machine:

   ```sh
   python3 network-xray-collector.py https://example.com/ --label "Second machine" > peer.json
   ```

4. Import `peer.json`, select the two saved observations, and compare.
5. Click a stage to inspect its evidence. A suggested experiment runs only after your explicit action, on the **current Hermes backend**, not on the machine named in an imported file.

The machine running Hermes is not necessarily the machine displaying Desktop or the phone you are chatting from. Labels do not move execution.

### CLI

```sh
hermes network-xray probe https://example.com/ --label Workstation
hermes network-xray import peer.json
hermes network-xray history
hermes network-xray compare LEFT_PROBE_ID RIGHT_PROBE_ID
hermes network-xray compare LEFT_PROBE_ID RIGHT_PROBE_ID --html > report.html
hermes network-xray collector > network-xray-collector.py
```

An explicit follow-up keeps the URL identity and certificate verification:

```sh
hermes network-xray probe https://example.com/ --label "Workstation follow-up" --connect-ip APPROVED_NUMERIC_IP
```

The placeholder must be replaced with an authorised numeric address. Do not disable certificate validation to make a failing test green.

### Agent tools

| Tool | Action |
|---|---|
| `network_xray_probe` | Collect and save one bounded local probe |
| `network_xray_import` | Validate and save a portable JSON observation |
| `network_xray_compare` | Compare two saved IDs for the same URL |
| `network_xray_history` | List the newest saved observations |

The bundled `network-xray:workflow` skill explains the evidence limits and safe workflow. No hooks, model routing changes, middleware or overrides are installed.

## What a probe does — and does not do

- Opens a **direct connection**. Proxy environment variables, VPN configuration and browser settings are not changed. A browser using a proxy or a different trust store can behave differently.
- Resolves the hostname, records up to eight distinct addresses and connects to **one** chosen address. This is not exhaustive IPv4/IPv6 or CDN testing.
- Uses the system Python TLS trust configuration with hostname verification enabled. It never continues to HTTP after certificate verification fails.
- Sends **HEAD**, not GET. Some servers handle HEAD differently. HTTP 4xx/5xx responses are application-layer failures, not proof that TCP or TLS failed.
- Does not follow redirects, capture response bodies, use cookies or supply authentication. URL credentials, query strings and fragments are rejected; queries frequently contain secrets.
- Allows explicitly requested private and loopback endpoints. Link-local, multicast and unspecified connection addresses are refused. This is a diagnostic tool, not a scanner or a security boundary around other Hermes tools.
- Uses bounded socket operations and an owned collector subprocess with a total deadline. A timeout with no returned stage evidence is **inconclusive**, not proof that a particular network layer failed.

A direct-IP experiment is marked as an override. It is not silently presented as successful normal DNS resolution.

## Privacy and disclosure

**Network:** only the target's DNS lookup and the explicit target/override address are contacted by the collector. Installation/development dependency downloads are separate. No telemetry, analytics, provider calls or automatic background collection.

**Local processes:** a probe starts one isolated Python collector child with a restricted environment and a bounded lifetime. No shell, arbitrary commands, persistent daemon or automatic SSH execution is part of the shipped plugin. You run the portable source on the second host yourself.

**Storage:** evidence lives under the active profile's `plugin-data/network-xray/`, not the plugin installation directory. It can include requested URLs, IP addresses, selected response headers, certificate fingerprints and timestamps. It does not automatically collect your username, hostname or interface inventory. History is bounded; it does not silently delete older records to make room.

**Files:** the CLI reads only the explicitly supplied import file, and the plugin serves its own collector source. Python may read its standard certificate trust files for TLS verification. There are no credential-store reads, `.env` reads or stored secrets.

**Imports and sharing:** a SHA-256 digest detects content changes; it does **not** authenticate a machine or prove an observation is truthful. Imported results are untrusted recorded evidence. Reports contain the actual diagnostic details, not guaranteed anonymised data. Review them before posting or sending.

**Approvals:** normal Hermes tool approvals remain intact. The plugin never auto-approves, changes model/provider defaults or disables safety controls. Run diagnostics only for endpoints you are authorised to inspect.

## Desktop, browser and mobile

The native Desktop page uses only the public Hermes SDK. A loopback-only development workbench uses the **same UI source and backend**, not a mockup. The native Android app does not automatically render Desktop SDK panes; ordinary tool results and the exported HTML report remain useful there.

## Development

```sh
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements-dev.txt
npm ci --ignore-scripts
npm run build
.venv/bin/python scripts/test.py -q
.venv/bin/ruff check .
```

The scripted test runner gives tests disposable HOME/HERMES_HOME directories and does not forward provider credentials. Keep the storage directory and its ancestors free of symlinks; the store refuses symlink traversal.

Run the real local workbench with an explicit private data directory:

```sh
.venv/bin/python scripts/serve.py --data ./artifacts/local-data --port 8765
```

Open `http://127.0.0.1:8765`. This server binds only to loopback, rejects unrecognised Host headers and cross-origin JSON mutations, and contains no authentication credentials. It is a development tool, not a public internet deployment.

Native catalog check:

```sh
hermes plugins doctor .
hermes plugins validate . --install-deps
```

`desktop/plugin.js` is a readable bundled ESM file; React and the SDK remain host-provided. The browser workbench bundles React locally, with licence notices retained. No compiled executables or native binaries are committed.

## Honest demo setup

The reproducible two-machine demonstration uses a **controlled loopback service**: it runs on one machine but not the other. The identical `127.0.0.1` URL reaches each machine's own loopback interface, so the real TCP outcomes differ. This is an intentional fixture, not an outage on a production service.

```sh
python3 scripts/demo_service.py --port 18764
# On that machine, collect http://127.0.0.1:18764/health.
# Run the same collector URL on the second machine, where the fixture is not running.
```

The comparison must show real captured results and timestamps. Synthetic test data is never presented as live network evidence. See `docs/VERIFICATION.md` for the release's actual verification scope once published.

## Licence and authorship

MIT. Created by Sam Russell for the Hermes Agent Plugin Hackathon. Development, testing and documentation were AI-assisted using Hermes Agent. Automated review and tests are not a claim of independent human security certification.
