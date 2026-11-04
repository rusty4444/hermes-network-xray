import test from 'node:test';
import assert from 'node:assert/strict';
import { createOperationGuard, formatDuration, parseImportText, validateRequest, errorMessage } from '../../ui/app.js';

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
