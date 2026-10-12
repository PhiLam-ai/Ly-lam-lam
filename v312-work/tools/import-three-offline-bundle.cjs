#!/usr/bin/env node
'use strict';
// Validate the exported transfer bundle and stage the exact tarball without shell-specific env syntax.
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const crypto = require('node:crypto');

const VERSION = '0.160.0';
const EXPECTED_PACKAGE = `three@${VERSION}`;
const args = process.argv.slice(2);
let bundleDir = path.resolve('three-offline-bundle');
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--bundle-dir') {
    if (!args[i + 1]) { console.error('FAIL: thiếu đường dẫn sau --bundle-dir.'); process.exit(2); }
    bundleDir = path.resolve(args[++i]);
  } else if (args[i] === '--help' || args[i] === '-h') {
    console.log('Dùng: node tools/import-three-offline-bundle.cjs [--bundle-dir thư-mục-gói]');
    console.log('Kiểm tra manifest + SHA-512 tarball rồi gọi công cụ staging Three.js đã có.');
    process.exit(0);
  } else { console.error(`FAIL: tham số không được hỗ trợ: ${args[i]}`); process.exit(2); }
}
function fail(message) { console.error(`FAIL: ${message}`); process.exit(1); }
const manifestPath = path.join(bundleDir, 'THREE-OFFLINE-MANIFEST.txt');
const tarballPath = path.join(bundleDir, `three-${VERSION}.tgz`);
if (!fs.existsSync(manifestPath) || !fs.statSync(manifestPath).isFile()) fail(`không tìm thấy manifest: ${manifestPath}`);
if (!fs.existsSync(tarballPath) || !fs.statSync(tarballPath).isFile()) fail(`không tìm thấy tarball: ${tarballPath}`);
const manifest = fs.readFileSync(manifestPath, 'utf8');
function field(label) {
  const matches = [...manifest.matchAll(new RegExp(`^${label}:\\s*(.+?)\\s*$`, 'gm'))];
  if (matches.length !== 1) fail(`manifest phải có đúng một trường "${label}".`);
  return matches[0][1];
}
const packageName = field('Package');
const sri = field('SHA-512 SRI');
const hex = field('SHA-512 hex');
const tarballName = field('Tarball');
if (packageName !== EXPECTED_PACKAGE) fail(`manifest phải ghim ${EXPECTED_PACKAGE}, nhận ${packageName}.`);
if (tarballName !== `three-${VERSION}.tgz`) fail(`tên tarball trong manifest không đúng: ${tarballName}`);
if (!/^sha512-[A-Za-z0-9+/]{86}==$/.test(sri)) fail('trường SHA-512 SRI không hợp lệ.');
if (!/^[a-f0-9]{128}$/i.test(hex)) fail('trường SHA-512 hex không hợp lệ.');
const bytes = fs.readFileSync(tarballPath);
const actualHex = crypto.createHash('sha512').update(bytes).digest('hex');
const actualSri = `sha512-${Buffer.from(actualHex, 'hex').toString('base64')}`;
if (actualHex.toLowerCase() !== hex.toLowerCase() || actualSri !== sri) {
  fail(`SHA-512 tarball không khớp manifest; thực tế ${actualHex}. Không giải nén gói.`);
}
console.log(`PASS: tarball ${EXPECTED_PACKAGE} khớp cả SHA-512 SRI và hex trong manifest.`);
const root = path.resolve(__dirname, '..');
const fetcher = path.join(__dirname, 'fetch-vendor-three.cjs');
const result = cp.spawnSync(process.execPath, [fetcher], {
  cwd: root,
  encoding: 'utf8',
  windowsHide: true,
  stdio: ['ignore', 'pipe', 'pipe'],
  env: {
    ...process.env,
    THREE_TARBALL: tarballPath,
    THREE_TARBALL_SHA512: sri,
    THREE_TARBALL_REQUIRE_SHA512: '1'
  },
  timeout: 120000
});
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
if (result.error) fail(`không chạy được công cụ staging: ${result.error.message}`);
if (result.status !== 0) fail(`công cụ staging Three.js thất bại (mã ${result.status}).`);
console.log('PASS: gói ngoại tuyến đã được xác minh và staging thành công.');
