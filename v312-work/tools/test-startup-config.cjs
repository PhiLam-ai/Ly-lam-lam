#!/usr/bin/env node
'use strict';

// Static startup checks for v312-work. Does not replace a real browser/WebGL test.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const htmlPath = path.join(root, 'index.html');
let failures = 0;
let passes = 0;
const warnings = [];

function check(label, condition, detail = '') {
  if (condition) {
    passes++;
    console.log('PASS:', label);
  } else {
    failures++;
    console.error('FAIL:', label, detail);
  }
}

function read(relative) {
  const file = path.join(root, relative);
  if (!fs.existsSync(file)) return null;
  return fs.readFileSync(file, 'utf8');
}

const html = fs.existsSync(htmlPath) ? fs.readFileSync(htmlPath, 'utf8') : null;
check('v312-work/index.html exists', Boolean(html));
if (html) {
  check('CDN is the default unless three=local is explicitly selected',
    html.includes("const local=mode==='local';") &&
    html.includes("https://cdn.jsdelivr.net/npm/three@0.160.0/"),
    'Import map should not default to ./vendor/three/.');
  check('unpkg fallback is configured',
    html.includes("https://unpkg.com/three@0.160.0/"));
  check('GLB loader points to the expected model',
    html.includes("targetUrl='./lam-default.glb'") &&
    html.includes('loader.load(targetUrl'));
  check('renderer success flag is set in startup code',
    html.includes('window.__lyLamRendererReady=true'));
  check('model success flag exists',
    html.includes('window.__lyLamAppBooted=true'));
  check('startup failure diagnostics exist',
    html.includes('window.__lyLamBootFailed') &&
    html.includes("addEventListener('unhandledrejection'"));
  const imports = [...html.matchAll(/import\s+['"]\.\/([^'"]+)['"]/g)].map(m => m[1]);
  for (const relative of imports) {
    check(`local module exists: ${relative}`, fs.existsSync(path.join(root, relative)));
  }
  const vendor = path.join(root, 'vendor/three/build/three.module.js');
  if (fs.existsSync(vendor) && fs.statSync(vendor).size === 0) {
    warnings.push('The optional local Three.js module is zero bytes; do not use ?three=local until vendored correctly.');
  }
}
const glbPath = path.join(root, 'lam-default.glb');
check('lam-default.glb exists', fs.existsSync(glbPath));
if (fs.existsSync(glbPath)) {
  const b = fs.readFileSync(glbPath);
  check('GLB header is valid glTF 2.0',
    b.length >= 20 && b.readUInt32LE(0) === 0x46546c67 &&
    b.readUInt32LE(4) === 2 && b.readUInt32LE(8) === b.length);
}
for (const warning of warnings) console.warn('WARN:', warning);
console.log(JSON.stringify({passes, failures, warnings, browserRenderTested: false}, null, 2));
if (failures) process.exitCode = 1;
