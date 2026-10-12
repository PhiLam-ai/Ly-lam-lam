#!/usr/bin/env node
'use strict';
// Create a transferable, integrity-pinned npm tarball on a machine with registry access.
// The bundle can then be copied to an offline checkout and consumed by fetch-vendor-three.cjs.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const crypto = require('node:crypto');

const VERSION = '0.160.0';
const SPEC = `three@${VERSION}`;
const args = process.argv.slice(2);
let outputDir = path.resolve('three-offline-bundle');
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--out') {
    if (!args[i + 1]) throw new Error('--out cần đường dẫn thư mục đích.');
    outputDir = path.resolve(args[++i]);
  } else if (args[i] === '--help' || args[i] === '-h') {
    console.log('Dùng: node tools/export-three-offline-bundle.cjs [--out thư-mục]');
    console.log('Chạy trên máy có Internet; truy vấn integrity từ npm registry rồi tải đúng three@0.160.0.');
    process.exit(0);
  } else throw new Error(`Tham số không được hỗ trợ: ${args[i]}`);
}
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
function run(args) {
  const result = cp.spawnSync(npm, args, { encoding: 'utf8', windowsHide: true, timeout: 120000, stdio: ['ignore', 'pipe', 'pipe'] });
  if (result.error) throw new Error(`Không chạy được npm: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`npm ${args.join(' ')} thất bại (mã ${result.status}):\n${[result.stdout, result.stderr].filter(Boolean).join('\n').trim()}`);
  return result.stdout.trim();
}
function isNetworkFailure(error) {
  return /\b(?:ENOTFOUND|EAI_AGAIN|ETIMEDOUT|ECONNRESET|ECONNREFUSED|EHOSTUNREACH|ENETUNREACH|ECONNABORTED|ERR_SOCKET_TIMEOUT)\b|\bsocket hang up\b|\bgetaddrinfo\b.*(?:ENOTFOUND|EAI_AGAIN)/i.test(error.message);
}
const registries = [
  { name: 'npm chính thức', url: 'https://registry.npmjs.org/' },
  { name: 'mirror npm npmmirror', url: 'https://registry.npmmirror.com/' }
];
function integrityFor(bytes) {
  return `sha512-${crypto.createHash('sha512').update(bytes).digest('base64')}`;
}
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-three-offline-'));
try {
  let expected;
  let metadataText;
  let packText;
  let selectedRegistry;
  let lastNetworkError = null;
  // Query integrity and pack from the same registry so a mirror fallback cannot
  // accidentally combine metadata from one source with bytes from another.
  for (const registry of registries) {
    try {
      console.log(`Đang truy vấn dist.integrity cho ${SPEC} từ ${registry.name}...`);
      metadataText = run(['view', SPEC, 'dist.integrity', '--json', '--registry', registry.url]);
      try { expected = JSON.parse(metadataText); } catch { expected = metadataText.replace(/^['"]|['"]$/g, ''); }
      if (typeof expected !== 'string' || !/^sha512-[A-Za-z0-9+/]+={0,2}$/.test(expected)) {
        throw new Error(`npm trả về dist.integrity không hợp lệ: ${metadataText}`);
      }
      console.log(`Đang tải ${SPEC} thành tarball từ cùng registry...`);
      const expectedFile = path.join(temp, `three-${VERSION}.tgz`);
      fs.rmSync(expectedFile, { force: true });
      packText = run(['pack', SPEC, '--pack-destination', temp, '--ignore-scripts', '--json', '--registry', registry.url]);
      selectedRegistry = registry;
      lastNetworkError = null;
      break;
    } catch (error) {
      if (!isNetworkFailure(error)) throw error;
      lastNetworkError = error;
      console.warn(`Không truy cập được ${registry.name}: ${error.message.split('\n').slice(-1)[0]}`);
    }
  }
  if (lastNetworkError || !selectedRegistry) throw lastNetworkError || new Error('Không tìm được registry để xuất gói.');
  let packInfo;
  try { packInfo = JSON.parse(packText); } catch (error) { throw new Error(`npm pack không trả JSON hợp lệ: ${error.message}`); }
  if (!Array.isArray(packInfo) || packInfo.length !== 1 || packInfo[0].filename !== `three-${VERSION}.tgz`) {
    throw new Error(`npm pack không trả về tarball dự kiến three-${VERSION}.tgz.`);
  }
  const source = path.join(temp, packInfo[0].filename);
  if (!fs.existsSync(source) || !fs.statSync(source).isFile()) throw new Error('Không tìm thấy tarball sau npm pack.');
  const bytes = fs.readFileSync(source);
  const actual = integrityFor(bytes);
  if (actual !== expected) throw new Error(`Integrity tarball không khớp metadata npm. Mong đợi ${expected}; thực tế ${actual}.`);
  if (packInfo[0].integrity && packInfo[0].integrity !== expected) throw new Error(`Integrity do npm pack báo không khớp npm view: ${packInfo[0].integrity}`);
  fs.mkdirSync(outputDir, { recursive: true });
  const tarballPath = path.join(outputDir, `three-${VERSION}.tgz`);
  const manifestPath = path.join(outputDir, 'THREE-OFFLINE-MANIFEST.txt');
  // Re-exporting into an existing bundle directory is intentionally supported: a
  // previous interrupted/older export should not block a newly verified tarball.
  // Bytes are copied only after the current tarball passed registry integrity checks.
  fs.copyFileSync(source, tarballPath);
  const hex = crypto.createHash('sha512').update(bytes).digest('hex');
  const manifest = [
    `Package: ${SPEC}`,
    `Source metadata: npm dist.integrity queried via ${selectedRegistry.url}; tarball packed from the same registry`,
    `SHA-512 SRI: ${expected}`,
    `SHA-512 hex: ${hex}`,
    `Tarball: three-${VERSION}.tgz`,
    'Transfer both files together. On the offline checkout, run:',
    `THREE_TARBALL="/path/to/three-${VERSION}.tgz" THREE_TARBALL_SHA512="${expected}" THREE_TARBALL_REQUIRE_SHA512=1 node tools/fetch-vendor-three.cjs`,
    ''
  ].join('\n');
  fs.writeFileSync(manifestPath, manifest, 'utf8');
  console.log(`PASS: gói ${SPEC} được xác minh với npm dist.integrity từ ${selectedRegistry.name}.`);
  console.log(`Tarball: ${tarballPath}`);
  console.log(`Manifest: ${manifestPath}`);
  console.log('Chuyển cả tarball và manifest sang checkout ngoại tuyến; không sửa nội dung tarball.');
} catch (error) {
  console.error(`FAIL: ${error.message}`);
  process.exitCode = 1;
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
