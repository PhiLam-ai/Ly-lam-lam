#!/usr/bin/env node
'use strict';
// Small dependency-free static server for local browser testing and optional same-Wi-Fi iPhone testing.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const args = process.argv.slice(2);
let host = '127.0.0.1';
let port = 8080;
let rootArg = '.';
let threeMode = 'cdn';
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === '--host') host = args[++i] || '';
  else if (arg === '--port') port = Number(args[++i]);
  else if (arg === '--root') rootArg = args[++i] || '';
  else if (arg === '--three') { threeMode = args[++i] || ''; if (!['cdn', 'unpkg', 'local'].includes(threeMode)) throw new Error('--three phải là cdn, unpkg hoặc local.'); }
  else if (arg === '--help' || arg === '-h') {
    console.log('Dùng: node tools/serve-preview.cjs [--port 8080] [--root .] [--host 127.0.0.1|0.0.0.0] [--three cdn|unpkg|local]');
    console.log('Mặc định chỉ lắng nghe localhost. --host 0.0.0.0 cho phép thiết bị cùng mạng truy cập; chỉ dùng trên mạng tin cậy.');
    process.exit(0);
  } else throw new Error(`Tham số không được hỗ trợ: ${arg}`);
}
if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('--port phải là số nguyên từ 0 đến 65535.');
if (!['127.0.0.1', 'localhost', '0.0.0.0', '::1'].includes(host)) throw new Error('--host chỉ chấp nhận 127.0.0.1, localhost, ::1 hoặc 0.0.0.0.');
const root = fs.realpathSync(path.resolve(rootArg));
if (!fs.statSync(root).isDirectory()) throw new Error('--root phải là thư mục.');
const mime = {
  '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.mjs':'text/javascript; charset=utf-8',
  '.cjs':'text/javascript; charset=utf-8', '.json':'application/json; charset=utf-8', '.glb':'model/gltf-binary',
  '.txt':'text/plain; charset=utf-8', '.css':'text/css; charset=utf-8', '.svg':'image/svg+xml',
  '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp', '.wasm':'application/wasm'
};
function reply(res, status, body) { res.writeHead(status, {'content-type':'text/plain; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}); res.end(body); }
const server = http.createServer((req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') return reply(res, 405, 'Method not allowed');
  let decoded;
  try {
    const rawPath = String(req.url || '/').split(/[?#]/, 1)[0];
    decoded = decodeURIComponent(rawPath);
  } catch { return reply(res, 400, 'Bad request'); }
  if (decoded.includes('\\') || decoded.includes('\0')) return reply(res, 400, 'Bad request');
  const relative = decoded.replace(/^\/+/, '') || 'index.html';
  const candidate = path.resolve(root, relative);
  if (candidate !== root && !candidate.startsWith(root + path.sep)) return reply(res, 403, 'Forbidden');
  let actual, stat;
  try { actual = fs.realpathSync(candidate); stat = fs.statSync(actual); } catch { return reply(res, 404, 'Not found'); }
  if (actual !== root && !actual.startsWith(root + path.sep)) return reply(res, 403, 'Forbidden');
  if (!stat.isFile()) return reply(res, 404, 'Not found');
  const headers = {'content-type':mime[path.extname(actual).toLowerCase()] || 'application/octet-stream','content-length':stat.size,'cache-control':'no-store','x-content-type-options':'nosniff'};
  res.writeHead(200, headers);
  if (req.method === 'HEAD') return res.end();
  const stream = fs.createReadStream(actual);
  stream.on('error', () => { if (!res.headersSent) reply(res, 500, 'Read error'); else res.destroy(); });
  stream.pipe(res);
});
server.on('error', error => { console.error(`Không thể mở máy chủ: ${error.message}`); process.exitCode = 1; });
server.listen(port, host, () => {
  const address = server.address();
  console.log(`LÝ LÂM LAM đang phục vụ thư mục: ${root}`);
  const suffix = threeMode === 'local' ? '?three=local' : threeMode === 'unpkg' ? '?three=unpkg' : '';
  console.log(`URL: http://${host === '0.0.0.0' ? '127.0.0.1' : host}:${address.port}/${suffix}`);
  if (host === '0.0.0.0') {
    const addresses = Object.values(os.networkInterfaces()).flat().filter(x => x && x.family === 'IPv4' && !x.internal);
    for (const item of addresses) console.log(`iPhone cùng Wi-Fi: http://${item.address}:${address.port}/${suffix}`);
    console.log('CẢNH BÁO: máy chủ HTTP không mã hóa, chỉ dùng trên mạng tin cậy; nhấn Ctrl+C để dừng.');
  } else console.log('Chỉ máy này truy cập được. Nhấn Ctrl+C để dừng.');
});
