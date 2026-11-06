import test from 'node:test';
import assert from 'node:assert/strict';
import { buildImportPayload, createOperationGuard, formatDuration, parseImportText, validateRequest, errorMessage, localError, TIMED_OUT_TEXT, UNREACHABLE_TEXT } from '../../ui/app.js';

test('import transport preserves the original JSON number spellings', () => {
  const raw = '{"a":12000.0,"b":-0.0,"c":1.2e4}';
  assert.notEqual(JSON.stringify(JSON.parse(raw)), raw);
  assert.deepEqual(JSON.parse(JSON.stringify(buildImportPayload(raw))), { bundle_json: raw });
  assert.throws(() => buildImportPayload('{"a":1,"a":2}'), /Duplicate/);
});

test('new operations invalidate only their own slot', () => {
  const guard = createOperationGuard(() => 'owner-A');
  const first = guard.begin('left');
  const right = guard.begin('right');
  const latest = guard.begin('left');
  assert.equal(first(), false);
  assert.equal(right(), true);
  assert.equal(latest(), true);
  guard.invalidate('left');
  assert.equal(latest(), false);
  guard.dispose();
  assert.equal(right(), false);
});

test('owner changes prevent an outstanding response from applying', () => {
  let owner = 'A';
  const guard = createOperationGuard(() => owner);
  const current = guard.begin('probe');
  owner = 'B';
  assert.equal(current(), false);
});

test('duration never invents a measurement for unknown values', () => {
  for (const value of [null, undefined, NaN, Infinity, -1, true, '4']) assert.equal(formatDuration(value), 'Not measured');
  assert.equal(formatDuration(0), '0 ms');
});

test('request preflight rejects secrets and malformed URLs without repair', () => {
  for (const url of [' https://example.com', 'example.com', 'ftp://example.com', 'https://a:b@example.com', 'https://example.com?', 'https://example.com#', 'https://example.com/\\path']) {
    assert.notEqual(validateRequest(url, 'Local'), '', url);
  }
  assert.equal(validateRequest('https://example.com/path', 'Local'), '');
  assert.notEqual(validateRequest('https://example.com/', ''), '');
});

test('imports preserve JSON values and reject duplicate keys before transport', () => {
  const input = { a: [{ x: 'comma, colon: and escaped "quote"', y: { nested: true } }], b: { x: null }, c: 1 };
  assert.deepEqual(parseImportText(JSON.stringify(input)), input);
  assert.throws(() => parseImportText('{"a":1,"a":2}'), /Duplicate/);
  assert.throws(() => parseImportText('{"a":{"x":1,"\\u0078":2}}'), /Duplicate/);
  assert.throws(() => parseImportText('{"a":[{"x":1,"x":2}]}'), /Duplicate/);
  assert.throws(() => parseImportText('{bad}'));
});

test('timeout messages do not falsely diagnose DNS', () => {
  assert.match(errorMessage(new Error('deadline exceeded')), /not evidence of a DNS/);
  assert.equal(errorMessage(new Error('Invalid label')), 'Invalid label');
});

// Hermes Desktop's ctx.rest: `${status}: ${body}` from main; every status but 404 behind the IPC prefix.
const desktop = (status, body) => new Error(status === 404 ? `${status}: ${body}` : `Error invoking remote method 'hermes:api': Error: ${status}: ${body}`);

test('Hermes Desktop rejections show the backend detail, not the IPC wrapper', () => {
  const invalid = 'Invalid input: check URL, fields, bundle schema/digest, and matching targets';
  assert.equal(errorMessage(desktop(400, JSON.stringify({ detail: invalid }))), invalid);
  assert.equal(errorMessage(desktop(404, '{"detail":"Probe not found in the active profile"}')), 'Probe not found in the active profile');
  assert.equal(errorMessage(desktop(429, '{"detail":"Four probes are already running; retry after they finish"}')), 'Four probes are already running; retry after they finish');
  assert.equal(errorMessage(desktop(403, '{"detail":{"message":"Cross-site requests are not accepted"}}')), 'Cross-site requests are not accepted');
  // A detail that merely contains a "<" is real text and stays.
  assert.equal(errorMessage(desktop(400, '{"detail":"Use a < 2048 character URL"}')), 'Use a < 2048 character URL');
  for (const shown of [errorMessage(desktop(400, '{"detail":"x"}')), errorMessage(desktop(503, 'oops'))]) {
    assert.doesNotMatch(shown, /Error invoking|hermes:api/);
  }
});

