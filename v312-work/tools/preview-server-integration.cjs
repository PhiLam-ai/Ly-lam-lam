#!/usr/bin/env node
'use strict';
// Integration smoke test for the real preview server, not a separate HTTP mock.
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');
const root = path.resolve(process.argv[2] || path.join(__dirname, '..'));
const serverScript = path.join(__dirname, 'serve-preview.cjs');
const child = spawn(process.execPath, [serverScript, '--host', '127.0.0.1', '--port', '0', '--root', root, '--three', 'local'], {
  cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']
});
let stdout = '', stderr = '', settled = false;
child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8');
child.stdout.on('data', chunk => { stdout += chunk; });
child.stderr.on('data', chunk => { stderr += chunk; });
function stop() {
  if (child.exitCode === null && !child.killed) child.kill();
}
function fail(message) {
  console.error(`FAIL preview server integration: ${message}`);
  if (stdout.trim()) console.error(stdout.trim());
  if (stderr.trim()) console.error(stderr.trim());
  stop(); process.exitCode = 1;
}
const startup = new Promise((resolve, reject) => {
  const startedAt = Date.now();
  const poll = setInterval(() => {
    const match = stdout.match(/URL: http:\/\/127\.0\.0\.1:(\d+)\/\?three=local/);
    if (match) { clearInterval(poll); resolve(`http://127.0.0.1:${match[1]}`); }
    else if (child.exitCode !== null) { clearInterval(poll); reject(new Error(`server exited (${child.exitCode})`)); }
    else if (Date.now() - startedAt > 8000) { clearInterval(poll); reject(new Error('server did not print a ready URL within 8 seconds')); }
  }, 25);
});
(async () => {
  try {
    const base = await startup;
    const checks = [
      ['/', 'text/html', body => body.toString('utf8').includes('Lý Lâm Lam') && body.toString('utf8').includes('type="module"')],
      ['/lam-default.glb', 'model/gltf-binary', body => body.length >= 20 && body.toString('ascii', 0, 4) === 'glTF' && body.readUInt32LE(4) === 2 && body.readUInt32LE(8) === body.length],
      ['/vendor/three/build/three.module.js', 'text/javascript', body => body.toString('utf8').includes('REVISION') || body.toString('utf8').includes('WebGLRenderer')],
      ['/vendor/three/examples/jsm/loaders/GLTFLoader.js', 'text/javascript', body => body.toString('utf8').includes('GLTFLoader')],
      ['/vendor/three/examples/jsm/controls/OrbitControls.js', 'text/javascript', body => body.toString('utf8').includes('OrbitControls')]
    ];
    for (const [url, contentType, validate] of checks) {
      const response = await fetch(base + url);
      if (!response.ok) throw new Error(`${url}: expected HTTP 200, got ${response.status}`);
      if (!(response.headers.get('content-type') || '').startsWith(contentType)) throw new Error(`${url}: wrong Content-Type ${response.headers.get('content-type')}`);
      const body = Buffer.from(await response.arrayBuffer());
      if (!body.length || !validate(body)) throw new Error(`${url}: empty or invalid response body`);
      console.log(`PASS real-server GET ${url} (${body.length} bytes)`);
    }
    const head = await fetch(base + '/lam-default.glb', { method: 'HEAD' });
    if (head.status !== 200 || Number(head.headers.get('content-length')) !== require('node:fs').statSync(path.join(root, 'lam-default.glb')).size || (await head.arrayBuffer()).byteLength !== 0) throw new Error('GLB HEAD metadata/body mismatch');
    console.log('PASS real-server HEAD /lam-default.glb');
    const missing = await fetch(base + '/__v306_missing__.js');
    if (missing.status !== 404) throw new Error(`missing asset should be HTTP 404, got ${missing.status}`);
    console.log('PASS real-server missing asset HTTP 404');
    // Use a raw HTTP request: fetch/URL normalizes encoded dot segments before sending.
    const address = new URL(base);
    const traversal = await new Promise((resolve, reject) => {
      const request = http.request({ hostname: address.hostname, port: Number(address.port), path: '/%2e%2e/package.json', method: 'GET' }, response => {
        response.resume(); response.on('end', () => resolve(response));
      });
      request.on('error', reject); request.end();
    });
    if (traversal.statusCode !== 403) throw new Error(`path traversal should be HTTP 403, got ${traversal.statusCode}`);
    console.log('PASS real-server path traversal HTTP 403');
    console.log('PASS REAL PREVIEW SERVER INTEGRATION');
  } catch (error) {
    fail(error && error.message ? error.message : String(error));
  } finally {
    settled = true; stop();
  }
})();
child.on('error', error => { if (!settled) fail(`could not start server: ${error.message}`); });
