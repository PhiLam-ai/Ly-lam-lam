'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawn, exec } = require('node:child_process');

const appRoot = path.resolve(__dirname, '..');
const serverScript = path.join(__dirname, 'serve-preview.cjs');
const requiredFiles = [
  'index.html',
  'lam-default.glb',
  'vendor/three/build/three.module.js',
  'vendor/three/examples/jsm/loaders/GLTFLoader.js',
  'vendor/three/examples/jsm/controls/OrbitControls.js',
  'tools/serve-preview.cjs'
];

function verifyFiles() {
  const missing = requiredFiles.filter(relative => !fs.existsSync(path.join(appRoot, relative)));
  if (missing.length) {
    throw new Error('Thiếu tệp cần thiết trong thư mục ứng dụng:\n- ' + missing.join('\n- '));
  }
}

try {
  verifyFiles();
} catch (error) {
  console.error('KHÔNG THỂ KHỞI ĐỘNG LÝ LÂM LAM');
  console.error(error.message);
  process.exit(1);
}

if (process.argv.includes('--check')) {
  console.log('PASS: Windows launcher prerequisites found (' + requiredFiles.length + ' files).');
  process.exit(0);
}

if (process.argv.length > 2) {
  console.error('Tham số không hỗ trợ. Dùng --check để kiểm tra tệp phụ thuộc.');
  process.exit(2);
}

console.log('Đang khởi động bản xem thử LÝ LÂM LAM bằng Three.js nội bộ...');
console.log('Máy chủ chỉ nghe trên localhost; không mở cổng ra mạng.');
const server = spawn(process.execPath, [
  serverScript, '--host', '127.0.0.1', '--port', '0', '--root', appRoot, '--three', 'local'
], {
  cwd: appRoot,
  windowsHide: false,
  stdio: ['inherit', 'pipe', 'pipe']
});

let pending = '';
let browserOpeningStarted = false;
let stopping = false;

server.stdout.setEncoding('utf8');
server.stderr.setEncoding('utf8');

server.stdout.on('data', chunk => {
  process.stdout.write(chunk);
  pending = (pending + chunk).slice(-4096);
  const match = pending.match(/URL: (http:\/\/127\.0\.0\.1:\d+\/\?three=local)/);
  if (!match || browserOpeningStarted) return;
  browserOpeningStarted = true;
  const url = match[1];
  if (process.platform === 'win32') {
    exec('start "" "' + url + '"', { windowsHide: true }, error => {
      if (error) console.log('Không tự mở được trình duyệt. Anh hãy mở đường dẫn này: ' + url);
    });
  } else {
    console.log('Mở trình duyệt và nhập địa chỉ: ' + url);
  }
});

server.stderr.on('data', chunk => process.stderr.write(chunk));
server.once('error', error => {
  console.error('Không chạy được máy chủ preview: ' + error.message);
  process.exitCode = 1;
});
server.once('exit', (code, signal) => {
  if (!stopping && code !== 0) {
    console.error('Máy chủ preview đã dừng (code=' + code + ', signal=' + signal + ').');
    process.exitCode = code || 1;
  }
});
process.once('SIGINT', () => {
  stopping = true;
  server.kill();
});
