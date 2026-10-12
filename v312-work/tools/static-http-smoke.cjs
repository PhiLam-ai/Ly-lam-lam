#!/usr/bin/env node
'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { once } = require('node:events');
// Optional target directory lets CI smoke-test the exact assembled deployment artifact.
const root = path.resolve(process.argv[2] || path.join(__dirname, '..'));
if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
  console.error(`FAIL: thư mục cần kiểm tra không tồn tại hoặc không phải thư mục: ${root}`);
  process.exit(1);
}
const mime = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.mjs':'text/javascript; charset=utf-8', '.cjs':'text/javascript; charset=utf-8', '.json':'application/json; charset=utf-8', '.glb':'model/gltf-binary', '.txt':'text/plain; charset=utf-8' };
function send(res, status, body, type='text/plain; charset=utf-8') { res.writeHead(status, {'content-type':type,'cache-control':'no-store'}); res.end(body); }
const server = http.createServer((req,res) => {
  let pathname;
  // Decode the raw request path before URL normalization. Parsing with new URL first
  // can normalize encoded dot segments and hide traversal attempts from this guard.
  try {
    const rawPath = String(req.url || '/').split(/[?#]/, 1)[0];
    pathname = decodeURIComponent(rawPath);
  } catch { return send(res,400,'Bad request'); }
  if (req.method !== 'GET' && req.method !== 'HEAD') return send(res,405,'Method not allowed');
  const relative = pathname.replace(/^\/+/, '') || 'index.html';
  const target = path.resolve(root, relative);
  if (target !== root && !target.startsWith(root + path.sep)) return send(res,403,'Forbidden');
  let stat;
  try { stat = fs.statSync(target); } catch { return send(res,404,'Not found'); }
  if (!stat.isFile()) return send(res,404,'Not found');
  res.writeHead(200, {'content-type':mime[path.extname(target)] || 'application/octet-stream','content-length':stat.size,'cache-control':'no-store'});
  if (req.method === 'HEAD') return res.end();
  fs.createReadStream(target).pipe(res);
});
(async () => {
  server.listen(0,'127.0.0.1');
  await once(server,'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  const checks = [
    ['index.html','text/html'],
    ['lam-default.glb','model/gltf-binary'],
    ['expression-baseline-cases-v1.json','application/json'],
    ['avatar_expression_motion.js','text/javascript'],
    ['avatar_api_recovery.js','text/javascript'],
    ['avatar_expression_composer.js','text/javascript'],
    ['avatar_morph_transition.js','text/javascript']
  ];
  try {
    for (const [url, expectedType] of checks) {
      const response = await fetch(`${base}/${url}`);
      if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
      if (!(response.headers.get('content-type') || '').startsWith(expectedType)) throw new Error(`${url}: Content-Type không đúng (${response.headers.get('content-type')})`);
      const bytes = Buffer.from(await response.arrayBuffer());
      if (!bytes.length) throw new Error(`${url}: response rỗng`);
      if (url === 'index.html' && !bytes.toString('utf8').includes('<script type="module">')) throw new Error('index.html thiếu module entrypoint');
      if (url === 'lam-default.glb' && (bytes.toString('ascii',0,4)!=='glTF' || bytes.readUInt32LE(4)!==2 || bytes.readUInt32LE(8)!==bytes.length)) throw new Error('GLB response header/length không hợp lệ');
      console.log(`PASS HTTP ${response.status} ${url} (${bytes.length} bytes)`);
    }
    // HEAD is commonly used by hosting/CDN health checks; it must expose the same
    // asset metadata as GET without transmitting the potentially large GLB body.
    for (const [url, expectedType] of checks.slice(0, 2)) {
      const response = await fetch(`${base}/${url}`, { method: 'HEAD' });
      if (!response.ok) throw new Error(`HEAD ${url}: HTTP ${response.status}`);
      if (!(response.headers.get('content-type') || '').startsWith(expectedType)) throw new Error(`HEAD ${url}: Content-Type không đúng (${response.headers.get('content-type')})`);
      const body = Buffer.from(await response.arrayBuffer());
      if (body.length !== 0) throw new Error(`HEAD ${url}: phản hồi không được có body`);
      const expectedSize = fs.statSync(path.join(root, url)).size;
      if (Number(response.headers.get('content-length')) !== expectedSize) throw new Error(`HEAD ${url}: Content-Length không khớp tệp nguồn`);
      console.log(`PASS HTTP HEAD ${url} (metadata ${expectedSize} bytes, body rỗng)`);
    }
    const missing = await fetch(`${base}/__startup-smoke_missing__.js`);
    if (missing.status !== 404) throw new Error(`Tài nguyên không tồn tại phải trả 404, nhận ${missing.status}`);
    console.log('PASS HTTP 404 cho tài nguyên không tồn tại');
    // Use a raw HTTP request so the client URL parser does not normalize dot segments
    // before the server receives the encoded traversal path.
    const traversal = await new Promise((resolve, reject) => {
      const request = http.request({ hostname: '127.0.0.1', port: server.address().port, path: '/%2e%2e/etc/passwd', method: 'GET' }, response => {
        response.resume(); response.on('end', () => resolve(response));
      });
      request.on('error', reject); request.end();
    });
    if (traversal.statusCode !== 403) throw new Error(`Đường dẫn thoát khỏi thư mục gốc phải trả 403, nhận ${traversal.statusCode}`);
    console.log('PASS HTTP 403 cho đường dẫn thoát khỏi thư mục gốc');
    console.log('Giới hạn: máy chủ HTTP cục bộ mô phỏng; không kiểm tra CDN, WebGL, render hoặc Safari/iPhone.');
  } finally { server.close(); }
})().catch(error => { console.error(`FAIL: ${error.message}`); server.close(() => process.exit(1)); });
