'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const api = require('../avatar_api_client.js');

const morphs = [
  'smile', 'blink_left', 'blink_right', 'mouth_open', 'jaw_open', 'jaw_hinge',
  'brow_raise', 'cheek_raise', 'lip_press', 'lip_fv', 'lip_round', 'tongue_tip'
];
const page = 'https://philam-ai.github.io/Ly-lam-lam/';

test('no endpoint is explicitly treated as not configured', () => {
  assert.deepEqual(api.resolveEndpoint('', page), {
    ok: false, configured: false, reason: 'not-configured', url: null
  });
});

test('resolves relative endpoint on same HTTPS origin', () => {
  const result = api.resolveEndpoint('./api/avatar/state', page);
  assert.equal(result.ok, true);
  assert.equal(result.url, 'https://philam-ai.github.io/Ly-lam-lam/api/avatar/state');
});

test('rejects malformed URLs, unsupported protocols, credentials and mixed content', () => {
  assert.equal(api.resolveEndpoint('http://[::bad', page).reason, 'invalid-url');
  assert.equal(api.resolveEndpoint('data:text/plain,hi', page).reason, 'unsupported-protocol');
  assert.equal(api.resolveEndpoint('https://user:pass@example.com/state', page).reason, 'credentials-in-url');
  assert.equal(api.resolveEndpoint('http://api.example.test/state', page).reason, 'mixed-content');
});

test('maps a valid versioned payload to all twelve morph names', () => {
  const parsed = api.parseStatePayload({
    schema: api.SCHEMA,
    version: 1,
    sequence: 12,
    emitted_at: '2026-10-17T12:00:00Z',
    weights: { smile: 0.35, mouth_open: 0.2 }
  }, morphs);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.weights.smile, 0.35);
  assert.equal(parsed.weights.mouth_open, 0.2);
  assert.equal(parsed.weights.blink_left, 0);
  assert.equal(parsed.weights.tongue_tip, 0);
  assert.equal(parsed.sequence, 12);
});

test('rejects malformed or incompatible payloads', () => {
  assert.equal(api.parseStatePayload(null, morphs).reason, 'invalid-payload');
  assert.equal(api.parseStatePayload({ schema: 'other', version: 1, weights: { smile: 0.2 } }, morphs).reason, 'unsupported-schema');
  assert.equal(api.parseStatePayload({ schema: api.SCHEMA, version: 2, weights: { smile: 0.2 } }, morphs).reason, 'unsupported-schema');
  assert.equal(api.parseStatePayload({ schema: api.SCHEMA, version: 1, weights: [] }, morphs).reason, 'invalid-weights-object');
  assert.equal(api.parseStatePayload({ schema: api.SCHEMA, version: 1, weights: {} }, morphs).reason, 'empty-weights');
  assert.equal(api.parseStatePayload({ schema: api.SCHEMA, version: 1, weights: { smile: 1.1 } }, morphs).reason, 'invalid-weight');
  assert.equal(api.parseStatePayload({ schema: api.SCHEMA, version: 1, weights: { smile: '0.5' } }, morphs).reason, 'invalid-weight');
  const unknown = api.parseStatePayload({ schema: api.SCHEMA, version: 1, weights: { happiness: 0.5 } }, morphs);
  assert.equal(unknown.reason, 'unknown-morphs');
  assert.deepEqual(unknown.unknown, ['happiness']);
});
