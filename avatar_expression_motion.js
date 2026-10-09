/* Small deterministic, testable timing controller for natural bilateral blinks. */
(function (root) {
  'use strict';
  function clamp01(value) { return Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0)); }
  function smoothstep01(value) { const t = clamp01(value); return t * t * (3 - 2 * t); }
  function positiveMs(value, fallback) { return Number.isFinite(value) && value > 0 ? value : fallback; }
  function createBlinkController(options) {
    const opts = options || {};
    const random = typeof opts.random === 'function' ? opts.random : Math.random;
    const minInterval = positiveMs(opts.minInterval, 2800);
    const maxInterval = Math.max(minInterval, positiveMs(opts.maxInterval, 5200));
    const closeMs = positiveMs(opts.closeMs, 95);
    const holdMs = Number.isFinite(opts.holdMs) && opts.holdMs >= 0 ? opts.holdMs : 55;
    const openMs = positiveMs(opts.openMs, 165);
    let nextBlinkAt = null;
    let startedAt = null;
    function schedule(from) {
      const r = clamp01(random());
      nextBlinkAt = from + minInterval + r * Math.max(0, maxInterval - minInterval);
    }
    function reset() { nextBlinkAt = null; startedAt = null; }
    function update(now, enabled) {
      if (!enabled || !Number.isFinite(now)) { reset(); return 0; }
      if (startedAt === null && nextBlinkAt === null) { schedule(now); return 0; }
      if (startedAt === null && now >= nextBlinkAt) {
        startedAt = nextBlinkAt;
        nextBlinkAt = null;
      }
      if (startedAt === null) return 0;
      const elapsed = Math.max(0, now - startedAt);
      const total = closeMs + holdMs + openMs;
      if (elapsed >= total) { const endedAt = startedAt + total; startedAt = null; schedule(endedAt); return 0; }
      if (elapsed < closeMs) return smoothstep01(elapsed / closeMs);
      if (elapsed < closeMs + holdMs) return 1;
      return 1 - smoothstep01((elapsed - closeMs - holdMs) / openMs);
    }
    return { update, reset };
  }
  const api = { createBlinkController, smoothstep01 };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.AvatarExpressionMotion = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
