'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const repo = path.resolve(__dirname, '../..');
const app = path.join(repo, 'v312-work');
const html = fs.readFileSync(path.join(app, 'index.html'), 'utf8');

function readGlbJson(filePath) {
  const data = fs.readFileSync(filePath);
  assert.ok(data.length >= 20, 'GLB must have a header and at least one chunk');
  assert.equal(data.toString('ascii', 0, 4), 'glTF', 'GLB magic');
  assert.equal(data.readUInt32LE(4), 2, 'glTF version 2');
  assert.equal(data.readUInt32LE(8), data.length, 'declared file length');
  let offset = 12;
  let doc = null;
  while (offset < data.length) {
    assert.ok(offset + 8 <= data.length, 'chunk header fits');
    const length = data.readUInt32LE(offset);
    const type = data.readUInt32LE(offset + 4);
    offset += 8;
    assert.ok(offset + length <= data.length, 'chunk fits file');
    if (type === 0x4e4f534a) {
      doc = JSON.parse(data.subarray(offset, offset + length).toString('utf8').replace(/[\u0000\u0020]+$/g, ''));
    }
    offset += length;
  }
  assert.equal(offset, data.length, 'all GLB chunks end at EOF');
  assert.ok(doc && doc.asset && doc.asset.version === '2.0', 'valid glTF 2.0 JSON chunk');
  return doc;
}

test('current GitHub Pages workflow deploys the v312-work directory', () => {
  const workflow = fs.readFileSync(path.join(repo, '.github/workflows/main.yml'), 'utf8');
  assert.match(workflow, /Deploy Lam Avatar to GitHub Pages/);
  assert.match(workflow, /path:\s*\.\/v312-work/);
  assert.match(workflow, /uses:\s*actions\/deploy-pages@v4/);
  const coreGate = workflow.indexOf('node --test v312-work/tests/avatar-core.test.cjs v312-work/tests/glb-structural-audit.test.cjs');
  const targetGate = workflow.indexOf('node --test automation/tests/v312-package-integrity.test.cjs');
  const deployStep = workflow.indexOf('uses: actions/deploy-pages@v4');
  assert.ok(coreGate >= 0 && targetGate > coreGate, 'both blocking test gates are declared before deployment');
  assert.ok(deployStep > targetGate, 'Pages deployment must be later than both test gates');
});

test('deployed V312 entry page uses bundled runtime assets that exist in the package', () => {
  assert.ok(html.length > 1000, 'application entry page exists');
  assert.match(html, /<html lang="vi">/i);
  assert.ok(html.includes("const local=mode==='local'||mode===null;"), 'missing explicit local-first default for the bundled runtime');
  assert.ok(html.includes("const base=local?'./vendor/three/':mode==='unpkg'?'https://unpkg.com/three@0.160.0/':'https://cdn.jsdelivr.net/npm/three@0.160.0/';"), 'local is default; pinned CDN paths remain explicit fallbacks');
  assert.match(html, /\.\/vendor\/three\//, 'runtime should use locally bundled Three.js assets');
  const assets = [
    'vendor/three/build/three.module.js',
    'vendor/three/examples/jsm/loaders/GLTFLoader.js',
    'vendor/three/examples/jsm/controls/OrbitControls.js'
  ];
  for (const rel of assets) {
    const p = path.join(app, rel);
    assert.ok(fs.existsSync(p) && fs.statSync(p).size > 1000, `runtime module exists: ${rel}`);
  }
});

test('actual Pages payload contains no symbolic links', () => {
  const inspect = (directory) => {
    for (const name of fs.readdirSync(directory)) {
      const item = path.join(directory, name);
      const stat = fs.lstatSync(item);
      assert.equal(stat.isSymbolicLink(), false, 'deployed payload must not contain symlinks: ' + path.relative(app, item));
      if (stat.isDirectory()) inspect(item);
    }
  };
  inspect(app);
});

test('deployed V312 page has iPhone-safe viewport and accessible avatar controls', () => {
  assert.match(html, /viewport-fit=cover/);
  assert.match(html, /height:\s*100dvh/);
  assert.match(html, /safe-area-inset-top/);
  assert.match(html, /safe-area-inset-left/);
  for (const id of ['quick-controls', 'view-face', 'view-full', 'zoom-in', 'zoom-out', 'view-reset', 'help-toggle', 'help']) {
    assert.match(html, new RegExp(`id=["']${id}["']`), `missing mobile control: ${id}`);
  }
});

test('diagnostics remain opt-in and the normal launch points at the bundled GLB', () => {
  assert.match(html, /targetUrl\s*=\s*['"]\.\/lam-default\.glb['"]/);
  assert.match(html, /get\(['"]diagnostics['"]\)\s*===\s*['"]1['"]/);
  assert.match(html, /avatar_expression_motion\.js/);
  assert.match(html, /avatar_mesh_inspector\.js/);
});

test('bundled GLB is structurally sound and carries all 12 expected morph names', () => {
  const doc = readGlbJson(path.join(app, 'lam-default.glb'));
  assert.ok(Array.isArray(doc.nodes) && doc.nodes.length > 0, 'nodes exist');
  assert.ok(Array.isArray(doc.meshes) && doc.meshes.length > 0, 'meshes exist');
  const morphs = new Set(doc.meshes.flatMap(mesh => mesh.extras?.targetNames || []));
  const expected = [
    'smile', 'blink_left', 'blink_right', 'mouth_open', 'jaw_open', 'jaw_hinge',
    'brow_raise', 'cheek_raise', 'lip_press', 'lip_fv', 'lip_round', 'tongue_tip'
  ];
  for (const name of expected) assert.ok(morphs.has(name), `missing morph: ${name}`);
});
