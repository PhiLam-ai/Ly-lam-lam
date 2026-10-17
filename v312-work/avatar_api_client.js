/* Configurable, read-only avatar state API contract. No endpoint is assumed. */
(function(root){
  'use strict';

  const SCHEMA = 'ly-lam-lam/avatar-state';
  const VALID_PROTOCOLS = new Set(['http:', 'https:']);

  function resolveEndpoint(candidate, pageHref) {
    if (typeof candidate !== 'string' || !candidate.trim()) {
      return { ok: false, configured: false, reason: 'not-configured', url: null };
    }

    let pageUrl;
    let endpoint;
    try {
      pageUrl = new URL(pageHref);
      endpoint = new URL(candidate.trim(), pageUrl);
    } catch (_) {
      return { ok: false, configured: true, reason: 'invalid-url', url: null };
    }

    if (!VALID_PROTOCOLS.has(endpoint.protocol)) {
      return { ok: false, configured: true, reason: 'unsupported-protocol', url: null };
    }
    if (endpoint.username || endpoint.password) {
      return { ok: false, configured: true, reason: 'credentials-in-url', url: null };
    }
    if (pageUrl.protocol === 'https:' && endpoint.protocol !== 'https:') {
      return { ok: false, configured: true, reason: 'mixed-content', url: null };
    }

    endpoint.hash = '';
    return { ok: true, configured: true, reason: null, url: endpoint.href };
  }

  function parseStatePayload(payload, expectedMorphs) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return { ok: false, reason: 'invalid-payload' };
    }
    if (payload.schema !== SCHEMA || payload.version !== 1) {
      return { ok: false, reason: 'unsupported-schema' };
    }
    if (!payload.weights || typeof payload.weights !== 'object' || Array.isArray(payload.weights)) {
      return { ok: false, reason: 'invalid-weights-object' };
    }
    if (!Array.isArray(expectedMorphs) || expectedMorphs.length === 0) {
      return { ok: false, reason: 'invalid-expected-morphs' };
    }

    const names = new Set(expectedMorphs);
    const incoming = Object.keys(payload.weights);
    if (incoming.length === 0) {
      return { ok: false, reason: 'empty-weights' };
    }
    const unknown = incoming.filter(name => !names.has(name));
    if (unknown.length) {
      return { ok: false, reason: 'unknown-morphs', unknown };
    }

    const weights = {};
    for (const name of expectedMorphs) {
      const value = Object.prototype.hasOwnProperty.call(payload.weights, name)
        ? payload.weights[name]
        : 0;
      if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) {
        return { ok: false, reason: 'invalid-weight', morph: name };
      }
      weights[name] = value;
    }
    return {
      ok: true,
      weights,
      emitted_at: typeof payload.emitted_at === 'string' ? payload.emitted_at : null,
      sequence: Number.isSafeInteger(payload.sequence) && payload.sequence >= 0
        ? payload.sequence : null
    };
  }

  const api = { SCHEMA, resolveEndpoint, parseStatePayload };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.AvatarApiClient = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
