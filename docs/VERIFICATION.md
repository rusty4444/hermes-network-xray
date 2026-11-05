# Verification scope

## Local release-candidate validation

The test runner uses disposable HOME/HERMES_HOME directories and removes provider credentials from child environments.

- `python scripts/test.py -q`: **189 tests passed**, zero failures or skips, on Python 3.12.13/macOS.
- `node --test tests/ui/helpers.test.mjs`: **7 tests passed**.
- `ruff check .`, `npm run build`, `npm run check` and generated-bundle checks passed.
- Coverage includes supervised collectors, strict bundles, private storage, comparisons, adapters, HTTP boundaries, synthetic browser contracts and a real loopback browser workflow.
- Import regressions exercise integral-valued floats, exponent forms and signed zero through the shared UI, both transport adapters and the real router/store. The native-adapter browser harness substitutes the SDK transport boundary; it is not an Electron integration test. Original IDs and digests survive, and tampered imports remain rejected.
- Null comparison IDs and malformed/cross-origin headers return controlled client errors.

One non-failing development dependency warning reports Starlette's transition from httpx to httpx2. It does not prevent tests or collector operation.

## Hermes integration

Actual Hermes 0.22.5 Doctor/discovery registered four tools, the CLI command and bundled skill. Catalog checks verified declared capabilities, no core overrides and the public Desktop SDK surface. An independent clean source runtime completed the supported PM installation and dependency-preparing catalog validation; the live user profile was not modified.

The native Desktop demonstration ran in a disposable Electron 44.9.3 / Chromium 152.0.7977.167 app using Hermes source `bf0203a794a07aac3ff764972ab9087baa4e4f4e`. It exercised the real plugin host and `ctx.rest` path, local capture, peer import, comparison and report export with no renderer errors. Footage provenance is published plugin commit `dafa4b320ba8a8cce723a86dca3334dd8e667ac3`, recorded locally as `47b533e` before commit-author metadata was normalised; both have tree `6f620b49fb0949501624bc461d215f853eb42451`. That revision predates the subsequent raw-JSON import transport fix. The six current browser import regressions verify the updated boundary; the recorded footage is not a claim that it ran later code.

## Real two-machine evidence

The controlled demonstration runs a loopback HTTP service on the macOS workstation and copies the byte-identical standalone collector to a Linux DGX host running Python 3.12.3. The remote source hash was read back before execution.

For the same `http://127.0.0.1:18764/health` URL:

- The workstation recorded DNS success, TCP success, TLS not applicable and HTTP 200.
- The DGX recorded DNS success and a refused TCP connection; it did not attempt HTTP.
- The native workbench imported that DGX JSON and identified TCP as the first observed difference.
- The exported HTML contains both observations and their content hashes.

This is an intentional fixture, not a production outage. Loopback addresses point to each machine itself. The plugin does not start or stop the fixture, execute remote commands, or authenticate a machine through its label.

The edited demo is 60 seconds, 1920×1080 at 30 fps. It uses actual native footage, labelled replay graphics, AI-generated narration and an original synthesised soundtrack. The final video/audio decode, transcript and caption-placement checks passed.

## Limits and publication gates

Synthetic fixtures test contracts and adverse cases; they do not establish live remote behaviour. The two-machine run establishes those recorded observations, not universal compatibility.

The product targets macOS and Linux. Its POSIX evidence store rejects symlink ancestors. The repository CI matrix covers supported Python versions on both platforms; local validation is distinct from remote CI.

Independent SPEC then QUALITY review, the exact public commit, remote CI, catalog PR, X post and contest-form confirmation remain separate release records. A catalog PR is not maintainer acceptance, and a demo video alone is not a submitted entry.
