# Verification scope

## Local candidate validation

The release workflow runs tests in a disposable HOME and HERMES_HOME with provider credentials removed from the child environment.

- `python scripts/test.py -q`: **155 distinct tests passed**, zero failures/errors/skips, on Python 3.12.13/macOS. This includes collector, bundle, storage, comparison, adapter, HTTP-boundary, synthetic browser-contract and real loopback browser-integration tests.
- `node --test tests/ui/helpers.test.mjs`: **6 tests passed**.
- `ruff check .`: passed.
- `npm run build` and `npm run check`: passed. The native bundle imports host React and the public Hermes SDK; the browser workbench bundles its dependencies locally.
- Installed Hermes 0.22.5 Doctor: real discovery/import/registration passed for four tools, a CLI command and bundled skill.
- Installed Hermes 0.22.5 catalog validator: passed, no warnings; declared capabilities matched, security scan safe, no core overrides, Desktop SDK surface accepted. These checks used the actual installed command handlers with isolated homes, rather than launcher repair or live-profile settings.

One non-failing development dependency warning reports Starlette's planned transition from httpx to httpx2. It is not a skipped test or a collector failure.

## Real two-machine evidence

The controlled demonstration runs a loopback HTTP service on the macOS workstation and copies the byte-identical standalone collector to a Linux DGX host running Python 3.12.3. The SHA-256 of the remote source is read back before execution.

For the same `http://127.0.0.1:18764/health` URL:

- The workstation recorded DNS success, TCP success, TLS not applicable and HTTP 200.
- The DGX recorded DNS success and a refused TCP connection; it did not attempt HTTP.
- The workbench imported the actual DGX JSON, read back identical evidence and showed TCP as the first observed status divergence.
- A real browser drove the workbench, inspected stage evidence and downloaded a standalone HTML report. No browser JavaScript errors occurred.

This is an intentional test fixture, not a production outage. Loopback addresses point to each machine itself. The plugin does not start or stop the fixture, execute remote commands, or claim that a label authenticates a machine.

## Limits

Synthetic unit/browser fixtures test contracts and adverse cases; they do not establish live remote behaviour. The separate two-machine run establishes the recorded demo observations, not universal network compatibility.

The product targets macOS and Linux. The evidence store uses POSIX no-follow directory operations and rejects symlink ancestors. Python 3.10 syntax compatibility was checked; the CI matrix covers additional runtime versions after publication.

Native Doctor/catalog checks and browser workbench operation do not, on their own, prove a successful live Electron page mount. Native Desktop mounting, independent reviews, remote CI and public publication are tracked as separate release gates; their final results belong in the release notes.
