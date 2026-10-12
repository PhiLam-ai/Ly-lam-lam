#!/usr/bin/env node
'use strict';
// Check relative module edges in the staged Three.js files before deployment.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(process.argv[2] || path.join(__dirname, '..'));
const vendor = path.join(root, 'vendor', 'three');
const entrypoints = ['build/three.module.js', 'examples/jsm/loaders/GLTFLoader.js', 'examples/jsm/controls/OrbitControls.js'];
const errors = [];
const visited = new Set();
function fail(message) { console.error(`FAIL: ${message}`); process.exit(1); }
function scanTree(dir) {
  if (!fs.existsSync(dir)) return;
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, item.name);
    if (item.isDirectory()) scanTree(file);
    else if (item.isFile() && /\.m?js$/.test(item.name)) visited.add(file);
  }
}
for (const relative of entrypoints) {
  const file = path.join(vendor, relative);
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) fail(`thiếu điểm vào vendor/three/${relative}`);
}
scanTree(path.join(vendor, 'build'));
scanTree(path.join(vendor, 'examples', 'jsm'));
let edgeCount = 0;
for (const file of visited) {
  const source = fs.readFileSync(file, 'utf8');
  // Static import/export declarations and literal dynamic imports, including multiline forms.
  // Match actual ES module declarations, not words inside template literals.
  const patterns = [
    /\b(?:import|export)\s+(?:[\s\S]*?\s+from\s*)?["']([^"']+)["']/g,
    /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g
  ];
  for (const pattern of patterns) for (const match of source.matchAll(pattern)) {
    const specifier = match[1];
    // Three.js example modules intentionally resolve the bare specifier `three`
    // through the application's import map. Reject any other bare package import
    // because this static deployment does not install a node_modules tree.
    if (!specifier.startsWith('./') && !specifier.startsWith('../')) {
      if (specifier === 'three') continue;
      if (/^(?:[a-zA-Z0-9@][^:]*)$/.test(specifier)) {
        errors.push(`${path.relative(root, file)}: import de package không được ánh xạ trong triển khai tĩnh: ${specifier}`);
      }
      continue;
    }
    const target = path.resolve(path.dirname(file), specifier);
    if (!target.startsWith(vendor + path.sep)) errors.push(`${path.relative(root, file)}: đường dẫn import thoát khỏi vendor/three: ${specifier}`);
    else if (!fs.existsSync(target) || !fs.statSync(target).isFile()) errors.push(`${path.relative(root, file)}: thiếu module ${specifier}`);
    edgeCount++;
  }
}
if (errors.length) {
  for (const error of errors) console.error(`FAIL: ${error}`);
  process.exit(1);
}
console.log(`PASS: ${visited.size} mô-đun Three.js đã quét, ${edgeCount} cạnh import tương đối hợp lệ.`);
console.log('Đã kiểm tra import bare: chỉ cho phép package specifier "three" được import map ánh xạ.');
console.log('Giới hạn: không xác minh mạng CDN, WebGL hoặc render trong trình duyệt.');
