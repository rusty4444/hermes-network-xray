// SYNTHETIC render-contract harness. Never imported by production entries.
import * as React from 'react';
import { createRoot } from 'react-dom/client';
import { createApp } from '../../ui/app.js';

function probe(id, label, failed = false) {
  return {
    schema_version: 1, kind: 'network_xray.probe', id, captured_at: '2026-01-01T00:00:00Z',
    vantage: { label, platform: 'synthetic-test', python: '3.12' },
    target: { url: 'https://synthetic.example/', host: 'synthetic.example', scheme: 'https', port: 443, path: '/', connect_ip: null },
    policy: { method: 'HEAD', redirects: 'not_followed', tls_verification: true, proxy: 'direct', body_capture: false },
    capture: { status: 'complete', duration_ms: 34.5, error: null },
    stages: ['dns', 'tcp', 'tls', 'http'].map((name, index) => ({
      name, status: failed && index === 2 ? 'error' : failed && index === 3 ? 'skipped' : 'ok',
      duration_ms: failed && index === 3 ? null : index + 0.5,
      summary: failed && index === 2 ? 'Synthetic certificate failure' : failed && index === 3 ? 'Previous stage failed' : `Synthetic ${name} observation`,
      details: index === 0 ? { addresses: ['192.0.2.1'], truncated: false }
        : index === 1 ? { address: '192.0.2.1', port: 443, family: 'ipv4', selection: 'dns' }
        : index === 2 ? { certificate_sha256: 'a'.repeat(64), server_name: 'synthetic.example', verified: !failed }
        : failed ? {} : { status_code: 200, reason: 'OK' }, error: null,
    })), integrity: { algorithm: 'sha256', digest: '0'.repeat(64) },
  };
}
const left = probe('11111111-1111-4111-8111-111111111111', 'Synthetic local');
const right = probe('22222222-2222-4222-8222-222222222222', 'Synthetic peer', true);
const third = probe('33333333-3333-4333-8333-333333333333', 'Synthetic third');
const envelopes = Object.fromEntries([left, right, third].map((value, index) => [value.id, { probe: value, origin: index === 1 ? 'imported' : 'local' }]));
const comparison = {
  schema_version: 1, kind: 'network_xray.comparison', id: 'synthetic-comparison', created_at: left.captured_at,
  left, right, verdict: 'diverged', first_divergence: 'tls', headline: 'TLS verification differs between these captures',
  findings: [
    { kind: 'observation', stage: 'tls', text: 'The recorded TLS outcomes differ.' },
    { kind: 'hypothesis', stage: 'tls', text: 'A different trust configuration could explain this.' },
    { kind: 'limitation', stage: 'capture', text: 'Synthetic test evidence, not a real capture.' },
  ], next_tests: [{ title: 'Try the peer address', reason: 'Isolate address selection.', url: left.target.url, connect_ip: '192.0.2.1', requires_confirmation: true }],
  limitations: ['Imported results are not authenticated.', 'One address per probe.'],
};
const listeners = new Set();
window.mock = {
  owner: 'synthetic-owner-A', requests: [], handlers: {}, pending: {}, envelopes, comparison,
  ids: [left.id, right.id, third.id],
  setOwner(owner) { this.owner = owner; for (const listener of listeners) listener(); },
  defer(path) { this.handlers[path] = () => new Promise((resolve, reject) => { this.pending[path] = { resolve, reject }; }); },
};
const api = {
  ownerKey: () => window.mock.owner,
  subscribeOwner: callback => { listeners.add(callback); return () => listeners.delete(callback); },
  async request(path, options = {}) {
    const mock = window.mock;
    mock.requests.push({ path, options, owner: mock.owner });
    if (mock.handlers[path]) return mock.handlers[path](options);
    if (path === '/probes') return { probes: Object.values(envelopes).map(({ probe: value, origin }) => ({ id: value.id, label: value.vantage.label, url: value.target.url, captured_at: value.captured_at, overall: value === right ? 'failed' : 'healthy', origin })) };
    if (path.startsWith('/probes/')) return envelopes[path.split('/').at(-1)];
    if (path === '/compare') return { ...comparison, left: envelopes[options.body.left_id].probe, right: envelopes[options.body.right_id].probe };
    if (path === '/probe' || path === '/import') return envelopes[left.id];
    if (path === '/collector') return { filename: 'synthetic-collector.py', source: '# synthetic download test only' };
    if (path.startsWith('/export/')) return { filename: 'synthetic-report.html', html: '<!doctype html><title>Synthetic report</title>' };
    throw new Error(`Unexpected test route: ${path}`);
  },
};
const app = React.createElement(createApp(React, api));
createRoot(document.getElementById('root')).render(location.search.includes('strict') ? React.createElement(React.StrictMode, null, app) : app);
