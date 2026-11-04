# Network X-ray UI

`createApp(React, api)` is the shared native/browser component factory. It never starts probes on mount; mount reads history only. Real probe values, comparison findings and suggestions come exclusively from the adapter. Synthetic fixtures exist only under `tests/ui/`.

## Entries

- `ui/desktop-entry.js`: parent bundles to a single native ESM file, keeping **only `react` and `@hermes/plugin-sdk` external**. Registers `/network-xray` page and sidebar navigation with `ctx.registerMany`. Uses `ctx.rest` decoded JSON directly, body objects and explicit timeouts.
- `ui/dev-entry.js`: parent bundles React + ReactDOM for a standalone document containing `<div id="root"></div>`. Uses relative `/api/plugins/network-xray` fetch; no CDN, secrets, or remote execution.
- `ui/styles.js`: scoped `.nx-root` CSS; native text, stroke and surface variables with graphite/light fallbacks. No core selectors or DOM writes. Only download anchors are constructed outside React, never attached to core UI.

Native compatibility checked against installed Hermes 0.22.5 source: `host.state.connectionId` (`null|string`) and `host.state.profile` (active gateway profile) are readonly nanostore atoms with `.get()` and `.subscribe(callback)` returning disposers. REST scope follows these atoms, not the focused chat. No `ctx.files`, `ctx.preview`, Node imports, or Fetch `.json()` on SDK responses. Native runtime integration still needs parent verification.

## Lifetime and trust boundaries

Owner changes reset the complete workspace and synchronously invalidate prior requests, including A→B→A identity round trips. Each request lane has an independent generation; new selections invalidate old comparison/report responses immediately, and file reads cannot post into a newly selected owner. User selection changes during capture prevent the completed capture from replacing the user's selection. StrictMode mount-effect replay has a browser test.

UI import rejects files larger than 128 KiB, invalid JSON and duplicate keys before transport. Server remains authoritative for schema, safety, integrity, and origin. Evidence is React text, not HTML. Exported HTML is downloaded, never embedded or executed. Blob URLs are revoked. Suggested tests preserve the server's exact URL/connect_ip and need an explicit checkbox + labelled local-vantage Run action.

## Verification

```sh
node --check ui/app.js
node --check ui/styles.js
node --check ui/desktop-entry.js
node --check ui/dev-entry.js
node --test tests/ui/helpers.test.mjs
.venv/bin/python -m pytest tests/ui/test_render_contract.py -q
```

The browser tests compile a **synthetic, mock-API** harness into `$TMPDIR`, serve it on an ephemeral loopback port and launch headless Chromium. They cover statuses, evidence, literal hostile strings, provenance, override disclosure, empty/validation/timeout states, duplicate/oversized imports, downloads, narrow layout, confirmation payloads, owner and selection races, and StrictMode. They do **not** prove real backend, collector, native auth/routing, second-host observations, or production integration. No test service survives the test fixture.

Design/code self-review: 8/10. Established spacing/type scales, native theme fallbacks, accessible focus/text statuses, and split transport/rendering; remaining improvement is decomposing the large workspace orchestration/render function and checking real native theme/accessibility contrast across installed themes. Parent owns integration and visual evidence.
