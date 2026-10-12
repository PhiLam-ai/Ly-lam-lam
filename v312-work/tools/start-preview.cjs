#!/usr/bin/env node
'use strict';
// One-command launcher: choose a verified local Three.js bundle when present, otherwise use the CDN path.
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const root = path.resolve(__dirname, '..');
let host = '127.0.0.1';
let port = 8080;
let projectRoot = root;
let forceLocal = false;
let requestedThree = null;
let openBrowser = false;
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === '--lan') host = '0.0.0.0';
  else if (arg === '--host') {
    const value = args[++i];
    if (!['127.0.0.1', 'localhost', '::1', '0.0.0.0'].includes(value)) throw new Error('--host chỉ chấp nhận 127.0.0.1, localhost, ::1 hoặc 0.0.0.0.');
    host = value;
  } else if (arg === '--port') {
    port = Number(args[++i]);
    if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('--port phải là số nguyên từ 0 đến 65535.');
  } else if (arg === '--root') {
    const value = args[++i];
    if (!value) throw new Error('--root cần một thư mục.');
    projectRoot = path.resolve(value);
  } else if (arg === '--local-three') forceLocal = true;
  else if (arg === '--open-browser') openBrowser = true;
  else if (arg === '--three') { const value = args[++i]; if (!['cdn', 'unpkg', 'local'].includes(value)) throw new Error('--three phải là cdn, unpkg hoặc local.'); requestedThree = value; }
  else if (arg === '--help' || arg === '-h') {
    console.log('Dùng: node tools/start-preview.cjs [--lan] [--port 8080] [--root thư-mục] [--local-three] [--three cdn|unpkg|local] [--open-browser]');
    console.log('Mặc định chỉ mở localhost; --lan cho phép iPhone cùng Wi-Fi truy cập trên mạng tin cậy.');
    console.log('--local-three hoặc --three local yêu cầu vendor/three có đủ core, GLTFLoader và OrbitControls; nếu thiếu, launcher dừng an toàn.');
    console.log('--three unpkg chọn CDN thay thế đã ghim three@0.160.0; vẫn cần Internet.');
    console.log('--open-browser mở URL xem thử bằng trình duyệt mặc định sau khi máy chủ báo sẵn sàng.');
    process.exit(0);
  } else throw new Error(`Tham số không được hỗ trợ: ${arg}`);
}
const realRoot = fs.realpathSync(projectRoot);
if (!fs.statSync(realRoot).isDirectory()) throw new Error('--root phải là thư mục.');
const localAssets = [
  'vendor/three/build/three.module.js',
  'vendor/three/examples/jsm/loaders/GLTFLoader.js',
  'vendor/three/examples/jsm/controls/OrbitControls.js',
  'lam-default.glb'
];
const missing = localAssets.filter(file => {
  try { return !fs.statSync(path.join(realRoot, file)).isFile(); } catch { return true; }
});
if (forceLocal && missing.length) {
  console.error(`Không thể khởi chạy với Three.js nội bộ; thiếu: ${missing.join(', ')}`);
  console.error('Chạy node tools/fetch-vendor-three.cjs trên máy có Internet rồi thử lại.');
  process.exit(1);
}
if (forceLocal) requestedThree = 'local';
if (requestedThree === 'local' && missing.length) {
  console.error(`Không thể khởi chạy với Three.js nội bộ; thiếu: ${missing.join(', ')}`);
  console.error('Chạy node tools/fetch-vendor-three.cjs trên máy có Internet rồi thử lại.');
  process.exit(1);
}
const useLocal = requestedThree ? requestedThree === 'local' : missing.length === 0;
const threeMode = requestedThree || (useLocal ? 'local' : 'cdn');
// File presence alone does not prove a usable local Three.js bundle. Validate the
// relative import graph before opening the preview so a partial/corrupt vendor tree
// fails early with a useful message rather than a blank avatar in the browser.
if (useLocal) {
  const integrityScript = path.join(__dirname, 'vendor-module-integrity.cjs');
  const integrity = cp.spawnSync(process.execPath, [integrityScript, realRoot], {
    cwd: root, encoding: 'utf8', windowsHide: true, timeout: 15000,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  if (integrity.stdout) process.stdout.write(integrity.stdout);
  if (integrity.stderr) process.stderr.write(integrity.stderr);
  if (integrity.error || integrity.status !== 0) {
    console.error(`Không thể khởi chạy chế độ Three.js nội bộ vì kiểm tra đồ thị module thất bại${integrity.error ? `: ${integrity.error.message}` : ` (mã ${integrity.status})`}.`);
    console.error('Hãy nhập lại gói three@0.160.0 chính thức bằng tools/import-three-offline-bundle.cjs rồi thử lại.');
    process.exit(1);
  }
}
const serverScript = path.join(root, 'tools', 'serve-preview.cjs');
const serverArgs = [serverScript, '--host', host, '--port', String(port), '--root', realRoot, '--three', threeMode];
console.log(`Chế độ Three.js: ${threeMode === 'local' ? 'nội bộ (đã tìm thấy các tệp bắt buộc)' : threeMode === 'unpkg' ? 'CDN thay thế unpkg (cần Internet)' : 'CDN jsDelivr (cần Internet; vendor/three chưa sẵn sàng)'}`);
console.log('Khởi chạy máy chủ xem trước…');
const child = cp.spawn(process.execPath, serverArgs, { stdio: ['inherit', 'pipe', 'pipe'], windowsHide: true });
let browserOpened = false;
let serverOutputBuffer = '';
child.stdout.setEncoding('utf8');
child.stderr.setEncoding('utf8');
child.stdout.on('data', chunk => {
  process.stdout.write(chunk);
  serverOutputBuffer += chunk;
  const lines = serverOutputBuffer.split(/\r?\n/);
  serverOutputBuffer = lines.pop() || '';
  const readyLine = lines.find(line => /URL: http:\/\//.test(line));
  const match = readyLine && readyLine.match(/URL: (http:\/\/[^\s]+)/);
  if (!openBrowser || browserOpened || !match) return;
  browserOpened = true;
  const url = match[1];
  let command, args;
  if (process.platform === 'win32') {
    command = 'cmd.exe'; args = ['/d', '/s', '/c', 'start', '', url];
  } else if (process.platform === 'darwin') {
    command = 'open'; args = [url];
  } else {
    command = 'xdg-open'; args = [url];
  }
  try {
    const opener = cp.spawn(command, args, { detached: true, stdio: 'ignore', windowsHide: true });
    opener.on('error', error => console.error(`Không tự mở được trình duyệt (${error.message}); hãy mở URL thủ công: ${url}`));
    opener.unref();
    console.log('Đã yêu cầu mở URL bằng trình duyệt mặc định. Nếu trình duyệt không bật, hãy mở URL ở dòng trên.');
  } catch (error) {
    console.error(`Không tự mở được trình duyệt (${error.message}); hãy mở URL thủ công: ${url}`);
  }
});
child.stderr.on('data', chunk => process.stderr.write(chunk));
// Forward terminal shutdown to the server child so Ctrl+C and test cleanup do not
// leave an orphan preview server listening after the launcher exits.
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    if (child.exitCode === null && !child.killed) child.kill(signal);
  });
}
child.on('error', error => { console.error(`Không khởi chạy được máy chủ: ${error.message}`); process.exitCode = 1; });
child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exitCode = code === null ? 1 : code;
});
