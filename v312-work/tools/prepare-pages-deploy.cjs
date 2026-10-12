#!/usr/bin/env node
'use strict';
// Prepare a GitHub Pages checkout to default to its staged, pinned local Three.js.
// This mutates only the checked-out deployment copy; source packages retain CDN default.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(process.argv[2] || path.join(__dirname, '..'));
const htmlPath = path.join(root, 'index.html');
const vendorRoot = path.join(root, 'vendor', 'three');
const required = ['build/three.module.js', 'examples/jsm/loaders/GLTFLoader.js', 'examples/jsm/controls/OrbitControls.js', 'LICENSE', 'package.json'];
function fail(message) { console.error(`FAIL: ${message}`); process.exit(1); }
if (!fs.existsSync(htmlPath)) fail('thiếu index.html trong thư mục triển khai');
for (const file of required) if (!fs.existsSync(path.join(vendorRoot, file)) || !fs.statSync(path.join(vendorRoot, file)).isFile()) fail(`thiếu vendor/three/${file}; hãy chạy tools/fetch-vendor-three.cjs trước`);
let pkg;
try { pkg = JSON.parse(fs.readFileSync(path.join(vendorRoot, 'package.json'), 'utf8')); }
catch (error) { fail(`package.json của vendor/three không hợp lệ: ${error.message}`); }
if (pkg.name !== 'three' || pkg.version !== '0.160.0') fail(`cần vendor three@0.160.0, nhận ${pkg.name || '(không tên)'}@${pkg.version || '(không phiên bản)'}`);
// Validate the complete relative-import graph before changing deployment HTML.
const integrity = require('node:child_process').spawnSync(process.execPath, [path.join(__dirname, 'vendor-module-integrity.cjs'), root], {
  cwd: root, encoding: 'utf8', windowsHide: true
});
if (integrity.error) fail(`không chạy được kiểm tra import: ${integrity.error.message}`);
if (integrity.status !== 0) {
  const details = [integrity.stdout, integrity.stderr].filter(Boolean).join('\n').trim();
  fail(`vendor/three không vượt qua kiểm tra import${details ? `:\n${details}` : ''}`);
}
if (integrity.stdout) process.stdout.write(integrity.stdout);
const originalHtml = fs.readFileSync(htmlPath, 'utf8');
const sourceSelector = "get('three')==='local'";
const deploySelector = "get('three')!=='cdn' && new URLSearchParams(location.search).get('three')!=='unpkg'";
let html = originalHtml;
let changed = false;
if (html.includes(sourceSelector)) {
  html = html.replace(sourceSelector, deploySelector);
  changed = true;
} else if (!html.includes(deploySelector)) {
  fail('không nhận diện được bộ chọn import map CDN/local; từ chối sửa index.html');
}
// Validate the candidate completely before touching the deployment HTML.
if (!html.includes("'./vendor/three/'") || !html.includes("'https://cdn.jsdelivr.net/npm/three@0.160.0/'") || !html.includes("'https://unpkg.com/three@0.160.0/'")) {
  fail('import map sau chuẩn bị thiếu đường dẫn local hoặc CDN; index.html được giữ nguyên');
}
if (changed) {
  // Write beside index.html and rename atomically so an interrupted write cannot leave a partial file.
  const stagedHtml = path.join(path.dirname(htmlPath), `.index.html-pages-${process.pid}.tmp`);
  try {
    fs.writeFileSync(stagedHtml, html, { flag: 'wx' });
    fs.renameSync(stagedHtml, htmlPath);
  } catch (error) {
    try { fs.rmSync(stagedHtml, { force: true }); } catch {}
    fail(`không thể thay thế index.html an toàn: ${error.message}; bản gốc được giữ nguyên nếu chưa xảy ra rename`);
  }
  console.log('PASS: GitHub Pages mặc định dùng vendor/three; ?three=cdn hoặc ?three=unpkg chọn CDN.');
} else {
  console.log('PASS: index.html đã được chuẩn bị để mặc định dùng vendor/three.');
}
