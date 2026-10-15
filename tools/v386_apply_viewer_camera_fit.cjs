'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const viewerRoot = process.env.V386_VIEWER_ROOT ? path.resolve(process.env.V386_VIEWER_ROOT) : '';
const reportPath = process.env.V386_CAMERA_FIT_REPORT_PATH || path.resolve('artifacts/v386-browser-test/viewer-camera-fit-report.json');
if (!viewerRoot) throw new Error('V386_VIEWER_ROOT is required.');
const htmlPath = path.join(viewerRoot, 'index.html');
if (!fs.existsSync(htmlPath)) throw new Error('Missing temporary viewer HTML: ' + htmlPath);

// Keep the browser smoke-test bounds gate unchanged. Add a little camera-distance
// margin because the narrower, more natural arm pose makes horizontal fit less
// restrictive and the old width-first fit makes the figure too tall on an iPhone.
const beforeToken = 'cameraDistance=Math.max(fitVertical,fitHorizontal,1.0)*1.20;';
const afterToken = 'cameraDistance=Math.max(fitVertical,fitHorizontal,1.0)*1.35;';
const source = fs.readFileSync(htmlPath, 'utf8');
const occurrences = source.split(beforeToken).length - 1;
if (occurrences !== 1) throw new Error('Expected exactly one candidate camera-fit formula; found ' + occurrences);
if (source.includes(afterToken)) throw new Error('V386 camera-fit patch already appears to be applied.');

const beforeSha256 = crypto.createHash('sha256').update(source).digest('hex');
const updated = source.replace(beforeToken, afterToken);
const afterSha256 = crypto.createHash('sha256').update(updated).digest('hex');
fs.writeFileSync(htmlPath, updated, 'utf8');
const report = {
  status: 'V386_TEMP_VIEWER_CAMERA_FIT_PATCH_APPLIED',
  scope: 'Temporary preview copy of v312-work/index.html only; repository source and production main branch are unchanged.',
  originalHtmlSha256: beforeSha256,
  patchedHtmlSha256: afterSha256,
  replacementCount: occurrences,
  cameraDistanceFormulaBefore: beforeToken,
  cameraDistanceFormulaAfter: afterToken,
  distanceScaleIncreaseFraction: 0.125,
  modelGlbUnchanged: true,
  intent: 'Keep the narrowed-arm candidate within the mobile projected-bounds gate with enough extra vertical margin; do not relax the smoke-test threshold.'
};
fs.mkdirSync(path.dirname(reportPath), { recursive: true });
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n', 'utf8');
console.log('V386_VIEWER_CAMERA_FIT_PATCH=' + JSON.stringify(report));
