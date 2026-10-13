#!/usr/bin/env node
'use strict';

// Diagnostic-only audit: reports scene hierarchy, transforms and accessor bounds.
// It deliberately does not rewrite the GLB or claim mesh connectivity.
const fs = require('node:fs');
const path = require('node:path');
const file = path.resolve(process.argv[2] || path.join(__dirname, '..', 'lam-default.glb'));
function fail(message) { console.error('FAIL:', message); process.exitCode = 1; }
if (!fs.existsSync(file)) { fail('GLB not found: ' + file); }
else {
  const b = fs.readFileSync(file);
  if (b.length < 20 || b.readUInt32LE(0) !== 0x46546c67 || b.readUInt32LE(4) !== 2) {
    fail('Invalid GLB header/version');
  } else {
    const jsonLength = b.readUInt32LE(12);
    let g;
    try { g = JSON.parse(b.subarray(20, 20 + jsonLength).toString('utf8').trim()); }
    catch (e) { fail('Invalid GLB JSON: ' + e.message); }
    if (g) {
      const nodes = g.nodes || [], meshes = g.meshes || [], accessors = g.accessors || [];
      const parents = new Array(nodes.length).fill(null);
      nodes.forEach((n, i) => (n.children || []).forEach(c => { if (c < parents.length) parents[c] = i; }));
      function vec(v, d) { return Array.isArray(v) ? v : d; }
      function world(i, stack = new Set()) {
        if (stack.has(i)) return { t:[0,0,0], s:[1,1,1], cycle:true };
        stack.add(i);
        const n = nodes[i], p = parents[i];
        const t = vec(n.translation,[0,0,0]), s = vec(n.scale,[1,1,1]);
        if (p == null) return {t,s};
        const pw = world(p,stack);
        return {t:[0,1,2].map(k => pw.t[k] + t[k]*pw.s[k]), s:[0,1,2].map(k=>pw.s[k]*s[k]), cycle:pw.cycle};
      }
      const rows = nodes.map((n,i) => {
        const w = world(i);
        const mesh = n.mesh == null ? null : meshes[n.mesh];
        const prims = (mesh?.primitives || []).map(p => {
          const a = accessors[p.attributes?.POSITION];
          return { positionAccessor:p.attributes?.POSITION, vertices:a?.count ?? null, min:a?.min ?? null, max:a?.max ?? null, targets:(p.targets||[]).length };
        });
        return { index:i, name:n.name || '(unnamed)', parent:parents[i], children:n.children||[], mesh:n.mesh ?? null, skin:n.skin ?? null,
          localTranslation:vec(n.translation,[0,0,0]), localRotation:vec(n.rotation,[0,0,0,1]), localScale:vec(n.scale,[1,1,1]),
          approximateWorldTranslation:w.t, approximateWorldScale:w.s, primitives:prims };
      });
      const scene = g.scenes?.[g.scene || 0];
      console.log(JSON.stringify({
        file:path.basename(file), bytes:b.length, sceneRoots:scene?.nodes||[],
        nodeCount:nodes.length, meshCount:meshes.length,
        nodesWithMesh:rows.filter(n=>n.mesh!==null).length,
        nodesWithNoParent:parents.filter(p=>p===null).length,
        diagnosticNote:'World transforms are approximate and ignore quaternion rotation when propagating bounds. This is diagnostic only; no model changes are made.',
        nodes:rows
      },null,2));
      if (!nodes.length || !meshes.length) fail('GLB has no nodes or meshes');
    }
  }
}
