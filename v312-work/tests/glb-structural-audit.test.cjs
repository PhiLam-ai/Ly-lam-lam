'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { auditGlbBytes } = require('../tools/glb-structural-audit.cjs');

function makeGlb(doc, bin = Buffer.from([1, 2, 3, 4])) {
  const jsonText = JSON.stringify(doc);
  const jsonLength = Math.ceil(Buffer.byteLength(jsonText) / 4) * 4;
  const json = Buffer.alloc(jsonLength, 0x20);
  json.write(jsonText, 'utf8');
  const binLength = Math.ceil(bin.length / 4) * 4;
  const paddedBin = Buffer.alloc(binLength);
  bin.copy(paddedBin);
  const total = 12 + 8 + json.length + 8 + paddedBin.length;
  const out = Buffer.alloc(total);
  out.write('glTF', 0, 'ascii'); out.writeUInt32LE(2, 4); out.writeUInt32LE(total, 8);
  out.writeUInt32LE(json.length, 12); out.writeUInt32LE(0x4e4f534a, 16); json.copy(out, 20);
  const binHeader = 20 + json.length;
  out.writeUInt32LE(paddedBin.length, binHeader); out.writeUInt32LE(0x004e4942, binHeader + 4); paddedBin.copy(out, binHeader + 8);
  return out;
}
const minimal = (overrides = {}) => ({ asset: { version: '2.0' }, buffers: [{ byteLength: 4 }], bufferViews: [{ buffer: 0, byteOffset: 0, byteLength: 4 }], accessors: [{ bufferView: 0, componentType: 5121, count: 4, type: 'SCALAR' }], meshes: [{ primitives: [{ attributes: { POSITION: 0 } }] }], nodes: [{ mesh: 0 }], scenes: [{ nodes: [0] }], scene: 0, ...overrides });

test('V310 structural GLB audit accepts the project model and reports useful counts', () => {
  const root = path.resolve(__dirname, '..');
  const result = auditGlbBytes(fs.readFileSync(path.join(root, 'lam-default.glb')));
  assert.equal(result.ok, true, result.errors.join('; '));
  assert.equal(result.summary.bytes, 390580);
  assert.equal(result.summary.nodes, 103);
  assert.equal(result.summary.meshes, 85);
  assert.equal(result.summary.accessors, 425);
  assert.equal(result.summary.bufferViews, 425);
});

test('V310 structural GLB audit accepts a valid minimal embedded GLB', () => {
  const result = auditGlbBytes(makeGlb(minimal()));
  assert.equal(result.ok, true, result.errors.join('; '));
  assert.equal(result.summary.nodes, 1);
});

test('V310 structural GLB audit rejects bufferViews beyond the declared buffer and actual BIN chunk', () => {
  const doc = minimal({ bufferViews: [{ buffer: 0, byteOffset: 2, byteLength: 4 }] });
  const result = auditGlbBytes(makeGlb(doc));
  assert.equal(result.ok, false);
  assert.ok(result.errors.some(message => message.includes('vượt quá độ dài buffer khai báo')));
  assert.ok(result.errors.some(message => message.includes('vượt quá dữ liệu BIN thực tế')));
});

test('V310 structural GLB audit rejects broken accessor and mesh references', () => {
  const doc = minimal({ accessors: [{ bufferView: 9, componentType: 5121, count: 4, type: 'SCALAR' }], meshes: [{ primitives: [{ attributes: { POSITION: 9 }, indices: 4 }] }] });
  const result = auditGlbBytes(makeGlb(doc));
  assert.equal(result.ok, false);
  assert.ok(result.errors.some(message => message.includes('accessors[0].bufferView')));
  assert.ok(result.errors.some(message => message.includes('attribute accessor')));
  assert.ok(result.errors.some(message => message.includes('indices accessor')));
});

test('V310 structural GLB audit rejects malformed chunk headers and invalid JSON', () => {
  const short = Buffer.from('glTF');
  assert.equal(auditGlbBytes(short).ok, false);
  const broken = makeGlb(minimal());
  broken.writeUInt32LE(0xffffffff, 12);
  const result = auditGlbBytes(broken);
  assert.equal(result.ok, false);
  assert.ok(result.errors.some(message => /exceeds|vượt quá|cắt cụt|độ dài/i.test(message)));
});

test('V310 startup preflight invokes the structural GLB audit and fails closed on audit errors', () => {
  const preflight = fs.readFileSync(path.join(__dirname, '..', 'tools', 'startup-preflight.cjs'), 'utf8');
  assert.match(preflight, /require\('\.\/glb-structural-audit\.cjs'\)/);
  assert.match(preflight, /auditGlbBytes\(fs\.readFileSync\(glbPath\)\)/);
  assert.match(preflight, /errors\.push\(\.\.\.audit\.errors/);
});
