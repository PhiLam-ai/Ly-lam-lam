'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const viewerRoot = process.env.V352_VIEWER_ROOT ? path.resolve(process.env.V352_VIEWER_ROOT) : '';
const reportPath = process.env.V352_PATCH_REPORT_PATH || path.resolve('artifacts/v352-browser-lighting/viewer-lighting-patch-report.json');
if (!viewerRoot) throw new Error('V352_VIEWER_ROOT is required.');
const htmlPath = path.join(viewerRoot, 'index.html');
if (!fs.existsSync(htmlPath)) throw new Error('Missing temporary viewer HTML: ' + htmlPath);

const originalLighting = 'scene.add(new THREE.HemisphereLight(0xdce8ff,0x252c3a,2.0)); const key=new THREE.DirectionalLight(0xffe5cf,2.2); key.position.set(2,4,3);scene.add(key);';
const candidateLighting = 'scene.add(new THREE.HemisphereLight(0xfff0e2,0x252c3a,2.2)); const key=new THREE.DirectionalLight(0xffe5cf,1.8); key.position.set(2,4,3);scene.add(key); const fill=new THREE.DirectionalLight(0xe0e9ff,0.8);fill.position.set(-3,2.6,4);scene.add(fill); const faceFill=new THREE.DirectionalLight(0xfff4e8,0.45);faceFill.position.set(0,2.2,4.5);scene.add(faceFill);';

const source = fs.readFileSync(htmlPath, 'utf8');
const occurrences = source.split(originalLighting).length - 1;
if (occurrences !== 1) throw new Error('Expected exactly one original lighting block; found ' + occurrences);
if (source.includes('const faceFill=new THREE.DirectionalLight(0xfff4e8,0.45)')) {
  throw new Error('V352 lighting patch appears to have already been applied.');
}

const beforeSha256 = crypto.createHash('sha256').update(source).digest('hex');
const updated = source.replace(originalLighting, candidateLighting);
const afterSha256 = crypto.createHash('sha256').update(updated).digest('hex');
fs.writeFileSync(htmlPath, updated, 'utf8');

const report = {
  status: 'V352_TEMP_VIEWER_LIGHTING_PATCH_APPLIED',
  scope: 'Temporary copy of v312-work/index.html only; source repository HTML and production main branch are not modified.',
  originalHtmlSha256: beforeSha256,
  patchedHtmlSha256: afterSha256,
  replacementCount: occurrences,
  baseline: {
    hemisphereColor: '0xdce8ff',
    hemisphereIntensity: 2.0,
    keyColor: '0xffe5cf',
    keyIntensity: 2.2,
    keyPosition: [2, 4, 3]
  },
  candidate: {
    hemisphereColor: '0xfff0e2',
    hemisphereIntensity: 2.2,
    keyColor: '0xffe5cf',
    keyIntensity: 1.8,
    keyPosition: [2, 4, 3],
    sideFill: { color: '0xe0e9ff', intensity: 0.8, position: [-3, 2.6, 4] },
    frontFill: { color: '0xfff4e8', intensity: 0.45, position: [0, 2.2, 4.5] }
  },
  modelUnchanged: true,
  intent: 'Lift frontal facial shadow detail by reducing the key slightly and adding low-intensity side/front fill lights. Keep V350 GLB, geometry, materials and camera behavior unchanged.'
};

fs.mkdirSync(path.dirname(reportPath), { recursive: true });
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n', 'utf8');
console.log('V352_VIEWER_PATCH_REPORT=' + JSON.stringify(report));
