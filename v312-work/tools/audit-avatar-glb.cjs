#!/usr/bin/env node
'use strict';

// Dependency-free structural audit for the Lý Lâm Lam GLB.
// Usage: node tools/audit-avatar-glb.cjs [path-to-glb]
const fs = require('node:fs');
const path = require('node:path');

const file = path.resolve(process.argv[2] || path.join(__dirname, '..', 'lam-default.glb'));
const requiredMorphs = [
  'smile', 'blink_left', 'blink_right', 'mouth_open', 'brow_raise',
  'jaw_open', 'jaw_hinge', 'cheek_raise', 'lip_press', 'lip_fv',
  'lip_round', 'tongue_tip'
];

function fail(message) {
  console.error('FAIL:', message);
  process.exitCode = 1;
}

if (!fs.existsSync(file)) {
  fail(`GLB not found: ${file}`);
} else {
  const bytes = fs.readFileSync(file);
  if (bytes.length < 20) {
    fail(`File is too small to be a valid GLB (${bytes.length} bytes)`);
  } else {
    const magic = bytes.readUInt32LE(0);
    const version = bytes.readUInt32LE(4);
    const declaredLength = bytes.readUInt32LE(8);
    const jsonLength = bytes.readUInt32LE(12);
    if (magic !== 0x46546c67) fail('Invalid GLB magic; expected glTF');
    if (version !== 2) fail(`Expected GLB version 2, got ${version}`);
    if (declaredLength !== bytes.length) fail(`Length mismatch: header=${declaredLength}, actual=${bytes.length}`);
    if (20 + jsonLength > bytes.length) fail('JSON chunk extends beyond end of file');

    if (process.exitCode !== 1) {
      let gltf;
      try {
        gltf = JSON.parse(bytes.subarray(20, 20 + jsonLength).toString('utf8').trim());
      } catch (error) {
        fail(`Could not parse GLB JSON chunk: ${error.message}`);
      }

      if (gltf) {
        const nodes = gltf.nodes || [];
        const meshes = gltf.meshes || [];
        const materials = gltf.materials || [];
        const skins = gltf.skins || [];
        const morphNames = new Set();
        let primitiveCount = 0;
        let morphPrimitiveCount = 0;
        for (const mesh of meshes) {
          for (const name of mesh.extras?.targetNames || []) morphNames.add(name);
          for (const primitive of mesh.primitives || []) {
            primitiveCount++;
            if ((primitive.targets || []).length) morphPrimitiveCount++;
          }
        }
        const missingMorphs = requiredMorphs.filter(name => !morphNames.has(name));
        const report = {
          file: path.basename(file),
          bytes: bytes.length,
          validGlbHeader: magic === 0x46546c67 && version === 2 && declaredLength === bytes.length,
          gltfVersion: gltf.asset?.version || null,
          generator: gltf.asset?.generator || null,
          scenes: (gltf.scenes || []).length,
          nodes: nodes.length,
          meshes: meshes.length,
          primitives: primitiveCount,
          materials: materials.map(material => material.name || '(unnamed)'),
          skins: skins.map(skin => ({ name: skin.name || '(unnamed)', joints: (skin.joints || []).length })),
          morphNames: [...morphNames].sort(),
          morphPrimitiveCount,
          missingRequiredMorphs: missingMorphs,
          note: meshes.length > 40
            ? 'High mesh count: inspect the rendered silhouette for visible seams between body parts.'
            : 'Review rendered silhouette and deformation quality in the viewer.'
        };
        console.log(JSON.stringify(report, null, 2));
        if (missingMorphs.length) fail(`Missing expected morph targets: ${missingMorphs.join(', ')}`);
        if (!nodes.length || !meshes.length) fail('No nodes or meshes found in GLB');
      }
    }
  }
}
