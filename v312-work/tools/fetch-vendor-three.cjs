#!/usr/bin/env node
'use strict';
// Downloads the exact official npm release into a temporary directory, then stages it
// through the same validation/replacement path as tools/vendor-three.cjs.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-three-0.160.0-'));
function run(command, args) {
  const result = cp.spawnSync(command, args, { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, timeout: 60000 });
  if (result.error) throw new Error(`${command}: ${result.error.message}`);
  if (result.status !== 0) {
    const details = [result.stdout, result.stderr].filter(Boolean).join('\n').trim();
    throw new Error(`${command} kết thúc với mã ${result.status}${details ? `:\n${details}` : ''}`);
  }
  return result.stdout || '';
}
try {
  const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  const installArgs = ['install', '--prefix', temp, '--no-save', '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false', '--fetch-retries=2', '--fetch-retry-mintimeout=1000', '--fetch-retry-maxtimeout=5000', '--fetch-timeout=15000'];
  // A separately downloaded official npm tarball enables deterministic staging on an offline machine.
  // The downstream vendor tool still validates package name/version and the complete relative-import graph.
  if (process.env.THREE_TARBALL) {
    const tarball = path.resolve(process.env.THREE_TARBALL);
    if (!fs.existsSync(tarball) || !fs.statSync(tarball).isFile()) throw new Error(`THREE_TARBALL không phải tệp tồn tại: ${tarball}`);
    // Optional integrity pin: accepts a 128-character SHA-512 hex digest or npm-style sha512-BASE64.
    // This lets an offline operator verify the exact archive before npm extracts it.
    const expected = (process.env.THREE_TARBALL_SHA512 || '').trim();
    const requirePin = /^(?:1|true|yes)$/i.test((process.env.THREE_TARBALL_REQUIRE_SHA512 || '').trim());
    if (requirePin && !expected) {
      throw new Error('THREE_TARBALL_REQUIRE_SHA512 đang bật nhưng chưa cung cấp THREE_TARBALL_SHA512; từ chối gói chưa được ghim mã kiểm tra.');
    }
    if (expected) {
      const actualHex = crypto.createHash('sha512').update(fs.readFileSync(tarball)).digest('hex');
      const actualSri = `sha512-${Buffer.from(actualHex, 'hex').toString('base64')}`;
      const valid = /^[a-f0-9]{128}$/i.test(expected)
        ? actualHex.toLowerCase() === expected.toLowerCase()
        : actualSri === expected;
      if (!valid) throw new Error(`SHA-512 của THREE_TARBALL không khớp; tệp bị từ chối trước khi giải nén. Thực tế: ${actualHex}`);
      console.log('PASS: SHA-512 tarball khớp giá trị THREE_TARBALL_SHA512.');
    } else {
      console.warn('WARN: không cấu hình THREE_TARBALL_SHA512; tarball chỉ được xác minh tên/phiên bản sau khi giải nén.');
    }
    console.log(`Đang cài gói Three.js từ tarball cục bộ: ${tarball}`);
    run(npm, [...installArgs, tarball]);
  } else {
    // Prefer an already cached official package so deployments can succeed during a registry outage.
    // An offline cache miss is expected; retry online and classify only that final failure.
    console.log('Đang thử lấy three@0.160.0 từ bộ nhớ đệm npm ngoại tuyến...');
    const offline = cp.spawnSync(npm, [...installArgs.slice(0, 1), '--offline', ...installArgs.slice(1), 'three@0.160.0'], { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, timeout: 5000 });
    if (!offline.error && offline.status === 0) {
      console.log('PASS: npm cache có sẵn three@0.160.0; không cần truy cập registry.');
    } else {
      const offlineDetails = [offline.stdout, offline.stderr].filter(Boolean).join('\n').trim();
      console.log(`Không dùng được cache ngoại tuyến${offlineDetails ? `: ${offlineDetails.split('\n').slice(-2).join(' ')}` : ''}`);
      const registries = [
        { name: 'npm chính thức', url: 'https://registry.npmjs.org/' },
        { name: 'mirror npm npmmirror', url: 'https://registry.npmmirror.com/' }
      ];
      let lastNetworkError = null;
      for (const registry of registries) {
        console.log(`Đang thử lấy three@0.160.0 từ ${registry.name} (${registry.url})...`);
        try {
          run(npm, [...installArgs, '--registry', registry.url, 'three@0.160.0']);
          lastNetworkError = null;
          break;
        } catch (error) {
          const networkFailure = /\b(?:ENOTFOUND|EAI_AGAIN|ETIMEDOUT|ECONNRESET|ECONNREFUSED|EHOSTUNREACH|ENETUNREACH|ECONNABORTED|ERR_SOCKET_TIMEOUT)\b|\bsocket hang up\b|\bgetaddrinfo\b.*(?:ENOTFOUND|EAI_AGAIN)/i.test(error.message);
          if (!networkFailure) throw error;
          lastNetworkError = error;
          console.warn(`Không truy cập được ${registry.name}: ${error.message.split('\n').slice(-1)[0]}`);
        }
      }
      if (lastNetworkError) throw lastNetworkError;
    }
  }
  const source = path.join(temp, 'node_modules', 'three');
  if (!fs.existsSync(path.join(source, 'package.json'))) throw new Error('npm không tạo ra node_modules/three/package.json.');
  run(process.execPath, [path.join(root, 'tools', 'vendor-three.cjs'), source]);
  console.log('Hoàn tất. Hãy chạy node tools/startup-preflight.cjs và node tools/static-http-smoke.cjs, rồi triển khai cả vendor/three.');
} catch (error) {
  console.error(`FAIL: ${error.message}`);
  // Classify common connectivity errors for a human-readable hint only. This script
  // must never emit a machine-readable fallback flag: deployment is fail-closed.
  const networkFailure = /\b(?:ENOTFOUND|EAI_AGAIN|ETIMEDOUT|ECONNRESET|ECONNREFUSED|EHOSTUNREACH|ENETUNREACH|ECONNABORTED|ERR_SOCKET_TIMEOUT)\b|\bsocket hang up\b|\bgetaddrinfo\b.*(?:ENOTFOUND|EAI_AGAIN)/i.test(error.message);
  if (networkFailure) {
    console.error('Gợi ý: kiểm tra mạng/registry npm hoặc chạy lại trên máy có Internet. Bước triển khai sẽ dừng; không chuyển sang CDN dự phòng.');
  }
  process.exitCode = 1;
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
