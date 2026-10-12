#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const { auditGlbBytes } = require('./glb-structural-audit.cjs');
const htmlPath = path.join(root, 'index.html');
const errors = [];
const warnings = [];
if (!fs.existsSync(htmlPath)) {
  console.error('FAIL: thiếu index.html');
  process.exit(1);
}
const html = fs.readFileSync(htmlPath, 'utf8');
const localSpecifiers = new Set();
const sourceFiles = [htmlPath];
for (const name of fs.readdirSync(root)) {
  if (/\.(?:js|mjs|cjs)$/.test(name)) sourceFiles.push(path.join(root, name));
}
for (const sourcePath of sourceFiles) {
  const source = fs.readFileSync(sourcePath, 'utf8');
  for (const match of source.matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"](\.\/[^'"]+)['"]/g)) {
    const specifier = match[1];
    const target = path.resolve(path.dirname(sourcePath), specifier);
    if (!target.startsWith(root + path.sep) || !fs.existsSync(target) || !fs.statSync(target).isFile()) errors.push(`Thiếu tài nguyên module trong ${path.relative(root, sourcePath)}: ${specifier}`);
    localSpecifiers.add(`${path.relative(root, sourcePath)} -> ${specifier}`);
  }
}
const requiredFiles = ['lam-default.glb', 'expression-baseline-cases-v1.json'];
for (const relative of requiredFiles) {
  const target = path.join(root, relative);
  if (!fs.existsSync(target) || !fs.statSync(target).isFile()) errors.push(`Thiếu tài nguyên cốt lõi: ${relative}`);
}
const glbPath = path.join(root, 'lam-default.glb');
if (fs.existsSync(glbPath)) {
  const audit = auditGlbBytes(fs.readFileSync(glbPath));
  if (!audit.ok) errors.push(...audit.errors.map(message => `lam-default.glb: ${message}`));
  else console.log(`PASS: GLB audit cấu trúc sâu (${audit.summary.bytes} byte; ${audit.summary.nodes} nodes; ${audit.summary.meshes} meshes; ${audit.summary.accessors} accessors; ${audit.summary.bufferViews} bufferViews).`);
}
const importMapMatch = html.match(/<script\s+type="importmap">([\s\S]*?)<\/script>/i);
if (/document\.write\('<script type="importmap">'\+JSON\.stringify\(\{imports\}\)/.test(html) && /get\('three'\)/.test(html) && /three@0\.160\.0/.test(html)) {
  if (!html.includes("'./vendor/three/'") || !html.includes("'https://cdn.jsdelivr.net/npm/three@0.160.0/'") || !html.includes("'https://unpkg.com/three@0.160.0/'")) errors.push('Bộ chọn import map không có đủ chế độ local và hai CDN đã ghim phiên bản.');
  if (html.includes("get('three')==='local'") && !html.includes('mode===null')) warnings.push('Three.js vẫn phụ thuộc CDN bên ngoài theo mặc định; ?three=local dùng thư viện tự lưu trữ nếu đã stage vào vendor/three.');
  else warnings.push('Bản triển khai mặc định dùng Three.js tự lưu trữ; ?three=cdn chọn lại CDN.');
  const vendorRoot = path.join(root, 'vendor', 'three');
  const vendorRequired = ['build/three.module.js', 'examples/jsm/loaders/GLTFLoader.js', 'examples/jsm/controls/OrbitControls.js', 'LICENSE', 'package.json'];
  const vendorPresent = vendorRequired.map(relative => fs.existsSync(path.join(vendorRoot, relative)) && fs.statSync(path.join(vendorRoot, relative)).isFile());
  if (vendorPresent.every(Boolean)) {
    try {
      const vendorPackage = JSON.parse(fs.readFileSync(path.join(vendorRoot, 'package.json'), 'utf8'));
      if (vendorPackage.name !== 'three' || vendorPackage.version !== '0.160.0') errors.push('vendor/three có package.json không khớp three@0.160.0.');
      else console.log('PASS: vendor/three có đủ tệp bắt buộc và đúng phiên bản three@0.160.0.');
    } catch (error) { errors.push(`vendor/three/package.json không hợp lệ: ${error.message}`); }
  } else if (vendorPresent.some(Boolean)) {
    errors.push(`vendor/three đã tồn tại nhưng thiếu tệp bắt buộc: ${vendorRequired.filter((_, i) => !vendorPresent[i]).join(', ')}`);
  } else {
    warnings.push('Chưa có vendor/three; chế độ ?three=local sẽ không khởi chạy cho đến khi chạy tools/vendor-three.cjs với gói chính thức three@0.160.0.');
  }
} else if (importMapMatch) {
  try {
    const map = JSON.parse(importMapMatch[1]);
    if (!map.imports?.three || !map.imports?.['three/addons/']) errors.push('Import map thiếu ánh xạ three hoặc three/addons/');
    if ([map.imports?.three, map.imports?.['three/addons/']].some(value => typeof value === 'string' && /^https:\/\/cdn\.jsdelivr\.net\//.test(value))) warnings.push('Three.js vẫn phụ thuộc CDN bên ngoài; preflight không kiểm tra được khả năng truy cập mạng.');
  } catch (error) { errors.push(`Import map JSON không hợp lệ: ${error.message}`); }
} else errors.push('Không tìm thấy import map tĩnh hoặc bộ chọn import map CDN/local hợp lệ.');
if (errors.length) {
  for (const item of errors) console.error(`FAIL: ${item}`);
  for (const item of warnings) console.warn(`WARN: ${item}`);
  process.exit(1);
}
console.log(`PASS: ${sourceFiles.length} tệp nguồn, ${localSpecifiers.size} tham chiếu module cục bộ, GLB 2.0 đã audit cấu trúc và JSON ca thử đều có mặt.`);
for (const item of warnings) console.warn(`WARN: ${item}`);
console.log('Giới hạn: đây là kiểm tra tệp tĩnh; không xác minh CDN, WebGL, render, host HTTPS hoặc Safari/iPhone.');