test('markup, empty and non-JSON bodies get a plain status message', () => {
  for (const body of ['<h1>Bad Gateway</h1>', '<!doctype html><html><body>502</body></html>', '']) {
    const shown = errorMessage(desktop(502, body));
    assert.match(shown, /^The Network X-ray backend failed \(HTTP 502\)\. .*not evidence about the target URL/);
    assert.doesNotMatch(shown, /Check the URL|</);
  }
  assert.equal(errorMessage(desktop(503, 'Service Unavailable')), 'Service Unavailable');
  // Only a request the backend judged bad points at the URL or bundle.
  assert.equal(errorMessage(desktop(400, '<p>bad</p>')), 'Backend rejected the request (HTTP 400). Check the URL or bundle and retry.');
  for (const status of [401, 403]) {
    const shown = errorMessage(desktop(status, '<html>denied</html>'));
    assert.match(shown, new RegExp(`^Hermes or a proxy in front of it refused the request \\(HTTP ${status}\\)\\. .*not evidence about the target URL`));
  }
});

test('errors the page raises itself are shown as written', () => {
  // V8 quotes the start of a bad file in its JSON.parse message, so file text must never be classified.
  for (const text of ['Network error report', 'connection refused at 09:00', 'fetch failed', 'Request timeout']) {
    const message = `This file is not valid JSON or contains duplicate keys. Choose an unmodified probe bundle. Unexpected token 'N', "${text}" is not valid JSON`;
    assert.equal(errorMessage(localError(message)), message);
  }
});

test("Hermes's own diagnosis survives when there is no HTTP status", () => {
  const ipc = message => new Error(`Error invoking remote method 'hermes:api': Error: ${message}`);
  const proxy = 'Expected JSON from http://127.0.0.1:9119/api/plugins/network-xray/history but the request was redirected (status 302) to https://sso.example/login. This is usually an authentication proxy.';
  assert.equal(errorMessage(ipc(proxy)), `Hermes could not complete the request: ${proxy} This is about the connection to the backend, not evidence about the target URL.`);
  assert.match(errorMessage(ipc('Gateway incompatible (runtime_protocol). Use hermes gateway status for recovery.')), /^Hermes could not complete the request: Gateway incompatible/);
  assert.match(errorMessage(ipc('x'.repeat(1000))), /x…  ?This is about/);
  // Connection failures and markup still get the plain unreachable text.
  assert.equal(errorMessage(ipc('connect ECONNREFUSED 127.0.0.1:9119')), UNREACHABLE_TEXT);
  assert.equal(errorMessage(ipc('<html>proxy</html>')), UNREACHABLE_TEXT);
  assert.equal(errorMessage(ipc('Timed out connecting to Hermes backend after 20000ms')), TIMED_OUT_TEXT);
});

test('the plugin host deadline and IPC transport failures are not target evidence', () => {
  assert.equal(errorMessage(desktop(504, '{"detail":"plugin \'network-xray\' did not answer within 60s"}')), TIMED_OUT_TEXT);
  assert.equal(errorMessage(desktop(504, '')), TIMED_OUT_TEXT);
  const abort = new Error('The operation was aborted'); abort.name = 'AbortError';
  assert.equal(errorMessage(abort), TIMED_OUT_TEXT);
  // No HTTP status: the request failed on the way to Hermes, not at the probed URL.
  assert.equal(errorMessage(new Error("Error invoking remote method 'hermes:api': TypeError: fetch failed")), UNREACHABLE_TEXT);
  assert.equal(errorMessage(new Error("Error invoking remote method 'hermes:api': Error: socket hang up")), UNREACHABLE_TEXT);
  assert.equal(errorMessage(new TypeError('Failed to fetch')), UNREACHABLE_TEXT);
  assert.match(UNREACHABLE_TEXT, /not evidence about the target URL/);
});
