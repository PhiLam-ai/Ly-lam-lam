#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const sourceArg = process.argv[2];
if (!sourceArg) {
  console.error('Cách dùng: node tools/vendor-three.cjs /đường/dẫn/tới/node_modules/three');
  console.error('Nguồn phải là gói Three.js chính thức phiên bản 0.160.0 đã cài sẵn.');
  process.exit(2);
}
const source = path.resolve(sourceArg);
const destination = path.join(root, 'vendor', 'three');
const pkgPath = path.join(source, 'package.json');
if (!fs.existsSync(pkgPath)) {
  console.error(`FAIL: Không tìm thấy package.json tại ${source}`);
  process.exit(1);
}
let pkg;
try { pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8')); }
catch (error) { console.error(`FAIL: package.json không hợp lệ: ${error.message}`); process.exit(1); }
if (pkg.name !== 'three' || pkg.version !== '0.160.0') {
  console.error(`FAIL: cần gói three@0.160.0; nhận được ${pkg.name || '(không tên)'}@${pkg.version || '(không phiên bản)'}`);
  process.exit(1);
}
const required = ['build/three.module.js', 'examples/jsm/loaders/GLTFLoader.js', 'examples/jsm/controls/OrbitControls.js', 'LICENSE'];
for (const relative of required) {
  if (!fs.existsSync(path.join(source, relative)) || !fs.statSync(path.join(source, relative)).isFile()) {
    console.error(`FAIL: gói nguồn thiếu ${relative}`);
    process.exit(1);
  }
}
// Copy into a temporary sibling first so a failed copy cannot leave a half-staged package.
const temp = path.join(root, 'vendor', `.three-staging-${process.pid}`);
try {
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.rmSync(temp, { recursive: true, force: true });
  fs.mkdirSync(temp, { recursive: true });
  for (const relative of ['build', 'examples/jsm', 'LICENSE', 'package.json']) {
    const from = path.join(source, relative), to = path.join(temp, relative);
    if (fs.statSync(from).isDirectory()) fs.cpSync(from, to, { recursive: true });
    else fs.copyFileSync(from, to);
  }
  // Keep the previous vendor package recoverable if replacing it fails.
  const backup = path.join(root, 'vendor', `.three-backup-${process.pid}`);
  fs.rmSync(backup, { recursive: true, force: true });
  const hadDestination = fs.existsSync(destination);
  if (hadDestination) fs.renameSync(destination, backup);
  try {
    fs.renameSync(temp, destination);
    // Validate the complete relative-import graph before discarding the previous package.
    const integrity = require('node:child_process').spawnSync(process.execPath, [path.join(__dirname, 'vendor-module-integrity.cjs')], {
      cwd: root, encoding: 'utf8', windowsHide: true
    });
    if (integrity.error) throw new Error(`không chạy được kiểm tra import: ${integrity.error.message}`);
    if (integrity.status !== 0) {
      const details = [integrity.stdout, integrity.stderr].filter(Boolean).join('\n').trim();
      throw new Error(`gói Three.js sau khi staging không vượt qua kiểm tra import${details ? `:\n${details}` : ''}`);
    }
    if (integrity.stdout) process.stdout.write(integrity.stdout);
  } catch (replaceError) {
    // Roll back even when graph validation fails, not just when rename itself fails.
    fs.rmSync(destination, { recursive: true, force: true });
    if (hadDestination && fs.existsSync(backup)) fs.renameSync(backup, destination);
    throw replaceError;
  }
  fs.rmSync(backup, { recursive: true, force: true });
  console.log(`PASS: Three.js ${pkg.version} đã được sao chép vào vendor/three.`);
  console.log('Mở ứng dụng bằng URL có ?three=local để dùng thư viện tự lưu trữ.');
  console.log('Lưu ý: cần triển khai cả thư mục vendor/three; chạy kiểm tra tệp và thử render sau khi triển khai.');
} catch (error) {
  fs.rmSync(temp, { recursive: true, force: true });
  console.error(`FAIL: Không thể chuẩn bị thư viện: ${error.message}`);
  process.exit(1);
}
