# Network X-ray Implementation Plan

> **For Hermes:** Use subagent-driven-development to implement this plan with SPEC review before QUALITY review.

**Goal:** Ship a reliable, visually polished Hermes plugin that compares read-only network observations from two vantage points, then publish a real demo and submit the hackathon entry.

**Architecture:** A stdlib Python collector/domain layer produces strictly validated evidence bundles. Thin Hermes tool/CLI/FastAPI adapters persist profile-local records. One shared React app renders native Desktop and an isolated local development/demo harness; static exports contain no executable untrusted content or external assets.

**Tech stack:** Python 3.10+ stdlib core, Hermes public plugin SDK, host FastAPI, readable ESM React UI, esbuild development build, pytest + browser tests. No runtime vendor account or paid API required.

**Frozen contract:** `docs/CONTRACT.md`. No worker changes public shapes without parent approval. Research evidence is in the sibling `hermes-hackathon-research-2026-11-05/` directory; do not publish private research or host details.

## Gates and ownership

- Parent owns contract, adapters, integration, documentation, publishing and final acceptance.
- Core writer owns `network_xray/` and `tests/test_core*.py` only.
- UI writer owns `ui/` and `tests/ui/` only after SDK preflight and core contract freeze.
- No concurrent edits to another writer's files. Reviewers are read-only against a frozen commit/worktree.
- Never dump environment values, read credential stores, alter provider defaults/fallbacks, patch Hermes core, install into other profiles, or publish private probes.

## Task 1 — preflight and contracts

Files: `docs/CONTRACT.md`, this plan, `.gitignore`, `pyproject.toml`, `package.json`.

1. Verify external workspace mount, installed Hermes version and toolchain.
2. Exercise a scratch minimal public-API plugin with real doctor/validate.
3. Freeze exact bundle/comparison JSON schemas, bounded side-effect policy and REST/UI seam.
4. Create isolated test environment; verify `python -m pytest --version` and esbuild availability.
5. Initialise new local repository and commit only public source/plan. No remote publication until inspected.

## Task 2 — bounded collector and strict evidence bundles

Files: `network_xray/collector.py`, `network_xray/bundles.py`, `network_xray/__init__.py`, `tests/test_core_probe.py`, `tests/test_core_bundles.py`.

1. Write and run failing URL/IP rejection tests and bundle contract tests.
2. Implement URL validation, canonical integrity sealing, duplicate-key-safe parsing and exact nested validation.
3. Write local HTTP fixture tests before network implementation: success, 500, redirect, oversized headers, timeout and refusal.
4. Implement stdlib DNS/TCP/TLS/HEAD collector and isolated owned subprocess deadline with clean environment.
5. Exercise real invalid-certificate fixture; assert no HTTP dispatch after TLS failure.
6. Run copied standalone collector with Python against loopback and validate its output through the same bundle validator.
7. Compile and run focused tests; retain output. No fabricated live result fixtures.

Expected public functions: `collector.probe(url,label,connect_ip=None)`; `bundles.validate_bundle`, `parse_bundle`, `seal_bundle`, `overall`. Collector file is executable directly and copied unchanged to second host. No package imports in standalone collector execution.

## Task 3 — deterministic comparison and storage

Files: `network_xray/compare.py`, `network_xray/store.py`, `tests/test_core_compare.py`, `tests/test_core_store.py`.

1. Write explicit failure/healthy/inconclusive/CDN-difference/override tests.
2. Implement `compare.compare(left,right)` against frozen JSON contract, hypotheses not causal claims.
3. Implement `Store(root).save_probe(bundle,origin)`, `get_probe(id)`, `list_probes()`; atomic persistence, restrictive directory/files, bounded limits, id/content collision checking and symlink rejection.
4. Reopen Store to prove persistence; exercise concurrent writes and malicious imports.
5. Run core suite; report scope and known limitations.

## Task 4 — native plugin, service and export adapters

Files: root `__init__.py`, `plugin.yaml`, `schemas.py`, `service.py`, `dashboard/plugin_api.py`, `cli.py`, `skills/network-xray/SKILL.md`, `export.py`, `tests/test_adapters.py`.

1. Write registration contract test and exact API error/size tests.
2. Register four explicit native tools, CLI if supported, and a workflow skill; no hooks or middleware.
3. Resolve plugin storage per invocation from documented host helper, not at import/global profile state.
4. Expose own-namespace API routes exactly as contract, including source collector download and escaped self-contained evidence export.
5. Validate imports and outputs with real plugin doctor/validate against an isolated home; fix warnings rather than hide them.
6. Run same engine via tools and REST and compare outputs.

## Task 5 — user interface

Files: `ui/app.js`, `ui/styles.js`, `ui/desktop-entry.js`, `ui/dev-entry.js`, `tests/ui/` (source); generated `desktop/plugin.js`, `web/` build outputs owned by parent build.

1. Build semantic page shell, empty state and URL/label inputs against frozen service API.
2. Implement actual collection, import, saved left/right selection and comparison.
3. Render two four-stage ladders, evidence drawer, verdict banner, origin/time/override badges and manual experiment controls.
4. Make loading, validation, network failure and unsupported states visible; no fake results or endless animations.
5. Add download/export, portable-collector instructions, keyboard navigation, reduced motion and mobile layout.
6. Browser tests click through real backend: collect, import, compare, inspect, reject malformed input and export.
7. Capture actual UI; assess visual hierarchy and fix concrete issues. No native app DOM manipulation.

## Task 6 — integrated acceptance and independent reviews

Files: `scripts/verify.py`, tests, `docs/VERIFICATION.md` (public summarised), private evidence outside repo.

1. Run full core + adapter + browser suite from a frozen candidate.
2. Run real probe on Mac and portable collector on DGX (key-only SSH first; brokered auth only if needed). No system configuration changes.
3. Use controlled service fault with clear disclosure. Preserve raw capture provenance privately and a sanitised, explicitly reviewed public evidence set.
4. Freeze commit, dispatch independent SPEC review; repair blockers and re-freeze/recheck as needed.
5. After SPEC PASS, dispatch independent QUALITY/security/reliability review. No public release with unresolved critical/important findings.
6. Validate clean installation and exact manifest capability set. Record actual source commit and test results, not intended outputs.

## Task 7 — demo and public release

Files: `README.md`, `LICENSE`, `CHANGELOG.md`, `docs/demo-script.md`, `docs/screenshots/`, GitHub CI workflows. Demo media kept outside plugin source if large.

1. README Australian English, AI-assisted development disclosure, precise supported platforms, security/network/storage disclosures and explicit limitations.
2. Record actual plugin/UI interactions and real probe outputs; label controlled faults and recorded observations. Aim 65–85 seconds including intro/outro.
3. Verify video duration/codec/audio and visually inspect frames; no secrets, private hostnames, unrelated screen content or misleading cuts.
4. Secret/PII/source scan, clean tree build and tests, publish public repo/release through approved GitHub identity; read back exact commit, visibility, release and assets.
5. Create upstream catalog PR containing one catalog YAML, full reviewed SHA, truthful version/floor/capabilities, screenshots and disclosures. Read back exact PR head/body/open state. Maintainer-triggered catalog CI may remain pending; report honestly.

## Task 8 — X and form submission

1. Verify X identity using approved Vault wrapper (already reachable as @mrru5s3ll).
2. Upload demo video, verify processing, publish <=280-character post tagging @NousResearch and linking repo/catalog PR as space permits.
3. Immediately read back exact post ID, author, full text, expanded URLs and video attachment. Never duplicate a post after an ambiguous response without exact-ID reconciliation.
4. Complete Typeform at `https://form.typeform.com/to/FwJLvOln` with verified PR/X links and accurate entrant/project details. Ask only if a required personal field or attestation cannot be established.
5. Verify final submission confirmation; save non-secret receipt/screenshot. Do not equate starting the form with submitting it.

## Completion criteria

Deliver installable public plugin/release, passing stated verification, playable <90s demo, open upstream catalog PR, exact public X video post, and Typeform confirmation. If a provider or organiser gate blocks any item, explicitly name the verified blocker and preserve all completed artifacts; do not claim acceptance or submission without evidence.
